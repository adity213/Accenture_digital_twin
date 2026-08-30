import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pipeline.risk_model import RiskScoringModel

def run_test():
    model = RiskScoringModel()
    
    # We'll monkeypatch the compute_baseline_risk and predict_proba to return controlled values
    model.compute_baseline_risk = lambda f: (0.05, 0.05, 0.05)
    model.is_trained = True
    
    class FakeModel:
        def predict_proba(self, X):
            import numpy as np
            # Return [P(class 0), P(class 1)]
            return np.array([[0.1, 0.9]])
            
    model.bottleneck_model = FakeModel()
    model.defect_model = FakeModel()
    
    # Features where divergence will be high (ml_comp = 0.9, base_comp = 0.05 -> divergence = 0.85)
    features = [0.0] * 19
    features[6] = 1.0 # sensor confidence
    
    result = model.predict_risk_with_routing(features, divergence_threshold=0.45)
    
    assert result["router_fallback_active"] == True, "Fallback should be active"
    assert result["serving_mode"] == "shadow_fallback_conservative", f"Serving mode is wrong: {result['serving_mode']}"
    assert result["composite_risk"] >= 0.9, f"Expected composite_risk >= 0.9, got {result['composite_risk']}"
    
    print(f"Test Passed: Fallback triggered. Composite risk is {result['composite_risk']} (base was 0.05, ml was 0.9)")
    
if __name__ == '__main__':
    run_test()
