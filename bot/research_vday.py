"""Does the ASX recover after a weak open? ("right side of the V")

1) 10 years of daily data: on days the ASX 200 opens down, what does an ASX 200 ETF (STW) do from open to close?
2) ~2 years of hourly data: on those days, does waiting for the market to turn back up (hourly close above the
   day's open, or above VWAP) and then buying do better than buying at the open?
Costs: $5 brokerage each way + 0.05% slippage each way (ETF spreads are tight). Writes data/backtest/vday.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import data as md  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TZ = "Australia/Sydney"
ETF, IDX = "STW.AX", "^AXJO"
FEE, SLIP, CAP = 5.0, 0.0005, 10000.0


def net_ret(entry, exit_):
    gross = (exit_ * (1 - SLIP)) / (entry * (1 + SLIP)) - 1
    return gross - 2 * FEE / CAP


def summarise(name, rets):
    s = pd.Series(rets, dtype=float)
    if s.empty:
        return {"name": name, "days": 0}
    eq = (1 + s).cumprod()
    return {"name": name, "days": int(s.size), "avg_net_pct": round(s.mean() * 100, 3),
            "pct_days_up": round((s > 0).mean() * 100, 1),
            "compounded_pct": round((eq.iloc[-1] - 1) * 100, 1),
            "max_drawdown_pct": round(((eq / eq.cummax()) - 1).min() * 100, 1)}


def main():
    d = md._download([ETF, IDX], period="10y", interval="1d")
    etf, idx = d[ETF], d[IDX]
    for df in (etf, idx):
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    j = etf.join(idx, lsuffix="_e", rsuffix="_i", how="inner").dropna()
    # Yahoo's ^AXJO "open" is usually just the prior close, so use the ETF's real opening trade instead
    j["gap_i"] = (j["Open_e"] / j["Close_e"].shift() - 1) * 100
    j = j.dropna()
    daily = []
    for lo, hi, label in [(-99, -1.5, "index opens down >1.5%"), (-1.5, -1.0, "down 1–1.5%"), (-1.0, -0.5, "down 0.5–1%"),
                          (-0.5, 0.5, "flat ±0.5%"), (0.5, 99, "up >0.5%")]:
        m = j[(j["gap_i"] >= lo) & (j["gap_i"] < hi)]
        r = [net_ret(o, c) for o, c in zip(m["Open_e"], m["Close_e"])]
        out = summarise(f"Buy STW at open, sell at close: {label}", r)
        out["avg_gross_open_to_close_pct"] = round(((m["Close_e"] / m["Open_e"]) - 1).mean() * 100, 3) if len(m) else None
        daily.append(out)
        print(json.dumps(out))

    # Hourly: wait for the turn
    h = md._download([ETF, IDX], period="730d", interval="60m")
    he, hi_ = md.to_sydney(h[ETF]), md.to_sydney(h[IDX])
    prev_close = j["Close_e"]
    hourly = {"open": [], "above_open": [], "above_vwap": []}
    for day, g in hi_.groupby(hi_.index.date):
        ts = pd.Timestamp(day)
        if ts not in prev_close.index:
            continue
        pc = prev_close.shift().get(ts)
        if pd.isna(pc) or g.empty:
            continue
        ge = he[he.index.date == day]
        if ge.empty:
            continue
        gap = (float(ge["Open"].iloc[0]) / pc - 1) * 100
        if gap > -1.0:
            continue
        if len(ge) < 3:
            continue
        exit_ = float(ge["Close"].iloc[-1])
        hourly["open"].append(net_ret(float(ge["Open"].iloc[0]), exit_))
        day_open = float(ge["Open"].iloc[0])
        tp = (ge["High"] + ge["Low"] + ge["Close"]) / 3
        vol = ge["Volume"].astype(float).clip(lower=1)
        vwap = (tp * vol).cumsum() / vol.cumsum()
        for key, cond in (("above_open", ge["Close"] > day_open), ("above_vwap", ge["Close"] > vwap)):
            hits = [t for t, ok in cond.items() if bool(ok) and t.hour < 15]
            if hits:
                t0 = hits[0]
                if t0 in ge.index:
                    hourly[key].append(net_ret(float(ge.loc[t0, "Close"]), exit_))
    hourly_out = [summarise("Index opened down >1%: buy STW at open", hourly["open"]),
                  summarise("…wait until STW closes an hour back above its open (before 3pm)", hourly["above_open"]),
                  summarise("…wait until STW closes an hour above its VWAP (before 3pm)", hourly["above_vwap"])]
    for x in hourly_out:
        print(json.dumps(x))
    out = ROOT / "data/backtest"
    out.mkdir(parents=True, exist_ok=True)
    (out / "vday.json").write_text(json.dumps({"run_at": pd.Timestamp.now(tz=TZ).isoformat(timespec="minutes"),
                                               "daily_10y": daily, "hourly_2y": hourly_out}, indent=1))


if __name__ == "__main__":
    main()
