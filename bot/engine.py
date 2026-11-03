"""Paper-trading engine: opening range breakout on ASX stocks in play.

Pure logic with no network access, so it can be tested with made-up bars.
A bar is a dict: {"t": pandas.Timestamp (Australia/Sydney), "o", "h", "l", "c", "v"}.
"""
from __future__ import annotations

import math
from datetime import datetime, time

import pandas as pd

TZ = "Australia/Sydney"
BAR = pd.Timedelta(minutes=5)


# ---------- ASX price steps ----------
def tick_size(price: float) -> float:
    if price < 0.10:
        return 0.001
    if price < 2.00:
        return 0.005
    return 0.01


def round_tick(price: float, direction: str) -> float:
    """Round to a valid ASX price step: 'up' for buys, 'down' for sells/stops."""
    step = tick_size(price)
    n = price / step
    n = math.ceil(n - 1e-9) if direction == "up" else math.floor(n + 1e-9)
    return round(n * step, 3)


def hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


# ---------- engine ----------
class Engine:
    def __init__(self, state: dict, trades: list, cfg: dict):
        self.s = state
        self.trades = trades
        self.cfg = cfg

    # --- helpers ---
    @property
    def day(self) -> dict:
        return self.s["day"]

    def log(self, t, msg: str):
        stamp = pd.Timestamp(t).tz_convert(TZ).strftime("%H:%M") if t is not None else ""
        self.day.setdefault("log", []).append(f"{stamp} {msg}".strip())

    def fee(self) -> float:
        return float(self.cfg["brokerage_per_trade"])

    def equity(self, prices: dict | None = None) -> float:
        eq = self.s["cash"]
        for p in self.s["positions"]:
            px = (prices or {}).get(p["sym"], p.get("last", p["entry"]))
            eq += p["qty"] * px
        return round(eq, 2)

    # --- day lifecycle ---
    def new_day(self, date_str: str, universe: dict):
        self.s["day"] = {
            "date": date_str,
            "phase": "waiting_open",   # waiting_open -> trading -> closed
            "start_equity": self.equity(),
            "universe_size": len(universe),
            "watchlist": [],
            "entered": [],
            "realized": 0.0,
            "losses_in_row": 0,
            "no_new_entries": False,
            "market_change_pct": None,
            "last_ts": None,
            "log": [],
        }

    def opening_range(self, bars: list) -> dict | None:
        """First N minutes of today's 5-minute bars (covers the ASX's staggered 10:00-10:10 open)."""
        n = self.cfg["opening_range_minutes"] // 5
        start = hhmm("10:00")
        orb = [b for b in bars if b["t"].time() >= start][:n]
        if len(orb) < n:
            return None
        # every OR bar must fall inside the window
        end = (datetime.combine(orb[0]["t"].date(), start) + pd.Timedelta(minutes=self.cfg["opening_range_minutes"])).time()
        if any(b["t"].time() >= end for b in orb):
            return None
        return {
            "open": orb[0]["o"],
            "high": max(b["h"] for b in orb),
            "low": min(b["l"] for b in orb),
            "close": orb[-1]["c"],
            "volume": sum(b["v"] for b in orb),
            "end": orb[-1]["t"],
        }

    def select_watchlist(self, bars_by_sym: dict, index_bars: list | None, universe: dict) -> bool:
        """Pick today's stocks in play once the opening range is complete. Returns True when done."""
        cfg = self.cfg
        # Market filter: long-only, so stand aside when the whole market opens weak.
        if index_bars:
            idx_or = self.opening_range(index_bars)
            if idx_or is None:
                return False
            prev = universe.get("__index__", {}).get("prev_close")
            if prev:
                chg = (idx_or["close"] / prev - 1) * 100
                self.day["market_change_pct"] = round(chg, 2)
                if chg < cfg["market_min_change_pct"]:
                    self.day["watchlist"] = []
                    self.day["phase"] = "trading"
                    self.day["no_new_entries"] = True
                    self.log(idx_or["end"], f"ASX 200 {chg:+.2f}% at the open: weak market, standing aside today.")
                    return True

        cands = []
        ready = 0
        for sym, bars in bars_by_sym.items():
            meta = universe.get(sym)
            if not meta:
                continue
            orr = self.opening_range(bars)
            if orr is None:
                continue
            ready += 1
            avg_or_vol = meta.get("avg_or_volume") or 0
            if avg_or_vol <= 0:
                continue
            rvol = orr["volume"] / avg_or_vol
            bullish = orr["close"] > orr["open"]
            above_prev = orr["close"] > meta.get("prev_close", 0)
            if rvol >= cfg["min_relative_volume"] and bullish and above_prev:
                cands.append({
                    "sym": sym,
                    "rvol": round(rvol, 2),
                    "or_high": orr["high"],
                    "or_low": orr["low"],
                    "or_open": orr["open"],
                    "or_close": orr["close"],
                    "atr": meta["atr"],
                    "gap_pct": round((orr["open"] / meta["prev_close"] - 1) * 100, 2) if meta.get("prev_close") else None,
                })
        if ready == 0:
            return False
        cands.sort(key=lambda c: c["rvol"], reverse=True)
        self.day["watchlist"] = cands[: cfg["watchlist_size"]]
        self.day["phase"] = "trading"
        if self.day["watchlist"]:
            names = ", ".join(f"{c['sym']} ({c['rvol']}x)" for c in self.day["watchlist"])
            self.log(None, f"Stocks in play: {names}")
        else:
            self.log(None, "No stock met the in-play rules today. No trades.")
        return True

    # --- trading ---
    def _risk_budget(self) -> float:
        return self.day["start_equity"] * self.cfg["risk_per_trade_pct"] / 100

    def _check_halt(self, t, unrealized: float):
        if self.day["no_new_entries"]:
            return
        limit = -self.day["start_equity"] * self.cfg["daily_loss_limit_pct"] / 100
        if self.day["realized"] + unrealized <= limit:
            self.day["no_new_entries"] = True
            self.log(t, "Daily loss limit reached. No more entries today.")
        elif self.day["losses_in_row"] >= self.cfg["max_losses_in_row"]:
            self.day["no_new_entries"] = True
            self.log(t, f"{self.day['losses_in_row']} losses in a row. Stopping for the day.")

    def _enter(self, w: dict, bar: dict):
        cfg = self.cfg
        trigger = w["or_high"] + tick_size(w["or_high"])
        raw = max(trigger, bar["o"]) * (1 + cfg["slippage_pct"] / 100)
        price = round_tick(raw, "up")
        stop = max(w["or_low"], price - cfg["stop_atr_fraction"] * w["atr"])
        stop = min(stop, price * (1 - cfg["min_stop_pct"] / 100))
        stop = round_tick(stop, "down")
        risk_ps = price - stop
        if risk_ps <= 0:
            return
        qty = int(self._risk_budget() / risk_ps)
        max_value = min(self.day["start_equity"] * cfg["max_position_pct"] / 100, self.s["cash"] - self.fee())
        qty = min(qty, int(max_value / price))
        if qty * price < cfg["min_trade_value"]:
            self.log(bar["t"], f"Skipped {w['sym']}: not enough cash or risk room for a sensible size.")
            w["skipped"] = True
            return
        cost = qty * price + self.fee()
        self.s["cash"] = round(self.s["cash"] - cost, 2)
        pos = {
            "sym": w["sym"], "qty": qty, "entry": price, "entry_time": bar["t"].isoformat(),
            "stop": stop, "initial_stop": stop, "risk_ps": round(risk_ps, 4), "high": bar["h"],
            "last": bar["c"], "fees": self.fee(), "rvol": w["rvol"], "atr": w["atr"], "stop_note": "initial",
        }
        self.s["positions"].append(pos)
        self.day["entered"].append(w["sym"])
        self.log(bar["t"], f"BUY {qty} {w['sym']} @ ${price:.3f}, stop ${stop:.3f} (breakout above ${w['or_high']:.3f})")
        # Same-bar stop check (conservative): if it closed below the stop, we're out.
        if bar["c"] <= stop:
            self._exit(pos, stop, bar["t"], "Stopped out on entry bar")

    def _exit(self, pos: dict, raw_price: float, t, reason: str):
        price = round_tick(raw_price * (1 - self.cfg["slippage_pct"] / 100), "down")
        proceeds = pos["qty"] * price - self.fee()
        self.s["cash"] = round(self.s["cash"] + proceeds, 2)
        fees = pos["fees"] + self.fee()
        gross = pos["qty"] * (price - pos["entry"])
        net = gross - fees
        r_mult = (price - pos["entry"]) / pos["risk_ps"] if pos["risk_ps"] else 0
        self.s["positions"].remove(pos)
        self.day["realized"] = round(self.day["realized"] + net, 2)
        self.day["losses_in_row"] = self.day["losses_in_row"] + 1 if net < 0 else 0
        trade = {
            "id": len(self.trades) + 1,
            "date": self.day["date"],
            "sym": pos["sym"],
            "qty": pos["qty"],
            "entry_time": pos["entry_time"],
            "entry_price": pos["entry"],
            "exit_time": pd.Timestamp(t).isoformat(),
            "exit_price": price,
            "initial_stop": pos["initial_stop"],
            "fees": round(fees, 2),
            "gross": round(gross, 2),
            "net": round(net, 2),
            "pct": round(net / (pos["qty"] * pos["entry"]) * 100, 2),
            "r": round(r_mult, 2),
            "rvol": pos.get("rvol"),
            "reason": reason,
        }
        self.trades.append(trade)
        self.log(t, f"SELL {pos['qty']} {pos['sym']} @ ${price:.3f} ({reason}) net ${net:+.2f}")

    def _manage(self, pos: dict, bar: dict):
        cfg = self.cfg
        # 1) stop hit? (gap through stop fills at the open)
        if bar["l"] <= pos["stop"]:
            fill = min(pos["stop"], bar["o"])
            reason = {"initial": "Stop loss", "breakeven": "Breakeven stop", "trail": "Trailing stop"}[pos["stop_note"]]
            self._exit(pos, fill, bar["t"], reason)
            return
        pos["last"] = bar["c"]
        pos["high"] = max(pos["high"], bar["h"])
        r = pos["risk_ps"]
        # 2) move stop to breakeven once +1R
        if pos["stop_note"] == "initial" and pos["high"] >= pos["entry"] + cfg["breakeven_at_r"] * r:
            pos["stop"] = round_tick(pos["entry"] + tick_size(pos["entry"]), "up")
            pos["stop_note"] = "breakeven"
        # 3) trail once +2R
        if pos["high"] >= pos["entry"] + cfg["trail_start_r"] * r:
            dist = max(cfg["trail_distance_r"] * r, cfg["trail_atr_fraction"] * pos.get("atr", 0))
            trail = round_tick(pos["high"] - dist, "down")
            if trail > pos["stop"]:
                pos["stop"] = trail
                pos["stop_note"] = "trail"

    def process(self, bars_by_sym: dict, unrealized_fn=None):
        """Walk forward through every complete bar not yet processed, in time order."""
        day = self.day
        if day["phase"] != "trading":
            return
        last_ts = pd.Timestamp(day["last_ts"]) if day["last_ts"] else None
        stamps = sorted({b["t"] for bars in bars_by_sym.values() for b in bars
                         if last_ts is None or b["t"] > last_ts})
        index = {sym: {b["t"]: b for b in bars} for sym, bars in bars_by_sym.items()}
        last_entry = hhmm(self.cfg["last_entry_time"])
        exit_t = hhmm(self.cfg["exit_time"])
        or_end = (datetime.combine(datetime.today(), hhmm("10:00")) +
                  pd.Timedelta(minutes=self.cfg["opening_range_minutes"])).time()

        for ts in stamps:
            if ts.time() < or_end:
                day["last_ts"] = ts.isoformat()
                continue
            # manage open positions
            for pos in list(self.s["positions"]):
                bar = index.get(pos["sym"], {}).get(ts)
                if bar:
                    self._manage(pos, bar)
            # time exit: close everything on the exit bar
            if ts.time() >= exit_t:
                for pos in list(self.s["positions"]):
                    bar = index.get(pos["sym"], {}).get(ts)
                    px = bar["c"] if bar else pos["last"]
                    self._exit(pos, px, ts, "End of day exit")
                day["last_ts"] = ts.isoformat()
                self.close_day(ts)
                return
            unreal = sum(p["qty"] * (p["last"] - p["entry"]) - p["fees"] for p in self.s["positions"])
            self._check_halt(ts, unreal)
            # entries
            if not day["no_new_entries"] and ts.time() < last_entry:
                for w in day["watchlist"]:
                    if len(self.s["positions"]) >= self.cfg["max_positions"]:
                        break
                    if w["sym"] in day["entered"] or w.get("skipped"):
                        continue
                    bar = index.get(w["sym"], {}).get(ts)
                    if bar and bar["h"] > w["or_high"]:
                        self._enter(w, bar)
            day["last_ts"] = ts.isoformat()

    def close_day(self, t=None, prices: dict | None = None):
        """Flatten anything left (e.g. a halted stock) and mark the day finished."""
        for pos in list(self.s["positions"]):
            px = (prices or {}).get(pos["sym"], pos["last"])
            self._exit(pos, px, t or pd.Timestamp.now(tz=TZ), "End of day exit")
        if self.day["phase"] != "closed":
            self.day["phase"] = "closed"
            eq = self.equity()
            self.day["end_equity"] = eq
            hist = self.s.setdefault("daily", [])
            hist[:] = [d for d in hist if d["date"] != self.day["date"]]
            todays = [x for x in self.trades if x["date"] == self.day["date"]]
            hist.append({
                "date": self.day["date"],
                "start_equity": self.day["start_equity"],
                "end_equity": eq,
                "pnl": round(eq - self.day["start_equity"], 2),
                "trades": len(todays),
                "market_change_pct": self.day.get("market_change_pct"),
            })
            self.log(t, f"Day closed. Equity ${eq:,.2f} ({eq - self.day['start_equity']:+.2f}).")
