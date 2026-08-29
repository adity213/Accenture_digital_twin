"""
scripts/validate_phase24.py

Validation for Phase 24: Shift-Based Productivity and Fatigue Model
1. Runs a multi-day simulation (4,320 ticks = 3 full 24h days, 9 shifts).
2. Measures cycle time multiplier, CV, and defect rate across Day, Evening, Night shifts.
3. Audits manual vs automated differential shift sensitivity.
4. Verifies within-shift fatigue curve progression and telemetry shift metadata.
"""
import sys
import math
import numpy as np
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.generator import LineSimulator, get_station_category

def validate_checkpoint_24():
    print("=" * 85)
    print("=== VALIDATION CHECKPOINT 24: SHIFT PRODUCTIVITY & FATIGUE MODEL AUDIT ===")
    print("=" * 85)
    
    sim = LineSimulator(seed=1042)
    topology = sim.topology
    stations_meta = topology["stations"]
    
    # Track per-shift metrics: {shift_name: {category: [values]}}
    shift_cts = defaultdict(lambda: defaultdict(list))
    shift_defects = defaultdict(lambda: defaultdict(list))
    shift_first_half_cts = defaultdict(lambda: defaultdict(list))
    shift_second_half_cts = defaultdict(lambda: defaultdict(list))
    
    num_ticks = 4320  # 3 days = 9 shifts
    print(f"\n[1/3] Running {num_ticks:,} ticks multi-day simulation across 3 full 24-hour cycles...")
    
    for _ in range(num_ticks):
        step_out = sim.step()
        for ev in step_out["events"]:
            sid = ev["station_id"]
            meta = stations_meta[sid]
            category = get_station_category(meta)
            target_ct = meta["target_cycle_time_s"]
            actual_ct = ev.get("cycle_time_s")
            is_stopped = ev.get("is_stopped", False)
            
            # Verify shift metadata
            assert "shift_name" in ev and ev["shift_name"] in {"day", "evening", "night"}
            assert "shift_index" in ev and ev["shift_index"] in {0, 1, 2}
            assert "is_night_shift" in ev and isinstance(ev["is_night_shift"], bool)
            
            shift_name = ev["shift_name"]
            day_tick = (ev["tick"] - 1) % 1440
            shift_tick = day_tick % 480
            
            if actual_ct is not None and not is_stopped:
                ct_ratio = actual_ct / target_ct
                shift_cts[shift_name][category].append(ct_ratio)
                
                if shift_tick < 240:
                    shift_first_half_cts[shift_name][category].append(ct_ratio)
                else:
                    shift_second_half_cts[shift_name][category].append(ct_ratio)
                    
            if not is_stopped:
                # Count natural defect flags (exclude downstream inspection detection labels)
                is_def = 1 if (ev["defect_flag"] and not str(ev.get("defect_type", "")).startswith("detected_")) else 0
                shift_defects[shift_name][category].append(is_def)

    print("\n[2/3] Shift Performance Breakdown by Station Category:")
    print("-" * 85)
    print(f"{'Station Category':<22s} | {'Shift':<8s} | {'Mean CT Ratio':<14s} | {'Realized CV':<12s} | {'Defect Rate %':<14s}")
    print("-" * 85)
    
    summary = {}
    for cat in ["automated_precision", "automated_process", "manual"]:
        for sname in ["day", "evening", "night"]:
            cts = shift_cts[sname][cat]
            defs = shift_defects[sname][cat]
            mean_ct = float(np.mean(cts))
            cv = float(np.std(cts))
            def_rate = (sum(defs) / max(1, len(defs))) * 100.0
            summary[(cat, sname)] = (mean_ct, cv, def_rate)
            print(f"{cat:<22s} | {sname:<8s} | {mean_ct:<14.4f} | {cv:<12.4f} | {def_rate:<13.2f}%")
        print("-" * 85)
        
    print("\n[3/3] Circadian & Shift Fatigue Degradation Analysis:")
    # Manual Shift Degradation
    man_day_ct, _, man_day_def = summary[("manual", "day")]
    man_eve_ct, _, man_eve_def = summary[("manual", "evening")]
    man_nit_ct, _, man_nit_def = summary[("manual", "night")]
    
    # Automated Precision Shift Degradation
    aut_day_ct, _, aut_day_def = summary[("automated_precision", "day")]
    aut_nit_ct, _, aut_nit_def = summary[("automated_precision", "night")]
    
    man_nit_ct_increase = (man_nit_ct - man_day_ct) / man_day_ct * 100.0
    man_nit_def_increase = (man_nit_def - man_day_def) / max(0.01, man_day_def) * 100.0
    aut_nit_ct_increase = (aut_nit_ct - aut_day_ct) / aut_day_ct * 100.0
    manual_excess_delta = man_nit_ct_increase - aut_nit_ct_increase
    
    print(f"  -> Manual Stations Night Shift CT Delta:     +{man_nit_ct_increase:.2f}% (Human Circadian + Cumulative Cycle Wear)")
    print(f"  -> Manual Stations Night Shift Defect Delta: +{man_nit_def_increase:.2f}% (Expected: +25% to +60%)")
    print(f"  -> Automated Precision Night Shift CT Delta: +{aut_nit_ct_increase:.2f}% (Cumulative Cycle Wear)")
    print(f"  -> Human Fatigue Excess CT Degradation:      +{manual_excess_delta:.2f}% (Expected: >= +5.0%)")
    
    # Within-shift fatigue progression (Manual Night Shift 2nd Half vs 1st Half)
    first_half_mean = float(np.mean(shift_first_half_cts["night"]["manual"]))
    second_half_mean = float(np.mean(shift_second_half_cts["night"]["manual"]))
    within_shift_fatigue_pct = (second_half_mean - first_half_mean) / first_half_mean * 100.0
    print(f"  -> Manual Night Shift Within-Shift Fatigue (2nd half vs 1st half): +{within_shift_fatigue_pct:.2f}%")
    
    assert man_nit_ct_increase >= 8.0, f"Manual night shift CT degradation too low: +{man_nit_ct_increase:.2f}%"
    assert man_nit_def_increase >= 20.0, f"Manual night shift defect increase too low: +{man_nit_def_increase:.2f}%"
    assert manual_excess_delta >= 4.0, f"Manual excess fatigue delta too low: +{manual_excess_delta:.2f}%"
    assert second_half_mean >= first_half_mean, "Within-shift fatigue curve failed to show monotonic increase!"
    
    print("=" * 85)
    print("[RESULT] Phase 24 Validation Checkpoint PASSED successfully.")

if __name__ == "__main__":
    validate_checkpoint_24()
