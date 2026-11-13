"""Market data: ASX company list + Yahoo Finance prices (via yfinance)."""
from __future__ import annotations

import io
import time as _time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

TZ = "Australia/Sydney"
HEADERS = {"User-Agent": "Mozilla/5.0 (asx-paper-trader)"}
ASX_LIST_URLS = [
    # Used by the ASX website's own company directory download
    "https://asx.api.markitdigital.com/asx-research/1.0/companies/directory/file?access_token=83ff96335c2d45a094df02a206a39ff4",
    # Legacy list
    "https://www.asx.com.au/asx/research/ASXListedCompanies.csv",
]


# ---------- ASX listings ----------
def _parse_codes(text: str) -> list[str]:
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if "ASX code" in l), None)
    if start is None:
        return []
    df = pd.read_csv(io.StringIO("\n".join(lines[start:])))
    col = next(c for c in df.columns if "ASX code" in c)
    codes = df[col].dropna().astype(str).str.strip().str.upper()
    return sorted({c for c in codes if c.isalnum() and 2 <= len(c) <= 6})


def asx_codes(cache: Path, max_age_days: int = 7) -> list[str]:
    """All ASX-listed codes. Refreshed weekly; falls back to the cached copy."""
    if cache.exists() and (_time.time() - cache.stat().st_mtime) < max_age_days * 86400:
        codes = cache.read_text().split()
        if len(codes) > 500:
            return codes
    for url in ASX_LIST_URLS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            codes = _parse_codes(r.text)
            if len(codes) > 500:
                cache.write_text("\n".join(codes))
                return codes
        except Exception as e:  # noqa: BLE001
            print(f"ASX list from {url[:60]} failed: {e}")
    if cache.exists():
        return cache.read_text().split()
    raise RuntimeError("Could not load the ASX company list")


# ---------- Yahoo ----------
def _yf():
    import yfinance as yf  # imported lazily so tests run without it
    return yf


def _download(tickers: list[str], _retry: bool = True, **kw) -> dict[str, pd.DataFrame]:
    """Batch download; returns {ticker: DataFrame[Open, High, Low, Close, Volume]}."""
    yf = _yf()
    out: dict[str, pd.DataFrame] = {}
    chunk = 150
    for i in range(0, len(tickers), chunk):
        batch = tickers[i:i + chunk]
        for attempt in range(3):
            try:
                df = yf.download(batch, group_by="ticker", auto_adjust=False, threads=True,
                                 progress=False, **kw)
                break
            except Exception as e:  # noqa: BLE001
                print(f"Yahoo download failed ({e}), retrying")
                _time.sleep(5 * (attempt + 1))
        else:
            continue
        if df is None or df.empty:
            continue
        for t in batch:
            try:
                sub = df[t] if isinstance(df.columns, pd.MultiIndex) else df
            except KeyError:
                continue
            sub = sub.dropna(subset=["Close"])
            if not sub.empty:
                out[t] = sub
        if len(tickers) > chunk:
            _time.sleep(2)
    missing = [t for t in tickers if t not in out]
    if missing and len(missing) < len(tickers) and _retry:
        _time.sleep(20)
        out.update(_download(missing, _retry=False, **kw))
    return out


