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

## 2026-11-07: weekly review #1 (no rule changes adopted)

**Live week (3–6 Nov): −2.5%** ($10,000 → $9,749.80) vs the +8% goal. 9 trades, 2 winners (22%), average −0.31R.
Losses were mostly ordinary stop-outs on 3 Nov (5 trades, −$236); FMG (+3.4R) and NWL (+1.1R) won on 5 Nov.
6 Nov: ASX 200 opened −1.4%, bot stood aside (market filter).

**Research this week:** Chan's "buy-on-gap" (buy shares that gap below yesterday's low in an uptrend, sell at the close;
strong 2005–2012 in US small caps, decayed after publication); Griffith University study of large Australian stocks
(intraday rebounds after very bad overnight news); Lou, Polk & Skouras "tug of war" (reversal profits mostly intraday,
momentum overnight); Baltussen/Da "end-of-day reversal" (≈0.04%/day gross, far below our costs); turn-of-month
(not significant in Australia in the full sample).

**Fix:** the 10-year daily backtest stopped trading once a losing variant shrank the account to ~$4,000 (positions
fell under the $1,000 minimum), so every losing variant showed the same "−60%". It now also reports each calendar year
restarted at $10k, the average gross move per trade, and % stopped. Costs and sizing rules unchanged.

**10-year daily test (Dec 2016 – Nov 2026, ~1,800 ASX shares, buy at open, sell at close, $5 + 0.10% each way):**

| Variant | Trades | 10-yr return | Avg R | Avg gross move | Max DD | Years up |
|---|---|---|---|---|---|---|
| Control: top 5 gap-ups ≥4% | 430 | −60% (account too small from 2019) | −0.07 | +0.15% | −60% | 0 of 11 |
| Gap-downs ≥3%, top 5 | 383 | −60% | −0.13 | +0.06% | −61% | 1 |
| …in uptrend (above 200-day avg) | 613 | −60% | +0.02 | +0.47% | −60% | 1 |
| Chan buy-on-gap | 629 | −60% | +0.01 | +0.41% | −60% | 1 |
| Chan, large caps ($20M+/day) | 450 | −47% | −0.02 | +0.29% | −47% | 1 |
| Large-cap gap-down ≥3% when STW opens ≤ −1% | 268 | −18% | +0.05 | +0.62% | −24% | 4 |
| **…when STW opens ≤ −1.5%** | 141 | **+5.7%** | **+0.17** | +1.27% | −8.5% | 5 of 9 |
| …same, 2% risk / 50% max size | 168 | +23.9% | +0.14 | +1.04% | −13.9% | 5 |
| …stock gap ≥4% | 120 | +5.8% | +0.18 | +1.29% | −7.7% | 6 |
| …STW ≤ −2% | 50 | +14.0% | +0.44 | +2.84% | −3.4% | 5 |
| STW ETF itself, opens ≤ −1.5% | 59 | −0.9% | −0.02 | +0.47% | −6.2% | 2 |

Finding: on the ASX, gap-downs *do* bounce from open to close (gross +0.3% to +2.8% per trade), and the bounce is
biggest in large caps on mornings when the whole market opens sharply down. After costs most versions still lose;
only the "weak-market morning, large-cap gap-down" family is positive, and only by ~0.5–2% a year (about 15 trades a
year). These variants were found by searching ~25 combinations, so some of the result is likely luck.

**60-day intraday test (5-minute data, 7 Sep – 6 Nov 2026, 253 shares):**

| Variant | Trades | Return | Avg R | Max DD |
|---|---|---|---|---|
| Current rules | 41 | −2.9% | −0.04 | −7.3% |
| Gap-down V (gapped down ≥2%, buy break of green opening range) | 13 | −4.3% | −0.66 | −4.3% |
| …also on weak-market days | 17 | −4.9% | −0.51 | −4.9% |
| Gap-down buy at 10:15, 1 ATR stop | 31 | −6.4% | −0.20 | −6.4% |
| Current + allow gap-downs | 44 | −6.4% | −0.18 | −8.5% |
| Current, 2% risk / 50% max size | 41 | −1.4% | −0.09 | −11.3% |
| Cameron filter (5× volume, gap 5%+) | 9 | +3.3% | +0.85 | −1.2% |

**Adopted: nothing.** No variant beat "current" on both return and avg R with ≥30 trades. 2% risk / 50% size improved
return but worsened avg R and drawdown (−4 points): rejected. Small-cap gap-down setups lost intraday. The weak-morning
large-cap bounce can't be tested intraday yet (only ~1–2 such mornings in 60 days); it needs engine support and a
live/shadow record before it could be switched on.

New engine switches (all default off / current behaviour): `max_gap_pct`, `require_above_prev`, `require_green_or`,
`entry_mode: "after_or"`, `stop_use_or_low`. Also fixed: `min_gap_pct` no longer bypassed the $20 price cap.

## 2026-11-08: ideas from nine classic trading books (see RESEARCH.md)
- New switchable filters (all off): `market_trend_ma`, `stock_trend_ma`, `near_high_pct`, `rs_min`, `or_close_top_pct`;
  universe now carries 50/200-day averages, 52-week high and 3-month return. 10-year daily test gained the same filters
  plus pivot, volume-surge, engulfing and hammer patterns. Tharp's SQN added to both backtests.
- Results: no book filter beat "current" on both return and avg R with 30+ trades (intraday: current −4.1%, avg −0.03R;
  best book variant "same size every trade" −2.4%, avg −0.035R). 10-year: every book entry filter lowered avg R.
  **Adopted: nothing.** Dashboard now shows SQN.
