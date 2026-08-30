import asyncio
import websockets
import json
import sys

async def dump_telemetry():
    uri = "ws://localhost:8000/api/ws/stream"
    try:
        async with websockets.connect(uri) as websocket:
            message = await websocket.recv()
            data = json.loads(message)
            with open("scratch/telemetry.json", "w") as f:
                json.dump(data, f, indent=2)
            print("Successfully dumped websocket telemetry")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

asyncio.run(dump_telemetry())
