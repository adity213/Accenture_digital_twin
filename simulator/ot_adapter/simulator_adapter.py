import abc
from typing import Dict, Any, List

class SimulatorAdapter(abc.ABC):
    """
    Abstract Base Class defining the operational telemetry interface.
    This contract ensures the API can seamlessly swap the Python
    stochastic LineSimulator for physical OPC UA or MQTT data streams.
    """

    @abc.abstractmethod
    def step(self) -> Dict[str, Any]:
        """
        Retrieves the latest tick of telemetry.
        Returns:
            Dict containing 'timestamp', 'events' (list of telemetry per station),
            and 'ground_truth' (internal state flags).
        """
        pass
    
    @abc.abstractproperty
    def current_tick(self) -> int:
        pass
        
    @abc.abstractproperty
    def target_jph(self) -> float:
        pass
        
    @target_jph.setter
    @abc.abstractmethod
    def target_jph(self, val: float):
        pass

    @abc.abstractproperty
    def completed_vehicles(self) -> List[Dict[str, Any]]:
        pass
        
    @abc.abstractproperty
    def active_vehicles(self) -> Dict[str, Dict[str, Any]]:
        pass
        
    @abc.abstractproperty
    def shortest_path_to_sink(self) -> Dict[str, int]:
        pass

    @abc.abstractmethod
    def inject_anomaly(self, anomaly_type: str, station_id: str, duration_ticks: int = 60) -> str:
        pass

    @abc.abstractmethod
    def retopologize(self, new_topology: Dict[str, Any]):
        pass

    @abc.abstractmethod
    def clear_anomalies(self):
        pass


class PythonSimulatorAdapter(SimulatorAdapter):
    """
    Concrete implementation wrapping the local Python `LineSimulator`.
    """
    def __init__(self, simulator_instance):
        self._sim = simulator_instance

    def retopologize(self, new_topology: Dict[str, Any]):
        if hasattr(self._sim, "retopologize"):
            self._sim.retopologize(new_topology)

    def step(self) -> Dict[str, Any]:
        return self._sim.step()
        
    @property
    def current_tick(self) -> int:
        return self._sim.current_tick
        
    @property
    def target_jph(self) -> float:
        return self._sim.target_jph
        
    @target_jph.setter
    def target_jph(self, val: float):
        self._sim.target_jph = val

    @property
    def completed_vehicles(self) -> List[Dict[str, Any]]:
        return list(self._sim.completed_vehicles)
        
    @property
    def active_vehicles(self) -> Dict[str, Dict[str, Any]]:
        return self._sim.active_vehicles
        
    @property
    def shortest_path_to_sink(self) -> Dict[str, int]:
        return self._sim.shortest_path_to_sink

    @property
    def stations(self) -> Dict[str, Any]:
        return getattr(self._sim, "stations", {})

    @property
    def anomaly_mgr(self):
        return getattr(self._sim, "anomaly_mgr", None)

    def __getattr__(self, name: str):
        return getattr(self._sim, name)

    def inject_anomaly(self, anomaly_type: str, station_id: str, duration_ticks: int = 60) -> str:
        cur = self._sim.current_tick
        atype = anomaly_type.lower()
        if atype in ["gradual_drift", "drift"]:
            return self._sim.anomaly_mgr.inject_gradual_drift(station_id, cur, duration_ticks)
        elif atype in ["sudden_stoppage", "stoppage"]:
            return self._sim.anomaly_mgr.inject_sudden_stoppage(station_id, cur, duration_ticks)
        elif atype in ["latent_defect", "defect_spike", "defect"]:
            return self._sim.anomaly_mgr.inject_latent_defect(station_id, "ST22", cur, duration_ticks)
        elif atype in ["sensor_blackout", "blackout"]:
            return self._sim.anomaly_mgr.inject_sensor_blackout(station_id, cur, duration_ticks)
        elif atype in ["energy_waste", "power_surge", "energy"]:
            return self._sim.anomaly_mgr.inject_energy_waste(station_id, cur, duration_ticks)
        else:
            raise ValueError(f"Unknown anomaly type: {atype}")

    def clear_anomalies(self):
        self._sim.anomaly_mgr.active_anomalies.clear()
