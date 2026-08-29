"""
DigitalTwin.ai - Prediction Lead-Time Evaluation
Evaluates the actual serving system (ML + Baselines + Divergence + Confidence)
to determine true operational lead time for simulator events.
"""
import sys
import json
import numpy as np
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulator.topology import build_line_topology
from simulator.generator import LineSimulator
from pipeline.risk_model import RiskScoringModel
from pipeline.spc import SPCEngine
from pipeline.virtual_sensor import VirtualSensorEngine
from pipeline.confidence import ConfidenceEngine
from pipeline.propagation import GraphPropagationEngine
from api.main import load_or_init_risk_model

def run_evaluation(sim_ticks: int = 15000):
    print(f"Initializing Lead-Time Evaluation (Simulating {sim_ticks} ticks)...")
    
    topology = build_line_topology()
    stations_meta = topology["stations"]
    
    simulator = LineSimulator(seed=42, custom_topology=topology)
    spc_engine = SPCEngine(lambda_ewma=0.3, z_threshold=3.0)
    virtual_sensor_engine = VirtualSensorEngine(stations_meta)
    confidence_engine = ConfidenceEngine(w1=0.5, w2=0.3, w3=0.2)
    risk_model = load_or_init_risk_model()
    
    anomaly_tracking = {}
    station_alert_state = {}
    total_alerts = 0
    matched_alerts = set()
    
    prev_tick_risk = {sid: 0.0 for sid in stations_meta}
    
    type_metrics = defaultdict(lambda: {"events": 0, "detected": 0, "lead_times": []})
    
    for t in range(sim_ticks):
        tick_res = simulator.step()
        curr_tick = simulator.current_tick
        
        # 1. Update ground-truth active anomalies
        active_anomalies = simulator.anomaly_mgr.active_anomalies
        for aid, anom in active_anomalies.items():
            if aid not in anomaly_tracking:
                anomaly_tracking[aid] = {
                    "anomaly_type": anom.anomaly_type,
                    "station_id": anom.station_id,
                    "actual_event_tick": anom.start_tick,
                    "first_prediction_tick": None,
                    "serving_mode": None,
                    "served_risk": None,
                }
        
        # 2. Run full serving decision logic for every station
        this_tick_risk = {}
        events_by_sid = {ev["station_id"]: ev for ev in tick_res["events"]}
        for sid, meta in stations_meta.items():
            ev = events_by_sid.get(sid, {})
            target_ct = meta["target_cycle_time_s"]
            is_blackout = ev.get("is_blackout", False)
            actual_ct = ev.get("cycle_time_s")
            
            if is_blackout or actual_ct is None:
                imputed = virtual_sensor_engine.impute_station_telemetry(sid, curr_tick, tick_res["events"])
                actual_ct = imputed["imputed_cycle_time_s"]
                disagreement = imputed["imputation_disagreement"]
            else:
                disagreement = 0.0
                
            spc_res = spc_engine.update_station(
                sid, actual_ct, target_ct,
                vibration=ev.get("vibration"),
                station_type=meta.get("station_type") or meta.get("type")
            )
            
            data_conf = confidence_engine.compute_data_confidence(
                sensor_tier=meta["sensor_tier"],
                is_blackout=is_blackout,
                ticks_since_last_reading=3 if is_blackout else 0,
                imputation_disagreement=disagreement
            )
            
            upstream_risks = [prev_tick_risk.get(u, 0.0) for u in meta.get("upstream_ids", [])]
            
            feats = risk_model.extract_features(
                station_id=sid,
                telemetry=ev,
                spc_result=spc_res,
                sensor_confidence=data_conf,
                upstream_risks=upstream_risks,
                target_cycle_time_s=target_ct,
                buffer_capacity=meta["buffer_capacity_units"],
                shift_tick=curr_tick,
                zone=meta.get("zone", "Body"),
                station_type=meta.get("station_type") or meta.get("type", "RoboticWeld")
            )
            
            # Using Shadow Mode Router
            routing_res = risk_model.predict_risk_with_routing(feats)
            risk_level = routing_res["risk_level"]
            comp_risk = routing_res["composite_risk"]
            serving_mode = routing_res["serving_mode"]
            
            this_tick_risk[sid] = comp_risk
            
            if risk_level in ["WARNING", "CRITICAL"]:
                if sid not in station_alert_state:
                    total_alerts += 1
                    alert_id = f"ALERT_{sid}_{curr_tick}"
                    station_alert_state[sid] = {
                        "id": alert_id,
                        "start_tick": curr_tick,
                        "serving_mode": serving_mode,
                        "served_risk": comp_risk
                    }
            else:
                if sid in station_alert_state:
                    del station_alert_state[sid]

        prev_tick_risk = this_tick_risk
        
        # 3. Associate predictions with anomalies
        for aid, track in anomaly_tracking.items():
            if track["first_prediction_tick"] is None:
                sid = track["station_id"]
                if sid in station_alert_state:
                    track["first_prediction_tick"] = station_alert_state[sid]["start_tick"]
                    track["serving_mode"] = station_alert_state[sid]["serving_mode"]
                    track["served_risk"] = station_alert_state[sid]["served_risk"]
                    matched_alerts.add(station_alert_state[sid]["id"])

    # 4. Compile Metrics
    num_events = len(anomaly_tracking)
    num_detected = sum(1 for a in anomaly_tracking.values() if a["first_prediction_tick"] is not None)
    num_missed = num_events - num_detected
    
    all_lead_times = []
    
    for aid, track in anomaly_tracking.items():
        type_metrics[track["anomaly_type"]]["events"] += 1
        if track["first_prediction_tick"] is not None:
            type_metrics[track["anomaly_type"]]["detected"] += 1
            lt = track["actual_event_tick"] - track["first_prediction_tick"]
            type_metrics[track["anomaly_type"]]["lead_times"].append(lt)
            all_lead_times.append(lt)

    median_lt = np.median(all_lead_times) if all_lead_times else 0.0
    p90_lt = np.percentile(all_lead_times, 90) if all_lead_times else 0.0
    
    false_alarm_rate = (total_alerts - len(matched_alerts)) / total_alerts if total_alerts > 0 else 0.0
    
    print("\n" + "="*50)
    print("P1.2: PREDICTION LEAD-TIME EVALUATION RESULTS")
    print("="*50)
    print(f"Total Events Injected: {num_events}")
    print(f"Total Events Detected: {num_detected} ({(num_detected/num_events*100) if num_events else 0:.1f}%)")
    print(f"Total Events Missed:   {num_missed}")
    print(f"Median Lead Time:      {median_lt:.1f} ticks")
    print(f"P90 Lead Time:         {p90_lt:.1f} ticks")
    print(f"System False Alarms:   {total_alerts - len(matched_alerts)}")
    print(f"False Alarm Rate:      {false_alarm_rate*100:.1f}%\n")
    
    print("--- Per-Anomaly Type Results ---")
    for atype, m in type_metrics.items():
        det_rate = (m["detected"] / m["events"] * 100) if m["events"] > 0 else 0
        type_med = np.median(m["lead_times"]) if m["lead_times"] else 0
        print(f"  {atype.upper()}:")
        print(f"    Events:   {m['events']}")
        print(f"    Detected: {m['detected']} ({det_rate:.1f}%)")
        print(f"    Med. LT:  {type_med:.1f} ticks\n")

if __name__ == "__main__":
    run_evaluation(sim_ticks=15000)
