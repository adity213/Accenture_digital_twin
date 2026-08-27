"""
DigitalTwin.ai - Risk Model Trainer

Consumes the CSV produced by scripts/generate_training_data.py and trains
pipeline.risk_model.RiskScoringModel for real (this is the piece that was
previously never invoked anywhere -- train_on_history() existed but nothing
called it, so api/main.py always ran the untrained heuristic fallback).

Validation strategy: SEED-HELD-OUT, not a trailing 70/30 slice of one run.
Each --seeds run in generate_training_data.py is an independent simulated
day with its own randomized anomaly campaign. Holding out entire seeds for
testing checks whether the model generalizes to anomaly instances it has
never seen the specific timing/severity of, which is a much more honest
test than holding out the tail of the same continuous run it trained on.

Reports, per model (bottleneck / defect):
  - AUC and PR-AUC (PR-AUC matters more here given class imbalance)
  - precision/recall at the default 0.5 threshold
  - recall broken down by zone / sensor_tier / station_type, so you can see
    directly whether the model under-performs on any subgroup (e.g. manual-tier
    stations, where sensor noise is higher, or singleton station types the
    campaign might still under-cover) before you ship it

Usage:
    python scripts/train_risk_model.py --data data/training_dataset.csv \
        --test-seeds 1005 --model-out data/risk_model.joblib
"""
import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import joblib
from pipeline.risk_model import RiskScoringModel, FEATURE_NAMES


def load_dataset(path: str):
    rows: List[Dict[str, Any]] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/training_dataset.csv")
    ap.add_argument("--test-seeds", type=str, default="", help="comma-separated seed values to hold out entirely for testing; if empty, uses the last seed found in the data")
    ap.add_argument("--model-out", default="data/risk_model.joblib")
    ap.add_argument("--threshold", type=float, default=0.5)
    args = ap.parse_args()

    rows = load_dataset(args.data)
    if not rows:
        print("No rows loaded -- run generate_training_data.py first.")
        return

    feature_cols = FEATURE_NAMES

    all_seeds = sorted({r["seed"] for r in rows})
    if args.test_seeds:
        test_seed_set = set(args.test_seeds.split(","))
    else:
        test_seed_set = {all_seeds[-1]}
    print(f"[train] seeds present: {all_seeds}")
    print(f"[train] held-out test seed(s): {sorted(test_seed_set)}")

    features_list: List[List[float]] = []
    bottleneck_labels: List[int] = []
    defect_labels: List[int] = []
    meta_rows: List[Dict[str, Any]] = []  # zone/sensor_tier/station_type for the fairness breakdown

    train_idx: List[int] = []
    test_idx: List[int] = []

    for i, r in enumerate(rows):
        features_list.append([float(r[c]) for c in feature_cols])
        bottleneck_labels.append(int(r["bottleneck_label"]))
        defect_labels.append(int(r["defect_label"]))
        meta_rows.append({"zone": r["zone"], "sensor_tier": r["sensor_tier"], "station_type": r["station_type"]})
        if r["seed"] in test_seed_set:
            test_idx.append(i)
        else:
            train_idx.append(i)

    if not test_idx:
        print("[train] ERROR: no rows matched the held-out seed(s) -- check --test-seeds")
        return
    if not train_idx:
        print("[train] ERROR: no training rows left -- you held out everything")
        return

    model = RiskScoringModel()
    metrics = model.train_on_history(
        features_list, bottleneck_labels, defect_labels,
        train_idx=train_idx, test_idx=test_idx,
        decision_threshold=args.threshold,
    )

    print("\n[train] === Overall metrics (held-out seed test set) ===")
    for k, v in metrics.items():
        print(f"   {k}: {v}")

    # ---- Subgroup recall breakdown on the held-out test set (fairness/robustness check) ----
    def subgroup_recall(key: str):
        X_test_sub = np.asarray([features_list[i] for i in test_idx], dtype=np.float32)
        probs = model.bottleneck_model.predict_proba(X_test_sub)[:, 1]
        by_group: Dict[str, List[int]] = defaultdict(lambda: [0, 0])  # [true_positives_caught, total_positives]
        for local_i, global_i in enumerate(test_idx):
            group = meta_rows[global_i][key]
            label = bottleneck_labels[global_i]
            pred = 1 if probs[local_i] >= args.threshold else 0
            if label == 1:
                by_group[group][1] += 1
                if pred == 1:
                    by_group[group][0] += 1
        print(f"\n[fairness] bottleneck recall by {key} (held-out test set):")
        for g, (caught, total) in sorted(by_group.items()):
            if total == 0:
                print(f"   {g:16s} no positives in test set -- cannot evaluate recall here")
            else:
                print(f"   {g:16s} recall={100*caught/total:5.1f}%  ({caught}/{total} caught)")

    subgroup_recall("zone")
    subgroup_recall("sensor_tier")
    subgroup_recall("station_type")

    out_path = Path(args.model_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_path)
    print(f"\n[train] saved trained model -> {out_path}")
    print(
        "\n[integrate] In api/main.py, replace `risk_model = RiskScoringModel()` with a "
        "load-if-present pattern, e.g.:\n"
        "    import joblib, os\n"
        "    _MODEL_PATH = 'data/risk_model.joblib'\n"
        "    risk_model = joblib.load(_MODEL_PATH) if os.path.exists(_MODEL_PATH) else RiskScoringModel()\n"
        "so the API serves the trained GBDT instead of always falling back to the heuristic. "
        "Also fix upstream_risks=[] in process_simulation_tick() (see Phase 1.1) -- a model "
        "trained on real upstream-risk values and served with hardcoded zeros for those two "
        "features will underperform live relative to these offline numbers."
    )


if __name__ == "__main__":
    main()
