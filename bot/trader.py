"""Runs every 5 minutes from GitHub Actions. Usage: python bot/trader.py

Env vars (testing only): TRADER_NOW=2026-11-04T11:00 to fake the clock.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from engine import TZ, Engine, hhmm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CFG = json.loads((ROOT / "bot" / "config.json").read_text())


def load(name, default):
    p = DATA / name
    return json.loads(p.read_text()) if p.exists() else default


def save(name, obj):
    DATA.mkdir(exist_ok=True)
    (DATA / name).write_text(json.dumps(obj, indent=1, default=str))


def is_trading_day(d) -> bool:
    if d.weekday() >= 5:
        return False
    try:
        import holidays
        try:
            cal = holidays.financial_holidays("XASX", years=d.year)
        except Exception:  # noqa: BLE001
            cal = holidays.Australia(subdiv="NSW", years=d.year)
        return d not in cal
    except ImportError:
        return True


def load_news(state, now, symbols, refresh=False):
    """Attach overnight price-sensitive ASX news (since yesterday 10:00) and the learned news rules to today."""
    if not CFG.get("news_enabled", True):
        return
    try:
        import news
        prev = (now - pd.offsets.BDay(1)).normalize().replace(hour=10)
        fresh = news.fetch(prev if not refresh else now - pd.Timedelta(hours=3), max_pages=40)
        stored = news.load_events(DATA / "news" / "events.json")
        known = {e["key"] for e in stored}
        all_ev = stored + [e for e in fresh if e["key"] not in known]
        m = news.morning_map(all_ev, prev, symbols)
        day = state["day"]
        day.setdefault("news", {}).update(m)
        st = DATA / "news" / "stats.json"
        if st.exists():
            day["news_rules"] = json.loads(st.read_text()).get("rules", {})
        if not refresh:
            Engine(state, [], CFG).log(now, f"Read {len(fresh)} price-sensitive ASX announcements; {len(m)} are for shares the bot can trade.")
    except Exception as e:  # noqa: BLE001
        print(f"News fetch failed: {e}")


def check_news_hourly(state, eng, now, symbols):
    """Every hour during the session: read new price-sensitive ASX announcements, flag news on held shares."""
    if not CFG.get("news_enabled", True):
        return
    day = state["day"]
    last = day.get("news_checked_at")
    every = CFG.get("news_check_minutes", 60)
    if last and (now - pd.Timestamp(last)).total_seconds() < every * 60:
        return
    try:
        import news
        since = pd.Timestamp(last) if last else now.normalize().replace(hour=10)
        fresh = news.fetch(since, max_pages=20)
        day["news_checked_at"] = now.isoformat()
        feed = day.setdefault("news_today", [])
        known = {x["key"] for x in feed}
        held = {p["sym"] for p in state["positions"]}
        added = 0
        for e in sorted(fresh, key=lambda e: e["time"]):
            if e["key"] in known or (e["sym"] not in symbols and e["sym"] not in held):
                continue
            feed.append({k: e[k] for k in ("key", "sym", "time", "category", "headline")})
            added += 1
            if e["sym"] in held:
                eng.log(now, f"NEWS on held share {e['sym']}: {e['category']}: {e['headline'][:100]}")
                if e["category"] in CFG.get("news_exit_categories", []):
                    pos = next(p for p in state["positions"] if p["sym"] == e["sym"])
                    eng._exit(pos, pos["last"], now, f"Sold on news: {e['category']}")
        del feed[:-60]
        eng.log(now, f"Hourly news check: {len(fresh)} new price-sensitive announcements, {added} for shares the bot trades.")
    except Exception as ex:  # noqa: BLE001
        print(f"Hourly news check failed: {ex}")


def main():
    now = pd.Timestamp(os.environ["TRADER_NOW"], tz=TZ) if os.environ.get("TRADER_NOW") else pd.Timestamp.now(tz=TZ)
    today = now.date().isoformat()

    state = load("state.json", None) or {
        "start_capital": CFG["start_capital"], "cash": CFG["start_capital"],
        "created": now.isoformat(), "positions": [], "daily": [], "day": {"date": None, "phase": "closed"},
    }
    trades = load("trades.json", [])
    curve = load("equity.json", [])
    eng = Engine(state, trades, CFG)

    def finish(status: str):
        state["status"] = status
        state["last_run"] = now.isoformat()
        save("state.json", state)
        save("trades.json", trades)
        save("equity.json", curve)
        print(status)

    if not is_trading_day(now.date()):
        if state.get("status") != "Market closed today":
            finish("Market closed today")
        return

    if now.time() < hhmm("09:15"):
        print("Too early")
        return

    # ---- new day: morning scan of every ASX listing ----
    if state["day"].get("date") != today:
        if state["positions"]:  # should never happen; never hold overnight
            eng.close_day(now)
        import data as md
        uni = load("universe.json", {})
        if uni.get("date") != today:
            codes = md.asx_codes(DATA / "asx_codes.txt")
            uni = md.build_universe(codes, CFG, now.to_pydatetime())
            save("universe.json", uni)
        eng.new_day(today, uni["symbols"])
        load_news(state, now, set(uni["symbols"]))
        eng.log(now, f"Scanned {uni.get('scanned')} ASX listings; {len(uni['symbols']) - 1} pass the liquidity and volatility filters.")
        finish("Morning scan done. Waiting for the 10:00 open.")
        return

    day = state["day"]
    if day["phase"] == "closed":
        print("Day already closed")
        return

    if now.time() < hhmm("10:00"):
        print("Waiting for open")
        return

    import data as md
    uni = load("universe.json", {})
    symbols = uni.get("symbols", {})
    delay = CFG["data_delay_minutes"]

    if day["phase"] == "waiting_open":
        tickers = [f"{s}.AX" for s in symbols if s != "__index__"]
        bars = md.intraday_bars(tickers + [CFG["market_index"]], now, delay)
        index_bars = bars.pop(CFG["market_index"], None)
        if not bars and now.time() > hhmm("11:00"):
            eng.close_day(now)
            finish("No ASX price data today (market holiday?).")
            return
        if not state["day"].get("news_refreshed"):
            load_news(state, now, set(symbols), refresh=True)
            state["day"]["news_refreshed"] = True
        if not eng.select_watchlist(bars, index_bars, symbols):
            finish("Building the opening range (prices are ~20 min delayed)")
            return
        wanted = {w["sym"] for w in day["watchlist"]}
        bars = {s: b for s, b in bars.items() if s in wanted}
    else:
        wanted = {w["sym"] for w in day["watchlist"]} | {p["sym"] for p in state["positions"]}
        bars = md.intraday_bars([f"{s}.AX" for s in wanted], now, delay)

    eng.process(bars)
    check_news_hourly(state, eng, now, set(symbols))

    # Late-day safety net: flatten if the exit bar never arrived (halt, data gap)
    if day["phase"] == "trading" and now.time() >= hhmm("16:45"):
        last = {s: b[-1]["c"] for s, b in bars.items() if b}
        eng.close_day(now, last)

    # End-of-day review: learn from today's losses, then from today's ASX news
    if day["phase"] == "closed" and not day.get("reviewed"):
        import learn
        learn.review_day(state, trades, CFG)
        eng.log(now, "Daily review done. See 'Learning from losses' on the dashboard.")
        try:
            import news_update
            news_update.update()
            eng.log(now, "News review done: today's announcements and price reactions recorded.")
        except Exception as e:  # noqa: BLE001
            print(f"News update failed: {e}")

    # mark to market + equity curve
    for p in state["positions"]:
        if bars.get(p["sym"]):
            p["last"] = bars[p["sym"]][-1]["c"]
    eq = eng.equity()
    curve.append({"t": now.isoformat(timespec="minutes"), "equity": eq})
    cutoff = (now - pd.Timedelta(days=14)).isoformat()
    curve[:] = [c for c in curve if c["t"] >= cutoff]

    if day["phase"] == "closed":
        status = f"Day finished. Equity ${eq:,.2f}"
    elif day.get("no_new_entries") and not state["positions"]:
        mc = day.get("market_change_pct")
        status = (f"Standing aside today: ASX 200 opened {mc:+.2f}%" if mc is not None and mc < CFG["market_min_change_pct"]
                  else "Done for today: daily loss limit reached")
    elif day.get("no_new_entries"):
        status = "Managing open trades only (no new entries today)"
    elif now.time() >= hhmm(CFG["last_entry_time"]):
        status = "Past the entry cut-off. Managing open trades until the close."
    else:
        status = f"Watching {len(day['watchlist'])} stocks in play for breakouts"
    finish(status)


if __name__ == "__main__":
    main()
