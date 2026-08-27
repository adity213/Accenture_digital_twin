"""
DigitalTwin.ai - Training Dataset Generator

Produces a labeled dataset for pipeline.risk_model.RiskScoringModel that is:

1. FEATURE-CONSISTENT with production: it runs the exact same SPCEngine,
   VirtualSensorEngine, ConfidenceEngine, and RiskScoringModel.extract_features()
   that api/main.py uses at serving time, so there's no train/serve skew.

2. LEAKAGE-SAFE: labels for tick t are built from a STRICTLY FUTURE window
   (t+1 .. t+horizon) in a second pass over already-simulated history. Nothing
   about the label is visible to the feature vector computed at tick t.
   NOTE: for the last `horizon` ticks of each run, this window is truncated --
   those rows are systematically less likely to be labeled positive. Negligible
   at --ticks-per-run 4000, but don't treat it as exactly equivalent to the rest.

3. BALANCED / BIAS-AUDITED: anomalies are injected via
   simulator/anomaly_campaign.py, which spreads every anomaly type evenly across
   every zone (not clustered on a few "demo-convenient" stations like the
   hardcoded ST22 inspection point in api/main.py's manual injection endpoint),
   with randomized severity/duration. The script prints a coverage/positive-rate
   breakdown by zone, station_type and sensor_tier at the end so you can
   actually see whether any subgroup is under-represented before you train on it.

4. FIXES A LIVE BUG: api/main.py currently calls extract_features(..., upstream_risks=[])
   -- always empty -- so 2 of the model's 11 features (avg/max upstream starvation risk)
   are permanently zero in production. This script computes them properly via a
   topologically-ordered pass using the previous tick's risk proxy. Apply the same
   fix to api/main.py's process_simulation_tick() once you're happy with results here
   (see Phase 1.1 in the main prompt -- this is not optional, it's train/serve parity).

Usage:
    python scripts/generate_training_data.py --out data/training_dataset.csv \
        --seeds 6 --ticks-per-run 4000 --horizon 15
"""
import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.generator import LineSimulator
from simulator.anomaly_campaign import generate_balanced_campaign, apply_campaign_event
from pipeline.spc import SPCEngine
from pipeline.virtual_sensor import VirtualSensorEngine
from pipeline.confidence import ConfidenceEngine
from pipeline.risk_model import RiskScoringModel, FEATURE_NAMES

# Matches the CRITICAL processing-time threshold already used elsewhere in the
# codebase (README core-parameters table / risk_model.py fallback heuristic).
BOTTLENECK_CT_RATIO_THRESHOLD = 1.30


def _topo_order(topology: Dict[str, Any]) -> List[str]:
    indeg = {sid: 0 for sid in topology["stations"]}
    adj = defaultdict(list)
    for u, v in topology["edges"]:
        indeg[v] += 1
        adj[u].append(v)
    frontier = [sid for sid, d in indeg.items() if d == 0]
    order = []
    while frontier:
        n = frontier.pop()
        order.append(n)
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                frontier.append(m)
    return order


