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


def lognormal_cycle_time(rng: random.Random, mean_ct: float, cv: float = 0.04) -> float:
    """
    Draws cycle time from a lognormal distribution parameterized so E[X] = mean_ct.
    Phase 18 replacement for hard-clipped Gaussian, avoiding artificial cliff at 1.3x.
    """
    sigma_ln = math.sqrt(math.log(1.0 + cv**2))
    mu_ln = math.log(mean_ct) - 0.5 * sigma_ln**2
    val = rng.lognormvariate(mu_ln, sigma_ln)
    return min(val, mean_ct * 2.5)  # soft cap on extreme outliers


def get_station_category(station: Dict[str, Any]) -> str:
    """
    Categorizes station into automated_precision, automated_process, or manual.
    Phase 19 category classification.
    """
    if station.get("sensor_tier") == "manual" or station.get("is_manual", False):
        return "manual"
    robotic_types = {
        "RoboticWeld", "RespotWeld", "MechanicalTorque", "RoboticTorque",
        "AutomatedTorque", "RoboticSpray", "RoboticUrethane", "LaserBrazing",
        "AutomatedMarriage", "MainFraming"
    }
    st_type = station.get("station_type") or station.get("type", "")
    if st_type in robotic_types:
        return "automated_precision"
    return "automated_process"


