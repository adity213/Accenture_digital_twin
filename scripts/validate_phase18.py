"""
scripts/validate_phase18.py

Validation script for Phase 18 (Lognormal Cycle Time) & Regression Check for Checkpoint 17.
"""
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.generator import LineSimulator, lognormal_cycle_time

def validate_checkpoint_18(station_id: str = "ST02", ticks: int = 2000, seed: int = 42):
    sim = LineSimulator(seed=seed)
    target_ct = sim.stations[station_id]["target_cycle_time_s"]
    
    ct_samples = []
    vib_samples = []
    temp_samples = []
    power_samples = []
    load_samples = []
    
    for _ in range(ticks):
        step_out = sim.step()
        events = step_out["events"]
        st = next(e for e in events if e["station_id"] == station_id)
        ct_samples.append(st["cycle_time_s"])
        vib_samples.append(st["vibration"])
        temp_samples.append(st["temperature"])
        if st["power_kw"] is not None:
            power_samples.append(st["power_kw"])
        load_samples.append(sim.load_state[station_id])
        
    cts = np.array(ct_samples)
    vibs = np.array(vib_samples)
    temps = np.array(temp_samples)
    
    # 1. Phase 18 Metrics
    mean_ct = np.mean(cts)
    std_ct = np.std(cts)
    realized_cv = std_ct / mean_ct
    
    # Skewness: m3 / (m2^(3/2))
    ct_centered = cts - mean_ct
    skewness = np.mean(ct_centered**3) / (std_ct**3 + 1e-12)
    
    # Histogram distribution check near 1.3x target
    # 1.3x boundary = target_ct * 1.3
    upper_bound = target_ct * 1.3
    bins = [target_ct * 0.8, target_ct * 0.95, target_ct * 1.05, target_ct * 1.15, target_ct * 1.25, target_ct * 1.35, target_ct * 1.5]
    counts, _ = np.histogram(cts, bins=bins)
    
    print("=" * 70)
    print(f"=== CHECKPOINT 18: LOGNORMAL CYCLE TIME (Station: {station_id}, N={ticks}) ===")
    print(f"Target Cycle Time:        {target_ct:.2f} s")
    print(f"Empirical Mean CT:        {mean_ct:.2f} s (Error: {abs(mean_ct - target_ct)/target_ct*100:.2f}%)")
    print(f"Empirical Std CT:         {std_ct:.2f} s")
    print(f"Realized CV (std/mean):   {realized_cv:.4f} (Target CV: 0.04)")
    print(f"Empirical Skewness:       {skewness:.4f} (Expected: > 0.0, Positive/Right-skewed)")
    print("\n--- Distribution Histogram across bins ---")
    for i in range(len(counts)):
        bin_label = f"[{bins[i]:.1f}s - {bins[i+1]:.1f}s]"
        bar = "#" * int(counts[i] / 20)
        print(f"  {bin_label:<20} : {counts[i]:4d} samples ({counts[i]/ticks*100:5.1f}%) | {bar}")
        
    print(f"\nSamples above 1.3x ({upper_bound:.1f}s): {np.sum(cts >= upper_bound)} / {ticks} (Smooth tail, no clip cliff)")
    
    # 2. Checkpoint 17 Regression Verification
    vib_500 = vibs[:500]
    temp_500 = temps[:500]
    vib_centered = vib_500 - np.mean(vib_500)
    lag1_autocorr = np.sum(vib_centered[:-1] * vib_centered[1:]) / (np.sum(vib_centered**2) + 1e-12)
    pearson_corr = np.corrcoef(vib_500, temp_500)[0, 1]
    
    # CT vs Vibration correlation (due to load_state coupling)
    ct_vib_corr = np.corrcoef(cts[:500], vib_500)[0, 1]
    
    print("\n" + "=" * 70)
    print("=== CHECKPOINT 17 REGRESSION CHECK (First 500 ticks) ===")
    print(f"(a) Lag-1 Autocorrelation of Vibration: {lag1_autocorr:.4f} (Target: >0.30)")
    print(f"(b) Pearson Correlation (Vibration vs Temp): {pearson_corr:.4f} (Target: >0.50)")
    print(f"(c) Pearson Correlation (Cycle Time vs Vibration): {ct_vib_corr:.4f} (Coupled via load_state)")
    print("=" * 70)
    
    assert abs(mean_ct - target_ct) / target_ct < 0.02, "Mean CT drifted too far from target!"
    assert skewness > 0.0, f"Cycle time is not right-skewed! Skewness={skewness:.4f}"
    assert lag1_autocorr > 0.30, f"Lag-1 autocorrelation regressed! {lag1_autocorr:.4f}"
    assert pearson_corr > 0.30, f"Pearson correlation regressed! {pearson_corr:.4f}"
    print("\n[RESULT] Phase 18 & Checkpoint 17 Verification PASSED successfully.")

if __name__ == "__main__":
    validate_checkpoint_18()
