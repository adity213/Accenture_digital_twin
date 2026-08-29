# Model Card: DigitalTwin.ai Risk Scoring Model

## 1. Model Details
- **Model Type:** Dual `HistGradientBoostingClassifier`
- **Library:** `scikit-learn` v1.9.0
- **Task:** Binary classification of (1) Bottleneck Risk and (2) Quality Defect Risk over a 30-tick forward horizon.
- **Input Features:** 19 telemetry, SPC, topological, and virtual sensor features per station.

## 2. Training Data & Splits
- **Total Samples:** 800,000 station-ticks across 5 scenario seeds.
- **Train/Val Split:** 80% (640,000 samples)
- **Held-out Test Split:** 20% (160,000 samples)
- **Base Rates:**
  - Bottleneck Prevalence: 27.88% (Train) / 25.63% (Test)
  - Defect Prevalence: 16.41% (Train) / 16.07% (Test)
- **Class Imbalance Strategy:**
  Class weighting (`sample_weight`) is dynamically applied during `fit()` using balanced ratios for positive and negative classes.

## 3. In-Distribution Metrics (Test Set)
Evaluated at operational decision threshold $\tau = 0.50$ on the held-out test split (Seed 1004).

| Metric        | Bottleneck Model | Defect Model |
|---------------|------------------|--------------|
| **ROC-AUC**   | 0.977            | 0.719        |
| **PR-AUC**    | 0.946            | 0.344        |
| **Precision** | 0.786            | 0.351        |
| **Recall**    | 0.951            | 0.600        |

### Algorithmic Fairness Analysis (Bottleneck Recall)
- **By Zone:** Assembly (94.8%), Body (94.6%), Paint (96.6%)
- **By Sensor Tier:** Manual (95.2%), Rich (95.0%) - Validates VirtualSensorEngine imputation equality.

## 4. Out-of-Distribution (OOD) Generalization
The models were evaluated against 7 distinct operational regimes to prevent simulation overfitting and ensure operational safety.

| Operating Regime                   | ROC-AUC (BN/Def)  | PR-AUC (BN/Def)   | Recall (BN/Def)   | FAR (BN/Def)     |
|------------------------------------|-------------------|-------------------|-------------------|------------------|
| 1. Baseline I.I.D.                 |  0.979 / 0.776    |  0.859 / 0.518    |  99.3% / 68.2%    |   9.3% / 21.0%   |
| 2. Spatial OOD (Cross-Station)     |  0.967 / 0.483    |  0.899 / 0.194    |  98.0% /  0.0%    |  12.8% /  0.2%   |
| 3. Symptom OOD (Compound Faults)   |  0.982 / 0.760    |  0.871 / 0.466    |  99.5% / 64.3%    |   8.3% / 19.7%   |
| 4. Speed Stress OOD (+20% Takt)    |  0.981 / 0.746    |  0.891 / 0.450    |  99.1% / 63.6%    |   8.2% / 20.5%   |
| 5. Severity Stress OOD (Extreme)   |  0.979 / 0.730    |  0.866 / 0.395    |  99.1% / 60.4%    |   8.6% / 22.0%   |
| 6. Sensor Degradation Stress (40%) |  0.955 / 0.717    |  0.726 / 0.296    |  96.9% / 59.9%    |  11.2% / 22.7%   |
| 7. Emergent Wear Failures (Organic)|  0.921 / 0.726    |  0.873 / 0.400    |  89.7% / 62.7%    |   9.6% / 23.8%   |

## 5. Shadow-Mode Router & Fallback Mechanics
To guarantee safe execution in production SCADA systems, the serving layer (`predict_risk_with_routing`) utilizes a **Shadow Mode Router**:
- **Virtual Sensor Confidence:** Monitored per-tick using the `ConfidenceEngine`.
- **Divergence Threshold:** $0.45$ (measures deviation between ML composite risk and deterministic baseline risk).
- **Fallback Trigger:** If sensor confidence falls below $0.65$ or prediction divergence exceeds $0.45$, the router fails safe to the deterministic baseline heuristic.
- **Benefit:** Ensures deterministic boundaries even when novel fault regimes break ML calibration.
