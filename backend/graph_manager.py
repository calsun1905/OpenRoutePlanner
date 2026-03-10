"""
graph_manager.py - OSMnx ile harita verisi yönetimi

Harita verilerini OpenStreetMap'ten indirir, .graphml olarak cache'ler,
ve POI (Points of Interest) aramalarını gerçekleştirir.
"""

import os
import osmnx as ox
import networkx as nx
from route_config import ROUTE_CONFIG

# Cache dizini
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def _cache_path(place_name: str) -> str:
    """Verilen yer adı için cache dosya yolunu döner."""
    safe_name = place_name.replace(",", "").replace(" ", "_").lower()
    return os.path.join(DATA_DIR, f"{safe_name}.graphml")


def get_graph(place_name: str = "Kadikoy, Istanbul, Turkey"):
    """
    Belirtilen bölgenin yürüyüş grafiğini döner.
    İlk çağrıda internetten indirir ve .graphml olarak cache'ler.
    Sonraki çağrılarda dosyadan okur (çok daha hızlı).
    """
    cache_file = _cache_path(place_name)

    if os.path.exists(cache_file):
        print(f"[GraphManager] Cache'den okunuyor: {cache_file}")
        G = ox.load_graphml(cache_file)
    else:
        print(f"[GraphManager] OSM'den indiriliyor: {place_name}")
        G = ox.graph_from_place(place_name, network_type="walk")
        ox.save_graphml(G, cache_file)
        print(f"[GraphManager] Cache'e kaydedildi: {cache_file}")

    return G


def get_graph_for_points(points: list):
    """
    Seçilen noktaların merkezinden, tüm noktaları kapsayacak
    yarıçapla graf indirir. graph_from_point kullanır (bbox'tan çok daha hızlı).
    
    Args:
        points: [(lat, lon), ...] koordinat listesi
    
    Returns:
        networkx.MultiDiGraph: Yürüyüş grafiği
    """
    import math
    
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    
    # Merkez noktayı hesapla
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)
    
    # En uzak noktaya olan mesafeyi hesapla (metre cinsinden)
    max_dist = 0
    for lat, lon in points:
        # Haversine yaklaşımı (basit)
        dlat = math.radians(lat - center_lat)
        dlon = math.radians(lon - center_lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(center_lat)) * math.cos(math.radians(lat)) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        dist = 6371000 * c  # metre
        if dist > max_dist:
            max_dist = dist
    
    min_radius = ROUTE_CONFIG.get("GRAPH_RADIUS_MIN_M", 500)
    padding = ROUTE_CONFIG.get("GRAPH_RADIUS_PADDING_M", 300)
    max_radius = ROUTE_CONFIG.get("GRAPH_RADIUS_MAX_M", 3500)

    # Minimum yarıçap + padding uygula. Maksimum değeri config yönetir.
    radius = min(max_radius, max(min_radius, max_dist + padding))
    
    # Cache key: merkez + yarıçap
    cache_key = f"point_{center_lat:.4f}_{center_lon:.4f}_{int(radius)}"
    cache_file = os.path.join(DATA_DIR, f"{cache_key}.graphml")
    
    if os.path.exists(cache_file):
        print(f"[GraphManager] Cache'den okunuyor: {cache_file}")
        G = ox.load_graphml(cache_file)
    else:
        print(f"[GraphManager] Graf indiriliyor: merkez=({center_lat:.4f}, {center_lon:.4f}), yarıçap={int(radius)}m")
        G = ox.graph_from_point((center_lat, center_lon), dist=radius, network_type="walk")
        ox.save_graphml(G, cache_file)
        print(f"[GraphManager] Cache'e kaydedildi: {cache_file}")
    
    return G


def find_nearest_node(G, lat: float, lon: float) -> int:
    """
    Verilen koordinata (lat, lon) en yakın graf düğümünü bulur.
    
    nearest_edges kullanarak en yakın yol kenarını bulur, sonra
    o kenarın uç noktalarından kullanıcıya en yakın olanı seçer.
    Bu sayede ana caddeye değil, gerçekten en yakın sokağa snap edilir.
    
    Args:
        G: NetworkX grafiği
        lat: Enlem
        lon: Boylam
    
    Returns:
        int: En yakın düğüm ID'si
    """
    try:
        # En yakın yol kenarını bul (u, v, key)
        u, v, _ = ox.nearest_edges(G, X=lon, Y=lat)
        
        # Kenarın iki uç noktasından kullanıcıya en yakın olanı seç
        u_data = G.nodes[u]
        v_data = G.nodes[v]

        dist_u = ((u_data["y"] - lat) ** 2 + (u_data["x"] - lon) ** 2)
        dist_v = ((v_data["y"] - lat) ** 2 + (v_data["x"] - lon) ** 2)

        return u if dist_u <= dist_v else v
    except Exception as e:
        # Fallback: nearest_nodes kullan
        print(f"[GraphManager] Manuel nearest node hatası, fallback kullanılıyor: {e}")
        return ox.nearest_nodes(G, X=lon, Y=lat)


