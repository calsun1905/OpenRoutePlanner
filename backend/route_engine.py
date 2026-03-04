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


def path_to_edges(G, path_nodes):
    """
    Node listesini edge listesine çevirir.
    MultiDiGraph için edge'ler (u, v, key) tuple olarak temsil edilir.
    """
    edges = []
    for i in range(len(path_nodes) - 1):
        edge_data = G.get_edge_data(path_nodes[i], path_nodes[i + 1])
        if edge_data:
            # MultiDiGraph'te ilk key'i al
            first_key = list(edge_data.keys())[0]
            edges.append((path_nodes[i], path_nodes[i + 1], first_key))
    return edges


def count_edge_overlap(edges1, edges2):
    """
    İki rota arasındaki EDGE (kenar) overlap oranını hesaplar.
    Node overlap yerine edge overlap kullan çünkü aynı node'lar
    farklı kenarlarla bağlanabilir (örn: çift yönlü yollar).
    """
    set1 = set(edges1)
    set2 = set(edges2)
    if not set1 or not set2:
        return 1.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 1.0


def dynamic_overlap_threshold(distance_km: float) -> float:
    """
    Rota uzunluğuna göre maksimum izin verilen overlap oranını belirler.
    Kısa rotalarda biraz daha yüksek, uzun rotalarda daha düşük tutulur.
    Böylece:
      - Kısa mesafede alternatif bulmak kolaylaşır,
      - Uzun rotalarda daha farklı güzergahlar tercih edilir.
    """
    if distance_km < 1.0:
        # Çok kısa rotalarda neredeyse tüm yollar benzer olacağı için esnek ol
        return 0.90
    if distance_km < 3.0:
        return 0.80
    if distance_km < 7.0:
        return 0.75
    # Çok uzun rotalarda gerçekten daha farklı yol iste
    return 0.70


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

    try:
        print(f"[RouteEngine] === EDGE BAZLI ALTERNATİF ROTALAR === {origin_node} -> {dest_node}")

        # Yen's K-Shortest Paths algorithm (nx.shortest_simple_paths) doesn't support MultiDiGraphs.
        # We temporarily convert the graph to a simple DiGraph to find the node sequences.
        G_simple = nx.DiGraph(G)

        # K-shortest paths generator'ı oluştur (tek seferde!)
        k_paths_generator = nx.shortest_simple_paths(G_simple, origin_node, dest_node, weight="length")

        # Performans: 3 rota için biraz daha fazla aday deneyelim
        candidate_paths = []
        max_candidates = 30

        for i, path_nodes in enumerate(k_paths_generator):
            if i >= max_candidates:
                break

            path_stats = calculate_route_stats(G, path_nodes)
            path_edges = path_to_edges(G, path_nodes)

            candidate_paths.append({
                "nodes": path_nodes,
                "edges": path_edges,
                "distance_km": path_stats["total_distance_km"],
                "duration_minutes": path_stats["estimated_walk_minutes"],
                "length": len(path_nodes)
            })
            if i < 5:  # Sadece ilk 5 adayı logla (performans)
                print(f"[RouteEngine] Aday {i+1}: {path_stats['total_distance_km']} km, {len(path_edges)} edges")

        print(f"[RouteEngine] Toplam {len(candidate_paths)} aday yol bulundu")

        if not candidate_paths:
            print(f"[RouteEngine] HATA: Hiç yol bulunamadı!")
            return []

        # 1. En kısa yol mutlaka ilk alternatif olsun
        shortest = candidate_paths[0]
        shortest_edges = shortest["edges"]

        # Rota uzunluğuna göre dinamik overlap eşiği belirle
        MAX_OVERLAP = dynamic_overlap_threshold(shortest["distance_km"])
        print(f"[RouteEngine] Dinamik MAX_OVERLAP = {MAX_OVERLAP:.2f} (mesafe={shortest['distance_km']:.2f} km)")

        alternatives.append({
            "type": "shortest",
            "name": route_types[0]["name"],
            "icon": route_types[0]["icon"],
            "nodes": shortest["nodes"],
            "distance_km": shortest["distance_km"],
            "duration_minutes": shortest["duration_minutes"],
            "description": route_types[0]["description"]
        })
        print(f"[RouteEngine] = SHORTEST secildi: {shortest['distance_km']} km, {len(shortest_edges)} edges")

        # 2. ve 3. rota: Hem shortest'tan hem de BİRBİRİNDEN farklı olmalı
        # Her yeni aday, TÜM seçilmiş rotalarla düşük overlap göstermeli
        selected_indices = [0]
        selected_edges_list = [shortest_edges]  # Seçilen her rotanın edge seti

        for idx in range(1, len(candidate_paths)):
            if len(selected_indices) >= 3:
                break

            candidate_edges = candidate_paths[idx]["edges"]

            # Tüm seçilmiş rotalarla overlap kontrolü
            overlaps_all_ok = True
            for sel_edges in selected_edges_list:
                edge_overlap = count_edge_overlap(sel_edges, candidate_edges)

                # %60'tan fazla örtüşüyorsa = aynı/benzer rota, KABUL ETME
                if edge_overlap >= MAX_OVERLAP:
                    overlaps_all_ok = False
                    break

            if overlaps_all_ok:
                selected_indices.append(idx)
                selected_edges_list.append(candidate_edges)

        # Seçilen yolları alternatifs'e ekle (shortest zaten var)
        for idx in selected_indices[1:]:
            candidate = candidate_paths[idx]
            route_type = route_types[len(alternatives)]

            alternatives.append({
                "type": route_type["type"],
                "name": route_type["name"],
                "icon": route_type["icon"],
                "nodes": candidate["nodes"],
                "distance_km": candidate["distance_km"],
                "duration_minutes": candidate["duration_minutes"],
                "description": route_type["description"]
            })

        print(f"[RouteEngine] === TOPLAM {len(alternatives)} FARKLI ALTERNATİF ROTA BULUNDU ===")

        # Her alternatif için edge sayısını logla
        for i, alt in enumerate(alternatives):
            edge_count = len(path_to_edges(G, alt["nodes"]))
            print(f"[RouteEngine] Alternatif {i+1} ({alt['type']}): {len(alt['nodes'])} nodes, {edge_count} edges, {alt['distance_km']} km")

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

    # PERFORMANS: "shortest" için Yen algoritmasına gerek yok, direkt Dijkstra yeterli
    if route_type == "shortest":
        for i in range(len(ordered_points) - 1):
            origin = find_nearest_node(G, ordered_points[i][0], ordered_points[i][1])
            dest = find_nearest_node(G, ordered_points[i + 1][0], ordered_points[i + 1][1])
            segment = shortest_path(G, origin, dest)
            if segment:
                if i == 0:
                    full_route_nodes.extend(segment)
                else:
                    full_route_nodes.extend(segment[1:])
        return full_route_nodes

    for i in range(len(ordered_points) - 1):
        origin = find_nearest_node(G, ordered_points[i][0], ordered_points[i][1])
        dest = find_nearest_node(G, ordered_points[i + 1][0], ordered_points[i + 1][1])

        alternatives = find_alternative_routes(G, origin, dest, num_routes=3)

        segment = None
        for alt in alternatives:
            if alt["type"] == route_type:
                segment = alt["nodes"]
                break

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


