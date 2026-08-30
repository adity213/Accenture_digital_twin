import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from simulator.anomalies import AnomalyManager

def run_test():
    mgr = AnomalyManager()
    
    # Run inject_latent_defect
    aid = mgr.inject_latent_defect("ST01", "ST40", 1)
    anomaly = mgr.active_anomalies[aid]
    
    defect_rate = anomaly.params.get("defect_rate")
    assert defect_rate == 0.05, f"Expected defect_rate 0.05, got {defect_rate}"
    print(f"Test Passed: Latent defect rate is {defect_rate} (yield loss ~5%)")
    
if __name__ == '__main__':
    run_test()
