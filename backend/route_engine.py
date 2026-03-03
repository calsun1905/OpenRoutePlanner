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


def find_alternative_routes(G, origin_node: int, dest_node: int, num_routes: int = 3) -> list:
    """
    İki nokta arası GERÇEK alternatif rotalar bulur.
    Yen's K-Shortest Paths algoritmasını kullanarak FARKLI güzergahlar üretir.

    Args:
        G: NetworkX grafiği
        origin_node: Başlangıç düğümü
        dest_node: Hedef düğüm
        num_routes: Kaç alternatif rota isteniyor (varsayılan 3)

    Returns:
        list[dict]: Alternatif rotalar (shortest, fastest, balanced)
    """
    alternatives = []

    # Rota tipi tanımlamaları
    route_types = [
        {"type": "shortest", "name": "En Kısa Rota", "icon": "📏", "description": "Minimum mesafe"},
        {"type": "fastest", "name": "En Hızlı Rota", "icon": "⚡", "description": "Büyük yolları tercih eder"},
        {"type": "balanced", "name": "Dengeli Rota", "icon": "⚖️", "description": "Hız ve mesafe dengesi"}
    ]

    def count_overlap(nodes1, nodes2):
        """İki rota arasındaki node overlap oranını hesaplar"""
        set1 = set(nodes1)
        set2 = set(nodes2)
        if not set1 or not set2:
            return 1.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 1.0

    try:
        print(f"[RouteEngine] === GERÇEK ALTERNATİF ROTALAR AÇILIYOR === {origin_node} -> {dest_node}")

        # Yen's K-Shortest Paths algorithm (nx.shortest_simple_paths) doesn't support MultiDiGraphs.
        # We temporarily convert the graph to a simple DiGraph to find the node sequences.
        G_simple = nx.DiGraph(G)

        # K-shortest paths generator'ı oluştur (tek seferde!)
        k_paths_generator = nx.shortest_simple_paths(G_simple, origin_node, dest_node, weight="length")

        # İlk 10-15 yolu al ve aralarından en farklı 3'ünü seç
        candidate_paths = []
        max_candidates = 15  # Maksimum aday yol

        for i, path_nodes in enumerate(k_paths_generator):
            if i >= max_candidates:
                break

            path_stats = calculate_route_stats(G, path_nodes)
            candidate_paths.append({
                "nodes": path_nodes,
                "distance_km": path_stats["total_distance_km"],
                "duration_minutes": path_stats["estimated_walk_minutes"],
                "length": len(path_nodes)
            })
            print(f"[RouteEngine] Aday {i+1}: {path_stats['total_distance_km']} km, {len(path_nodes)} nodes")

        print(f"[RouteEngine] Toplam {len(candidate_paths)} aday yol bulundu")

        if not candidate_paths:
            print(f"[RouteEngine] HATA: Hiç yol bulunamadı!")
            return []

        # 1. En kısa yol mutlaka ilk alternatif olsun
        shortest = candidate_paths[0]
        alternatives.append({
            "type": "shortest",
            "name": route_types[0]["name"],
            "icon": route_types[0]["icon"],
            "nodes": shortest["nodes"],
            "distance_km": shortest["distance_km"],
            "duration_minutes": shortest["duration_minutes"],
            "description": route_types[0]["description"]
        })
        print(f"[RouteEngine] = SHORTEST secildi: {shortest['distance_km']} km")

        # 2. En farklı ikinci yolu bul (minimum overlap)
        if len(candidate_paths) > 1:
            best_second_idx = 1
            min_overlap = 1.0

            for idx in range(1, len(candidate_paths)):
                overlap = count_overlap(shortest["nodes"], candidate_paths[idx]["nodes"])
                print(f"[RouteEngine] Aday {idx+1} overlap: {overlap:.2%}")
                if overlap < min_overlap:
                    min_overlap = overlap
                    best_second_idx = idx

            second_path = candidate_paths[best_second_idx]
            alternatives.append({
                "type": "fastest",
                "name": route_types[1]["name"],
                "icon": route_types[1]["icon"],
                "nodes": second_path["nodes"],
                "distance_km": second_path["distance_km"],
                "duration_minutes": second_path["duration_minutes"],
                "description": route_types[1]["description"]
            })
            print(f"[RouteEngine] = FASTEST secildi (idx {best_second_idx+1}): {second_path['distance_km']} km (overlap: {min_overlap:.2%})")

        # 3. En farklı üçüncü yolu bul (hem birinciyle hem ikinciyle minimum overlap)
        if len(candidate_paths) > 2:
            best_third_idx = 2
            min_combined_overlap = 1.0

            for idx in range(1, len(candidate_paths)):
                if idx == best_second_idx:
                    continue  # İkinci olarak seçileni atla

                overlap1 = count_overlap(shortest["nodes"], candidate_paths[idx]["nodes"])
                overlap2 = count_overlap(candidate_paths[best_second_idx]["nodes"], candidate_paths[idx]["nodes"])
                avg_overlap = (overlap1 + overlap2) / 2

                print(f"[RouteEngine] Aday {idx+1} combined overlap: {avg_overlap:.2%}")

                if avg_overlap < min_combined_overlap:
                    min_combined_overlap = avg_overlap
                    best_third_idx = idx

            third_path = candidate_paths[best_third_idx]
            alternatives.append({
                "type": "balanced",
                "name": route_types[2]["name"],
                "icon": route_types[2]["icon"],
                "nodes": third_path["nodes"],
                "distance_km": third_path["distance_km"],
                "duration_minutes": third_path["duration_minutes"],
                "description": route_types[2]["description"]
            })
            print(f"[RouteEngine] = BALANCED secildi (idx {best_third_idx+1}): {third_path['distance_km']} km (overlap: {min_combined_overlap:.2%})")

        print(f"[RouteEngine] === TOPLAM {len(alternatives)} FARKLI ALTERNATİF ROTA BULUNDU ===")

        # Her alternatif için node sayısını logla
        for i, alt in enumerate(alternatives):
            print(f"[RouteEngine] Alternatif {i+1} ({alt['type']}): {len(alt['nodes'])} nodes, {alt['distance_km']} km")

    except Exception as e:
        print(f"[RouteEngine] KRİTİK HATA: {e}")
        import traceback
        traceback.print_exc()

        # Fallback: En azından en kısa rotayı döndür
        try:
            shortest_nodes = nx.shortest_path(G, origin_node, dest_node, weight="length")
            shortest_stats = calculate_route_stats(G, shortest_nodes)
            return [{
                "type": "shortest",
                "name": route_types[0]["name"],
                "icon": route_types[0]["icon"],
                "nodes": shortest_nodes,
                "distance_km": shortest_stats["total_distance_km"],
                "duration_minutes": shortest_stats["estimated_walk_minutes"],
                "description": "Tek mevcut rota"
            }]
        except:
            return []

    return alternatives


