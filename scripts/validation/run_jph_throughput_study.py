import os
import sys
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from simulator.generator import LineSimulator

def run_study():
    jph_targets = [30.0, 55.0, 90.0]
    
    print("=" * 115)
    print("EXPERIMENT 1: 2-HOUR (120 TICKS) RUN AT TARGET JPH = [30, 55, 90]")
    print("=" * 115)
    print(f"{'Target JPH':<12} | {'Sim Hours':<10} | {'WIP Cap':<10} | {'Vehicles Entered ST01':<22} | {'Actual Ingress JPH':<20} | {'Completed':<10} | {'Avg Line WIP':<14}")
    print("-" * 115)
    
    for jph in jph_targets:
        sim = LineSimulator(seed=42)
        sim.target_jph = float(jph)
        initial_counter = sim.vehicle_counter
        wip_samples = []
        
        line_transit_hours = 2497.0 / 3600.0
        wip_cap = max(10, min(int(math.ceil(sim.target_jph * line_transit_hours * 1.25)), sum(1 + s["buffer_capacity_units"] for s in sim.stations.values())))
        
        for tick in range(1, 121):
            sim.step()
            wip_samples.append(len(sim.active_vehicles))
            
        spawned = sim.vehicle_counter - initial_counter
        actual_ingress_jph = spawned / 2.0
        completed = sim.total_completed_vehicles
        avg_wip = sum(wip_samples) / len(wip_samples)
        
        print(f"{jph:<12.1f} | {2.0:<10.1f} | {wip_cap:<10} | {spawned:<22} | {actual_ingress_jph:<20.2f} | {completed:<10} | {avg_wip:<14.2f}")
        
    print("=" * 115)
    print("\n" + "=" * 115)
    print("EXPERIMENT 2: 5-HOUR (300 TICKS) EXTENDED STEADY-STATE RUN AT TARGET JPH = [30, 55, 90]")
    print("=" * 115)
    print(f"{'Target JPH':<12} | {'Sim Hours':<10} | {'WIP Cap':<10} | {'Vehicles Entered ST01':<22} | {'Actual Ingress JPH':<20} | {'Completed':<10} | {'Avg Line WIP':<14}")
    print("-" * 115)
    
    for jph in jph_targets:
        sim = LineSimulator(seed=42)
        sim.target_jph = float(jph)
        initial_counter = sim.vehicle_counter
        wip_samples = []
        
        line_transit_hours = 2497.0 / 3600.0
        wip_cap = max(10, min(int(math.ceil(sim.target_jph * line_transit_hours * 1.25)), sum(1 + s["buffer_capacity_units"] for s in sim.stations.values())))
        
        for tick in range(1, 301):
            sim.step()
            wip_samples.append(len(sim.active_vehicles))
            
        spawned = sim.vehicle_counter - initial_counter
        actual_ingress_jph = spawned / 5.0
        completed = sim.total_completed_vehicles
        avg_wip = sum(wip_samples) / len(wip_samples)
        
        print(f"{jph:<12.1f} | {5.0:<10.1f} | {wip_cap:<10} | {spawned:<22} | {actual_ingress_jph:<20.2f} | {completed:<10} | {avg_wip:<14.2f}")
    print("=" * 115)

if __name__ == "__main__":
    run_study()
