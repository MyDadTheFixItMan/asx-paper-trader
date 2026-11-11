# What successful day traders do — and what held up on ASX data (3 Nov 2026)

## The evidence on day traders as a group
- Brazil, 19,646 new index-futures day traders 2013–15: of those who kept going 300+ days, only 0.5% earned more than a bank teller's starting wage; no evidence they improved with practice (Chague, De-Losso & Giovannetti, 2020).
- Taiwan, whole market 1992–2006: under 3% of day traders on any day were consistently profitable (Barber, Lee, Liu & Odean).
- Australia: ASIC found retail traders lost money trying to time the market in the 2020 volatility, and about $6.3M a month in the micro-cap "momentum ignition" craze.

## What the winners have in common
| Trader | Verified record | Core habits |
|---|---|---|
| Ross Cameron | $583 → $18.8M audited profits 2017–2025 | Only "stocks in play": 5× relative volume, big % move, news catalyst; strict stops; small risk per trade |
| Kristjan Kullamägi | Among Sweden's largest taxpayers (2021) | Episodic pivots: 10%+ gap on news, buy the opening-range high, stop at low of day, risk ≤ 1 ADR; ~25–30% win rate with 5:1 winners |
| Lance Breitstein (ex-Trillium top trader) | 8–9 figure P&L | Trade with the trend; "no longs below VWAP"; wait for the "right side of the V"; size up only on A+ setups |
| SMB Capital (prop firm) | Trains 7-figure traders | A written playbook of setups, reviewed every day; trade only what has proven edge |
| Zarattini, Aziz & Barbon (research) | Peer-reviewed / SSRN | Opening-range breakout on stocks in play; VWAP trend; "noise area" intraday momentum on SPY |

Common thread: very few, very selective trades; small fixed risk; cut losers fast; let winners run; daily review.
None of them claim anything close to 8% a week sustained, and their best years came in exceptional momentum markets (2020–21 for Cameron).

## What does NOT carry over to the ASX
- **First-half-hour → last-half-hour momentum** (Gao et al. 2018, strong in the US): Ho, Lv & Schultz (2021) found no significant effect in Australia. Not implemented.
- **Buying gap-ups:** on 10 years of daily ASX data (Dec 2016 – Nov 2026, ~1,800 shares, liquid only), gap-ups on average *fade* from open to close:

| Opening gap | Avg open→close move |
|---|---|
| down >4% | +0.17% |
| down 2–4% | +0.15% |
| 0–2% up | −0.13% |
| 2–4% up | −0.39% |
| 4–8% up | −0.48% |
| 8%+ up | −1.01% |

Every "buy the gap at the open" version lost money over 10 years after costs (−9%/yr), including the episodic-pivot version (lost every single year).
The small bounce after gap-downs (+0.15%) is real but smaller than our ~0.6% round-trip cost.

## 60-day intraday test of the traders' rules (5-minute data, 2 Sep – 2 Nov 2026)
| Rule | Trades | Return | Avg R | Max DD |
|---|---|---|---|---|
| Current rules | 70 | −8.2% | −0.12 | −9.0% |
| **No longs below VWAP (Breitstein / Zarattini-Aziz) — adopted** | 52 | **−3.5%** | **+0.04** | −6.8% |
| Sell on close below VWAP | 41 | −5.0% | −0.04 | −5.6% |
| VWAP filter + exit | 41 | −5.2% | −0.04 | −5.7% |
| Episodic pivot (gap 4%+, stop low of day) | 5 | −2.1% | −0.90 | −2.1% |
| Time stop 60 min | 64 | −11.6% | −0.28 | −11.6% |
| A+ sizing (1.5× risk at 10× volume) | 70 | −7.9% | −0.11 | −9.3% |
| Ross Cameron filter (5× volume, gap 5%+) | 6 | +0.6% | +0.28 | −1.8% |

The VWAP entry filter is the first rule with a positive average R. It's adopted. Cameron's filter looks good but 6 trades is far too few to trust; it stays on the test list.

## Honest bottom line
On ASX data, the classic momentum day-trading playbook is roughly break-even before costs and negative after them for a $10k account. The most promising directions for the weekly improver:
1. VWAP-based trend rules (first positive avg R).
2. Very selective "stocks in play" (Cameron-style), tested as more data accumulates.
3. Mean-reversion after gap-downs, if execution costs can be brought below ~0.15% (larger positions, cheaper broker).

## Ross Cameron in detail (4 Nov 2026)
What he publishes: audited yearly totals, monthly broker statements, yearly stats, and daily recap videos.
His own numbers: one period at 71% accuracy, average winner $1,800 vs average loser $761, winners held ~3 min, losers ~2 min;
target 2:1 profit-to-loss. Five pillars: up 10%+, 5× relative volume, breaking news, $2–$20, float under 10M.
He starts each day at quarter size until he's up for the day, shrinks size in cold markets, and trades mainly the first 90 minutes.