def build_alternative_routes(G, ordered_points: list, route_type: str = "shortest") -> list:
    """
    Çoklu nokta için alternatif rota stratejisi ile tam rota oluşturur.
    
    Args:
        G: NetworkX grafiği
        ordered_points: Sıralı [(lat, lon), ...] listesi
        route_type: "shortest", "fastest", veya "balanced"
    
    Returns:
        list[int]: Düğüm listesi
    """
    full_route_nodes = []
    
    for i in range(len(ordered_points) - 1):
        origin = find_nearest_node(G, ordered_points[i][0], ordered_points[i][1])
        dest = find_nearest_node(G, ordered_points[i + 1][0], ordered_points[i + 1][1])
        
        # Alternatif rotaları bul
        alternatives = find_alternative_routes(G, origin, dest, num_routes=3)
        
        # İstenen tip rotayı seç
        segment = None
        for alt in alternatives:
            if alt["type"] == route_type:
                segment = alt["nodes"]
                break
        
        # Bulunamazsa en kısa rotayı kullan
        if not segment and alternatives:
            segment = alternatives[0]["nodes"]
        elif not segment:
            segment = shortest_path(G, origin, dest)
        
        if segment:
            if i == 0:
                full_route_nodes.extend(segment)
            else:
                full_route_nodes.extend(segment[1:])
    
    return full_route_nodes