NO_DRIFT_CONTROL_STATIONS = {"ST03", "ST15", "ST31"}


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
        self.total_completed_vehicles: int = 0
        self.active_vehicles: Dict[str, Dict[str, Any]] = {}
        self.completed_vehicles: deque = deque(maxlen=50)
        self.station_dwell_seconds: Dict[str, float] = {}
        self.ingress_accumulator: float = 0.0
        
        for sid, s in self.stations.items():
            cap = s["buffer_capacity_units"]
            self.buffers[sid] = 0
            self.station_buffers[sid] = deque(maxlen=cap)
            self.station_processing[sid] = None
            self.station_dwell_ticks[sid] = 0
            self.station_dwell_seconds[sid] = 0.0

        # Latent load state per station (Phase 17)
        self.load_state: Dict[str, float] = {sid: 0.0 for sid in self.stations}

        # Emergent wear state per station & maintenance tracking (Phase 21)
        self.wear_state: Dict[str, float] = {
            sid: (0.0 if sid in NO_DRIFT_CONTROL_STATIONS else self.rng.uniform(0.0, 0.15))
            for sid in self.stations
        }
        self.maintenance_interval_ticks: int = 1440  # Daily preventive service window (1440 simulated minutes)
        self.maintenance_resets_count: int = 0
        self.unscheduled_failures_count: int = 0
        self.unscheduled_failure_stations: set = set()

        # Phase 25/P0b: Pre-compute shortest path to sink for routing estimates
        self.shortest_path_to_sink = self._compute_shortest_paths_to_sink()

    def reset_state(self):
        """Resets the simulator to a pristine empty state with paced takt ingress."""
        self.current_tick = 0
        self.vehicle_counter = 1000
        self.total_completed_vehicles = 0
        self.active_vehicles.clear()
        self.completed_vehicles.clear()
        self.ingress_accumulator = 0.0
        self.anomaly_mgr.active_anomalies.clear()
        for sid, s in self.stations.items():
            cap = s["buffer_capacity_units"]
            self.buffers[sid] = 0
            self.station_buffers[sid] = deque(maxlen=cap)
            self.station_processing[sid] = None
            self.station_dwell_ticks[sid] = 0
            self.station_dwell_seconds[sid] = 0.0
            self.load_state[sid] = 0.0
            self.wear_state[sid] = 0.0 if sid in NO_DRIFT_CONTROL_STATIONS else self.rng.uniform(0.0, 0.15)

    def _compute_shortest_paths_to_sink(self) -> Dict[str, int]:
        adj = {sid: set() for sid in self.stations}
        for u, v in self.edges:
            adj[u].add(v)
            
        terminals = [sid for sid, meta in self.stations.items() if not meta.get("downstream_ids")]
        
        dists = {sid: float('inf') for sid in self.stations}
        queue = deque()
        for t in terminals:
            dists[t] = 1
            queue.append(t)
            
        rev_adj = {sid: set() for sid in self.stations}
        for u, vs in adj.items():
            for v in vs:
                rev_adj[v].add(u)
                
        while queue:
            curr = queue.popleft()
            for prev in rev_adj[curr]:
                if dists[curr] + 1 < dists[prev]:
                    dists[prev] = dists[curr] + 1
                    queue.append(prev)
                    
        return {k: int(v) if v != float('inf') else 1 for k, v in dists.items()}

    def retopologize(self, new_topology: Dict[str, Any]):
        """
        Hot-reloads the assembly line DAG topology without destroying in-flight vehicle states,
        buffer FIFO queues, wear degradation, or simulation tick clocks (Issue 2).
        """
        self.topology = new_topology
        self.stations = new_topology["stations"]
        self.edges = new_topology["edges"]
        self.shortest_path_to_sink = self._compute_shortest_paths_to_sink()

        # Synchronize per-station state containers
        for sid, s in self.stations.items():
            cap = s.get("buffer_capacity_units", 4)
            if sid not in self.station_buffers:
                # Newly added station
                self.buffers[sid] = 0
                self.station_buffers[sid] = deque(maxlen=cap)
                self.station_processing[sid] = None
                self.station_dwell_ticks[sid] = 0
                self.station_dwell_seconds[sid] = 0.0
                self.load_state[sid] = 0.0
                self.wear_state[sid] = 0.0
            else:
                # Existing station: adjust deque capacity while preserving in-flight vehicles
                existing_items = list(self.station_buffers[sid])
                self.station_buffers[sid] = deque(existing_items, maxlen=cap)
                self.buffers[sid] = len(self.station_buffers[sid])

        # Clean up removed stations gracefully (if any)
        removed_sids = set(self.station_buffers.keys()) - set(self.stations.keys())
        for r_sid in removed_sids:
            orphaned = []
            if self.station_processing.get(r_sid):
                orphaned.append(self.station_processing[r_sid])
                self.station_processing[r_sid] = None
            orphaned.extend(list(self.station_buffers.get(r_sid, [])))
            self.station_buffers.pop(r_sid, None)
            self.buffers.pop(r_sid, None)
            self.station_dwell_ticks.pop(r_sid, None)
            self.station_dwell_seconds.pop(r_sid, None)
            self.load_state.pop(r_sid, None)
            self.wear_state.pop(r_sid, None)
            
            first_sid = list(self.stations.keys())[0] if self.stations else None
            for vin in orphaned:
                if vin in self.active_vehicles and first_sid:
                    self.active_vehicles[vin]["current_station"] = first_sid
                    self.station_buffers[first_sid].append(vin)

    def get_simulated_time(self) -> str:
        sim_dt = self.start_time + timedelta(minutes=self.current_tick)
        return sim_dt.strftime("%Y-%m-%d %H:%M:%S")

    def step(self) -> Dict[str, Any]:
        self.current_tick += 1
        sim_time_str = self.get_simulated_time()
        
        tick_telemetry: List[Dict[str, Any]] = []
        ground_truth: List[Dict[str, Any]] = []
        updated_genealogy_records: List[Dict[str, Any]] = []
        
        # Check for active issues across the line (Option 1: Andon Safety Ingress Lock)
        active_anom_list = list(self.anomaly_mgr.active_anomalies.values())
        is_andon_active = len(active_anom_list) > 0
        andon_reasons = [f"{a.anomaly_type}@{a.station_id}" for a in active_anom_list]
        self.andon_ingress_locked = is_andon_active
        self.andon_reason = ", ".join(andon_reasons) if andon_reasons else None

        # 1. Vehicle Ingress at ST01 (Paced Takt Ingress)
        st01_cap = self.stations["ST01"]["buffer_capacity_units"]
        max_line_wip = sum(1 + s["buffer_capacity_units"] for s in self.stations.values())
        
        # Little's Law WIP Cap Arithmetic
        line_transit_hours = 2497.0 / 3600.0  # 0.6936 hours
        wip_cap = max(10, min(int(math.ceil(self.target_jph * line_transit_hours * 1.25)), max_line_wip))

        # Takt-Paced Ingress Release: 1 vehicle at a time at Takt cadence T_takt = 3600 / target_jph
        takt_time_s = 3600.0 / max(10.0, self.target_jph)
        if not is_andon_active:
            self.ingress_accumulator += 60.0
            # Paced single-vehicle release at takt cadence, held if ST01 infeed buffer has >= 1 vehicle
            if (
                self.ingress_accumulator >= takt_time_s
                and len(self.active_vehicles) < wip_cap
                and len(self.station_buffers["ST01"]) < 1
            ):
                self.ingress_accumulator = max(0.0, self.ingress_accumulator - takt_time_s)
                self.vehicle_counter += 1
                vin = f"VIN-2026-{self.vehicle_counter:05d}"
                veh_info = {
                    "vehicle_id": vin,
                    "entry_tick": self.current_tick,
                    "completion_tick": None,
                    "current_station": "ST01",
                    "status": "IN_PROGRESS",
                    "visit_history": [{"station_id": "ST01", "tick": self.current_tick, "defect_flag": False}],
                    "route_station_ids": ["ST01"],
                    "defect_flags": []
                }
                self.active_vehicles[vin] = veh_info
                self.station_buffers["ST01"].append(vin)
            elif self.ingress_accumulator > takt_time_s * 2.0:
                self.ingress_accumulator = takt_time_s * 2.0

        # Periodic preventive maintenance service window (Phase 21: simulated 48-hr maintenance window)
        if self.current_tick > 0 and self.current_tick % self.maintenance_interval_ticks == 0:
            for sid in self.stations:
                if sid not in NO_DRIFT_CONTROL_STATIONS and self.wear_state[sid] > 0.65:
                    if self.rng.random() < 0.75:  # Realistic service coverage
                        self.wear_state[sid] = self.rng.uniform(0.05, 0.15)
                        self.maintenance_resets_count += 1

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
            
            # Phase 19: Station category classification & multipliers
            category = get_station_category(s)
            
            # Phase 24: 3-Shift Circadian Schedule (1440 ticks/day: Day 0-479, Evening 480-959, Night 960-1439)
            day_tick = (self.current_tick - 1) % 1440
            shift_tick = day_tick % 480
            tau_fatigue = shift_tick / 480.0  # 0.0 to 1.0 within shift
            
            if day_tick < 480:
                shift_name = "day"
                shift_index = 0
                is_night_shift = False
                shift_ct_mult = 1.00
                shift_defect_mult = 1.00
                shift_cv_mult = 1.00
            elif day_tick < 960:
                shift_name = "evening"
                shift_index = 1
                is_night_shift = False
                if category == "manual":
                    shift_ct_mult = 1.04
                    shift_defect_mult = 1.15
                    shift_cv_mult = 1.05
                else:
                    shift_ct_mult = 1.00
                    shift_defect_mult = 1.00
                    shift_cv_mult = 1.00
            else:
                shift_name = "night"
                shift_index = 2
                is_night_shift = True
                if category == "manual":
                    shift_ct_mult = 1.10
                    shift_defect_mult = 1.40
                    shift_cv_mult = 1.15
                else:
                    shift_ct_mult = 1.01
                    shift_defect_mult = 1.02
                    shift_cv_mult = 1.00

            # Within-shift fatigue modulation on manual stations (gradual fatigue with mid-shift break relief)
            if category == "manual":
                fatigue_growth = 0.05 * (tau_fatigue - 0.4 * math.sin(2.0 * math.pi * tau_fatigue))
                shift_ct_mult += max(0.0, fatigue_growth)
                shift_defect_mult += max(0.0, fatigue_growth * 1.5)

            ct_cv = {"automated_precision": 0.04, "automated_process": 0.06, "manual": 0.13}[category] * shift_cv_mult
            defect_prob = 0.008 * {"automated_precision": 0.6, "automated_process": 1.0, "manual": 2.8}[category] * shift_defect_mult

            # Phase 21: Emergent wear accumulation & unscheduled failure trigger
            if sid in NO_DRIFT_CONTROL_STATIONS:
                base_wear_rate = 0.0
            else:
                base_wear_rate = {"automated_precision": 0.00025, "automated_process": 0.00030, "manual": 0.00035}[category]
                shock = 0.04 if self.rng.random() < 0.0015 else 0.0
                self.wear_state[sid] = min(1.2, self.wear_state[sid] + base_wear_rate * (1.0 + max(0.0, self.load_state[sid])) + shock)

            # Trigger unscheduled failure if wear exceeds threshold
            if self.wear_state[sid] > 0.85 and not any(an["type"] == "unscheduled_failure" for an in anom_effects["active_anomalies"]):
                prob_fail = min(0.12, (self.wear_state[sid] - 0.85) * 0.35)
                if self.rng.random() < prob_fail:
                    self.anomaly_mgr.inject_unscheduled_failure(sid, self.current_tick, duration_ticks=35)
                    self.unscheduled_failures_count += 1
                    self.unscheduled_failure_stations.add(sid)
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

            # Phase 17: Latent load state AR(1) update coupled to wear and fatigue
            rho = 0.90
            innovation_sigma = 0.06
            wear_influence = getattr(self, "wear_state", {}).get(sid, 0.0) * 0.4
            fatigue_influence = 0.15 * (shift_ct_mult - 1.0)
            target_load_mean = wear_influence + fatigue_influence
            self.load_state[sid] = rho * self.load_state[sid] + (1 - rho) * target_load_mean + self.rng.gauss(0, innovation_sigma)
            self.load_state[sid] = max(-1.0, min(2.0, self.load_state[sid]))

            # Phase 18/19/24: Lognormal cycle time with load_state, shift fatigue & category CV
            load_ct_mult = 1.0 + 0.05 * self.load_state[sid]
            effective_mean_ct = effective_target_ct * max(0.8, min(1.3, load_ct_mult * shift_ct_mult))
            actual_ct = lognormal_cycle_time(self.rng, effective_mean_ct, cv=ct_cv)
            
            if is_stopped:
                actual_ct = effective_target_ct * 4.5
            else:
                actual_ct *= ct_multiplier

            # Defect simulation & Genealogy Attachment
            defect_flag = False
            defect_type = None
            
            # Natural defect rate with Phase 19 category multiplier
            if self.rng.random() < defect_prob:
                defect_flag = True
                defect_type = "surface_scratch" if s["zone"] == "Paint" else "fastener_undertorque"
            
            if has_latent_defect:
                defect_flag = True
                defect_type = latent_type or "weld_porosity"

            current_vin = self.station_processing[sid]
            prior_dwell = self.station_dwell_seconds[sid]
            t_remain = 0.0
            is_ready = False

            if current_vin and not is_stopped:
                time_needed_to_finish = max(0.0, actual_ct - prior_dwell)
                if 60.0 >= time_needed_to_finish:
                    # Completed during this 60s tick interval
                    t_remain = 60.0 - time_needed_to_finish
                    self.station_dwell_seconds[sid] = actual_ct
                    self.station_dwell_ticks[sid] = int(actual_ct // 60.0)
                    is_ready = True
                    dwell_prog = 1.0
                else:
                    # In progress
                    t_remain = 0.0
                    self.station_dwell_seconds[sid] += 60.0
                    self.station_dwell_ticks[sid] = int(self.station_dwell_seconds[sid] // 60.0)
                    is_ready = False
                    dwell_prog = round(min(1.0, self.station_dwell_seconds[sid] / max(1.0, actual_ct)), 2)
            else:
                dwell_prog = 0.0

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

            # Physics signals: vibration & temperature (driven by shared load_state)
            base_vib = 1.2 if category == "automated_precision" else 0.4
            load_factor = 1.0 + 0.35 * self.load_state[sid]
            vib_noise_sigma = 0.035 * (base_vib / 1.2)
            vib_noise = self.rng.gauss(0, vib_noise_sigma)
            vibration = max(0.05, base_vib * load_factor + vib_noise)

            base_temp = 24.0
            if s["station_type"] in ["ThermalOven"]:
                base_temp = 190.0
            elif s["station_type"] in ["ChemicalBath", "ElectroDeposition"]:
                base_temp = 55.0

            temp_noise = self.rng.gauss(0, 0.3)
            temperature = base_temp + (self.load_state[sid] * 3.0) + temp_noise

            # Phase 20/21: Decoupled anomaly-type-specific physical signatures
            active_types = {an["type"] for an in anom_effects["active_anomalies"]}
            has_drift = "gradual_drift" in active_types
            has_unscheduled_fail = "unscheduled_failure" in active_types

            if is_stopped:
                vibration = max(0.02, 0.05 + self.rng.gauss(0, 0.01))
                temperature = base_temp + temp_noise
            elif (has_drift or has_unscheduled_fail) and ct_multiplier > 1.0:
                # Mechanical wear / failure signature: vibration and temp rise specifically under gradual drift or unscheduled failure
                vibration += min(3.5, (ct_multiplier - 1.0) * 3.5)
                temperature += min(35.0, (ct_multiplier - 1.0) * 12.0)

            # Power & Energy (kW & kWh)
            if base_kw is not None:
                base_power_factor = 0.9 if not is_stopped else 0.25
                if (has_drift or has_unscheduled_fail) and not is_stopped and ct_multiplier > 1.0:
                    base_power_factor *= (1.0 + min(0.3, (ct_multiplier - 1.0) * 0.25))
                if power_multiplier > 1.0:
                    base_power_factor = min(2.5, base_power_factor * power_multiplier)
                eff_power_factor = base_power_factor * (load_factor if not is_stopped else 1.0)
                power_kw = max(0.0, base_kw * eff_power_factor + self.rng.gauss(0, 0.15))
                energy_kwh = (power_kw / 60.0)
            else:
                power_kw = None
                energy_kwh = None

            # Buffer count represents items in buffer queue plus current processing
            self.buffers[sid] = len(self.station_buffers[sid]) + (1 if current_vin else 0)
            queued_list = list(self.station_buffers[sid])

            downstreams = s.get("downstream_ids", [])
            is_blocked = bool(
                is_ready
                and downstreams
                and not any(len(self.station_buffers[d]) < self.stations[d]["buffer_capacity_units"] for d in downstreams)
            )

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
                    "shift_name": shift_name,
                    "shift_index": shift_index,
                    "is_night_shift": is_night_shift,
                    "is_blackout": True,
                    "is_stopped": False,
                    "is_blocked": False
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
                    "shift_name": shift_name,
                    "shift_index": shift_index,
                    "is_night_shift": is_night_shift,
                    "is_blackout": False,
                    "is_stopped": is_stopped,
                    "is_blocked": is_blocked
                }
            tick_telemetry.append(event)

            # Check if current station finished its dwell cycle and is ready to dispatch
            if is_ready:
                dispatched_this_tick[sid] = (current_vin, t_remain)

        # Phase 2: Dispatch completed vehicles downstream (strict Blocking-After-Service protocol)
        for sid, (vin, t_remain) in dispatched_this_tick.items():
            s = self.stations[sid]
            downstreams = s["downstream_ids"]
            
            if downstreams:
                # Find available downstream stations with space in their buffer
                available_downstreams = [
                    d for d in downstreams 
                    if len(self.station_buffers[d]) < self.stations[d]["buffer_capacity_units"]
                ]
                
                if available_downstreams:
                    # Pick available downstream with lowest total occupancy (buffer queue + active cradle processing)
                    def _station_occupancy_score(d):
                        q_len = len(self.station_buffers[d])
                        in_proc = 1 if self.station_processing.get(d) is not None else 0
                        total = q_len + in_proc
                        cap = max(1, self.stations[d]["buffer_capacity_units"])
                        return (total / cap, total)

                    target_down = min(available_downstreams, key=_station_occupancy_score)
                    self.station_buffers[target_down].append(vin)
                    if vin in self.active_vehicles:
                        self.active_vehicles[vin]["current_station"] = target_down
                        self.active_vehicles[vin]["route_station_ids"].append(target_down)
                        self.active_vehicles[vin]["visit_history"].append({
                            "station_id": target_down,
                            "tick": self.current_tick,
                            "defect_flag": False
                        })
                        updated_genealogy_records.append(dict(self.active_vehicles[vin]))
                    
                    # Successfully transferred downstream: free cradle and carry over remaining work time
                    self.station_processing[sid] = None
                    self.station_dwell_seconds[sid] = t_remain
                    self.station_dwell_ticks[sid] = 0
                else:
                    # BACKPRESSURE / BLOCKED: All downstream buffers are full!
                    # Station remains blocked with the vehicle in the cradle.
                    self.station_dwell_seconds[sid] = max(self.station_dwell_seconds[sid], s["target_cycle_time_s"])
                    self.station_dwell_ticks[sid] = int(self.station_dwell_seconds[sid] // 60.0)
            else:
                # Terminal Station (ST40 Buy-Off) Completed!
                if vin in self.active_vehicles:
                    v_rec = self.active_vehicles.pop(vin)
                    v_rec["completion_tick"] = self.current_tick
                    v_rec["status"] = "COMPLETED"
                    self.completed_vehicles.append(v_rec)
                    self.total_completed_vehicles += 1
                    updated_genealogy_records.append(v_rec)

                # Successfully completed and exited line: free cradle and carry over remaining work time
                self.station_processing[sid] = None
                self.station_dwell_seconds[sid] = t_remain
                self.station_dwell_ticks[sid] = 0

        # Phase 3: Admit next queued vehicle into empty cradles
        for sid in self.stations.keys():
            if self.station_processing[sid] is None:
                if len(self.station_buffers[sid]) > 0:
                    self.station_processing[sid] = self.station_buffers[sid].popleft()
                    # Carry over remaining work time
                else:
                    self.station_dwell_seconds[sid] = 0.0
                    self.station_dwell_ticks[sid] = 0

        # Phase 4: Synchronize Telemetry Events with Accurate Post-Admission Cradle & Buffer State
        for event in tick_telemetry:
            sid = event["station_id"]
            cur_proc = self.station_processing.get(sid)
            q_list = list(self.station_buffers.get(sid, []))
            self.buffers[sid] = len(q_list) + (1 if cur_proc else 0)
            event["buffer_level"] = self.buffers[sid]
            event["processing_vin"] = cur_proc
            event["vehicle_id"] = cur_proc
            event["queued_vins"] = q_list
            event["is_processing"] = bool(cur_proc and not event.get("is_stopped", False))

        return {
            "tick": self.current_tick,
            "timestamp": sim_time_str,
            "events": tick_telemetry,
            "ground_truth": ground_truth,
            "buffers": dict(self.buffers),
            "genealogy_records": updated_genealogy_records,
            "andon_ingress_locked": is_andon_active,
            "andon_reason": self.andon_reason
        }
