import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pipeline.risk_model import RiskScoringModel

def run_test():
    model = RiskScoringModel()
    # Dummy features. Indices we care about:
    # 0-5: some numbers, 16: vibration, 17: temp
    # Feature 16 is machine_shaking_vibration
    # Feature 17 is motor_heat_temperature
    features = [0.0] * 19
    
    # Test 1: temp = 70.0, vibration = 1.5
    features[16] = 1.5
    features[17] = 70.0
    _, def_risk, _ = model.compute_baseline_risk(features)
    assert def_risk >= 0.45, f"Expected def_risk >= 0.45, got {def_risk}"
    print(f"Test 1 Passed: def_risk = {def_risk} with temp 70.0, vib 1.5")
    
    # Test 2: temp = 50.0, vibration = 1.5
    features[16] = 1.5
    features[17] = 50.0
    _, def_risk2, _ = model.compute_baseline_risk(features)
    assert def_risk2 == 0.20, f"Expected def_risk == 0.20, got {def_risk2}"
    print(f"Test 2 Passed: def_risk = {def_risk2} with temp 50.0, vib 1.5")
    
if __name__ == '__main__':
    run_test()
