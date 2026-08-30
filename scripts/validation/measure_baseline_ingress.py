import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from simulator.generator import LineSimulator

def measure_baseline(jph_targets, duration_ticks=120):
    print("=" * 105)
    print(f"MEASUREMENT RUN: CURRENT CODE (Duration: {duration_ticks} ticks = {duration_ticks/60:.1f} sim hours)")
    print("=" * 105)
    print(f"{'Target JPH':<12} | {'Sim Hours':<10} | {'Vehicles Spawned':<18} | {'Actual Ingress JPH':<20} | {'Completed':<10} | {'Avg Active WIP':<15}")
    print("-" * 105)
    
    for jph in jph_targets:
        sim = LineSimulator(seed=42)
        initial_counter = sim.vehicle_counter
        sim.target_jph = float(jph)
        wip_samples = []
        
        for tick in range(1, duration_ticks + 1):
            sim.step()
            wip_samples.append(len(sim.active_vehicles))
            
        spawned = sim.vehicle_counter - initial_counter
        actual_jph = spawned / (duration_ticks / 60.0)
        completed = len(sim.completed_vehicles)
        avg_wip = sum(wip_samples) / len(wip_samples)
        
        print(f"{jph:<12.1f} | {duration_ticks/60.0:<10.1f} | {spawned:<18} | {actual_jph:<20.2f} | {completed:<10} | {avg_wip:<15.2f}")
    print("=" * 105)

if __name__ == "__main__":
    measure_baseline([30.0, 55.0, 90.0], duration_ticks=120)
