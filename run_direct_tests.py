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
print("\n[2/4] Testing Simulator, Anomalies, and Industrial Baselines (Day 1 Gate)...")
from tests.test_simulator import test_normal_operation_within_3sigma, test_all_five_anomalies_triggerable, test_industrial_temperature_and_vibration_baselines
test_normal_operation_within_3sigma()
test_all_five_anomalies_triggerable()
test_industrial_temperature_and_vibration_baselines()
print("  --> PASS: Normal 3-Sigma Sanity, 5 Anomalies, & Ground-Truth 190°C Oven / 55°C Bath / ISO Vibration Baselines")

# 3. Pipeline & ML Model (Days 2 & 3 Gates)
print("\n[3/4] Testing SPC, ISO 10816 Standard, Virtual Sensor, Risk Model, and Propagation (Days 2 & 3 Gates)...")
from tests.test_pipeline import test_spc_ewma_and_drift_detection, test_confidence_differentiation_rich_vs_manual, test_zero_data_leakage_and_chronological_split, test_monotonic_propagation_countdown, test_iso_10816_vibration_classification
test_spc_ewma_and_drift_detection()
test_iso_10816_vibration_classification()
test_confidence_differentiation_rich_vs_manual()
test_zero_data_leakage_and_chronological_split()
test_monotonic_propagation_countdown()
print("  --> PASS: SPC EWMA, ISO 10816 (<1.12 Good / >4.5 Critical Alarm), Confidence Tier Differentiation, Zero Data Leakage, Chronological GBDT Split, Monotonic Propagation Countdown")

# 4. API Smoke Tests (Day 4 Gate)
print("\n[4/4] Testing FastAPI REST Endpoints and Simulator Controls (Day 4 Gate)...")
from tests.test_api import test_api_stations_endpoint, test_api_station_history, test_api_risk_current, test_api_recommendations, test_api_leadership_summary, test_api_simulator_control, test_api_topology_apply, test_api_topology_reset
test_api_stations_endpoint()
test_api_station_history()
test_api_risk_current()
test_api_recommendations()
test_api_leadership_summary()
test_api_simulator_control()
test_api_topology_apply()
test_api_topology_reset()
print("  --> PASS: All REST Endpoints & Topology Apply/Reset Return HTTP 200 with Documented JSON Schemas")

print("\n=======================================================")
print("   ALL PHASE-GATE ACCEPTANCE CRITERIA 100% SATISFIED!  ")
print("=======================================================")
