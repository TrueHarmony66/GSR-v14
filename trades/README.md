# Trade Lifecycle

## Native lifecycle

The EA uses one magic number (140001) and one position at a time:

1. A qualifying 13:00 H1 decision produces one market order.
2. The order uses live Bid/Ask, fixed 0.02 lots by baseline preset, structural SL and 2R TP.
3. The position exits by stop, target, the 12-bar timeout, or Friday flattening.
4. MT5 records entry and exit as separate deals; commissions and swaps belong to the native tester ledger.

## Historical smoke example

From the bounded native smoke comparison (May 11–22, 2026):

| Field | Value |
|---|---|
| Direction | Sell |
| Entry | 2026-05-13 13:00:00 |
| Volume | 0.02 |
| Entry fill | 4696.995 |
| Stop / target | 4716.20 / 4658.60 |
| Exit | 2026-05-14 02:00:00 |
| Exit reason | 12-bar timeout |
| Exit fill | 4705.455 |
| Result | -$13.95 |

This example is illustrative, not a promise about future outcomes.