def search_pois(place_name: str, category: str) -> list:
    """
    Belirtilen bölgede POI (Points of Interest) arar.

    Args:
        place_name: Bölge adı
        category: Kategori ('museum', 'cafe', 'park', 'restaurant')

    Returns:
        list of dict: [{"name": "...", "lat": ..., "lon": ...}, ...]
    """
    print(f"[POI] Arama baslatildi: {place_name}, kategori={category}")

    from osm_poi_dictionary import POI_MAPPING

    category = category.lower().strip()

    # Eğer category sözlükte varsa onun tag'ini kullan, yoksa tourism veya amenity varsay
    if category in POI_MAPPING:
        tags = POI_MAPPING[category]
    else:
        tags = {"tourism": category} # Fallback

    try:
        gdf = ox.features_from_place(place_name, tags=tags)
    except Exception as e:
        print(f"[GraphManager] POI arama hatası: {e}")
        return []

    pois = []
    for _, row in gdf.iterrows():
        # Geometriden merkez koordinatı al
        try:
            centroid = row.geometry.centroid
            name = row.get("name", "İsimsiz")
            if name is None or (hasattr(name, '__len__') and len(str(name)) == 0):
                name = "İsimsiz"

            # Ek bilgileri OSM verisinden al
            website = row.get("website", "") or ""
            wikipedia = row.get("wikipedia", "") or ""
            opening_hours = row.get("opening_hours", "") or ""
            description = row.get("description", "") or ""
            image = row.get("image", "") or ""

            # Wikipedia linkini oluştur
            wiki_url = ""
            if wikipedia and isinstance(wikipedia, str) and ":" in wikipedia:
                lang, title = wikipedia.split(":", 1)
                wiki_url = f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"

            poi_data = {
                "name": str(name),
                "lat": centroid.y,
                "lon": centroid.x,
                "category": category,
                "website": str(website) if website else "",
                "wikipedia_url": wiki_url,
                "opening_hours": str(opening_hours) if opening_hours else "",
                "description": str(description) if description else "",
                "image": str(image) if image else "",
            }
            pois.append(poi_data)
        except Exception as e:
            # Tek bir POI'nin hatası tüm aramayı bozmasın
            print(f"[POI] POI verisi hatası (atlanıyor): {e}")
            continue

    print(f"[POI] {len(pois)} POI bulundu: {place_name} ({category})")
    return pois


# =============================================================================
# GRAPH PRELOADING - Popüler bölgeler için hızlı erişim
# =============================================================================

# Popüler bölgeler (Türkiye'nin en çok kullanılan bölgeleri)
# Uygulama başladığında bu bölgelerin grafileri ön yüklenir
POPULAR_REGIONS = [
    "Kadikoy, Istanbul, Turkey",
    "Besiktas, Istanbul, Turkey",
    "Taksim, Istanbul, Turkey",
    "Sisli, Istanbul, Turkey",
    "Uskudar, Istanbul, Turkey",
    "Maslak, Istanbul, Turkey",
    "Levent, Istanbul, Turkey",
]

_preloaded_graphs = {}


def preload_popular_regions():
    """
    Popüler bölgelerin grafilerini ön yükler.
    Uygulama başlangıcında çağrılmalıdır.
    İlk rota hesaplamalarını %80 daha hızlı yapar.
    """
    import threading

    def _preload_region(place_name):
        try:
            print(f"[GraphPreload] Ön yükleniyor: {place_name}")
            G = get_graph(place_name)
            _preloaded_graphs[place_name] = G

            # LRU cache'e de ekle (preload önceliği yüksek)
            from cache_manager import get_graph_cache
            cache = get_graph_cache()
            cache.put(place_name, G, preloaded=True)

            print(f"[GraphPreload] Yüklendi: {place_name}")
        except Exception as e:
            print(f"[GraphPreload] Hata {place_name}: {e}")

    # Paralel yüklemeyi başlat
    threads = []
    for region in POPULAR_REGIONS:
        t = threading.Thread(target=_preload_region, args=(region,))
        t.start()
        threads.append(t)

    # Tüm thread'lerin tamamlanmasını bekle
    for t in threads:
        t.join()

    print(f"[GraphPreload] {len(_preloaded_graphs)} bölge ön yüklendi")


def is_preloaded(place_name: str) -> bool:
    """
    Belirtilen bölgenin grafiklerinin önceden yüklenip yüklenmediğini kontrol eder.
    """
    return place_name in _preloaded_graphs


def get_preloaded_graph(place_name: str):
    """
    Önceden yüklenmiş grafı döner. Varsa cache'ten alır, yoksa None döner.
    """
    return _preloaded_graphs.get(place_name)
