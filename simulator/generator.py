"""
DigitalTwin.ai - Synthetic Assembly Line Simulator
Generates high-fidelity telemetry across 40 stations with:
- Gaussian cycle times & queue buffer dynamics
- Power & energy calculations
- Vibration & temperature physics
- Vehicle flow & genealogy tracking
- Separate ground-truth anomaly logging
"""
import random
import math
import time
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
        
        # Runtime station state
        self.buffers: Dict[str, int] = {}
        self.station_vehicles: Dict[str, Optional[str]] = {}
        self.vehicle_counter = 1000
        self.active_vehicles: Dict[str, Dict[str, Any]] = {}
        self.completed_vehicles: List[Dict[str, Any]] = []
        
        for sid, s in self.stations.items():
            # Initial buffer level roughly 40-60% of capacity
            cap = s["buffer_capacity_units"]
            self.buffers[sid] = max(1, int(cap * 0.5))
            self.station_vehicles[sid] = None

    def get_simulated_time(self) -> str:
        sim_dt = self.start_time + timedelta(minutes=self.current_tick)
        return sim_dt.strftime("%Y-%m-%d %H:%M:%S")

    def step(self) -> Dict[str, Any]:
        self.current_tick += 1
        sim_time_str = self.get_simulated_time()
        
        tick_telemetry: List[Dict[str, Any]] = []
        ground_truth: List[Dict[str, Any]] = []
        
        # Vehicle introduction at ST01
        if self.rng.random() < 0.85:
            self.vehicle_counter += 1
            vin = f"VIN-2026-{self.vehicle_counter:05d}"
            self.active_vehicles[vin] = {
                "vehicle_id": vin,
                "entry_tick": self.current_tick,
                "completion_tick": None,
                "current_station": "ST01",
                "visits": [{"station_id": "ST01", "tick": self.current_tick}],
                "defects": []
            }
            if self.station_vehicles["ST01"] is None:
                self.station_vehicles["ST01"] = vin

        # Process each station
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
            sigma = target_ct * 0.04  # 4% coefficient of variation
            actual_ct = self.rng.gauss(target_ct, sigma)
            actual_ct = max(target_ct * 0.8, min(target_ct * 1.3, actual_ct))
            
            if is_stopped:
                actual_ct = target_ct * 4.5  # Heavy delay / stoppage
            else:
                actual_ct *= ct_multiplier

            # Defect simulation
            defect_flag = False
            defect_type = None
            
            # Natural defect rate ~0.8%
            if self.rng.random() < 0.008:
                defect_flag = True
                defect_type = "surface_scratch" if s["zone"] == "Paint" else "fastener_undertorque"
            
            if has_latent_defect:
                defect_flag = True
                defect_type = latent_type or "weld_porosity"
                # Attach to current vehicle if present
                v_curr = self.station_vehicles.get(sid)
                if v_curr and v_curr in self.active_vehicles:
                    self.active_vehicles[v_curr]["defects"].append({
                        "station_id": sid,
                        "tick": self.current_tick,
                        "type": defect_type
                    })

            # Queueing buffer dynamics
            # Inflow from upstreams
            inflow = 0
            if not s["upstream_ids"]:
                inflow = 1 if self.rng.random() < 0.9 else 0
            else:
                # Buffer transfer from upstream stations
                for up_id in s["upstream_ids"]:
                    if self.buffers.get(up_id, 0) > 0 and self.rng.random() < 0.8:
                        inflow += 1
                        self.buffers[up_id] = max(0, self.buffers[up_id] - 1)
                        break
            
            # Outflow to current station processing
            outflow = 0
            if self.buffers[sid] > 0 and not is_stopped:
                outflow = 1 if self.rng.random() < 0.85 else 0

            self.buffers[sid] = max(0, min(cap, self.buffers[sid] + inflow - outflow))
            
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

            # Sensor blackout behavior (applies to any station when blackout is active)
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
                    "vehicle_id": self.station_vehicles.get(sid),
                    "sensor_tier": tier,
                    "is_blackout": False,
                    "is_stopped": is_stopped
                }
            
            tick_telemetry.append(event)

        return {
            "tick": self.current_tick,
            "timestamp": sim_time_str,
            "events": tick_telemetry,
            "ground_truth": ground_truth,
            "buffers": dict(self.buffers)
        }
