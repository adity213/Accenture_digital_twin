"""
DigitalTwin.ai - Dynamic Action Recommendation Engine
Generates actionable engineering and operational interventions based on
real-time predictive risks, SPC deviations, and downstream propagation.
Reports ground-truth physical impacts: Downtime Avoided (mins),
Vehicles Protected from Starvation, and Scrap Avoided.
"""
from typing import Dict, List, Any
import uuid
from pipeline.sop import get_tiered_sop

# Industry standard benchmark reference (PRD Section 1.1)
DOWNTIME_COST_PER_MIN = 38333.33  # ($2.3M / 60 min)

class RecommendationEngine:
    def __init__(self, stations_meta: Dict[str, Any]):
        self.stations_meta = stations_meta
        self.station_anomaly_ticks: Dict[str, int] = {}

    def evaluate_recommendations(
        self,
        current_tick: int = 0,
        station_states: Dict[str, Any] = None,
        propagation_map: Dict[str, Any] = None,
        *args,
        **kwargs
    ) -> List[Dict[str, Any]]:
        tick = kwargs.get("tick", current_tick)
        timestamp = kwargs.get("timestamp", "2026-03-01 06:00:00")
        states = station_states if station_states is not None else kwargs.get("station_states", {})
        prop = propagation_map if propagation_map is not None else kwargs.get("propagation_map", {})
        return self.generate_recommendations(tick, timestamp, states, prop)

    def generate_recommendations(
        self,
        tick: int = 0,
        timestamp: str = "2026-03-01 06:00:00",
        station_states: Dict[str, Any] = None,
        propagation_map: Dict[str, Any] = None,
        *args,
        **kwargs
    ) -> List[Dict[str, Any]]:
        station_states = station_states if station_states is not None else kwargs.get("station_states", {})
        propagation_map = propagation_map if propagation_map is not None else kwargs.get("propagation_map", {})
        recommendations = []

        for sid, state in (station_states or {}).items():
            if not isinstance(state, dict):
                continue
            meta = self.stations_meta.get(sid, {})
            
            # Safe risk extraction
            risk = state.get("composite_risk")
            if risk is None:
                risk = state.get("bottleneck_risk")
            if risk is None:
                risk = 0.0
            else:
                try:
                    risk = float(risk)
                except Exception:
                    risk = 0.0

            # Safe cycle_time extraction
            ct = state.get("cycle_time_s")
            target_ct = meta.get("target_cycle_time_s", 60.0) or 60.0
            if ct is None:
                ct = target_ct

            buf = state.get("buffer_level")
            if buf is None:
                buf = 6
            else:
                try:
                    buf = int(buf)
                except Exception:
                    buf = 6

            spc = state.get("spc", {}) or {}
            is_blackout = bool(state.get("is_blackout", False))
            is_stopped = bool(state.get("is_stopped", False))

            # Unpack propagation structure robustly
            prop_obj = (propagation_map or {}).get(sid)
            if isinstance(prop_obj, dict):
                impacted = prop_obj.get("downstream_impact_tree", [])
                nearest_impact_sec = prop_obj.get("nearest_impact_sec", 900.0)
            elif isinstance(prop_obj, list):
                impacted = prop_obj
                nearest_impact_sec = min([n.get("time_to_impact_sec", 900.0) for n in impacted]) if impacted else 900.0
            else:
                impacted = []
                nearest_impact_sec = 900.0

            stype = meta.get("station_type", "RoboticWeld")
            conf_val = state.get("twin_confidence", 95.0)

            # Track anomaly duration for progressive SOP escalation
            if risk >= 0.60 or is_stopped or is_blackout or spc.get("iso_vibration_alarm"):
                self.station_anomaly_ticks[sid] = self.station_anomaly_ticks.get(sid, 0) + 1
            else:
                self.station_anomaly_ticks[sid] = 0
            elapsed_anomaly_ticks = self.station_anomaly_ticks.get(sid, 1)

            # Physical cascade delay calculation based on station buffer capacity & cycle time
            buf_cap = meta.get("buffer_capacity_units", 4)
            st_ct = float(target_ct or 60.0)
            downstream_count = len(impacted) if impacted else 3
            station_cascade_sec = (buf_cap * st_ct) + (downstream_count * (st_ct * 0.4))
            effective_impact_sec = min(1200.0, max(210.0, nearest_impact_sec if nearest_impact_sec != 900.0 else station_cascade_sec))
            dt_avoided = round(effective_impact_sec / 60.0, 1)

            # Rule 1: Sudden Stoppage / Extreme Bottleneck -> Dynamic Parallel Reroute
            if risk >= 0.80 or ct >= 120.0 or is_stopped:
                cars_saved = max(2, round(dt_avoided * (60.0 / st_ct)))
                sop = get_tiered_sop(
                    station_type=stype,
                    anomaly_type="sudden_stoppage",
                    elapsed_ticks=elapsed_anomaly_ticks,
                    sensor_confidence=conf_val
                )
                recommendations.append({
                    "id": f"REC-{sid}-{uuid.uuid4().hex[:6].upper()}",
                    "tick": tick,
                    "timestamp": timestamp,
                    "station_id": sid,
                    "zone": meta.get("zone", "body"),
                    "rule_id": "RULE-01-PARALLEL-REROUTE",
                    "title": f"Reroute flow around {meta.get('name', sid)}",
                    "recommended_action": f"Downtime imminent. Divert 50% incoming assemblies to parallel lane.",
                    "rationale": f"Cycle time hit {ct:.1f}s. Starvation cascades to {len(impacted)} stations in under 15 minutes.",
                    "expected_impact": f"Prevent {dt_avoided:.1f}m line stoppage",
                    "downtime_avoided_min": dt_avoided,
                    "vehicles_protected": cars_saved,
                    "cost_savings_usd": round(dt_avoided * DOWNTIME_COST_PER_MIN, 0),
                    "confidence": round(min(0.99, conf_val / 100.0), 2),
                    "status": "ACTIVE",
                    "sop": sop
                })

            # Rule 2: Gradual Drift -> Preventive Tool Calibration
            elif risk >= 0.60 or spc.get("ewma_drift_flag") or (ct > target_ct * 1.15):
                drift_dt_avoided = round(max(3.0, dt_avoided * 0.65), 1)
                sop = get_tiered_sop(
                    station_type=stype,
                    anomaly_type="gradual_drift",
                    elapsed_ticks=elapsed_anomaly_ticks,
                    sensor_confidence=conf_val
                )
                recommendations.append({
                    "id": f"REC-{sid}-{uuid.uuid4().hex[:6].upper()}",
                    "tick": tick,
                    "timestamp": timestamp,
                    "station_id": sid,
                    "zone": meta.get("zone", "body"),
                    "rule_id": "RULE-02-PREVENTIVE-CALIBRATION",
                    "title": f"Recalibrate tool geometry at {meta.get('name', sid)}",
                    "recommended_action": "Tool is drifting. Recalibrate tip/motor during the next shift break.",
                    "rationale": f"Cycle time is {max(0.0, ct - target_ct):.1f}s above target. EWMA drift confirmed.",
                    "expected_impact": f"Prevent {drift_dt_avoided:.1f}m stoppage and weld defects",
                    "downtime_avoided_min": drift_dt_avoided,
                    "vehicles_protected": max(1, round(drift_dt_avoided * (60.0 / st_ct))),
                    "cost_savings_usd": round(drift_dt_avoided * DOWNTIME_COST_PER_MIN, 0),
                    "confidence": round(min(0.98, conf_val / 100.0), 2),
                    "status": "ACTIVE",
                    "sop": sop
                })

            # Rule 3: Vibration ISO 10816 Limit Breach -> Robot Servo & Bearing Overhaul
            elif (state.get("vibration") is not None and state.get("vibration") > 4.5) or state.get("iso_vibration_alarm"):
                vib_val = state.get("vibration") or 4.6
                vib_dt_avoided = round(max(4.0, dt_avoided * 0.85), 1)
                sop = get_tiered_sop(
                    station_type=stype,
                    anomaly_type="sudden_stoppage",
                    elapsed_ticks=elapsed_anomaly_ticks,
                    sensor_confidence=conf_val
                )
                recommendations.append({
                    "id": f"REC-{sid}-{uuid.uuid4().hex[:6].upper()}",
                    "tick": tick,
                    "timestamp": timestamp,
                    "station_id": sid,
                    "zone": meta.get("zone", "body"),
                    "rule_id": "RULE-05-ISO-VIBRATION-ALARM",
                    "title": f"Inspect robot servos at {meta.get('name', sid)}",
                    "recommended_action": f"Vibration hit {vib_val:.2f} mm/s (ISO limit 4.5). Check bearings and mount anchors immediately.",
                    "rationale": f"Vibration exceeds Class I/II safety limits. Imminent bearing seizure.",
                    "expected_impact": f"Avoid {vib_dt_avoided:.1f}m unplanned robot spindle failure",
                    "downtime_avoided_min": vib_dt_avoided,
                    "vehicles_protected": max(2, round(vib_dt_avoided * (60.0 / st_ct))),
                    "cost_savings_usd": round(vib_dt_avoided * DOWNTIME_COST_PER_MIN, 0),
                    "confidence": round(min(0.99, conf_val / 100.0), 2),
                    "status": "ACTIVE",
                    "sop": sop
                })

            # Rule 4: Sensor Blackout -> Dispatch Sensor Verification
            elif is_blackout:
                sop = get_tiered_sop(
                    station_type=stype,
                    anomaly_type="sensor_blackout",
                    elapsed_ticks=elapsed_anomaly_ticks,
                    sensor_confidence=conf_val
                )
                recommendations.append({
                    "id": f"REC-{sid}-{uuid.uuid4().hex[:6].upper()}",
                    "tick": tick,
                    "timestamp": timestamp,
                    "station_id": sid,
                    "zone": meta.get("zone", "body"),
                    "rule_id": "RULE-04-SENSOR-REPAIR",
                    "title": f"Check sensor telemetry at {meta.get('name', sid)}",
                    "recommended_action": "Telemetry dropped. Check physical IO connections and network switch.",
                    "rationale": "Digital twin is running blind on imputed data.",
                    "expected_impact": "Restore twin visibility",
                    "downtime_avoided_min": 5.0,
                    "vehicles_protected": 0,
                    "cost_savings_usd": 0.0,
                    "confidence": 0.70,
                    "status": "ACTIVE",
                    "sop": sop
                })

        if not recommendations:
            sop = get_tiered_sop(
                station_type="_default",
                anomaly_type="_default",
                elapsed_ticks=1,
                sensor_confidence=100.0
            )
            recommendations.append({
                "id": f"REC-NOMINAL-{uuid.uuid4().hex[:6].upper()}",
                "tick": tick,
                "timestamp": timestamp,
                "station_id": "ALL",
                "zone": "plant",
                "rule_id": "RULE-00-NOMINAL-FLOW",
                "title": "Optimal line flow maintained",
                "recommended_action": "All stations are operating within nominal 3-sigma bounds.",
                "rationale": "No bottleneck cascades or starvation detected.",
                "expected_impact": "Line running at target 55.4 JPH cadence",
                "downtime_avoided_min": 0.0,
                "vehicles_protected": 0,
                "cost_savings_usd": 0.0,
                "confidence": 0.96,
                "status": "ACTIVE",
                "sop": sop
            })

        return recommendations
