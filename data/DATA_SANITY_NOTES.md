# DigitalTwin.ai: Data Sanity and Model Evaluation Notes

**Date:** 2026-08-28  
**Audit Script:** `scripts/audit_defect_rate_concentration.py`  
**Dataset:** `data/training_dataset.csv` (8 seeds, 32,000 ticks, 1,280,000 observations)  
**Trained Model:** `data/risk_model.joblib`

---

## 1. Defect Label Concentration

**Question:** Why do inspection stations (ST12 QualityScan, ST22 VisionQC, ST40 FinalInspection) show higher positive defect rates (28.7% to 55.7%) than upstream machining stations? Is this a bug in data generation?

**Answer:** No. Upstream machining and welding cells introduce flaws (porosity, scratches, undertorque) that do not stop the carrier immediately. These flaws travel downstream with the vehicle until they hit an inspection gate designed to catch them. Dwell time at inspection stations is identical to other stations (~2.0 ticks per car), confirming this pattern reflects line defect accumulation rather than a simulation timing bug.

---

## 2. Bottleneck vs. Defect Model Performance

| Task | ROC-AUC | PR-AUC | Precision | Recall | Target Positive Rate | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Bottleneck Risk** | **0.932** | **0.826** | **97.3%** | **83.2%** | 0.85% | Production Ready. Reliable across all zones and sensor tiers. |
| **Defect Precursor** | **0.601** | **0.289** | **43.4%** | **23.2%** | 13.81% | Advisory Only. Catches roughly 1 in 4 defect precursor events. |

> [!WARNING]
> **Defect Model Status:**
> The defect model catches only 23.2% of defect precursors. It is labeled as an **advisory signal** in the leadership screens and SOP recommendations. The bottleneck model should be trusted for line pacing and stoppage avoidance; defect predictions are rough indicators.

---

## 3. Distribution Shifts and Test Set Variations

### A. Precision Spreads Across OOD Scenarios
Across the 6 scenario benchmarks in `docs/SCENARIO_VALIDATION_REPORT.md`, Precision ranges from 4.9% (Compound Faults) to 98.4% (Spatial OOD):
- This variation comes from **prevalence shift** (the different proportion of positive cases across synthetic test sets), not erratic model ranking.
- In dense anomaly scenarios, precision is high. In sparse scenarios, precision naturally drops. Across all regimes, ROC-AUC remains steady between 0.920 and 0.939, and Recall stays between 84.4% and 86.8%.

### B. Missing Telemetry and Confidence Downgrade
When 40% of sensor telemetry is dropped, model ROC-AUC falls to 0.701 (Recall: 52.2%):
- When `sensor_confidence < 65%`, the system displays a **DEGRADED VISIBILITY** status in the interface and forces Step 1 of the SOP to require a manual physical check rather than trusting automated predictions.

---

## 4. Evaluation Semantics

> [!IMPORTANT]
> **Station-Tick vs. Vehicle Independence:**
> Each dataset row is a single station-tick (1Hz sample). Because cars spend ~2 ticks inside each station, consecutive ticks during the same visit share quality state.
> 
> All reported Precision, Recall, and AUC figures are computed **per station-tick**. Recall measures whether the model detects a disruption occurring within the forward 15-tick window at that station.
