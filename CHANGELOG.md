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

## 2026-11-08 (evening): hourly news + intraday-news test
- Live bot now checks ASX price-sensitive announcements every hour during the session, logs them, flags news on held
  shares, and shows "Today's ASX news" on the dashboard. Optional `news_exit_categories` (empty = off).
- Test (bot/research_intraday_news.py, 58 days, 5-minute data): only 87 intraday announcements in tradeable shares;
  those that jumped 1%+ in the first 25 minutes then drifted −0.44% by the close (−1.04% after costs, 40% rose).
  With ~20-minute delayed data, chasing intraday news loses → no intraday news entry setup.

## 2026-11-11: mid-week research (see RESEARCH.md)

**Adopted: 10-minute opening range** (`opening_range_minutes` 15 → 10). Zarattini, Barbon & Aziz found shorter opening
ranges work best (5 min in the US); 10 min is the shortest that covers the ASX's staggered 10:00–10:10 open.
60-day intraday test (10 Sep – 10 Nov 2026, 254 shares; a second run on the same data gave identical numbers):

| Variant | Trades | Return | Avg R | SQN | Max DD |
|---|---|---|---|---|---|
| Current (15-min range) | 48 | −7.3% | −0.22 | −1.09 | −10.3% |
| **10-min range — adopted** | 57 | **−6.7%** | **−0.20** | −1.08 | −11.4% |
| 10-min range, top 10 at 2× volume | 101 | −21.3% | −0.35 | −2.96 | −21.3% |
| 15-min range, top 10 at 2× volume | 108 | −17.3% | −0.22 | −1.80 | −18.6% |
| 10-min range, stop 0.25 ATR | 49 | −7.4% | −0.17 | −0.52 | −11.5% |

Meets every adoption rule (better return and avg R, 57 trades, drawdown 1.1 points worse, not testable on daily bars),
but the gain is small and within noise. The core strategy is still losing (−7% over 60 days): this is a tweak, not a fix.
Saturday's run re-checks the old 15-minute range as a variant. Loosening the stocks-in-play filter (top 10, 2× volume)
roughly doubled trades and losses. `tests/simulate_day.py` fixture now scales its normal opening volume with the range length.

**10-year daily test (Dec 2016 – Nov 2026), large-cap ($20M+/day) gap-downs ≥3%, buy open / sell close:**

| Variant | Trades | 10-yr return | Avg R | Max DD | Years up |
|---|---|---|---|---|---|
| Best so far: STW opens ≤ −1.5% | 141 | +5.7% | +0.17 | −8.5% | 5 |
| Nagel: STW 20-day vol ≥ 20% (no open filter) | 138 | −16.4% | −0.04 | −19.5% | 0 |
| Nagel: vol ≥ 15% and STW opens ≤ −1% | 115 | −7.4% | +0.04 | −10.1% | 2 |
| Nagel: best so far + vol ≥ 15% | 70 | +4.5% | +0.18 | −4.1% | 3 |
| Prior-day losers (fell ≥5% yesterday) | 386 | −60% | −0.12 | −60% | 1 |
| …when vol ≥ 20% | 80 | −12.1% | −0.05 | −14.1% | 1 |
| **Stress: STW fell ≥1.5% yesterday** | 115 | +6.2% | +0.20 | −10.7% | 4 |
| **Stress: STW fell ≥2% yesterday** | 74 | **+14.0%** | **+0.36** | −7.6% | 6 |
| Weak open OR stress day | 219 | +1.3% | +0.13 | −13.3% | 5 |
| Stress + Nagel | 73 | −1.2% | +0.11 | −8.7% | 3 |

Not adoptable (the live engine has no gap-down setup yet), but the "stress day" version (buy large caps that gap down
≥3% the morning after the ASX 200 ETF fell ≥2%) is now the strongest daily result: +0.36R, SQN 2.9, ~7 trades a year.
Caveat: thresholds were picked from ~35 combinations tested so far; 2020 alone contributed +11%.
New daily-test keys: `prev_ret_max`, `mkt_vol_min`, `mkt_prev_ret_max`, `or_mkt_prev_ret_max`.

## 2026-11-14: weekly review #2: two adoptions (late-entry rule; stress-day gap-down bounce)

**Live week (9–13 Nov): −0.9%** ($9,749.80 → $9,658.48) vs the +8% goal. 12 trades, 6 winners (50%), average −0.07R.
Mon–Tue made +$96 (5 of 7 trades won); Wed–Thu lost $190 on 4 straight stop-outs, all on mornings the ASX 200 opened slightly
down (−0.3% to −0.4%). Since launch: −3.4% in two weeks, 21 trades. In the bot's own review, breakouts bought before
10:30 averaged −0.48R (15 trades) and those on down-opening mornings −0.94R (6 trades).

**Research:** S&P 500 overnight moves and the ASX (FirstLinks "Night moves": the ASX closes in the same direction as a
>2.5% US move 90% of the time); Stübinger & Schneider (2019, JRFM) overnight-gap mean reversion in S&P 500 stocks, strongest
in the first hours; Concretum "Identifying stocks to fade" (gap reversal, gross only, decayed since 2022 from crowding);
Akbas et al. / Lou, Polk & Skouras (overnight moves reverse intraday); Quantpedia correlated-stress reversal.

**60-day intraday test (5-minute data, 14 Sep – 13 Nov 2026, 254 shares; run twice, identical numbers):**

