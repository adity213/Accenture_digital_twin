"""
Phase 6 — Virtual Sensor Imputation Audit & Error Bounds Evaluation
Runs the simulator for 1,000 ticks, artificially drops station telemetry,
and computes MAE, RMSE, and Max Absolute Error across Sensor Tiers (rich vs manual).
Asserts physical plausibility bounds across all 40 stations.
"""
import sys
import random
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.generator import LineSimulator
from pipeline.virtual_sensor import VirtualSensorEngine


def main():
    sim = LineSimulator(seed=1042)
    topology = sim.topology
    stations_meta = topology["stations"]
    vs_engine = VirtualSensorEngine(stations_meta)

    num_ticks = 1000
    mask_rate = 0.25  # 25% synthetic dropout

    errors_by_tier = defaultdict(list)
    errors_by_station = defaultdict(list)
    max_abs_errors = defaultdict(float)
    bound_violations = 0

    rng = random.Random(999)

    for t in range(1, num_ticks + 1):
        tick_res = sim.step()
        events = tick_res["events"]
        event_map = {e["station_id"]: e for e in events}

        # Select subset of stations to mask
        for sid, meta in stations_meta.items():
            if rng.random() < mask_rate:
                actual_ev = event_map.get(sid, {})
                actual_ct = actual_ev.get("cycle_time_s")
                if actual_ct is None:
                    continue

                # Run virtual sensor imputation
                imputed = vs_engine.impute_station_telemetry(sid, t, event_map)
                pred_ct = imputed["imputed_cycle_time_s"]
                err = abs(pred_ct - actual_ct)
                
                tier = meta["sensor_tier"]
                errors_by_tier[tier].append(err)
                errors_by_station[sid].append(err)
                if err > max_abs_errors[sid]:
                    max_abs_errors[sid] = err

                # Physical Bounds Check
                target_ct = meta["target_cycle_time_s"]
                if pred_ct <= 0 or pred_ct > (target_ct * 2.5):
                    bound_violations += 1

    print("\n" + "="*80)
    print(" VIRTUAL SENSOR IMPUTATION ACCURACY & ERROR BOUNDS REPORT (1,000 Ticks)")
    print("="*80)
    print(f"{'Sensor Tier':<16} | {'Samples':<10} | {'MAE (s)':<10} | {'RMSE (s)':<10} | {'Max Error (s)':<14} | {'Target Error %'}")
    print("-" * 80)

    for tier, errs in errors_by_tier.items():
        arr = np.array(errs)
        mae = np.mean(arr)
        rmse = np.sqrt(np.mean(arr**2))
        max_err = np.max(arr)
        # Average target cycle time in this tier
        tier_stations = [s for s in stations_meta.values() if s["sensor_tier"] == tier]
        avg_target = sum(s["target_cycle_time_s"] for s in tier_stations) / len(tier_stations)
        rel_err = (mae / avg_target) * 100.0

        print(f"{tier:<16} | {len(errs):<10} | {mae:<10.3f} | {rmse:<10.3f} | {max_err:<14.3f} | {rel_err:<10.2f}%")

    print("="*80)
    print(f" Physical Bounds Violations (pred <= 0 or pred > 2.5x target): {bound_violations}")
    print(f" Status: {'VALIDATED (ALL 40 STATIONS WITHIN SAFE BOUNDS)' if bound_violations == 0 else 'FAILED'}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
