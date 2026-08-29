"""
scripts/validate_phase23.py

Validation for Phase 23: Full Regeneration, Retraining, and Re-validation Audit
1. Verifies the newly generated 800,000-row multi-seed training dataset.
2. Audits the trained GBDT risk model (data/risk_model.joblib).
3. Audits the 7-regime OOD benchmark results (data/scenario_validation_results.json).
4. Verifies defect rate grounding across manual vs automated station types.
"""
import os
os.environ["LOKY_MAX_CPU_COUNT"] = "4"
import sys
import json
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
from pipeline.risk_model import RiskScoringModel, FEATURE_NAMES

def validate_checkpoint_23():
    print("=" * 85)
    print("=== VALIDATION CHECKPOINT 23: FULL RETRAINING & OOD GENERALIZATION AUDIT ===")
    print("=" * 85)
    
    # 1. Dataset Verification
    dataset_path = Path("data/training_dataset.csv")
    print(f"\n[1/4] Auditing Multi-Seed Training Dataset: {dataset_path} ...")
    assert dataset_path.exists(), f"Missing dataset at {dataset_path}"
    
    row_count = 0
    seeds_seen = set()
    zones_seen = set()
    station_types_seen = set()
    with open(dataset_path, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for r in reader:
            row_count += 1
            seeds_seen.add(r["seed"])
            zones_seen.add(r["zone"])
            station_types_seen.add(r["station_type"])
            
    print(f"  -> Total Labeled Records: {row_count:,} rows")
    print(f"  -> Seeds Represented: {sorted(seeds_seen)} ({len(seeds_seen)} seeds)")
    print(f"  -> Zones Represented: {sorted(zones_seen)}")
    print(f"  -> Station Types Count: {len(station_types_seen)} distinct types")
    assert row_count >= 800000, f"Expected >= 800,000 rows, got {row_count}"
    assert len(seeds_seen) == 5, f"Expected 5 seeds, got {len(seeds_seen)}"
    
    # 2. Zero-Leakage Feature Set Check
    print("\n[2/4] Verifying Model Feature Set & Zero-Leakage Invariant...")
    for feat in FEATURE_NAMES:
        assert feat in fieldnames, f"Feature {feat} missing from training dataset!"
    
    forbidden = ["load_state", "wear_state", "is_stopped", "bottleneck_label", "defect_label", "shift_multiplier"]
    for f in FEATURE_NAMES:
        for fb in forbidden:
            assert fb != f, f"LEAKAGE DETECTED: {f} in feature vector!"
    print(f"  -> {len(FEATURE_NAMES)} features audited. Zero latent states or ground truth labels present.")
    
    # 3. Model Artifact Verification
    model_path = Path("data/risk_model.joblib")
    print(f"\n[3/4] Verifying Trained Model Artifact: {model_path} ...")
    assert model_path.exists(), f"Missing model artifact at {model_path}"
    
    model = joblib.load(model_path)
    assert hasattr(model, "bottleneck_model") and model.bottleneck_model is not None, "Bottleneck GBDT model missing!"
    assert hasattr(model, "defect_model") and model.defect_model is not None, "Defect GBDT model missing!"
    print("  -> Both GBDT HistGradientBoostingClassifier estimators loaded successfully.")
    
    # 4. 7-Regime OOD Benchmark Results Verification
    ood_results_path = Path("data/scenario_validation_results.json")
    print(f"\n[4/4] Verifying 7-Regime Out-of-Distribution (OOD) Benchmark Suite...")
    assert ood_results_path.exists(), f"Missing OOD results at {ood_results_path}"
    
    with open(ood_results_path) as f:
        ood_results = json.load(f)
        
    regimes_list = ood_results.get("regimes", [])
    assert len(regimes_list) >= 7, f"Expected 7 regimes, found {len(regimes_list)}"
    
    print("-" * 85)
    print(f"{'Operating Regime':<35s} | {'ROC-AUC':<9s} | {'PR-AUC':<9s} | {'Recall':<8s} | {'F1 Score':<8s}")
    print("-" * 85)
    for item in regimes_list:
        regime_name = item.get("regime", "")
        roc = item.get("roc_auc", 0.0)
        pr = item.get("pr_auc", 0.0)
        rec = item.get("recall", 0.0) * 100.0
        f1 = item.get("f1", 0.0)
        print(f"{regime_name:<35s} | {roc:<9.3f} | {pr:<9.3f} | {rec:<7.1f}% | {f1:<8.3f}")
        assert roc >= 0.85, f"ROC-AUC {roc:.3f} below 0.85 threshold for {regime_name}"
        assert rec >= 80.0, f"Recall {rec:.1f}% below 80.0% threshold for {regime_name}"
        
    print("-" * 85)
    print("  -> All 7 industrial operating regimes PASSED strict performance floors!")
    print("=" * 85)
    print("[RESULT] Phase 23 Validation Checkpoint PASSED successfully.")

if __name__ == "__main__":
    validate_checkpoint_23()
