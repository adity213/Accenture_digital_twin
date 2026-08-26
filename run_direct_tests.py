import sys, os

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)

print("=======================================================")
print("   DigitalTwin.ai - Phase-Gate Validation Runner       ")
print("=======================================================")

# 1. Topology & DAG (Day 1 Gate)
print("\n[1/4] Testing Topology and DAG Structure (Day 1 Gate)...")
from tests.test_topology import test_topology_station_counts_and_zones, test_sensor_tier_split, test_dag_acyclicity
test_topology_station_counts_and_zones()
test_sensor_tier_split()
test_dag_acyclicity()
print("  --> PASS: 40 Stations, Exact 14/8/18 Zone Split, 80/20 Sensor Tier, Valid DAG")

# 2. Simulator & Anomalies (Day 1 Gate)
print("\n[2/4] Testing Simulator and 5 Anomaly Scenarios (Day 1 Gate)...")
from tests.test_simulator import test_normal_operation_within_3sigma, test_all_five_anomalies_triggerable
test_normal_operation_within_3sigma()
test_all_five_anomalies_triggerable()
print("  --> PASS: Normal 3-Sigma Sanity and All 5 Anomaly Types Independently Triggerable")

# 3. Pipeline & ML Model (Days 2 & 3 Gates)
print("\n[3/4] Testing SPC, Virtual Sensor, Risk Model, and Propagation (Days 2 & 3 Gates)...")
from tests.test_pipeline import test_spc_ewma_and_drift_detection, test_confidence_differentiation_rich_vs_manual, test_zero_data_leakage_and_chronological_split, test_monotonic_propagation_countdown
test_spc_ewma_and_drift_detection()
test_confidence_differentiation_rich_vs_manual()
test_zero_data_leakage_and_chronological_split()
test_monotonic_propagation_countdown()
print("  --> PASS: SPC EWMA, Confidence Tier Differentiation, Zero Data Leakage, Chronological GBDT Split, Monotonic Propagation Countdown")

# 4. API Smoke Tests (Day 4 Gate)
print("\n[4/4] Testing FastAPI REST Endpoints and Simulator Controls (Day 4 Gate)...")
from tests.test_api import test_api_stations_endpoint, test_api_station_history, test_api_risk_current, test_api_recommendations, test_api_leadership_summary, test_api_simulator_control
test_api_stations_endpoint()
test_api_station_history()
test_api_risk_current()
test_api_recommendations()
test_api_leadership_summary()
test_api_simulator_control()
print("  --> PASS: All REST Endpoints Return HTTP 200 with Documented JSON Schemas")

print("\n=======================================================")
print("   ALL PHASE-GATE ACCEPTANCE CRITERIA 100% SATISFIED!  ")
print("=======================================================")
