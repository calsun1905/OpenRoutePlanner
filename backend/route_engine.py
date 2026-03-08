"""
route_engine.py - Rota Hesaplama Çekirdeği v3.0

Dijkstra/A* ile en kısa yol, TSP ile çoklu nokta optimizasyonu,
mesafe ve yürüme süresi hesaplaması.

v3.0 DEĞİŞİKLİKLER:
- Via-Node (Ara Nokta): Endüstri standardı alternatif rota üretimi
- Asimetrik overlap: Jaccard yerine "yeni rotanın % kaçı eskiyle aynı?"
- Gövde-only penalty: Baş/son %10'a dokunma, sadece gövdeye ceza ver
- Disjoint paths → Via-Node (OSM çıkmaz sokak problemi çözüldü)
- Telemetry logging ile performans takibi
"""

import networkx as nx
from networkx.algorithms.approximation import traveling_salesman_problem
from networkx.algorithms.connectivity import edge_disjoint_paths, edge_connectivity
from graph_manager import find_nearest_node
from route_config import ROUTE_CONFIG
import time
import math
from typing import Dict, List, Tuple, Optional


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


def _node_coord(G, node_id: int) -> List[float]:
    """Graf node'unu [lat, lon] formatinda dondurur."""
    data = G.nodes[node_id]
    return [data["y"], data["x"]]  # y=lat, x=lon


def _extract_edge_coords(G, u: int, v: int) -> List[List[float]]:
    """
    Iki node arasindaki edge geometrisini [lat, lon] listesine cevirir.
    Geometri yoksa veya okunamazsa [u, v] node koordinatlarini dondurur.
    """
    default_coords = [_node_coord(G, u), _node_coord(G, v)]
    edge_data = G.get_edge_data(u, v)
    if not edge_data:
        return default_coords

    # Birden fazla paralel edge varsa "length" en kisa olani sec.
    best = min(edge_data.values(), key=lambda d: d.get("length", float("inf")))
    geom = best.get("geometry")
    if geom is None:
        return default_coords

    try:
        # Shapely LineString -> [(lon, lat), ...] formatinda gelir.
        coords = [[lat, lon] for lon, lat in geom.coords]
    except Exception:
        return default_coords

    if len(coords) < 2:
        return default_coords

    # Geometri yonu tersse rota yonune gore cevir.
    u_coord = _node_coord(G, u)
    v_coord = _node_coord(G, v)

    def sqdist(a: List[float], b: List[float]) -> float:
        return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2

    normal_cost = sqdist(coords[0], u_coord) + sqdist(coords[-1], v_coord)
    reverse_cost = sqdist(coords[0], v_coord) + sqdist(coords[-1], u_coord)
    if reverse_cost < normal_cost:
        coords.reverse()

    return coords


def nodes_to_coords(G, node_list: list) -> list:
    """
    Node listesi icin rota geometrisini [lat, lon] listesi olarak dondurur.
    Edge geometry varsa ona gore cizer; yoksa node'lari dogrudan birlestirir.
    """
    if not node_list:
        return []
    if len(node_list) == 1:
        return [_node_coord(G, node_list[0])]

    route_coords: List[List[float]] = []
    for i in range(len(node_list) - 1):
        seg_coords = _extract_edge_coords(G, node_list[i], node_list[i + 1])
        if not route_coords:
            route_coords.extend(seg_coords)
        else:
            # Bir onceki segmentin son noktasi ile duplicate olusmasin.
            if route_coords[-1] == seg_coords[0]:
                route_coords.extend(seg_coords[1:])
            else:
                route_coords.extend(seg_coords)
    return route_coords

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
    print(f"[ROUTE] TSP baslatildi: {n} nokta")

    if n <= 2:
        print(f"[ROUTE] TSP tamamlandi: {list(range(n))} (2 nokta, optimizasyon gerekmez)")
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

    print(f"[ROUTE] TSP tamamlandi: {ordered_indices}")
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
            if edge_data and len(edge_data) > 0:
                # MultiDiGraph: ilk kenarın uzunluğunu al
                first_key = list(edge_data.keys())[0]
                length = edge_data[first_key].get("length", 0)
                total_length += length
        except Exception as e:
            print(f"[RouteEngine] Kenar uzunluğu hesaplama hatası (segment {i}): {e}")
            continue
    
    total_km = round(total_length / 1000, 2)

    # Ortalama yürüme hızı: config'den al
    walk_speed_kmh = ROUTE_CONFIG.get("WALK_SPEED_KMH", 5.0)
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
        if edge_data and len(edge_data) > 0:
            # MultiDiGraph'te ilk key'i al
            first_key = list(edge_data.keys())[0]
            edges.append((path_nodes[i], path_nodes[i + 1], first_key))
    return edges


