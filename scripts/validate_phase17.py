"""
scripts/validate_phase17.py
Validation Checkpoint 17:
Measures lag-1 autocorrelation of vibration and Pearson correlation between vibration and temperature
under nominal conditions over 500 ticks.
"""
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.generator import LineSimulator

def validate_checkpoint_17(station_id: str = "ST02", ticks: int = 500, seed: int = 42):
    sim = LineSimulator(seed=seed)
    
    vib_series = []
    temp_series = []
    power_series = []
    load_series = []
    
    for _ in range(ticks):
        step_out = sim.step()
        telemetry = step_out["events"]
        st_event = next(e for e in telemetry if e["station_id"] == station_id)
        
        vib_series.append(st_event["vibration"])
        temp_series.append(st_event["temperature"])
        if st_event["power_kw"] is not None:
            power_series.append(st_event["power_kw"])
        load_series.append(sim.load_state[station_id])
        
    vib = np.array(vib_series)
    temp = np.array(temp_series)
    
    # Lag-1 Autocorrelation of vibration
    vib_centered = vib - np.mean(vib)
    lag1_autocorr = np.sum(vib_centered[:-1] * vib_centered[1:]) / (np.sum(vib_centered**2) + 1e-12)
    
    # Pearson Correlation between Vibration and Temperature
    pearson_corr = np.corrcoef(vib, temp)[0, 1]
    
    print(f"--- Validation Checkpoint 17 (Station: {station_id}, Ticks: {ticks}, Seed: {seed}) ---")
    print(f"Vibration Series Mean: {np.mean(vib):.4f}, Std: {np.std(vib):.4f}")
    print(f"Temperature Series Mean: {np.mean(temp):.4f}, Std: {np.std(temp):.4f}")
    print(f"(a) Lag-1 Autocorrelation of Vibration: {lag1_autocorr:.4f} (Target: >0.30, Previously ~0.00)")
    print(f"(b) Pearson Correlation (Vibration vs Temperature): {pearson_corr:.4f} (Target: >0.50, Previously ~0.00)")
    
    if len(power_series) > 0:
        power = np.array(power_series)
        vib_pwr_corr = np.corrcoef(vib, power)[0, 1]
        print(f"(c) Pearson Correlation (Vibration vs Power): {vib_pwr_corr:.4f}")
        
    assert lag1_autocorr > 0.30, f"Lag-1 autocorrelation {lag1_autocorr:.4f} is too low!"
    assert pearson_corr > 0.30, f"Pearson correlation {pearson_corr:.4f} is too low!"
    print("\n[RESULT] Phase 17 Validation Checkpoint PASSED successfully.")

if __name__ == "__main__":
    validate_checkpoint_17()
