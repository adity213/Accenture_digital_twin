import requests
import json
try:
    res = requests.get("http://localhost:8000/api/telemetry", timeout=2)
    with open("scratch/telemetry.json", "w") as f:
        json.dump(res.json(), f, indent=2)
    print("Telemetry dumped!")
except Exception as e:
    print(f"Error: {e}")
