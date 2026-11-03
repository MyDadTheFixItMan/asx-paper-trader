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

VARIANTS = [
    {"name": "top 5 gaps ≥2%, stop 0.5 ATR", "min_gap": 2, "max_gap": 99, "stop_atr": 0.5, "top": 5},
    {"name": "top 5 gaps ≥2%, stop 1 ATR", "min_gap": 2, "max_gap": 99, "stop_atr": 1.0, "top": 5},
    {"name": "top 5 gaps ≥4%, stop 1 ATR", "min_gap": 4, "max_gap": 99, "stop_atr": 1.0, "top": 5},
    {"name": "top 3 gaps ≥8% (episodic pivot), stop 1 ATR", "min_gap": 8, "max_gap": 99, "stop_atr": 1.0, "top": 3},
    {"name": "small gaps 1–4%, stop 1 ATR", "min_gap": 1, "max_gap": 4, "stop_atr": 1.0, "top": 5},
    {"name": "top 5 gaps ≥4%, no stop (open to close)", "min_gap": 4, "max_gap": 99, "stop_atr": 99, "top": 5},
]


def load():
    codes = md.asx_codes(ROOT / "data/asx_codes.txt")
    raw = md._download([f"{c}.AX" for c in codes] + [CFG["market_index"]], period="10y", interval="1d")
    frames = {}
    for t, df in raw.items():
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        if len(df) > 60:
            frames[t[:-3] if t.endswith(".AX") else t] = df
    return frames


def panel(frames, field):
    return pd.DataFrame({s: f[field] for s, f in frames.items() if s != CFG["market_index"]})


def run(v, O, H, L, C, V, ATR, TURN):
    cfg = CFG
    eq = cfg["start_capital"]
    fee = cfg["brokerage_per_trade"]
    slip = cfg["slippage_pct"] / 100
    prevC = C.shift(1)
    gap = (O / prevC - 1) * 100
    ok = (prevC >= cfg["min_price"]) & (TURN.shift(1) >= cfg["min_avg_turnover"]) & \
         (ATR.shift(1) / prevC * 100 >= cfg["min_atr_pct"]) & (gap >= v["min_gap"]) & (gap < v["max_gap"])
    daily, trades = [], []
    for d in O.index[30:]:
        row = gap.loc[d][ok.loc[d].fillna(False)].dropna()
        # skip absurd gaps (data errors, reconstructions)
        row = row[row < 60].sort_values(ascending=False).head(v["top"])
        start = eq
        for s in row.index:
            o, h, l, c, atr = O.at[d, s], H.at[d, s], L.at[d, s], C.at[d, s], ATR.shift(1).at[d, s]
            if any(map(lambda x: x is None or (isinstance(x, float) and math.isnan(x)), (o, l, c, atr))):
                continue
            if tick_size(o) / o * 100 > cfg.get("max_tick_pct", 100):
                continue
            entry = round_tick(o * (1 + slip), "up")
            stop = round_tick(min(entry - v["stop_atr"] * atr, entry * (1 - cfg["min_stop_pct"] / 100)), "down")
            if stop <= 0:
                stop = round_tick(entry * 0.5, "down")
            risk_ps = entry - stop + (entry + stop) * slip + tick_size(stop)
            budget = start * cfg["risk_per_trade_pct"] / 100
            qty = int(max(0, budget - 2 * fee) / risk_ps) if risk_ps > 0 else 0
            qty = min(qty, int(start * cfg["max_position_pct"] / 100 / entry))
            if qty * entry < cfg["min_trade_value"]:
                continue
            exitp = stop if l <= stop else c
            exitp = round_tick(exitp * (1 - slip), "down")
            net = qty * (exitp - entry) - 2 * fee
            eq += net
            trades.append({"date": d.date().isoformat(), "sym": s, "gap": round(row[s], 2), "net": round(net, 2),
                           "r": round((exitp - entry) / (entry - stop), 2) if entry > stop else 0,
                           "stopped": bool(l <= stop)})
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
        "max_drawdown_pct": round(float(((eqs / peak) - 1).min() * 100), 1),
        "yearly_pct": {str(k.year): round(float(x), 1) for k, x in yret.items()},
        "end_equity": round(float(eqs.iloc[-1]), 2),
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
        vals = oc[m].stack()
        diag.append({"gap": f"{lo}% to {hi}%", "n": int(vals.size), "avg_open_to_close_pct": round(float(vals.mean()), 3),
                     "pct_up": round(float((vals > 0).mean() * 100), 1)})
    print(json.dumps(diag, indent=1))

    idx = frames.get(CFG["market_index"])
    bench = None
    if idx is not None:
        bench = round((idx["Close"].iloc[-1] / idx["Close"].iloc[30] - 1) * 100, 1)

    results = []
    for v in VARIANTS:
        daily, trades = run(v, O, H, L, C, V, ATR, TURN)
        r = summarise(v, daily, trades, CFG["start_capital"])
        print(json.dumps({k: r.get(k) for k in ("name", "trades", "total_return_pct", "cagr_pct", "avg_week_pct", "weeks_hitting_8pct", "win_rate", "avg_r", "max_drawdown_pct")}))
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
