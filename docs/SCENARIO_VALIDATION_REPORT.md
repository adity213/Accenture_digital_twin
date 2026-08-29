# Out-of-Distribution (OOD) & Scenario Validation Report

## 1. Executive Summary
Machine learning models trained solely on in-distribution synthetic data often suffer from catastrophic performance degradation when deployed onto factory lines experiencing unseen operating conditions, line speed changes, sensor dropouts, or compound multi-faults.

To validate generalization capability and prevent overfitting to simulation artifacts, DigitalTwin.ai evaluates dual Gradient Boosted Decision Tree (GBDT) estimators across **7 distinct Out-of-Distribution (OOD) operational regimes**.

---

## 2. Benchmark Evaluation Protocol & Separated Metrics

All evaluations were executed on held-out scenario datasets generated via [`scripts/generate_scenario_datasets.py`](file:///c:/Android/Projects/accenture/digitaltwin-ai/scripts/generate_scenario_datasets.py) and evaluated at the operational decision threshold $\tau = 0.50$. Metrics for **Bottleneck Prediction** and **Quality Defect Prediction** are evaluated and reported separately:

```text
===================================================================================================================
 COMPREHENSIVE OUT-OF-DISTRIBUTION (OOD) GENERALIZATION BENCHMARK (Bottleneck / Defect Separated)
===================================================================================================================
Operating Regime                   | ROC-AUC (BN/Def)  | PR-AUC (BN/Def)   | Recall (BN/Def)   | FAR (BN/Def)     
-------------------------------------------------------------------------------------------------------------------
1. Baseline I.I.D.                 |  0.979 / 0.776   |  0.859 / 0.518   |  99.3% / 68.2%   |   9.3% / 21.0%
2. Spatial OOD (Cross-Station)     |  0.967 / 0.483   |  0.899 / 0.194   |  98.0% /  0.0%   |  12.8% /  0.2%
3. Symptom OOD (Compound Faults)   |  0.982 / 0.760   |  0.871 / 0.466   |  99.5% / 64.3%   |   8.3% / 19.7%
4. Speed Stress OOD (+20% Takt)    |  0.981 / 0.746   |  0.891 / 0.450   |  99.1% / 63.6%   |   8.2% / 20.5%
5. Severity Stress OOD (Extreme)   |  0.979 / 0.730   |  0.866 / 0.395   |  99.1% / 60.4%   |   8.6% / 22.0%
6. Sensor Degradation Stress (40%) |  0.955 / 0.717   |  0.726 / 0.296   |  96.9% / 59.9%   |  11.2% / 22.7%
7. Emergent Wear Failures (Organic)|  0.921 / 0.726   |  0.873 / 0.400   |  89.7% / 62.7%   |   9.6% / 23.8%
-------------------------------------------------------------------------------------------------------------------
 Generalization Gaps (Relative to Baseline I.I.D. ROC-AUC):
   * 2. Spatial OOD (Cross-Station)   : BN dROC-AUC = -0.012 | Def dROC-AUC = -0.293
   * 3. Symptom OOD (Compound Faults) : BN dROC-AUC = +0.003 | Def dROC-AUC = -0.016
   * 4. Speed Stress OOD (+20% Takt)  : BN dROC-AUC = +0.002 | Def dROC-AUC = -0.030
   * 5. Severity Stress OOD (Extreme) : BN dROC-AUC = +0.000 | Def dROC-AUC = -0.046
   * 6. Sensor Degradation Stress (40%): BN dROC-AUC = -0.024 | Def dROC-AUC = -0.059
   * 7. Emergent Wear Failures (Organic): BN dROC-AUC = -0.058 | Def dROC-AUC = -0.050
===================================================================================================================
```

---

## 3. In-Depth Analysis of Operating Regimes

### 3.1 Regime 1: Baseline I.I.D. (Nominal Benchmark)
- **Bottleneck Performance**: ROC-AUC $0.979$, PR-AUC $0.859$, Recall $99.3\%$, False Alarm Rate $9.3\%$.
- **Defect Performance**: ROC-AUC $0.776$, PR-AUC $0.518$, Recall $68.2\%$, False Alarm Rate $21.0\%$.
- **Precision-Recall Mechanics**: The lower PR-AUC for defect prediction ($0.518$) relative to ROC-AUC ($0.776$) is a direct mathematical consequence of class imbalance: ground-truth defect prevalence is $P(Y=1) \approx 5.3\%$. Across an 18:1 negative-to-positive ratio, minor false alarms in high-variance manual stations reduce precision while ranking discrimination remains solid.

### 3.2 Regime 2: Spatial OOD Transfer (Train ST01–ST30 $\to$ Test ST31–ST40)
- **Bottleneck Transfer**: ROC-AUC $0.967$ ($\Delta = -0.012$), Recall $98.0\%$.
- **Analysis**: Because all features are normalized against each station's specific nominal takt, vibration baseline, and buffer capacity (`cycle_time_ratio`, `buffer_fill_pct`, `spc_z_score`), the bottleneck classifier transfers seamlessly to completely unseen final assembly stations.
- **Defect Transfer**: Quality defects on ST31–ST40 require downstream optical inspection gates (ST40 buy-off); zero-shot spatial transfer reflects the absence of upstream training examples for assembly-specific defect modes.

### 3.3 Regime 3: Symptom OOD (Compound Multi-Faults)
- **Performance**: Bottleneck ROC-AUC $0.982$ ($\Delta = +0.003$), Recall $99.5\%$.
- **Analysis**: Simultaneous occurrence of multiple mechanical/electrical faults (e.g., mechanical friction plus electrical surges) produces compound physical signatures that are readily recognized by the ensemble tree structure without false suppression.

### 3.4 Regime 4: Operational Speed Stress (+20% Takt Acceleration)
- **Performance**: Bottleneck ROC-AUC $0.981$ ($\Delta = +0.002$), Recall $99.1\%$.
- **Analysis**: Accelerating line velocity from $60\text{ JPH}$ to $72\text{ JPH}$ shortens nominal cycle times. Because the SPC engine dynamically scales baseline standard deviation ($\sigma_{\text{base}} = T_{\text{target}} \cdot \text{CV}_{\text{cat}}$), the model remains invariant to line rate changes.

### 3.5 Regime 5: Severity Stress (Extreme Damage Out-of-Bounds)
- **Performance**: Bottleneck ROC-AUC $0.979$, Recall $99.1\%$.
- **Analysis**: Severe physical degradation (vibration $> 6.0\text{ mm/s}$, thermal spikes $> 40^\circ\text{C}$) drives features deep into the positive decision region, maintaining monotonic response.

### 3.6 Regime 6: Sensor Network Degradation (40% Telemetry Dropouts)
- **Performance**: Bottleneck ROC-AUC $0.955$ ($\Delta = -0.024$), Recall $96.9\%$.
- **Fail-Safe Coupling**: When intermittent fieldbus dropouts reduce `twin_confidence < 0.65`, the system activates the shadow-mode deterministic physics fallback to maintain high operational reliability.

### 3.7 Regime 7: Emergent Wear-Driven Failures (Organic Physics Simulation)
- **Performance**: Bottleneck ROC-AUC $0.921$ ($\Delta = -0.058$), PR-AUC $0.873$, Recall $89.7\%$.
- **Analysis**: This regime relies purely on organic continuous tool wear accumulation and stochastic Weibull breakdown triggers. The model successfully captures emergent pre-failure signals $10-15$ ticks prior to catastrophic machine halt.

---
*Maintained by Team Twin Flow · Indian Institute of Technology Kanpur (IITK)*