def count_edge_overlap(edges1, edges2):
    """
    İki rota arasındaki asimetrik EDGE overlap oranını hesaplar.
    "edges2 (yeni rota) kenarlarının ne kadarı edges1 (eski rota) ile örtüşüyor?"

    v3.0: Jaccard (intersection/union) yerine asimetrik formül.
    Jaccard alt küme durumunu yakalayamaz:
      100 kenarlık rotanın 20 kenarı → Jaccard %20, gerçek %100.
      Asimetrik: 20/20 = %100 → doğru şekilde reddedilir.
    """
    if not edges1 or not edges2:
        return 0.0  # Boş set = örtüşme yok

    # Edge'leri normalize et: key'i ignore et, sadece (u, v) çiftini kullan
    # MultiDiGraph'ta aynı sokak (u, v, 0) ve (v, u, 0) farklı olabilir
    # Bu yüzden yön-independent normalize et
    def normalize_edge(edge):
        if len(edge) >= 2:
            u, v = edge[0], edge[1]
            return (min(u, v), max(u, v))  # Yönsuz çift
        return edge

    set1 = {normalize_edge(e) for e in edges1}
    set2 = {normalize_edge(e) for e in edges2}

    if not set1 or not set2:
        return 0.0

    intersection = len(set1 & set2)
    # Asimetrik: "Yeni rotanın (set2) ne kadarı eski rotayla örtüşüyor?"
    return intersection / len(set2) if len(set2) > 0 else 0.0


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
        return ROUTE_CONFIG.get("OVERLAP_THRESHOLD_SHORT", 0.90)
    if distance_km < 3.0:
        return ROUTE_CONFIG.get("OVERLAP_THRESHOLD_MEDIUM", 0.80)
    if distance_km < 7.0:
        return ROUTE_CONFIG.get("OVERLAP_THRESHOLD_LONG", 0.75)
    # Çok uzun rotalarda gerçekten daha farklı yol iste
    return ROUTE_CONFIG.get("OVERLAP_THRESHOLD_VERY_LONG", 0.70)


def get_max_candidates(distance_km: float) -> int:
    """
    Rota uzunluğuna göre dinamik aday sayısı belirler.
    Kısa rotalarda daha az, uzun rotalarda daha fazla aday dener.
    """
    if distance_km < 1.0:
        return ROUTE_CONFIG.get("MAX_CANDIDATES_VERY_SHORT", 50)   # Çok kısa rotalar
    elif distance_km < 3.0:
        return ROUTE_CONFIG.get("MAX_CANDIDATES_SHORT", 75)        # Kısa rotalar
    elif distance_km < 7.0:
        return ROUTE_CONFIG.get("MAX_CANDIDATES_LONG", 100)        # Orta rotalar
    else:
        return ROUTE_CONFIG.get("MAX_CANDIDATES_VERY_LONG", 150)   # Uzun rotalar - maksimum alternatif şansı


# ===========================================================================
# YENİ v2.0 FONKSİYONLAR - Topology Analizi ve Disjoint Paths
# ===========================================================================

class RouteTelemetry:
    """
    Alternatif rota üretimi için telemetry sınıfı.
    Performans metriklerini takip eder.
    """
    def __init__(self):
        self.start_time = time.time()
        self.connectivity = None
        self.disjoint_found = 0
        self.via_node_found = 0
        self.yen_candidates = 0
        self.unique_routes = 0
        self.overlaps = []
        self.generation_method = None

    def finish(self):
        """Telemetry verilerini tamamla ve logla"""
        self.elapsed = time.time() - self.start_time

        print(f"[RouteTelemetry] ════════════════════════════════════")
        print(f"[RouteTelemetry] Generation Method: {self.generation_method}")
        print(f"[RouteTelemetry] Edge Connectivity: {self.connectivity}")
        print(f"[RouteTelemetry] Via-Node Found: {self.via_node_found}")
        print(f"[RouteTelemetry] Penalty Candidates: {self.yen_candidates}")
        print(f"[RouteTelemetry] Unique Routes: {self.unique_routes}")
        if self.overlaps:
            print(f"[RouteTelemetry] Overlaps: {[f'{o:.1%}' for o in self.overlaps]}")
        print(f"[RouteTelemetry] Total Time: {self.elapsed:.2f}s")
        print(f"[RouteTelemetry] ════════════════════════════════════")

        return {
            "connectivity": self.connectivity,
            "disjoint_found": self.disjoint_found,
            "unique_routes": self.unique_routes,
            "overlaps": self.overlaps,
            "generation_time": self.elapsed
        }


