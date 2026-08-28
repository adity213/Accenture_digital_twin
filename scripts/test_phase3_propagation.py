"""
scripts/test_phase3_propagation.py
Test script to investigate fault propagation behavior when sudden_stoppage is injected.
"""
import sys
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
from simulator.topology import build_line_topology
from simulator.generator import LineSimulator
from pipeline.spc import SPCEngine
from pipeline.virtual_sensor import VirtualSensorEngine
from pipeline.confidence import ConfidenceEngine
from pipeline.risk_model import RiskScoringModel
from pipeline.propagation import GraphPropagationEngine

def test_propagation():
    topology = build_line_topology(seed=42)
    stations_meta = topology["stations"]
    simulator = LineSimulator(seed=42, custom_topology=topology)
    spc_engine = SPCEngine(lambda_ewma=0.3, z_threshold=3.0)
    virtual_sensor_engine = VirtualSensorEngine(stations_meta)
    confidence_engine = ConfidenceEngine(w1=0.5, w2=0.3, w3=0.2)
    
    model_path = Path("data/risk_model.joblib")
    if model_path.exists():
        risk_model = joblib.load(model_path)
    else:
        risk_model = RiskScoringModel()
        
    propagation_engine = GraphPropagationEngine(topology)
    
    # Run warmup for 30 ticks
    for _ in range(30):
        simulator.step()
        
    target_station = "ST06" # Mid-line Framing Main Station (Body)
    print(f"\n[PHASE 3 TEST] Injecting sudden_stoppage at {target_station} (tick {simulator.current_tick + 1})...")
    simulator.anomaly_mgr.inject_sudden_stoppage(target_station, simulator.current_tick + 1, duration_ticks=30)
    
    prev_tick_risk = {sid: 0.0 for sid in stations_meta}
    
    print("\nTracing next 20 ticks:")
    print(f"{'Tick':<6} | {'ST06 Risk':<10} | {'ST06 Buffer':<12} | {'Downstream Buffer (ST07, ST08)':<32} | {'Propagation Map Populated?':<28}")
    print("-" * 100)
    
    for step_i in range(1, 21):
        tick_result = simulator.step()
        events = tick_result["events"]
        event_map = {e["station_id"]: e for e in events}
        
        station_states = {}
        raw_risks = {}
        current_buffers = {}
        this_tick_risk = {}
        
        for sid in stations_meta:
            meta = stations_meta[sid]
            ev = event_map.get(sid, {})
            target_ct = meta["target_cycle_time_s"]
            is_blackout = ev.get("is_blackout", False)
            actual_ct = ev.get("cycle_time_s")
            
            imputed_data = None
            if is_blackout or actual_ct is None:
                imputed_data = virtual_sensor_engine.impute_station_telemetry(sid, simulator.current_tick, event_map)
                actual_ct = imputed_data["imputed_cycle_time_s"]
                imputation_disagreement = imputed_data["imputation_disagreement"]
            else:
                imputation_disagreement = 0.0

            spc_res = spc_engine.update_station(
                sid, actual_ct, target_ct,
                vibration=ev.get("vibration"),
                station_type=meta.get("station_type") or meta.get("type")
            )
            data_conf = confidence_engine.compute_data_confidence(
                sensor_tier=meta["sensor_tier"],
                is_blackout=is_blackout,
                ticks_since_last_reading=3 if is_blackout else 0,
                imputation_disagreement=imputation_disagreement
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
                shift_tick=simulator.current_tick,
                zone=meta.get("zone", "Body"),
                station_type=meta.get("station_type") or meta.get("type", "RoboticWeld")
            )
            bn_risk, def_risk, risk_level = risk_model.predict_risk(feats)
            comp_risk = max(bn_risk, def_risk)
            this_tick_risk[sid] = comp_risk
            raw_risks[sid] = comp_risk
            current_buffers[sid] = ev.get("buffer_level") if ev.get("buffer_level") is not None else int(meta["buffer_capacity_units"] * 0.5)
            station_states[sid] = {
                "composite_risk": comp_risk,
                "is_stopped": ev.get("is_stopped", False),
                "buffer_level": current_buffers[sid]
            }

        prev_tick_risk = this_tick_risk
        
        propagation_map = {}
        for sid, state in station_states.items():
            if (state.get("composite_risk") or 0.0) > 0.50:
                prop_res = propagation_engine.compute_propagation(sid, raw_risks, current_buffers)
                propagation_map[sid] = prop_res
                
        is_pop = len(propagation_map) > 0
        st6_risk = station_states["ST06"]["composite_risk"]
        st6_buf = station_states["ST06"]["buffer_level"]
        st7_buf = station_states["ST07"]["buffer_level"]
        st8_buf = station_states["ST08"]["buffer_level"]
        
        print(f"t+{step_i:<4} | {st6_risk:>9.3f} | {st6_buf:>11d} | ST07:{st7_buf} units, ST08:{st8_buf} units     | {str(is_pop):<6} (Keys: {list(propagation_map.keys())})")
        if step_i == 1 and is_pop:
            prop_tree = propagation_map[target_station]["downstream_impact_tree"]
            print(f"\nSample downstream impact tree from {target_station} at t+1:")
            for item in prop_tree[:4]:
                print(f"  -> {item['station_id']} ({item['station_name']}): Hops={item['distance_hops']}, Prop Risk={item['propagated_risk']}, TimeToImpact={item['time_to_impact_min']}min")
            print()

if __name__ == "__main__":
    test_propagation()
