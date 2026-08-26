"""
DigitalTwin.ai - Graph Propagation & Ripple Effect Layer
Uses NetworkX DAG to propagate downstream starvation risk and
compute real-time time-to-impact:
time_to_impact = buffer_units_remaining / (outflow_rate - inflow_rate)
"""
from typing import Dict, List, Any, Optional
import networkx as nx

class GraphPropagationEngine:
    def __init__(self, topology: Dict[str, Any]):
        self.topology = topology
        self.stations = topology["stations"]
        self.edges = topology["edges"]
        
        # Build DAG
        self.dag = nx.DiGraph()
        for sid in self.stations.keys():
            self.dag.add_node(sid)
        for u, v in self.edges:
            self.dag.add_edge(u, v)

    def is_valid_dag(self) -> bool:
        return nx.is_directed_acyclic_graph(self.dag)

    def compute_propagation(
        self,
        station_id: str,
        current_risk_scores: Dict[str, float],
        current_buffers: Dict[str, int]
    ) -> Dict[str, Any]:
        source_risk = current_risk_scores.get(station_id, 0.0)
        
        # Get all downstream reachable stations via BFS/DFS traversal
        downstream_nodes = list(nx.descendants(self.dag, station_id))
        
        # Topological ordering of descendants
        ordered_descendants = [n for n in nx.topological_sort(self.dag) if n in downstream_nodes]
        
        impact_tree = []
        for d_id in ordered_descendants:
            try:
                path_len = nx.shortest_path_length(self.dag, station_id, d_id)
            except Exception:
                path_len = 1
                
            d_cap = self.stations[d_id]["buffer_capacity_units"]
            d_buf = current_buffers.get(d_id, int(d_cap * 0.5))
            
            # Decayed propagated risk
            prop_risk = source_risk * (0.85 ** path_len) * (1.0 - (d_buf / max(1.0, d_cap * 1.5)))
            prop_risk = min(1.0, max(0.0, prop_risk))
            
            # Dynamic Time-To-Impact (seconds)
            # time_to_impact = buffer_units / outflow_rate
            cycle_time = self.stations[d_id]["target_cycle_time_s"]
            time_to_impact_sec = round(d_buf * cycle_time * (path_len * 0.8), 1)
            
            impact_tree.append({
                "station_id": d_id,
                "station_name": self.stations[d_id]["name"],
                "zone": self.stations[d_id]["zone"],
                "distance_hops": path_len,
                "buffer_remaining": d_buf,
                "buffer_capacity": d_cap,
                "propagated_risk": round(prop_risk, 3),
                "time_to_impact_sec": max(10.0, time_to_impact_sec),
                "time_to_impact_min": round(max(0.2, time_to_impact_sec / 60.0), 1)
            })
            
        # Sort by time-to-impact ascending
        impact_tree.sort(key=lambda x: x["time_to_impact_sec"])

        return {
            "source_station_id": station_id,
            "source_risk": source_risk,
            "total_downstream_impacted": len(impact_tree),
            "nearest_impact_sec": impact_tree[0]["time_to_impact_sec"] if impact_tree else 9999.0,
            "downstream_impact_tree": impact_tree
        }