def run_one_seed(seed: int, num_ticks: int, horizon: int) -> List[Dict[str, Any]]:
    sim = LineSimulator(seed=seed)
    topology = sim.topology
    stations_meta = topology["stations"]
    topo_order = _topo_order(topology)

    campaign_rng = random.Random(seed * 7919 + 13)
    campaign = generate_balanced_campaign(topology, campaign_rng, num_ticks)
    campaign_by_tick: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for ev in campaign:
        campaign_by_tick[ev["start_tick"]].append(ev)

    spc_engine = SPCEngine()
    vs_engine = VirtualSensorEngine(stations_meta)
    conf_engine = ConfidenceEngine()
    risk_model = RiskScoringModel()  # only extract_features() is used here, never predict/fit

    prev_tick_risk: Dict[str, float] = {sid: 0.0 for sid in stations_meta}
    per_station_rows: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for t in range(1, num_ticks + 1):
        for ev in campaign_by_tick.get(t, []):
            apply_campaign_event(sim.anomaly_mgr, ev)

        tick_result = sim.step()
        event_map = {e["station_id"]: e for e in tick_result["events"]}
        this_tick_risk: Dict[str, float] = {}

        for sid in topo_order:
            meta = stations_meta[sid]
            ev = event_map.get(sid, {})
            target_ct = meta["target_cycle_time_s"]
            is_blackout = ev.get("is_blackout", False)
            actual_ct = ev.get("cycle_time_s")

            if is_blackout or actual_ct is None:
                imputed = vs_engine.impute_station_telemetry(sid, sim.current_tick, event_map)
                actual_ct = imputed["imputed_cycle_time_s"]
                imputation_disagreement = imputed["imputation_disagreement"]
            else:
                imputation_disagreement = 0.0

            spc_res = spc_engine.update_station(sid, actual_ct, target_ct, vibration=ev.get("vibration"))
            data_conf = conf_engine.compute_data_confidence(
                sensor_tier=meta["sensor_tier"],
                is_blackout=is_blackout,
                ticks_since_last_reading=3 if is_blackout else 0,
                imputation_disagreement=imputation_disagreement,
            )

            # Real upstream-risk propagation (production currently passes upstream_risks=[]
            # -- see module docstring). Uses previous tick's proxy risk so it's causal.
            upstream_risks = [prev_tick_risk.get(u, 0.0) for u in meta["upstream_ids"]]

            feats = risk_model.extract_features(
                station_id=sid,
                telemetry=ev,
                spc_result=spc_res,
                sensor_confidence=data_conf,
                upstream_risks=upstream_risks,
                target_cycle_time_s=target_ct,
                buffer_capacity=meta["buffer_capacity_units"],
                shift_tick=sim.current_tick,
                zone=meta["zone"],
                station_type=meta["station_type"],
            )

            raw_ct = ev.get("cycle_time_s")
            ct_ratio = (raw_ct / target_ct) if raw_ct else None
            is_stopped = bool(ev.get("is_stopped", False))
            defect_flag = bool(ev.get("defect_flag", False))

            # Cheap ground-truth-adjacent proxy purely to seed NEXT tick's upstream_risks
            # feature -- deliberately simple so it doesn't circularly depend on the model
            # we're about to train.
            proxy_risk = 0.0
            if is_stopped:
                proxy_risk = 1.0
            elif ct_ratio and ct_ratio > 1.15:
                proxy_risk = 0.6
            elif spc_res.get("trend") == "DRIFT_UP":
                proxy_risk = 0.4
            this_tick_risk[sid] = proxy_risk

            per_station_rows[sid].append({
                "tick": t,
                "zone": meta["zone"],
                "station_type": meta["station_type"],
                "sensor_tier": meta["sensor_tier"],
                "features": feats,
                "is_stopped": is_stopped,
                "ct_ratio": ct_ratio,
                "defect_flag": defect_flag,
            })

        prev_tick_risk = this_tick_risk

    # ---- Second pass: strictly-future labels, no leakage into features above ----
    dataset_rows: List[Dict[str, Any]] = []
    for sid, rows in per_station_rows.items():
        for i, row in enumerate(rows):
            window = rows[i + 1: i + 1 + horizon]
            bottleneck_label = 0
            defect_label = 0
            for w in window:
                if w["is_stopped"] or (w["ct_ratio"] is not None and w["ct_ratio"] > BOTTLENECK_CT_RATIO_THRESHOLD):
                    bottleneck_label = 1
                if w["defect_flag"]:
                    defect_label = 1
                if bottleneck_label and defect_label:
                    break
            dataset_rows.append({
                "seed": seed,
                "station_id": sid,
                "zone": row["zone"],
                "station_type": row["station_type"],
                "sensor_tier": row["sensor_tier"],
                "tick": row["tick"],
                **dict(zip(FEATURE_NAMES, row["features"])),
                "bottleneck_label": bottleneck_label,
                "defect_label": defect_label,
            })

    return dataset_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/training_dataset.csv")
    ap.add_argument("--seeds", type=int, default=6, help="independent simulated runs, each with its own randomized campaign")
    ap.add_argument("--ticks-per-run", type=int, default=4000)
    ap.add_argument("--horizon", type=int, default=15)
    ap.add_argument("--base-seed", type=int, default=1000)
    args = ap.parse_args()

    all_rows: List[Dict[str, Any]] = []
    for i in range(args.seeds):
        seed = args.base_seed + i
        print(f"[gen] seed={seed} ticks={args.ticks_per_run} ...")
        rows = run_one_seed(seed, args.ticks_per_run, args.horizon)
        all_rows.extend(rows)
        pos_bn = sum(r["bottleneck_label"] for r in rows)
        pos_def = sum(r["defect_label"] for r in rows)
        print(f"       rows={len(rows)}  bottleneck+={pos_bn} ({100*pos_bn/len(rows):.2f}%)  defect+={pos_def} ({100*pos_def/len(rows):.2f}%)")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\n[gen] wrote {len(all_rows)} rows -> {out_path}")

    def _breakdown(key: str):
        agg: Dict[str, List[int]] = defaultdict(lambda: [0, 0, 0])
        for r in all_rows:
            agg[r[key]][0] += r["bottleneck_label"]
            agg[r[key]][1] += r["defect_label"]
            agg[r[key]][2] += 1
        print(f"\n[bias audit] by {key}:")
        for k, (bn, de, tot) in sorted(agg.items()):
            print(f"   {str(k):16s} n={tot:7d}  bottleneck_rate={100*bn/tot:5.2f}%  defect_rate={100*de/tot:5.2f}%")

    _breakdown("zone")
    _breakdown("sensor_tier")
    _breakdown("station_type")

    print(
        "\n[note] If you see a subgroup with ~0% positive rate or wildly higher/lower than "
        "the rest, that's a coverage gap -- either widen simulator/anomaly_campaign.py's "
        "events_per_zone_per_type for that group, or accept and document the gap explicitly "
        "in your write-up rather than let the model quietly generalize badly there."
    )


if __name__ == "__main__":
    main()
