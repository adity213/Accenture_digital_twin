# 📊 DigitalTwin.ai — Data Sanctity & Model Confidence Notes

**Date:** 2026-08-28  
**Audit Script:** `scripts/audit_defect_rate_concentration.py`  
**Dataset:** `data/training_dataset.csv` (8 seeds, 32,000 ticks, 1,280,000 observations)  
**Trained Artifact:** `data/risk_model.joblib`

---

## 1. Executive Summary & Core Finding

**Question:** Is the elevated `defect_label` rate (28.7%–55.7%) at inspection stations (`QualityScan`, `VisionQC`, `FinalInspection`) explained by (a) real physics — latent defects correctly surfacing there — or (b) a labeling bug?

**Finding:** **(a) Real Physical Defect Accumulation across Line Topology.**  
The concentration of positive defect labels at inspection stations is physically authentic and represents the cumulative detection of upstream latent defects (weld porosity, surface scratches, undertorque) that propagate down the DAG until trapped at end-of-zone inspection gates.

---

## 2. Model Performance Asymmetry: Bottleneck vs. Defect Prediction

| Model Task | ROC-AUC | PR-AUC | Precision | Recall | Target Base Rate | Operational Maturity |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Bottleneck Risk Model** | **0.932** | **0.826** | **97.3%** | **83.2%** | $0.85\%$ | **Production Ready**: High discriminative power across all zones and sensor tiers. |
| **Defect Precursor Model** | **0.601** | **0.289** | **43.4%** | **23.2%** | $13.81\%$ | **Experimental / Advisory Only**: Catches ~1 in 4 defect-precursor events. |

> [!WARNING]
> **Defect Model Confidence Flag:**
> The Defect Prediction Model currently operates with a lower recall (23.2%) and PR-AUC (0.289). It is explicitly designated as an **advisory / lower-confidence signal** in all leadership dashboards and SOP escalation flows. Quality yield forecasts must treat defect risk as an early indicator rather than a deterministic ground truth.

---

## 3. Generalization & Distribution Shift Clarifications

### A. Synthetic OOD Precision Fluctuations (Prevalence Shift)
Across the 6 scenario-based OOD validation benchmarks (`docs/SCENARIO_VALIDATION_REPORT.md`), observed Precision varied from **4.9%** (Compound Faults) to **98.4%** (Spatial OOD):
- **Mechanism**: This precision spread is driven by **prevalence shift** (the varying proportion of positive anomaly ticks in each synthetic evaluation regime), not erratic ranking capability.
- In high-density regimes (Spatial OOD on `ST31–ST40` where positive rate is higher), precision is naturally elevated ($98.4\%$).
- In sparse compound anomaly regimes, precision reflects the lower positive baseline. ROC-AUC ($0.920–0.939$) and Recall ($84.4\%–86.8\%$) remain invariant across all regimes.

### B. Sensor Degradation Shift & Uncertainty Principle
Under extreme 40% telemetry dropouts, model ROC-AUC gracefully degraded to **0.701** (Recall: 52.2%):
- **Core Design Rule**: The `ConfidenceEngine` dynamically tracks data trust. When `sensor_confidence < 65%`, the Digital Twin explicitly flags predictions as **DEGRADED VISIBILITY**, downgrades risk certainty in the SCADA HMI, and triggers Step 1 SOP physical gauge verification before automated actions are recommended.

---

## 4. Methodological Note on Evaluation Interpretation

> [!IMPORTANT]
> **Station-Tick vs. Vehicle-Inspection Independence:**
> In the training dataset, each row represents a single **station-tick** ($1\text{Hz}$ sample). Because vehicles dwell for $2\text{ ticks}$ per station, adjacent ticks during the same vehicle visit share the vehicle's underlying quality state.
> 
> When presenting model evaluation metrics to stakeholders and competition judges:
> - Reported Precision, Recall, PR-AUC, and ROC-AUC are evaluated **per station-tick**.
> - Headline recall represents the model's ability to predict an event occurring within the forward $15\text{-tick}$ ($15\text{s}$) operational window at that specific station.
