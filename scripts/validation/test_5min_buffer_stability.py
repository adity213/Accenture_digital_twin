import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from simulator.generator import LineSimulator

def run_5min_stability_test():
    sim = LineSimulator(seed=42)
    sim.target_jph = 55.0
    
    target_stations = ["ST01", "ST02", "ST03", "ST04", "ST05", "ST07", "ST08", "ST09", "ST25", "ST26", "ST27"]
    
    print("=" * 120)
    print("5-MINUTE (300-TICK) LIVE SIMULATION BUFFER OCCUPANCY STABILITY TEST (Target JPH = 55.0)")
    print("=" * 120)
    
    header = f"{'Tick':<6} | {'Sim Time':<19} | " + " | ".join([f"{sid} (Cap:{sim.stations[sid]['buffer_capacity_units']})" for sid in target_stations])
    print(header)
    print("-" * 120)
    
    history = {sid: [] for sid in target_stations}
    
    for tick in range(1, 301):
        res = sim.step()
        buffers = res["buffers"]
        for sid in target_stations:
            # Buffer level includes in-processing + queue
            q_len = len(sim.station_buffers[sid])
            proc_val = 1 if sim.station_processing[sid] else 0
            tot_occ = q_len + proc_val
            history[sid].append(tot_occ)
            
        if tick == 1 or tick % 30 == 0:
            row = f"{tick:<6} | {res['timestamp']:<19} | " + " | ".join([f"{history[sid][-1]:>11}" for sid in target_stations])
            print(row)
            
    print("=" * 120)
    print("STEADY-STATE BUFFER OCCUPANCY SUMMARY (TICKS 100 - 300):")
    print("=" * 120)
    print(f"{'Station':<8} | {'Zone':<10} | {'Type':<18} | {'Capacity':<10} | {'Min Occ':<10} | {'Avg Occ':<10} | {'Max Occ':<10} | {'Stability Status':<20}")
    print("-" * 120)
    
    for sid in target_stations:
        st_meta = sim.stations[sid]
        cap = st_meta["buffer_capacity_units"]
        window_data = history[sid][100:] # steady-state window
        min_occ = min(window_data)
        max_occ = max(window_data)
        avg_occ = sum(window_data) / len(window_data)
        
        status = "STABLE (bounded)" if max_occ < cap else "AT CAP (backpressured)"
        print(f"{sid:<8} | {st_meta['zone']:<10} | {st_meta['station_type']:<18} | {cap:<10} | {min_occ:<10} | {avg_occ:<10.2f} | {max_occ:<10} | {status:<20}")
        
    print("=" * 120)

if __name__ == "__main__":
    run_5min_stability_test()
