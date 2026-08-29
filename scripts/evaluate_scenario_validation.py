"""
DigitalTwin.ai - Scenario-Based & Out-of-Distribution (OOD) Validation Suite

Systematically evaluates model generalization across 6 industrial operating regimes:
1. Baseline I.I.D. (Standard within-distribution split)
2. Spatial OOD (Cross-Station: Train ST01-ST30 -> Test ST31-ST40)
3. Phenomenological OOD (Cross-Anomaly: Train Isolated -> Test Compound Drift+Energy)
4. Operational Speed Stress (+20% Takt Acceleration)
5. Severity Stress (Non-linear Extreme Physical Degradation)
6. Sensor Network Degradation Stress (40% Telemetry Dropouts)

Outputs:
- Rich comparative summary table to stdout
- Machine-readable JSON results at data/scenario_validation_results.json
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.risk_model import RiskScoringModel, FEATURE_NAMES


def load_dataset_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Scenario dataset missing at: {path}")
    rows: List[Dict[str, Any]] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def parse_features_and_labels(rows: List[Dict[str, Any]]) -> Tuple[np.ndarray, List[int], List[int]]:
    X = np.asarray([[float(r[c]) for c in FEATURE_NAMES] for r in rows], dtype=np.float32)
    y_bn = [int(r["bottleneck_label"]) for r in rows]
    y_def = [int(r["defect_label"]) for r in rows]
    return X, y_bn, y_def


def evaluate_regime(
    model: RiskScoringModel,
    X_test: np.ndarray,
    y_test: List[int],
    regime_name: str,
    regime_desc: str,
    threshold: float = 0.50,
) -> Dict[str, Any]:
    metrics = model._evaluate(model.bottleneck_model, X_test, y_test, threshold=threshold)
    pos_count = sum(y_test)
    total_count = len(y_test)
    pos_rate = round(pos_count / max(1, total_count), 4)

    return {
        "regime": regime_name,
        "description": regime_desc,
        "test_samples": total_count,
        "positives": pos_count,
        "positive_rate": pos_rate,
        "roc_auc": metrics["auc"],
        "pr_auc": metrics["pr_auc"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "brier_score": metrics["brier_score"],
        "false_alarm_rate": metrics["false_alarm_rate"],
    }


def main():
    ap = argparse.ArgumentParser(description="Run Scenario-Based & OOD Validation Suite")
    ap.add_argument("--data-dir", default="data/scenarios")
    ap.add_argument("--out-json", default="data/scenario_validation_results.json")
    ap.add_argument("--threshold", type=float, default=0.50)
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"[eval] Error: scenarios directory {data_dir} does not exist. Run scripts/generate_scenario_datasets.py first.")
        sys.exit(1)

    print("=" * 88)
    print(" DIGITALTWIN.AI -- PREDICTIVE RISK MODEL SCENARIO & OOD VALIDATION BENCHMARK")
    print("=" * 88)
    print(f"Loading scenario partitions from: {data_dir.resolve()}\n")

    results: List[Dict[str, Any]] = []

    # ---------------------------------------------------------------------------------
    # REGIME 1: Baseline I.I.D. (Standard 70/30 split on nominal 40-station data)
    # ---------------------------------------------------------------------------------
    print("[1/6] Evaluating Baseline I.I.D. (Within-Distribution Split)...")
    iid_rows = load_dataset_rows(data_dir / "baseline_iid.csv")
    X_iid, y_bn_iid, y_def_iid = parse_features_and_labels(iid_rows)
    split_idx = int(len(X_iid) * 0.70)

    X_iid_train, X_iid_test = X_iid[:split_idx], X_iid[split_idx:]
    y_bn_iid_train, y_bn_iid_test = y_bn_iid[:split_idx], y_bn_iid[split_idx:]
    y_def_iid_train, _ = y_def_iid[:split_idx], y_def_iid[split_idx:]

    model_iid = RiskScoringModel()
    model_iid.train_on_history(
        X_iid.tolist(), y_bn_iid, y_def_iid,
        train_idx=list(range(split_idx)),
        test_idx=list(range(split_idx, len(X_iid))),
        decision_threshold=args.threshold,
    )
    res_iid = evaluate_regime(
        model_iid, X_iid_test, y_bn_iid_test,
        regime_name="1. Baseline I.I.D.",
        regime_desc="70/30 random slice across all 40 stations with nominal conditions",
        threshold=args.threshold,
    )
    results.append(res_iid)

    # ---------------------------------------------------------------------------------
    # REGIME 2: Spatial OOD (Cross-Station: Train ST01-ST30 -> Test ST31-ST40)
    # ---------------------------------------------------------------------------------
    print("[2/6] Evaluating Spatial OOD (Cross-Station: Train ST01-ST30 -> Test ST31-ST40)...")
    spatial_train_rows = load_dataset_rows(data_dir / "train_spatial_st01_st30.csv")
    spatial_test_rows = load_dataset_rows(data_dir / "test_spatial_st31_st40.csv")

    X_sp_train, y_bn_sp_train, y_def_sp_train = parse_features_and_labels(spatial_train_rows)
    X_sp_test, y_bn_sp_test, _ = parse_features_and_labels(spatial_test_rows)

    model_spatial = RiskScoringModel()
    # Train strictly on ST01-ST30
    model_spatial.train_on_history(
        X_sp_train.tolist(), y_bn_sp_train, y_def_sp_train,
        train_idx=list(range(len(X_sp_train))),
        test_idx=list(range(len(X_sp_train))), # dummy test for fit
        decision_threshold=args.threshold,
    )
    res_spatial = evaluate_regime(
        model_spatial, X_sp_test, y_bn_sp_test,
        regime_name="2. Spatial OOD (Cross-Station)",
        regime_desc="Trained on ST01-ST30; zero-shot evaluation on unseen ST31-ST40",
        threshold=args.threshold,
    )
    results.append(res_spatial)

    # ---------------------------------------------------------------------------------
    # REGIME 3: Phenomenological OOD (Cross-Anomaly: Train Isolated -> Test Compound)
    # ---------------------------------------------------------------------------------
    print("[3/6] Evaluating Phenomenological OOD (Train Isolated -> Test Compound Multi-Faults)...")
    isolated_train_rows = load_dataset_rows(data_dir / "train_isolated_anomalies.csv")
    compound_test_rows = load_dataset_rows(data_dir / "test_compound_anomalies.csv")

    X_iso_train, y_bn_iso_train, y_def_iso_train = parse_features_and_labels(isolated_train_rows)
    X_comp_test, y_bn_comp_test, _ = parse_features_and_labels(compound_test_rows)

    model_compound = RiskScoringModel()
    model_compound.train_on_history(
        X_iso_train.tolist(), y_bn_iso_train, y_def_iso_train,
        train_idx=list(range(len(X_iso_train))),
        test_idx=list(range(len(X_iso_train))),
        decision_threshold=args.threshold,
    )
    res_compound = evaluate_regime(
        model_compound, X_comp_test, y_bn_comp_test,
        regime_name="3. Symptom OOD (Compound Faults)",
        regime_desc="Trained on single faults; tested on compound drift + motor surge",
        threshold=args.threshold,
    )
    results.append(res_compound)

    # ---------------------------------------------------------------------------------
    # REGIME 4: Operational Speed Stress (+20% Takt Acceleration)
    # ---------------------------------------------------------------------------------
    print("[4/6] Evaluating Operational Speed Stress (+20% Takt Acceleration)...")
    speed_test_rows = load_dataset_rows(data_dir / "test_speed_stress.csv")
    X_speed_test, y_bn_speed_test, _ = parse_features_and_labels(speed_test_rows)

    res_speed = evaluate_regime(
        model_iid, X_speed_test, y_bn_speed_test,
        regime_name="4. Speed Stress OOD (+20% Takt)",
        regime_desc="Evaluated under +20% accelerated line speed and shortened takt",
        threshold=args.threshold,
    )
    results.append(res_speed)

    # ---------------------------------------------------------------------------------
    # REGIME 5: Severity Stress (Non-linear Extreme Wear Out of Bounds)
    # ---------------------------------------------------------------------------------
    print("[5/6] Evaluating Severity Stress (Extreme Damage Out-of-Bounds)...")
    sev_test_rows = load_dataset_rows(data_dir / "test_severity_stress.csv")
    X_sev_test, y_bn_sev_test, _ = parse_features_and_labels(sev_test_rows)

    res_severity = evaluate_regime(
        model_iid, X_sev_test, y_bn_sev_test,
        regime_name="5. Severity Stress OOD (Extreme)",
        regime_desc="Drift factor up to 1.20 and power surges up to 5.0x outside training bounds",
        threshold=args.threshold,
    )
    results.append(res_severity)

    # ---------------------------------------------------------------------------------
    # REGIME 6: Sensor Network Degradation Stress (40% Telemetry Dropouts)
    # ---------------------------------------------------------------------------------
    print("[6/7] Evaluating Sensor Network Degradation Stress (40% Dropouts)...")
    sensor_test_rows = load_dataset_rows(data_dir / "test_sensor_degraded.csv")
    X_sensor_test, y_bn_sensor_test, _ = parse_features_and_labels(sensor_test_rows)

    res_sensor = evaluate_regime(
        model_iid, X_sensor_test, y_bn_sensor_test,
        regime_name="6. Sensor Degradation Stress (40%)",
        regime_desc="40% stochastic sensor dropouts stressing Virtual Sensor Imputation",
        threshold=args.threshold,
    )
    results.append(res_sensor)

    # ---------------------------------------------------------------------------------
    # REGIME 7: Emergent Wear-Driven Failures (Organic Physics Simulation)
    # ---------------------------------------------------------------------------------
    print("[7/7] Evaluating Emergent Wear-Driven Failures (Organic Physics Simulation)...")
    emergent_test_file = data_dir / "test_emergent_wear.csv"
    if emergent_test_file.exists():
        emergent_test_rows = load_dataset_rows(emergent_test_file)
        X_emergent_test, y_bn_emergent_test, _ = parse_features_and_labels(emergent_test_rows)

        res_emergent = evaluate_regime(
            model_iid, X_emergent_test, y_bn_emergent_test,
            regime_name="7. Emergent Wear Failures (Organic)",
            regime_desc="Emergent mechanical wear accumulation and stochastic unscheduled failures",
            threshold=args.threshold,
        )
        results.append(res_emergent)

    # ---------------------------------------------------------------------------------
    # FORMATTED REPORT TABLE
    # ---------------------------------------------------------------------------------
    header_fmt = "{:<32s} | {:>7s} | {:>7s} | {:>7s} | {:>7s} | {:>6s} | {:>6s} | {:>7s}"
    row_fmt    = "{:<32s} | {:>7.3f} | {:>7.3f} | {:>7.1f}% | {:>7.1f}% | {:>6.3f} | {:>6.4f} | {:>6.2f}%"

    print("\n" + "=" * 98)
    print(" COMPREHENSIVE OUT-OF-DISTRIBUTION (OOD) GENERALIZATION BENCHMARK")
    print("=" * 98)
    print(header_fmt.format(
        "Operating Regime", "ROC-AUC", "PR-AUC", "Prec", "Recall", "F1", "Brier", "FAR"
    ))
    print("-" * 98)

    base_auc = res_iid["roc_auc"]
    base_pr = res_iid["pr_auc"]

    for r in results:
        print(row_fmt.format(
            r["regime"],
            r["roc_auc"],
            r["pr_auc"],
            r["precision"] * 100,
            r["recall"] * 100,
            r["f1"],
            r["brier_score"],
            r["false_alarm_rate"] * 100,
        ))

    print("-" * 98)
    print(" Generalization Gaps (Relative to Baseline I.I.D. ROC-AUC):")
    for r in results[1:]:
        delta_auc = r["roc_auc"] - base_auc
        delta_pr = r["pr_auc"] - base_pr
        sign_auc = "+" if delta_auc >= 0 else ""
        sign_pr = "+" if delta_pr >= 0 else ""
        print(f"   * {r['regime']:<32s}: dROC-AUC = {sign_auc}{delta_auc:.3f} | dPR-AUC = {sign_pr}{delta_pr:.3f} | Recall = {r['recall']*100:.1f}%")
    print("=" * 98)

    # Save JSON summary
    out_json_path = Path(args.out_json)
    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_payload = {
        "status": "success",
        "benchmark_type": "scenario_based_ood_validation",
        "decision_threshold": args.threshold,
        "baseline_auc": base_auc,
        "regimes": results
    }
    with open(out_json_path, "w") as f:
        json.dump(summary_payload, f, indent=2)
    print(f"\n[eval] Saved machine-readable benchmark results -> {out_json_path.resolve()}\n")


if __name__ == "__main__":
    main()