def check_alternative_potential(G: nx.Graph, origin: int, dest: int, telemetry: RouteTelemetry = None) -> int:
    """
    Topoloji ön-analizi: Origin ve destination arası kaç edge-disjoint yol var?

    NetworkX edge_connectivity kullanarak maksimum farklı yol sayısını tahmin eder.
    Bu sayede "gerçekte kaç alternatif mümkün" önceden bilinir.

    Args:
        G: NetworkX grafiği
        origin: Başlangıç düğümü
        dest: Hedef düğümü
        telemetry: Opsiyonel telemetry nesnesi

    Returns:
        int: Mümkün olan maksimum alternatif rota sayısı (1-3 arası)
    """
    try:
        # Edge connectivity: Kaç kenar silinirse iki node ayrılır?
        # Bu, maksimum edge-disjoint path sayısına eşittir (Menger's teoremi)
        max_disjoint = edge_connectivity(G, origin, dest)

        if telemetry:
            telemetry.connectivity = max_disjoint

        print(f"[RouteEngine] Topoloji analizi: edge_connectivity = {max_disjoint}")

        # Graceful degrade: Gerçekçi sayıya dönüştür
        # 1'den az olamaz, 3'ten fazla gerek yok (biz max 3 istiyoruz)
        realistic_max = min(max_disjoint, 3)

        if realistic_max < 3:
            print(f"[RouteEngine] ⚠️  Graph sadece {realistic_max} alternatif destekliyor (graceful degrade)")

        return max(1, realistic_max)

    except Exception as e:
        print(f"[RouteEngine] Edge connectivity hesaplama hatası: {e}")
        if telemetry:
            telemetry.connectivity = "unknown"
        # Hata durumunda en az 1 rota garanti
        return 1


def find_disjoint_paths(G: nx.Graph, origin: int, dest: int, num_paths: int = 2, telemetry: RouteTelemetry = None) -> list:
    """
    Suurballe-style edge-disjoint paths bulur.

    NetworkX'in edge_disjoint_paths fonksiyonunu kullanarak
    birbirini KESİŞMEYEN yollar (farklı sokaklar) üretir.

    Args:
        G: NetworkX grafiği
        origin: Başlangıç düğümü
        dest: Hedef düğümü
        num_paths: Kaç disjoint yol isteniyor
        telemetry: Opsiyonel telemetry nesnesi

    Returns:
        list[dict]: Disjoint rotalar (nodes, edges, distance_km, duration_minutes)
    """
    disjoint_routes = []

    try:
        print(f"[RouteEngine] Disjoint paths aranıyor (max {num_paths})...")

        # NetworkX edge_disjoint_paths kullan
        # Bu fonksiyon flow algoritması kullanır, garantili disjoint
        paths_generator = edge_disjoint_paths(G, origin, dest, cutoff=num_paths)

        for path_nodes in paths_generator:
            if len(disjoint_routes) >= num_paths:
                break

            path_edges = path_to_edges(G, path_nodes)
            path_stats = calculate_route_stats(G, path_nodes)

            disjoint_routes.append({
                "nodes": path_nodes,
                "edges": path_edges,
                "distance_km": path_stats["total_distance_km"],
                "duration_minutes": path_stats["estimated_walk_minutes"],
                "length": len(path_nodes),
                "source": "disjoint"  # Kaynak işaretle
            })

            print(f"[RouteEngine] ✓ Disjoint rota #{len(disjoint_routes)}: {path_stats['total_distance_km']:.2f} km")

        if telemetry:
            telemetry.disjoint_found = len(disjoint_routes)

    except nx.NetworkXNoPath:
        print(f"[RouteEngine] Disjoint paths bulunamadı (yol yok)")

    except Exception as e:
        print(f"[RouteEngine] Disjoint paths hatası: {e}")

    return disjoint_routes


def dynamic_overlap_threshold_connectivity(distance_km: float, connectivity: int = None) -> float:
    """
    Hem mesafeye HEM connectivity'ye göre dinamik overlap eşiği.

    Mantık:
    - Yüksek connectivity (3+) → Daha fazla alternatif var → Biraz daha katı threshold
    - Düşük connectivity (1-2) → Az alternatif var → Esnek threshold

    BUG FIX v2.0.1:
    - Çarpanları daha conservative yap (telemetry ile tune edilecek)
    - Eski: *0.5, *0.7, *0.9 → Yeni: *0.75, *0.85, *0.95
    - Bu şekilde daha fazla alternatif kabul edilir

    Args:
        distance_km: Rota mesafesi
        connectivity: Edge connectivity değeri (opsiyonel)

    Returns:
        float: Maksimum izin verilen overlap oranı (0-1 arası)
    """
    # Önce mesafe bazlı taban threshold
    if distance_km < 1.0:
        base_threshold = 0.90
    elif distance_km < 3.0:
        base_threshold = 0.80
    elif distance_km < 7.0:
        base_threshold = 0.75
    else:
        base_threshold = 0.70

    # Connectivity varsa, buna göre ayarla (CONSERVATIVE çarpanlar)
    if connectivity is not None:
        if connectivity >= 3:
            # Yüksek connectivity → Biraz daha katı (ama abartma)
            return base_threshold * 0.75  # %52-67 arası (eski: %35-45)

        elif connectivity == 2:
            # Orta connectivity → Orta seviye
            return base_threshold * 0.85  # %68-85 arası (eski: %50-60)

        else:  # connectivity == 1
            # Düşük connectivity → Çok esnek (az alternatif var)
            return base_threshold * 0.95  # %76-95 arası (eski: %60-80)

    return base_threshold


