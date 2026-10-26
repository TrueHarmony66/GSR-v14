# v14 Trading Rules

## Time sequence

1. At a new H1 bar, process only once.
2. Flatten positions on Friday at or after 20:00 server-time hour when enabled.
3. Close positions once the maximum H1 holding age reaches 12 bars.
4. Allow at most one position for magic number 140001.
5. Reject entries when spread exceeds 80 points.
6. Evaluate entries only at the 13:00 hour.

## London range

The EA reads the same day's H1 bars from 07:00 through 11:00:

- Require at least four qualifying bars.
- Range must be between $8.00 and $32.00 per ounce.
- Compute midpoint = (London high + London low) / 2.
- The 11:00 close defines directional strength.

## Long setup

- London closes in the upper 35% of its range.
- The 12:00 bar trades down to within $2.50 above the midpoint.
- The 12:00 close finishes above the midpoint.
- Ask-to-stop distance is between $6.00 and $25.00.
- Buy at the live Ask.
- Stop = London low − $0.50.
- Target = entry + 2.0 × risk distance.

## Short setup

- London closes in the lower 35% of its range.
- The 12:00 bar trades up to within $2.50 below the midpoint.
- The 12:00 close finishes below the midpoint.
- Bid-to-stop distance is between $6.00 and $25.00.
- Sell at the live Bid.
- Stop = London high + $0.50 + current spread.
- Target = entry − 2.0 × risk distance.

All thresholds are the current v14 baseline. Do not silently change them; use a separately identified experiment.
