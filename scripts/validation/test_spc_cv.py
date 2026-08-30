import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pipeline.spc import SPCEngine

def run_test():
    engine = SPCEngine()
    
    # Pass 1: Sensor tier manual should yield cv=0.130
    res1 = engine.update_station("ST08", cycle_time_s=110.0, target_cycle_time_s=100.0, sensor_tier="manual")
    baseline_sigma1 = res1.get("baseline_sigma")
    assert baseline_sigma1 == 13.0, f"Expected baseline_sigma 13.0, got {baseline_sigma1}"
    
    # Pass 2: Sensor tier rich (automated) should yield cv=0.050
    engine2 = SPCEngine()
    res2 = engine2.update_station("ST08", cycle_time_s=110.0, target_cycle_time_s=100.0, sensor_tier="rich")
    baseline_sigma2 = res2.get("baseline_sigma")
    assert baseline_sigma2 == 5.0, f"Expected baseline_sigma 5.0, got {baseline_sigma2}"
    
    print(f"Test Passed: Manual sigma={baseline_sigma1}, Rich sigma={baseline_sigma2}")
    
if __name__ == '__main__':
    run_test()
