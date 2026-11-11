"""10-year test of the core idea on DAILY bars (Yahoo has no free 10-year intraday data).

Each day: pick the shares that gapped up most at the open (using only information known at the
open: the gap, plus price/turnover/ATR from earlier days), buy at the open, exit at the stop
(assumed hit whenever the day's low reaches it) or at the close. Same costs as the live bot.

Caveats: today's ASX list (delisted shares missing = survivorship bias); the stop is assumed hit
before any gain on days when both happen (conservative); no opening-range or volume confirmation
(daily volume isn't known at the open).
Writes data/backtest/daily10y.json.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import data as md  # noqa: E402
from engine import round_tick, tick_size  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "bot/config.json").read_text())

# Each variant: which shares to buy at the open and how to size/stop them. Keys:
#   side "up"/"down": gap direction; min_gap/max_gap: signed gap range in % (down: e.g. -20 to -3)
#   chan: Ernest Chan's "buy on gap" (open below prior low by > 1 sd of daily returns, open above 20-day average)
#   ma200: prior close above its 200-day average (uptrend); min_turnover: liquidity override ($/day)
#   market_max_gap: only on days STW (ASX 200 ETF) opens down at least this much; syms: restrict to these codes
#   risk/max_pos: % risk per trade and max % of equity per position (defaults: config, within guardrails)
GU = {"side": "up", "min_gap": 4, "max_gap": 60, "stop_atr": 1.0, "top": 5}
LC = {"side": "down", "min_gap": -40, "stop_atr": 1.0, "min_turnover": 20e6, "max_gap": -3, "top": 3, "market_max_gap": -1.5}
VARIANTS = [
    dict(GU, name="control: top 5 gap-ups >=4%, stop 1 ATR"),
    dict(LC, name="best so far: large-cap gap-down >=3% when STW opens <= -1.5%"),
    # Nagel (2012) "Evaporating Liquidity": reversal returns rise with market volatility (VIX). Proxy: STW 20-day realised vol.
    dict(LC, name="Nagel: large-cap gap-down >=3% when STW 20-day vol >= 20% (no open filter)", market_max_gap=None, mkt_vol_min=20),
    dict(LC, name="Nagel: large-cap gap-down >=3% when STW vol >= 15% and STW opens <= -1%", market_max_gap=-1.0, mkt_vol_min=15),
    dict(LC, name="Nagel: best so far + STW vol >= 15%", mkt_vol_min=15),
    # Lou, Polk & Skouras (2019) / Bremer & Sweeney: losers reverse, and the reversal is earned intraday
    dict(LC, name="Prior-day losers: large caps that fell >=5% yesterday, opening below +1%", max_gap=1, prev_ret_max=-5, market_max_gap=None),
    dict(LC, name="Prior-day losers >=5% when STW 20-day vol >= 20%", max_gap=1, prev_ret_max=-5, market_max_gap=None, mkt_vol_min=20),
    # Stress-day reversal (Quantpedia 2025): buy the morning after the whole market sold off
    dict(LC, name="Stress: large-cap gap-down >=3% after STW fell >=1.5% yesterday", market_max_gap=None, mkt_prev_ret_max=-1.5),
    dict(LC, name="Stress: same, STW fell >=2% yesterday", market_max_gap=None, mkt_prev_ret_max=-2.0),
    dict(LC, name="Weak open OR stress day: best so far, or STW fell >=1.5% yesterday", or_mkt_prev_ret_max=-1.5),
    dict(LC, name="Stress + Nagel: STW fell >=1.5% yesterday and STW vol >= 15%", market_max_gap=None, mkt_prev_ret_max=-1.5, mkt_vol_min=15),
]
EXTRA = ["STW.AX"]  # ETFs aren't in the company list


def load():
    codes = md.asx_codes(ROOT / "data/asx_codes.txt")
    tickers = sorted({f"{c}.AX" for c in codes} | set(EXTRA)) + [CFG["market_index"]]
    raw = md._download(tickers, period="10y", interval="1d")
    frames = {}
    for t, df in raw.items():
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        if len(df) > 60:
            frames[t[:-3] if t.endswith(".AX") else t] = df
    return frames


def panel(frames, field):
    return pd.DataFrame({s: f[field] for s, f in frames.items() if s != CFG["market_index"]})


def signals(v, P):
    """Boolean frame of eligible shares and a score (lower = picked first for gap-downs)."""
    cfg = CFG
    O, L, C = P["O"], P["L"], P["C"]
    prevC, prevL = C.shift(1), L.shift(1)
    gap = (O / prevC - 1) * 100
    turn = v.get("min_turnover", cfg["min_avg_turnover"])
    ok = (prevC >= cfg["min_price"]) & (P["TURN"].shift(1) >= turn) & \
         (P["ATR"].shift(1) / prevC * 100 >= v.get("min_atr", cfg["min_atr_pct"])) & (gap >= v["min_gap"]) & (gap < v["max_gap"])
    if v.get("syms"):
        mask = pd.DataFrame(False, index=O.index, columns=O.columns)
        for sym in v["syms"]:
            if sym in mask.columns:
                mask[sym] = True
        ok = ok & mask
    score = gap
    if v.get("chan"):
        sd = (C / C.shift(1) - 1).rolling(90).std().shift(1)
        ma20 = C.rolling(20).mean().shift(1)
        low_gap = O / prevL - 1
        ok = ok & (low_gap < -sd) & (O > ma20)
        score = low_gap
    if v.get("ma200"):
        ok = ok & (prevC > C.rolling(200).mean().shift(1))
    # ---- Ideas from the trading books (all use only information known before the open) ----
    stw_c = C["STW"] if "STW" in C.columns else None
    if v.get("mkt_ma") and stw_c is not None:            # Tudor Jones / O'Neil "M": only trade when the market is in an uptrend
        up = (stw_c > stw_c.rolling(v["mkt_ma"]).mean()).shift(1)
        ok = ok.mul(up.fillna(False), axis=0)
    if v.get("stock_ma"):                                  # Murphy / Pring: stock in its own uptrend
        ok = ok & (prevC > C.rolling(v["stock_ma"]).mean().shift(1))
    if v.get("near_high_pct") is not None:                 # O'Neil / Livermore: leaders trade near their highs
        hi = P["H"].rolling(252, min_periods=150).max().shift(1)
        ok = ok & (prevC >= hi * (1 - v["near_high_pct"] / 100))
    if v.get("rs_min") is not None and stw_c is not None:  # O'Neil relative strength: beat the market over ~3 months
        rs = (C / C.shift(63) - 1).sub(stw_c / stw_c.shift(63) - 1, axis=0) * 100
        ok = ok & (rs.shift(1) >= v["rs_min"])
    if v.get("pivot_days"):                                # Livermore pivotal point: open above the prior N-day high
        ok = ok & (O > P["H"].rolling(v["pivot_days"]).max().shift(1))
    if v.get("prev_vol_surge"):                            # O'Neil: volume surge (prior day volume vs 50-day average)
        V = P["V"]
        ok = ok & (V.shift(1) >= V.rolling(50).mean().shift(2) * v["prev_vol_surge"])
    if v.get("prev_engulf"):                               # Nison: bullish engulfing candle the day before
        pO, pC, ppO, ppC = O.shift(1), C.shift(1), O.shift(2), C.shift(2)
        ok = ok & (pC > pO) & (ppC < ppO) & (pC >= ppO) & (pO <= ppC)
    if v.get("prev_hammer"):                               # Nison: hammer the day before (long lower shadow, small body near the high)
        pO, pH, pL, pC = O.shift(1), P["H"].shift(1), L.shift(1), C.shift(1)
        body, rng = (pC - pO).abs(), (pH - pL)
        ok = ok & (rng > 0) & ((pO.where(pO < pC, pC) - pL) >= 2 * body) & ((pH - pO.where(pO > pC, pC)) <= body)
    # ---- Mid-week research 11 Nov 2026 (only information known before the open) ----
    if v.get("prev_ret_max") is not None:                  # Lou/Polk/Skouras; "returns after large one-day declines":
        prev_ret = (C / C.shift(1) - 1).shift(1) * 100     # yesterday's close-to-close fall, reversal earned intraday
        ok = ok & (prev_ret <= v["prev_ret_max"])
        score = prev_ret
    if v.get("mkt_vol_min") is not None and stw_c is not None:  # Nagel (2012) / Dai et al.: reversal pays when volatility is high
        rv = ((stw_c / stw_c.shift(1) - 1).rolling(20).std() * (252 ** 0.5) * 100).shift(1)
        ok = ok.mul((rv >= v["mkt_vol_min"]).fillna(False), axis=0)
    if v.get("mkt_prev_ret_max") is not None and stw_c is not None:  # market sold off yesterday (stress day)
        mprev = ((stw_c / stw_c.shift(1) - 1) * 100).shift(1)
        ok = ok.mul((mprev <= v["mkt_prev_ret_max"]).fillna(False), axis=0)
    if v.get("market_max_gap") is not None and "STW" in O.columns:
        mkt = (O["STW"] / C["STW"].shift(1) - 1) * 100
        cond = mkt <= v["market_max_gap"]
        if v.get("or_mkt_prev_ret_max") is not None and stw_c is not None:
            # either a sharply weak open OR yesterday was a market sell-off (stress day)
            cond = cond | (((stw_c / stw_c.shift(1) - 1) * 100).shift(1) <= v["or_mkt_prev_ret_max"])
        ok = ok.mul(cond, axis=0)
    return ok.fillna(False).astype(bool), score


def run(v, P, reset_yearly=False):
    cfg = CFG
    O, H, L, C = P["O"], P["H"], P["L"], P["C"]
    ATRp = P["ATR"].shift(1)
    eq = cfg["start_capital"]
    fee = cfg["brokerage_per_trade"]
    slip = cfg["slippage_pct"] / 100
    risk_pct = min(v.get("risk", cfg["risk_per_trade_pct"]), 2.0)      # guardrail: <= 2%
    max_pos = min(v.get("max_pos", cfg["max_position_pct"]), 50)      # guardrail: <= 50%
    ok, score = signals(v, P)
    daily, trades = [], []
    year = None
    for d in O.index[30:]:
        if reset_yearly and d.year != year:
            year, eq = d.year, cfg["start_capital"]
        row = score.loc[d][ok.loc[d]].dropna()
        row = row.sort_values(ascending=(v["side"] == "down")).head(v["top"])
        start = eq
        for s in row.index:
            o, h, l, c, atr = O.at[d, s], H.at[d, s], L.at[d, s], C.at[d, s], ATRp.at[d, s]
            if any(map(lambda x: x is None or (isinstance(x, float) and math.isnan(x)), (o, l, c, atr))):
                continue
            if tick_size(o) / o * 100 > cfg.get("max_tick_pct", 100):
                continue
            entry = round_tick(o * (1 + slip), "up")
            stop = round_tick(min(entry - v["stop_atr"] * atr, entry * (1 - cfg["min_stop_pct"] / 100)), "down")
            if stop <= 0:
                stop = round_tick(entry * 0.5, "down")
            risk_ps = entry - stop + (entry + stop) * slip + tick_size(stop)
            budget = start * risk_pct / 100
            qty = int(max(0, budget - 2 * fee) / risk_ps) if risk_ps > 0 else 0
            qty = min(qty, int(start * max_pos / 100 / entry))
            if qty * entry < cfg["min_trade_value"]:
                continue
            exitp = stop if l <= stop else c
            exitp = round_tick(exitp * (1 - slip), "down")
            net = qty * (exitp - entry) - 2 * fee
            eq += net
            trades.append({"date": d.date().isoformat(), "sym": s, "score": round(float(row[s]), 3), "net": round(net, 2),
                           "r": round((exitp - entry) / (entry - stop), 2) if entry > stop else 0,
                           "gross_pct": round((c if l > stop else stop) / o * 100 - 100, 3),
                           "net_pct_of_equity": round(net / start * 100, 3), "stopped": bool(l <= stop)})
        daily.append((d, start, eq))
    return daily, trades


def summarise(v, daily, trades, start_capital):
    eqs = pd.Series([e for _, _, e in daily], index=[d for d, _, _ in daily])
    if eqs.empty:
        return {"name": v["name"], "trades": 0}
    wk = eqs.resample("W-FRI").last().dropna()
    wret = wk.pct_change().dropna() * 100
    yr = eqs.resample("YE").last()
    yret = (yr / yr.shift(1).fillna(start_capital) - 1) * 100
    peak = eqs.cummax()
    years = (eqs.index[-1] - eqs.index[0]).days / 365.25
    n = len(trades)
    return {
        "name": v["name"], "trades": n,
        "total_return_pct": round((eqs.iloc[-1] / start_capital - 1) * 100, 1),
        "cagr_pct": round(((max(eqs.iloc[-1], 1) / start_capital) ** (1 / years) - 1) * 100, 1) if years > 0 else None,
        "avg_week_pct": round(float(wret.mean()), 3), "best_week_pct": round(float(wret.max()), 2),
        "weeks": int(len(wret)), "weeks_hitting_8pct": int((wret >= 8).sum()),
        "win_rate": round(sum(t["net"] > 0 for t in trades) / n * 100, 1) if n else 0,
        "avg_r": round(float(np.mean([t["r"] for t in trades])), 3) if n else 0,
        "sqn": round(float(np.mean([t["r"] for t in trades]) / (np.std([t["r"] for t in trades]) or 1) * min(n, 100) ** 0.5), 2) if n > 1 else 0,
        "max_drawdown_pct": round(float(((eqs / peak) - 1).min() * 100), 1),
        "yearly_pct": {str(k.year): round(float(x), 1) for k, x in yret.items()},
        "end_equity": round(float(eqs.iloc[-1]), 2),
        "avg_gross_move_pct": round(float(np.mean([t["gross_pct"] for t in trades])), 3) if n else 0,
        "avg_net_pct_of_equity": round(float(np.mean([t["net_pct_of_equity"] for t in trades])), 4) if n else 0,
        "pct_stopped": round(sum(t["stopped"] for t in trades) / n * 100, 1) if n else 0,
        "too_small_to_trade_from": (str(eqs.index[[i for i, x in enumerate(eqs.values) if x < start_capital * 0.42][0]].date())
                                    if (eqs < start_capital * 0.42).any() else None),
    }


def main():
    frames = load()
    O, H, L, C, V = (panel(frames, f) for f in ("Open", "High", "Low", "Close", "Volume"))
    tr = pd.concat({s: pd.concat([H[s] - L[s], (H[s] - C[s].shift()).abs(), (L[s] - C[s].shift()).abs()], axis=1).max(axis=1)
                    for s in C.columns}, axis=1)
    ATR = tr.rolling(14).mean()
    TURN = (C * V).rolling(20).mean()

    # Diagnostic: average open->close move by gap size (does the ASX continue or fade gaps?)
    prevC = C.shift(1)
    gap = (O / prevC - 1) * 100
    oc = (C / O - 1) * 100
    liquid = (TURN.shift(1) >= CFG["min_avg_turnover"]) & (prevC >= CFG["min_price"])
    buckets = [(-99, -4), (-4, -2), (-2, 0), (0, 2), (2, 4), (4, 8), (8, 60)]
    diag = []
    for lo, hi in buckets:
        m = liquid & (gap >= lo) & (gap < hi)
        vals = oc[m].stack().dropna()
        diag.append({"gap": f"{lo}% to {hi}%", "n": int(vals.size), "avg_open_to_close_pct": round(float(vals.mean()), 3),
                     "pct_up": round(float((vals > 0).mean() * 100), 1)})
    print(json.dumps(diag, indent=1))

    idx = frames.get(CFG["market_index"])
    bench = None
    if idx is not None:
        bench = round((idx["Close"].iloc[-1] / idx["Close"].iloc[30] - 1) * 100, 1)

    P = {"O": O, "H": H, "L": L, "C": C, "V": V, "ATR": ATR, "TURN": TURN}
    results = []
    for v in VARIANTS:
        daily, trades = run(v, P)
        r = summarise(v, daily, trades, CFG["start_capital"])
        # Same rules, but every calendar year restarts at $10k: shows each year on its own even if the
        # compounding run shrank the account below the minimum trade size.
        dy, ty = run(v, P, reset_yearly=True)
        r["yearly_reset_pct"] = {}
        for y in sorted({d.year for d, _, _ in dy}):
            ys = [e for d, _, e in dy if d.year == y]
            r["yearly_reset_pct"][str(y)] = round((ys[-1] / CFG["start_capital"] - 1) * 100, 1)
        r["years_profitable"] = sum(x > 0 for x in r["yearly_reset_pct"].values())
        print(json.dumps({k: r.get(k) for k in ("name", "trades", "total_return_pct", "cagr_pct", "avg_week_pct", "weeks_hitting_8pct", "win_rate", "avg_r", "sqn", "max_drawdown_pct", "avg_gross_move_pct", "years_profitable", "too_small_to_trade_from")}))
        results.append(r)
    out = ROOT / "data/backtest"
    out.mkdir(parents=True, exist_ok=True)
    (out / "daily10y.json").write_text(json.dumps({
        "run_at": pd.Timestamp.now(tz="Australia/Sydney").isoformat(timespec="minutes"),
        "period": [str(O.index[30].date()), str(O.index[-1].date())],
        "shares": int(C.shape[1]), "asx200_price_return_pct": bench,
        "gap_diagnostic": diag, "results": results}, indent=1))


if __name__ == "__main__":
    main()
