# Model Card: DigitalTwin.ai Risk Scoring Model

## 1. Model Details
- **Model Type:** Dual `HistGradientBoostingClassifier`
- **Library:** `scikit-learn` v1.9.0
- **Task:** Binary classification of (1) Bottleneck Risk and (2) Quality Defect Risk over a 15-tick forward horizon.
- **Input Features:** 11 telemetry, SPC, topological, and virtual sensor features per station.

## 2. Training Data & Splits
- **Total Samples:** 960,000 station-ticks across 6 scenario seeds (1000-1005).
- **Train Split:** 800,000 (Seeds 1000-1004)
- **Held-out Test Split:** 160,000 (Seed 1005)
- **Base Rates (measured, not assumed):**
  - Bottleneck Prevalence: 27.43% (Train) / 27.47% (Test)
  - Defect Prevalence: 17.10% (Train) / 18.16% (Test)
- **Class Imbalance Strategy:**
  Class weighting (`sample_weight`) is dynamically applied during `fit()` using balanced ratios for positive and negative classes.

### Note on Defect Prevalence
The `defect_rate` parameter in `simulator/anomalies.py` (changed from 0.85 to 0.05) is stored in the `ActiveAnomaly.params` dict but is **never actually read** by any consumer code. Defect labels in training data come from two sources:
1. Natural per-tick `defect_prob` in `generator.py` (line 232): `0.008 * category_multiplier * shift_multiplier`
2. The `latent_defect_flag` from active anomaly injections, which always sets `defect_flag=True` for the anomaly duration regardless of `defect_rate`.

The measured defect prevalence of ~17% reflects this combination and did not change between model versions. The earlier claim of "~5% defect prevalence" in a prior version of this document was incorrect — the parameter change was inert.

## 3. Original Demo-Calibrated Model (Seed 1004 held-out)

These metrics are from the model trained and shipped prior to the August 2026 retraining.

| Metric        | Bottleneck Model | Defect Model |
|---------------|------------------|--------------|
| **ROC-AUC**   | 0.977            | 0.719        |
| **PR-AUC**    | 0.946            | 0.344        |
| **Precision** | 0.786            | 0.351        |
| **Recall**    | 0.951            | 0.600        |

### Algorithmic Fairness Analysis (Bottleneck Recall)
- **By Zone:** Assembly (94.8%), Body (94.6%), Paint (96.6%)
- **By Sensor Tier:** Manual (95.2%), Rich (95.0%)

## 4. Retrained Model (August 2026, Seed 1005 held-out)

Retrained on 960,000 rows with Task 6 SPC fix applied (`sensor_tier` parameter replaces hardcoded `MANUAL_STATION_IDS`).

| Metric        | Bottleneck Model | Defect Model |
|---------------|------------------|--------------|
| **ROC-AUC**   | 0.979            | 0.746        |
| **PR-AUC**    | 0.950            | 0.478        |
| **Precision** | 0.793            | 0.412        |
| **Recall**    | 0.964            | 0.623        |

### Comparison
The retrained model shows marginal improvement across the board:
- Bottleneck ROC-AUC: 0.977 → 0.979, PR-AUC: 0.946 → 0.950, Recall: 0.951 → 0.964
- Defect ROC-AUC: 0.719 → 0.746, PR-AUC: 0.344 → 0.478, Recall: 0.600 → 0.623

The improvement in defect PR-AUC (0.344 → 0.478, +39% relative) is attributable to the SPC sigma calibration fix (Task 6): manual-tier stations previously received automated-precision CV values (0.050) instead of their correct manual CV (0.130), producing systematically wrong z-scores that the model had to learn around. With correct CV values, the SPC features are now informative rather than misleading for those 8 stations.

### Algorithmic Fairness Analysis (Bottleneck Recall, Retrained)
- **By Zone:** Assembly (96.7%), Body (96.2%), Paint (95.9%)
- **By Sensor Tier:** Manual (96.3%), Rich (96.5%)
- **Known Gap:** TransferBuffer station type has 0% recall on 15 positive test samples — this station type generates very few bottleneck events due to its buffer-only role, so the model has insufficient signal to learn from. Documented rather than papered over.

## 5. Out-of-Distribution (OOD) Generalization
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

*Note: OOD table above reflects the original model. Retraining the OOD scenarios is pending (requires running `generate_scenario_datasets.py` + `validate_ood_scenarios.py` end-to-end with the new SPC fix).*

## 6. Shadow-Mode Router & Fallback Mechanics
To guarantee safe execution in production SCADA systems, the serving layer (`predict_risk_with_routing`) utilizes a **Shadow Mode Router**:
- **Virtual Sensor Confidence:** Monitored per-tick using the `ConfidenceEngine`.
- **Divergence Threshold:** $0.45$ (measures deviation between ML composite risk and deterministic baseline risk).
- **Fallback Trigger:** If sensor confidence falls below $0.65$ or prediction divergence exceeds $0.45$, the router takes `max(ml_risk, baseline_risk)` (conservative fallback) rather than blindly discarding the ML prediction.
- **Benefit:** Ensures the system never under-reports risk, even when novel fault regimes break ML calibration.