What transfers to this bot: the stock filter (price band, volume) and the "be selective" principle.
What doesn't: his edge comes from 1-minute charts, real-time Level 2 and 2–3 minute holds in US low-float stocks.
This bot sees 5-minute bars 20 minutes late, so it can't scalp like that, and ASX small caps have far less of the
US retail-driven momentum. His 2:1 profit target and quarter-size start both made results worse here (see CHANGELOG).

## Weak open, then recovery? (6 Nov 2026, bot/research_vday.py)
Buying an ASX 200 ETF (STW) at the open and selling at the close, after costs ($5 each way, 0.05% slippage):

| How the ETF opened | Days (10 yrs) | Avg gross move | Avg after costs | Days up |
|---|---|---|---|---|
| **Down more than 1.5%** | 60 | **+0.44%** | **+0.24%** | 52% |
| Down 1–1.5% | 72 | −0.02% | −0.22% | 39% |
| Down 0.5–1% | 229 | −0.04% | −0.24% | 32% |
| Flat ±0.5% | 1,686 | −0.02% | −0.22% | 31% |
| Up more than 0.5% | 481 | −0.05% | −0.25% | 33% |

Hourly data (2 years, days opening down >1%, 34 days): buying at the open ≈ 0%; waiting for the ETF to climb back above
its open ≈ 0%; waiting for it to close above VWAP −0.07%. Waiting for the turn didn't help in this sample.

Takeaway: a real but small, rare bounce after big down opens (~6 days a year). Candidate setup for the weekly improver:
"weak-open bounce": buy STW/IOZ at the open when it opens down >1.5%, sell at the close, with a stop; test the stop's effect first.

## Gap-downs on the ASX: the bounce is real but small (7 Nov 2026, 10-year daily test)
- Ernest Chan's "buy-on-gap" (buy shares opening below yesterday's low by more than one daily standard deviation while
  above their 20-day average; sell at the close) earned well in US small caps 2005–2012 but decayed after it was
  published (financialnoob; QuantRocket). On the ASX over 10 years it averaged +0.41% gross per trade — not enough to
  cover ~0.5% costs on a $10k account: −60%.
- A Griffith University study of large Australian stocks found intraday rebounds after very bad overnight news.
  Consistent with that, large caps ($20M+/day) gapping down ≥3% on mornings the ASX 200 ETF (STW) opens ≥1.5% down
  rose +1.3% on average from open to close (141 trades, 51% winners) — the only family positive after costs, but only
  +5.7% over 10 years with config sizing (+24% at 2% risk / 50% size).
- Reversal profits are earned intraday and momentum overnight (Lou, Polk & Skouras 2019), which fits: a long-only,
  never-overnight bot is better placed to buy weakness than to chase strength.
- Candidate setup for the weekly improver: "weak-morning large-cap bounce". Needs engine support, a stop, and a shadow
  record before going live; expect ~15 trades a year.

## The classic trading books (8 Nov 2026)
Core ideas (summarised, not quoted), what we built, and what the tests said.

| Book | Core idea | How it's used / tested |
|---|---|---|
| Douglas, *Trading in the Zone* / *The Disciplined Trader* | Any one trade is random; an edge only shows over many trades, so execute every signal the same way and judge on samples, not single results | The bot is fully mechanical; no rule is adopted on fewer than 30 trades. Tested "same size every trade" (no cutting size after losing days): return −2.4% vs −4.1% but avg R slightly worse (−0.035 vs −0.029) → not adopted yet |
| Tharp, *Trade Your Way to Financial Freedom* | Think in R-multiples; expectancy and position sizing matter more than entries; System Quality Number (SQN) | R and avg R were already tracked; **SQN now reported in every backtest and on the dashboard**. Tested 2% risk earlier: worse avg R and drawdown |
| Schwager, *Market Wizards* | Cut losses, let winners run, never average down, respect the market trend (e.g. Tudor Jones's 200-day rule) | Hard stops, no averaging down, hold to close already in place. 200-day market filter: intraday −1.7% vs −4.1% but only 23 trades and worse avg R; 10-year test: made results worse → not adopted |
| O'Neil, *How to Make Money in Stocks* (CAN SLIM) | Buy market leaders near new highs, with relative strength and volume surges, only in a confirmed uptrend | Leaders filter (near 52-wk high + RS + uptrend): 10-year avg R −0.26 (worse than control −0.07); intraday near-high and RS filters −6.4% / −6.8% → rejected. CAN SLIM is a multi-week swing method; on the ASX, leaders that gap up fade *within the day* |
| Murphy, *Technical Analysis of the Financial Markets*; Pring, *Technical Analysis Explained* | Trade in the direction of the trend (moving averages), confirm with volume, multiple timeframes | Stock above 50-day: intraday −7.2% (worse). On the best 10-yr setup (large-cap gap-down on weak mornings), adding "stock above 200-day" gave +4.0% vs +5.7% → no improvement |
| Lefèvre, *Reminiscences of a Stock Operator* (Livermore) | Buy at pivotal points (new highs), follow the line of least resistance, sit with winners | Pivot entries (open above 20-day / 52-week high): 10-year avg R −0.14 / −0.23 → rejected for day trading. "Sit with winners" is already how exits work (no profit targets; tests showed targets hurt) |
| Nison, *Japanese Candlestick Charting Techniques* | Reversal/continuation candle patterns | Bullish engulfing before a gap-up: 10-yr avg R −0.19; hammer before a large-cap gap-down: −0.09 (vs +0.17 without); strong opening candle intraday: −4.5%. No benefit found, consistent with academic tests of candlesticks |

Bottom line: the books' risk rules (small fixed risk, hard stops, no averaging down, mechanical execution, judge by
expectancy over samples) are already the bot's foundation. Their entry methods were built for multi-day to multi-week
holds in US markets; as same-day ASX filters, none improved results. The one promising area remains the large-cap
gap-down bounce on sharply weak mornings (10-yr +5.7%, avg +0.17R, SQN ~2), which none of the book filters improved.

