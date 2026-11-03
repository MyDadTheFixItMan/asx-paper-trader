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
