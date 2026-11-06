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
