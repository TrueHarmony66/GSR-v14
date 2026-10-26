# GSR v14 — London-to-New York Midpoint Retest Continuation

This repository archive contains the GSR v14 XAUUSD research candidate, its MetaTrader 5 implementation, native validation outputs, and an explainer layer.

## Documentation

- [System rules](rules/README.md)
- [Mechanism and decision flow](mechanism/README.md)
- [Trade lifecycle and examples](trades/README.md)
- [Risk and parameters](risk/README.md)
- [Validation and limitations](validation/README.md)
- [Architecture diagram](diagrams/architecture.svg)

The EA source and compiled binary are in the repository's `v14/` folder.

The historical R075 report records 400 trades, +$732.08 net at 0.02 lots, PF 1.18 and 5.54% maximum equity drawdown on the tested custom-symbol real-tick history. These are research results, not a guarantee of live profitability. Broker server time, spread, fills, commissions and slippage must be independently verified before deployment.

This is an H1 intraday continuation system, not a high-frequency scalp engine.
