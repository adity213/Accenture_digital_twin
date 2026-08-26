"""
Unit Tests for Topology & DAG Validation (Day 1 Gate)
- 40 stations total
- Zone split: Body=14, Paint=8, Assembly=18
- Sensor tier: 80% rich (32) / 20% manual (8)
- Valid DAG check (networkx.is_directed_acyclic_graph)
"""
import pytest
import networkx as nx
from simulator.topology import build_line_topology

def test_topology_station_counts_and_zones():
    top = build_line_topology(seed=42)
    stations = top["stations"]
    meta = top["metadata"]
    
    assert meta["total_stations"] == 40, f"Expected 40 stations, got {meta['total_stations']}"
    assert meta["zones"]["Body"] == 14, f"Expected 14 Body stations, got {meta['zones']['Body']}"
    assert meta["zones"]["Paint"] == 8, f"Expected 8 Paint stations, got {meta['zones']['Paint']}"
    assert meta["zones"]["Assembly"] == 18, f"Expected 18 Assembly stations, got {meta['zones']['Assembly']}"

def test_sensor_tier_split():
    top = build_line_topology(seed=42)
    meta = top["metadata"]
    assert meta["sensor_tiers"]["rich"] == 32, f"Expected 32 rich stations, got {meta['sensor_tiers']['rich']}"
    assert meta["sensor_tiers"]["manual"] == 8, f"Expected 8 manual stations, got {meta['sensor_tiers']['manual']}"

def test_dag_acyclicity():
    top = build_line_topology(seed=42)
    dag = nx.DiGraph()
    for sid in top["stations"].keys():
        dag.add_node(sid)
    for u, v in top["edges"]:
        dag.add_edge(u, v)
        
    assert nx.is_directed_acyclic_graph(dag), "Topology graph must be a valid DAG (no circular loops)"
    assert nx.is_weakly_connected(dag), "Topology graph must be connected"