| Variant | Trades | Return | Avg R | SQN | Max DD |
|---|---|---|---|---|---|
| Current | 58 | −7.4% | −0.21 | −1.19 | −11.4% |
| **No breakout entries before 10:30 — adopted** | 52 | **−5.3%** | **−0.08** | −0.42 | **−7.7%** |
| No entries before 10:20 | 51 | −4.6% | −0.12 | −0.66 | −9.5% |
| No entries before 10:45 | 58 | −8.8% | −0.22 | −1.42 | −8.8% |
| No entries before 10:30, 15-min range | 44 | −5.6% | −0.08 | −0.39 | −6.9% |
| Market filter 0% (only when ASX 200 is up at 10:10) | 44 | −9.6% | −0.42 | −3.21 | −10.4% |
| Market filter −0.5% | 62 | −13.1% | −0.38 | −2.82 | −13.1% |
| 15-min range (re-check) | 47 | −7.2% | −0.22 | −1.09 | −10.3% |
| Gap-down bounce setup (any trigger) | 58 | −7.4% | −0.21 | −1.19 | −11.4% (no stress days in the window → no extra trades) |

The live "market down at open" lesson did not hold: tighter market filters made results worse. The 10:30 rule meets every
adoption rule, but it is fragile (10:45 was worse than current) and the breakout strategy still loses (−5% over 60 days).

**10-year daily test (Dec 2016 – Nov 2026, 1,814 shares, buy at open, sell at close or stop, $5 + 0.10% each way).**
Large caps ($20M+/day) gapping down ≥3%, top 3:

| Variant | Trades | 10-yr return | Avg R | SQN | Max DD | Avg gross | Years up |
|---|---|---|---|---|---|---|---|
| Weak open ≤ −1.5% OR STW fell ≥2% yesterday | 194 | +5.3% | +0.16 | 1.9 | −12.6% | +1.13% | 5 |
| …shares $2–$20 only (live price band) | 180 | −1.7% | +0.12 | 1.5 | −16.0% | +0.92% | 4 |
| S&P 500 fell ≥1.5% overnight | 296 | −12.8% | +0.08 | 1.0 | −17.7% | +0.76% | 4 |
| S&P 500 fell ≥2% overnight | 184 | +10.2% | +0.18 | 2.2 | −5.3% | +1.38% | 4 |
| S&P 500 fell ≥2.5% overnight | 121 | +17.5% | +0.29 | 3.1 | −5.3% | +1.90% | 6 |
| S&P 500 fell ≥3% overnight | 78 | +24.0% | +0.47 | 4.1 | −3.5% | +2.84% | 5 |
| **S&P 500 fell ≥2.5%, stop 0.5 ATR — adopted** | **148** | **+54.8%** | **+0.59** | **3.7** | **−3.1%** | +2.06% | **8 of 9** |
| STW ≥2% OR S&P ≥2.5%, stop 0.5 ATR | 195 | +44.3% | +0.45 | 2.9 | −5.1% | +1.59% | 7 |
| …same, 2% risk / 50% position, 1 ATR stop | 195 | +62.3% | +0.21 | 2.5 | −10.4% | +1.49% | 7 |
| Any trigger incl. weak open | 222 | +1.3% | +0.14 | 1.7 | −10.2% | +1.02% | 4 |
| Control: same stress days, large caps that did NOT gap down | 218 | −41.2% | −0.19 | −3.0 | −41.2% | −0.16% | 0 |
| Control: large-cap gap-downs on calm days (S&P up, STW open ≥ −0.5%) | 402 | −59.8% | −0.11 | −1.2 | −59.8% | −0.01% | 0 |
| Control: top 5 gap-ups ≥4% | 430 | −60% | −0.07 | −0.6 | −60% | +0.15% | 0 |

Finding: the bounce is a market-stress effect. Large caps that gap down hard *after a big US sell-off* recover +2% on
average by the close; the same shares on calm days, and non-gapping shares on the same stress days, lose. The effect grows
with the size of the US fall (1.5% → 2% → 2.5% → 3%), and 2022 (a bear year) was positive. Tighter 0.5 ATR stop worked better
because it allows larger positions (cost is a smaller share of each trade) while the stop is rarely hit on real bounces.

**Adopted (2):**
1. `first_entry_time: "10:30"`: no breakout entries before 10:30 (60-day test: better return, avg R and drawdown, 52 trades;
   intraday-only, can't be tested on daily bars).
2. **New setup, `gapdown_enabled: true`**: after the S&P 500 falls ≥2.5% overnight, buy up to 3 large caps ($20M+/day
   turnover, any price) that open ≥3% down, at the first bar after the opening range (10:10), stop 0.5 ATR (min 1%),
   sell at 15:50. Same 1% risk sizing, daily loss limit and position caps as every trade. Expect ~12–15 trades a year.
   Note on the adoption rule: this setup had no trigger days in the 60-day intraday window, so it changed nothing there
   (it can't beat "current" in that run, only match it). It is adopted on the 10-year daily test (148 trades, +55%,
   +0.59R, −3.1% max drawdown, two negative controls) because the setup is fully expressible on daily bars. Caveats:
   thresholds chosen from ~45 daily combinations tested since 7 Nov; the live bot buys at 10:10 on delayed data rather than
   at the 10:00 open; 2020 contributed a large share of the gain.

**Rejected:** market filter 0% / −0.5%, 15-min range, entries from 10:45, weak-open and STW-only triggers (weaker than the
US trigger), restricting the gap-down setup to $2–$20 shares, 2% risk sizing (better return, worse avg R and drawdown).

Engine: new switches `first_entry_time`, `gapdown_*`; universe now records yesterday's ASX 200 move and the S&P 500's last
overnight move; trades record their `setup` ("orb" or "gapdown"). Costs and results calculations unchanged.
