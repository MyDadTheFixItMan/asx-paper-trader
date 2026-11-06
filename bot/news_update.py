"""Fetch new ASX announcements, measure price reactions, rebuild news stats.

Daily (called by trader.py after the close):   python bot/news_update.py
Backfill (run once from the Research workflow): NEWS_LOOKBACK_DAYS=90 python bot/news_update.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import data as md  # noqa: E402
import news  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NEWS = ROOT / "data" / "news"
CFG = json.loads((ROOT / "bot/config.json").read_text())


def update(lookback_days: int | None = None):
    events_path = NEWS / "events.json"
    events = news.load_events(events_path)
    known = {e["key"] for e in events}
    now = pd.Timestamp.now(tz=news.TZ)
    if lookback_days is None:
        lookback_days = 4 if events else 30
    since = now - pd.Timedelta(days=lookback_days)
    fresh = [e for e in news.fetch(since) if e["key"] not in known]
    events.extend(fresh)
    print(f"{len(fresh)} new price-sensitive announcements ({len(events)} stored)")

    # Price reactions for events not yet measured
    todo = sorted({e["sym"] for e in events if e.get("move") is None and e.get("sym")})
    oldest = min((pd.Timestamp(e["time"]) for e in events if e.get("move") is None), default=now)
    days = (now - oldest).days + 10
    period = "1mo" if days <= 25 else "3mo" if days <= 85 else "6mo" if days <= 175 else "1y"
    daily = {}
    if todo:
        raw = md._download([f"{s}.AX" for s in todo], period=period, interval="1d")
        for t, df in raw.items():
            df = df.copy()
            df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
            daily[t[:-3]] = df
    # Trading days from the market itself (an ETF that trades every session)
    cal = md._download(["STW.AX"], period=period, interval="1d").get("STW.AX")
    trading_days = sorted({d for d in pd.to_datetime(cal.index).date}) if cal is not None else []
    # allow today/tomorrow as news days even before their bars exist
    nxt = pd.Timestamp(now.date())
    extra = [d.date() for d in pd.bdate_range(nxt, nxt + pd.Timedelta(days=5))]
    news.assign_days(events, sorted(set(trading_days) | set(extra)))
    news.measure(events, daily)
    news.save_events(events_path, events)

    st = news.stats(events)
    rl = news.rules(st, CFG)
    measured = sum(e.get("move") is not None for e in events)
    (NEWS / "stats.json").write_text(json.dumps({
        "updated": now.isoformat(timespec="minutes"), "events": len(events), "measured": measured,
        "first_day": min((e["day"] for e in events if e.get("day")), default=None),
        "rules": rl, "categories": st}, indent=1))
    print(json.dumps(st[:15], indent=1))
    print("rules:", rl)


if __name__ == "__main__":
    lb = os.environ.get("NEWS_LOOKBACK_DAYS")
    update(int(lb) if lb else None)
