import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from simulator.generator import LineSimulator

def measure_runs(jph_targets, duration_ticks=120):
    print("=" * 115)
    print(f"MEASUREMENT RUN 2: CORRECTED WIP CAP & RATE-MATCHED INGRESS (Duration: {duration_ticks} ticks = {duration_ticks/60:.1f} sim hours)")
    print("=" * 115)
    print(f"{'Target JPH':<12} | {'Sim Hours':<10} | {'WIP Cap':<10} | {'Vehicles Spawned':<18} | {'Actual Ingress JPH':<20} | {'Completed':<10} | {'Avg Active WIP':<15}")
    print("-" * 115)
    
    for jph in jph_targets:
        sim = LineSimulator(seed=42)
        sim.target_jph = float(jph)
        initial_counter = sim.vehicle_counter
        wip_samples = []
        
        # Calculate derived WIP cap for display
        line_transit_hours = 2497.0 / 3600.0
        wip_cap = max(10, int(sim.target_jph * line_transit_hours * 1.25))
        
        for tick in range(1, duration_ticks + 1):
            sim.step()
            wip_samples.append(len(sim.active_vehicles))
            
        spawned = sim.vehicle_counter - initial_counter
        actual_ingress_jph = spawned / (duration_ticks / 60.0)
        completed = len(sim.completed_vehicles)
        avg_wip = sum(wip_samples) / len(wip_samples)
        
        print(f"{jph:<12.1f} | {duration_ticks/60.0:<10.1f} | {wip_cap:<10} | {spawned:<18} | {actual_ingress_jph:<20.2f} | {completed:<10} | {avg_wip:<15.2f}")
    print("=" * 115)

if __name__ == "__main__":
    measure_runs([30.0, 55.0, 90.0], duration_ticks=120)
