import sys
import os

# Set working directory to backend so paths like "cache/map_data.graphml" work
os.chdir(os.path.join(os.path.dirname(__file__), "backend"))
sys.path.append(os.getcwd())

from route_engine import find_alternative_routes, calculate_route_stats
from graph_manager import get_graph_for_points, find_nearest_node

print("Loading graph...")
lat1, lon1 = 41.0368, 28.9850
lat2, lon2 = 41.0150, 28.9750
G = get_graph_for_points([(lat1, lon1), (lat2, lon2)])
print("Graph loaded.")

origin = find_nearest_node(G, lat1, lon1)
dest = find_nearest_node(G, lat2, lon2)

print(f"Finding paths between {origin} and {dest}...")
alts = find_alternative_routes(G, origin, dest, num_routes=3)

print("Result:")
for alt in alts:
    print(f"Type: {alt['type']}, Distance: {alt['distance_km']}, Nodes: {len(alt['nodes'])}")
