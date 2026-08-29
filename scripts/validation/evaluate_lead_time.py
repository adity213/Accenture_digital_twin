import time
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator.generator import LineSimulator
from pipeline.spc import SPCEngine

def benchmark_routing_latency(num_ticks=5000):
    sim = LineSimulator(seed=42)
    
    # Let simulator run for a bit to populate vehicles and buffers
    print("Warming up the simulation (500 ticks)...")
    for _ in range(500):
        sim.step()
    
    print(f"Starting benchmark for {num_ticks} ticks...")
    routing_times = []
    total_decisions = 0
    
    for i in range(num_ticks):
        # We want to measure only the routing decision part.
        # process_tick() handles moving vehicles, advancing queue, generating telemetry, and routing.
        # Since we want to benchmark the queue-aware routing, we can time the whole tick
        # and specifically extract the routing phase if possible.
        # In generator.py, routing happens inside process_tick() at the end (moving vehicles across edges).
        # We will time process_tick() and use the total time as an upper bound,
        # but realistically, the prompt says "benchmark routing decision latency".
        # Let's time process_tick and average it.
        
        start_time = time.perf_counter()
        tick_result = sim.step()
        end_time = time.perf_counter()
        
        tick_duration_ms = (end_time - start_time) * 1000
        routing_times.append(tick_duration_ms)
        
        # Count number of decisions made
        total_decisions += 1  # 1 tick = 1 round of routing

    avg_time_ms = sum(routing_times) / len(routing_times)
    max_time_ms = max(routing_times)
    p95_time_ms = sorted(routing_times)[int(len(routing_times) * 0.95)]
    p99_time_ms = sorted(routing_times)[int(len(routing_times) * 0.99)]
    
    print("\n" + "="*50)
    print("ROUTING DECISION LATENCY BENCHMARK RESULTS")
    print("="*50)
    print(f"Total simulated ticks  : {num_ticks}")
    print(f"Total branch decisions : {total_decisions}")
    print(f"Average tick time      : {avg_time_ms:.3f} ms")
    print(f"95th percentile time   : {p95_time_ms:.3f} ms")
    print(f"99th percentile time   : {p99_time_ms:.3f} ms")
    print(f"Max tick time          : {max_time_ms:.3f} ms")
    print("="*50)
    
    if max_time_ms > 5.0:
        print("⚠️ WARNING: Peak latency exceeded the 5ms SCADA limit.")
    else:
        print("✅ SUCCESS: Routing latency is well within the 5ms SCADA limit.")

if __name__ == '__main__':
    benchmark_routing_latency(5000)
