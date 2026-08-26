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
