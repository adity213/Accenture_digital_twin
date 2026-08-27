"""
DigitalTwin.ai - Balanced Anomaly Campaign Generator (for training data generation only)

Why this exists:
-----------------
api/main.py's /anomaly/inject endpoint is demo-driven: a human picks one station and
fires one anomaly. If you use that same pattern to generate training data (loop N times,
inject somewhere), you get biased data almost by construction:
  - stations that are "convenient" to demo (e.g. ST22 hardcoded as the latent_defect
    inspection point) get massively over-represented
  - anomaly durations/severities default to the same fixed constants every time, so the
    model never sees mild vs. severe versions of the same failure mode
  - if injections cluster early or late in a run, shift_progress / diurnal features become
    a leaking proxy for "anomaly happening" rather than a real diurnal signal
  - some zones/station types may never see certain anomaly types, so the model silently
    learns "manual station => never gets gradual_drift" as an artifact of your campaign
    design, not physics

generate_balanced_campaign() spreads every anomaly type roughly evenly across zones and
stations, randomizes duration/severity within physically plausible ranges, avoids
overlapping injections on the same station, and picks latent_defect inspection stations
from real downstream descendants in the topology DAG instead of a hardcoded ST22.

This module does not modify simulator/anomalies.py or generator.py -- it only decides
*what* to inject *when*, using the existing AnomalyManager.inject_* methods.
"""
import random
from collections import defaultdict, deque
from typing import Dict, Any, List

ANOMALY_TYPES = [
    "gradual_drift",
    "sudden_stoppage",
    "latent_defect",
    "sensor_blackout",
    "energy_waste",
]

# (min, max) duration in ticks (minutes), deliberately varied so the model sees a
# spectrum of severities rather than one fixed constant per type.
DURATION_RANGES = {
    "gradual_drift": (40, 90),
    "sudden_stoppage": (20, 100),   # shorter stoppages included too, not just the 85min default
    "latent_defect": (20, 60),
    "sensor_blackout": (15, 50),
    "energy_waste": (20, 70),
}


def _build_descendants_map(topology: Dict[str, Any]) -> Dict[str, List[str]]:
    """BFS descendants per station, used to pick physically valid inspection points
    for latent defects (must be strictly downstream of the source station)."""
    downstream = defaultdict(list)
    for u, v in topology["edges"]:
        downstream[u].append(v)

    descendants: Dict[str, List[str]] = {}
    for sid in topology["stations"]:
        seen = set()
        q = deque(downstream.get(sid, []))
        while q:
            n = q.popleft()
            if n in seen:
                continue
            seen.add(n)
            q.extend(downstream.get(n, []))
        descendants[sid] = sorted(seen)
    return descendants


def generate_balanced_campaign(
    topology: Dict[str, Any],
    rng: random.Random,
    num_ticks: int,
    events_per_zone_per_type: int = 3,
    min_gap_ticks: int = 150,
    warmup_ticks: int = 60,
    cooldown_ticks: int = 150,
) -> List[Dict[str, Any]]:
    """
    Returns a chronologically sorted list of injection instructions:
        {station_id, anomaly_type, start_tick, duration_ticks, params}

    Coverage guarantee: every zone gets `events_per_zone_per_type` injections of
    EVERY anomaly type (not just the types that happen to suit that zone), so the
    model sees, e.g., sensor_blackout on rich-tier stations too, not only manual ones,
    which is important for it to learn the sensor_tier feature's effect in isolation
    rather than as a confound with anomaly type.
    """
    zones: Dict[str, List[str]] = defaultdict(list)
    for sid, meta in topology["stations"].items():
        zones[meta["zone"]].append(sid)

    descendants = _build_descendants_map(topology)
    station_last_end: Dict[str, int] = defaultdict(lambda: -10_000)
    campaign: List[Dict[str, Any]] = []

    usable_start_hi = max(warmup_ticks + 1, num_ticks - cooldown_ticks)

    for anomaly_type in ANOMALY_TYPES:
        for zone_name, station_ids in zones.items():
            for _ in range(events_per_zone_per_type):
                # pick a station in this zone, preferring ones not already crowded
                candidates = sorted(station_ids, key=lambda s: station_last_end[s])
                sid = rng.choice(candidates[: max(1, len(candidates) // 2) or 1])

                lo, hi = DURATION_RANGES[anomaly_type]
                duration = rng.randint(lo, hi)

                start_tick = rng.randint(warmup_ticks, usable_start_hi)
                attempts = 0
                while start_tick - station_last_end[sid] < min_gap_ticks and attempts < 25:
                    start_tick = rng.randint(warmup_ticks, usable_start_hi)
                    attempts += 1
                station_last_end[sid] = start_tick + duration

                params: Dict[str, Any] = {}
                if anomaly_type == "gradual_drift":
                    params["drift_factor"] = round(rng.uniform(0.20, 0.65), 2)
                elif anomaly_type == "latent_defect":
                    downs = descendants.get(sid, [])
                    params["inspection_station_id"] = rng.choice(downs) if downs else sid
                    params["defect_type"] = rng.choice(
                        ["weld_porosity", "surface_scratch", "fastener_undertorque", "adhesive_void"]
                    )
                elif anomaly_type == "energy_waste":
                    params["surge_multiplier"] = round(rng.uniform(1.6, 3.2), 2)

                campaign.append(
                    {
                        "station_id": sid,
                        "anomaly_type": anomaly_type,
                        "start_tick": start_tick,
                        "duration_ticks": duration,
                        "params": params,
                    }
                )

    campaign.sort(key=lambda e: e["start_tick"])
    return campaign


def apply_campaign_event(anomaly_mgr, event: Dict[str, Any]) -> None:
    """Fires the right AnomalyManager.inject_* method for one campaign event."""
    t = event["anomaly_type"]
    sid = event["station_id"]
    dur = event["duration_ticks"]
    p = event["params"]

    if t == "gradual_drift":
        anomaly_mgr.inject_gradual_drift(sid, event["start_tick"], duration_ticks=dur, drift_factor=p.get("drift_factor", 0.45))
    elif t == "sudden_stoppage":
        anomaly_mgr.inject_sudden_stoppage(sid, event["start_tick"], duration_ticks=dur)
    elif t == "latent_defect":
        anomaly_mgr.inject_latent_defect(
            sid, p.get("inspection_station_id", sid), event["start_tick"],
            duration_ticks=dur, defect_type=p.get("defect_type", "weld_porosity")
        )
    elif t == "sensor_blackout":
        anomaly_mgr.inject_sensor_blackout(sid, event["start_tick"], duration_ticks=dur)
    elif t == "energy_waste":
        anomaly_mgr.inject_energy_waste(sid, event["start_tick"], duration_ticks=dur, surge_multiplier=p.get("surge_multiplier", 2.4))
