# Validation Record and Limitations

## R075 historical validation

The archived report records:

- 2020–2026 custom-symbol real-tick tester run
- 400 positions / 800 deals
- +$732.08 net at 0.02 lots
- PF 1.18
- 5.54% maximum equity drawdown
- 0.00 deal-pairing gap

## Independent smoke parity

The protected original and the isolated telemetry copy were run separately under identical bounded conditions (May 11–22, 2026). They produced one identical trade and the same final balance of $4,986.05.

The telemetry copy received a conditional pass because stable setup identity at close events and UTC conversion remain unresolved. That limitation affects research telemetry, not the observed trade parity in the smoke window.

Source and preset hashes, compile output and aggregate results are preserved in `v14/`. Do not modify the protected baseline silently; version every experimental change separately.
