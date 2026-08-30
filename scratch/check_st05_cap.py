from simulator.topology import build_line_topology
topo = build_line_topology()
print("ST05:", topo["stations"]["ST05"]["buffer_capacity_units"])
print("ST06:", topo["stations"]["ST06"]["buffer_capacity_units"])
