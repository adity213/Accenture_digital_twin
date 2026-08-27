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

def test_industrial_temperature_and_vibration_baselines():
    sim = LineSimulator(seed=42)
    tick_res = sim.step()
    event_map = {e["station_id"]: e for e in tick_res["events"]}
    
    # 1. Paint Shop Curing Oven (190°C Standard)
    oven_ev = event_map["ST17"]
    assert oven_ev["temperature"] is not None
    assert 187.0 <= oven_ev["temperature"] <= 193.0, f"Oven temperature should be ~190°C, got {oven_ev['temperature']}"
    
    # 2. Pre-Treatment Chemical & E-Coat Bath (55°C Standard)
    bath_ev = event_map["ST15"]
    assert bath_ev["temperature"] is not None
    assert 52.0 <= bath_ev["temperature"] <= 58.0, f"Bath temperature should be ~55°C, got {bath_ev['temperature']}"
    
    # 3. Ambient Assembly Stations (24°C Standard)
    ambient_ev = event_map["ST01"]
    assert ambient_ev["temperature"] is not None
    assert 22.0 <= ambient_ev["temperature"] <= 26.0, f"Ambient temperature should be ~24°C, got {ambient_ev['temperature']}"
    
    # 4. Robotic Welding Arm Vibration Baseline (1.2 mm/s ISO baseline)
    robot_ev = event_map["ST02"]
    assert robot_ev["vibration"] is not None
    assert 0.90 <= robot_ev["vibration"] <= 1.50, f"Robotic arm vibration should be ~1.2 mm/s, got {robot_ev['vibration']}"
    
    # 5. Conveyor / Transfer Buffer Vibration (0.4 mm/s baseline)
    buffer_ev = event_map["ST14"]
    assert buffer_ev["vibration"] is not None
    assert 0.20 <= buffer_ev["vibration"] <= 0.60, f"Buffer vibration should be ~0.4 mm/s, got {buffer_ev['vibration']}"
