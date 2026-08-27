import sys
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)

from pipeline.risk_model import RiskScoringModel
from simulator.topology import build_line_topology
from simulator.generator import LineSimulator
from pipeline.spc import SPCEngine
from pipeline.confidence import ConfidenceEngine

def verify_auc():
    print("--- 1. AUC UNFLOORED TEST ---")
    top = build_line_topology(seed=42)
    sim = LineSimulator(seed=42)
    spc = SPCEngine()
    conf_engine = ConfidenceEngine()
    model = RiskScoringModel()
    
    features_list = []
    bn_labels = []
    def_labels = []
    
    sim.anomaly_mgr.inject_sudden_stoppage("ST06", current_tick=10, duration_ticks=40)
    sim.anomaly_mgr.inject_gradual_drift("ST16", current_tick=15, duration_ticks=50)
    
    for _ in range(80):
        tick_res = sim.step()
        gt_types = {g["station_id"]: g["true_anomaly_type"] for g in tick_res["ground_truth"]}
        event_map = {e["station_id"]: e for e in tick_res["events"]}
        
        for sid, st in top["stations"].items():
            ev = event_map[sid]
            spc_res = spc.update_station(sid, ev.get("cycle_time_s") or st["target_cycle_time_s"], st["target_cycle_time_s"])
            data_conf = conf_engine.compute_data_confidence(st["sensor_tier"], ev.get("is_blackout", False), 0)
            feats = model.extract_features(sid, ev, spc_res, data_conf, [], st["target_cycle_time_s"], st["buffer_capacity_units"], sim.current_tick)
            
            features_list.append(feats)
            bn_label = 1 if gt_types.get(sid) in ["sudden_stoppage", "gradual_drift"] else 0
            def_label = 1 if gt_types.get(sid) == "latent_defect" else 0
            bn_labels.append(bn_label)
            def_labels.append(def_label)
            
    train_res = model.train_on_history(features_list, bn_labels, def_labels)
    print("Computed Training Results:", train_res)

def verify_api():
    print("\n--- 2 & 3. FLEET CONFIDENCE AND LEADERSHIP KPIS ---")
    from api.main import process_simulation_tick, get_leadership_summary, simulator
    
    # Run a few ticks to populate some data
    for _ in range(5):
        payload = process_simulation_tick()
        
    print("Fleet Twin Confidence:", payload["kpis"]["fleet_twin_confidence"])
    
    # Generate some fake completed vehicles to test yield
    simulator.completed_vehicles = [
        {"vin": "V1", "defect_flag": 0},
        {"vin": "V2", "defect_flag": 0},
        {"vin": "V3", "defect_flag": 1}, # defect!
        {"vin": "V4", "defect_flag": 0}
    ]
    
    summary = get_leadership_summary()
    print("Quality Yield:", summary["summary"]["quality_yield_pct"], "%")
    print("Energy Waste Mitigated:", summary["summary"]["energy_waste_mitigated_pct"], "%")
    print("Top Root Causes:", summary["top_root_causes"])

if __name__ == "__main__":
    verify_auc()
    verify_api()
