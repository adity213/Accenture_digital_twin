"""
ITEM 5 Task 6 verification: For every station where sensor_tier == "manual",
call SPCEngine.update_station() and inspect the returned baseline_sigma to
derive the actual CV used.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulator.generator import LineSimulator
from pipeline.spc import SPCEngine

sim = LineSimulator(seed=42)
stations = sim.topology["stations"]

print("=" * 75)
print(f"{'Station':<8} {'sensor_tier':<12} {'station_type':<22} {'target_ct':<10} {'sigma':<8} {'CV':<8} {'Status'}")
print("=" * 75)

manual_count = 0
all_ok = True
for sid in sorted(stations.keys()):
    meta = stations[sid]
    tier = meta.get("sensor_tier", "rich")
    stype = meta.get("station_type", "Unknown")
    
    if tier != "manual":
        continue
    
    manual_count += 1
    target_ct = meta["target_cycle_time_s"]
    
    # Call the actual SPCEngine with the same args the production code uses
    spc = SPCEngine()
    res = spc.update_station(
        sid, target_ct, target_ct,  # use target as actual for a clean measurement
        vibration=None,
        station_type=stype,
        sensor_tier=tier
    )
    
    sigma = res["baseline_sigma"]
    cv = sigma / target_ct if target_ct > 0 else 0
    status = "OK" if cv >= 0.129 else "MISMATCH"
    if status == "MISMATCH":
        all_ok = False
    
    print(f"{sid:<8} {tier:<12} {stype:<22} {target_ct:<10.1f} {sigma:<8.3f} {cv:<8.3f} {status}")

print(f"\nTotal manual stations: {manual_count}")
print(f"All manual stations resolve to CV >= 0.130: {all_ok}")
