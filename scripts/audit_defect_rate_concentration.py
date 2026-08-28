"""
scripts/audit_defect_rate_concentration.py

Phase 1 Audit:
1. Simulates runs & loads data/audit_dataset.csv
2. Audits defect_label positive rate, tick-level defect_flag rate, distinct vehicles with defects
3. Computes average dwell ticks per vehicle across station types (VisionQC, FinalInspection vs non-inspection)
4. Evaluates whether elevated defect rate at inspection stations is explained by:
   (a) real physics (latent defects surfacing downstream + dwell time + 15-tick horizon labeling)
   (b) a labeling/telemetry bug
"""
import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from simulator.generator import LineSimulator
from simulator.anomaly_campaign import generate_balanced_campaign, apply_campaign_event

def run_simulation_trace(seeds: List[int], num_ticks: int = 3000):
    """
    Direct simulation audit to inspect exact defect_flag generation,
    dwell times, and per-vehicle defect propagation.
    """
    stats_by_stype = defaultdict(lambda: {
        "ticks_total": 0,
        "ticks_with_vehicle": 0,
        "ticks_defect_flag_true": 0,
        "dwell_tick_counts": [],
        "vehicles_visited": set(),
        "vehicles_with_defect_flag": set(),
        "vehicles_with_prior_defect": set(),
    })
    
    for seed in seeds:
        sim = LineSimulator(seed=seed)
        topology = sim.topology
        campaign_rng = random.Random(seed * 7919 + 13)
        campaign = generate_balanced_campaign(topology, campaign_rng, num_ticks)
        campaign_by_tick = defaultdict(list)
        for ev in campaign:
            campaign_by_tick[ev["start_tick"]].append(ev)
            
        current_vin_tracking = {}
        dwell_counter = defaultdict(int)
        
        for t in range(1, num_ticks + 1):
            for ev in campaign_by_tick.get(t, []):
                apply_campaign_event(sim.anomaly_mgr, ev)
            step_res = sim.step()
            
            for ev in step_res["events"]:
                sid = ev["station_id"]
                stype = topology["stations"][sid]["station_type"]
                vin = ev.get("vehicle_id") or ev.get("processing_vin")
                defect_flag = ev.get("defect_flag", False)
                is_proc = ev.get("is_processing", False)
                
                s_stat = stats_by_stype[stype]
                s_stat["ticks_total"] += 1
                
                if vin:
                    s_stat["ticks_with_vehicle"] += 1
                    s_stat["vehicles_visited"].add((seed, vin))
                    if defect_flag:
                        s_stat["ticks_defect_flag_true"] += 1
                        s_stat["vehicles_with_defect_flag"].add((seed, vin))
                    
                    # Track dwell
                    if current_vin_tracking.get(sid) == vin:
                        dwell_counter[sid] += 1
                    else:
                        if current_vin_tracking.get(sid) is not None:
                            s_stat["dwell_tick_counts"].append(dwell_counter[sid])
                        current_vin_tracking[sid] = vin
                        dwell_counter[sid] = 1
                else:
                    if current_vin_tracking.get(sid) is not None:
                        s_stat["dwell_tick_counts"].append(dwell_counter[sid])
                        current_vin_tracking[sid] = None
                        dwell_counter[sid] = 0

    return stats_by_stype


def audit_dataset_and_sim(csv_path: str, seeds: List[int] = [1000, 1001, 1002], num_ticks: int = 3000):
    print("==========================================================================================")
    print(f"               PHASE 1 AUDIT: DEFECT-RATE CONCENTRATION AT INSPECTION STATIONS            ")
    print("==========================================================================================\n")
    
    # 1. Load CSV data
    print(f"[1] Loading dataset from {csv_path}...")
    csv_rows_by_stype = defaultdict(list)
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            csv_rows_by_stype[r["station_type"]].append(r)

    # 2. Run simulation trace
    print(f"[2] Running high-fidelity simulation trace across seeds {seeds} ({num_ticks} ticks/seed)...")
    sim_stats = run_simulation_trace(seeds, num_ticks)
    
    print("\n" + "=" * 125)
    print(f"{'Station Type':<18} | {'Rows':<7} | {'Defect Label %':<15} | {'Ticks Defect=T':<15} | {'Unique VINs':<12} | {'VIN Defect %':<13} | {'Avg Dwell':<10} | {'Expected Tick %':<15}")
    print("-" * 125)
    
    for stype in sorted(csv_rows_by_stype.keys()):
        c_rows = csv_rows_by_stype[stype]
        n_rows = len(c_rows)
        pos_labels = sum(1 for r in c_rows if int(r["defect_label"]) == 1)
        defect_label_pct = pos_labels / n_rows * 100.0
        
        s = sim_stats[stype]
        unique_vins = len(s["vehicles_visited"])
        vins_with_defect = len(s["vehicles_with_defect_flag"])
        vin_defect_pct = (vins_with_defect / unique_vins * 100.0) if unique_vins > 0 else 0.0
        ticks_def = s["ticks_defect_flag_true"]
        avg_dwell = np.mean(s["dwell_tick_counts"]) if s["dwell_tick_counts"] else 1.0
        
        # Vehicle defect rate * avg dwell as percentage of total processing ticks
        ticks_with_veh = s["ticks_with_vehicle"]
        tick_defect_rate = (ticks_def / ticks_with_veh * 100.0) if ticks_with_veh > 0 else 0.0
        
        print(f"{stype:<18} | {n_rows:<7} | {defect_label_pct:>13.2f}% | {ticks_def:>14d} | {unique_vins:>12d} | {vin_defect_pct:>11.2f}% | {avg_dwell:>8.2f}t | {tick_defect_rate:>13.2f}%")

    print("\n" + "=" * 100)
    print("PHYSICS & DWELL TIME BREAKDOWN: INSPECTION vs NON-INSPECTION")
    print("=" * 100)
    
    for st in ["VisionQC", "FinalInspection", "QualityScan", "RoboticWeld", "MechanicalTorque", "RoboticSpray"]:
        s = sim_stats[st]
        c_rows = csv_rows_by_stype[st]
        n_rows = len(c_rows)
        pos_labels = sum(1 for r in c_rows if int(r["defect_label"]) == 1)
        defect_label_pct = pos_labels / n_rows * 100.0
        unique_vins = len(s["vehicles_visited"])
        vins_def = len(s["vehicles_with_defect_flag"])
        vin_def_pct = (vins_def / unique_vins * 100.0) if unique_vins > 0 else 0.0
        avg_dwell = np.mean(s["dwell_tick_counts"]) if s["dwell_tick_counts"] else 1.0
        tick_def_pct = (s["ticks_defect_flag_true"] / s["ticks_with_vehicle"] * 100.0) if s["ticks_with_vehicle"] > 0 else 0.0
        
        print(f"\nStation Type: {st}")
        print(f"  - Unique Vehicles Processed: {unique_vins}")
        print(f"  - Vehicles with Defect: {vins_def} ({vin_def_pct:.2f}%)")
        print(f"  - Average Dwell Ticks per Vehicle: {avg_dwell:.2f} ticks")
        print(f"  - Tick-Level Defect Flag Positive Rate (per occupied tick): {tick_def_pct:.2f}%")
        print(f"  - Forward Horizon Defect Label Rate (15-tick horizon in dataset): {defect_label_pct:.2f}%")
        print(f"  - Ratio (Tick Defect Flag Rate / Vehicle Defect Rate): {tick_def_pct / max(0.001, vin_def_pct):.3f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/audit_dataset.csv")
    args = parser.parse_args()
    audit_dataset_and_sim(args.data)
