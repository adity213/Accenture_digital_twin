"""
DigitalTwin.ai - Tiered Standard Operating Procedure (SOP) Lookup & Escalation Engine

Defines multi-tiered action ladders for line operators, line leads, and maintenance engineers.
SOPs escalate based on condition persistence (elapsed ticks in anomaly state).
Includes automated fallback to physical gauge validation when sensor_confidence < 65%.
"""
from typing import Dict, List, Any, Optional, Tuple


# Pre-defined tiered SOP lookup table
# Key: (station_type_category, anomaly_type)
SOP_TABLE: Dict[Tuple[str, str], List[Dict[str, Any]]] = {
    # 1. Robotic Weld Cells & Stamping (ST01 - ST14)
    ("RoboticWeld", "sudden_stoppage"): [
        {
            "step": 1,
            "role": "Operator",
            "action": "Check E-stop status and weld gun position; clear mechanical obstruction or weld slag if visible.",
            "escalate_after_ticks": 5
        },
        {
            "step": 2,
            "role": "Line Lead",
            "action": "If unresolved after 5 ticks, dispatch mechanical maintenance and reroute oncoming carriers via parallel branch buffer.",
            "escalate_after_ticks": 15
        },
        {
            "step": 3,
            "role": "Maintenance",
            "action": "Full diagnostic on weld servo motor seizure and hydraulic clamp pressure; escalate to plant engineering if overhaul required.",
            "escalate_after_ticks": None
        }
    ],
    ("RoboticWeld", "gradual_drift"): [
        {
            "step": 1,
            "role": "Operator",
            "action": "Perform automated electrode tip dress cycle; inspect weld cap diameter and alignment.",
            "escalate_after_ticks": 10
        },
        {
            "step": 2,
            "role": "Line Lead",
            "action": "Schedule tip changeover during next micro-break; review SPC cycle time trend.",
            "escalate_after_ticks": 25
        },
        {
            "step": 3,
            "role": "Maintenance",
            "action": "Calibrate weld servo drive torque limits and inspect primary transformer cooling.",
            "escalate_after_ticks": None
        }
    ],

    # 2. Paint Shop Chemical Baths & Thermal Ovens (ST15 - ST22)
    ("ThermalOven", "gradual_drift"): [
        {
            "step": 1,
            "role": "Operator",
            "action": "Verify IR radiant emitter zone pyrometer temperatures against physical analog gauges.",
            "escalate_after_ticks": 8
        },
        {
            "step": 2,
            "role": "Line Lead",
            "action": "Adjust conveyor chain drive indexing speed to maintain 22-min paint bake envelope.",
            "escalate_after_ticks": 20
        },
        {
            "step": 3,
            "role": "Maintenance",
            "action": "Inspect exhaust air recirculation dampers and replace clogged burner air filters.",
            "escalate_after_ticks": None
        }
    ],
    ("ChemicalBath", "latent_defect"): [
        {
            "step": 1,
            "role": "Operator",
            "action": "Sample tank pH, zinc phosphate concentration, and immersion temperature; trigger automated chemical dosing.",
            "escalate_after_ticks": 10
        },
        {
            "step": 2,
            "role": "Quality Lead",
            "action": "Tag downstream carriers for E-coat thickness verification at ST22 Vision Inspection.",
            "escalate_after_ticks": None
        }
    ],

    # 3. Final Assembly Torquing, Marriage & Trim (ST23 - ST40)
    ("MechanicalTorque", "gradual_drift"): [
        {
            "step": 1,
            "role": "Operator",
            "action": "Recalibrate DC electric torque nutrunner with master calibration transducer; check socket bit wear.",
            "escalate_after_ticks": 6
        },
        {
            "step": 2,
            "role": "Line Lead",
            "action": "Swap backup tool controller; review torque-angle fastener seating curve on station HMI.",
            "escalate_after_ticks": 15
        },
        {
            "step": 3,
            "role": "Quality Lead",
            "action": "Perform 100% manual click-wrench audit on last 5 chassis batches.",
            "escalate_after_ticks": None
        }
    ],
    ("AutomatedMarriage", "sudden_stoppage"): [
        {
            "step": 1,
            "role": "Operator",
            "action": "Inspect AGV optical alignment target and pallet locking pins; ensure carrier is seated.",
            "escalate_after_ticks": 4
        },
        {
            "step": 2,
            "role": "Line Lead",
            "action": "Switch AGV to manual creep mode; check powertrain lift hydraulic manifold pressure.",
            "escalate_after_ticks": 12
        },
        {
            "step": 3,
            "role": "Maintenance",
            "action": "Full electrical diagnostic on lifter VFD inverter fault code; initiate emergency carrier bypass.",
            "escalate_after_ticks": None
        }
    ],

    # 4. Universal Anomaly Fallbacks
    ("_generic", "sensor_blackout"): [
        {
            "step": 1,
            "role": "Operator",
            "action": "Sensor confidence degraded (<65%). Verify physical station running state and log manual tally.",
            "escalate_after_ticks": 10
        },
        {
            "step": 2,
            "role": "Maintenance",
            "action": "Check Profinet / Modbus fieldbus drop cable, 24V DC sensor power supply, and I/O module LED diagnostic.",
            "escalate_after_ticks": None
        }
    ],
    ("_generic", "energy_waste"): [
        {
            "step": 1,
            "role": "Operator",
            "action": "Check for auxiliary cooling fan, hydraulic power pack, or heater bank running while line is starved/idle.",
            "escalate_after_ticks": 8
        },
        {
            "step": 2,
            "role": "Maintenance",
            "action": "Engage automated Eco-Sleep mode on PLC drive controllers; verify power metering CT transducer.",
            "escalate_after_ticks": None
        }
    ],
    ("_generic", "latent_defect"): [
        {
            "step": 1,
            "role": "Quality Inspector",
            "action": "Flag vehicle genealogy ID for quarantine; inspect upstream station process logs for parameter drift.",
            "escalate_after_ticks": 10
        },
        {
            "step": 2,
            "role": "Quality Lead",
            "action": "Isolate suspect production batch and notify upstream team leader for containment audit.",
            "escalate_after_ticks": None
        }
    ],
    ("_default", "_default"): [
        {
            "step": 1,
            "role": "Operator",
            "action": "Acknowledge anomaly alert; visually inspect station cradle and verify part alignment.",
            "escalate_after_ticks": 8
        },
        {
            "step": 2,
            "role": "Line Lead",
            "action": "Evaluate downstream buffer capacity; adjust upstream dispatch pacing if bottleneck persists.",
            "escalate_after_ticks": 20
        },
        {
            "step": 3,
            "role": "Maintenance",
            "action": "Dispatch maintenance technician for on-station diagnostic and root cause containment.",
            "escalate_after_ticks": None
        }
    ]
}


