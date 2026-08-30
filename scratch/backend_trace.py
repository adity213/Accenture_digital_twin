import requests
import time

def trace():
    print("Injecting stoppage at ST06...")
    requests.post("http://localhost:8000/api/anomalies/inject", json={
        "target_station": "ST06",
        "anomaly_type": "sudden_stoppage"
    })
    
    print("Monitoring queues for 15 seconds...")
    for _ in range(15):
        res = requests.get("http://localhost:8000/api/telemetry")
        if res.status_code != 404:
            # We must use websocket since /api/telemetry is 404
            pass
        time.sleep(1)

if __name__ == "__main__":
    trace()
