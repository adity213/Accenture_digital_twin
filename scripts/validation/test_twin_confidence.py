import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pipeline.confidence import ConfidenceEngine

def run_test():
    engine = ConfidenceEngine()
    
    # Body zone, defect driven
    conf1 = engine.compute_composite_twin_confidence(
        data_confidence=1.0, 
        model_risk_prob=0.9, 
        spc_deviation_flag=False, 
        zone="Body", 
        is_defect_driven=True
    )
    
    # Assembly zone, defect driven
    conf2 = engine.compute_composite_twin_confidence(
        data_confidence=1.0, 
        model_risk_prob=0.9, 
        spc_deviation_flag=False, 
        zone="Assembly", 
        is_defect_driven=True
    )
    
    # Assembly zone, NOT defect driven
    conf3 = engine.compute_composite_twin_confidence(
        data_confidence=1.0, 
        model_risk_prob=0.9, 
        spc_deviation_flag=False, 
        zone="Assembly", 
        is_defect_driven=False
    )
    
    assert conf2 < conf1, f"Expected Assembly defect confidence {conf2} < Body defect confidence {conf1}"
    assert conf3 == conf1, f"Expected Assembly non-defect confidence {conf3} == Body non-defect confidence {conf1}"
    
    print(f"Test Passed: Body={conf1}, Assembly(Defect)={conf2}, Assembly(Non-Defect)={conf3}")
    
if __name__ == '__main__':
    run_test()
