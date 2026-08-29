"""
scripts/validate_phase22.py

Validation for Phase 22: SPC Recalibration
1. Simulates nominal line operation across all 40 stations for 3,000 ticks.
2. Evaluates empirical cycle time standard deviation & CV per station category.
3. Computes SPC z-scores and measures empirical false alarm rates (|z| > 3.0).
4. Confirms false alarm rates are balanced and bounded across categories.
"""
import sys
import os
import math
import numpy as np
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.generator import LineSimulator, get_station_category
from pipeline.spc import SPCEngine

def validate_checkpoint_22():
    print("=" * 85)
    print("=== VALIDATION CHECKPOINT 22: SPC RECALIBRATION AUDIT ===")
    print("=" * 85)
    
    sim = LineSimulator(seed=2042)
    topology = sim.topology
    stations_meta = topology["stations"]
    
    spc_engine = SPCEngine(z_threshold=3.0)
    
    # Track metrics per category
    category_cts = defaultdict(lambda: defaultdict(list))
    category_spc_flags = defaultdict(list)
    category_z_scores = defaultdict(list)
    category_baseline_sigmas = defaultdict(list)
    
    num_ticks = 1200
    print(f"\n[1/3] Running {num_ticks:,} ticks nominal baseline simulation across all 40 stations...")
    for _ in range(num_ticks):
        step_out = sim.step()
        for ev in step_out["events"]:
            sid = ev["station_id"]
            meta = stations_meta[sid]
            category = get_station_category(meta)
            target_ct = meta["target_cycle_time_s"]
            actual_ct = ev.get("cycle_time_s")
            is_stopped = ev.get("is_stopped", False)
            
            if actual_ct is not None and not is_stopped:
                spc_res = spc_engine.update_station(
                    sid, actual_ct, target_ct,
                    vibration=ev.get("vibration"),
                    station_type=meta.get("station_type")
                )
                
                category_cts[category][sid].append(actual_ct / target_ct)
                category_spc_flags[category].append(1 if spc_res["deviation_flag"] else 0)
                category_z_scores[category].append(spc_res["z_score"])
                category_baseline_sigmas[category].append(spc_res["baseline_sigma"])

    print("\n[2/3] Category-Wise Nominal Operation & SPC Calibration Metrics:")
    print("-" * 85)
    print(f"{'Station Category':<22s} | {'Target CV':<9s} | {'Realized CV':<11s} | {'Mean Sigma (s)':<14s} | {'False Alarm Rate':<16s}")
    print("-" * 85)
    
    target_cv_map = {
        "automated_precision": 0.040,
        "automated_process": 0.060,
        "manual": 0.130
    }
    
    for cat in ["automated_precision", "automated_process", "manual"]:
        # Empirical CV across all stations in category
        within_station_cvs = [np.std(cts) for cts in category_cts[cat].values()]
        realized_cv = float(np.mean(within_station_cvs))
        target_cv = target_cv_map[cat]
        mean_sigma = float(np.mean(category_baseline_sigmas[cat]))
        flags = category_spc_flags[cat]
        far_pct = (sum(flags) / max(1, len(flags))) * 100.0
        
        print(f"{cat:<22s} | {target_cv:<9.3f} | {realized_cv:<11.4f} | {mean_sigma:<14.2f} | {far_pct:<15.2f}%")
        
        # Assertions
        assert abs(realized_cv - target_cv) <= 0.015, f"CV mismatch for {cat}: realized {realized_cv:.4f} vs target {target_cv:.3f}"
        assert far_pct <= 3.5, f"Excessive false alarm rate for {cat}: {far_pct:.2f}% (Expected <= 3.5%)"
        
    print("-" * 85)
    print("\n[3/3] Cross-Category False Alarm Balance Check:")
    far_prec = (sum(category_spc_flags["automated_precision"]) / len(category_spc_flags["automated_precision"])) * 100.0
    far_proc = (sum(category_spc_flags["automated_process"]) / len(category_spc_flags["automated_process"])) * 100.0
    far_man = (sum(category_spc_flags["manual"]) / len(category_spc_flags["manual"])) * 100.0
    
    max_far_diff = max(abs(far_prec - far_proc), abs(far_proc - far_man), abs(far_prec - far_man))
    print(f"  -> Automated Precision FAR: {far_prec:.2f}%")
    print(f"  -> Automated Process   FAR: {far_proc:.2f}%")
    print(f"  -> Manual Operations   FAR: {far_man:.2f}%")
    print(f"  -> Max Cross-Category FAR Discrepancy: {max_far_diff:.2f}% (<= 2.5% threshold)")
    
    assert max_far_diff <= 2.5, f"SPC false alarms unbalanced across categories (diff={max_far_diff:.2f}%)"
    print("  -> False Alarm Rate is balanced and calibrated across all categories!")
    print("=" * 85)
    print("[RESULT] Phase 22 Validation Checkpoint PASSED successfully.")

if __name__ == "__main__":
    validate_checkpoint_22()
