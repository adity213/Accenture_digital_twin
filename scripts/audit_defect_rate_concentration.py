"""
DigitalTwin.ai - Defect Rate Concentration Audit Script

Audits the defect_label rate, tick-level defect_flag occurrences, distinct-vehicle defect rates,
and dwell time multipliers across station types (specifically VisionQC, QualityScan, FinalInspection
vs. upstream processing stations).
"""
import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Set

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.generator import LineSimulator
from simulator.anomaly_campaign import generate_balanced_campaign, apply_campaign_event


def audit_simulation_traces(seeds: List[int], ticks_per_run: int):
    print("=" * 80)
    print("PHASE 1: SIMULATION VEHICLE TRACE AUDIT (DIRECT TICK-BY-TICK & VEHICLE GENEALOGY)")
    print("=" * 80)

    # Aggregates across seeds
    station_type_rows = defaultdict(int)
    station_type_flag_ticks = defaultdict(int)
    station_type_visited_vins = defaultdict(set)
    station_type_flagged_vins = defaultdict(set)
    station_type_dwell_ticks = defaultdict(list)
    
    # Track dwell runs per vehicle visit
    # (station_id, vin) -> current consecutive ticks
    current_dwell: Dict[tuple, int] = defaultdict(int)

    for seed in seeds:
        sim = LineSimulator(seed=seed)
        topology = sim.topology
        campaign_rng = random.Random(seed * 7919 + 13)
        campaign = generate_balanced_campaign(topology, campaign_rng, ticks_per_run)
        campaign_by_tick = defaultdict(list)
        for ev in campaign:
            campaign_by_tick[ev["start_tick"]].append(ev)

        for t in range(1, ticks_per_run + 1):
            for ev in campaign_by_tick.get(t, []):
                apply_campaign_event(sim.anomaly_mgr, ev)

            tick_res = sim.step()
            events = tick_res["events"]

            for ev in events:
                sid = ev["station_id"]
                stype = topology["stations"][sid]["station_type"]
                vin = ev.get("processing_vin") or ev.get("vehicle_id")
                flag = ev.get("defect_flag", False)

                station_type_rows[stype] += 1
                if flag:
                    station_type_flag_ticks[stype] += 1

                if vin:
                    station_type_visited_vins[stype].add(vin)
                    if flag:
                        station_type_flagged_vins[stype].add(vin)
                    current_dwell[(sid, vin)] += 1
                
            # Collect ended dwells
            active_pairs = {(ev["station_id"], ev.get("processing_vin") or ev.get("vehicle_id")) for ev in events if ev.get("processing_vin") or ev.get("vehicle_id")}
            for (sid, vin), d_count in list(current_dwell.items()):
                if (sid, vin) not in active_pairs:
                    stype = topology["stations"][sid]["station_type"]
                    station_type_dwell_ticks[stype].append(d_count)
                    del current_dwell[(sid, vin)]

    print(f"\n{'STATION TYPE':<20} | {'ROWS':<8} | {'FLAG TICKS':<10} | {'FLAG TICK %':<11} | {'UNIQUE VINS':<11} | {'FLAG VINS':<10} | {'VEH DEFECT %':<12} | {'AVG DWELL'}")
    print("-" * 105)
    for stype in sorted(station_type_rows.keys()):
        rows = station_type_rows[stype]
        flag_ticks = station_type_flag_ticks[stype]
        flag_tick_pct = 100.0 * flag_ticks / max(1, rows)
        
        uniq_vins = len(station_type_visited_vins[stype])
        flag_vins = len(station_type_flagged_vins[stype])
        veh_defect_pct = 100.0 * flag_vins / max(1, uniq_vins)
        
        dwells = station_type_dwell_ticks[stype]
        avg_dwell = sum(dwells) / max(1, len(dwells)) if dwells else 0.0

        print(f"{stype:<20} | {rows:<8} | {flag_ticks:<10} | {flag_tick_pct:<10.2f}% | {uniq_vins:<11} | {flag_vins:<10} | {veh_defect_pct:<11.2f}% | {avg_dwell:.2f} ticks")

    print("\n" + "=" * 80)
    print("PHASE 2: IN-DEPTH DWELL & ACCUMULATION ANALYSIS FOR INSPECTION STATIONS")
    print("=" * 80)

    for insp_type in ["VisionQC", "FinalInspection", "QualityScan", "RoboticWeld", "ManualTrim"]:
        if insp_type in station_type_rows:
            uniq_vins = len(station_type_visited_vins[insp_type])
            flag_vins = len(station_type_flagged_vins[insp_type])
            veh_rate = flag_vins / max(1, uniq_vins)
            
            dwells = station_type_dwell_ticks[insp_type]
            avg_dwell = sum(dwells) / max(1, len(dwells)) if dwells else 1.0
            
            flag_ticks = station_type_flag_ticks[insp_type]
            rows = station_type_rows[insp_type]
            tick_rate = flag_ticks / max(1, rows)
            
            print(f"Station Type: {insp_type}")
            print(f"   Unique Vehicles Passed: {uniq_vins}, Vehicles with Defect Flagged: {flag_vins} ({veh_rate*100:.2f}%)")
            print(f"   Avg Dwell Time: {avg_dwell:.2f} ticks/vehicle")
            print(f"   Observed Tick-Level defect_flag Rate: {tick_rate*100:.2f}% ({flag_ticks}/{rows} ticks)")
            print(f"   Ratio (Flag Ticks / Flagged Vehicles): {flag_ticks / max(1, flag_vins):.2f} ticks per flagged vehicle")
            print()


def audit_csv_dataset(csv_path: str):
    print("=" * 80)
    print(f"PHASE 3: TRAINING CSV AUDIT: {csv_path}")
    print("=" * 80)
    
    rows = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    stype_counts = defaultdict(int)
    stype_defect_labels = defaultdict(int)
    for r in rows:
        stype = r["station_type"]
        stype_counts[stype] += 1
        if int(r.get("defect_label", 0)) == 1:
            stype_defect_labels[stype] += 1

    print(f"\n{'STATION TYPE':<20} | {'TOTAL ROWS':<10} | {'DEFECT_LABEL=1':<15} | {'DEFECT_LABEL POSITIVE RATE'}")
    print("-" * 75)
    for stype in sorted(stype_counts.keys()):
        tot = stype_counts[stype]
        pos = stype_defect_labels[stype]
        rate = 100.0 * pos / max(1, tot)
        print(f"{stype:<20} | {tot:<10} | {pos:<15} | {rate:6.2f}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="data/audit_dataset.csv")
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--ticks", type=int, default=3000)
    args = parser.parse_args()

    audit_simulation_traces(seeds=[1000 + i for i in range(args.seeds)], ticks_per_run=args.ticks)
    
    if Path(args.csv).exists():
        audit_csv_dataset(args.csv)
    else:
        print(f"\nNote: CSV {args.csv} does not exist yet. Run generate_training_data.py to create it.")
