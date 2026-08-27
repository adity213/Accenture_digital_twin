"""
DigitalTwin.ai - Scenario & Out-of-Distribution (OOD) Dataset Generator

Generates distinct simulated datasets to evaluate model generalization across:
1. Baseline I.I.D. (Standard 40-station balanced campaign)
2. Spatial OOD: Train ST01-ST30 (Body, Paint, early Assembly) vs Test ST31-ST40 (Downstream Assembly)
3. Phenomenological OOD: Train on isolated single anomalies vs Test on compound multi-faults (Drift + Energy)
4. Operational Speed Stress: Accelerated takt time (+20% production velocity)
5. Severity Stress: Non-linear severe damage out of training distribution bounds
6. Sensor Degradation Stress: 40% stochastic telemetry dropouts stressing Virtual Sensor Imputation

Zero-leakage, feature-consistent with production pipeline.
"""
import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.generator import LineSimulator
from simulator.anomaly_campaign import (
    generate_scenario_campaign,
    apply_campaign_event,
    ANOMALY_TYPES
)
from pipeline.spc import SPCEngine
from pipeline.virtual_sensor import VirtualSensorEngine
from pipeline.confidence import ConfidenceEngine
from pipeline.risk_model import RiskScoringModel, FEATURE_NAMES

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


def simulate_scenario_run(
    seed: int,
    num_ticks: int,
    horizon: int = 15,
    station_whitelist: Optional[List[str]] = None,
    anomaly_types: Optional[List[str]] = None,
    include_compound: bool = False,
    severity_mode: str = "normal",
    speed_factor: float = 1.0,
    sensor_dropout_rate: float = 0.0,
    scenario_tag: str = "nominal",
) -> List[Dict[str, Any]]:
    sim = LineSimulator(
        seed=seed,
        speed_factor=speed_factor,
        sensor_dropout_rate=sensor_dropout_rate
    )
    topology = sim.topology
    stations_meta = topology["stations"]
    topo_order = _topo_order(topology)

    campaign_rng = random.Random(seed * 7919 + 31)
    campaign = generate_scenario_campaign(
        topology=topology,
        rng=campaign_rng,
        num_ticks=num_ticks,
        station_whitelist=station_whitelist,
        anomaly_types=anomaly_types,
        include_compound=include_compound,
        severity_mode=severity_mode,
        events_per_group=3,
    )

    campaign_by_tick: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for ev in campaign:
        campaign_by_tick[ev["start_tick"]].append(ev)

    spc_engine = SPCEngine()
    vs_engine = VirtualSensorEngine(stations_meta)
    conf_engine = ConfidenceEngine()
    risk_model = RiskScoringModel()

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
            target_ct = meta["target_cycle_time_s"] / speed_factor
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

            proxy_risk = 0.0
            if is_stopped:
                proxy_risk = 1.0
            elif ct_ratio and ct_ratio > 1.15:
                proxy_risk = 0.6
            elif spc_res.get("trend") == "DRIFT_UP":
                proxy_risk = 0.4
            this_tick_risk[sid] = proxy_risk

            if station_whitelist is None or sid in station_whitelist:
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

    # Second pass: strictly-future labeling
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
                "scenario": scenario_tag,
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


def save_dataset_csv(rows: List[Dict[str, Any]], out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"   [saved] {len(rows):6d} rows -> {out_path.name}")


