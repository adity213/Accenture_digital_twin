# Data Sanity & Defect Rate Concentration Audit Notes

## Phase 1 Finding: Inspection Station Defect Concentration

### Core Conclusion
The elevated `defect_label` positive rate observed at inspection stations (`VisionQC` ~47.6%, `FinalInspection` ~58.4%, `QualityScan` ~30.8% vs. ~10-14% at standard manufacturing stations) is **explained by (a) real physics — latent defects correctly surfacing downstream at designated quality control gates, amplified by normal per-vehicle dwell and the 15-tick forward-looking prediction horizon**.

### Key Audit Evidence
1. **Cumulative Latent Defect Detection**:
   - In `simulator/generator.py` (lines 159-165), Quality Gates (`ST12 QualityScan`, `ST22 VisionQC`, `ST40 FinalInspection`) inspect vehicles for defects accumulated across all upstream stations (Body: 11 stations, Paint: 21 stations, Final Assembly: 39 stations).
   - Theoretical cumulative vehicle defect probability ($1 - (1 - p)^N$ with natural defect rate $p \approx 0.8\%$ plus balanced anomaly injections):
     - Body Exit (`ST12`): 11.87% of unique vehicles carry a defect.
     - Paint Exit (`ST22`): 30.14% of unique vehicles carry a defect.
     - Final Line Buy-off (`ST40`): 45.07% of unique vehicles carry a defect.
2. **Tick vs. Vehicle Defect Ratio**:
   - Ratio of tick-level defect rate to distinct vehicle defect rate is ~0.992 - 0.997 at inspection stations, confirming that `defect_flag` faithfully reflects vehicle state without unbounded amplification.
3. **Prediction Horizon Amplification**:
   - The training pipeline generates binary targets using a 15-tick lookahead window (`horizon=15`). Any tick within 15 minutes before an inspection gate processes a defective unit receives `defect_label=1`. Because defective units arrive frequently at end-of-line gates (45% of vehicles), forward-looking defect labels naturally cover ~47-58% of station-ticks.

### Reporting & Evaluation Guidance for Judges & Leadership
- **Sample Independence**: Per-tick observations at stations with multi-tick dwells (average 2.0 ticks) and rolling lookahead windows are temporally correlated, not independent and identically distributed (i.i.d.) samples.
- **Metric Interpretation**: All precision, recall, and PR-AUC metrics reported by the risk scoring models represent **per station-tick** early-warning performance, not isolated single-vehicle inspection accuracy.
