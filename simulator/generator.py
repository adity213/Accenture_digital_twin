"""
DigitalTwin.ai - Synthetic Assembly Line Simulator
Generates high-fidelity telemetry across 40 stations with:
- Gaussian cycle times & dynamic queue buffer dynamics
- Power & energy calculations
- Real-time vibration & temperature physics
- Full-line vehicle genealogy & VIN lifecycle tracking across all 40 stations
- Latent defect downstream inspection delay simulation
- Separate ground-truth anomaly logging (strict zero-leakage)
"""
import random
import math
import time
from collections import deque, defaultdict
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from .topology import build_line_topology
from .anomalies import AnomalyManager


class LineSimulator:
    def __init__(
        self,
        seed: int = 42,
        start_time: Optional[datetime] = None,
        custom_topology: Optional[Dict[str, Any]] = None,
        speed_factor: float = 1.0,
        sensor_dropout_rate: float = 0.0,
    ):
        self.seed = seed
        self.speed_factor = max(0.2, float(speed_factor))
        self.sensor_dropout_rate = max(0.0, min(1.0, float(sensor_dropout_rate)))
        self.rng = random.Random(seed)
        self.topology = custom_topology if custom_topology else build_line_topology(seed=seed)
        self.stations = self.topology["stations"]
        self.edges = self.topology["edges"]
        
        self.current_tick = 0
        self.start_time = start_time or datetime(2026, 3, 1, 6, 0, 0)
        self.anomaly_mgr = AnomalyManager()
        
        # Runtime station state & FIFO Queues
        self.buffers: Dict[str, int] = {}
        self.station_buffers: Dict[str, deque] = {}
        self.station_processing: Dict[str, Optional[str]] = {}
        self.station_dwell_ticks: Dict[str, int] = {}
        self.target_jph: float = 55.0
        self.vehicle_counter = 1000
        self.active_vehicles: Dict[str, Dict[str, Any]] = {}
        self.completed_vehicles: deque = deque(maxlen=50)
        
        for sid, s in self.stations.items():
            cap = s["buffer_capacity_units"]
            self.buffers[sid] = max(1, int(cap * 0.5))
            self.station_buffers[sid] = deque(maxlen=cap)
            self.station_processing[sid] = None
            self.station_dwell_ticks[sid] = 0

    def get_simulated_time(self) -> str:
        sim_dt = self.start_time + timedelta(minutes=self.current_tick)
        return sim_dt.strftime("%Y-%m-%d %H:%M:%S")

    def step(self) -> Dict[str, Any]:
        self.current_tick += 1
        sim_time_str = self.get_simulated_time()
        
        tick_telemetry: List[Dict[str, Any]] = []
        ground_truth: List[Dict[str, Any]] = []
        updated_genealogy_records: List[Dict[str, Any]] = []
        
        # 1. Vehicle Ingress at ST01 (Paced cleanly: max 12 active vehicles on the line to prevent overpiling)
        spawn_prob = min(0.6, max(0.15, self.target_jph / 90.0))
        if self.rng.random() < spawn_prob and len(self.active_vehicles) < 12 and len(self.station_buffers["ST01"]) == 0:
            self.vehicle_counter += 1
            vin = f"VIN-2026-{self.vehicle_counter:05d}"
            veh_info = {
                "vehicle_id": vin,
                "entry_tick": self.current_tick,
                "completion_tick": None,
                "current_station": "ST01",
                "status": "IN_PROGRESS",
                "visit_history": [{"station_id": "ST01", "tick": self.current_tick, "defect_flag": False}],
                "defect_flags": []
            }
            self.active_vehicles[vin] = veh_info
            self.station_buffers["ST01"].append(vin)

        # 2. Process Station Telemetry & Physical States
        dispatched_this_tick: Dict[str, str] = {}
        for sid, s in self.stations.items():
            nominal_target_ct = s["target_cycle_time_s"]
            effective_target_ct = nominal_target_ct / self.speed_factor
            tier = s["sensor_tier"]
            cap = s["buffer_capacity_units"]
            base_kw = s["power_base_kw"]
            
            # Anomaly modifications
            anom_effects = self.anomaly_mgr.get_station_anomaly_effects(sid, self.current_tick)
            
            is_stopped = anom_effects["is_stopped"]
            ct_multiplier = anom_effects["cycle_time_multiplier"]
            has_latent_defect = anom_effects["latent_defect_flag"]
            latent_type = anom_effects["latent_defect_type"]
            is_blackout = anom_effects["sensor_blackout"]
            power_multiplier = anom_effects["power_multiplier"]

            # Stochastic sensor network dropout stress testing
            if not is_blackout and self.sensor_dropout_rate > 0.0:
                if self.rng.random() < self.sensor_dropout_rate:
                    is_blackout = True
            
            # Log ground truth for active anomalies
            for an in anom_effects["active_anomalies"]:
                ground_truth.append({
                    "tick": self.current_tick,
                    "timestamp": sim_time_str,
                    "station_id": sid,
                    "true_anomaly_type": an["type"],
                    "severity": 1.0,
                    "details": {"anomaly_id": an["id"], "progress": an["progress"]}
                })
            
            # Base Gaussian cycle time calibrated to effective takt
            sigma = effective_target_ct * 0.04
            actual_ct = self.rng.gauss(effective_target_ct, sigma)
            actual_ct = max(effective_target_ct * 0.8, min(effective_target_ct * 1.3, actual_ct))
            
            if is_stopped:
                actual_ct = effective_target_ct * 4.5
            else:
                actual_ct *= ct_multiplier

            # Defect simulation & Genealogy Attachment
            defect_flag = False
            defect_type = None
            
            # Natural defect rate ~0.8%
            if self.rng.random() < 0.008:
                defect_flag = True
                defect_type = "surface_scratch" if s["zone"] == "Paint" else "fastener_undertorque"
            
            if has_latent_defect:
                defect_flag = True
                defect_type = latent_type or "weld_porosity"

            current_vin = self.station_processing[sid]
            if current_vin and not is_stopped:
                self.station_dwell_ticks[sid] += 1

            # Attach defect to current vehicle genealogy
            if defect_flag and current_vin and current_vin in self.active_vehicles:
                self.active_vehicles[current_vin]["defect_flags"].append({
                    "station_id": sid,
                    "tick": self.current_tick,
                    "type": defect_type
                })

            # Check if vehicle has inherited defect from upstream that downstream QC catches
            if sid in ["ST12", "ST22", "ST40"] and current_vin and current_vin in self.active_vehicles:
                prior_defects = self.active_vehicles[current_vin]["defect_flags"]
                if prior_defects:
                    defect_flag = True
                    defect_type = f"detected_{prior_defects[-1]['type']}"

            # Physics signals: vibration & temperature
            robotic_types = [
                "RoboticWeld", "RespotWeld", "MechanicalTorque", "RoboticTorque",
                "AutomatedTorque", "RoboticSpray", "RoboticUrethane", "LaserBrazing",
                "AutomatedMarriage", "MainFraming"
            ]
            base_vib = 1.2 if s["station_type"] in robotic_types else 0.4
            vib_noise = self.rng.gauss(0, 0.08)
            vibration = max(0.1, base_vib + vib_noise)

            base_temp = 24.0
            if s["station_type"] in ["ThermalOven"]:
                base_temp = 190.0
            elif s["station_type"] in ["ChemicalBath", "ElectroDeposition"]:
                base_temp = 55.0

            temp_noise = self.rng.gauss(0, 0.5)
            temperature = base_temp + temp_noise

            if is_stopped:
                vibration = 0.05
                temperature = base_temp + temp_noise
            elif ct_multiplier > 1.2:
                vibration += min(3.5, (ct_multiplier - 1.0) * 3.5)
                temperature += min(35.0, (ct_multiplier - 1.0) * 12.0)

            # Power & Energy (kW & kWh)
            if base_kw is not None:
                load_factor = 0.9 if not is_stopped else 0.25
                if power_multiplier > 1.0:
                    load_factor = min(2.5, load_factor * power_multiplier)
                power_kw = base_kw * load_factor + self.rng.gauss(0, 0.3)
                energy_kwh = (power_kw / 60.0)
            else:
                power_kw = None
                energy_kwh = None

            # Buffer count represents items in buffer queue plus current processing
            self.buffers[sid] = len(self.station_buffers[sid]) + (1 if current_vin else 0)
            queued_list = list(self.station_buffers[sid])
            required_dwell = max(1, math.ceil(actual_ct / 55.0))
            dwell_prog = round(min(1.0, self.station_dwell_ticks[sid] / max(1, required_dwell)), 2) if current_vin else 0.0

            # Telemetry Event Record
            if is_blackout:
                event = {
                    "tick": self.current_tick,
                    "timestamp": sim_time_str,
                    "station_id": sid,
                    "cycle_time_s": None,
                    "buffer_level": self.buffers[sid],
                    "buffer_capacity": cap,
                    "vibration": None,
                    "temperature": None,
                    "power_kw": None,
                    "energy_kwh": None,
                    "defect_flag": False,
                    "defect_type": None,
                    "vehicle_id": None,
                    "processing_vin": None,
                    "queued_vins": queued_list,
                    "is_processing": False,
                    "dwell_progress": 0.0,
                    "sensor_tier": tier,
                    "is_blackout": True,
                    "is_stopped": False
                }
            else:
                event = {
                    "tick": self.current_tick,
                    "timestamp": sim_time_str,
                    "station_id": sid,
                    "cycle_time_s": round(actual_ct, 2),
                    "buffer_level": self.buffers[sid],
                    "buffer_capacity": cap,
                    "vibration": round(vibration, 3),
                    "temperature": round(temperature, 2),
                    "power_kw": round(power_kw, 2) if power_kw is not None else None,
                    "energy_kwh": round(energy_kwh, 4) if energy_kwh is not None else None,
                    "defect_flag": defect_flag,
                    "defect_type": defect_type,
                    "vehicle_id": current_vin,
                    "processing_vin": current_vin,
                    "queued_vins": queued_list,
                    "is_processing": bool(current_vin and not is_stopped),
                    "dwell_progress": dwell_prog,
                    "sensor_tier": tier,
                    "is_blackout": False,
                    "is_stopped": is_stopped
                }
            tick_telemetry.append(event)

            # Check if current station finished its dwell cycle
            if current_vin and not is_stopped and self.station_dwell_ticks[sid] >= required_dwell:
                dispatched_this_tick[sid] = current_vin

        # Phase 2: Dispatch completed vehicles downstream (cleanly isolated from pickup)
        for sid, vin in dispatched_this_tick.items():
            s = self.stations[sid]
            downstreams = s["downstream_ids"]
            
            if downstreams:
                # Pick downstream with smallest queue buffer (load balancing)
                target_down = min(downstreams, key=lambda d: len(self.station_buffers.get(d, [])))
                if len(self.station_buffers[target_down]) < self.stations[target_down]["buffer_capacity_units"]:
                    self.station_buffers[target_down].append(vin)
                    if vin in self.active_vehicles:
                        self.active_vehicles[vin]["current_station"] = target_down
                        self.active_vehicles[vin]["visit_history"].append({
                            "station_id": target_down,
                            "tick": self.current_tick,
                            "defect_flag": False
                        })
                        updated_genealogy_records.append(dict(self.active_vehicles[vin]))
            else:
                # Terminal Station (ST40 Buy-Off) Completed!
                if vin in self.active_vehicles:
                    v_rec = self.active_vehicles.pop(vin)
                    v_rec["completion_tick"] = self.current_tick
                    v_rec["status"] = "COMPLETED"
                    self.completed_vehicles.append(v_rec)
                    updated_genealogy_records.append(v_rec)

            self.station_processing[sid] = None
            self.station_dwell_ticks[sid] = 0

        # Phase 3: Admit next queued vehicle into empty cradles
        for sid in self.stations.keys():
            if self.station_processing[sid] is None and len(self.station_buffers[sid]) > 0:
                self.station_processing[sid] = self.station_buffers[sid].popleft()
                self.station_dwell_ticks[sid] = 0

        return {
            "tick": self.current_tick,
            "timestamp": sim_time_str,
            "events": tick_telemetry,
            "ground_truth": ground_truth,
            "buffers": dict(self.buffers),
            "genealogy_records": updated_genealogy_records
        }