def main():
    ap = argparse.ArgumentParser(description="Generate scenario validation datasets")
    ap.add_argument("--out-dir", default="data/scenarios")
    ap.add_argument("--ticks-per-run", type=int, default=1500)
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--horizon", type=int, default=15)
    ap.add_argument("--base-seed", type=int, default=1000)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stations_st01_st30 = [f"ST{i:02d}" for i in range(1, 31)]
    stations_st31_st40 = [f"ST{i:02d}" for i in range(31, 41)]

    print(f"[scenario_gen] Building datasets across {args.seeds} seeds ({args.ticks_per_run} ticks/run)...")

    # 1. Baseline I.I.D. Dataset (all 40 stations, standard single anomalies)
    print("\n1. Generating Baseline I.I.D. dataset (all stations, nominal conditions)...")
    base_rows = []
    for s_idx in range(args.seeds):
        base_rows.extend(simulate_scenario_run(
            seed=args.base_seed + s_idx,
            num_ticks=args.ticks_per_run,
            horizon=args.horizon,
            scenario_tag="baseline_iid"
        ))
    save_dataset_csv(base_rows, out_dir / "baseline_iid.csv")

    # 2. Spatial OOD: Train ST01-ST30, Test ST31-ST40
    print("\n2. Generating Spatial OOD: Train (ST01-ST30) & Test (ST31-ST40)...")
    spatial_train_rows = []
    spatial_test_rows = []
    for s_idx in range(args.seeds):
        spatial_train_rows.extend(simulate_scenario_run(
            seed=args.base_seed + s_idx,
            num_ticks=args.ticks_per_run,
            horizon=args.horizon,
            station_whitelist=stations_st01_st30,
            scenario_tag="spatial_train_st01_st30"
        ))
        spatial_test_rows.extend(simulate_scenario_run(
            seed=args.base_seed + 100 + s_idx,
            num_ticks=args.ticks_per_run,
            horizon=args.horizon,
            station_whitelist=stations_st31_st40,
            scenario_tag="spatial_test_st31_st40"
        ))
    save_dataset_csv(spatial_train_rows, out_dir / "train_spatial_st01_st30.csv")
    save_dataset_csv(spatial_test_rows, out_dir / "test_spatial_st31_st40.csv")

    # 3. Phenomenological OOD: Train on Isolated Anomalies vs Test on Compound Anomalies (Drift + Energy)
    print("\n3. Generating Phenomenological OOD: Train (Isolated) & Test (Compound Drift+Energy)...")
    isolated_train_rows = []
    compound_test_rows = []
    isolated_anomalies = ["gradual_drift", "sudden_stoppage", "sensor_blackout", "latent_defect"]
    for s_idx in range(args.seeds):
        isolated_train_rows.extend(simulate_scenario_run(
            seed=args.base_seed + s_idx,
            num_ticks=args.ticks_per_run,
            horizon=args.horizon,
            anomaly_types=isolated_anomalies,
            include_compound=False,
            scenario_tag="isolated_train"
        ))
        compound_test_rows.extend(simulate_scenario_run(
            seed=args.base_seed + 200 + s_idx,
            num_ticks=args.ticks_per_run,
            horizon=args.horizon,
            anomaly_types=["compound_drift_energy"],
            include_compound=True,
            scenario_tag="compound_test_drift_energy"
        ))
    save_dataset_csv(isolated_train_rows, out_dir / "train_isolated_anomalies.csv")
    save_dataset_csv(compound_test_rows, out_dir / "test_compound_anomalies.csv")

    # 4. Operational Speed Stress OOD (+20% Takt Acceleration)
    print("\n4. Generating Operational Speed Stress OOD (+20% line velocity)...")
    speed_test_rows = []
    for s_idx in range(args.seeds):
        speed_test_rows.extend(simulate_scenario_run(
            seed=args.base_seed + 300 + s_idx,
            num_ticks=args.ticks_per_run,
            horizon=args.horizon,
            speed_factor=1.20,
            scenario_tag="speed_stress_1.2x"
        ))
    save_dataset_csv(speed_test_rows, out_dir / "test_speed_stress.csv")

    # 5. Severity Stress OOD (Extreme Physical Damage)
    print("\n5. Generating Severity Stress OOD (extreme out-of-bounds wear)...")
    severity_test_rows = []
    for s_idx in range(args.seeds):
        severity_test_rows.extend(simulate_scenario_run(
            seed=args.base_seed + 400 + s_idx,
            num_ticks=args.ticks_per_run,
            horizon=args.horizon,
            severity_mode="extreme",
            scenario_tag="severity_stress_extreme"
        ))
    save_dataset_csv(severity_test_rows, out_dir / "test_severity_stress.csv")

    # 6. Sensor Network Degradation OOD (40% Telemetry Dropouts)
    print("\n6. Generating Sensor Network Degradation OOD (40% dropouts)...")
    sensor_test_rows = []
    for s_idx in range(args.seeds):
        sensor_test_rows.extend(simulate_scenario_run(
            seed=args.base_seed + 500 + s_idx,
            num_ticks=args.ticks_per_run,
            horizon=args.horizon,
            sensor_dropout_rate=0.40,
            scenario_tag="sensor_degradation_40pct"
        ))
    save_dataset_csv(sensor_test_rows, out_dir / "test_sensor_degraded.csv")

    print(f"\n[scenario_gen] Completed! All 8 scenario partitions written to {out_dir}/")


if __name__ == "__main__":
    main()
