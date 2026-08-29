# Router Threshold Audit

| Divergence Threshold | Min Sensor Confidence | Fallback Triggered (%) | ML Model Was Actually Better (%) |
|----------------------|-----------------------|------------------------|----------------------------------|
| 0.2 | 0.5 | 74.2% | 39.4% |
| 0.2 | 0.6 | 74.2% | 39.4% |
| 0.2 | 0.65 | 74.2% | 39.4% |
| 0.2 | 0.7 | 80.8% | 40.9% |
| 0.3 | 0.5 | 35.5% | 42.9% |
| 0.3 | 0.6 | 35.5% | 42.9% |
| 0.3 | 0.65 | 35.5% | 42.9% |
| 0.3 | 0.7 | 44.1% | 46.6% |
| 0.4 | 0.5 | 13.4% | 58.7% |
| 0.4 | 0.6 | 13.4% | 58.7% |
| 0.4 | 0.65 | 13.4% | 58.7% |
| 0.4 | 0.7 | 26.1% | 64.8% |
| 0.45 | 0.5 | 12.8% | 58.4% |
| 0.45 | 0.6 | 12.8% | 58.4% |
| 0.45 | 0.65 | 12.8% | 58.4% |
| 0.45 | 0.7 | 25.5% | 65.0% |
| 0.5 | 0.5 | 12.7% | 58.7% |
| 0.5 | 0.6 | 12.7% | 58.7% |
| 0.5 | 0.65 | 12.7% | 58.7% |
| 0.5 | 0.7 | 25.4% | 65.1% |
| 0.6 | 0.5 | 12.3% | 59.2% |
| 0.6 | 0.6 | 12.3% | 59.2% |
| 0.6 | 0.65 | 12.3% | 59.2% |
| 0.6 | 0.7 | 25.1% | 65.5% |

## Recommendation

### What the data actually shows

1. **Divergence is a weak, near-coin-flip signal.** At every threshold tested, when fallback triggers, the ML model was closer to ground truth somewhere between 39-65% of the time. This means the divergence metric alone cannot reliably distinguish "ML is wrong" from "ML is right but disagrees with the baseline." It is better than random at the looser thresholds (59-65% at div≥0.4) but still wrong about 4 in 10 times.

2. **The current default (0.45 / 0.65) is not the best point in this grid.** The row (0.6, 0.5) achieves both a lower fallback rate (12.3% vs 12.8%) and a higher ML-was-better rate (59.2% vs 58.4%). That said, the differences between all rows in the div≥0.4 band are small — they all cluster around 12-13% fallback rate with 58-59% ML-better rate, because `min_sensor_confidence` values 0.5-0.65 almost never trigger on their own (most rich-tier stations report confidence well above 0.65).

3. **The `min_sensor_confidence=0.7` column is different.** Raising this to 0.7 roughly doubles the fallback rate (to ~25%) because it starts catching rich-tier stations during normal operation, not just actual degradation. The ML-was-better rate also rises to ~65%, confirming that a large fraction of these extra fallbacks are unnecessary.

### Practical implication

The real safety improvement came from Task 2's change to the fallback *behavior*, not from threshold tuning. The previous fallback blindly replaced ML output with the baseline. The current fallback takes `max(ml_risk, baseline_risk)` — a conservative envelope that never under-reports risk regardless of which prediction was closer to truth. This means that even when the divergence signal incorrectly triggers fallback (the 40% false-trigger rate), the system still uses whichever prediction was *higher*, preserving safety.

Given this, the exact threshold values matter less than they would under a blind-override fallback. The defaults of `divergence_threshold=0.45` / `min_sensor_confidence=0.65` are acceptable; moving to `0.6` / `0.5` would be marginally better by the numbers but the difference is within noise.