def get_tiered_sop(
    station_type: str,
    anomaly_type: str,
    elapsed_ticks: int = 1,
    sensor_confidence: float = 100.0
) -> Dict[str, Any]:
    """
    Returns the ordered SOP steps and highlights the current active step
    based on elapsed ticks and data confidence.
    """
    # 1. Uncertainty Rule: If sensor confidence < 65%, prepend physical verification step
    if sensor_confidence < 65.0:
        base_steps = SOP_TABLE.get(("_generic", "sensor_blackout"), SOP_TABLE[("_default", "_default")])
    else:
        # Check exact (station_type, anomaly_type)
        if (station_type, anomaly_type) in SOP_TABLE:
            base_steps = SOP_TABLE[(station_type, anomaly_type)]
        elif ("_generic", anomaly_type) in SOP_TABLE:
            base_steps = SOP_TABLE[("_generic", anomaly_type)]
        elif (station_type, "sudden_stoppage") in SOP_TABLE and anomaly_type == "sudden_stoppage":
            base_steps = SOP_TABLE[(station_type, "sudden_stoppage")]
        else:
            base_steps = SOP_TABLE[("_default", "_default")]

    # Deep copy steps to evaluate active step
    steps = [dict(s) for s in base_steps]

    active_step_num = 1
    cumulative_ticks = 0
    for s in steps:
        esc_after = s.get("escalate_after_ticks")
        if esc_after is not None:
            cumulative_ticks += esc_after
            if elapsed_ticks > cumulative_ticks:
                active_step_num = min(len(steps), s["step"] + 1)

    return {
        "sop_type": f"{station_type} // {anomaly_type}",
        "active_step_number": active_step_num,
        "elapsed_ticks": elapsed_ticks,
        "steps": steps
    }
