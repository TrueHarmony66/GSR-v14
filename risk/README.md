# Risk, Parameters and Operating Boundaries

## Baseline preset

- Fixed volume: 0.02 lots
- Target: 2.0R
- Initial stop distance: 6–25 dollars after setup construction
- Spread ceiling: 80 points ($0.80 under the tested symbol specification)
- Maximum age: 12 H1 bars
- Friday flatten: hour 20 enabled
- Magic number: 140001

The EA does not calculate account-percentage risk sizing; changing volume changes dollar risk. Any sizing change is a new experiment and must be validated separately.

The R075 report is a native MT5 research result on a custom historical symbol. It is not evidence of guaranteed live returns. Live broker symbol specifications, server-time offset, spread, commission, slippage, liquidity and stop execution can materially change results.

Do not infer high-frequency trade frequency from this EA: the observed rate was approximately 4.88 trades/month over the tested span.
