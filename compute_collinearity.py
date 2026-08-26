import pandas as pd
import numpy as np
from simulator.generator import LineSimulator
from pipeline.spc import SPCEngine

def compute():
    sim = LineSimulator(seed=42)
    spc = SPCEngine()
    
    data = []
    
    print("Generating 2000 ticks of simulation data...")
    for _ in range(2000):
        tick_data = sim.step()
        for event in tick_data["events"]:
            station_id = event["station_id"]
            ct = event["cycle_time_s"] or 60.0
            
            # Find target cycle time from topology
            target_ct = 60.0
            for s_id, s_data in sim.stations.items():
                if s_id == station_id:
                    target_ct = s_data["target_cycle_time_s"]
                    break

            spc_res = spc.update_station(station_id, ct, target_ct)
            
            # Primary Features
            buf = event["buffer_level"]
            cap = event["buffer_capacity"]
            vib = event["vibration"]
            pwr = event["power_kw"]
            
            # Derived Features
            ct_ratio = ct / target_ct
            buf_fill = buf / cap
            z_score = spc_res.get("z_score", 0.0)
            
            trend_map = {"STABLE": 0.0, "DRIFT_UP": 1.0, "DRIFT_DOWN": -1.0}
            trend_val = trend_map.get(spc_res.get("trend", "STABLE"), 0.0)
            
            data.append({
                "raw_cycle_time": ct,
                "raw_buffer_level": buf,
                "raw_vibration": vib,
                "raw_power": pwr,
                "derived_ct_ratio": ct_ratio,
                "derived_buf_fill": buf_fill,
                "derived_z_score": z_score,
                "derived_trend_val": trend_val
            })
            
    df = pd.DataFrame(data).dropna()
    corr = df.corr()
    
    print("\n--- Correlation (Collinearity) Matrix ---")
    print(corr.round(3).to_string())
    
    print("\n--- Analysis of Crossover ---")
    print(f"Correlation between raw_cycle_time and derived_ct_ratio: {corr.loc['raw_cycle_time', 'derived_ct_ratio']:.3f}")
    print(f"Correlation between raw_cycle_time and derived_z_score: {corr.loc['raw_cycle_time', 'derived_z_score']:.3f}")
    print(f"Correlation between raw_cycle_time and derived_trend_val: {corr.loc['raw_cycle_time', 'derived_trend_val']:.3f}")
    print(f"Correlation between derived_z_score and derived_ct_ratio: {corr.loc['derived_z_score', 'derived_ct_ratio']:.3f}")

if __name__ == "__main__":
    compute()
