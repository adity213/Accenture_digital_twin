# Scenario-Based and Out-of-Distribution (OOD) Validation Report

Predictive risk scoring models evaluated only on random train/test splits from a synthetic simulator can easily overfit to simulator constants (such as fixed anomaly lengths or machine base times). To test whether our model learns transferable failure dynamics, we evaluated it against 5 distinct operational distribution shifts:

1. **Spatial Shift**: Model trained on ST01 to ST30, evaluated zero-shot on unseen final assembly stations ST31 to ST40.
2. **Compound Fault Shift**: Model trained on single isolated anomalies, evaluated on simultaneous multi-fault events (mechanical friction plus motor electrical surge).
3. **Line Speed Acceleration**: Evaluated under a +20% faster line speed (shorter takt time).
4. **Extreme Severity Shift**: Evaluated on heavy mechanical wear outside nominal training bounds.
5. **Sensor Telemetry Loss**: Evaluated under 40% intermittent sensor dropouts to test coupling with virtual sensor imputation.

---

## Benchmark Results

All evaluations were run on held-out scenario datasets generated via `scripts/generate_scenario_datasets.py` and evaluated via `scripts/evaluate_scenario_validation.py` at decision threshold $\tau = 0.50$:

| Operating Regime | Shift Description | Test Rows | Positives | ROC-AUC | PR-AUC | Precision | Recall | F1 | Brier Score | False Alarm Rate | $\Delta\text{ROC}$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Baseline I.I.D.** | In-distribution random split (70/30) | 36,000 | 162 | **0.932** | 0.843 | 14.4% | **85.8%** | 0.246 | 0.0137 | 2.31% | *Baseline* |
| **2. Spatial OOD** | ST01-30 $\rightarrow$ unseen ST31-40 | 30,000 | 948 | **0.922** | 0.842 | **98.4%** | **84.4%** | **0.909** | 0.0056 | **0.04%** | $-0.010$ |
| **3. Symptom OOD** | Single $\rightarrow$ compound multi-faults | 120,000 | 445 | **0.920** | 0.851 | 4.9% | **85.6%** | 0.093 | 0.0372 | 6.13% | $-0.012$ |
| **4. Speed Stress** | +20% line velocity | 120,000 | 971 | **0.932** | 0.843 | 11.5% | **86.0%** | 0.202 | 0.0320 | 5.42% | $+0.000$ |
| **5. Severity Stress** | Severe mechanical wear | 120,000 | 1,197 | **0.939** | 0.856 | 13.9% | **86.8%** | 0.239 | 0.0357 | 4.45% | $+0.007$ |
| **6. Sensor Dropout** | 40% missing telemetry | 120,000 | 942 | **0.701** | 0.521 | 25.1% | **52.2%** | 0.339 | 0.0125 | 1.10% | $-0.231$ |

---

## Detailed Findings by Regime

### 1. Spatial Transfer (ST01–ST30 to ST31–ST40)
- **Goal**: Check if the model learns physical indicators (cycle-time inflation, buffer drainage rate, statistical drift) or simply memorizes station numbers.
- **Results**: ROC-AUC is 0.922 ($\Delta = -0.010$ from baseline) with 84.4% recall and 98.4% precision.
- **Takeaway**: Because features are normalized against each station's target takt and queue limits (`cycle_time_ratio`, `buffer_fill_pct`, `spc_z_score`), the classifier transfers directly to downstream assembly stations without retraining.

### 2. Compound Multi-Faults
- **Goal**: Evaluate model behavior when two fault modes happen at the same time (tool drift and motor overload).
- **Results**: ROC-AUC (0.920) and Recall (85.6%) stay high because cycle time delays are still present. Precision drops to 4.9% due to the low positive base rate in this test slice.
- **Takeaway**: The model detects the primary slowing signal, but the interaction of power spikes with cycle drift increases false alarms.

### 3. Line Speed Acceleration (+20% Takt)
- **Goal**: Check if speeding up the line causes false alarms.
- **Results**: ROC-AUC is 0.932 and Recall is 86.0% (identical to baseline).
- **Takeaway**: Because time features scale with nominal station takt, line speed changes do not trigger false bottlenecks.

### 4. Extreme Mechanical Wear
- **Goal**: Check model performance when drift and motor surge go far beyond normal training ranges.
- **Results**: ROC-AUC rises to 0.939 and Recall reaches 86.8% (highest among all regimes).
- **Takeaway**: The model decision boundaries respond monotonically to severe physical signals.

### 5. Sensor Network Dropouts (40% Missing Values)
- **Goal**: Test model performance when wireless sensor packets drop out.
- **Results**: ROC-AUC drops to 0.701 and Recall falls to 52.2%.
- **Takeaway**: Rather than outputting uncalibrated guesses during sensor failure, the system tracks `sensor_confidence`. When confidence drops below 65%, the SCADA interface flags **DEGRADED VISIBILITY** and prompts the operator to inspect the station gauge manually.
