"""Can the bot profit from price-sensitive news released DURING the trading day?

For each announcement released 10:00–15:00 in the last ~60 days (liquid shares), using real 5-minute bars:
  jump   = price 25 min after the news vs the last price before it (what we miss because Yahoo is ~20 min late)
  drift  = from 25 min after the news to the 3:50pm close (what the bot could actually capture)
Also: drift only when the jump was positive (the bot only buys rising shares). Grouped by news category.
Costs for a $2,500 position: $10 brokerage round trip + 0.2% slippage = ~0.6%.
Writes data/backtest/intraday_news.json.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import data as md  # noqa: E402
import news  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TZ = "Australia/Sydney"
COST = 0.6  # % round trip on a ~$2,500 position


def main():
    events = news.load_events(ROOT / "data/news/events.json")
    cutoff = pd.Timestamp.now(tz=TZ) - pd.Timedelta(days=58)
    ev = []
    for e in events:
        t = pd.Timestamp(e["time"]).tz_convert(TZ)
        if t < cutoff or t.weekday() >= 5:
            continue
        mins = t.hour * 60 + t.minute
        if 600 <= mins <= 900 and (e.get("turnover") or 0) >= 500_000 and (e.get("prev_close") or 0) >= 0.2:
            ev.append((e, t))
    syms = sorted({e["sym"] for e, _ in ev})
    print(f"{len(ev)} intraday announcements in {len(syms)} liquid shares")
    bars = {}
    for i in range(0, len(syms), 100):
        got = md._download([f"{s}.AX" for s in syms[i:i + 100]], period="60d", interval="5m")
        bars.update({t[:-3]: md.to_sydney(df) for t, df in got.items()})
    agg = defaultdict(lambda: {"n": 0, "jump": [], "drift": [], "drift_after_up": []})
    for e, t in ev:
        df = bars.get(e["sym"])
        if df is None:
            continue
        day = df[df.index.date == t.date()]
        before = day[day.index < t]
        after = day[day.index >= t + pd.Timedelta(minutes=25)]
        close = day[day.index.time <= pd.Timestamp("15:50").time()]
        if before.empty or after.empty or close.empty:
            continue
        p0, p1, pc = float(before["Close"].iloc[-1]), float(after["Open"].iloc[0]), float(close["Close"].iloc[-1])
        if min(p0, p1, pc) <= 0 or after.index[0] >= close.index[-1]:
            continue
        jump, drift = (p1 / p0 - 1) * 100, (pc / p1 - 1) * 100
        for cat in (e["category"], "ALL"):
            a = agg[cat]
            a["n"] += 1
            a["jump"].append(jump)
            a["drift"].append(drift)
            if jump > 1:
                a["drift_after_up"].append(drift)
    rows = []
    for cat, a in agg.items():
        up = a["drift_after_up"]
        rows.append({"category": cat, "n": a["n"],
                     "avg_jump_first_25min_pct": round(sum(a["jump"]) / a["n"], 2),
                     "avg_drift_to_close_pct": round(sum(a["drift"]) / a["n"], 2),
                     "n_jumped_up_1pct": len(up),
                     "drift_after_jump_up_pct": round(sum(up) / len(up), 2) if up else None,
                     "net_after_costs_if_bought_pct": round(sum(up) / len(up) - COST, 2) if up else None,
                     "pct_up_after_jump": round(sum(x > 0 for x in up) / len(up) * 100, 1) if up else None})
    rows.sort(key=lambda r: -r["n"])
    for r in rows:
        print(json.dumps(r))
    out = ROOT / "data/backtest"
    out.mkdir(parents=True, exist_ok=True)
    (out / "intraday_news.json").write_text(json.dumps({"run_at": pd.Timestamp.now(tz=TZ).isoformat(timespec="minutes"),
                                                         "cost_assumed_pct": COST, "categories": rows}, indent=1))


if __name__ == "__main__":
    main()
