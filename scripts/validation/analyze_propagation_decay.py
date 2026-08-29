"""
scripts/analyze_propagation_decay.py

Empirical calibration of the downstream propagation decay constant (gamma)
using pre-generated training dataset rows and DAG topology.
"""
import sys
import csv
import numpy as np
from collections import defaultdict
from pathlib import Path
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.topology import build_line_topology

def measure_empirical_decay_from_csv(csv_path: str = "data/training_dataset.csv"):
    topology = build_line_topology(seed=42)
    stations_meta = topology["stations"]
    
    # Build NetworkX DAG
    dag = nx.DiGraph()
    for sid in stations_meta:
        dag.add_node(sid)
    for u, v in topology["edges"]:
        dag.add_edge(u, v)

    # Precalculate all shortest path lengths
    shortest_paths = dict(nx.all_pairs_shortest_path_length(dag))

    print(f"Loading dataset from {csv_path}...")
    
    ticks_data = defaultdict(dict)
    total_rows = 0
    seeds_present = set()
    
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            seed = r["seed"]
            seeds_present.add(seed)
            tick = int(r["tick"])
            sid = r["station_id"]
            ct_ratio = float(r["processing_time_ratio"])
            bn_label = int(r["bottleneck_label"])
            ticks_data[(seed, tick)][sid] = {
                "ct_ratio": ct_ratio,
                "bn_label": bn_label
            }
            total_rows += 1

    print(f"Loaded {total_rows:,} rows across {len(seeds_present)} seeds ({sorted(seeds_present)}).")
    print(f"Total unique (seed, tick) line states: {len(ticks_data):,}")
    
    # Downstream propagation tracking:
    # When an upstream station is actively experiencing a severe bottleneck/stoppage (ct_ratio >= 1.30 or bn_label == 1),
    # count how many times downstream stations at hop distance h also experience bottleneck (bn_label == 1).
    decay_by_hop = defaultdict(lambda: {"total": 0, "positives": 0})
    
    for (seed, tick), st_map in ticks_data.items():
        for src_id, src_val in st_map.items():
            if src_val["ct_ratio"] >= 1.30 or src_val["bn_label"] == 1:
                if src_id in shortest_paths:
                    for dest_id, hop in shortest_paths[src_id].items():
                        if hop > 0 and dest_id in st_map:
                            dest_val = st_map[dest_id]
                            decay_by_hop[hop]["total"] += 1
                            if dest_val["bn_label"] == 1:
                                decay_by_hop[hop]["positives"] += 1

    print("\n" + "=" * 105)
    print(f"{'Path Hop (h)':<14} | {'Downstream Pairs':<18} | {'Positive Bottlenecks (y=1)':<28} | {'Positive Rate':<15} | {'Assumed (0.85^h)':<18}")
    print("-" * 105)
    
    hops_list = []
    prob_list = []
    pos_counts = []
    
    for h in sorted(decay_by_hop.keys())[:7]:
        d = decay_by_hop[h]
        tot = d["total"]
        pos = d["positives"]
        pos_counts.append(pos)
        mean_p = pos / max(1, tot)
        assumed = 0.85 ** h
        hops_list.append(h)
        prob_list.append(mean_p)
        reliability_tag = " [LOW SAMPLE]" if pos < 50 else ""
        print(f"{h:<14d} | {tot:<18,d} | {pos:<28d} | {mean_p*100:>13.2f}% | {assumed:>16.3f}{reliability_tag}")

    base_p = prob_list[0] if prob_list and prob_list[0] > 0 else 0.001
    norm_decay = [p / base_p for p in prob_list]
    
    print("\n--- Normalized Relative Decay (relative to Hop 1) ---")
    for h, pos, nd in zip(hops_list, pos_counts, norm_decay):
        note = " (LOW SAMPLE: n_pos < 50)" if pos < 50 else ""
        print(f"  Hop {h}: Positives={pos:3d} | Rel Decay = {nd:.3f} | Assumed (0.85^(h-1)) = {(0.85**(h-1)):.3f}{note}")
        
    low_sample = any(p < 50 for p in pos_counts)
    if low_sample:
        print("\n[NOTE ON RELIABILITY]")
        print("Because positive bottleneck events per hop bucket are under ~50 at several hops, the fitted decay")
        print("constant is dominated by small-sample variance across discrete anomaly injection windows.")
    else:
        if len(hops_list) >= 3:
            log_y = np.log(np.maximum(0.001, norm_decay))
            slope = np.polyfit([h - 1 for h in hops_list], log_y, 1)[0]
            gamma_fit = float(np.exp(slope))
            print(f"\nEmpirical Exponential Decay Factor: gamma = {gamma_fit:.3f} (vs Assumed: 0.850)")

if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "data/training_dataset.csv"
    measure_empirical_decay_from_csv(csv_file)
