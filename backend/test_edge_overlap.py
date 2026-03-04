# -*- coding: utf-8 -*-
"""
Edge Based Alternative Route Test
"""

import networkx as nx
import osmnx as ox
import sys
sys.path.insert(0, '.')

# Import new functions from route_engine
from route_engine import path_to_edges, count_edge_overlap, calculate_route_stats

print("=== EDGE BASED ALTERNATIVE ROUTE TEST ===\n")

# 1. Download a small graph
print("1. Downloading graph...")
G = ox.graph_from_point((40.990, 29.029), dist=1000, network_type="walk")
print(f"   Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges\n")

# 2. Select two random nodes
nodes = list(G.nodes())
origin = nodes[0]
dest = nodes[-1]
print(f"2. Origin: {origin}, Dest: {dest}\n")

# 3. Shortest path
shortest = nx.shortest_path(G, origin, dest, weight="length")
shortest_edges = path_to_edges(G, shortest)
shortest_stats = calculate_route_stats(G, shortest)
print(f"3. SHORTEST: {len(shortest)} nodes, {shortest_stats['total_distance_km']:.2f}km, {len(shortest_edges)} edges\n")

# 4. K-Shortest Paths candidates
G_simple = nx.DiGraph(G)
k_paths = nx.shortest_simple_paths(G_simple, origin, dest, weight="length")

print("=== EDGE OVERLAP ANALYSIS (First 10 Candidates) ===")
candidates = []
for i, path in enumerate(k_paths):
    if i >= 10:
        break

    edges = path_to_edges(G, path)
    stats = calculate_route_stats(G, path)

    # Calculate edge overlap
    edge_overlap = count_edge_overlap(shortest_edges, edges)
    diff_percent = (1 - edge_overlap) * 100

    # Threshold check
    accepted = "[OK]" if edge_overlap < 0.60 else "[REJECT]"
    if i == 0:
        accepted = "[SHORTEST]"

    print(f"Path {i+1}: {len(path)} nodes, {stats['total_distance_km']:.2f}km, {len(edges)} edges")
    print(f"        Edge overlap: {edge_overlap:.1%} ({diff_percent:.0f}% different) {accepted}\n")

    candidates.append({"nodes": path, "edges": edges, "stats": stats})

# 5. Filter with threshold
print("=== AFTER THRESHOLD (Max 60% overlap) ===")
selected = [0]  # Shortest
for idx in range(1, len(candidates)):
    edge_overlap = count_edge_overlap(shortest_edges, candidates[idx]["edges"])
    if edge_overlap < 0.60:
        selected.append(idx)
        print(f"[OK] Path {idx+1} selected ({(1-edge_overlap)*100:.0f}% different streets)")
        if len(selected) >= 3:
            break

print(f"\nResult: {len(selected)} different routes found!")
