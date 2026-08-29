"""
scripts/validate_phase20.py

Validation script for Phase 20: Anomaly-type-specific physical signal effect profiles.
Tests all 5 anomaly types individually on a test station, running 30 ticks each,
and reporting the observed deltas for Cycle Time, Vibration, Temperature, and Power from baseline.
"""
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.generator import LineSimulator

def measure_station_series(sim: LineSimulator, station_id: str, ticks: int):
    cts, vibs, temps, powers, blackouts = [], [], [], [], []
    for _ in range(ticks):
        step_out = sim.step()
        ev = next(e for e in step_out["events"] if e["station_id"] == station_id)
        cts.append(ev["cycle_time_s"] if ev["cycle_time_s"] is not None else np.nan)
        vibs.append(ev["vibration"] if ev["vibration"] is not None else np.nan)
        temps.append(ev["temperature"] if ev["temperature"] is not None else np.nan)
        powers.append(ev["power_kw"] if ev["power_kw"] is not None else np.nan)
        blackouts.append(ev["is_blackout"])
    return {
        "ct": np.nanmean(cts) if not all(np.isnan(cts)) else np.nan,
        "vib": np.nanmean(vibs) if not all(np.isnan(vibs)) else np.nan,
        "temp": np.nanmean(temps) if not all(np.isnan(temps)) else np.nan,
        "power": np.nanmean(powers) if not all(np.isnan(powers)) else np.nan,
        "blackout_count": sum(blackouts)
    }

def validate_checkpoint_20(station_id: str = "ST02", ticks_per_anomaly: int = 30, seed: int = 42):
    # 1. Baseline Nominal Operation
    sim_base = LineSimulator(seed=seed)
    base_metrics = measure_station_series(sim_base, station_id, ticks=ticks_per_anomaly)
    
    print("=" * 95)
    print(f"=== CHECKPOINT 20: ANOMALY PHYSICAL SIGNATURE DECOUPLING AUDIT (Station: {station_id}) ===")
    print(f"Baseline Nominal Metrics (30 ticks): CT = {base_metrics['ct']:.2f}s, Vib = {base_metrics['vib']:.3f}g, Temp = {base_metrics['temp']:.2f}°C, Power = {base_metrics['power']:.2f}kW")
    print("=" * 95)
    print(f"{'Anomaly Type':<20} | {'CT Delta (s)':<14} | {'Vib Delta (g)':<15} | {'Temp Delta (°C)':<16} | {'Power Delta (kW)':<18} | {'Blackout Ticks':<14}")
    print("-" * 95)
    
    anomaly_types = ["gradual_drift", "sudden_stoppage", "latent_defect", "sensor_blackout", "energy_waste"]
    results = {}
    
    for anom_type in anomaly_types:
        sim = LineSimulator(seed=seed)
        # Fast forward 10 ticks for steady state
        for _ in range(10):
            sim.step()
            
        cur_tick = sim.current_tick
        # Inject specific anomaly
        if anom_type == "gradual_drift":
            sim.anomaly_mgr.inject_gradual_drift(station_id, cur_tick + 1, duration_ticks=ticks_per_anomaly, drift_factor=0.45)
        elif anom_type == "sudden_stoppage":
            sim.anomaly_mgr.inject_sudden_stoppage(station_id, cur_tick + 1, duration_ticks=ticks_per_anomaly)
        elif anom_type == "latent_defect":
            sim.anomaly_mgr.inject_latent_defect(station_id, "ST22", cur_tick + 1, duration_ticks=ticks_per_anomaly)
        elif anom_type == "sensor_blackout":
            sim.anomaly_mgr.inject_sensor_blackout(station_id, cur_tick + 1, duration_ticks=ticks_per_anomaly)
        elif anom_type == "energy_waste":
            sim.anomaly_mgr.inject_energy_waste(station_id, cur_tick + 1, duration_ticks=ticks_per_anomaly, surge_multiplier=2.4)
            
        m = measure_station_series(sim, station_id, ticks=ticks_per_anomaly)
        
        d_ct = m["ct"] - base_metrics["ct"] if not np.isnan(m["ct"]) else np.nan
        d_vib = m["vib"] - base_metrics["vib"] if not np.isnan(m["vib"]) else np.nan
        d_temp = m["temp"] - base_metrics["temp"] if not np.isnan(m["temp"]) else np.nan
        d_pwr = m["power"] - base_metrics["power"] if not np.isnan(m["power"]) else np.nan
        
        results[anom_type] = {"d_ct": d_ct, "d_vib": d_vib, "d_temp": d_temp, "d_pwr": d_pwr, "blackout": m["blackout_count"]}
        
        ct_str = f"{d_ct:+6.2f}" if not np.isnan(d_ct) else "   N/A"
        vib_str = f"{d_vib:+7.3f}" if not np.isnan(d_vib) else "    N/A"
        temp_str = f"{d_temp:+7.2f}" if not np.isnan(d_temp) else "    N/A"
        pwr_str = f"{d_pwr:+8.2f}" if not np.isnan(d_pwr) else "     N/A"
        
        print(f"{anom_type:<20} | {ct_str:<14} | {vib_str:<15} | {temp_str:<16} | {pwr_str:<18} | {m['blackout_count']:<14}")

    print("=" * 95)
    
    # Assertions for Checkpoint 20
    # 1. gradual_drift: vib and temp rise clearly
    assert results["gradual_drift"]["d_vib"] > 0.50, f"gradual_drift vibration delta too low: {results['gradual_drift']['d_vib']:.3f}"
    assert results["gradual_drift"]["d_temp"] > 2.0, f"gradual_drift temperature delta too low: {results['gradual_drift']['d_temp']:.2f}"
    
    # 2. sudden_stoppage: vib drops towards zero (large negative delta), power drops
    assert results["sudden_stoppage"]["d_vib"] < -0.80, f"sudden_stoppage vibration did not drop: {results['sudden_stoppage']['d_vib']:.3f}"
    assert results["sudden_stoppage"]["d_pwr"] < -10.0, f"sudden_stoppage power did not drop: {results['sudden_stoppage']['d_pwr']:.2f}"
    
    # 3. latent_defect: ~no telemetry changes (|delta| near 0)
    assert abs(results["latent_defect"]["d_vib"]) < 0.15, f"latent_defect caused unintended vibration delta: {results['latent_defect']['d_vib']:.3f}"
    assert abs(results["latent_defect"]["d_temp"]) < 1.0, f"latent_defect caused unintended temperature delta: {results['latent_defect']['d_temp']:.2f}"
    assert abs(results["latent_defect"]["d_pwr"]) < 2.0, f"latent_defect caused unintended power delta: {results['latent_defect']['d_pwr']:.2f}"
    
    # 4. energy_waste: power surges (+>25 kW), but vibration delta is ~0
    assert results["energy_waste"]["d_pwr"] > 20.0, f"energy_waste power surge too low: {results['energy_waste']['d_pwr']:.2f}"
    assert abs(results["energy_waste"]["d_vib"]) < 0.15, f"energy_waste leaked into vibration: {results['energy_waste']['d_vib']:.3f}"
    assert abs(results["energy_waste"]["d_temp"]) < 1.0, f"energy_waste leaked into temperature: {results['energy_waste']['d_temp']:.2f}"
    
    # 5. sensor_blackout: blackout ticks recorded
    assert results["sensor_blackout"]["blackout"] == ticks_per_anomaly, "sensor_blackout did not produce 100% blackout ticks"
    
    print("\n[RESULT] Phase 20 Validation Checkpoint PASSED successfully.")

if __name__ == "__main__":
    validate_checkpoint_20()
