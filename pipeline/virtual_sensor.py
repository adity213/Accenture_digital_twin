"""
DigitalTwin.ai - Virtual Sensor Imputation Engine
Imputes missing or manual-tier station telemetry from:
(i) Correlated neighboring stations
(ii) Time-of-shift historical baselines
(iii) Multi-variable upstream/downstream flow regression
Calculates imputation disagreement metric (0-1).
"""
from typing import Dict, List, Any, Optional
import math

class VirtualSensorEngine:
    def __init__(self, stations_meta: Dict[str, Any]):
        self.stations_meta = stations_meta

    def impute_station_telemetry(
        self,
        station_id: str,
        current_tick: int,
        all_station_telemetry: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        meta = self.stations_meta.get(station_id, {})
        target_ct = meta.get("target_cycle_time_s", 60.0)
        cap = meta.get("buffer_capacity_units", 10)
        up_ids = meta.get("upstream_ids", [])
        down_ids = meta.get("downstream_ids", [])
        
        # 1. Neighboring correlated signals
        neighbor_cts = []
        for nid in up_ids + down_ids:
            if nid in all_station_telemetry and all_station_telemetry[nid].get("cycle_time_s") is not None:
                n_target = self.stations_meta.get(nid, {}).get("target_cycle_time_s", 60.0)
                ratio = all_station_telemetry[nid]["cycle_time_s"] / max(1.0, n_target)
                neighbor_cts.append(target_ct * ratio)
                
        est_neighbor = sum(neighbor_cts) / len(neighbor_cts) if neighbor_cts else target_ct
        
        # 2. Shift baseline with diurnal progress wave
        shift_minute = current_tick % 480  # 8-hour shift
        diurnal_factor = 1.0 + 0.03 * math.sin((shift_minute / 480.0) * 2 * math.pi)
        est_shift = target_ct * diurnal_factor
        
        # 3. Flow regression estimate
        up_buffers = [all_station_telemetry[u]["buffer_level"] for u in up_ids if u in all_station_telemetry and all_station_telemetry[u].get("buffer_level") is not None]
        avg_up_buf = sum(up_buffers)/len(up_buffers) if up_buffers else cap * 0.5
        est_flow = target_ct * (1.0 + (avg_up_buf / max(1, cap) - 0.5) * 0.08)
        
        # Blended imputation
        imputed_ct = 0.45 * est_neighbor + 0.35 * est_flow + 0.20 * est_shift
        imputed_buffer = int(avg_up_buf * 0.9)
        
        # Disagreement variance
        estimates = [est_neighbor, est_shift, est_flow]
        mean_est = sum(estimates) / 3.0
        disagreement = sum((x - mean_est)**2 for x in estimates) / (3.0 * (target_ct ** 2))
        disagreement_score = min(1.0, max(0.0, disagreement * 80.0))

        return {
            "station_id": station_id,
            "imputed_cycle_time_s": round(imputed_ct, 2),
            "imputed_buffer_level": max(0, min(cap, imputed_buffer)),
            "imputation_disagreement": round(disagreement_score, 3),
            "methods": {
                "neighbor_estimate": round(est_neighbor, 2),
                "shift_estimate": round(est_shift, 2),
                "flow_estimate": round(est_flow, 2)
            }
        }
