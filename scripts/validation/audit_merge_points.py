import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from simulator.topology import build_line_topology

def audit_merge_points():
    topology = build_line_topology(seed=42)
    stations = topology["stations"]
    edges = topology["edges"]
    
    upstream_map = {sid: [] for sid in stations}
    for u, v in edges:
        upstream_map[v].append(u)
        
    print("=" * 115)
    print(f"{'Station':<8} | {'Station Name':<34} | {'Feeders (Cycle Times)':<28} | {'Arrival Rate':<14} | {'Drain Rate':<12} | {'Ratio':<7} | {'Status':<10}")
    print("=" * 115)
    
    merge_points_found = 0
    for sid, s in stations.items():
        feeders = upstream_map[sid]
        if len(feeders) >= 2:
            merge_points_found += 1
            feeder_cts = [stations[f]["target_cycle_time_s"] for f in feeders]
            feeder_desc = ", ".join([f"{f}({ct:.1f}s)" for f, ct in zip(feeders, feeder_cts)])
            
            combined_in_rate = sum(1.0 / ct for ct in feeder_cts)
            own_ct = s["target_cycle_time_s"]
            own_rate = 1.0 / own_ct
            ratio = combined_in_rate / own_rate
            
            status = "BALANCED" if ratio < 1.0 else "OVERLOADED"
            headroom = f"({(1.0 - ratio)*100:.1f}% headroom)" if ratio < 1.0 else f"({(ratio - 1.0)*100:.1f}% excess)"
            
            print(f"{sid:<8} | {s['name']:<34} | {feeder_desc:<28} | {combined_in_rate:.6f} veh/s | {own_rate:.6f} veh/s | {ratio:.4f}  | {status:<10} {headroom}")
            
    print("=" * 115)
    print(f"Total Merge Points Audited: {merge_points_found}")
    print("=" * 115)

if __name__ == "__main__":
    audit_merge_points()
