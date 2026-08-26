"""
Master Phase-Gate Scorecard & Runner for DigitalTwin.ai
Executes validation checks across Days 1 to 6 and outputs structured results.
"""
import pytest
import sys
import time

def run_scorecard():
    print("==================================================================")
    print("   DigitalTwin.ai - Phase-Gate Prototype Verification Scorecard   ")
    print("==================================================================")
    
    ret_code = pytest.main(["-v", os.path.dirname(__file__)])
    
    print("\n------------------------------------------------------------------")
    if ret_code == 0:
        print(" [PASS] ALL PHASE-GATE ACCEPTANCE CRITERIA SATISFIED SUCCESSFULLY!")
    else:
        print(f" [FAIL] Test suite exited with code {ret_code}")
    print("------------------------------------------------------------------\n")
    return ret_code

if __name__ == "__main__":
    import os
    sys.exit(run_scorecard())
