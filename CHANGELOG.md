# Changelog

## 2026-11-03: first backtests (2 Sep – 2 Nov 2026, 334 ASX shares, real Yahoo 5-minute data)

**Result: every version tested lost money.** The original rules lost 14–29% over ~40 trading days
(the two runs differ because Yahoo returned slightly different data each time; compare variants within one run).
The main problem is costs: with $10k, $5 brokerage each way plus slippage costs about 0.6% per round trip,
close to the whole risk on a tight-stop trade.

| Variant (round 2) | Trades | Return | Win rate | Avg R | Max drawdown |
|---|---|---|---|---|---|
| Original rules | 71 | −14.2% | 14% | −0.34 | −14.2% |
| Wide stop (0.5 ATR), hold to close | 131 | −21.8% | 25% | −0.21 | −21.8% |
| …with 1 ATR stop | 141 | −22.9% | 22% | −0.19 | −22.9% |
| **…plus 3× volume, top 5 only (adopted)** | 70 | **−8.2%** | 26% | **−0.12** | −9.0% |
| …with 30-min range | 122 | −18.9% | 25% | −0.15 | −18.9% |
| …max 3 positions | 85 | −12.2% | 26% | −0.14 | −15.3% |
| …shares over $2 only | 138 | −23.2% | 26% | −0.23 | −23.2% |

Adopted the least-bad version: buy the breakout as it happens (the close-confirmation rule added earlier today
from one losing trade made things worse over 40 days), stop at ½ ATR (at least 1%), no breakeven or trailing stop
(hold to 3:50pm unless stopped), only stocks at 3× normal volume, top 5 only. It still lost money in the backtest:
this is damage control, not a working edge yet. Next: test different setups (gap fades, closing-auction effects,
mean reversion) and lower-cost execution assumptions.

## 2026-11-03 (evening): research deep dive (see RESEARCH.md)
- Added switchable rules from successful traders: VWAP entry filter and exit (Breitstein, Zarattini & Aziz),
  episodic pivot with low-of-day stop (Kullamägi), A+ sizing (Breitstein), time stop, minimum gap (Cameron).
- New 10-year daily backtest (bot/backtest_daily.py): buying ASX gap-ups at the open lost money in every version
  over Dec 2016 – Nov 2026; gap-ups fade on average on the ASX.
- 60-day intraday test: **adopted "no longs below VWAP"**: −3.5% vs −8.2%, avg R +0.04 vs −0.12, 52 trades,
  max drawdown −6.8% vs −9.0%. Everything else rejected or needs more trades.

## 2026-11-04: Ross Cameron's published rules (see RESEARCH.md)
Tested his rules as switchable options on 60 days of 5-minute ASX data, in two separate runs (Yahoo data differs slightly run to run):

| Rule | Run 1 (trades, return, avg R) | Run 2 |
|---|---|---|
| Current | 68, −7.8%, −0.10 | 60, −8.5%, −0.14 |
| **Shares $2–$20 only — adopted** | 41, **−1.4%**, −0.01 | 36, **−4.4%**, −0.04 |
| No entries after 11:00 | 43, −1.9%, +0.04 | 64, −9.7%, −0.13 (flipped: rejected) |
| No entries after 11:30 | 65, −6.8%, −0.07 | n/a |
| Take profit at 2R / 3R | 73, −12.3% / 70, −10.3% | n/a (rejected: cutting winners hurts) |
| Quarter size until green | 1 trade (positions too small for a $10k account) | n/a |
| 5 pillars (5× volume, up 10%+) | 3 trades, +2.4%, +1.65 | n/a (too few trades; keep watching) |

Adopted: price band $2–$20 (improved return, avg R and drawdown in both runs).

## 2026-11-06: ASX news
- New: the bot reads the ASX's price-sensitive announcements each morning (and again at selection), tags each stock
  in play and each trade with its news, and after every close records how each announcement moved the price
  (data/news/events.json, data/news/stats.json). Backfilled 10,000 announcements (29 Jul – 6 Nov 2026).
- Finding: on the ASX most "good news" gaps up then fades. For shares that opened up, the rest of the day averaged:
  Results +0.5% (432), Exploration +1.5% (69), Acquisition +0.8% (31), Quarterly −1.0% (103), Contract/deal −1.3% (33).
- 60-day intraday test (walk-forward, no hindsight): news rules did not help (current −4.1%, avg −0.03R;
  news learning −4.1%, −0.07R; news-only 14 trades). Rules stay OFF; history keeps growing for re-tests.