def apply_penalty_to_graph(G: nx.Graph, used_edges: list, penalty_factor: float = None) -> nx.Graph:
    """
    Kullanılan kenarlara ceza uygulayarak grafiği kopyalar.

    Penalty-based generation: Önceden kullanılan yolları pahalı hale getirir,
    böylece sonraki aramalar FARKLI yolları tercih eder.

    BUG FIX v2.0.1:
    - MultiDiGraph için güvenli approach
    - Tekil 'penalty_length' attribute ile çalış
    - weight='penalty_length' ile doğrudan kullanılabilir

    Args:
        G: Orijinal NetworkX grafiği
        used_edges: Kullanılan kenar listesi [(u, v, key), ...]
        penalty_factor: Cezalandırma çarpanı (varsayılan 2x)

    Returns:
        nx.Graph: Penalize edilmiş graf kopyası
    """
    if penalty_factor is None:
        penalty_factor = ROUTE_CONFIG.get("PENALTY_FACTOR", 2.0)

    G_penalty = G.copy()

    # Her düğüm çifti için en az bir edge var mı kontrol et
    penalized_edges = set()

    for edge in used_edges:
        if len(edge) >= 2:
            u, v = edge[0], edge[1]
            # Yönsuz normalize et
            edge_key = (min(u, v), max(u, v))
            penalized_edges.add(edge_key)

    # Penalize edilmiş edge'lere yeni weight ekle
    for u, v, key, data in G_penalty.edges(keys=True, data=True):
        edge_key = (min(u, v), max(u, v))

        if edge_key in penalized_edges:
            # Bu kenar kullanıldı, cezalandır
            original_length = data.get('length', 1)
            data['penalty_length'] = original_length * penalty_factor
        else:
            # Kullanılmadı, normal length
            data['penalty_length'] = data.get('length', 1)

    return G_penalty


def find_routes_with_penalty(G: nx.Graph, origin: int, dest: int,
                            used_edges: list, num_routes: int = 3,
                            penalty_factor: float = None) -> list:
    """
    Penalty-based generation ile ekstra rotalar bulur.

    Mevcut rotalarda kullanılan kenarlara ceza vererek,
    aynı yolları tekrar bulmayı engeller.

    BUG FIX v2.0.1:
    - weight='penalty_length' ile doğrudan shortest_path kullan
    - Karmaşık weight fonksiyonu yerine hazır attribute
    - MultiDiGraph uyumlu

    Args:
        G: NetworkX grafiği
        origin: Başlangıç düğümü
        dest: Hedef düğümü
        used_edges: Daha önce kullanılan kenarlar (TÜM kullanılan kenarlar)
        num_routes: Kaç rota isteniyor
        penalty_factor: Cezalandırma çarpanı

    Returns:
        list[dict]: Penalty ile bulunan rotalar
    """
    if penalty_factor is None:
        penalty_factor = ROUTE_CONFIG.get("PENALTY_FACTOR", 2.0)

    penalty_routes = []

    try:
        current_used = list(used_edges)  # Girişi mutate etme, kopya al

        for i in range(num_routes):
            try:
                # Her iterasyonda penalty grafını YENİDEN oluştur
                G_penalty = apply_penalty_to_graph(G, current_used, penalty_factor)

                path_nodes = nx.shortest_path(G_penalty, origin, dest, weight="penalty_length")
                path_edges = path_to_edges(G, path_nodes)
                path_stats = calculate_route_stats(G, path_nodes)

                penalty_routes.append({
                    "nodes": path_nodes,
                    "edges": path_edges,
                    "distance_km": path_stats["total_distance_km"],
                    "duration_minutes": path_stats["estimated_walk_minutes"],
                    "length": len(path_nodes),
                    "source": "penalty"
                })

                print(f"[RouteEngine] ✓ Penalty rota #{i+1}: {path_stats['total_distance_km']:.2f} km")

                # Sonraki iterasyona bu kenarları da ekle
                current_used.extend(path_edges)

            except nx.NetworkXNoPath:
                break

    except Exception as e:
        print(f"[RouteEngine] Penalty-based generation hatası: {e}")

    return penalty_routes


def get_fallback_routes(G, origin_node: int, dest_node: int) -> list:
    """
    Multi-level fallback stratejisi.
    Her seviye daha basit ama daha güvenilir.
    """
    fallbacks = []

    # Level 1: Basit Dijkstra
    try:
        shortest_nodes = nx.shortest_path(G, origin_node, dest_node, weight="length")
        shortest_stats = calculate_route_stats(G, shortest_nodes)
        fallbacks.append({
            "type": "route_1",
            "name": "Rota 1",
            "icon": "📍",
            "nodes": shortest_nodes,
            "distance_km": shortest_stats["total_distance_km"],
            "duration_minutes": shortest_stats["estimated_walk_minutes"],
            "description": f"{shortest_stats['total_distance_km']} km"
        })
        print(f"[RouteEngine] Fallback Level 1: Dijkstra ile rota bulundu")
    except nx.NetworkXNoPath:
        print(f"[RouteEngine] Fallback Level 1 basarisiz")
        return []

    # Level 2: Komşu node'ları dene (en fazla 2 tane)
    if len(fallbacks) < 3:
        try:
            origin_neighbors = list(G.neighbors(origin_node))[:3]
            dest_neighbors = list(G.neighbors(dest_node))[:3]

            for o_n in origin_neighbors:
                for d_n in dest_neighbors:
                    if len(fallbacks) >= 3:
                        break
                    try:
                        alt_path = nx.shortest_path(G, o_n, d_n, weight="length")
                        full_path = [origin_node] + alt_path + [dest_node]
                        stats = calculate_route_stats(G, full_path)

                        # Çok uzun değilse kabul et
                        if stats["total_distance_km"] <= shortest_stats["total_distance_km"] * 1.5:
                            fallbacks.append({
                                "type": f"route_{len(fallbacks)+1}",
                                "name": f"Rota {len(fallbacks)+1}",
                                "icon": "📍",
                                "nodes": full_path,
                                "distance_km": stats["total_distance_km"],
                                "duration_minutes": stats["estimated_walk_minutes"],
                                "description": f"{stats['total_distance_km']:.1f} km"
                            })
                            print(f"[RouteEngine] Fallback Level 2: Komşu node ile rota bulundu")
                    except nx.NetworkXNoPath:
                        continue
                if len(fallbacks) >= 3:
                    break
        except Exception as e:
            print(f"[RouteEngine] Fallback Level 2 hatasi: {e}")

    return fallbacks[:3]


