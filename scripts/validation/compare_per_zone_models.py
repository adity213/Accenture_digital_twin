"""
Phase 3 — Per-Zone Modeling Evaluation Script
Compares:
(a) Single global model with zone/station_type features
(b) 3 separate dedicated models trained per zone (Body, Paint, Assembly)
Evaluates per-zone precision and recall on the held-out test seed.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.risk_model import RiskScoringModel, FEATURE_NAMES


def load_dataset(path: str):
    rows: List[Dict[str, Any]] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def main():
    rows = load_dataset("data/training_dataset.csv")
    if not rows:
        print("No training dataset found.")
        return

    test_seed = "1005"
    feature_cols = FEATURE_NAMES

    train_rows = [r for r in rows if r["seed"] != test_seed]
    test_rows = [r for r in rows if r["seed"] == test_seed]

    print(f"[eval] Train samples: {len(train_rows)}, Held-out test samples: {len(test_rows)}")

    # 1. Global Model Evaluation
    global_model = RiskScoringModel()
    X_train = np.asarray([[float(r[c]) for c in feature_cols] for r in train_rows], dtype=np.float32)
    y_train = [int(r["bottleneck_label"]) for r in train_rows]
    y_def_train = [int(r["defect_label"]) for r in train_rows]

    X_test = np.asarray([[float(r[c]) for c in feature_cols] for r in test_rows], dtype=np.float32)
    y_test = [int(r["bottleneck_label"]) for r in test_rows]
    y_def_test = [int(r["defect_label"]) for r in test_rows]

    global_metrics = global_model.train_on_history(
        X_train, y_train, y_def_train,
        train_idx=list(range(len(train_rows))),
        test_idx=list(range(len(test_rows))),
        decision_threshold=0.5
    )

    global_probs = global_model.bottleneck_model.predict_proba(X_test)[:, 1]

    # Evaluate Global Model by Zone
    zones = ["Body", "Paint", "Assembly"]
    print("\n" + "="*70)
    print(" (a) GLOBAL MODEL WITH ZONE/STATION_TYPE FEATURES")
    print("="*70)
    for z in zones:
        z_idx = [i for i, r in enumerate(test_rows) if r["zone"] == z]
        z_y = [y_test[i] for i in z_idx]
        z_probs = [global_probs[i] for i in z_idx]
        z_preds = [1 if p >= 0.5 else 0 for p in z_probs]
        tp = sum(1 for p, y in zip(z_preds, z_y) if p == 1 and y == 1)
        fp = sum(1 for p, y in zip(z_preds, z_y) if p == 1 and y == 0)
        fn = sum(1 for p, y in zip(z_preds, z_y) if p == 0 and y == 1)
        pos = sum(z_y)
        prec = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = (tp / pos) if pos > 0 else 0.0
        print(f"   Zone {z:10s} -> Positives={pos:4d} | Caught={tp:4d} | Precision={prec*100:5.1f}% | Recall={rec*100:5.1f}%")

    # 2. Per-Zone Dedicated Models Evaluation
    print("\n" + "="*70)
    print(" (b) 3 SEPARATE DEDICATED PER-ZONE MODELS")
    print("="*70)
    for z in zones:
        z_train = [r for r in train_rows if r["zone"] == z]
        z_test = [r for r in test_rows if r["zone"] == z]

        z_X_train = np.asarray([[float(r[c]) for c in feature_cols] for r in z_train], dtype=np.float32)
        z_y_train = [int(r["bottleneck_label"]) for r in z_train]
        z_y_def_train = [int(r["defect_label"]) for r in z_train]

        z_X_test = np.asarray([[float(r[c]) for c in feature_cols] for r in z_test], dtype=np.float32)
        z_y_test = [int(r["bottleneck_label"]) for r in z_test]
        z_y_def_test = [int(r["defect_label"]) for r in z_test]

        zone_model = RiskScoringModel()
        zone_model.train_on_history(
            z_X_train, z_y_train, z_y_def_train,
            train_idx=list(range(len(z_train))),
            test_idx=list(range(len(z_test))),
            decision_threshold=0.5
        )
        z_probs = zone_model.bottleneck_model.predict_proba(z_X_test)[:, 1]
        z_preds = [1 if p >= 0.5 else 0 for p in z_probs]

        tp = sum(1 for p, y in zip(z_preds, z_y_test) if p == 1 and y == 1)
        fp = sum(1 for p, y in zip(z_preds, z_y_test) if p == 1 and y == 0)
        fn = sum(1 for p, y in zip(z_preds, z_y_test) if p == 0 and y == 1)
        pos = sum(z_y_test)
        prec = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = (tp / pos) if pos > 0 else 0.0
        print(f"   Zone {z:10s} -> Positives={pos:4d} | Caught={tp:4d} | Precision={prec*100:5.1f}% | Recall={rec*100:5.1f}%")

    print("="*70 + "\n")


if __name__ == "__main__":
    main()
