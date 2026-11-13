# ASX Paper Trader

A paper-trading (no real money) day-trading bot for the ASX, starting with $10,000.
It runs on GitHub Actions every 5 minutes through the trading day, using Yahoo Finance prices,
and publishes a phone-friendly dashboard on GitHub Pages.

## How it trades

The rules come from published research and well-known traders' risk rules:

| Rule | Setting | Source |
|---|---|---|
| Scan every ASX listing each morning, keep only shares priced $2–$20 with ≥ $1M average daily turnover and ATR ≥ 1.5% | `min_price`, `max_price`, `min_avg_turnover`, `min_atr_pct` | Liquidity first; Ross Cameron's price band (adopted 4 Nov after two backtests) |
| Trade only **stocks in play**: opening volume ≥ 3× normal, green opening range, above yesterday's close; top 5 by relative volume | `min_relative_volume`, `watchlist_size` | Zarattini, Barbon & Aziz (2024); Cameron's relative-volume rule |
| **Opening range breakout**: buy when price breaks the high of the first 10 minutes (the shortest range that covers the ASX's staggered 10:00–10:10 open) | `opening_range_minutes` | Toby Crabel; Zarattini et al. (adopted 11 Nov: 10 min beat 15 min in the 60-day test) |
| **No longs below VWAP** | `vwap_entry_filter` | Lance Breitstein; Zarattini & Aziz (adopted 3 Nov: first rule with positive avg R) |
| Long only; stand aside when the ASX 200 opens down more than 1% | `market_min_change_pct` | Trade with the market |
| Risk 1% of equity per trade (scaled down after losing days), max 25% of equity in one stock, max 5 positions | `risk_per_trade_pct` … | Paul Tudor Jones / Linda Raschke: defence first |
| Stop below the opening range or ½ ATR (at least 1%); no breakeven or trailing stop, hold to the close | `stop_atr_fraction`, `min_stop_pct` | Backtest: cutting winners early made results worse |
| Breakouts only between 10:30 and 12:30; all positions closed at 15:50 | `first_entry_time`, `last_entry_time`, `exit_time` | Early breakouts were false starts (adopted 14 Nov after the 60-day test); never hold overnight |
| **Stress-day gap-down bounce** (second setup): after the S&P 500 falls ≥2.5% overnight, buy up to 3 large caps (≥$20M/day, any price) that open ≥3% down, stop ½ ATR, sell at the close | `gapdown_*` | 10-year daily test: 148 trades, +55%, +0.59R (adopted 14 Nov); Stübinger & Schneider (2019); Quantpedia stress reversal |
| Stop for the day after −2% or 3 losses in a row | `daily_loss_limit_pct`, `max_losses_in_row` | Protect the account on bad days |
| $5 brokerage per trade + 0.10% slippage each way | `brokerage_per_trade`, `slippage_pct` | Realistic costs |
| Tested but off: news filters, small-cap gap-down setups, Cameron 5-pillar filter, larger sizing, tighter market filter | see CHANGELOG.md | Not yet proven over ≥30 trades |

Every setting lives in `bot/config.json`.

## Important limits

- **Yahoo's ASX prices are ~20 minutes delayed.** The bot trades on those delayed bars, so a real trader
  with live data would get different fills.
- **8% a week is the challenge target**, far above anything any tested rule has achieved, not an expectation. Most day traders lose money; treat the dashboard as an honest test.
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