# ===========================================================================
# v3.0 FONKSİYONLAR - Via-Node ve Gövde-Only Penalty
# ===========================================================================

def get_body_edges(edges, skip_ratio=0.10):
    """
    Rotanın baş ve son kısmını atlayıp sadece gövde kenarlarını döndürür.
    Penalty sisteminde zikzak oluşmasını önler:
    baş/son kenarlar cezalandırılmaz, sadece ortadaki gövde kenarları.
    """
    n = len(edges)
    if n <= 4:
        return edges
    skip = max(1, int(n * skip_ratio))
    return edges[skip:-skip]


def find_via_node_routes(G, origin_node, dest_node, main_route_nodes,
                         num_via_routes=2, max_distance_ratio=1.5):
    """
    Via-Node (Ara Nokta) yaklaşımı ile alternatif rotalar bulur.

    Endüstri standardı: Google Maps / OSRM tarzı.
    Ana rotadan geometrik olarak uzak büyük kavşakları bulur,
    rotayı bu kavşaklardan geçmeye zorlar (A → C → B).

    Algoritma:
    1. Ana rota koordinatlarının bounding box'ını genişlet
    2. Bounding box içindeki yüksek degree (kavşak) node'ları bul
    3. Ana rotadan en uzak olanları via-node olarak seç
    4. A → via → B rotası oluştur
    5. Çok uzun rotaları reddet (max_distance_ratio)
    """
    via_routes = []

    if not main_route_nodes or len(main_route_nodes) < 2:
        return via_routes

    # Ana rota koordinatları
    main_coords = []
    for n in main_route_nodes:
        data = G.nodes[n]
        main_coords.append((data.get('y', 0), data.get('x', 0)))

    main_stats = calculate_route_stats(G, main_route_nodes)
    main_km = main_stats["total_distance_km"]

    if main_km <= 0:
        return via_routes

    # Bounding box hesapla ve genişlet
    lats = [c[0] for c in main_coords]
    lons = [c[1] for c in main_coords]
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)

    # %30 genişlet + minimum ~200m garanti (çok kısa rotalar için)
    MIN_MARGIN = 0.002
    lat_margin = max(MIN_MARGIN, (lat_max - lat_min) * 0.3)
    lon_margin = max(MIN_MARGIN, (lon_max - lon_min) * 0.3)
    lat_min -= lat_margin
    lat_max += lat_margin
    lon_min -= lon_margin
    lon_max += lon_margin

    main_node_set = set(main_route_nodes)

    # Bounding box içindeki kavşak node'larını bul (degree >= 3)
    candidate_nodes = []
    for node, data in G.nodes(data=True):
        lat, lon = data.get('y', 0), data.get('x', 0)
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            if node not in main_node_set:
                degree = G.degree(node)
                if degree >= 3:
                    candidate_nodes.append((node, lat, lon, degree))

    if not candidate_nodes:
        print(f"[RouteEngine] Via-Node: Bounding box'ta kavşak bulunamadı")
        return via_routes

    # Rotanın her ~20. noktasını sample'la (performans için)
    sampled_coords = main_coords[::max(1, len(main_coords) // 20)]

    def min_distance_to_route(lat, lon):
        """Noktanın rotaya olan minimum yaklaşık mesafesi (metre)"""
        min_dist = float('inf')
        cos_lat = math.cos(math.radians(lat))
        for rlat, rlon in sampled_coords:
            dlat = (lat - rlat) * 111000
            dlon = (lon - rlon) * 111000 * cos_lat
            dist = math.sqrt(dlat * dlat + dlon * dlon)
            if dist < min_dist:
                min_dist = dist
        return min_dist

    # Score: uzaklık * log(degree) — hem uzak hem büyük kavşak = ideal via-node
    scored = []
    for node, lat, lon, degree in candidate_nodes:
        dist = min_distance_to_route(lat, lon)
        score = dist * math.log(degree + 1)
        scored.append((node, lat, lon, degree, dist, score))

    scored.sort(key=lambda x: x[5], reverse=True)

    print(f"[RouteEngine] Via-Node: {len(scored)} kavşak aday bulundu")

    max_km = main_km * max_distance_ratio

    for node, lat, lon, degree, dist, score in scored[:30]:
        if len(via_routes) >= num_via_routes:
            break
        try:
            path_a = nx.shortest_path(G, origin_node, node, weight="length")
            path_b = nx.shortest_path(G, node, dest_node, weight="length")
            full_path = path_a + path_b[1:]

            stats = calculate_route_stats(G, full_path)

            # Çok uzun rotaları reddet
            if stats["total_distance_km"] > max_km:
                continue

            new_edges = path_to_edges(G, full_path)

            # Daha önce bulunan via rotalarla çok benzer olmamalı
            too_similar = False
            for existing in via_routes:
                overlap = count_edge_overlap(existing["edges"], new_edges)
                if overlap > 0.70:
                    too_similar = True
                    break

            if too_similar:
                continue

            via_routes.append({
                "nodes": full_path,
                "edges": new_edges,
                "distance_km": stats["total_distance_km"],
                "duration_minutes": stats["estimated_walk_minutes"],
                "via_node": node,
                "source": "via_node"
            })

            print(f"[RouteEngine] ✓ Via-Node #{len(via_routes)}: "
                  f"{stats['total_distance_km']:.2f} km (degree={degree}, uzaklık={dist:.0f}m)")

        except (nx.NetworkXNoPath, Exception):
            continue

    return via_routes


def find_alternative_routes(G, origin_node: int, dest_node: int, num_routes: int = 3) -> list:
    """
    İki nokta arası GERÇEK alternatif rotalar bulur (v3.0 - Via-Node).

    v3.0:
    - Via-Node (Ara Nokta): Endüstri standardı (Google Maps/OSRM tarzı)
    - Asimetrik overlap: "Yeni rotanın % kaçı eskiyle aynı?"
    - Gövde-only penalty: Baş/son %10'a dokunma, sadece gövdeye ceza
    - Telemetry logging ile performans takibi

    Strateji sırası:
    1. En kısa yol (Rota 1 - Dijkstra)
    2. Via-Node (Rota 2, 3 - ana rotadan uzak kavşaklardan geçir)
    3. Penalty yedek (via-node yetmezse, sadece gövde kenarlarına ceza)

    Args:
        G: NetworkX grafiği
        origin_node: Başlangıç düğümü
        dest_node: Hedef düğüm
        num_routes: Kaç alternatif rota isteniyor (varsayılan 3)

    Returns:
        list[dict]: Alternatif rotalar
    """
    telemetry = RouteTelemetry()
    alternatives = []

    if G is None or G.number_of_nodes() == 0:
        print("[RouteEngine] HATA: Boş graf!")
        return []

    if origin_node not in G.nodes() or dest_node not in G.nodes():
        print(f"[RouteEngine] HATA: Node'lar grafte yok: {origin_node}, {dest_node}")
        return []

    try:
        print(f"[ROUTE] Alternatif rota: origin={origin_node}, dest={dest_node}, n={num_routes}")
        print(f"[RouteEngine] ════════════════════════════════════")
        print(f"[RouteEngine] ALTERNATIF ROTALAR v3.0 (Via-Node)")
        print(f"[RouteEngine] Origin: {origin_node} → Dest: {dest_node}")
        print(f"[RouteEngine] ════════════════════════════════════")

        # ============================================================
        # ADIM 1: En kısa rotayı bul (Rota 1)
        # ============================================================
        try:
            shortest_nodes = nx.shortest_path(G, origin_node, dest_node, weight="length")
            shortest_stats = calculate_route_stats(G, shortest_nodes)
            shortest_km = shortest_stats["total_distance_km"]
            print(f"[RouteEngine] ✓ Rota 1 (en kısa): {shortest_km:.2f} km")
        except nx.NetworkXNoPath:
            print("[RouteEngine] HATA: Aralarında yol yok!")
            return get_fallback_routes(G, origin_node, dest_node)

        alternatives.append({
            "type": "route_1",
            "name": "Rota 1",
            "icon": "📍",
            "nodes": shortest_nodes,
            "distance_km": shortest_km,
            "duration_minutes": shortest_stats["estimated_walk_minutes"],
            "description": f"{shortest_km:.1f} km"
        })

        if num_routes <= 1:
            telemetry.unique_routes = 1
            telemetry.generation_method = "shortest_only"
            telemetry.finish()
            return alternatives

        # ============================================================
        # ADIM 2: Via-Node rotaları (ana strateji)
        # ============================================================
        print(f"[RouteEngine] ════════════════════════════════════")
        print(f"[RouteEngine] ADIM 2: Via-Node Rotaları Aranıyor")
        print(f"[RouteEngine] ════════════════════════════════════")

        via_routes = find_via_node_routes(
            G, origin_node, dest_node, shortest_nodes,
            num_via_routes=num_routes - 1,
            max_distance_ratio=1.5
        )

        MAX_OVERLAP = dynamic_overlap_threshold(shortest_km)
        existing_edges_list = [path_to_edges(G, shortest_nodes)]

        if via_routes:
            telemetry.via_node_found = len(via_routes)
            print(f"[RouteEngine] ✓ {len(via_routes)} via-node rota aday bulundu")

            for route in via_routes:
                if len(alternatives) >= num_routes:
                    break

                route_edges = route["edges"]

                ok = True
                for existing_edges in existing_edges_list:
                    overlap = count_edge_overlap(existing_edges, route_edges)
                    telemetry.overlaps.append(overlap)
                    if overlap >= MAX_OVERLAP:
                        print(f"[RouteEngine] ✗ Via-node rota reddedildi (overlap {overlap:.0%} >= {MAX_OVERLAP:.0%})")
                        ok = False
                        break

                if ok:
                    route_num = len(alternatives) + 1
                    alternatives.append({
                        "type": f"route_{route_num}",
                        "name": f"Rota {route_num}",
                        "icon": "📍",
                        "nodes": route["nodes"],
                        "distance_km": route["distance_km"],
                        "duration_minutes": route["duration_minutes"],
                        "description": f"{route['distance_km']:.1f} km"
                    })
                    existing_edges_list.append(route_edges)
                    print(f"[RouteEngine] ✓ Via-node Rota {route_num}: {route['distance_km']:.2f} km")
        else:
            print(f"[RouteEngine] ⚠️  Via-node rota bulunamadı, penalty'ye geçiliyor")

        # ============================================================
        # ADIM 3: Penalty (yedek - gövde-only)
        # ============================================================
        if len(alternatives) < num_routes:
            print(f"[RouteEngine] ════════════════════════════════════")
            print(f"[RouteEngine] ADIM 3: Penalty (Gövde-Only)")
            print(f"[RouteEngine] ════════════════════════════════════")

            # Sadece gövde kenarlarına ceza ver (baş/son %10'a dokunma)
            body_edges = []
            for alt in alternatives:
                edges = path_to_edges(G, alt["nodes"])
                body_edges.extend(get_body_edges(edges, skip_ratio=0.10))

            remaining = num_routes - len(alternatives)
            penalty_routes = find_routes_with_penalty(
                G, origin_node, dest_node,
                used_edges=body_edges,
                num_routes=remaining + 1,
                penalty_factor=ROUTE_CONFIG.get("PENALTY_FACTOR", 2.0)
            )
            telemetry.yen_candidates = len(penalty_routes)

            for route in penalty_routes:
                if len(alternatives) >= num_routes:
                    break

                route_edges = route["edges"]

                ok = True
                for existing_edges in existing_edges_list:
                    overlap = count_edge_overlap(existing_edges, route_edges)
                    telemetry.overlaps.append(overlap)
                    if overlap >= MAX_OVERLAP:
                        ok = False
                        break

                if ok:
                    route_num = len(alternatives) + 1
                    alternatives.append({
                        "type": f"route_{route_num}",
                        "name": f"Rota {route_num}",
                        "icon": "📍",
                        "nodes": route["nodes"],
                        "distance_km": route["distance_km"],
                        "duration_minutes": route["duration_minutes"],
                        "description": f"{route['distance_km']:.1f} km"
                    })
                    existing_edges_list.append(route_edges)
                    print(f"[RouteEngine] ✓ Penalty Rota {route_num}: {route['distance_km']:.2f} km")

        # ============================================================
        # ADIM 4: Sırala ve isimleri ata
        # ============================================================
        alternatives.sort(key=lambda x: x["distance_km"])

        for i, alt in enumerate(alternatives):
            alt["type"] = f"route_{i+1}"
            alt["name"] = f"Rota {i+1}"

        # Telemetry
        telemetry.unique_routes = len(alternatives)
        telemetry.generation_method = "via_node" if telemetry.via_node_found > 0 else "penalty"
        telemetry.finish()

        print(f"[RouteEngine] ════════════════════════════════════")
        print(f"[RouteEngine] ✓ TOPLAM {len(alternatives)} ROTA BULUNDU")
        print(f"[RouteEngine] ════════════════════════════════════")

    except nx.NetworkXNoPath:
        print(f"[RouteEngine] NetworkXNoPath: Yol bulunamadi")
        return get_fallback_routes(G, origin_node, dest_node)

    except nx.NodeNotFound:
        print(f"[RouteEngine] NodeNotFound: Gecersiz node ID")
        return get_fallback_routes(G, origin_node, dest_node)

    except MemoryError:
        print(f"[RouteEngine] MemoryError: Yetersiz hafiza")
        try:
            shortest_nodes = nx.shortest_path(G, origin_node, dest_node, weight="length")
            shortest_stats = calculate_route_stats(G, shortest_nodes)
            return [{
                "type": "route_1", "name": "Rota 1", "icon": "📍",
                "nodes": shortest_nodes,
                "distance_km": shortest_stats["total_distance_km"],
                "duration_minutes": shortest_stats["estimated_walk_minutes"],
                "description": f"{shortest_stats['total_distance_km']:.1f} km"
            }]
        except (KeyError, ValueError, TypeError) as e:
            print(f"[RouteEngine] Fallback rota hesaplama hatası: {e}")
            return []

    except Exception as e:
        print(f"[RouteEngine] KRITIK HATA: {e}")
        import traceback
        traceback.print_exc()
        return get_fallback_routes(G, origin_node, dest_node)

    # Minimum alternatif garantisi
    if len(alternatives) < num_routes and alternatives:
        print(f"[RouteEngine] ⚠️  Sadece {len(alternatives)} rota bulundu")
        while len(alternatives) < num_routes:
            base = alternatives[0].copy()
            route_num = len(alternatives) + 1
            base["type"] = f"route_{route_num}"
            base["name"] = f"Rota {route_num} (Kopya)"
            base["icon"] = "📍"
            base["description"] = f"{base['distance_km']:.1f} km (kopya)"
            base["is_duplicate"] = True
            alternatives.append(base)

    print(f"[ROUTE] {len(alternatives)} alternatif rota bulundu")
    return alternatives


def build_alternative_routes(G, ordered_points: list, route_index: int = 0) -> list:
    """
    Çoklu nokta için alternatif rota stratejisi ile tam rota oluşturur.

    Args:
        G: NetworkX grafiği
        ordered_points: Sıralı [(lat, lon), ...] listesi
        route_index: Hangi rotayı istiyoruz (0=ilk, 1=ikinci, 2=üçüncü)

    Returns:
        list[int]: Düğüm listesi
    """
    full_route_nodes = []

    for i in range(len(ordered_points) - 1):
        origin = find_nearest_node(G, ordered_points[i][0], ordered_points[i][1])
        dest = find_nearest_node(G, ordered_points[i + 1][0], ordered_points[i + 1][1])

        alternatives = find_alternative_routes(G, origin, dest, num_routes=3)

        segment = None
        if route_index < len(alternatives):
            segment = alternatives[route_index]["nodes"]
        elif alternatives:
            segment = alternatives[0]["nodes"]
        else:
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

    Basit sistem:
    - 3 rota döner: "Rota 1", "Rota 2", "Rota 3"
    - Her rota kıya rotaya yakın ama geometrik olarak farklı

    Returns:
        list[dict]: [{"type": "route_1", "name": "Rota 1", "icon": "📍", "nodes": [...], ...}, ...]
    """
    # Her segment için alternatifleri BİR KEZ hesapla
    segment_alternatives = []
    for i in range(len(ordered_points) - 1):
        origin = find_nearest_node(G, ordered_points[i][0], ordered_points[i][1])
        dest = find_nearest_node(G, ordered_points[i + 1][0], ordered_points[i + 1][1])
        print(f"[RouteEngine] [BATCH] Segment {i+1}: {ordered_points[i]} -> {ordered_points[i+1]}")
        alts = find_alternative_routes(G, origin, dest, num_routes=3)
        print(f"[RouteEngine] [BATCH] Segment {i+1} icin {len(alts)} alternatif bulundu")
        segment_alternatives.append(alts)

    # 3 tam rota oluştur (her biri için aynı index'teki segmenti seç)
    results = []
    num_routes = 3

    for route_idx in range(num_routes):
        full_nodes = []
        print(f"[RouteEngine] [BATCH] === Rota {route_idx+1} tam rota olusturuluyor ===")

        for seg_idx, alts in enumerate(segment_alternatives):
            segment = None
            chosen_idx = None

            # Aynı index'teki rotayı seç (0→0, 1→1, 2→2)
            if route_idx < len(alts):
                segment = alts[route_idx]["nodes"]
                chosen_idx = route_idx
            elif alts:
                segment = alts[0]["nodes"]
                chosen_idx = 0
            else:
                # Fallback: shortest path
                origin = find_nearest_node(G, ordered_points[seg_idx][0], ordered_points[seg_idx][1])
                dest = find_nearest_node(G, ordered_points[seg_idx + 1][0], ordered_points[seg_idx + 1][1])
                segment = shortest_path(G, origin, dest)
                chosen_idx = "fallback"

            if segment:
                if seg_idx == 0:
                    full_nodes.extend(segment)
                else:
                    full_nodes.extend(segment[1:])
                print(f"[RouteEngine] [BATCH] Segment {seg_idx+1} icin secilen rota: {chosen_idx}, uzunluk={len(segment)}")

        if full_nodes:
            stats = calculate_route_stats(G, full_nodes)
            route_num = route_idx + 1
            print(f"[RouteEngine] [BATCH] Rota {route_num}: {stats['total_distance_km']} km, {stats['estimated_walk_minutes']} dk")
            results.append({
                "type": f"route_{route_num}",
                "name": f"Rota {route_num}",
                "icon": "📍",
                "nodes": full_nodes,
                "distance_km": stats["total_distance_km"],
                "duration_minutes": stats["estimated_walk_minutes"],
                "description": f"{stats['total_distance_km']:.1f} km"
            })

    return results
