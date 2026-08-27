"""
DigitalTwin.ai - Pydantic Request & Response Schemas
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class SimControlRequest(BaseModel):
    action: str
    speed_multiplier: Optional[float] = 1.0
    anomaly_type: Optional[str] = None
    station_id: Optional[str] = None
    duration_ticks: Optional[int] = 60

# Alias for backward compatibility
SimulatorControlRequest = SimControlRequest

class OverrideRequest(BaseModel):
    action: str
    reason: Optional[str] = ""

class TopologyUpdateRequest(BaseModel):
    stations: Dict[str, Any]
    edges: List[List[str]]
    metadata: Dict[str, Any]

class StationTelemetrySchema(BaseModel):
    station_id: str
    cycle_time_s: Optional[float] = None
    buffer_level: Optional[int] = None
    vibration: Optional[float] = None
    temperature: Optional[float] = None
    power_kw: Optional[float] = None
    is_blackout: Optional[bool] = False
