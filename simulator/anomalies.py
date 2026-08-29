"""
DigitalTwin.ai - Synthetic Anomaly Injector
Implements all 5 PRD Anomaly Types:
1. Gradual Equipment Drift (mimics tool wear / degradation)
2. Sudden Stoppage (80-90 min outage causing bottleneck ripple)
3. Latent / Late-Surfacing Defect (upstream defect flagged at downstream inspection)
4. Sensor Blackout (telemetry gap on manual stations for virtual sensing)
5. Energy Waste Pattern (high idle power surge during starvation / blockage)
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import random

@dataclass
class ActiveAnomaly:
    anomaly_id: str
    anomaly_type: str
    station_id: str
    start_tick: int
    duration_ticks: int
    severity: float = 1.0
    params: Dict[str, Any] = field(default_factory=dict)
    active: bool = True

class AnomalyManager:
    def __init__(self):
        self.active_anomalies: Dict[str, ActiveAnomaly] = {}
        self.anomaly_history: List[Dict[str, Any]] = []

    def inject_gradual_drift(self, station_id: str, current_tick: int, duration_ticks: int = 60, drift_factor: float = 0.45) -> str:
        aid = f"DRIFT_{station_id}_{current_tick}"
        anomaly = ActiveAnomaly(
            anomaly_id=aid,
            anomaly_type="gradual_drift",
            station_id=station_id,
            start_tick=current_tick,
            duration_ticks=duration_ticks,
            severity=1.0,
            params={"drift_factor": drift_factor}
        )
        self.active_anomalies[aid] = anomaly
        return aid

    def inject_sudden_stoppage(self, station_id: str, current_tick: int, duration_ticks: int = 85) -> str:
        aid = f"STOPPAGE_{station_id}_{current_tick}"
        anomaly = ActiveAnomaly(
            anomaly_id=aid,
            anomaly_type="sudden_stoppage",
            station_id=station_id,
            start_tick=current_tick,
            duration_ticks=duration_ticks,
            severity=1.0,
            params={"stoppage_reason": "Robotic weld gun mechanical seizure"}
        )
        self.active_anomalies[aid] = anomaly
        return aid

    def inject_latent_defect(self, source_station_id: str, inspection_station_id: str, current_tick: int, duration_ticks: int = 40, defect_type: str = "weld_porosity") -> str:
        aid = f"LATENT_{source_station_id}_{current_tick}"
        anomaly = ActiveAnomaly(
            anomaly_id=aid,
            anomaly_type="latent_defect",
            station_id=source_station_id,
            start_tick=current_tick,
            duration_ticks=duration_ticks,
            severity=1.0,
            params={"inspection_station_id": inspection_station_id, "defect_type": defect_type, "defect_rate": 0.05}
        )
        self.active_anomalies[aid] = anomaly
        return aid

    def inject_sensor_blackout(self, station_id: str, current_tick: int, duration_ticks: int = 35) -> str:
        aid = f"BLACKOUT_{station_id}_{current_tick}"
        anomaly = ActiveAnomaly(
            anomaly_id=aid,
            anomaly_type="sensor_blackout",
            station_id=station_id,
            start_tick=current_tick,
            duration_ticks=duration_ticks,
            severity=1.0,
            params={"blackout_mode": "no_telemetry_stream"}
        )
        self.active_anomalies[aid] = anomaly
        return aid

    def inject_energy_waste(self, station_id: str, current_tick: int, duration_ticks: int = 45, surge_multiplier: float = 2.4) -> str:
        aid = f"ENERGY_{station_id}_{current_tick}"
        anomaly = ActiveAnomaly(
            anomaly_id=aid,
            anomaly_type="energy_waste",
            station_id=station_id,
            start_tick=current_tick,
            duration_ticks=duration_ticks,
            severity=1.0,
            params={"surge_multiplier": surge_multiplier}
        )
        self.active_anomalies[aid] = anomaly
        return aid

    def inject_unscheduled_failure(self, station_id: str, current_tick: int, duration_ticks: int = 35) -> str:
        aid = f"UNSCHEDULED_FAIL_{station_id}_{current_tick}"
        anomaly = ActiveAnomaly(
            anomaly_id=aid,
            anomaly_type="unscheduled_failure",
            station_id=station_id,
            start_tick=current_tick,
            duration_ticks=duration_ticks,
            severity=1.0,
            params={"failure_mode": "mechanical_wear_outage"}
        )
        self.active_anomalies[aid] = anomaly
        return aid

    def get_station_anomaly_effects(self, station_id: str, current_tick: int) -> Dict[str, Any]:
        effects = {
            "cycle_time_multiplier": 1.0,
            "is_stopped": False,
            "latent_defect_flag": False,
            "latent_defect_type": None,
            "sensor_blackout": False,
            "power_multiplier": 1.0,
            "active_anomalies": []
        }
        
        expired = []
        for aid, anom in self.active_anomalies.items():
            if not anom.active:
                continue
            if current_tick < anom.start_tick:
                continue
            if current_tick >= anom.start_tick + anom.duration_ticks:
                anom.active = False
                expired.append(aid)
                continue
            
            if anom.station_id == station_id:
                effects["active_anomalies"].append({
                    "id": anom.anomaly_id,
                    "type": anom.anomaly_type,
                    "progress": (current_tick - anom.start_tick) / max(1, anom.duration_ticks)
                })
                
                if anom.anomaly_type == "gradual_drift":
                    progress = (current_tick - anom.start_tick) / max(1, anom.duration_ticks)
                    # Immediate +22% baseline jump that ramps up to +67%
                    base_drift = 0.22
                    ramp_drift = anom.params.get("drift_factor", 0.45) * progress
                    effects["cycle_time_multiplier"] = max(effects["cycle_time_multiplier"], 1.0 + base_drift + ramp_drift)
                
                elif anom.anomaly_type == "sudden_stoppage":
                    effects["is_stopped"] = True
                    effects["cycle_time_multiplier"] = 999.0
                    
                elif anom.anomaly_type == "latent_defect":
                    effects["latent_defect_flag"] = True
                    effects["latent_defect_type"] = anom.params.get("defect_type", "weld_porosity")
                    
                elif anom.anomaly_type == "sensor_blackout":
                    effects["sensor_blackout"] = True
                    
                elif anom.anomaly_type == "energy_waste":
                    effects["power_multiplier"] = max(effects["power_multiplier"], anom.params.get("surge_multiplier", 2.4))

                elif anom.anomaly_type == "unscheduled_failure":
                    progress = (current_tick - anom.start_tick) / max(1, anom.duration_ticks)
                    if progress > 0.5:
                        effects["is_stopped"] = True
                        effects["cycle_time_multiplier"] = 999.0
                    else:
                        effects["cycle_time_multiplier"] = max(effects["cycle_time_multiplier"], 1.30 + progress * 0.40)
                    
        return effects
