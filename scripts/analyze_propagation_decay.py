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

    print(f"Loading training data from {csv_path}...")
    
    # Group rows by (seed, tick) -> {station_id: bottleneck_label or processing_time_ratio}
    ticks_data = defaultdict(dict)
    
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            seed = r["seed"]
            tick = int(r["tick"])
            sid = r["station_id"]
            ct_ratio = float(r["processing_time_ratio"])
            bn_label = int(r["bottleneck_label"])
            ticks_data[(seed, tick)][sid] = {
                "ct_ratio": ct_ratio,
                "bn_label": bn_label
            }

    print(f"Loaded {len(ticks_data)} unique (seed, tick) manufacturing states.")
    
    # Analyze decay: when an upstream station has a severe anomaly (ct_ratio > 1.30 or bn_label == 1),
    # what is the downstream bottleneck likelihood / degradation at distance h?
    decay_by_hop = defaultdict(list)
    
    for (seed, tick), st_map in ticks_data.items():
        for src_id, src_val in st_map.items():
            if src_val["ct_ratio"] >= 1.30 or src_val["bn_label"] == 1:
                src_mag = max(0.5, src_val["ct_ratio"] - 1.0)
                if src_id in shortest_paths:
                    for dest_id, hop in shortest_paths[src_id].items():
                        if hop > 0 and dest_id in st_map:
                            dest_val = st_map[dest_id]
                            # downstream impact magnitude relative to source
                            dest_mag = max(0.0, dest_val["ct_ratio"] - 1.0)
                            rel_impact = min(1.0, dest_mag / max(0.01, src_mag)) if src_mag > 0 else 0.0
                            decay_by_hop[hop].append(dest_val["bn_label"])

    print("\n=== EMPIRICAL PROPAGATION DECAY ANALYSIS ===")
    print(f"{'Path Len (Hops)':<16} | {'Downstream Samples':<20} | {'Downstream Bottleneck Prob':<30} | {'Assumed (0.85^h)':<18}")
    print("-" * 90)
    
    hops_list = []
    prob_list = []
    
    for h in sorted(decay_by_hop.keys())[:7]:
        samples = decay_by_hop[h]
        mean_p = np.mean(samples)
        assumed = 0.85 ** h
        hops_list.append(h)
        prob_list.append(mean_p)
        print(f"{h:<16d} | {len(samples):<20d} | {mean_p:>28.3f} | {assumed:>16.3f}")

    # Normalized relative decay starting from hop 1
    base_p = prob_list[0] if prob_list and prob_list[0] > 0 else 0.01
    norm_decay = [p / base_p for p in prob_list]
    
    print("\n--- Relative Decay Normalized to Hop 1 ---")
    for h, nd in zip(hops_list, norm_decay):
        print(f"  Hop {h}: Empirical Rel Decay = {nd:.3f} | Assumed (0.85^(h-1)) = {(0.85**(h-1)):.3f}")
        
    if len(hops_list) >= 3:
        log_y = np.log(np.maximum(0.001, norm_decay))
        slope = np.polyfit([h - 1 for h in hops_list], log_y, 1)[0]
        gamma_fit = float(np.exp(slope))
        print(f"\nEmpirical Exponential Decay Factor: gamma = {gamma_fit:.3f} (vs Assumed: 0.850)")
        print(f"Difference: {abs(gamma_fit - 0.850):.3f}")
        return gamma_fit

if __name__ == "__main__":
    measure_empirical_decay_from_csv()
