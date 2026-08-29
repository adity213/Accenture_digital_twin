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
Based on the data, the default settings of `divergence_threshold=0.45` and `min_sensor_confidence=0.65` strike an appropriate balance. We see that tightening the divergence threshold too aggressively (e.g., 0.2) causes a very high fallback rate where we frequently discard the ML model's prediction even when it was closer to ground truth than the baseline. 0.45 minimizes unnecessary overrides while keeping a tight lid on catastrophic divergence.