## Mid-week research (11 Nov 2026)
Ideas found (newest evidence first), what was tested, and the verdict.

| Idea | Source | Test | Verdict |
|---|---|---|---|
| Shorter opening range works better for stocks-in-play ORB (5 min best in US; 17 of 25 OR-length/universe combos beat SPY in a replication) | [Zarattini, Barbon & Aziz](https://concretumgroup.com/a-profitable-day-trading-strategy-for-the-u-s-equity-market/); [QuantConnect replication](https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/) (replication had no costs; commenters say other years were weaker) | 60-day intraday: 10-min range −6.7% / −0.20R vs −7.3% / −0.22R | **Adopted** (marginal) |
| Paper's wider net (top 20, relative volume > 1) | same | top 10 at 2× volume: −21% | Rejected: on the ASX the strict 3× / top-5 filter matters |
| Reversal profits rise with market volatility ("evaporating liquidity"): large liquid stocks ≈0 when VIX low, ≈0.1%/day when high | [Nagel 2012 (NBER w17653)](https://www.nber.org/papers/w17653.pdf); [Drechsler, Moreira & Savov, "Liquidity and Volatility"](https://rodneywhitecenter.wharton.upenn.edu/wp-content/uploads/2020/12/18-20.Drechsler2.pdf) (VIX +1 pt → +9 bps over 5 days for large-cap reversal) | 10-yr daily: STW 20-day realised vol filters | Volatility alone doesn't work on the ASX; added to the weak-open setup it cut drawdown (−4.1% vs −8.5%) but also return. Not better |
| Buy prior-day losers; reversal earned intraday | [Lou, Polk & Skouras 2019]; [Chai et al. 2016, Australian short-term reversals](https://ideas.repec.org/a/sae/ausman/v41y2016i1p55-76.html) (Australian reversals are mainly a 1-month, small-cap effect) | 10-yr daily: large caps down ≥5% yesterday | Rejected: −0.04% gross per trade. Large ASX losers keep falling the next day |
| "Correlated stress" reversal: buy equities the day after a broad risk-off day | [Quantpedia 2025](https://quantpedia.com/short-term-correlated-stress-reversal-trading/) | 10-yr daily: large-cap gap-downs ≥3% after STW fell ≥1.5% / ≥2% | **Best daily result yet** (≥2%: 74 trades, +14%, +0.36R, SQN 2.9, 6 of 9 active years up). Lead for the gap-down engine work |
| Buy first half-hour, sell last half-hour on the ASX 200 (U-shaped intraday returns) | [Early bird / late bird, IJMF](https://www.emeraldinsight.com/doi/pdfplus/10.1108/IJMF-06-2018-0184) | Already covered by the 6 Nov STW open→close test (−0.22% per trade after costs) | Not re-tested |

**Market regime (this week):** RBA raised the cash rate 25 bp on 3 Nov (inflation not back in band until late 2027);
ASX 200 near 9,000 (9,030 on 9 Nov) after swinging from early losses; miners and gold stocks firm on Chinese
producer prices, banks weak after ANZ's result, oil falling ([Trading Economics, 3 Nov](https://tradingeconomics.com/australia/stock-market/news/597537),
[9 Nov](https://tradingeconomics.com/australia/stock-market/news/599428)). Rising rates and choppy opens keep the
weak-market filter relevant; no regime change that alters the rules.

**Most promising lead:** a "stress-day large-cap bounce" (weak open or prior-day sell-off of ≥2%, large caps gapping
down ≥3%, buy open, sell close, 1 ATR stop). Needs engine support plus a shadow record before going live.
