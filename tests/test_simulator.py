"""
Unit Tests for Simulator & Anomaly Generation (Day 1 Gate)
- Normal-operation 3-sigma sanity
- All 5 anomaly types independently triggerable
- Ground-truth label generation
"""
import pytest
from simulator.generator import LineSimulator

def test_normal_operation_within_3sigma():
    sim = LineSimulator(seed=42)
    cycle_time_deviations = []
    
    for _ in range(40):
        tick_res = sim.step()
        for ev in tick_res["events"]:
            sid = ev["station_id"]
            target_ct = sim.stations[sid]["target_cycle_time_s"]
            actual_ct = ev["cycle_time_s"]
            if actual_ct is not None:
                dev = abs(actual_ct - target_ct) / target_ct
                cycle_time_deviations.append(dev)
                
    within_bounds = sum(1 for d in cycle_time_deviations if d < 0.20) / len(cycle_time_deviations)
    assert within_bounds >= 0.99, f"Normal cycle times should be within ±3sigma >= 99% of time, got {within_bounds*100:.1f}%"

def test_all_five_anomalies_triggerable():
    sim = LineSimulator(seed=42)
    
    a1 = sim.anomaly_mgr.inject_gradual_drift("ST02", current_tick=1, duration_ticks=30)
    a2 = sim.anomaly_mgr.inject_sudden_stoppage("ST06", current_tick=1, duration_ticks=30)
    a3 = sim.anomaly_mgr.inject_latent_defect("ST07", "ST22", current_tick=1, duration_ticks=30)
    a4 = sim.anomaly_mgr.inject_sensor_blackout("ST09", current_tick=1, duration_ticks=30)
    a5 = sim.anomaly_mgr.inject_energy_waste("ST17", current_tick=1, duration_ticks=30)
    
    tick_res = sim.step()
    gt = tick_res["ground_truth"]
    
    types_found = {g["true_anomaly_type"] for g in gt}
    assert "gradual_drift" in types_found, "Gradual drift ground truth missing"
    assert "sudden_stoppage" in types_found, "Sudden stoppage ground truth missing"
    assert "latent_defect" in types_found, "Latent defect ground truth missing"
    assert "sensor_blackout" in types_found, "Sensor blackout ground truth missing"
    assert "energy_waste" in types_found, "Energy waste ground truth missing"
