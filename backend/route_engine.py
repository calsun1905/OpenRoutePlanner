"""
route_engine.py - Rota Hesaplama Çekirdeği

Dijkstra/A* ile en kısa yol, TSP ile çoklu nokta optimizasyonu,
mesafe ve yürüme süresi hesaplaması.
"""

import networkx as nx
from networkx.algorithms.approximation import traveling_salesman_problem
from graph_manager import find_nearest_node


def shortest_path(G, origin_node: int, dest_node: int) -> list:
    """
    İki düğüm arası en kısa yolu Dijkstra algoritması ile bulur.
    
    Args:
        G: NetworkX grafiği
        origin_node: Başlangıç düğümü ID
        dest_node: Hedef düğüm ID
    
    Returns:
        list[int]: Düğüm ID listesi (rota)
    """
    try:
        path = nx.shortest_path(G, origin_node, dest_node, weight="length")
        return path
    except nx.NetworkXNoPath:
        print(f"[RouteEngine] {origin_node} -> {dest_node} arası yol bulunamadı!")
        return []


def nodes_to_coords(G, node_list: list) -> list:
    """
    Düğüm ID listesini [[lat, lon], ...] koordinat listesine çevirir.
    
    Args:
        G: NetworkX grafiği
        node_list: Düğüm ID listesi
    
    Returns:
        list[list[float]]: [[lat, lon], ...]
    """
    coords = []
    for node in node_list:
        data = G.nodes[node]
        coords.append([data["y"], data["x"]])  # y=lat, x=lon
    return coords


def solve_tsp(G, points: list) -> list:
    """
    Çoklu nokta için TSP (Gezgin Satıcı Problemi) optimizasyonu.
    En verimli ziyaret sırasını belirler.
    
    Args:
        G: NetworkX grafiği
        points: [(lat, lon), ...] koordinat listesi
    
    Returns:
        list[int]: Optimize edilmiş sıra indeksleri [0, 2, 1, 3, ...]
    """
    n = len(points)
    
    if n <= 2:
        return list(range(n))
    
    # Noktaları graf düğümlerine çevir
    nodes = [find_nearest_node(G, lat, lon) for lat, lon in points]
    
    # Düğümler arası mesafe matrisi oluştur
    # TSP için tam bir alt grafik (complete subgraph) gerekli
    # Her düğüm çifti arası en kısa yol uzunluğunu hesapla
    dist_matrix = {}
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            try:
                length = nx.shortest_path_length(G, nodes[i], nodes[j], weight="length")
                dist_matrix[(nodes[i], nodes[j])] = length
            except nx.NetworkXNoPath:
                dist_matrix[(nodes[i], nodes[j])] = float("inf")
    
    # TSP alt grafını oluştur
    tsp_graph = nx.Graph()
    for i in range(n):
        for j in range(i + 1, n):
            w = dist_matrix.get((nodes[i], nodes[j]), float("inf"))
            tsp_graph.add_edge(nodes[i], nodes[j], weight=w)
    
    # NetworkX TSP approximation kullan
    try:
        tsp_route = traveling_salesman_problem(
            tsp_graph, weight="weight", cycle=False
        )
    except Exception as e:
        print(f"[RouteEngine] TSP çözücü hatası: {e}, sıralı rota kullanılıyor.")
        return list(range(n))
    
    # TSP sonucunu orijinal indekslere çevir
    node_to_index = {node: idx for idx, node in enumerate(nodes)}
    ordered_indices = []
    seen = set()
    for node in tsp_route:
        if node in node_to_index and node not in seen:
            ordered_indices.append(node_to_index[node])
            seen.add(node)
    
    # Eksik indeks varsa sona ekle
    for i in range(n):
        if i not in ordered_indices:
            ordered_indices.append(i)
    
    return ordered_indices


def build_full_route(G, ordered_points: list) -> list:
    """
    TSP sıralamasına göre tüm noktalar arasındaki rotaları birleştirir.
    
    Args:
        G: NetworkX grafiği
        ordered_points: TSP sırasına göre [(lat, lon), ...] listesi
    
    Returns:
        list[int]: Tüm ara düğümleri içeren birleşik rota
    """
    full_route_nodes = []
    
    for i in range(len(ordered_points) - 1):
        origin = find_nearest_node(G, ordered_points[i][0], ordered_points[i][1])
        dest = find_nearest_node(G, ordered_points[i + 1][0], ordered_points[i + 1][1])
        
        segment = shortest_path(G, origin, dest)
        
        if segment:
            # İlk segment hariç, başlangıç düğümünü ekleme (önceki segmentin sonuyla aynı)
            if i == 0:
                full_route_nodes.extend(segment)
            else:
                full_route_nodes.extend(segment[1:])
    
    return full_route_nodes


def calculate_route_stats(G, route_nodes: list) -> dict:
    """
    Rota istatistiklerini hesaplar: toplam mesafe ve tahmini yürüme süresi.
    
    Args:
        G: NetworkX grafiği
        route_nodes: Düğüm ID listesi
    
    Returns:
        dict: {"total_distance_km": float, "estimated_walk_minutes": int}
    """
    total_length = 0.0  # metre cinsinden
    
    for i in range(len(route_nodes) - 1):
        try:
            # MultiDiGraph'ta birden fazla kenar olabilir, en kısasını al
            edge_data = G.get_edge_data(route_nodes[i], route_nodes[i + 1])
            if edge_data:
                # MultiDiGraph: ilk kenarın uzunluğunu al
                first_key = list(edge_data.keys())[0]
                length = edge_data[first_key].get("length", 0)
                total_length += length
        except Exception:
            continue
    
    total_km = round(total_length / 1000, 2)
    
    # Ortalama yürüme hızı: 5 km/saat
    walk_speed_kmh = 5.0
    walk_minutes = round((total_km / walk_speed_kmh) * 60)
    
    return {
        "total_distance_km": total_km,
        "estimated_walk_minutes": walk_minutes,
    }


def generate_google_maps_link(ordered_points: list) -> str:
    """
    Verilen koordinat listesi için Google Maps yol tarifi linki oluşturur.
    
    Args:
        ordered_points: [(lat, lon), ...] sıralı koordinat listesi
    
    Returns:
        str: Google Maps URL'si
    """
    if not ordered_points:
        return ""
    
    base = "https://www.google.com/maps/dir/"
    parts = [f"{lat},{lon}" for lat, lon in ordered_points]
    return base + "/".join(parts)
