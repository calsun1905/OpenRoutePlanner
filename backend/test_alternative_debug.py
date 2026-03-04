"""
Alternatif Rota Debug Testi
2 nokta arası kaç farklı rota var?
"""

import networkx as nx
import osmnx as ox

# 1. Küçük bir graf indir (Kadıköy merkez, test için)
print("Graf indiriliyor...")
G = ox.graph_from_point((40.990, 29.029), dist=1000, network_type="walk")
print(f"Graf yüklendi: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# 2. İki rastgele nokta seç
nodes = list(G.nodes())
origin = nodes[0]
dest = nodes[-1]
print(f"\nOrigin: {origin}")
print(f"Dest: {dest}")

# 3. En kısa yol
shortest = nx.shortest_path(G, origin, dest, weight="length")
shortest_length = nx.shortest_path_length(G, origin, dest, weight="length")
print(f"\n[SHORTEST] {len(shortest)} nodes, {shortest_length:.0f}m")

# 4. K-Shortest Paths (Şu anki yöntem)
G_simple = nx.DiGraph(G)
k_paths = nx.shortest_simple_paths(G_simple, origin, dest, weight="length")

print("\n=== K-SHORTEST PATHS (İlk 10) ===")
paths = []
for i, path in enumerate(k_paths):
    if i >= 10:
        break

    # Uzunluk hesapla
    length = sum(G.get_edge_data(path[j], path[j+1])[0]['length']
                 for j in range(len(path)-1))

    # Node overlap
    overlap = len(set(shortest) & set(path)) / len(set(shortest) | set(path))

    print(f"{i+1}. {len(path)} nodes, {length:.0f}m, overlap: {overlap:.1%}")
    paths.append(path)

# 5. Kaç gerçekten FARKLI yol var?
print("\n=== FARKLILIK ANALİZİ ===")
for i in range(min(5, len(paths))):
    if i == 0:
        continue
    overlap = len(set(paths[0]) & set(paths[i])) / len(set(paths[0]) | set(paths[i]))
    fark = len(set(paths[0]) ^ set(paths[i]))  # Simetrik fark
    print(f"Path {i+1} vs Shortest: {overlap:.1%} overlap, {fark} farklı node")