def build_universe(codes: list[str], cfg: dict, today: datetime) -> dict:
    """Morning scan of every listing -> tradeable universe with ATR, turnover and opening volume norms."""
    tickers = [f"{c}.AX" for c in codes]
    daily = _download(tickers, period="1y", interval="1d")
    today_d = today.date()
    rows = []
    for t, df in daily.items():
        df = df.copy()
        idx = pd.to_datetime(df.index)
        df.index = idx.tz_localize(TZ) if idx.tz is None else idx.tz_convert(TZ)
        df = df[df.index.date < today_d]  # completed sessions only
        if len(df) < 20:
            continue
        prev_close = float(df["Close"].iloc[-1])
        if prev_close < cfg["min_price"]:
            continue
        hl = df["High"] - df["Low"]
        hc = (df["High"] - df["Close"].shift()).abs()
        lc = (df["Low"] - df["Close"].shift()).abs()
        atr = float(pd.concat([hl, hc, lc], axis=1).max(axis=1).tail(14).mean())
        turnover = float((df["Close"] * df["Volume"]).tail(20).mean())
        atr_pct = atr / prev_close * 100
        if turnover < cfg["min_avg_turnover"] or atr_pct < cfg["min_atr_pct"]:
            continue
        rows.append((t[:-3], prev_close, atr, turnover, trend_meta(df["Close"], df["High"])))
    rows.sort(key=lambda r: r[3], reverse=True)
    rows = rows[: cfg["max_universe"]]
    syms = {r[0]: {"prev_close": round(r[1], 4), "atr": round(r[2], 4), "avg_turnover": round(r[3]), **r[4]}
            for r in rows}

    # Typical opening-range volume over the last 14 sessions (for relative volume)
    n = cfg["opening_range_minutes"]
    intraday = _download([f"{s}.AX" for s in syms], period="1mo", interval="5m")
    for t, df in intraday.items():
        s = t[:-3]
        df = to_sydney(df)
        df = df[df.index.date < today_d]
        mins = df.index.hour * 60 + df.index.minute
        first = df[(mins >= 600) & (mins < 600 + n)]
        per_day = first.groupby(first.index.date)["Volume"].sum()
        per_day = per_day[per_day > 0].tail(14)
        if len(per_day) >= 5:
            syms[s]["avg_or_volume"] = float(per_day.mean())
    syms = {s: m for s, m in syms.items() if m.get("avg_or_volume")}

    idx = _download([cfg["market_index"]], period="1y", interval="1d").get(cfg["market_index"])
    index_prev = None
    if idx is not None:
        idx = to_sydney(idx)
        idx = idx[idx.index.date < today_d]
        if len(idx):
            index_prev = float(idx["Close"].iloc[-1])
    syms["__index__"] = {"prev_close": index_prev, **(trend_meta(idx["Close"]) if idx is not None and len(idx) else {})}
    if idx is not None and len(idx) >= 2:  # yesterday's ASX 200 move (stress-day filter for the gap-down setup)
        syms["__index__"]["prev_ret"] = round(float(idx["Close"].iloc[-1] / idx["Close"].iloc[-2] - 1) * 100, 2)
    us = _download(["^GSPC"], period="1mo", interval="1d").get("^GSPC")
    if us is not None:  # last completed US session before this ASX morning (S&P 500 overnight move)
        us = to_sydney(us)
        us = us[us.index.date < today_d]["Close"].dropna()
        if len(us) >= 2:
            syms["__index__"]["us_prev_ret"] = round(float(us.iloc[-1] / us.iloc[-2] - 1) * 100, 2)
    return {"date": today_d.isoformat(), "scanned": len(codes), "priced": len(daily), "symbols": syms}


def trend_meta(closes: pd.Series, highs: pd.Series | None = None) -> dict:
    """Book-style trend facts from completed daily closes (Murphy/Pring MAs, O'Neil 52-week high & 3-month return)."""
    c = closes.dropna()
    out = {}
    if len(c) >= 50:
        out["ma50"] = round(float(c.tail(50).mean()), 4)
    if len(c) >= 200:
        out["ma200"] = round(float(c.tail(200).mean()), 4)
    if len(c) >= 64:
        out["ret63"] = round(float(c.iloc[-1] / c.iloc[-64] - 1) * 100, 2)
    h = (highs if highs is not None else c).dropna().tail(252)
    if len(h) >= 150:
        out["high252"] = round(float(h.max()), 4)
    return out


def to_sydney(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    idx = pd.to_datetime(df.index)
    df.index = idx.tz_localize("UTC").tz_convert(TZ) if idx.tz is None else idx.tz_convert(TZ)
    return df


def intraday_bars(tickers: list[str], now: pd.Timestamp, delay_min: int) -> dict[str, list[dict]]:
    """Today's completed 5-minute bars per symbol (Yahoo ASX data runs ~20 minutes behind)."""
    if not tickers:
        return {}
    data = _download(tickers, period="1d", interval="5m")
    cutoff = now - pd.Timedelta(minutes=5 + delay_min)
    out = {}
    for t, df in data.items():
        df = to_sydney(df)
        df = df[(df.index.date == now.date()) & (df.index <= cutoff)]
        bars = [{"t": ts, "o": float(r.Open), "h": float(r.High), "l": float(r.Low),
                 "c": float(r.Close), "v": float(r.Volume or 0)} for ts, r in df.iterrows()]
        key = t[:-3] if t.endswith(".AX") else t
        if bars:
            out[key] = bars
    return out
