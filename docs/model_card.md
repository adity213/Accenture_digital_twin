# Model Card: Predictive Risk Scoring Model

## Model Overview
- **Name**: TwinSphere Predictive Risk Scoring Model
- **Version**: 1.0 (Phase 24)
- **Architecture**: Gradient Boosted Decision Tree (GBDT) Ensemble (`HistGradientBoostingClassifier` via `scikit-learn`)
- **Task**: Binary classification for two targets:
  1. Bottleneck Risk: Probability of a station bottleneck forming in the next 15 minutes.
  2. Defect Risk: Probability of a defect being introduced.

## Training Details
- **Features**: 19 features extracted from physical telemetry (e.g., `processing_time_ratio`, `buffer_utilization`, `degradation_momentum`, `spc_z_score`, `machine_shaking_vibration`).
- **Data Leakage Prevention**: Strict zero data leakage policy. Only historical state up to the current tick is used.
- **Handling Imbalance**: Implements class-imbalance-aware sample weighting during training. Bottlenecks and defects are rare events; without weighting, the model would converge to predicting the majority "NORMAL" class. Sample weights are assigned inversely proportional to class frequencies.
- **Decision Threshold**: 0.5

## Shadow-Mode Routing (Phase 25)
The model operates in a shadow-mode router pattern:
1. **Deterministic Baseline**: A physics-grounded heuristic computes baseline risk probabilities based on thresholds (e.g., ISO 10816 vibration limits).
2. **ML Model**: Computes probabilities from the trained GBDT ensemble.
3. **Router**:
   - Compares ML output against the deterministic baseline.
   - If the divergence is too high (e.g., >0.45) or sensor confidence drops below the minimum threshold (e.g., <0.65), it falls back to the deterministic baseline.
   - Otherwise, the ML model predictions are served.

## Performance Metrics
- **Bottleneck AUC**: Evaluated post-training to measure discrimination capability for bottleneck prediction.
- **Defect AUC**: Evaluated post-training to measure discrimination capability for defect prediction.
- *Refer to training logs for specific metrics on evaluation sets.*

## Explainability (Risk Drivers)
GBDT feature contributions are statistical patterns, not mechanical truths. The model calculates risk drivers relative to calibrated nominal baselines, highlighting the top 3 driving features and their influence percentage (e.g., 'Model triggered by: High Vibration (70% influence) + Job Time Deviation (30%)'). These are visualized in the operator cockpit as statistical evidence.
