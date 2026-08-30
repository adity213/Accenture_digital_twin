import requests
import time

URL = "http://localhost:8000"

print("Injecting ST06 Stoppage...")
requests.post(f"{URL}/api/anomalies/inject", json={"station_id": "ST06", "anomaly_type": "sudden_stoppage", "severity": 1.0, "duration_ticks": 60})

for i in range(15):
    time.sleep(1)
    try:
        res = requests.get(f"{URL}/api/telemetry")
        if res.status_code == 200:
            data = res.json()
            st05 = data["station_states"].get("ST05", {})
            st06 = data["station_states"].get("ST06", {})
            st05_q = st05.get("queued_vins", [])
            st06_q = st06.get("queued_vins", [])
            print(f"Tick {data['tick']} | ST05 queued: {len(st05_q)} | ST06 queued: {len(st06_q)}")
    except Exception as e:
        print(f"Error: {e}")
