"""ASX company announcements: fetch, classify, measure how the price reacted, and learn which news helps or hurts.

Source: the ASX's own announcements feed (the one behind asx.com.au). Price-sensitive announcements only.

How an announcement is linked to a trading day: news released after 10:00 on day D-1 and up to 10:00 on day D is
"overnight news for day D" (that's what the bot can see at the open). Its reaction is measured on day D:
  gap   = open / previous close - 1    (what the market priced in at the open)
  move  = close / open - 1             (what happened after the open: what a day trader can capture)
"""
from __future__ import annotations

import json
import re
import time as _time
from collections import defaultdict
from pathlib import Path

import pandas as pd
import requests

TZ = "Australia/Sydney"
FEED = ("https://asx.api.markitdigital.com/asx-research/1.0/markets/announcements"
        "?page={page}&itemsPerPage=100&priceSensitiveOnly=true&access_token=83ff96335c2d45a094df02a206a39ff4")
HEADERS = {"User-Agent": "Mozilla/5.0 (asx-paper-trader)", "Accept": "application/json"}

# Plain-English categories from the headline and the ASX's announcement type (first match wins)
CATEGORIES = [
    ("Trading halt", r"trading halt|suspension|pause in trading"),
    ("Capital raising", r"placement|capital rais|entitlement|share purchase plan|\bspp\b|rights issue|institutional offer|bookbuild|convertible note"),
    ("Takeover / merger", r"takeover|scheme of arrangement|\bscheme\b|merger|non-binding|indicative offer|bidder|target's statement|binding offer"),
    ("Guidance downgrade", r"downgrade|lower guidance|guidance revision|impairment|write-?down|profit warning|below guidance"),
    ("Guidance upgrade", r"upgrade|raises guidance|increases guidance|above guidance|record (profit|revenue|result|quarter|sales)"),
    ("Contract / deal", r"contract|agreement|offtake|partnership|award|order|supply deal|binding term sheet|mou\b|licen[cs]e"),
    ("Acquisition / sale", r"acqui|divest|sale of|disposal|purchase of"),
    ("Exploration / drilling", r"drill|assay|intercept|high[- ]grade|discovery|mineral resource|ore reserve|resource (update|estimate)|exploration|metres? @|g/t|\bjorc\b"),
    ("Regulatory / clinical", r"\bfda\b|\btga\b|clinical|\btrials?\b|approval|patent|phase (i|ii|iii|1|2|3)"),
    ("Quarterly report", r"quarterly|4c|appendix 5b|activities report|cash ?flow report"),
    ("Results", r"half[- ]year|full[- ]year|annual report|results|appendix 4[de]|financial report|earnings"),
    ("Dividend / buy-back", r"dividend|distribution|buy-?back"),
    ("Management change", r"ceo|managing director|chair|director appointment|resign|cfo"),
]


def classify(headline: str, types: list[str] | None = None) -> str:
    text = f"{headline} {' '.join(types or [])}".lower()
    for label, pattern in CATEGORIES:
        if re.search(pattern, text):
            return label
    return "Other"


def fetch(since: pd.Timestamp, max_pages: int = 400, pause: float = 0.25) -> list[dict]:
    """Price-sensitive announcements newer than `since` (tz-aware), newest first."""
    out, seen = [], set()
    for page in range(max_pages):
        items = None
        for attempt in range(3):
            try:
                r = requests.get(FEED.format(page=page), headers=HEADERS, timeout=30)
                r.raise_for_status()
                items = (r.json().get("data") or {}).get("items") or []
                break
            except Exception as e:  # noqa: BLE001
                print(f"ASX news page {page} failed ({e}), retrying")
                _time.sleep(3 * (attempt + 1))
        if not items:
            break
        oldest = None
        for it in items:
            key = it.get("documentKey")
            if not key or key in seen:
                continue
            seen.add(key)
            t = pd.Timestamp(it["date"]).tz_convert(TZ)
            oldest = t if oldest is None or t < oldest else oldest
            if t <= since:
                continue
            types = it.get("announcementTypes") or []
            out.append({
                "key": key, "sym": it.get("symbol"), "time": t.isoformat(),
                "headline": (it.get("headline") or "").strip(), "type": types[0] if types else "",
                "category": classify(it.get("headline") or "", types),
            })
        if oldest is not None and oldest <= since:
            break
        _time.sleep(pause)
    return out


