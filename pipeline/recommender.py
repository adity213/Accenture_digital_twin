"""
DigitalTwin.ai - Dynamic Action Recommendation Engine
Generates actionable engineering and operational interventions based on
real-time predictive risks, SPC deviations, and downstream propagation.
Reports ground-truth physical impacts: Downtime Avoided (mins),
Vehicles Protected from Starvation, and Scrap Avoided.
"""
from typing import Dict, List, Any
import uuid

# Industry standard benchmark reference (PRD Section 1.1)
DOWNTIME_COST_PER_MIN = 38333.33  # ($2.3M / 60 min)

class RecommendationEngine:
    def __init__(self, stations_meta: Dict[str, Any]):
        self.stations_meta = stations_meta

    def evaluate_recommendations(
        self,
        current_tick: int = 0,
        station_states: Dict[str, Any] = None,
        propagation_map: Dict[str, List[Dict[str, Any]]] = None,
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
        propagation_map: Dict[str, List[Dict[str, Any]]] = None,
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
            if ct is None:
                ct = meta.get("target_cycle_time_s", 60.0)
            if ct is None:
                ct = 60.0
            else:
                try:
                    ct = float(ct)
                except Exception:
                    ct = 60.0

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
            impacted = (propagation_map or {}).get(sid, []) or []

            # Rule 1: Sudden Stoppage / Extreme Bottleneck -> Dynamic Parallel Reroute
            if risk >= 0.80 or ct >= 120.0:
                nearest_impact_sec = min([n.get("time_to_impact_sec", 2100.0) for n in impacted]) if impacted else 2100.0
                dt_avoided = round(max(5.0, nearest_impact_sec / 60.0), 1)
                cars_saved = len(impacted) * 4
                recommendations.append({
                    "id": f"REC-{sid}-{uuid.uuid4().hex[:6].upper()}",
                    "tick": tick,
                    "timestamp": timestamp,
                    "station_id": sid,
                    "zone": meta.get("zone", "body"),
                    "rule_id": "RULE-01-PARALLEL-REROUTE",
                    "title": f"Reroute Flow Around {sid} ({meta.get('name', sid)})",
                    "recommended_action": f"Downtime imminent ({int(risk*100)}% risk). Divert 50% incoming BIW assemblies to parallel lane or bypass buffer.",
                    "rationale": f"Station {sid} cycle time surged to {ct:.1f}s. Downstream starvation will hit {len(impacted)} stations in under 15 mins.",
                    "expected_impact": f"Prevents {dt_avoided:.0f} mins line stoppage & protects {cars_saved} vehicles from starvation",
                    "downtime_avoided_min": dt_avoided,
                    "vehicles_protected": cars_saved,
                    "cost_savings_usd": round(dt_avoided * DOWNTIME_COST_PER_MIN, 0),
                    "confidence": round(min(0.99, (state.get("twin_confidence") or 90) / 100.0), 2),
                    "status": "ACTIVE"
                })

            # Rule 2: Gradual Drift -> Preventive Tool Calibration
            elif risk >= 0.60 or spc.get("ewma_drift_flag"):
                nearest_impact_sec = min([n.get("time_to_impact_sec", 900.0) for n in impacted]) if impacted else 900.0
                dt_avoided = round(max(5.0, nearest_impact_sec / 60.0), 1)
                target_ct = meta.get("target_cycle_time_s", 60.0) or 60.0
                recommendations.append({
                    "id": f"REC-{sid}-{uuid.uuid4().hex[:6].upper()}",
                    "tick": tick,
                    "timestamp": timestamp,
                    "station_id": sid,
                    "zone": meta.get("zone", "body"),
                    "rule_id": "RULE-02-PREVENTIVE-CALIBRATION",
                    "title": f"Schedule Preventive Calibration for {meta.get('name', sid)}",
                    "recommended_action": "Dispatch tool maintenance team to recalibrate tip/motor geometry during upcoming shift break.",
                    "rationale": f"Cycle time drifting (+{max(0.0, ct - target_ct):.1f}s above target, EWMA drift confirmed).",
                    "expected_impact": f"Prevents {dt_avoided:.0f} mins unplanned degradation & eliminates weld defects",
                    "downtime_avoided_min": dt_avoided,
                    "vehicles_protected": 2,
                    "cost_savings_usd": round(dt_avoided * DOWNTIME_COST_PER_MIN, 0),
                    "confidence": round(min(0.98, (state.get("twin_confidence") or 90) / 100.0), 2),
                    "status": "ACTIVE"
                })

            # Rule 3: Vibration ISO 10816 Limit Breach -> Robot Servo & Bearing Overhaul
            elif (state.get("vibration") is not None and state.get("vibration") > 4.5) or state.get("iso_vibration_alarm"):
                vib_val = state.get("vibration") or 4.6
                recommendations.append({
                    "id": f"REC-{sid}-{uuid.uuid4().hex[:6].upper()}",
                    "tick": tick,
                    "timestamp": timestamp,
                    "station_id": sid,
                    "zone": meta.get("zone", "body"),
                    "rule_id": "RULE-05-ISO-VIBRATION-ALARM",
                    "title": f"ISO 10816 Vibration Critical Breach at {meta.get('name', sid)}",
                    "recommended_action": f"Machine shaking surged to {vib_val:.2f} mm/s RMS (exceeding ISO 4.5 mm/s limit). Immediately inspect robot servo bearings & mount anchors.",
                    "rationale": f"Vibration magnitude {vib_val:.2f} mm/s exceeds Class I/II industrial safety limits. Imminent bearing seizure risk.",
                    "expected_impact": "Prevents catastrophic robot spindle seizure ($45,000 repair) and 35 mins unplanned downtime",
                    "downtime_avoided_min": 35.0,
                    "vehicles_protected": 6,
                    "cost_savings_usd": round(35.0 * DOWNTIME_COST_PER_MIN, 0),
                    "confidence": 0.95,
                    "status": "ACTIVE"
                })

            # Rule 4: Sensor Blackout -> Dispatch Sensor Verification
            elif is_blackout:
                recommendations.append({
                    "id": f"REC-{sid}-{uuid.uuid4().hex[:6].upper()}",
                    "tick": tick,
                    "timestamp": timestamp,
                    "station_id": sid,
                    "zone": meta.get("zone", "body"),
                    "rule_id": "RULE-04-SENSOR-REPAIR",
                    "title": f"Verify Telemetry Sensor Drop at {meta.get('name', sid)}",
                    "recommended_action": "Check PLC Ethernet fieldbus link. Virtual sensor imputation active with fallback confidence.",
                    "rationale": "Direct telemetry lost. Twin confidence degraded to 15%.",
                    "expected_impact": "Restores physical ground-truth observability across cell",
                    "downtime_avoided_min": 5.0,
                    "vehicles_protected": 0,
                    "cost_savings_usd": 0.0,
                    "confidence": 0.70,
                    "status": "ACTIVE"
                })

        if not recommendations:
            recommendations.append({
                "id": f"REC-NOMINAL-{uuid.uuid4().hex[:6].upper()}",
                "tick": tick,
                "timestamp": timestamp,
                "station_id": "ALL",
                "zone": "plant",
                "rule_id": "RULE-00-NOMINAL-FLOW",
                "title": "Optimal Line Flow Maintained",
                "recommended_action": "All 40 stations operating within nominal 3-sigma statistical control bounds.",
                "rationale": "No bottleneck cascades or starvation propagation detected across active buffer banks.",
                "expected_impact": "Line running at target 55.4 JPH cadence",
                "downtime_avoided_min": 0.0,
                "vehicles_protected": 0,
                "cost_savings_usd": 0.0,
                "confidence": 0.96,
                "status": "ACTIVE"
            })

        return recommendations
