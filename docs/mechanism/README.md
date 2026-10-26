# v14 Mechanism

The system models a three-stage sequence:

1. London inventory formation (07:00–11:00): directional range and close location establish the trend side.
2. Pre-New-York retracement (12:00): price tests the London midpoint while the close remains on the trend side.
3. New York resumption (13:00): the EA enters in the established direction with a structural stop and 2R target.

The design is deliberately selective. Across the R075 historical test it produced about 4.88 trades per month, so it should not be evaluated like a thousand-trade scalp EA.

See `v14_flow.svg` and `v14_flow.mmd`.
