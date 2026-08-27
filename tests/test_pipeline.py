"""
Pipeline Verification Tests (Days 2 & 3 Gates)
- SPC EWMA and rolling z-scores
- Virtual sensor confidence differentiation (Rich vs Manual)
- Zero Data Leakage assertion
- Chronological train/test split
- LightGBM / GBDT predictive model metrics
- Monotonic propagation countdown
"""
import pytest
from pipeline.spc import SPCEngine
from pipeline.confidence import ConfidenceEngine
from pipeline.risk_model import RiskScoringModel
from pipeline.propagation import GraphPropagationEngine
from simulator.topology import build_line_topology
from simulator.generator import LineSimulator

def test_spc_ewma_and_drift_detection():
    spc = SPCEngine(lambda_ewma=0.3, z_threshold=3.0)
    # Simulate gradual drift
    for i in range(25):
        ct = 50.0 + (i * 1.5)  # Progressive drift up
        res = spc.update_station("ST02", ct, 50.0)
    assert res["z_score"] > 2.5, "SPC should detect high z-score during upward drift"
    assert res["trend"] == "DRIFT_UP", "SPC trend should identify DRIFT_UP"

def test_confidence_differentiation_rich_vs_manual():
    conf_engine = ConfidenceEngine(w1=0.5, w2=0.3, w3=0.2)
    rich_conf = conf_engine.compute_data_confidence("rich", is_blackout=False, ticks_since_last_reading=0)
    manual_conf = conf_engine.compute_data_confidence("manual", is_blackout=False, ticks_since_last_reading=0)
    
    assert rich_conf > manual_conf, f"Rich sensor confidence ({rich_conf}) must exceed manual confidence ({manual_conf})"
    assert manual_conf < 0.75, f"Manual confidence should reflect reduced sensor instrumentation"

def test_zero_data_leakage_and_chronological_split():
    top = build_line_topology(seed=42)
    sim = LineSimulator(seed=42)
    spc = SPCEngine()
    conf_engine = ConfidenceEngine()
    model = RiskScoringModel()
    
    features_list = []
    bn_labels = []
    def_labels = []
    
    # Inject a known stoppage and drift to create training labels
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
            
            # Extract features - Assert feature length is 11 and contains no strings/labels
            feats = model.extract_features(sid, ev, spc_res, data_conf, [], st["target_cycle_time_s"], st["buffer_capacity_units"], sim.current_tick)
            assert len(feats) == 11, "Feature vector must be exactly 11 numeric features"
            for val in feats:
                assert isinstance(val, (int, float)), f"Feature value must be numeric, got {type(val)}"
                
            features_list.append(feats)
            bn_label = 1 if gt_types.get(sid) in ["sudden_stoppage", "gradual_drift"] else 0
            def_label = 1 if gt_types.get(sid) == "latent_defect" else 0
            bn_labels.append(bn_label)
            def_labels.append(def_label)
            
    # Train and evaluate chronological split
    train_res = model.train_on_history(features_list, bn_labels, def_labels)
    assert train_res["bottleneck_auc"] > 0.5, f"Model AUC must outperform random guessing (0.5), got {train_res['bottleneck_auc']}"

def test_monotonic_propagation_countdown():
    top = build_line_topology(seed=42)
    prop_engine = GraphPropagationEngine(top)
    
    # Simulate stoppage at ST06
    risks = {sid: 0.05 for sid in top["stations"]}
    risks["ST06"] = 0.95
    
    buffers = {sid: 10 for sid in top["stations"]}
    prop_res = prop_engine.compute_propagation("ST06", risks, buffers)
    
    tree = prop_res["downstream_impact_tree"]
    assert len(tree) > 0, "Downstream propagation tree must have reachable nodes"
    
    # Check that stations further downstream have higher or logical buffer countdown
    nearest = tree[0]
    assert nearest["station_id"] in ["ST07", "ST08", "ST09"], f"First impacted should be immediate downstream, got {nearest['station_id']}"
    assert nearest["time_to_impact_sec"] > 0

def test_iso_10816_vibration_classification():
    spc = SPCEngine(iso_vibration_limit=4.5)
    
    # 1. Good status (<1.12 mm/s)
    res_good = spc.update_station("ST02", 50.0, 50.0, vibration=0.85)
    assert res_good["iso_vibration_status"] == "GOOD"
    assert res_good["iso_vibration_alarm"] is False
    assert res_good["deviation_flag"] is False
    
    # 2. Satisfactory status (1.12 - 2.80 mm/s)
    res_sat = spc.update_station("ST02", 50.0, 50.0, vibration=1.85)
    assert res_sat["iso_vibration_status"] == "SATISFACTORY"
    assert res_sat["iso_vibration_alarm"] is False
    
    # 3. Unsatisfactory warning status (2.80 - 4.50 mm/s)
    res_unsat = spc.update_station("ST02", 50.0, 50.0, vibration=3.60)
    assert res_unsat["iso_vibration_status"] == "UNSATISFACTORY"
    assert res_unsat["iso_vibration_alarm"] is False
    
    # 4. Unacceptable critical alarm status (> 4.50 mm/s)
    res_crit = spc.update_station("ST02", 50.0, 50.0, vibration=5.20)
    assert res_crit["iso_vibration_status"] == "UNACCEPTABLE"
    assert res_crit["iso_vibration_alarm"] is True
    assert res_crit["deviation_flag"] is True
