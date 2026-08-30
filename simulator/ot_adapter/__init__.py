import os
import logging
from .simulator_adapter import SimulatorAdapter, PythonSimulatorAdapter
from .opcua_adapter import OpcUaAdapter
from .mqtt_adapter import MqttAdapter

logger = logging.getLogger(__name__)

def create_ot_adapter(raw_simulator=None, adapter_type: str = None) -> SimulatorAdapter:
    """
    Factory creating the designated OT Ingestion Adapter.
    Defaults to high-fidelity PythonSimulatorAdapter, with pluggable OPC UA or MQTT support (Issue 6).
    """
    kind = (adapter_type or os.getenv("OT_ADAPTER_TYPE", "SIMULATOR")).strip().upper()
    
    if kind == "OPCUA":
        endpoint = os.getenv("OPCUA_ENDPOINT_URL", "opc.tcp://localhost:4840/freeopcua/server/")
        logger.info("Initializing Physical OPC UA Adapter connecting to %s", endpoint)
        return OpcUaAdapter(endpoint_url=endpoint)
    elif kind == "MQTT":
        broker = os.getenv("MQTT_BROKER_URL", "mqtt://localhost:1883")
        topic = os.getenv("MQTT_TELEMETRY_TOPIC", "factory/line1/telemetry")
        logger.info("Initializing Physical MQTT Adapter connecting to %s (%s)", broker, topic)
        return MqttAdapter(broker_url=broker, topic=topic)
    else:
        if raw_simulator is None:
            from ..generator import LineSimulator
            raw_simulator = LineSimulator(seed=42)
        return PythonSimulatorAdapter(raw_simulator)

__all__ = ["SimulatorAdapter", "PythonSimulatorAdapter", "OpcUaAdapter", "MqttAdapter", "create_ot_adapter"]
