"""
graph_manager.py - OSMnx ile harita verisi yönetimi

Harita verilerini OpenStreetMap'ten indirir, .graphml olarak cache'ler,
ve POI (Points of Interest) aramalarını gerçekleştirir.
"""

import os
import osmnx as ox
import networkx as nx

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
    
    Args:
        place_name: OSM yer adı (ör: "Kadikoy, Istanbul, Turkey")
    
    Returns:
        networkx.MultiDiGraph: Yürüyüş grafiği
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


def find_nearest_node(G, lat: float, lon: float) -> int:
    """
    Verilen koordinata (lat, lon) en yakın graf düğümünü bulur.
    
    Args:
        G: NetworkX grafiği
        lat: Enlem
        lon: Boylam
    
    Returns:
        int: En yakın düğüm ID'si
    """
    nearest = ox.nearest_nodes(G, X=lon, Y=lat)
    return nearest


def search_pois(place_name: str, category: str) -> list:
    """
    Belirtilen bölgede POI (Points of Interest) arar.
    
    Args:
        place_name: Bölge adı
        category: Kategori ('museum', 'cafe', 'park', 'restaurant')
    
    Returns:
        list of dict: [{"name": "...", "lat": ..., "lon": ...}, ...]
    """
    # OSM etiketleri
    tag_map = {
        "museum":     {"tourism": "museum"},
        "cafe":       {"amenity": "cafe"},
        "park":       {"leisure": "park"},
        "restaurant": {"amenity": "restaurant"},
        "library":    {"amenity": "library"},
        "mosque":     {"amenity": "place_of_worship", "religion": "muslim"},
        "hotel":      {"tourism": "hotel"},
    }

    tags = tag_map.get(category, {"tourism": category})

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
        except Exception:
            continue

    print(f"[GraphManager] {place_name} bölgesinde {len(pois)} adet '{category}' bulundu.")
    return pois
