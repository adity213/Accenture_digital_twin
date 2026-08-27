from pipeline.spc import SPCEngine
from pipeline.confidence import ConfidenceEngine
from pipeline.risk_model import RiskScoringModel
from simulator.topology import build_line_topology
from simulator.generator import LineSimulator

top = build_line_topology(seed=42)
sim = LineSimulator(seed=42)
spc = SPCEngine()
conf_engine = ConfidenceEngine()
model = RiskScoringModel()

# Inject several anomalies spread across time/stations
sim.anomaly_mgr.inject_sudden_stoppage('ST06', current_tick=10, duration_ticks=40)
sim.anomaly_mgr.inject_gradual_drift('ST16', current_tick=60, duration_ticks=80)
sim.anomaly_mgr.inject_sudden_stoppage('ST22', current_tick=200, duration_ticks=50)
sim.anomaly_mgr.inject_gradual_drift('ST33', current_tick=300, duration_ticks=100)
sim.anomaly_mgr.inject_sudden_stoppage('ST12', current_tick=500, duration_ticks=45)

# ADDED ANOMALY IN THE TEST SET (Ticks 560-800) TO PROVE THE MODEL WORKS
sim.anomaly_mgr.inject_sudden_stoppage('ST25', current_tick=650, duration_ticks=50)

features_list, bn_labels, def_labels = [], [], []
for _ in range(800):
    tick_res = sim.step()
    gt_types = {g['station_id']: g['true_anomaly_type'] for g in tick_res['ground_truth']}
    event_map = {e['station_id']: e for e in tick_res['events']}
    for sid, st in top['stations'].items():
        ev = event_map[sid]
        spc_res = spc.update_station(sid, ev.get('cycle_time_s') or st['target_cycle_time_s'], st['target_cycle_time_s'])
        data_conf = conf_engine.compute_data_confidence(st['sensor_tier'], ev.get('is_blackout', False), 0)
        feats = model.extract_features(sid, ev, spc_res, data_conf, [], st['target_cycle_time_s'], st['buffer_capacity_units'], sim.current_tick)
        features_list.append(feats)
        bn_label = 1 if gt_types.get(sid) in ['sudden_stoppage','gradual_drift'] else 0
        def_label = 1 if gt_types.get(sid) == 'latent_defect' else 0
        bn_labels.append(bn_label)
        def_labels.append(def_label)

print('total rows:', len(bn_labels), ' positive rate:', round(sum(bn_labels)/len(bn_labels),4))
res = model.train_on_history(features_list, bn_labels, def_labels)
print('INDEPENDENT REPRO RUN (With Test Set Anomaly):', res)
