# ASX Paper Trader

A paper-trading (no real money) day-trading bot for the ASX, starting with $10,000.
It runs on GitHub Actions every 5 minutes through the trading day, using Yahoo Finance prices,
and publishes a phone-friendly dashboard on GitHub Pages.

## How it trades

The rules come from published research and well-known traders' risk rules:

| Rule | Setting | Source |
|---|---|---|
| Scan every ASX listing each morning, keep only shares with ≥ $1M average daily turnover, price ≥ $0.20 and ATR ≥ 1.5% | `min_avg_turnover`, `min_price`, `min_atr_pct` | Liquidity first: a $10k account must be able to get in and out |
| Trade only **stocks in play**: opening volume ≥ 2× normal, green opening range, above yesterday's close; top 10 by relative volume | `min_relative_volume`, `watchlist_size` | Zarattini, Barbon & Aziz (2024) “A Profitable Day Trading Strategy for the U.S. Equity Market”; Ross Cameron's relative-volume rule |
| **Opening range breakout**: buy when price breaks the high of the first 15 minutes (covers the ASX's staggered 10:00–10:10 open) | `opening_range_minutes` | Toby Crabel; Zarattini et al. |
| Long only; stand aside when the ASX 200 opens down more than 1% | `market_min_change_pct` | Trade with the market |
| Risk 1% of equity per trade, max 25% of equity in one stock, max 5 positions | `risk_per_trade_pct` … | Paul Tudor Jones / Linda Raschke: defence first |
| Stop below the opening range or ¼ ATR, whichever is tighter; breakeven at +1R; trail by max(1R, ½ ATR) after +2R | `stop_atr_fraction`, `breakeven_at_r`, `trail_*` | Cut losses fast, let winners run |
| No new entries after 12:30 (midday chop); all positions closed at 15:50 | `last_entry_time`, `exit_time` | Morning momentum; never hold overnight |
| Stop for the day after −2% or 3 losses in a row | `daily_loss_limit_pct`, `max_losses_in_row` | Protect the account on bad days |
| $5 brokerage per trade + 0.10% slippage each way | `brokerage_per_trade`, `slippage_pct` | Realistic costs |

Every setting lives in `bot/config.json`.

## Important limits

- **Yahoo's ASX prices are ~20 minutes delayed.** The bot trades on those delayed bars, so a real trader
  with live data would get different fills.
- **8% a month is a stretch target**, not an expectation. Most day traders lose money; treat the dashboard as an honest test.
- GitHub's scheduled runs can start a few minutes late when GitHub is busy. The bot replays every
  missed 5-minute bar in order, so late runs don't change the results.
- The repo should be **public**: it keeps GitHub Actions free and lets the dashboard read the data.
  It contains only paper trades.

## Setup (one time)

1. Push this repo to GitHub (public).
2. Settings → Pages → Source: **GitHub Actions**. Then Actions → *Publish dashboard* → Run workflow.
3. Actions → *Paper trader* → Run workflow once to check it works (outside market hours it just exits).
4. Open `https://<your-username>.github.io/<repo>/` on your phone and add it to your home screen.

## Files

- `bot/trader.py`: runs each 5-minute cycle · `bot/engine.py`: trading rules · `bot/data.py`: ASX list + Yahoo prices
- `data/`: state, trades and equity written by the bot (the dashboard reads these)
- `docs/index.html`: the dashboard
- `tests/simulate_day.py`: replays a made-up trading day through the whole bot
