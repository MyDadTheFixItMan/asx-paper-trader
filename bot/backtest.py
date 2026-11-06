"""Replay the strategy over the last ~60 trading days of real Yahoo 5-minute data.

Runs on GitHub Actions (workflow "Backtest"). Tests every variant in bot/backtest_variants.json
against the current config and writes data/backtest/results.json.

Caveats: uses today's universe (some survivorship bias) and Yahoo's 60-day limit on 5-minute data.
"""
from __future__ import annotations

import copy
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import data as md  # noqa: E402
import learn  # noqa: E402
import news  # noqa: E402
from engine import TZ, Engine  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "bot/config.json").read_text())


def load_market(cfg):
    uni = json.loads((ROOT / "data/universe.json").read_text())["symbols"]
    syms = [s for s in uni if s != "__index__"]
    tickers = [f"{s}.AX" for s in syms]
    intraday = {t[:-3] if t.endswith(".AX") else t: md.to_sydney(df)
                for t, df in md._download(tickers + [cfg["market_index"]], period="60d", interval="5m").items()}
    daily = {t[:-3] if t.endswith(".AX") else t: md.to_sydney(df)
             for t, df in md._download(tickers + [cfg["market_index"]], period="6mo", interval="1d").items()}
    return syms, intraday, daily


def bars_for(df, d):
    sub = df[df.index.date == d]
    return [{"t": ts, "o": float(r.Open), "h": float(r.High), "l": float(r.Low), "c": float(r.Close),
             "v": float(r.Volume or 0)} for ts, r in sub.iterrows()]


def meta_for(sym, d, intraday, daily, cfg):
    dd = daily.get(sym)
    if dd is None:
        return None
    hist = dd[dd.index.date < d].tail(30)
    if len(hist) < 15:
        return None
    hl = hist["High"] - hist["Low"]
    hc = (hist["High"] - hist["Close"].shift()).abs()
    lc = (hist["Low"] - hist["Close"].shift()).abs()
    atr = float(pd.concat([hl, hc, lc], axis=1).max(axis=1).tail(14).mean())
    prev = float(hist["Close"].iloc[-1])
    turnover = float((hist["Close"] * hist["Volume"]).tail(20).mean())
    if prev < cfg["min_price"] or turnover < cfg["min_avg_turnover"] or atr / prev * 100 < cfg["min_atr_pct"]:
        return None
    df = intraday.get(sym)
    if df is None:
        return None
    pre = df[df.index.date < d]
    mins = pre.index.hour * 60 + pre.index.minute
    first = pre[(mins >= 600) & (mins < 600 + cfg["opening_range_minutes"])]
    per = first.groupby(first.index.date)["Volume"].sum()
    per = per[per > 0].tail(14)
    if len(per) < 5:
        return None
    return {"prev_close": prev, "atr": atr, "avg_or_volume": float(per.mean())}


EVENTS = news.load_events(ROOT / "data/news/events.json")


def run(cfg, syms, intraday, daily, days):
    state = {"start_capital": cfg["start_capital"], "cash": cfg["start_capital"], "positions": [], "daily": [],
             "day": {"date": None, "phase": "closed"}}
    trades: list = []
    eng = Engine(state, trades, cfg)
    idx = cfg["market_index"]
    for d in days:
        uni = {}
        for s in syms:
            m = meta_for(s, d, intraday, daily, cfg)
            if m:
                uni[s] = m
        idd = daily.get(idx)
        prev_idx = None
        if idd is not None:
            h = idd[idd.index.date < d]
            prev_idx = float(h["Close"].iloc[-1]) if len(h) else None
        uni["__index__"] = {"prev_close": prev_idx}
        eng.new_day(d.isoformat(), uni)
        # News known at that morning, and rules learned only from earlier days (walk-forward, no hindsight)
        ov = news.overnight_news(EVENTS, d.isoformat())
        state["day"]["news"] = {sym: {"category": evs[-1]["category"], "headline": evs[-1]["headline"][:140]}
                                for sym, evs in ov.items()}
        state["day"]["news_rules"] = news.rules(news.stats(EVENTS, before=d.isoformat()), cfg)
        bars = {s: bars_for(intraday[s], d) for s in uni if s != "__index__" and s in intraday}
        bars = {s: b for s, b in bars.items() if b}
        index_bars = bars_for(intraday[idx], d) if idx in intraday else None
        if not eng.select_watchlist(bars, index_bars, uni):
            eng.close_day(pd.Timestamp(f"{d} 16:00", tz=TZ))
            continue
        wanted = {w["sym"] for w in state["day"]["watchlist"]}
        eng.process({s: b for s, b in bars.items() if s in wanted})
        if state["day"]["phase"] != "closed":
            last = {s: b[-1]["c"] for s, b in bars.items() if b}
            eng.close_day(pd.Timestamp(f"{d} 16:00", tz=TZ), last)
        learn.review_day(state, trades, cfg)
    return state, trades


def summarise(name, cfg, state, trades):
    daily = state["daily"]
    eq = [cfg["start_capital"]] + [x["end_equity"] for x in daily]
    peak, mdd = eq[0], 0.0
    for v in eq:
        peak = max(peak, v)
        mdd = min(mdd, (v / peak - 1) * 100)
    weeks = {}
    for x in daily:
        wk = datetime.fromisoformat(x["date"]).strftime("%G-W%V")
        weeks.setdefault(wk, [x["start_equity"], x["end_equity"]])[1] = x["end_equity"]
    wret = [round((e / s - 1) * 100, 2) for s, e in weeks.values()]
    n = len(trades)
    return {
        "name": name,
        "days": len(daily),
        "trades": n,
        "total_return_pct": round((eq[-1] / eq[0] - 1) * 100, 2),
        "avg_week_pct": round(sum(wret) / len(wret), 2) if wret else 0,
        "weeks_hitting_8pct": sum(w >= 8 for w in wret),
        "weekly_returns": wret,
        "win_rate": round(sum(t["net"] > 0 for t in trades) / n * 100, 1) if n else 0,
        "avg_r": round(sum(t["r"] for t in trades) / n, 3) if n else 0,
        "max_drawdown_pct": round(mdd, 2),
        "fees": round(sum(t["fees"] for t in trades), 2),
    }


def main():
    variants = json.loads((ROOT / "bot/backtest_variants.json").read_text())
    syms, intraday, daily = load_market(CFG)
    idx = intraday.get(CFG["market_index"])
    all_days = sorted({d for d in idx.index.date}) if idx is not None else []
    today = pd.Timestamp.now(tz=TZ).date()
    days = [d for d in all_days if d < today][15:]  # first 15 days only warm up the volume averages
    results = []
    for v in [{"name": "current", "overrides": {}}] + variants:
        cfg = copy.deepcopy(CFG)
        cfg.update(v["overrides"])
        state, trades = run(cfg, syms, intraday, daily, days)
        r = summarise(v["name"], cfg, state, trades)
        r["overrides"] = v["overrides"]
        results.append(r)
        print(json.dumps({k: r[k] for k in ("name", "trades", "total_return_pct", "avg_week_pct", "win_rate", "avg_r", "max_drawdown_pct")}))
    out = ROOT / "data/backtest"
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps({
        "run_at": pd.Timestamp.now(tz=TZ).isoformat(timespec="minutes"),
        "period": [days[0].isoformat(), days[-1].isoformat()] if days else None,
        "universe": len(syms), "results": results}, indent=1))


if __name__ == "__main__":
    main()
