"""
DigitalTwin.ai - Assembly Line Topology Definition
40 stations across 3 zones: Body Construction (14), Paint (8), and Final Assembly (18).
Sensor tier split: 80% rich (32) / 20% manual (8).
Buffer capacity: 5-15 units.
Topology represented as a Directed Acyclic Graph (DAG) with parallel branches.
"""
import random
from typing import Dict, List, Any

RANDOM_SEED = 42

def build_line_topology(seed: int = RANDOM_SEED) -> Dict[str, Any]:
    random.seed(seed)
    
    stations_data = [
        # Body Construction (14 Stations: ST01 - ST14)
        {"id": "ST01", "name": "Underbody Sub-Assembly", "zone": "Body", "type": "SubAssembly", "target_cycle_time": 60.0, "power_base_kw": 18.5},
        {"id": "ST02", "name": "Floor Pan Robotic Weld", "zone": "Body", "type": "RoboticWeld", "target_cycle_time": 55.0, "power_base_kw": 32.0},
        {"id": "ST03", "name": "Side Panel Outer - LH", "zone": "Body", "type": "RoboticWeld", "target_cycle_time": 58.0, "power_base_kw": 28.0},
        {"id": "ST04", "name": "Side Panel Outer - RH", "zone": "Body", "type": "RoboticWeld", "target_cycle_time": 58.0, "power_base_kw": 28.0},
        # MERGE POINT: ST05 fed by parallel ST03 (58s) + ST04 (58s).
        # Branches alternate arrivals (not simultaneous), avg interarrival ~29s.
        # CT=52s handles merge drain while not overwhelming downstream ST06 (65s).
        # Buffer=14 absorbs burst arrivals during anomaly recovery.
        {"id": "ST05", "name": "Roof Assembly & Laser Brazing", "zone": "Body", "type": "LaserBrazing", "target_cycle_time": 52.0, "power_base_kw": 35.0, "buffer_capacity": 14},
        {"id": "ST06", "name": "Framing Main Station", "zone": "Body", "type": "MainFraming", "target_cycle_time": 65.0, "power_base_kw": 40.0},
        {"id": "ST07", "name": "Respot Welding Line A", "zone": "Body", "type": "RespotWeld", "target_cycle_time": 62.0, "power_base_kw": 30.0},
        {"id": "ST08", "name": "Respot Welding Line B", "zone": "Body", "type": "RespotWeld", "target_cycle_time": 62.0, "power_base_kw": 30.0},
        # MERGE POINT: ST09 fed by parallel ST07 (62s) + ST08 (62s).
        # CT=42s handles alternating merge while not overwhelming downstream ST10 (54s).
        {"id": "ST09", "name": "Structural Sealer & Adhesive", "zone": "Body", "type": "Dispensing", "target_cycle_time": 42.0, "power_base_kw": 12.0, "buffer_capacity": 14},
        {"id": "ST10", "name": "Door Hanging & Alignment", "zone": "Body", "type": "Fitting", "target_cycle_time": 54.0, "power_base_kw": 15.0},
        {"id": "ST11", "name": "Hood & Tailgate Mounting", "zone": "Body", "type": "Fitting", "target_cycle_time": 52.0, "power_base_kw": 14.0},
        {"id": "ST12", "name": "Body Geometry CMM Scan", "zone": "Body", "type": "QualityScan", "target_cycle_time": 48.0, "power_base_kw": 22.0},
        {"id": "ST13", "name": "Body Metal Finishing & Polish", "zone": "Body", "type": "ManualFinishing", "target_cycle_time": 56.0, "power_base_kw": 8.0},
        {"id": "ST14", "name": "BIW Transfer Buffer", "zone": "Body", "type": "TransferBuffer", "target_cycle_time": 45.0, "power_base_kw": 10.0},

        # Paint Zone (8 Stations: ST15 - ST22)
        {"id": "ST15", "name": "Pre-Treatment & Degreasing", "zone": "Paint", "type": "ChemicalBath", "target_cycle_time": 70.0, "power_base_kw": 25.0},
        {"id": "ST16", "name": "E-Coat Dip Tank", "zone": "Paint", "type": "ElectroDeposition", "target_cycle_time": 75.0, "power_base_kw": 45.0},
        {"id": "ST17", "name": "E-Coat Curing Oven", "zone": "Paint", "type": "ThermalOven", "target_cycle_time": 80.0, "power_base_kw": 55.0},
        {"id": "ST18", "name": "Underbody PVC Sealing", "zone": "Paint", "type": "ManualSealing", "target_cycle_time": 68.0, "power_base_kw": 9.0},
        {"id": "ST19", "name": "Primer Surfacer Robotic Booth", "zone": "Paint", "type": "RoboticSpray", "target_cycle_time": 72.0, "power_base_kw": 38.0},
        {"id": "ST20", "name": "Basecoat Robotic Application", "zone": "Paint", "type": "RoboticSpray", "target_cycle_time": 74.0, "power_base_kw": 42.0},
        {"id": "ST21", "name": "Clearcoat & Infrared Curing", "zone": "Paint", "type": "RoboticSpray", "target_cycle_time": 78.0, "power_base_kw": 48.0},
        {"id": "ST22", "name": "Paint Defect Vision Inspection", "zone": "Paint", "type": "VisionQC", "target_cycle_time": 60.0, "power_base_kw": 20.0},

        # Final Assembly (18 Stations: ST23 - ST40)
        {"id": "ST23", "name": "Paint-to-Assembly Infeed Buffer", "zone": "Assembly", "type": "TransferBuffer", "target_cycle_time": 45.0, "power_base_kw": 10.0},
        {"id": "ST24", "name": "Wire Harness Routing", "zone": "Assembly", "type": "ManualWiring", "target_cycle_time": 65.0, "power_base_kw": 7.5},
        {"id": "ST25", "name": "Cockpit / IP Module Marriage", "zone": "Assembly", "type": "ModuleMarriage", "target_cycle_time": 62.0, "power_base_kw": 22.0},
        {"id": "ST26", "name": "Front Suspension Assembly", "zone": "Assembly", "type": "MechanicalTorque", "target_cycle_time": 58.0, "power_base_kw": 20.0},
        # MERGE POINT: ST27 fed by parallel ST25 (62s) + ST26 (58s).
        # CT=48s handles alternating merge while not overwhelming downstream ST28 (70s).
        {"id": "ST27", "name": "Rear Axle & Brake Lines", "zone": "Assembly", "type": "MechanicalTorque", "target_cycle_time": 48.0, "power_base_kw": 21.0, "buffer_capacity": 14},
        {"id": "ST28", "name": "Drivetrain & Battery Marriage", "zone": "Assembly", "type": "AutomatedMarriage", "target_cycle_time": 70.0, "power_base_kw": 50.0},
        {"id": "ST29", "name": "Exhaust & Undercarriage Bolting", "zone": "Assembly", "type": "RoboticTorque", "target_cycle_time": 55.0, "power_base_kw": 24.0},
        {"id": "ST30", "name": "Windshield Robotic Glazing", "zone": "Assembly", "type": "RoboticUrethane", "target_cycle_time": 50.0, "power_base_kw": 26.0},
        {"id": "ST31", "name": "Headliner & Pillars Trim", "zone": "Assembly", "type": "ManualTrim", "target_cycle_time": 62.0, "power_base_kw": 6.0},
        {"id": "ST32", "name": "Carpeting & Sound Absorption", "zone": "Assembly", "type": "ManualTrim", "target_cycle_time": 58.0, "power_base_kw": 5.5},
        {"id": "ST33", "name": "Front & Rear Seat Install", "zone": "Assembly", "type": "ModuleMarriage", "target_cycle_time": 64.0, "power_base_kw": 18.0},
        {"id": "ST34", "name": "Steering & Safety Systems", "zone": "Assembly", "type": "SafetyCalibration", "target_cycle_time": 52.0, "power_base_kw": 15.0},
        {"id": "ST35", "name": "Automated Wheel Torquing", "zone": "Assembly", "type": "AutomatedTorque", "target_cycle_time": 48.0, "power_base_kw": 30.0},
        {"id": "ST36", "name": "Fluids Vacuum Fill & Bleed", "zone": "Assembly", "type": "FluidFill", "target_cycle_time": 56.0, "power_base_kw": 25.0},
        {"id": "ST37", "name": "Door Final Mount & Weatherstrip", "zone": "Assembly", "type": "ManualFitting", "target_cycle_time": 60.0, "power_base_kw": 8.0},
        {"id": "ST38", "name": "EOL ECU Flash & Sensor Sync", "zone": "Assembly", "type": "ElectronicFlash", "target_cycle_time": 55.0, "power_base_kw": 16.0},
        {"id": "ST39", "name": "Dynamometer & Roll Bench Test", "zone": "Assembly", "type": "DynamicTest", "target_cycle_time": 72.0, "power_base_kw": 45.0},
        {"id": "ST40", "name": "Final Buy-off & ADAS Calibration", "zone": "Assembly", "type": "FinalInspection", "target_cycle_time": 65.0, "power_base_kw": 28.0},
    ]

    manual_station_ids = {"ST09", "ST11", "ST13", "ST18", "ST24", "ST31", "ST32", "ST37"}
    
    edges = [
        # Body
        ("ST01", "ST02"), ("ST02", "ST03"), ("ST02", "ST04"),
        ("ST03", "ST05"), ("ST04", "ST05"), ("ST05", "ST06"),
        ("ST06", "ST07"), ("ST06", "ST08"), ("ST07", "ST09"),
        ("ST08", "ST09"), ("ST09", "ST10"), ("ST10", "ST11"),
        ("ST11", "ST12"), ("ST12", "ST13"), ("ST13", "ST14"),
        # Inter-zone: Body -> Paint
        ("ST14", "ST15"),
        # Paint
        ("ST15", "ST16"), ("ST16", "ST17"), ("ST17", "ST18"),
        ("ST18", "ST19"), ("ST19", "ST20"), ("ST20", "ST21"),
        ("ST21", "ST22"),
        # Inter-zone: Paint -> Final Assembly
        ("ST22", "ST23"),
        # Final Assembly
        ("ST23", "ST24"), ("ST24", "ST25"), ("ST24", "ST26"),
        ("ST25", "ST27"), ("ST26", "ST27"), ("ST27", "ST28"),
        ("ST28", "ST29"), ("ST29", "ST30"), ("ST30", "ST31"),
        ("ST31", "ST32"), ("ST32", "ST33"), ("ST33", "ST34"),
        ("ST34", "ST35"), ("ST35", "ST36"), ("ST36", "ST37"),
        ("ST37", "ST38"), ("ST38", "ST39"), ("ST39", "ST40")
    ]
    
    upstream_map = {st["id"]: [] for st in stations_data}
    downstream_map = {st["id"]: [] for st in stations_data}
    for u, v in edges:
        downstream_map[u].append(v)
        upstream_map[v].append(u)
        
    stations = {}
    for st in stations_data:
        sid = st["id"]
        tier = "manual" if sid in manual_station_ids else "rich"
        cap = st.get("buffer_capacity", random.randint(8, 12))
        
        # Realistic staggered preventive maintenance schedule (5 to 22 days from sim epoch)
        station_num = int(sid[2:]) if sid[2:].isdigit() else 1
        day_offset = (station_num * 3) % 18 + 5
        maint_date = f"2026-03-{day_offset:02d}T08:00"
        maint_interval = 168 if tier == "rich" else 336  # Weekly (168h) or Bi-weekly (336h)

        stations[sid] = {
            "station_id": sid,
            "name": st["name"],
            "zone": st["zone"],
            "station_type": st["type"],
            "sensor_tier": tier,
            "target_cycle_time_s": st["target_cycle_time"],
            "power_base_kw": st["power_base_kw"],
            "buffer_capacity_units": cap,
            "next_maintenance_date": maint_date,
            "maintenance_interval_hours": maint_interval,
            "upstream_ids": upstream_map[sid],
            "downstream_ids": downstream_map[sid]
        }
        
    return {
        "metadata": {
            "total_stations": len(stations),
            "zones": {"Body": 14, "Paint": 8, "Assembly": 18},
            "sensor_tiers": {"rich": len(stations) - len(manual_station_ids), "manual": len(manual_station_ids)},
            "seed": seed
        },
        "stations": stations,
        "edges": edges
    }