def news_day(release: pd.Timestamp, trading_days: list) -> str | None:
    """First trading day whose 10:00 open window comes after the release."""
    for d in trading_days:
        if pd.Timestamp(f"{d} 10:00", tz=TZ) > release:
            return str(d)
    return None


def overnight_news(events: list[dict], date_str: str) -> dict:
    """{sym: [events]} of news assigned to `date_str` (released between yesterday 10:00 and today 10:00)."""
    out = defaultdict(list)
    for e in events:
        if e.get("day") == date_str:
            out[e["sym"]].append(e)
    return dict(out)


def assign_days(events: list[dict], trading_days: list):
    for e in events:
        if not e.get("day"):
            e["day"] = news_day(pd.Timestamp(e["time"]), trading_days)


def measure(events: list[dict], daily: dict[str, pd.DataFrame]):
    """Fill in gap / move for events whose news day has completed (daily bars available)."""
    for e in events:
        if e.get("move") is not None or not e.get("day"):
            continue
        df = daily.get(e["sym"])
        if df is None:
            continue
        dates = [str(x) for x in df.index.date]
        if e["day"] not in dates:
            continue
        i = dates.index(e["day"])
        if i == 0:
            continue
        o, c, prev = float(df["Open"].iloc[i]), float(df["Close"].iloc[i]), float(df["Close"].iloc[i - 1])
        vol = float(df["Volume"].iloc[i] or 0)
        if min(o, c, prev) <= 0 or vol <= 0:
            continue
        turnover = float((df["Close"] * df["Volume"]).iloc[max(0, i - 20):i].mean())
        e.update({"gap": round((o / prev - 1) * 100, 3), "move": round((c / o - 1) * 100, 3),
                  "prev_close": round(prev, 4), "turnover": round(turnover)})


def stats(events: list[dict], before: str | None = None, min_price=0.2, min_turnover=500_000) -> list[dict]:
    """Average reaction by category, for liquid shares, using only news days before `before` (walk-forward)."""
    agg = defaultdict(lambda: {"n": 0, "gap": 0.0, "move": 0.0, "up": 0, "gap_up_move": [], })
    for e in events:
        if e.get("move") is None or (before and e["day"] >= before):
            continue
        if e.get("prev_close", 0) < min_price or e.get("turnover", 0) < min_turnover:
            continue
        a = agg[e["category"]]
        a["n"] += 1
        a["gap"] += e["gap"]
        a["move"] += e["move"]
        a["up"] += e["move"] > 0
        if e["gap"] > 0:
            a["gap_up_move"].append(e["move"])
    out = []
    for cat, a in agg.items():
        out.append({"category": cat, "n": a["n"], "avg_gap_pct": round(a["gap"] / a["n"], 2),
                    "avg_move_after_open_pct": round(a["move"] / a["n"], 2),
                    "pct_up_after_open": round(a["up"] / a["n"] * 100, 1),
                    "gap_up_then_move_pct": round(sum(a["gap_up_move"]) / len(a["gap_up_move"]), 2) if a["gap_up_move"] else None})
    return sorted(out, key=lambda x: -x["n"])


def rules(stat_rows: list[dict], cfg: dict) -> dict:
    """Learned rules: avoid categories that fall after the open, favour ones that rise (only with enough history)."""
    block, boost = [], []
    for s in stat_rows:
        if s["n"] < cfg.get("news_min_events", 30) or s["category"] == "Other":
            continue
        if s["avg_move_after_open_pct"] <= cfg.get("news_block_move_pct", -0.3):
            block.append(s["category"])
        elif s["avg_move_after_open_pct"] >= cfg.get("news_boost_move_pct", 0.3):
            boost.append(s["category"])
    return {"block": block, "boost": boost}


def load_events(path: Path) -> list[dict]:
    return json.loads(path.read_text()) if path.exists() else []


def save_events(path: Path, events: list[dict], keep_days: int = 400):
    cutoff = (pd.Timestamp.now(tz=TZ) - pd.Timedelta(days=keep_days)).isoformat()
    events = [e for e in events if e["time"] >= cutoff]
    events.sort(key=lambda e: e["time"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(events, separators=(",", ":")))