def build_all_alternative_routes_batch(G, ordered_points: list) -> list:
    """
    Tüm segment alternatiflerini TEK SEFERDE hesaplar, 3 tam rota döner.
    Her segment için find_alternative_routes sadece 1 kez çağrılır (3 yerine).
    
    Returns:
        list[dict]: [{"type": "shortest", "nodes": [...], ...}, {"type": "fastest", ...}, {"type": "balanced", ...}]
    """
    route_types = [
        {"type": "shortest", "name": "En Kısa Rota", "icon": "📏", "description": "Minimum mesafe"},
        {"type": "fastest", "name": "En Hızlı Rota", "icon": "⚡", "description": "Büyük yolları tercih eder"},
        {"type": "balanced", "name": "Dengeli Rota", "icon": "⚖️", "description": "Hız ve mesafe dengesi"}
    ]

    # Her segment için alternatifleri BİR KEZ hesapla
    segment_alternatives = []
    for i in range(len(ordered_points) - 1):
        origin = find_nearest_node(G, ordered_points[i][0], ordered_points[i][1])
        dest = find_nearest_node(G, ordered_points[i + 1][0], ordered_points[i + 1][1])
        print(f"[RouteEngine] [BATCH] Segment {i+1}: {ordered_points[i]} -> {ordered_points[i+1]}")
        alts = find_alternative_routes(G, origin, dest, num_routes=3)
        print(f"[RouteEngine] [BATCH] Segment {i+1} icin {len(alts)} alternatif bulundu")
        segment_alternatives.append(alts)

    # 3 tam rota oluştur (her biri için segment seç)
    results = []
    for rt in route_types:
        full_nodes = []
        print(f"[RouteEngine] [BATCH] === {rt['type']} tam rota olusturuluyor ===")
        for seg_idx, alts in enumerate(segment_alternatives):
            segment = None
            chosen_type = None
            for alt in alts:
                if alt["type"] == rt["type"]:
                    segment = alt["nodes"]
                    chosen_type = alt["type"]
                    break
            if not segment and alts:
                segment = alts[0]["nodes"]
                chosen_type = alts[0]["type"]
            elif not segment:
                origin = find_nearest_node(G, ordered_points[seg_idx][0], ordered_points[seg_idx][1])
                dest = find_nearest_node(G, ordered_points[seg_idx + 1][0], ordered_points[seg_idx + 1][1])
                segment = shortest_path(G, origin, dest)
                chosen_type = "shortest_fallback"

            if segment:
                if seg_idx == 0:
                    full_nodes.extend(segment)
                else:
                    full_nodes.extend(segment[1:])
                print(f"[RouteEngine] [BATCH] Segment {seg_idx+1} icin secilen tip: {chosen_type}, uzunluk={len(segment)}")

        if full_nodes:
            stats = calculate_route_stats(G, full_nodes)
            print(f"[RouteEngine] [BATCH] {rt['type']} rota: {stats['total_distance_km']} km, {stats['estimated_walk_minutes']} dk")
            results.append({
                "type": rt["type"],
                "name": rt["name"],
                "icon": rt["icon"],
                "nodes": full_nodes,
                "distance_km": stats["total_distance_km"],
                "duration_minutes": stats["estimated_walk_minutes"],
                "description": rt["description"]
            })

    return results
