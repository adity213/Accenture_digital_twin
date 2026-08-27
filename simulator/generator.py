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
    def __init__(self, seed: int = 42, start_time: Optional[datetime] = None, custom_topology: Optional[Dict[str, Any]] = None):
        self.seed = seed
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
        self.vehicle_counter = 1000
        self.active_vehicles: Dict[str, Dict[str, Any]] = {}
        self.completed_vehicles: deque = deque(maxlen=500)
        
        for sid, s in self.stations.items():
            cap = s["buffer_capacity_units"]
            self.buffers[sid] = max(1, int(cap * 0.5))
            self.station_buffers[sid] = deque(maxlen=cap)
            self.station_processing[sid] = None

    def get_simulated_time(self) -> str:
        sim_dt = self.start_time + timedelta(minutes=self.current_tick)
        return sim_dt.strftime("%Y-%m-%d %H:%M:%S")

    def step(self) -> Dict[str, Any]:
        self.current_tick += 1
        sim_time_str = self.get_simulated_time()
        
        tick_telemetry: List[Dict[str, Any]] = []
        ground_truth: List[Dict[str, Any]] = []
        updated_genealogy_records: List[Dict[str, Any]] = []
        
        # 1. Vehicle Introduction at ST01 (Inflow rate ~85% per tick)
        if self.rng.random() < 0.85:
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
            if len(self.station_buffers["ST01"]) < self.stations["ST01"]["buffer_capacity_units"]:
                self.station_buffers["ST01"].append(vin)

        # 2. Process Station Telemetry & Physical States
        for sid, s in self.stations.items():
            target_ct = s["target_cycle_time_s"]
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
            
            # Base Gaussian cycle time
            sigma = target_ct * 0.04
            actual_ct = self.rng.gauss(target_ct, sigma)
            actual_ct = max(target_ct * 0.8, min(target_ct * 1.3, actual_ct))
            
            if is_stopped:
                actual_ct = target_ct * 4.5
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

            # Assign vehicle to station if slot is empty and buffer has queue
            if self.station_processing[sid] is None and len(self.station_buffers[sid]) > 0:
                self.station_processing[sid] = self.station_buffers[sid].popleft()

            current_vin = self.station_processing[sid]

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

            # Buffer count represents items in buffer plus current processing
            self.buffers[sid] = len(self.station_buffers[sid]) + (1 if current_vin else 0)

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
                    "sensor_tier": tier,
                    "is_blackout": False,
                    "is_stopped": is_stopped
                }
            tick_telemetry.append(event)

            # Vehicle Flow & Transition (if completed this cycle and station not stopped)
            if current_vin and not is_stopped and self.rng.random() < 0.88:
                if current_vin in self.active_vehicles:
                    self.active_vehicles[current_vin]["visit_history"].append({
                        "station_id": sid,
                        "tick": self.current_tick,
                        "cycle_time_s": round(actual_ct, 2),
                        "defect_flag": defect_flag
                    })
                    updated_genealogy_records.append(dict(self.active_vehicles[current_vin]))

                downstreams = s["downstream_ids"]
                if downstreams:
                    # Pick downstream with smallest queue buffer (load balancing)
                    target_down = min(downstreams, key=lambda d: len(self.station_buffers.get(d, [])))
                    if len(self.station_buffers[target_down]) < self.stations[target_down]["buffer_capacity_units"]:
                        self.station_buffers[target_down].append(current_vin)
                        if current_vin in self.active_vehicles:
                            self.active_vehicles[current_vin]["current_station"] = target_down
                else:
                    # Terminal Station (ST40 Buy-Off) Completed!
                    if current_vin in self.active_vehicles:
                        v_rec = self.active_vehicles.pop(current_vin)
                        v_rec["completion_tick"] = self.current_tick
                        v_rec["status"] = "COMPLETED"
                        self.completed_vehicles.append(v_rec)
                        updated_genealogy_records.append(v_rec)

                self.station_processing[sid] = None

        return {
            "tick": self.current_tick,
            "timestamp": sim_time_str,
            "events": tick_telemetry,
            "ground_truth": ground_truth,
            "buffers": dict(self.buffers),
            "genealogy_records": updated_genealogy_records
        }
