"""Full factory diagnostic: dump every station's queue depth, processing state, and cycle times."""
import asyncio
import websockets
import json

async def diagnose():
    uri = "ws://localhost:8000/api/ws/stream"
    async with websockets.connect(uri) as ws:
        msg = json.loads(await ws.recv())
    
    stations = msg.get("stations", {})
    vehicles = msg.get("vehicles", [])
    
    print(f"=== FACTORY DIAGNOSTIC ===")
    print(f"Total active vehicles: {len(vehicles)}")
    print()
    
    total_queued = 0
    total_processing = 0
    problem_stations = []
    
    for sid in sorted(stations.keys(), key=lambda s: int(s.replace("ST","").replace("A","99"))):
        st = stations[sid]
        q_len = len(st.get("queued_vins", []))
        proc = st.get("processing_vin", None)
        cap = st.get("buffer_capacity", "?")
        ct = st.get("cycle_time", "?")
        stopped = st.get("is_stopped", False)
        total_queued += q_len
        if proc:
            total_processing += 1
        
        flag = ""
        if q_len > 3:
            flag = " *** HIGH QUEUE"
            problem_stations.append(sid)
        if stopped:
            flag += " *** STOPPED"
        
        print(f"  {sid:6s} | queue: {q_len:3d}/{cap} | processing: {'YES' if proc else '---'} | cycle_time: {ct}s | stopped: {stopped}{flag}")
    
    print()
    print(f"TOTAL vehicles queued across all stations: {total_queued}")
    print(f"TOTAL vehicles being processed: {total_processing}")
    print(f"TOTAL vehicles in system: {len(vehicles)}")
    print(f"Problem stations (queue > 3): {problem_stations}")
    
    # Check JPH setting
    print()
    print("=== VEHICLE SPAWN ANALYSIS ===")
    vins = sorted([v["vin"] for v in vehicles])
    if vins:
        print(f"First VIN: {vins[0]}")
        print(f"Last VIN:  {vins[-1]}")
        print(f"Total fleet size: {len(vins)}")
    
    # Check where vehicles are concentrated
    station_counts = {}
    for v in vehicles:
        cs = v.get("current_station", "?")
        station_counts[cs] = station_counts.get(cs, 0) + 1
    
    print()
    print("=== VEHICLES PER STATION ===")
    for sid in sorted(station_counts.keys(), key=lambda s: int(s.replace("ST","").replace("A","99"))):
        cnt = station_counts[sid]
        bar = "#" * cnt
        print(f"  {sid:6s}: {cnt:3d} {bar}")

asyncio.run(diagnose())
