"""
API Smoke & Schema Validation Tests (Day 4 Gate)
Tests all REST endpoints return HTTP 200 with required JSON keys.
"""
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_api_stations_endpoint():
    response = client.get("/api/stations")
    assert response.status_code == 200
    data = response.json()
    assert "stations" in data
    assert len(data["stations"]) == 40
    assert "edges" in data

def test_api_station_history():
    response = client.get("/api/stations/ST01/history")
    assert response.status_code == 200
    data = response.json()
    assert data["station_id"] == "ST01"
    assert "history" in data

def test_api_risk_current():
    response = client.get("/api/risk/current")
    assert response.status_code == 200
    data = response.json()
    assert "stations" in data

def test_api_recommendations():
    response = client.get("/api/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data

def test_api_leadership_summary():
    response = client.get("/api/leadership/summary")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "heatmap" in data
    assert "top_root_causes" in data

def test_api_simulator_control():
    # Test pause, play, step, inject anomaly
    r1 = client.post("/api/simulator/control", json={"action": "pause"})
    assert r1.status_code == 200
    assert r1.json()["is_running"] is False
    
    r2 = client.post("/api/simulator/control", json={"action": "step"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "STEPPED"
    
    r3 = client.post("/api/simulator/control", json={"action": "inject_anomaly", "anomaly_type": "sudden_stoppage", "station_id": "ST06"})
    assert r3.status_code == 200
    assert r3.json()["status"] == "ANOMALY_INJECTED"

def test_api_topology_apply():
    # Test applying topology with added station ST41
    res = client.get("/api/stations")
    data = res.json()
    stations = data["stations"]
    edges = data["edges"]
    
    stations["ST41"] = {
        "id": "ST41",
        "name": "Robotic Vision Inspection Cell",
        "zone": "Assembly",
        "station_type": "QualityScan",
        "sensor_tier": "rich",
        "target_cycle_time_s": 50.0,
        "power_base_kw": 22.0,
        "buffer_capacity_units": 8
    }
    edges.append(["ST40", "ST41"])
    
    req = {
        "stations": stations,
        "edges": edges,
        "metadata": {"name": "Test DAG Layout"}
    }
    resp = client.post("/api/topology/apply", json=req)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "TOPOLOGY_APPLIED"
    assert res_data["station_count"] == 41

def test_api_topology_reset():
    resp = client.post("/api/topology/reset")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "TOPOLOGY_RESET"
    assert data["station_count"] == 40

