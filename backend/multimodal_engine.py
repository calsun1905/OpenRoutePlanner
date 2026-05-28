"""
multimodal_engine.py - Multimodal Rota Planlama Motoru

Yuruyus ve toplu tasima seceneklerini karsilastirarak
en iyi rotayi olusturur.

Algoritmalar:
- Yakin durak bulma (Haversine + bounding box)
- Ortak hat arama (SQLite join)
- Seyahat suresi hesaplama
- Yuruyus vs toplu tasima karsilastirmasi
"""

import math
import re
import copy
import requests
import time as _time
import heapq
from collections import defaultdict
from typing import Any, List, Dict, Optional, Tuple

from ibb_transit import (
    get_stops_in_area,
    find_connecting_routes,
    get_route_info,
    get_metro_stations_in_area,
    get_metro_lines_for_station,
    get_metro_line_stations,
    _haversine_distance,
    _get_db_connection,
)

from gtfs_shapes import get_metro_line_shape
from route_config import ROUTE_CONFIG


# ============================================================================
# SABITLER
# ============================================================================

# Yurume hizi: 5 km/s -> 83.3 m/dk
WALKING_SPEED_M_PER_MIN = 83.3

# Ortalama otobus bekleme suresi (dakika)
AVG_BUS_WAIT_MIN = 5

# Ortalama otobus hizi (trafik dahil, km/s)
AVG_BUS_SPEED_KMH = 18
AVG_METRO_SPEED_KMH = 34

# Maksimum yurume mesafesi duraga (metre)
MAX_WALK_TO_STOP_M = float(ROUTE_CONFIG.get("MULTIMODAL_MAX_WALK_TO_STOP_M", 800))
MAX_RAIL_TRANSFER_WALK_M = float(ROUTE_CONFIG.get("MULTIMODAL_MAX_RAIL_TRANSFER_WALK_M", 1500))

# Arama yaricaplari (dar -> genis)
SEARCH_RADII = [600, 1000, 1500]

# OSRM public API
OSRM_BASE_URL = "http://router.project-osrm.org"
_OSRM_ROUTE_CACHE: Dict[Tuple, List[List[float]]] = {}
_OSRM_MULTI_CACHE: Dict[Tuple, List[List[float]]] = {}
_OSRM_CACHE_MAX_ITEMS = 800
_COMPARE_ROUTE_CACHE: Dict[Tuple, Tuple[float, Dict]] = {}
_COMPARE_CACHE_MAX_ITEMS = int(ROUTE_CONFIG.get("MULTIMODAL_COMPARE_CACHE_MAX_ITEMS", 220))
_ENABLE_COMPARE_CACHE = bool(ROUTE_CONFIG.get("MULTIMODAL_COMPARE_CACHE_ENABLED", False))
_COMPARE_CACHE_TTL_SEC = float(ROUTE_CONFIG.get("MULTIMODAL_COMPARE_CACHE_TTL_SEC", 300))
_COMPARE_CACHE_HITS = 0
_COMPARE_CACHE_MISSES = 0
_TRANSIT_LOOKUP_CACHE: Dict[Tuple, Tuple[float, Any]] = {}
_TRANSIT_LOOKUP_CACHE_MAX_ITEMS = int(ROUTE_CONFIG.get("MULTIMODAL_TRANSIT_LOOKUP_CACHE_MAX_ITEMS", 2500))
_TRANSIT_LOOKUP_CACHE_TTL_SEC = float(ROUTE_CONFIG.get("MULTIMODAL_TRANSIT_LOOKUP_CACHE_TTL_SEC", 900))
_TRANSIT_LOOKUP_CACHE_HITS = 0
_TRANSIT_LOOKUP_CACHE_MISSES = 0


def _effective_walk_to_stop_limit_m(direct_walk_m: float) -> float:
    """
    Ilk/son duraga yurume limitini mesafeye gore dinamiklestirir.
    Kisa rotalarda default limit korunur; uzun rotalarda limit biraz esner.
    """
    base = float(ROUTE_CONFIG.get("MULTIMODAL_MAX_WALK_TO_STOP_M", MAX_WALK_TO_STOP_M))
    medium = float(ROUTE_CONFIG.get("MULTIMODAL_MAX_WALK_TO_STOP_MEDIUM_M", 1000))
    long_ = float(ROUTE_CONFIG.get("MULTIMODAL_MAX_WALK_TO_STOP_LONG_M", 1200))
    medium_trigger = float(ROUTE_CONFIG.get("MULTIMODAL_WALK_EXPAND_MEDIUM_TRIGGER_M", 20000))
    long_trigger = float(ROUTE_CONFIG.get("MULTIMODAL_WALK_EXPAND_LONG_TRIGGER_M", 50000))

    try:
        walk_m = float(direct_walk_m)
    except (TypeError, ValueError):
        walk_m = 0.0

    limit = base
    if walk_m >= long_trigger:
        limit = max(limit, long_)
    elif walk_m >= medium_trigger:
        limit = max(limit, medium)
    return float(limit)


def _cache_get(cache: Dict[Tuple, List[List[float]]], key: Tuple) -> Optional[List[List[float]]]:
    v = cache.get(key)
    if v is None:
        return None
    return [list(c) for c in v]


def _cache_put(cache: Dict[Tuple, List[List[float]]], key: Tuple, value: List[List[float]]) -> None:
    if not value:
        return
    if len(cache) >= _OSRM_CACHE_MAX_ITEMS:
        # FIFO-benzeri basit tahliye
        try:
            first_key = next(iter(cache))
            cache.pop(first_key, None)
        except Exception:
            cache.clear()
    cache[key] = [list(c) for c in value]


def _ttl_cache_get(cache: Dict[Tuple, Tuple[float, Any]], key: Tuple, ttl_sec: float) -> Optional[Any]:
    if ttl_sec <= 0:
        return None
    item = cache.get(key)
    if item is None:
        return None
    created_at, value = item
    if (_time.time() - created_at) > ttl_sec:
        cache.pop(key, None)
        return None
    return copy.deepcopy(value)


def _ttl_cache_put(cache: Dict[Tuple, Tuple[float, Any]], key: Tuple, value: Any, max_items: int) -> None:
    if max_items <= 0:
        return
    if len(cache) >= max_items:
        try:
            first_key = next(iter(cache))
            cache.pop(first_key, None)
        except Exception:
            cache.clear()
    cache[key] = (_time.time(), copy.deepcopy(value))


def _compare_cache_get(key: Tuple) -> Optional[Dict]:
    global _COMPARE_CACHE_HITS, _COMPARE_CACHE_MISSES
    if not _ENABLE_COMPARE_CACHE:
        return None
    data = _ttl_cache_get(_COMPARE_ROUTE_CACHE, key, _COMPARE_CACHE_TTL_SEC)
    if data is None:
        _COMPARE_CACHE_MISSES += 1
        return None
    _COMPARE_CACHE_HITS += 1
    return data


def _compare_cache_put(key: Tuple, value: Dict) -> None:
    if not _ENABLE_COMPARE_CACHE:
        return
    _ttl_cache_put(_COMPARE_ROUTE_CACHE, key, value, _COMPARE_CACHE_MAX_ITEMS)


def _lookup_cache_get(key: Tuple) -> Optional[Any]:
    global _TRANSIT_LOOKUP_CACHE_HITS, _TRANSIT_LOOKUP_CACHE_MISSES
    data = _ttl_cache_get(_TRANSIT_LOOKUP_CACHE, key, _TRANSIT_LOOKUP_CACHE_TTL_SEC)
    if data is None:
        _TRANSIT_LOOKUP_CACHE_MISSES += 1
        return None
    _TRANSIT_LOOKUP_CACHE_HITS += 1
    return data


def _lookup_cache_put(key: Tuple, value: Any) -> None:
    _ttl_cache_put(_TRANSIT_LOOKUP_CACHE, key, value, _TRANSIT_LOOKUP_CACHE_MAX_ITEMS)


def get_compare_cache_stats() -> Dict[str, object]:
    total = _COMPARE_CACHE_HITS + _COMPARE_CACHE_MISSES
    hit_rate = (_COMPARE_CACHE_HITS / total) if total > 0 else 0.0
    return {
        "enabled": bool(_ENABLE_COMPARE_CACHE),
        "size": len(_COMPARE_ROUTE_CACHE),
        "max_items": int(_COMPARE_CACHE_MAX_ITEMS),
        "ttl_sec": float(_COMPARE_CACHE_TTL_SEC),
        "hits": int(_COMPARE_CACHE_HITS),
        "misses": int(_COMPARE_CACHE_MISSES),
        "hit_rate": f"{hit_rate:.1%}",
    }


def get_transit_lookup_cache_stats() -> Dict[str, object]:
    total = _TRANSIT_LOOKUP_CACHE_HITS + _TRANSIT_LOOKUP_CACHE_MISSES
    hit_rate = (_TRANSIT_LOOKUP_CACHE_HITS / total) if total > 0 else 0.0
    return {
        "enabled": _TRANSIT_LOOKUP_CACHE_MAX_ITEMS > 0 and _TRANSIT_LOOKUP_CACHE_TTL_SEC > 0,
        "size": len(_TRANSIT_LOOKUP_CACHE),
        "max_items": int(_TRANSIT_LOOKUP_CACHE_MAX_ITEMS),
        "ttl_sec": float(_TRANSIT_LOOKUP_CACHE_TTL_SEC),
        "hits": int(_TRANSIT_LOOKUP_CACHE_HITS),
        "misses": int(_TRANSIT_LOOKUP_CACHE_MISSES),
        "hit_rate": f"{hit_rate:.1%}",
    }


def _cached_get_stops_in_area(lat: float, lon: float, radius: float) -> List[Dict]:
    key = ("stops_area", id(get_stops_in_area), float(lat), float(lon), float(radius))
    cached = _lookup_cache_get(key)
    if cached is not None:
        return cached
    data = get_stops_in_area(lat, lon, radius)
    _lookup_cache_put(key, data)
    return copy.deepcopy(data)


def _cached_find_connecting_routes(stop_a: int, stop_b: int) -> List[Dict]:
    key = ("connecting_routes", id(find_connecting_routes), int(stop_a), int(stop_b))
    cached = _lookup_cache_get(key)
    if cached is not None:
        return cached
    data = find_connecting_routes(stop_a, stop_b)
    _lookup_cache_put(key, data)
    return copy.deepcopy(data)


def _cached_get_route_info(route_code: str) -> Optional[Dict]:
    key = ("route_info", id(get_route_info), str(route_code))
    cached = _lookup_cache_get(key)
    if cached is not None:
        return cached
    data = get_route_info(route_code)
    if data is not None:
        _lookup_cache_put(key, data)
    return copy.deepcopy(data)


def _cached_get_metro_stations_in_area(lat: float, lon: float, radius: float) -> List[Dict]:
    key = ("metro_stations_area", id(get_metro_stations_in_area), float(lat), float(lon), float(radius))
    cached = _lookup_cache_get(key)
    if cached is not None:
        return cached
    data = get_metro_stations_in_area(lat, lon, radius)
    _lookup_cache_put(key, data)
    return copy.deepcopy(data)


def _cached_get_metro_lines_for_station(station_id: int) -> List[Dict]:
    key = ("metro_lines_for_station", id(get_metro_lines_for_station), int(station_id))
    cached = _lookup_cache_get(key)
    if cached is not None:
        return cached
    data = get_metro_lines_for_station(station_id)
    _lookup_cache_put(key, data)
    return copy.deepcopy(data)


def _cached_get_metro_line_stations(line_id: int) -> List[Dict]:
    key = ("metro_line_stations", id(get_metro_line_stations), int(line_id))
    cached = _lookup_cache_get(key)
    if cached is not None:
        return cached
    data = get_metro_line_stations(line_id)
    _lookup_cache_put(key, data)
    return copy.deepcopy(data)


# ============================================================================
# OSRM ROAD-LEVEL ROUTING
# ============================================================================

def _osrm_route_coords(from_lat: float, from_lon: float,
                        to_lat: float, to_lon: float,
                        mode: str = "driving") -> List[List[float]]:
    """
    OSRM API ile iki nokta arasi yol koordinatlarini dondurur.
    Google Maps gibi yol takip eden polyline olusturur.

    Args:
        mode: "driving" veya "foot"

    Returns:
        [[lat, lon], ...] - yol uzerinden koordinatlar
    """
    key = (
        "route", str(mode),
        round(float(from_lat), 6), round(float(from_lon), 6),
        round(float(to_lat), 6), round(float(to_lon), 6),
    )
    cached = _cache_get(_OSRM_ROUTE_CACHE, key)
    if cached is not None:
        return cached

    try:
        url = f"{OSRM_BASE_URL}/route/v1/{mode}/{from_lon},{from_lat};{to_lon},{to_lat}"
        params = {"overview": "full", "geometries": "geojson"}
        r = requests.get(url, params=params, timeout=8)

        if r.status_code != 200:
            fallback = [[from_lat, from_lon], [to_lat, to_lon]]
            _cache_put(_OSRM_ROUTE_CACHE, key, fallback)
            return fallback

        data = r.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            fallback = [[from_lat, from_lon], [to_lat, to_lon]]
            _cache_put(_OSRM_ROUTE_CACHE, key, fallback)
            return fallback

        # GeoJSON format: [lon, lat] -> [lat, lon] cevir
        coords = data["routes"][0]["geometry"]["coordinates"]
        out = [[c[1], c[0]] for c in coords]
        _cache_put(_OSRM_ROUTE_CACHE, key, out)
        return out

    except Exception:
        fallback = [[from_lat, from_lon], [to_lat, to_lon]]
        _cache_put(_OSRM_ROUTE_CACHE, key, fallback)
        return fallback


def _get_bus_road_coords(stop_coords: List[List[float]]) -> List[List[float]]:
    """
    Otobus duraklari arasindaki yol koordinatlarini OSRM ile hesaplar.
    Ardiksik her iki durak icin OSRM driving sorgusu yapar ve
    sonuclari birlestirerek gercek yol takip eden polyline olusturur.

    Cok fazla durak varsa, her 3-4 duragi bir OSRM waypoint olarak gonderir
    (daha az API cagirisi).

    Args:
        stop_coords: [[lat, lon], ...] - durak koordinatlari sirali

    Returns:
        [[lat, lon], ...] - yol uzerinden koordinatlar
    """
    if len(stop_coords) < 2:
        return stop_coords

    def _sample_waypoints(coords: List[List[float]], max_waypoints: int = 20) -> List[List[float]]:
        if len(coords) <= max_waypoints:
            return coords
        # OSRM'e tum duraklari dayatmak bazen sacma zigzag uretir.
        # Bu nedenle esit aralikli ornekleyip ilk/son duragi koruyoruz.
        sampled = [coords[0]]
        step = max(1, int((len(coords) - 2) / max(1, (max_waypoints - 2))))
        idx = step
        while idx < len(coords) - 1 and len(sampled) < (max_waypoints - 1):
            sampled.append(coords[idx])
            idx += step
        sampled.append(coords[-1])
        return sampled

    stop_path_dist = _path_distance_m(stop_coords)

    if len(stop_coords) <= 25:
        query_coords = _sample_waypoints(stop_coords, max_waypoints=20)
        road_coords = _osrm_multi_waypoint(query_coords)
    else:
        all_coords = []
        for i in range(0, len(stop_coords), 19):
            chunk = stop_coords[i:i + 20]
            if len(chunk) < 2:
                all_coords.extend(chunk)
                continue
            query_chunk = _sample_waypoints(chunk, max_waypoints=16)
            road_chunk = _osrm_multi_waypoint(query_chunk)
            if all_coords and road_chunk:
                road_chunk = road_chunk[1:]  # Overlap noktasini atla
            all_coords.extend(road_chunk)
        road_coords = all_coords if len(all_coords) >= 2 else stop_coords

    road_dist = _path_distance_m(road_coords)
    # Google Maps benzeri, asiri sapmayan bir cizim icin kalite kontrolu.
    # OSRM detour'u cok buyukse veya cok kucukse durak polyline'ina geri don.
    if stop_path_dist > 0:
        if road_dist > (stop_path_dist * 1.85) or road_dist < (stop_path_dist * 0.55):
            return stop_coords

    return road_coords if len(road_coords) >= 2 else stop_coords


def _osrm_multi_waypoint(coords: List[List[float]]) -> List[List[float]]:
    """
    Birden fazla waypoint ile OSRM sorgusu yapar.
    Tum duraklarin uzerinden gecen tek bir rota dondurur.
    """
    if len(coords) < 2:
        return coords

    compact = tuple((round(float(c[0]), 6), round(float(c[1]), 6)) for c in coords)
    key = ("multi", compact)
    cached = _cache_get(_OSRM_MULTI_CACHE, key)
    if cached is not None:
        return cached

    try:
        # OSRM format: lon1,lat1;lon2,lat2;...
        waypoints = ";".join([f"{c[1]},{c[0]}" for c in coords])
        url = f"{OSRM_BASE_URL}/route/v1/driving/{waypoints}"
        params = {"overview": "full", "geometries": "geojson"}

        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            _cache_put(_OSRM_MULTI_CACHE, key, coords)
            return coords

        data = r.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            _cache_put(_OSRM_MULTI_CACHE, key, coords)
            return coords

        geojson_coords = data["routes"][0]["geometry"]["coordinates"]
        out = [[c[1], c[0]] for c in geojson_coords]
        _cache_put(_OSRM_MULTI_CACHE, key, out)
        return out

    except Exception:
        _cache_put(_OSRM_MULTI_CACHE, key, coords)
        return coords


def _get_walk_road_coords(from_lat: float, from_lon: float,
                           to_lat: float, to_lon: float) -> List[List[float]]:
    """Yurume guzergahini OSRM foot routing ile hesaplar."""
    return _osrm_route_coords(from_lat, from_lon, to_lat, to_lon, mode="foot")


# ============================================================================
# YARDIMCI FONKSIYONLAR
# ============================================================================

def _walking_time_minutes(distance_m: float) -> float:
    """Yurume suresi (dakika)."""
    return round(distance_m / WALKING_SPEED_M_PER_MIN, 1)


def _bus_travel_time_minutes(distance_km: float) -> float:
    """Otobus seyahat suresi (dakika)."""
    if distance_km <= 0:
        return 0
    return round((distance_km / AVG_BUS_SPEED_KMH) * 60, 1)


def _metro_travel_time_minutes(distance_km: float) -> float:
    """Metro/tram/funikuler ortalama sure (dakika)."""
    if distance_km <= 0:
        return 0
    return round((distance_km / AVG_METRO_SPEED_KMH) * 60, 1)


def _ferry_travel_time_minutes(distance_km: float) -> float:
    """Vapur ortalama sure (dakika)."""
    if distance_km <= 0:
        return 0
    # Ortalama 22 km/s + minimum operasyon suresi
    return round(max(6.0, (distance_km / 22.0) * 60), 1)


FERRY_TERMINAL_LINKS = [
    ("uskudar", "kabatas"),
    ("uskudar", "besiktas"),
    ("kadikoy", "besiktas"),
    ("kadikoy", "kabatas"),
    ("kadikoy", "eminonu"),
    ("uskudar", "eminonu"),
    ("karakoy", "kadikoy"),
    # Halic hatti senaryolari (Sutluce/Feshane -> Kadikoy dogrudan vapur)
    ("feshane", "kadikoy"),
]

FERRY_TERMINAL_SET = set()
for _a, _b in FERRY_TERMINAL_LINKS:
    FERRY_TERMINAL_SET.add(_a)
    FERRY_TERMINAL_SET.add(_b)

FERRY_TERMINAL_ALIASES = {
    "kadikoy ido": "kadikoy",
    "eyup": "feshane",
    "eyupsultan": "feshane",
    "sutluce": "feshane",
}

FERRY_TERMINAL_DISPLAY = {
    "uskudar": "Uskudar",
    "kabatas": "Kabatas",
    "besiktas": "Besiktas",
    "kadikoy": "Kadikoy",
    "eminonu": "Eminonu",
    "karakoy": "Karakoy",
    # Veride tek istasyon "Feshane" oldugu icin kullaniciya acik isim goster.
    "feshane": "Feshane / Sutluce",
}


def _ferry_display_name(raw_name: str) -> str:
    name = str(raw_name or "").strip()
    if not name:
        return "Iskele"
    norm = _normalized_station_name(name)
    canonical = FERRY_TERMINAL_ALIASES.get(norm, norm)
    return FERRY_TERMINAL_DISPLAY.get(canonical, name)

USER_TRANSIT_MODES = {"bus", "metro", "metrobus", "ferry"}
DEFAULT_TRANSFER_MAX_M = 220.0
EXTENDED_TRANSFER_NAMES = {
    "yenikapi",
    "aksaray",
    "eminonu",
    "kabatas",
    "levent",
}
HALIC_WALK_BRIDGE_CHECKPOINTS = [
    # Ataturk (Unkapani) Koprusu
    (41.0209, 28.9648),
    # Halic Metro Koprusu
    (41.0257, 28.9691),
    # Galata Koprusu
    (41.0222, 28.9734),
]
ALIBEY_WALK_BRIDGE_CHECKPOINTS = [
    # Miniaturk/Sutluce gecisleri
    (41.0584, 28.9497),
    # Sunnet Koprusu
    (41.0637, 28.9505),
    # Fil Koprusu
    (41.0696, 28.9424),
]


def _transfer_max_distance_for_name(norm_name: str) -> float:
    """
    Ayni adli istasyonlar arasinda transfer icin mesafe limiti.
    Bazi buyuk hub'larda biraz daha genis limit taninir.
    """
    return 420.0 if norm_name in EXTENDED_TRANSFER_NAMES else DEFAULT_TRANSFER_MAX_M


def _bosphorus_side(lon: float) -> int:
    """
    Bogaz icin kaba taraf tespiti:
    -1: Avrupa, +1: Anadolu, 0: gri bolge.
    """
    if lon <= 29.010:
        return -1
    if lon >= 29.014:
        return 1
    return 0


def _is_forbidden_bosphorus_walk(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
) -> bool:
    """
    Istanbul iki yaka arasi yuruyus (Bogaz gecisi) fiilen mumkun degil.
    Bu nedenle bu tip yaya segmentlerini dogrudan reddederiz.

    ROUTE_CONFIG["MULTIMODAL_ENFORCE_WATER_CROSSING_GUARDS"] = False ise
    bu koruma devre disi birakilir (test amacli veya ozel durumlar icin).
    """
    if not ROUTE_CONFIG.get("MULTIMODAL_ENFORCE_WATER_CROSSING_GUARDS", True):
        return False

    lat_min = min(from_lat, to_lat)
    lat_max = max(from_lat, to_lat)
    if lat_max < 40.90 or lat_min > 41.28:
        return False

    side_a = _bosphorus_side(from_lon)
    side_b = _bosphorus_side(to_lon)
    return side_a != 0 and side_b != 0 and side_a != side_b


def _is_likely_halic_straight_cross(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
) -> bool:
    """
    Halic uzerinden duz-cizgi fallback gecisi (genelde OSRM fallback artefakti).
    Gercek yurume varsa OSRM yol dondurur; fallback duz cizgi ise reddedelim.
    """
    if not (
        28.93 <= from_lon <= 28.995 and 28.93 <= to_lon <= 28.995
        and 41.015 <= from_lat <= 41.065 and 41.015 <= to_lat <= 41.065
    ):
        return False
    return (from_lat < 41.03 and to_lat > 41.04) or (to_lat < 41.03 and from_lat > 41.04)


def _is_major_water_crossing_straight(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
) -> bool:
    if _is_forbidden_bosphorus_walk(from_lat, from_lon, to_lat, to_lon):
        return True
    if _is_likely_halic_straight_cross(from_lat, from_lon, to_lat, to_lon):
        return True
    if _is_likely_alibey_crossing(from_lat, from_lon, to_lat, to_lon):
        return True
    return False


def _is_likely_halic_crossing(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
) -> bool:
    """
    Halic etrafinda iki bank arasi gecis olasiligi.
    """
    in_bbox = (
        28.93 <= from_lon <= 28.995 and 28.93 <= to_lon <= 28.995
        and 41.015 <= from_lat <= 41.070 and 41.015 <= to_lat <= 41.070
    )
    if not in_bbox:
        return False
    # Cok lokal ayni-yaka hareketleri disla.
    if abs(from_lat - to_lat) < 0.006 and abs(from_lon - to_lon) < 0.006:
        return False
    # Bank farki heuristigi.
    return (
        (from_lat < 41.031 <= to_lat)
        or (to_lat < 41.031 <= from_lat)
        or abs(from_lon - to_lon) >= 0.012
    )


def _is_likely_alibey_crossing(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
) -> bool:
    """
    Halic'in kuzey kolu (Alibeykoy deresi) uzerinde bank degisimi.
    """
    in_bbox = (
        28.939 <= from_lon <= 28.954 and 28.939 <= to_lon <= 28.954
        and 41.051 <= from_lat <= 41.072 and 41.051 <= to_lat <= 41.072
    )
    if not in_bbox:
        return False
    if abs(from_lon - to_lon) < 0.0023:
        return False
    if abs(from_lat - to_lat) > 0.016:
        return False

    def _alibey_side(lon: float) -> int:
        if lon <= 28.9476:
            return -1
        if lon >= 28.9491:
            return 1
        return 0

    side_a = _alibey_side(from_lon)
    side_b = _alibey_side(to_lon)
    if side_a != 0 and side_b != 0 and side_a != side_b:
        return True

    # Gri koridorda kalan endpoint'ler icin daha toleransli crossing heuristigi.
    lon_span_min = min(from_lon, to_lon)
    lon_span_max = max(from_lon, to_lon)
    if (
        abs(from_lon - to_lon) >= 0.0016
        and lon_span_min <= 28.9484
        and lon_span_max >= 28.9492
    ):
        return True

    # Dar gri bolgede bir endpoint kalsa bile su koridoru cizgisi kesiliyorsa crossing kabul et.
    if min(from_lon, to_lon) <= 28.9476 and max(from_lon, to_lon) >= 28.9484:
        return True

    # Daha genis yedek kontrol.
    return min(from_lon, to_lon) <= 28.9470 and max(from_lon, to_lon) >= 28.9497


def _coords_pass_near_checkpoints(
    coords: List[List[float]],
    checkpoints: List[Tuple[float, float]],
    max_dist_m: float = 450.0,
) -> bool:
    if not coords:
        return False
    for c in coords:
        if not isinstance(c, list) or len(c) < 2:
            continue
        lat = float(c[0])
        lon = float(c[1])
        for cp_lat, cp_lon in checkpoints:
            if _haversine_distance(lat, lon, cp_lat, cp_lon) <= max_dist_m:
                return True
    return False


def _is_allowed_water_crossing_walk(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
    coords: List[List[float]],
    is_fallback: bool,
) -> bool:
    """
    Su gecisi iceren yuruyuslerde deterministik kural.
    """
    if _is_forbidden_bosphorus_walk(from_lat, from_lon, to_lat, to_lon):
        return False
    if _is_likely_alibey_crossing(from_lat, from_lon, to_lat, to_lon):
        if is_fallback:
            return False
        return _coords_pass_near_checkpoints(coords, ALIBEY_WALK_BRIDGE_CHECKPOINTS, max_dist_m=420.0)
    if not _is_likely_halic_crossing(from_lat, from_lon, to_lat, to_lon):
        return True
    if is_fallback:
        return False
    return _coords_pass_near_checkpoints(coords, HALIC_WALK_BRIDGE_CHECKPOINTS, max_dist_m=450.0)


def _path_distance_m(coords: List[List[float]]) -> float:
    """Verilen [lat, lon] dizi boyunca toplam mesafe (metre)."""
    if not coords or len(coords) < 2:
        return 0.0
    total = 0.0
    for i in range(len(coords) - 1):
        total += _haversine_distance(
            coords[i][0], coords[i][1],
            coords[i + 1][0], coords[i + 1][1],
        )
    return total


def _max_jump_in_coords_m(coords: List[List[float]]) -> float:
    """Ardışık koordinatlar arasındaki maksimum sıçrama mesafesi (metre)."""
    if not coords or len(coords) < 2:
        return 0.0
    max_jump = 0.0
    for i in range(len(coords) - 1):
        jump = _haversine_distance(
            coords[i][0], coords[i][1],
            coords[i + 1][0], coords[i + 1][1],
        )
        if jump > max_jump:
            max_jump = jump
    return max_jump


def _has_implausible_segment_jump(option: Dict) -> bool:
    """
    Transit segment geometrisinde bariz 'teleport' sıçramaları var mı?
    Bu filtre, haritada düz atlama çizen zayıf adayları eler.
    """
    for seg in (option.get("segments") or []):
        mode = str(seg.get("mode") or "").lower()
        if mode == "ferry":
            continue

        coords = seg.get("coords") or []
        if len(coords) < 2:
            continue

        max_jump = _max_jump_in_coords_m(coords)

        # Mode bazlı muhafazakar eşikler.
        if mode == "walk" and max_jump > 3000:
            return True
        if mode == "bus" and max_jump > 5000:
            return True
        if mode == "rail" and max_jump > 5000:
            return True

    return False


def _sum_walk_distance_m(segments: List[Dict]) -> float:
    total = 0.0
    for seg in segments or []:
        if str(seg.get("mode") or "").lower() != "walk":
            continue
        total += float(seg.get("distance_m", 0) or 0)
    return total


def _sum_walk_duration_min(segments: List[Dict]) -> float:
    total = 0.0
    for seg in segments or []:
        if str(seg.get("mode") or "").lower() != "walk":
            continue
        total += float(seg.get("duration_min", 0) or 0)
    return total


def _looks_like_straight_fallback(coords: List[List[float]], start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> bool:
    """
    OSRM hatali/fallback dondugunde genelde sadece [start, end] verir.
    """
    if not coords or len(coords) != 2:
        return False
    a, b = coords[0], coords[1]
    eps = 0.0005
    return (
        abs(a[0] - start_lat) <= eps
        and abs(a[1] - start_lon) <= eps
        and abs(b[0] - end_lat) <= eps
        and abs(b[1] - end_lon) <= eps
    )


def _direct_walk_metrics(origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float) -> Tuple[float, float, List[List[float]]]:
    """
    Direkt yurume metrigini OSRM foot ile guvenilir hale getir.
    OSRM fallback donerse haversine'i ceza carpaniyla sisirerek
    yaka gecisinde yanlis "yurume en hizli" secimini azaltir.
    """
    walk_coords = _get_walk_road_coords(origin_lat, origin_lon, dest_lat, dest_lon)
    geo_direct_m = _haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon)
    if _is_forbidden_bosphorus_walk(origin_lat, origin_lon, dest_lat, dest_lon):
        penalized_m = max(geo_direct_m * 6.0, geo_direct_m + 35000)
        return penalized_m, _walking_time_minutes(penalized_m), walk_coords
    road_m = _path_distance_m(walk_coords)

    if road_m > 10:
        if not _is_allowed_water_crossing_walk(
            origin_lat, origin_lon, dest_lat, dest_lon,
            walk_coords,
            is_fallback=False,
        ):
            penalized_m = max(geo_direct_m * 3.8, geo_direct_m + 9000)
            return penalized_m, _walking_time_minutes(penalized_m), walk_coords
        return road_m, _walking_time_minutes(road_m), walk_coords

    if _looks_like_straight_fallback(walk_coords, origin_lat, origin_lon, dest_lat, dest_lon):
        if _is_forbidden_bosphorus_walk(origin_lat, origin_lon, dest_lat, dest_lon):
            # Iki yaka fallback'i "yurume en hizli"ye dusmesin diye sert ceza.
            penalized_m = max(geo_direct_m * 6.0, geo_direct_m + 35000)
            return penalized_m, _walking_time_minutes(penalized_m), walk_coords
        if _is_likely_halic_crossing(origin_lat, origin_lon, dest_lat, dest_lon):
            penalized_m = max(geo_direct_m * 3.8, geo_direct_m + 8000)
            return penalized_m, _walking_time_minutes(penalized_m), walk_coords
        # OSRM cevap veremediyse direkt kus-ucusu mesafeyi oldugu gibi kullanma.
        # Istanbul bogaz/yaka gecislerinde ciddi underestimate oluyordu.
        penalized_m = max(geo_direct_m * 2.4, geo_direct_m + 2500)
        return penalized_m, _walking_time_minutes(penalized_m), walk_coords

    return geo_direct_m, _walking_time_minutes(geo_direct_m), walk_coords


def _is_feasible_transfer_walk(
    a_lat: float,
    a_lon: float,
    b_lat: float,
    b_lon: float,
    straight_m: float,
) -> bool:
    """
    Transfer edge'i icin iki istasyon arasi yurume baglantisini dogrula.
    Kus-ucusu yakin ama fiziksel olarak gecilemeyen (su/otoyol bariyeri) durumlari azaltir.
    """
    if straight_m <= 0:
        return False
    if _is_forbidden_bosphorus_walk(a_lat, a_lon, b_lat, b_lon):
        return False

    walk_coords = _get_walk_road_coords(a_lat, a_lon, b_lat, b_lon)
    walk_m = _path_distance_m(walk_coords)

    # OSRM fallback olasiligi: sadece iki nokta dondurup dogrudan cizgi olabilir.
    is_fallback = _looks_like_straight_fallback(walk_coords, a_lat, a_lon, b_lat, b_lon)
    if is_fallback:
        return False
    if not _is_allowed_water_crossing_walk(a_lat, a_lon, b_lat, b_lon, walk_coords, is_fallback=is_fallback):
        return False

    if walk_m <= 0:
        return False

    # Kisa transferde yol mesafesi kus-ucusuna gore asiri sapmamali.
    ratio = walk_m / straight_m
    if ratio > 3.5:
        return False

    # Transfer yuruyusu makul olculerde olmali.
    if walk_m > 1400:
        return False

    return True


def _build_walk_leg(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
    max_distance_m: float = 1800.0,
    allow_fallback_if_short: bool = True,
    fallback_max_m: float = 220.0,
    max_ratio: float = 2.8,
) -> Optional[Dict[str, object]]:
    """
    Yaya segmentini OSRM foot ile dogrulayip dondurur.
    Mumkun degilse None dondurur.
    """
    straight_m = _haversine_distance(from_lat, from_lon, to_lat, to_lon)
    if straight_m <= 5:
        # Nokta istasyonun ustundeyse 0m yuruyus gecerli kabul edilir.
        return {
            "coords": [[from_lat, from_lon], [to_lat, to_lon]],
            "distance_m": 0.0,
            "duration_min": 0.0,
        }
    if _is_forbidden_bosphorus_walk(from_lat, from_lon, to_lat, to_lon):
        return None

    major_water_straight = _is_major_water_crossing_straight(from_lat, from_lon, to_lat, to_lon)
    short_fallback_ok = allow_fallback_if_short and straight_m <= fallback_max_m and not major_water_straight

    coords = _get_walk_road_coords(from_lat, from_lon, to_lat, to_lon)
    is_fallback = _looks_like_straight_fallback(coords, from_lat, from_lon, to_lat, to_lon)
    if not _is_allowed_water_crossing_walk(from_lat, from_lon, to_lat, to_lon, coords, is_fallback=is_fallback):
        return None
    road_m = _path_distance_m(coords)

    if is_fallback:
        if not short_fallback_ok:
            return None
        road_m = straight_m
    elif road_m <= 0:
        return None

    if road_m > max_distance_m:
        if short_fallback_ok:
            road_m = straight_m
            coords = [[from_lat, from_lon], [to_lat, to_lon]]
        else:
            return None

    if straight_m > 0 and road_m / straight_m > max_ratio:
        if short_fallback_ok:
            road_m = straight_m
            coords = [[from_lat, from_lon], [to_lat, to_lon]]
        else:
            return None

    # Kisa kus-ucusu mesafede asiri dolambacli rota varsa transferi reddet.
    if straight_m <= 900 and road_m > 1400:
        if short_fallback_ok:
            road_m = straight_m
            coords = [[from_lat, from_lon], [to_lat, to_lon]]
        else:
            return None

    return {
        "coords": coords,
        "distance_m": float(road_m),
        "duration_min": _walking_time_minutes(float(road_m)),
    }


def _get_routes_at_stop(stop_code: int) -> List[str]:
    """Bir duraktan gecen hatlari dondurur."""
    key = ("routes_at_stop", int(stop_code))
    cached = _lookup_cache_get(key)
    if cached is not None:
        return cached
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT route_code FROM route_stops WHERE stop_code = ?",
        (stop_code,),
    )
    routes = [row["route_code"] for row in cursor.fetchall()]
    conn.close()
    _lookup_cache_put(key, routes)
    return routes


def _normalize_transit_stop_name(name: str) -> str:
    """Durak isimlerini kod/farkli karakter varyasyonlarina karsi normalize eder."""
    if not name:
        return ""
    text = str(name).lower().strip()
    text = (
        text.replace("ı", "i")
        .replace("ö", "o")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ç", "c")
        .replace("ğ", "g")
    )
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


def _expand_route_stop_code_aliases(cursor, route_code: str, stop_code: int) -> set[int]:
    """
    Ayni fiziksel duragin hat-yon bazli farkli kodlarini toplar.
    Ornek: CEVIZLIBAG icin 900191/900192 gibi.
    """
    try:
        stop_code_int = int(stop_code)
    except Exception:
        return set()

    key = ("route_stop_aliases", str(route_code), stop_code_int)
    cached = _lookup_cache_get(key)
    if cached is not None:
        return set(cached)

    cursor.execute(
        """
        SELECT rs.stop_code, s.name
        FROM route_stops rs
        LEFT JOIN stops s ON s.code = rs.stop_code
        WHERE rs.route_code = ?
        """,
        (route_code,),
    )
    rows = cursor.fetchall()
    if not rows:
        aliases = {stop_code_int}
        _lookup_cache_put(key, aliases)
        return aliases

    target_norm = ""
    for row in rows:
        try:
            code = int(row["stop_code"])
        except Exception:
            continue
        if code == stop_code_int:
            target_norm = _normalize_transit_stop_name(row["name"])
            break

    if not target_norm:
        cursor.execute("SELECT name FROM stops WHERE code = ?", (stop_code_int,))
        hit = cursor.fetchone()
        if hit:
            target_norm = _normalize_transit_stop_name(hit["name"])

    aliases: set[int] = {stop_code_int}
    if not target_norm:
        _lookup_cache_put(key, aliases)
        return aliases

    for row in rows:
        try:
            code = int(row["stop_code"])
        except Exception:
            continue
        if _normalize_transit_stop_name(row["name"]) == target_norm:
            aliases.add(code)

    _lookup_cache_put(key, aliases)
    return aliases


def _get_route_stop_coords(route_code: str, from_stop_code: int, to_stop_code: int) -> List[List[float]]:
    """
    Bir hat uzerindeki binis duragindan inis duragina kadar
    duraklarin koordinatlarini SIRALI dondurur.

    Her iki yon (D, G) de denenir ve from_stop -> to_stop
    sirasina uyan yon secilir.

    Returns:
        [[lat, lon], [lat, lon], ...] - binis'ten inis'e sirali koordinatlar
    """
    cache_key = ("route_stop_coords", str(route_code), int(from_stop_code), int(to_stop_code))
    cached = _lookup_cache_get(cache_key)
    if cached is not None:
        return cached

    conn = _get_db_connection()
    cursor = conn.cursor()

    from_aliases = _expand_route_stop_code_aliases(cursor, route_code, from_stop_code)
    to_aliases = _expand_route_stop_code_aliases(cursor, route_code, to_stop_code)
    code_pool = sorted(from_aliases | to_aliases)
    if len(code_pool) < 2:
        conn.close()
        _lookup_cache_put(cache_key, [])
        return []
    placeholders = ",".join(["?"] * len(code_pool))

    # Ayni route/direction icinde bir stop birden fazla kez gecebilir.
    # Bu nedenle tek bir "son gorulen stop_order" yerine tum aday ciftleri degerlendir.
    candidates_forward: List[Tuple[int, str, int, int, bool]] = []
    candidates_reverse: List[Tuple[int, str, int, int, bool]] = []

    for direction in ["D", "G"]:
        cursor.execute(
            f"""
            SELECT stop_code, stop_order
            FROM route_stops
            WHERE route_code = ? AND direction = ? AND stop_code IN ({placeholders})
            ORDER BY stop_order
            """,
            (route_code, direction, *code_pool),
        )
        rows = cursor.fetchall()
        if len(rows) < 2:
            continue

        from_orders = [int(r["stop_order"]) for r in rows if int(r["stop_code"]) in from_aliases]
        to_orders = [int(r["stop_order"]) for r in rows if int(r["stop_code"]) in to_aliases]
        if not from_orders or not to_orders:
            continue

        for from_order in from_orders:
            for to_order in to_orders:
                if from_order == to_order:
                    continue
                if from_order <= to_order:
                    candidates_forward.append((to_order - from_order, direction, from_order, to_order, False))
                else:
                    # Fallback: direction sabitken ters sirali eslesme cikarsa
                    # araligi yine alip cikista ters cevir.
                    candidates_reverse.append((from_order - to_order, direction, to_order, from_order, True))

    selected = None
    if candidates_forward:
        candidates_forward.sort(key=lambda x: x[0])
        selected = candidates_forward[0]
    elif candidates_reverse:
        candidates_reverse.sort(key=lambda x: x[0])
        selected = candidates_reverse[0]

    if not selected:
        conn.close()
        _lookup_cache_put(cache_key, [])
        return []

    _, direction, start_order, end_order, reverse_needed = selected
    cursor.execute(
        """
        SELECT rs.stop_order, s.lat, s.lon
        FROM route_stops rs
        LEFT JOIN stops s ON rs.stop_code = s.code
        WHERE rs.route_code = ? AND rs.direction = ?
        AND rs.stop_order >= ? AND rs.stop_order <= ?
        ORDER BY rs.stop_order
        """,
        (route_code, direction, start_order, end_order),
    )

    coords: List[List[float]] = []
    for row in cursor.fetchall():
        lat = row["lat"]
        lon = row["lon"]
        if lat is None or lon is None:
            continue
        coords.append([float(lat), float(lon)])

    if reverse_needed:
        coords.reverse()

    conn.close()
    _lookup_cache_put(cache_key, coords)
    return coords


def _get_nearby_routes(lat: float, lon: float, radius: int = 500) -> List[Dict]:
    """Belirli yaricaptaki duraklardan gecen hatlari toplar."""
    stops = _cached_get_stops_in_area(lat, lon, radius)
    route_set = {}
    for stop in stops[:15]:
        routes = _get_routes_at_stop(stop["code"])
        for r in routes:
            if r not in route_set:
                route_set[r] = {
                    "route_code": r,
                    "stop_name": stop["name"],
                    "stop_code": stop["code"],
                    "distance_m": stop["distance_m"],
                }
    return list(route_set.values())


def _normalize_station_name(name: str) -> str:
    if not name:
        return ""
    return (
        name.lower()
        .replace("-", " ")
        .replace("_", " ")
        .replace("ı", "i")
        .replace("ö", "o")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ç", "c")
        .replace("ğ", "g")
        .strip()
    )


def _get_line_path_between_stations(line_id: int, from_station_id: int, to_station_id: int) -> List[Dict]:
    stations = _cached_get_metro_line_stations(line_id)
    if len(stations) < 2:
        return []
    from_idx = None
    to_idx = None
    for i, st in enumerate(stations):
        if st["id"] == from_station_id:
            from_idx = i
        if st["id"] == to_station_id:
            to_idx = i
    if from_idx is None or to_idx is None:
        return []
    if from_idx <= to_idx:
        return stations[from_idx:to_idx + 1]
    seg = stations[to_idx:from_idx + 1]
    seg.reverse()
    return seg


def _find_metro_transfer_pairs(
    line_a_stations: List[Dict],
    line_b_stations: List[Dict],
    max_distance_m: float = 260.0,
) -> List[Tuple[Dict, Dict]]:
    """
    Iki farkli metro hatti arasinda aktarma olabilecek istasyon ciftlerini bulur.
    Once isim eslesmesini, sonra fiziksel yakinligi kullanir.
    """
    a_name_map = {_normalize_station_name(s.get("description") or s.get("name")): s for s in line_a_stations}
    b_name_map = {_normalize_station_name(s.get("description") or s.get("name")): s for s in line_b_stations}

    pairs: List[Tuple[Dict, Dict]] = []
    seen_ids = set()

    # 1) Isim bazli guclu eslesme
    for nm, a_st in a_name_map.items():
        if not nm or nm not in b_name_map:
            continue
        b_st = b_name_map[nm]
        dist = _haversine_distance(a_st["lat"], a_st["lon"], b_st["lat"], b_st["lon"])
        # Ayni isimli fakat farkli bolgedeki istasyonlar yalanci aktarma uretebilir
        # (ornegin farkli hatlarda "Yenimahalle"). Isim eslesmesinde de
        # fiziksel yakinligi zorunlu kil.
        if dist > (max_distance_m * 1.8):
            continue
        key = (a_st["id"], b_st["id"])
        if key in seen_ids:
            continue
        seen_ids.add(key)
        pairs.append((a_st, b_st))

    # 2) Fiziksel yakinlik bazli eslesme
    # Interchange istasyon isimleri her zaman birebir ayni gelmeyebiliyor.
    close_pairs = []
    for a_st in line_a_stations:
        for b_st in line_b_stations:
            dist = _haversine_distance(a_st["lat"], a_st["lon"], b_st["lat"], b_st["lon"])
            if dist <= max_distance_m:
                close_pairs.append((dist, a_st, b_st))

    close_pairs.sort(key=lambda x: x[0])
    for _, a_st, b_st in close_pairs[:4]:
        key = (a_st["id"], b_st["id"])
        if key in seen_ids:
            continue
        seen_ids.add(key)
        pairs.append((a_st, b_st))
        if len(pairs) >= 5:
            break

    return pairs


def _build_metro_options(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    direct_walk_min: float,
    direct_walk_m: float,
    max_results: int = 4,
) -> List[Dict]:
    """Metro API verisinden direkt ve tek aktarmali secenekler uretir."""
    options = []
    search_radii = [900, 1600, 2600, 4000, 5500]

    origin_candidates = []
    dest_candidates = []
    for radius in search_radii:
        origin_candidates = _cached_get_metro_stations_in_area(origin_lat, origin_lon, radius)
        dest_candidates = _cached_get_metro_stations_in_area(dest_lat, dest_lon, radius)
        if origin_candidates and dest_candidates:
            break

    if not origin_candidates or not dest_candidates:
        return []

    origin_candidates = origin_candidates[:15]
    dest_candidates = dest_candidates[:15]

    seen = set()
    for o in origin_candidates:
        for d in dest_candidates:
            o_lines = _cached_get_metro_lines_for_station(o["id"])
            d_lines = _cached_get_metro_lines_for_station(d["id"])
            if not o_lines or not d_lines:
                continue

            # Direkt ayni hat
            d_lines_by_id = {ln["id"]: ln for ln in d_lines}
            for o_line in o_lines:
                line_id = o_line["id"]
                if line_id not in d_lines_by_id:
                    continue
                line_path = _get_line_path_between_stations(line_id, o["id"], d["id"])
                if len(line_path) < 2:
                    continue
                walk_to_seg = _build_walk_leg(
                    origin_lat, origin_lon, float(o["lat"]), float(o["lon"]),
                    max_distance_m=1500,
                    allow_fallback_if_short=True,
                    fallback_max_m=1200,
                    max_ratio=8.0,
                )
                walk_from_seg = _build_walk_leg(
                    float(d["lat"]), float(d["lon"]), dest_lat, dest_lon,
                    max_distance_m=1800,
                    allow_fallback_if_short=True,
                    fallback_max_m=1200,
                    max_ratio=8.0,
                )
                if not walk_to_seg or not walk_from_seg:
                    continue
                rail_coords = [[s["lat"], s["lon"]] for s in line_path]
                rail_distance_m = _path_distance_m(rail_coords)
                walk_to = float(walk_to_seg["duration_min"])
                walk_from = float(walk_from_seg["duration_min"])
                wait_time = 4.0
                rail_time = _metro_travel_time_minutes(rail_distance_m / 1000)
                total_time = walk_to + wait_time + rail_time + walk_from

                if total_time > max(direct_walk_min * 2.5, 90):
                    continue
                if (float(walk_to_seg["distance_m"]) + rail_distance_m + float(walk_from_seg["distance_m"])) > max(direct_walk_m * 5.5, 22000):
                    continue

                key = ("direct", line_id, o["id"], d["id"])
                if key in seen:
                    continue
                seen.add(key)
                line_name = o_line.get("name", f"L{line_id}")
                options.append({
                    "type": "transit",
                    "transit_mode": "metro",
                    "icon": "metro",
                    "name": f"{line_name} Metro",
                    "description": f"{o['description']} -> {d['description']}",
                    "total_time_min": round(total_time, 1),
                    "total_distance_m": round(float(walk_to_seg["distance_m"]) + rail_distance_m + float(walk_from_seg["distance_m"])),
                    "total_walk_m": round(float(walk_to_seg["distance_m"]) + float(walk_from_seg["distance_m"])),
                    "route_code": line_name,
                    "route_name": o_line.get("long_description", line_name),
                    "transfer_count": 0,
                    "segments": [
                        {
                            "mode": "walk",
                            "description": f"Istasyona yuru: {o['description']}",
                            "distance_m": round(float(walk_to_seg["distance_m"])),
                            "duration_min": walk_to,
                            "coords": walk_to_seg["coords"],
                        },
                        {
                            "mode": "rail",
                            "description": f"{line_name} hatti",
                            "route_code": line_name,
                            "from_stop": o["description"],
                            "to_stop": d["description"],
                            "distance_m": round(rail_distance_m),
                            "duration_min": rail_time,
                            "wait_min": wait_time,
                            "coords": rail_coords,
                            "stop_coords": rail_coords,
                        },
                        {
                            "mode": "walk",
                            "description": "Istasyondan hedefe yuru",
                            "distance_m": round(float(walk_from_seg["distance_m"])),
                            "duration_min": walk_from,
                            "coords": walk_from_seg["coords"],
                        },
                    ],
                })

            # Tek aktarma (isim bazli transfer)
            o_lines_map = {ln["id"]: ln for ln in o_lines}
            d_lines_map = {ln["id"]: ln for ln in d_lines}
            for line_a_id, line_a in o_lines_map.items():
                a_stations = _cached_get_metro_line_stations(line_a_id)
                if len(a_stations) < 2:
                    continue

                for line_b_id, line_b in d_lines_map.items():
                    if line_a_id == line_b_id:
                        continue
                    b_stations = _cached_get_metro_line_stations(line_b_id)
                    if len(b_stations) < 2:
                        continue
                    transfer_pairs = _find_metro_transfer_pairs(a_stations, b_stations)
                    if not transfer_pairs:
                        continue

                    # Aktarma adaylarini dar bir ilk-3 kesitiyle sinirlamak,
                    # M1B->M1A gibi hatlarda daha dogru dugumleri (ornegin Otogar)
                    # hic denemeden elemekteydi. Tum adaylari degerlendirip
                    # en iyi sonucu asagida sureye gore seciyoruz.
                    for transfer_a, transfer_b in transfer_pairs:
                        leg1 = _get_line_path_between_stations(line_a_id, o["id"], transfer_a["id"])
                        leg2 = _get_line_path_between_stations(line_b_id, transfer_b["id"], d["id"])
                        if len(leg1) < 2 or len(leg2) < 2:
                            continue
                        walk_to_seg = _build_walk_leg(
                            origin_lat, origin_lon, float(o["lat"]), float(o["lon"]),
                            max_distance_m=1500,
                            allow_fallback_if_short=True,
                            fallback_max_m=1200,
                            max_ratio=8.0,
                        )
                        walk_from_seg = _build_walk_leg(
                            float(d["lat"]), float(d["lon"]), dest_lat, dest_lon,
                            max_distance_m=1800,
                            allow_fallback_if_short=True,
                            fallback_max_m=1200,
                            max_ratio=8.0,
                        )
                        if not walk_to_seg or not walk_from_seg:
                            continue

                        transfer_direct_m = _haversine_distance(
                            float(transfer_a["lat"]),
                            float(transfer_a["lon"]),
                            float(transfer_b["lat"]),
                            float(transfer_b["lon"]),
                        )
                        if transfer_direct_m > (MAX_RAIL_TRANSFER_WALK_M * 1.6):
                            continue
                        transfer_walk_seg = _build_walk_leg(
                            float(transfer_a["lat"]),
                            float(transfer_a["lon"]),
                            float(transfer_b["lat"]),
                            float(transfer_b["lon"]),
                            max_distance_m=MAX_RAIL_TRANSFER_WALK_M,
                            allow_fallback_if_short=True,
                            fallback_max_m=min(MAX_RAIL_TRANSFER_WALK_M, 1000.0),
                            max_ratio=8.0,
                        )
                        if not transfer_walk_seg:
                            continue

                        coords1 = [[s["lat"], s["lon"]] for s in leg1]
                        coords2 = [[s["lat"], s["lon"]] for s in leg2]
                        dist1 = _path_distance_m(coords1)
                        dist2 = _path_distance_m(coords2)
                        walk_to = float(walk_to_seg["duration_min"])
                        walk_from = float(walk_from_seg["duration_min"])
                        transfer_walk_min = float(transfer_walk_seg["duration_min"])
                        transfer_walk_m = float(transfer_walk_seg["distance_m"])
                        wait1 = 4.0
                        wait2 = 4.0
                        rail1 = _metro_travel_time_minutes(dist1 / 1000)
                        rail2 = _metro_travel_time_minutes(dist2 / 1000)
                        total_time = walk_to + wait1 + rail1 + transfer_walk_min + wait2 + rail2 + walk_from

                        total_distance = (
                            float(walk_to_seg["distance_m"])
                            + dist1
                            + transfer_walk_m
                            + dist2
                            + float(walk_from_seg["distance_m"])
                        )
                        if total_time > max(direct_walk_min * 3.1, 110):
                            continue
                        if total_distance > max(direct_walk_m * 6.2, 28000):
                            continue

                        key = ("transfer", line_a_id, line_b_id, o["id"], d["id"], transfer_a["id"], transfer_b["id"])
                        if key in seen:
                            continue
                        seen.add(key)

                        name_a = line_a.get("name", f"L{line_a_id}")
                        name_b = line_b.get("name", f"L{line_b_id}")
                        transfer_desc_a = transfer_a.get("description") or transfer_a.get("name") or "Transfer"
                        transfer_desc_b = transfer_b.get("description") or transfer_b.get("name") or "Transfer"
                        transfer_desc = transfer_desc_a if transfer_desc_a == transfer_desc_b else f"{transfer_desc_a} -> {transfer_desc_b}"
                        options.append({
                            "type": "transit",
                            "transit_mode": "metro",
                            "icon": "metro",
                            "name": f"{name_a} + {name_b} Aktarmali",
                            "description": f"{o['description']} -> {transfer_desc} -> {d['description']}",
                            "total_time_min": round(total_time, 1),
                            "total_distance_m": round(total_distance),
                            "total_walk_m": round(
                                float(walk_to_seg["distance_m"]) + transfer_walk_m + float(walk_from_seg["distance_m"])
                            ),
                            "route_code": f"{name_a}->{name_b}",
                            "route_name": f"{name_a} + {name_b}",
                            "transfer_count": 1,
                            "segments": [
                                {
                                    "mode": "walk",
                                    "description": f"Istasyona yuru: {o['description']}",
                                    "distance_m": round(float(walk_to_seg["distance_m"])),
                                    "duration_min": walk_to,
                                    "coords": walk_to_seg["coords"],
                                },
                                {
                                    "mode": "rail",
                                    "description": f"{name_a} hatti",
                                    "route_code": name_a,
                                    "from_stop": o["description"],
                                    "to_stop": transfer_desc_a,
                                    "distance_m": round(dist1),
                                    "duration_min": rail1,
                                    "wait_min": wait1,
                                    "coords": coords1,
                                    "stop_coords": coords1,
                                },
                                {
                                    "mode": "walk",
                                    "description": f"Aktarma yuruyusu: {transfer_desc_a} -> {transfer_desc_b}",
                                    "distance_m": round(transfer_walk_m),
                                    "duration_min": transfer_walk_min,
                                    "coords": transfer_walk_seg["coords"],
                                },
                                {
                                    "mode": "rail",
                                    "description": f"{name_b} hatti",
                                    "route_code": name_b,
                                    "from_stop": transfer_desc_b,
                                    "to_stop": d["description"],
                                    "distance_m": round(dist2),
                                    "duration_min": rail2,
                                    "wait_min": wait2,
                                    "coords": coords2,
                                    "stop_coords": coords2,
                                },
                                {
                                    "mode": "walk",
                                    "description": "Istasyondan hedefe yuru",
                                    "distance_m": round(float(walk_from_seg["distance_m"])),
                                    "duration_min": walk_from,
                                    "coords": walk_from_seg["coords"],
                                },
                            ],
                        })

    options.sort(key=lambda x: x["total_time_min"])

    # Ayni hat kombinasyonunu farkli istasyon secimiyle tekrar gostermeyi azalt.
    unique = []
    seen = set()
    for opt in options:
        transfer_count = int(opt.get("transfer_count", 0))
        if transfer_count == 0:
            key = ("metro_direct", str(opt.get("route_code", "")))
        else:
            key = ("metro_transfer", str(opt.get("route_code", "")))
        if key in seen:
            continue
        seen.add(key)
        unique.append(opt)
        if len(unique) >= max_results:
            break

    return unique


def _normalized_station_name(name: str) -> str:
    raw = (name or "").strip().lower()
    if not raw:
        return ""
    raw = (
        raw.replace("ı", "i")
        .replace("ğ", "g")
        .replace("ş", "s")
        .replace("ç", "c")
        .replace("ö", "o")
        .replace("ü", "u")
    )
    raw = re.sub(r"\s+", " ", raw)
    raw = raw.replace(" istasyonu", "").replace(" station", "")
    return raw


def _normalized_station_name(name: str) -> str:
    """
    Istasyon adlarini ortak anahtara indirger.
    Hem Turkce karakterleri hem de bozuk UTF-8 gorunumlerini normalize eder.
    """
    raw = (name or "").strip().lower()
    if not raw:
        return ""

    raw = (
        raw.replace("ı", "i")
        .replace("ğ", "g")
        .replace("ş", "s")
        .replace("ç", "c")
        .replace("ö", "o")
        .replace("ü", "u")
        .replace("â", "a")
        .replace("î", "i")
        .replace("û", "u")
    )
    raw = (
        raw.replace("ı", "i")
        .replace("ğ", "g")
        .replace("ş", "s")
        .replace("ç", "c")
        .replace("ö", "o")
        .replace("ü", "u")
    )
    raw = re.sub(r"\s+", " ", raw)
    raw = raw.replace(" istasyonu", "").replace(" station", "")
    return raw


def _build_metro_graph_data() -> Tuple[Dict[int, Dict], Dict[int, Dict], Dict[int, List[Tuple[int, float, int, str]]]]:
    """
    Metro/tram/funikuler agini graf olarak hazirlar.
    Edge tuple: (to_station_id, distance_m, line_id, edge_kind['rail'|'transfer'|'ferry'])
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, long_description, line_type, is_active FROM metro_lines WHERE is_active = 1")
    line_rows = [dict(r) for r in cursor.fetchall()]
    line_map: Dict[int, Dict] = {int(r["id"]): r for r in line_rows}

    # Metro API'de bazi istasyonlarda is_active=0 gelebiliyor ama hat aktif.
    # Bu satirlar route graph'tan dusunce M2 gibi hatlar gorunmuyor.
    cursor.execute("SELECT id, name, description, lat, lon, is_active FROM metro_stations")
    station_rows = [dict(r) for r in cursor.fetchall()]
    station_map: Dict[int, Dict] = {int(r["id"]): r for r in station_rows}

    cursor.execute(
        """
        SELECT line_id, station_id, station_order
        FROM metro_line_stations
        ORDER BY line_id, station_order
        """
    )
    mls_rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    line_station_order: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
    station_lines: Dict[int, set] = defaultdict(set)
    for row in mls_rows:
        line_id = int(row["line_id"])
        station_id = int(row["station_id"])
        if line_id not in line_map or station_id not in station_map:
            continue
        station_lines[station_id].add(line_id)
        line_station_order[line_id].append((int(row["station_order"] or 0), station_id))

    graph: Dict[int, List[Tuple[int, float, int, str]]] = defaultdict(list)

    # Ayni hat uzerindeki ardilsik istasyonlar
    for line_id, ordered in line_station_order.items():
        ordered = sorted(ordered, key=lambda x: x[0])
        for i in range(len(ordered) - 1):
            a_id = ordered[i][1]
            b_id = ordered[i + 1][1]
            a = station_map.get(a_id)
            b = station_map.get(b_id)
            if not a or not b:
                continue
            dist = _haversine_distance(float(a["lat"]), float(a["lon"]), float(b["lat"]), float(b["lon"]))
            if dist <= 0:
                continue
            graph[a_id].append((b_id, dist, line_id, "rail"))
            graph[b_id].append((a_id, dist, line_id, "rail"))

    # Hatlar arasi transfer edge:
    # GENEL yakinlik eslestirmesi yerine sadece ayni istasyon adina sahip
    # ve gercekten yurunebilir ciftlere izin ver.
    station_name_ids: Dict[str, List[int]] = defaultdict(list)
    for sid, st in station_map.items():
        norm = _normalized_station_name(str(st.get("description") or st.get("name") or ""))
        if norm:
            station_name_ids[norm].append(int(sid))

    transfer_cache: Dict[Tuple[int, int], bool] = {}

    def _is_valid_transfer_pair(a_id: int, b_id: int, norm_name: str) -> bool:
        key = (min(a_id, b_id), max(a_id, b_id))
        cached = transfer_cache.get(key)
        if cached is not None:
            return cached

        a = station_map.get(a_id)
        b = station_map.get(b_id)
        if not a or not b:
            transfer_cache[key] = False
            return False

        dist = _haversine_distance(float(a["lat"]), float(a["lon"]), float(b["lat"]), float(b["lon"]))
        if dist > _transfer_max_distance_for_name(norm_name):
            transfer_cache[key] = False
            return False

        walk_ok = _is_feasible_transfer_walk(
            float(a["lat"]), float(a["lon"]),
            float(b["lat"]), float(b["lon"]),
            dist,
        )
        transfer_cache[key] = walk_ok
        return walk_ok

    for norm_name, ids in station_name_ids.items():
        if len(ids) < 2:
            continue
        for i in range(len(ids)):
            a_id = ids[i]
            a_lines = station_lines.get(a_id, set())
            if not a_lines:
                continue
            for j in range(i + 1, len(ids)):
                b_id = ids[j]
                b_lines = station_lines.get(b_id, set())
                if not b_lines:
                    continue
                if a_lines & b_lines:
                    continue
                if not _is_valid_transfer_pair(a_id, b_id, norm_name):
                    continue
                a = station_map[a_id]
                b = station_map[b_id]
                dist = _haversine_distance(float(a["lat"]), float(a["lon"]), float(b["lat"]), float(b["lon"]))
                graph[a_id].append((b_id, dist, 0, "transfer"))
                graph[b_id].append((a_id, dist, 0, "transfer"))

    # Marmaray omurga entegrasyonu (IBB Metro API'de bazi senaryolarda eksik kaldigi icin).
    # Bu baglar yaka gecisindeki metro onerilerini destekler.
    VIRTUAL_MARMARAY_LINE_ID = -100
    if VIRTUAL_MARMARAY_LINE_ID not in line_map:
        line_map[VIRTUAL_MARMARAY_LINE_ID] = {
            "id": VIRTUAL_MARMARAY_LINE_ID,
            "name": "Marmaray",
            "long_description": "Marmaray Entegrasyonu",
            "line_type": "metro",
            "is_active": 1,
        }

    virtual_links = [
        ("uskudar", "yenikapi"),
        ("ayrilik cesmesi", "yenikapi"),
        ("ayrilik cesmesi", "sirkeci"),
        ("uskudar", "sirkeci"),
    ]

    for left_name, right_name in virtual_links:
        left_ids = station_name_ids.get(left_name, [])
        right_ids = station_name_ids.get(right_name, [])
        if not left_ids or not right_ids:
            continue
        for a_id in left_ids:
            for b_id in right_ids:
                if a_id == b_id:
                    continue
                a = station_map.get(a_id)
                b = station_map.get(b_id)
                if not a or not b:
                    continue
                dist = _haversine_distance(float(a["lat"]), float(a["lon"]), float(b["lat"]), float(b["lon"]))
                if dist <= 0:
                    continue
                graph[a_id].append((b_id, dist, VIRTUAL_MARMARAY_LINE_ID, "rail"))
                graph[b_id].append((a_id, dist, VIRTUAL_MARMARAY_LINE_ID, "rail"))

    # Vapur omurga entegrasyonu (genel, iskele bazli).
    VIRTUAL_FERRY_LINE_ID = -200
    if VIRTUAL_FERRY_LINE_ID not in line_map:
        line_map[VIRTUAL_FERRY_LINE_ID] = {
            "id": VIRTUAL_FERRY_LINE_ID,
            "name": "Vapur",
            "long_description": "Sehir Hatlari Entegrasyonu",
            "line_type": "ferry",
            "is_active": 1,
        }

    for left_name, right_name in FERRY_TERMINAL_LINKS:
        left_ids = station_name_ids.get(left_name, [])
        right_ids = station_name_ids.get(right_name, [])
        if not left_ids or not right_ids:
            continue
        for a_id in left_ids:
            for b_id in right_ids:
                if a_id == b_id:
                    continue
                a = station_map.get(a_id)
                b = station_map.get(b_id)
                if not a or not b:
                    continue
                dist = _haversine_distance(float(a["lat"]), float(a["lon"]), float(b["lat"]), float(b["lon"]))
                if dist <= 0:
                    continue
                graph[a_id].append((b_id, dist, VIRTUAL_FERRY_LINE_ID, "ferry"))
                graph[b_id].append((a_id, dist, VIRTUAL_FERRY_LINE_ID, "ferry"))

    return line_map, station_map, graph


def _shortest_metro_path(
    origin_candidates: List[Dict],
    dest_candidates: List[Dict],
    final_dest_lat: Optional[float] = None,
    final_dest_lon: Optional[float] = None,
    allow_ferry: bool = True,
) -> Optional[Dict]:
    """
    Cok aktarmali metro aginda en iyi yolu bulur (Dijkstra).
    """
    if not origin_candidates or not dest_candidates:
        return None

    line_map, station_map, graph = _build_metro_graph_data()
    if not graph:
        return None

    dest_ids = {int(d["id"]) for d in dest_candidates}
    origin_by_id = {int(o["id"]): o for o in origin_candidates}
    dest_by_id = {int(d["id"]): d for d in dest_candidates}

    # State: (cost, station_id, current_line_id, transfer_count)
    pq: List[Tuple[float, int, int, int]] = []
    best: Dict[Tuple[int, int, int], float] = {}
    parent: Dict[Tuple[int, int, int], Tuple[Tuple[int, int, int], Tuple[int, float, int, str]]] = {}

    for o in origin_candidates:
        sid = int(o["id"])
        walk_to = _walking_time_minutes(float(o.get("distance_m", 0)))
        state = (sid, 0, 0)  # station, current_line, transfer_count
        best[state] = walk_to
        heapq.heappush(pq, (walk_to, sid, 0, 0))

    best_goal_state = None
    best_goal_cost = float("inf")
    goal_walk_seg_by_state: Dict[Tuple[int, int, int], Dict[str, object]] = {}

    while pq:
        cost, sid, current_line, transfer_count = heapq.heappop(pq)
        state = (sid, current_line, transfer_count)
        if cost > best.get(state, float("inf")):
            continue

        if sid in dest_ids:
            walk_seg = None
            if final_dest_lat is not None and final_dest_lon is not None:
                st = station_map.get(sid)
                if st is not None:
                    walk_seg = _build_walk_leg(
                        float(st["lat"]),
                        float(st["lon"]),
                        float(final_dest_lat),
                        float(final_dest_lon),
                        max_distance_m=5000,
                        allow_fallback_if_short=True,
                        fallback_max_m=2000,
                        max_ratio=20.0,
                    )
                if not walk_seg:
                    continue
                walk_from = float(walk_seg.get("duration_min", 0.0))
            else:
                walk_from = _walking_time_minutes(float(dest_by_id[sid].get("distance_m", 0)))
                walk_seg = {
                    "coords": [],
                    "distance_m": float(dest_by_id[sid].get("distance_m", 0)),
                    "duration_min": float(walk_from),
                }
            total = cost + walk_from
            if total < best_goal_cost:
                best_goal_cost = total
                best_goal_state = state
                goal_walk_seg_by_state[state] = walk_seg

        for to_sid, dist_m, line_id, edge_kind in graph.get(sid, []):
            if edge_kind == "ferry" and not allow_ferry:
                continue
            next_transfer = transfer_count
            add_cost = 0.0
            next_line = current_line

            if edge_kind in {"rail", "ferry"}:
                if edge_kind == "ferry":
                    ride_min = _ferry_travel_time_minutes(dist_m / 1000.0)
                else:
                    ride_min = _metro_travel_time_minutes(dist_m / 1000.0)
                if ride_min <= 0:
                    continue
                # Yeni hatta binis bekleme/aktarma cezasi
                if current_line == 0:
                    add_cost += (4.5 if edge_kind == "ferry" else 3.5)
                elif current_line != line_id:
                    next_transfer += 1
                    add_cost += (6.0 if edge_kind == "ferry" else 5.0)
                next_line = line_id
                add_cost += ride_min
            else:
                # Fiziksel transfer yuruyusu
                add_cost += _walking_time_minutes(dist_m)
                if current_line != 0:
                    next_transfer += 1
                next_line = 0

            if next_transfer > 3:
                continue

            next_cost = cost + add_cost
            next_state = (to_sid, next_line, next_transfer)
            if next_cost + 1e-6 < best.get(next_state, float("inf")):
                best[next_state] = next_cost
                parent[next_state] = (state, (to_sid, dist_m, line_id, edge_kind))
                heapq.heappush(pq, (next_cost, to_sid, next_line, next_transfer))

    if best_goal_state is None:
        return None

    # Path reconstruct
    path_states = []
    cur = best_goal_state
    while cur in parent:
        prev, edge = parent[cur]
        path_states.append((prev, cur, edge))
        cur = prev
    path_states.reverse()

    start_station_id = path_states[0][0][0] if path_states else best_goal_state[0]
    end_station_id = best_goal_state[0]
    start_station = station_map.get(start_station_id)
    end_station = station_map.get(end_station_id)
    if not start_station or not end_station:
        return None

    # Segmentleri hatlara gore grupla
    grouped = []
    current = None
    for prev_state, _, edge in path_states:
        from_sid = int(prev_state[0])
        to_sid, dist_m, line_id, edge_kind = edge
        if edge_kind not in {"rail", "ferry"}:
            if current is not None:
                grouped.append(current)
                current = None
            grouped.append({"kind": "transfer", "from_sid": from_sid, "to_sid": to_sid, "distance_m": dist_m})
            continue
        if current is None or current["line_id"] != line_id:
            if current is not None:
                grouped.append(current)
            current = {
                "kind": "rail",
                "edge_kind": edge_kind,
                "line_id": line_id,
                "station_ids": [from_sid, to_sid],
                "distance_m": dist_m
            }
        else:
            if not current["station_ids"] or int(current["station_ids"][-1]) != to_sid:
                current["station_ids"].append(to_sid)
            current["distance_m"] += dist_m
    if current is not None:
        grouped.append(current)

    return {
        "line_map": line_map,
        "station_map": station_map,
        "origin_station": origin_by_id.get(start_station_id),
        "dest_station": dest_by_id.get(end_station_id),
        "grouped_segments": grouped,
        "total_time_min": round(best_goal_cost, 1),
        "transfer_count": int(best_goal_state[2]),
        "dest_walk_seg": goal_walk_seg_by_state.get(best_goal_state),
    }


def _build_graph_metro_option(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    direct_walk_min: float,
    direct_walk_m: float,
) -> Optional[Dict]:
    search_radii = [1200, 2200, 3500, 5200, 7000]
    best_path_info: Optional[Dict] = None
    best_origin_candidates: List[Dict] = []
    best_dest_candidates: List[Dict] = []
    best_score = float("inf")
    same_side = (
        _bosphorus_side(float(origin_lon)) != 0
        and _bosphorus_side(float(origin_lon)) == _bosphorus_side(float(dest_lon))
    )
    # Ayni yakada gorece kisa yolculuklarda once karasal/railsel rota denensin.
    prefer_non_ferry = same_side and direct_walk_m <= 18000

    for radius in search_radii:
        raw_origin = _cached_get_metro_stations_in_area(origin_lat, origin_lon, radius)
        raw_dest = _cached_get_metro_stations_in_area(dest_lat, dest_lon, radius)
        access_cap = 2000 if direct_walk_m < 20000 else 2600
        max_access_m = min(access_cap, max(800, int(radius * 0.50)))
        origin_candidates = [dict(s) for s in raw_origin if float(s.get("distance_m", 10**9)) <= max_access_m][:12]
        dest_candidates = [dict(s) for s in raw_dest if float(s.get("distance_m", 10**9)) <= max_access_m][:12]
        if not origin_candidates or not dest_candidates:
            continue

        path_variants: List[Dict] = []
        if prefer_non_ferry:
            no_ferry_path = _shortest_metro_path(
                origin_candidates,
                dest_candidates,
                final_dest_lat=dest_lat,
                final_dest_lon=dest_lon,
                allow_ferry=False,
            )
            if no_ferry_path:
                path_variants.append(no_ferry_path)

        any_path = _shortest_metro_path(
            origin_candidates,
            dest_candidates,
            final_dest_lat=dest_lat,
            final_dest_lon=dest_lon,
            allow_ferry=True,
        )
        if any_path:
            path_variants.append(any_path)

        for path_info in path_variants:
            score = float(path_info.get("total_time_min", 10**9))
            has_ferry_leg = any(
                str(seg.get("edge_kind") or "") == "ferry"
                for seg in (path_info.get("grouped_segments") or [])
            )
            # Ayni yakada ferry'yi varsayilan kazanan yapma: ciddi kazanc yoksa geri plana at.
            if prefer_non_ferry and has_ferry_leg:
                score += 9.0

            if score < best_score:
                best_score = score
                best_path_info = path_info
                best_origin_candidates = origin_candidates
                best_dest_candidates = dest_candidates

    if not best_path_info:
        return None

    path_info = best_path_info
    origin_candidates = best_origin_candidates
    dest_candidates = best_dest_candidates

    origin_st = path_info.get("origin_station") or {}
    dest_st = path_info.get("dest_station") or {}
    grouped = path_info.get("grouped_segments") or []
    line_map = path_info.get("line_map") or {}
    station_map = path_info.get("station_map") or {}
    transfer_count = int(path_info.get("transfer_count", 0))
    total_time_min = float(path_info.get("total_time_min", 0.0))

    if total_time_min <= 0:
        return None
    if total_time_min > max(direct_walk_min * 3.3, 125):
        return None

    walk_to_seg = origin_st.get("_walk_seg")
    if not walk_to_seg:
        walk_to_seg = _build_walk_leg(
            origin_lat, origin_lon,
            float(origin_st.get("lat")), float(origin_st.get("lon")),
            max_distance_m=5000,
            allow_fallback_if_short=True,
            fallback_max_m=2000,
            max_ratio=20.0,
        )
    walk_from_seg = path_info.get("dest_walk_seg") or dest_st.get("_walk_seg")
    if not walk_from_seg:
        walk_from_seg = _build_walk_leg(
            float(dest_st.get("lat")), float(dest_st.get("lon")),
            dest_lat, dest_lon,
            max_distance_m=5000,
            allow_fallback_if_short=True,
            fallback_max_m=2000,
            max_ratio=20.0,
        )
    if not walk_to_seg or not walk_from_seg:
        return None

    segments = [{
        "mode": "walk",
        "description": f"Istasyona yuru: {origin_st.get('description') or origin_st.get('name') or 'Baslangic'}",
        "distance_m": round(float(walk_to_seg.get("distance_m", 0))),
        "duration_min": float(walk_to_seg.get("duration_min", 0)),
        "coords": walk_to_seg.get("coords") or [],
    }]

    route_labels = []
    total_distance_m = float(walk_to_seg.get("distance_m", 0)) + float(walk_from_seg.get("distance_m", 0))
    for seg in grouped:
        if seg.get("kind") == "transfer":
            from_station = station_map.get(int(seg.get("from_sid", 0)), {})
            to_station = station_map.get(int(seg["to_sid"]), {})
            transfer_coords: List[List[float]] = []
            if from_station and to_station:
                transfer_seg = _build_walk_leg(
                    float(from_station.get("lat")),
                    float(from_station.get("lon")),
                    float(to_station.get("lat")),
                    float(to_station.get("lon")),
                    max_distance_m=900,
                    allow_fallback_if_short=False,
                )
                if not transfer_seg:
                    return None
                transfer_coords = transfer_seg.get("coords") or []
            segments.append({
                "mode": "walk",
                "description": f"Aktarma yuru: {to_station.get('description') or to_station.get('name') or 'Transfer'}",
                "distance_m": round(float(seg.get("distance_m", 0))),
                "duration_min": _walking_time_minutes(float(seg.get("distance_m", 0))),
                "coords": transfer_coords,
            })
            total_distance_m += float(seg.get("distance_m", 0))
            continue

        line_id = int(seg.get("line_id", 0))
        line = line_map.get(line_id, {})
        line_name = str(line.get("name") or f"L{line_id}")
        edge_kind = str(seg.get("edge_kind") or "rail")

        station_ids = seg.get("station_ids", [])
        
        # Gerçek tünel güzergahı koordinatlarını al (GTFS shapes veya fallback)
        shape_coords = get_metro_line_shape(line_name)
        
        if shape_coords and len(shape_coords) >= 2 and len(station_ids) >= 2:
            # İlk ve son istasyonun shape üzerindeki pozisyonlarını bul
            start_st = station_map.get(int(station_ids[0]), {})
            end_st = station_map.get(int(station_ids[-1]), {})
            
            if not start_st or not end_st:
                # İstasyon verisi yok, station koordinatlarını kullan
                rail_coords = [[float(station_map.get(int(sid), {}).get("lat", 0)),
                               float(station_map.get(int(sid), {}).get("lon", 0))]
                              for sid in station_ids if station_map.get(int(sid))]
            else:
                start_lat, start_lon = float(start_st["lat"]), float(start_st["lon"])
                end_lat, end_lon = float(end_st["lat"]), float(end_st["lon"])
                
                # Başlangıç ve bitiş istasyonlarına en yakın shape indekslerini bul
                best_start_idx = -1
                best_start_dist = float('inf')
                best_end_idx = -1
                best_end_dist = float('inf')
                
                for idx, (shape_lat, shape_lon) in enumerate(shape_coords):
                    dist_start = _haversine_distance(start_lat, start_lon, shape_lat, shape_lon)
                    dist_end = _haversine_distance(end_lat, end_lon, shape_lat, shape_lon)
                    
                    if dist_start < best_start_dist:
                        best_start_dist = dist_start
                        best_start_idx = idx
                    if dist_end < best_end_dist:
                        best_end_dist = dist_end
                        best_end_idx = idx
                
                # Akıllı İstasyon Snapping: Mesafe 800 metreden uzaksa shape kullanma, direkt koordinatları kullan
                if best_start_dist > 800.0 or best_end_dist > 800.0:
                    rail_coords = [[float(station_map.get(int(sid), {}).get("lat", 0)),
                                   float(station_map.get(int(sid), {}).get("lon", 0))]
                                  for sid in station_ids if station_map.get(int(sid))]
                    snapped_indices = []
                else:
                    # Tüm istasyonları en yakın shape noktalarına snap et (sırayla)
                    snapped_indices = []
                    for sid in station_ids:
                        st = station_map.get(int(sid))
                        if not st:
                            continue
                        st_lat, st_lon = float(st["lat"]), float(st["lon"])
                        
                        best_idx = -1
                        best_dist = float('inf')
                        for idx, (shape_lat, shape_lon) in enumerate(shape_coords):
                            dist = _haversine_distance(st_lat, st_lon, shape_lat, shape_lon)
                            if dist < best_dist:
                                best_dist = dist
                                best_idx = idx
                        # İstasyonun shape noktasına olan mesafesi 800 metreden azsa snap et
                        if best_idx >= 0 and best_dist <= 800.0:
                            snapped_indices.append(best_idx)
                
                # Eğer snap edilmiş istasyonlar M2 gibi tek yönlü bir hatta aitse,
                # sadece aradaki tüm shape noktalarını döndür (tünel çizgisi için)
                if snapped_indices and len(snapped_indices) >= 2:
                    # Yonu ilk ve son istasyon snap indeksleri belirler.
                    first_st_idx = int(snapped_indices[0])
                    last_st_idx = int(snapped_indices[-1])

                    if first_st_idx <= last_st_idx:
                        rail_coords = [
                            [float(shape_coords[i][0]), float(shape_coords[i][1])]
                            for i in range(first_st_idx, last_st_idx + 1)
                        ]
                    else:
                        # Python range son degeri disladigi icin last_st_idx - 1 kullanilir.
                        rail_coords = [
                            [float(shape_coords[i][0]), float(shape_coords[i][1])]
                            for i in range(first_st_idx, last_st_idx - 1, -1)
                        ]
                else:
                    # Yeterli istasyon yok, sadece start-end arasını al
                    if best_start_idx < best_end_idx:
                        rail_coords = [[float(shape_coords[i][0]), float(shape_coords[i][1])] 
                                       for i in range(best_start_idx, best_end_idx + 1)]
                    else:
                        rail_coords = [[float(shape_coords[i][0]), float(shape_coords[i][1])] 
                                       for i in range(best_end_idx, best_start_idx + 1)][::-1]
        else:
            # Shape yok, istasyon koordinatlarını doğrudan kullan
            rail_coords = []
            for sid in station_ids:
                st = station_map.get(int(sid))
                if st:
                    rail_coords.append([float(st["lat"]), float(st["lon"])])
        # Shape snap kotu/eksik kalirsa istasyon koordinatlarindan minimum
        # guvenilir segmenti geri kur.
        if len(rail_coords) < 2 and len(station_ids) >= 2:
            station_fallback: List[List[float]] = []
            for sid in station_ids:
                st = station_map.get(int(sid))
                if not st:
                    continue
                lat = st.get("lat")
                lon = st.get("lon")
                if lat is None or lon is None:
                    continue
                pt = [float(lat), float(lon)]
                if not station_fallback or station_fallback[-1] != pt:
                    station_fallback.append(pt)
            if len(station_fallback) >= 2:
                rail_coords = station_fallback

        if len(rail_coords) < 2:
            continue
        route_labels.append(line_name)

        from_station_name = ""
        to_station_name = ""
        if station_ids:
            first_st = station_map.get(int(station_ids[0]), {})
            last_st = station_map.get(int(station_ids[-1]), {})
            from_station_name = str(first_st.get("description") or first_st.get("name") or "")
            to_station_name = str(last_st.get("description") or last_st.get("name") or "")

        total_distance_m += float(seg.get("distance_m", 0))
        segment_mode = "ferry" if edge_kind == "ferry" else "rail"
        if segment_mode == "ferry":
            from_station_name = _ferry_display_name(from_station_name)
            to_station_name = _ferry_display_name(to_station_name)
        if segment_mode == "ferry":
            seg_duration = _ferry_travel_time_minutes(float(seg.get("distance_m", 0)) / 1000.0)
        else:
            seg_duration = _metro_travel_time_minutes(float(seg.get("distance_m", 0)) / 1000.0)
        segments.append({
            "mode": segment_mode,
            "description": f"{line_name} hatti",
            "route_code": line_name,
            "from_stop": from_station_name,
            "to_stop": to_station_name,
            "distance_m": round(float(seg.get("distance_m", 0))),
            "duration_min": seg_duration,
            "wait_min": 6.0 if segment_mode == "ferry" else 4.0,
            "coords": rail_coords,
            "stop_coords": rail_coords,
        })

    segments.append({
        "mode": "walk",
        "description": "Istasyondan hedefe yuru",
        "distance_m": round(float(walk_from_seg.get("distance_m", 0))),
        "duration_min": float(walk_from_seg.get("duration_min", 0)),
        "coords": walk_from_seg.get("coords") or [],
    })

    has_transit_leg = any(s.get("mode") in {"rail", "ferry", "bus"} for s in segments)
    if not has_transit_leg:
        return None

    route_labels = [r for r in route_labels if r]
    has_ferry_leg = any(s.get("mode") == "ferry" for s in segments)
    has_rail_leg = any(s.get("mode") == "rail" for s in segments)
    if has_ferry_leg and same_side:
        saved_min = float(direct_walk_min) - float(total_time_min)
        detour_ratio = float(total_distance_m) / max(1.0, float(direct_walk_m))
        # Ayni yakada vapurlu "tur" secenegi ancak net fayda varsa kabul edilir.
        if detour_ratio >= 1.8 and saved_min < 24:
            return None

    if has_ferry_leg and not has_rail_leg:
        route_code = "->".join(route_labels[:4]) if route_labels else "Vapur"
        route_name = "Vapur"
        display_name = "Vapur"
        transit_mode = "ferry"
        icon = "ferry"
        origin_label = _ferry_display_name(str(origin_st.get("description") or origin_st.get("name") or ""))
        dest_label = _ferry_display_name(str(dest_st.get("description") or dest_st.get("name") or ""))
        route_description = f"{origin_label} -> {dest_label}"
    else:
        route_code = "->".join(route_labels[:4]) if route_labels else "Metro"
        route_name = " + ".join(dict.fromkeys(route_labels)) if route_labels else "Metro"
        if transfer_count > 0:
            display_name = f"{route_name} Aktarmali"
        else:
            display_name = f"{route_name} Metro"
        transit_mode = "metro"
        icon = "metro"
        route_description = f"{origin_st.get('description') or origin_st.get('name') or ''} -> {dest_st.get('description') or dest_st.get('name') or ''}"

    return {
        "type": "transit",
        "transit_mode": transit_mode,
        "icon": icon,
        "name": display_name,
        "description": route_description,
        "total_time_min": round(total_time_min, 1),
        "total_distance_m": round(total_distance_m),
        "total_walk_m": round(_sum_walk_distance_m(segments)),
        "route_code": route_code,
        "route_name": route_name,
        "transfer_count": transfer_count,
        "segments": segments,
    }


def _build_ferry_only_options(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    direct_walk_min: float,
    max_results: int = 2,
) -> List[Dict]:
    """
    Dogrudan vapur terminal ciftlerinden secenek uretir.
    """
    options: List[Dict] = []

    def _ferry_terminal_name(st: Dict) -> str:
        key = str(st.get("terminal_key") or "").strip().lower()
        label = FERRY_TERMINAL_DISPLAY.get(key)
        if label:
            return label
        return str(st.get("description") or st.get("name") or "Iskele")

    def _near_ferry_terminals(lat: float, lon: float) -> List[Dict]:
        candidates = _cached_get_metro_stations_in_area(lat, lon, 4500)
        out = []
        for c in candidates:
            nm = _normalized_station_name(str(c.get("description") or c.get("name") or ""))
            canonical_nm = FERRY_TERMINAL_ALIASES.get(nm, nm)
            if canonical_nm in FERRY_TERMINAL_SET:
                item = dict(c)
                item["terminal_key"] = canonical_nm
                out.append(item)
        out.sort(key=lambda x: float(x.get("distance_m", 10**9)))
        return out[:10]

    origins = _near_ferry_terminals(origin_lat, origin_lon)
    dests = _near_ferry_terminals(dest_lat, dest_lon)
    if not origins or not dests:
        return []

    allowed_pairs = set()
    for a, b in FERRY_TERMINAL_LINKS:
        allowed_pairs.add((a, b))
        allowed_pairs.add((b, a))

    seen = set()
    for o in origins:
        for d in dests:
            pair = (str(o["terminal_key"]), str(d["terminal_key"]))
            if pair not in allowed_pairs:
                continue
            if pair in seen:
                continue
            seen.add(pair)

            walk_to = _build_walk_leg(
                origin_lat, origin_lon,
                float(o["lat"]), float(o["lon"]),
                max_distance_m=1800,
                allow_fallback_if_short=True,
                fallback_max_m=1200,
                max_ratio=8.0,
            )
            walk_from = _build_walk_leg(
                float(d["lat"]), float(d["lon"]),
                dest_lat, dest_lon,
                max_distance_m=2200,
                allow_fallback_if_short=True,
                fallback_max_m=1400,
                max_ratio=8.0,
            )
            if not walk_to or not walk_from:
                continue

            ferry_dist_m = _haversine_distance(float(o["lat"]), float(o["lon"]), float(d["lat"]), float(d["lon"]))
            ferry_time = _ferry_travel_time_minutes(ferry_dist_m / 1000.0)
            total_time = float(walk_to["duration_min"]) + 6.0 + ferry_time + float(walk_from["duration_min"])

            # Yurumeye gore anlamsiz secenekleri ele.
            if total_time > max(direct_walk_min * 1.7, 90):
                continue

            origin_label = _ferry_terminal_name(o)
            dest_label = _ferry_terminal_name(d)

            options.append(
                {
                    "type": "transit",
                    "transit_mode": "ferry",
                    "icon": "ferry",
                    "name": "Vapur",
                    "description": f"{origin_label} -> {dest_label}",
                    "total_time_min": round(total_time, 1),
                    "total_distance_m": round(float(walk_to["distance_m"]) + ferry_dist_m + float(walk_from["distance_m"])),
                    "total_walk_m": round(float(walk_to["distance_m"]) + float(walk_from["distance_m"])),
                    "route_code": f"VAPUR:{o['terminal_key']}->{d['terminal_key']}",
                    "route_name": "Vapur",
                    "transfer_count": 0,
                    "selection_reason": "ferry_direct",
                    "segments": [
                        {
                            "mode": "walk",
                            "description": f"Iskeleye yuru: {origin_label}",
                            "distance_m": round(float(walk_to["distance_m"])),
                            "duration_min": float(walk_to["duration_min"]),
                            "coords": walk_to["coords"],
                        },
                        {
                            "mode": "ferry",
                            "description": "Vapur hatti",
                            "route_code": "Vapur",
                            "from_stop": origin_label,
                            "to_stop": dest_label,
                            "distance_m": round(ferry_dist_m),
                            "duration_min": ferry_time,
                            "wait_min": 6.0,
                            "coords": [[float(o["lat"]), float(o["lon"])], [float(d["lat"]), float(d["lon"])]],
                            "stop_coords": [[float(o["lat"]), float(o["lon"])], [float(d["lat"]), float(d["lon"])]],
                        },
                        {
                            "mode": "walk",
                            "description": "Iskeleden hedefe yuru",
                            "distance_m": round(float(walk_from["distance_m"])),
                            "duration_min": float(walk_from["duration_min"]),
                            "coords": walk_from["coords"],
                        },
                    ],
                }
            )

    options.sort(key=lambda x: float(x.get("total_time_min", 10**9)))
    return options[:max_results]


def _transit_signature(opt: Dict) -> Tuple[str, str, int]:
    return (
        str(opt.get("transit_mode") or "bus"),
        str(opt.get("route_code") or ""),
        int(opt.get("transfer_count", 0) or 0),
    )


def _diversify_transit_options(transit_options: List[Dict], max_options: int = 8) -> List[Dict]:
    """
    Farkli tercih tiplerine hitap eden toplu tasima secenekleri sec.
    """
    if not transit_options:
        return []

    def _option_walk_m(opt: Dict) -> float:
        if opt.get("total_walk_m") is not None:
            return float(opt.get("total_walk_m", 0) or 0)
        return _sum_walk_distance_m(opt.get("segments") or [])

    def _option_walk_min(opt: Dict) -> float:
        return _sum_walk_duration_min(opt.get("segments") or [])

    def _effective_time(opt: Dict) -> float:
        total_time = float(opt.get("total_time_min", 10**9))
        walk_min = _option_walk_min(opt)
        walk_m = _option_walk_m(opt)
        penalty = walk_min * 0.35
        if walk_m > 1200:
            penalty += min(12.0, (walk_m - 1200.0) / 250.0)
        return total_time + penalty

    options = sorted(
        transit_options,
        key=lambda o: (
            _effective_time(o),
            int(o.get("transfer_count", 0) or 0),
            _option_walk_m(o),
            float(o.get("total_time_min", 10**9)),
        ),
    )

    selected: List[Dict] = []
    seen = set()
    route_usage: Dict[str, int] = {}
    bus_route_repeat_cap = 2

    def _count_mode(opt: Dict, mode_name: str) -> int:
        return sum(
            1 for seg in (opt.get("segments") or [])
            if str(seg.get("mode") or "").lower() == mode_name
        )

    def _option_bus_routes(opt: Dict) -> set[str]:
        routes: set[str] = set()
        for seg in (opt.get("segments") or []):
            if str(seg.get("mode") or "").lower() != "bus":
                continue
            code = str(seg.get("route_code") or "").strip().upper()
            if code:
                routes.add(code)

        # Segment bazli route_code yoksa route_code alanindan fallback topla.
        if not routes:
            raw_route_code = str(opt.get("route_code") or "").strip().upper()
            if raw_route_code:
                for part in re.split(r"->|\+|,|\s+", raw_route_code):
                    part = part.strip().upper()
                    if part and any(ch.isdigit() for ch in part):
                        routes.add(part)

        return routes

    def _can_pick_under_route_cap(opt: Dict) -> bool:
        routes = _option_bus_routes(opt)
        if not routes:
            return True
        return all(route_usage.get(route_code, 0) < bus_route_repeat_cap for route_code in routes)

    def _route_usage_score(opt: Dict) -> int:
        routes = _option_bus_routes(opt)
        if not routes:
            return 0
        return max(route_usage.get(route_code, 0) for route_code in routes)

    def _register_route_usage(opt: Dict) -> None:
        for route_code in _option_bus_routes(opt):
            route_usage[route_code] = route_usage.get(route_code, 0) + 1

    def _metrobus_simplicity_score(opt: Dict) -> Tuple[int, int]:
        # Daha sade metrobus onerisi: az ferry + az rail katmani.
        ferry_legs = _count_mode(opt, "ferry")
        rail_legs = _count_mode(opt, "rail")
        transfer_count = int(opt.get("transfer_count", 0) or 0)
        penalty = (ferry_legs * 6) + max(0, rail_legs - 1) + transfer_count
        return penalty, rail_legs

    def _pick(candidates: List[Dict], reason: str) -> None:
        # 1) Route cesitliligini koruyan secim.
        for item in candidates:
            sig = _transit_signature(item)
            if sig in seen:
                continue
            if not _can_pick_under_route_cap(item):
                continue
            cloned = dict(item)
            cloned["selection_reason"] = reason
            selected.append(cloned)
            seen.add(sig)
            _register_route_usage(cloned)
            return

        # 2) Baska secenek yoksa cap'i gevset, bos liste yaratma.
        for item in candidates:
            sig = _transit_signature(item)
            if sig in seen:
                continue
            cloned = dict(item)
            cloned["selection_reason"] = reason
            selected.append(cloned)
            seen.add(sig)
            _register_route_usage(cloned)
            return

    # En hizli
    _pick(options, "fastest")

    # En az aktarmali
    by_transfer = sorted(
        options,
        key=lambda o: (
            int(o.get("transfer_count", 0) or 0),
            _count_mode(o, "ferry"),
            _effective_time(o),
        ),
    )
    _pick(by_transfer, "least_transfer")

    # Dogrudan vapur secenegi (varsa listede mutlaka yer alsin)
    ferry_only = [
        o for o in options
        if str(o.get("transit_mode") or "") == "ferry"
    ]
    _pick(ferry_only, "ferry_direct")

    # Metro oncelikli
    metro_only = [o for o in options if str(o.get("transit_mode") or "") == "metro"]
    _pick(metro_only, "metro_preferred")

    # Metrobus (34*) iceren secenek varsa mutlaka goster.
    metrobus_opts = [
        o for o in options
        if any(
            str(seg.get("mode") or "") == "bus"
            and str(seg.get("route_code") or "").upper().startswith("34")
            for seg in (o.get("segments") or [])
        )
    ]
    metrobus_opts = sorted(
        metrobus_opts,
        key=lambda o: (
            _metrobus_simplicity_score(o),
            float(o.get("total_time_min", 10**9)),
            float(o.get("total_walk_m", 10**9)),
        ),
    )
    _pick(metrobus_opts, "metrobus_preferred")

    # Yurume az
    by_walk = sorted(
        options,
        key=lambda o: (
            _option_walk_m(o),
            _effective_time(o),
        ),
    )
    _pick(by_walk, "low_walk")

    remaining = sorted(
        options,
        key=lambda o: (
            _route_usage_score(o),
            _effective_time(o),
            int(o.get("transfer_count", 0) or 0),
            float(o.get("total_time_min", 10**9)),
        ),
    )

    # Once ayni hatti tekrar tekrar basmadan doldur.
    for item in remaining:
        if len(selected) >= max_options:
            break
        sig = _transit_signature(item)
        if sig in seen:
            continue
        if not _can_pick_under_route_cap(item):
            continue
        cloned = dict(item)
        cloned["selection_reason"] = "alternative"
        selected.append(cloned)
        seen.add(sig)
        _register_route_usage(cloned)

    # Hala yer varsa, cap'i gevsetip alternatifleri tamamla.
    for item in remaining:
        if len(selected) >= max_options:
            break
        sig = _transit_signature(item)
        if sig in seen:
            continue
        cloned = dict(item)
        cloned["selection_reason"] = "alternative"
        selected.append(cloned)
        seen.add(sig)
        _register_route_usage(cloned)

    return selected[:max_options]


def _is_reasonable_transit_time(total_time_min: float, direct_walk_min: float, with_transfer: bool = False) -> bool:
    """
    Transit suresini asiri kotu secenekleri elemek icin kontrol eder.
    Direkt yuruyuse gore cok uzun kalani filtreler ama fazla katı davranmaz.
    """
    multiplier = 2.40 if with_transfer else 1.85
    return total_time_min <= (direct_walk_min * multiplier)


def _is_reasonable_transit_distance(total_distance_m: float, direct_walk_m: float, with_transfer: bool = False) -> bool:
    """
    Transit toplam mesafesi, direkt mesafeye gore asiri sapmasin.
    """
    multiplier = 6.0 if with_transfer else 4.2
    return total_distance_m <= (direct_walk_m * multiplier)


def _normalize_allowed_modes(allowed_modes: Optional[List[str]]) -> set:
    """
    Kullanici tarafindan gelen mod listesini normalize eder.
    Bos/None durumda tum modlari acik kabul eder.
    """
    if not allowed_modes:
        return set(USER_TRANSIT_MODES)

    normalized = set()
    for mode in allowed_modes:
        m = str(mode or "").strip().lower()
        if m in USER_TRANSIT_MODES:
            normalized.add(m)
    return normalized if normalized else set(USER_TRANSIT_MODES)


def _is_metrobus_code(route_code: str) -> bool:
    code = str(route_code or "").strip().upper()
    return bool(re.match(r"^34[A-Z0-9]*$", code))


def _is_rail_route_code(route_code: str) -> bool:
    """
    Otobus olmayan rayli sistem kodlarini kabaca ayirt et.
    Not: Istanbul otobus kodlari genelde sayi/harf kombinasyonudur (34, 146T vb.),
    M/T/F ile baslayan kisa kodlar rayli sistem tarafinda kullanilir.
    """
    code = str(route_code or "").strip().upper()
    if not code:
        return False
    if code in {"MARMARAY"}:
        return True
    return bool(re.match(r"^(M\d+[A-Z]?|T\d+[A-Z]?|F\d+[A-Z]?|TF\d+[A-Z]?|B\d+[A-Z]?|U\d+[A-Z]?|H\d+[A-Z]?)$", code))


def _option_user_modes(option: Dict) -> set:
    """
    Bir transit seceneginin gercekte hangi ulasim tiplerini kullandigini cikartir.
    """
    modes = set()
    segments = option.get("segments") or []
    for seg in segments:
        seg_mode = str(seg.get("mode") or "").lower()
        if seg_mode == "rail":
            modes.add("metro")
        elif seg_mode == "ferry":
            modes.add("ferry")
        elif seg_mode == "bus":
            if _is_metrobus_code(str(seg.get("route_code") or "")):
                modes.add("metrobus")
            else:
                modes.add("bus")

    # Segment bazli tespit yoksa transit_mode alanindan minimum fallback.
    if modes:
        return modes
    transit_mode = str(option.get("transit_mode") or "").lower()
    if transit_mode == "metro":
        return {"metro"}
    if transit_mode == "ferry":
        return {"ferry"}
    if transit_mode == "bus":
        route_code = str(option.get("route_code") or "")
        return {"metrobus"} if _is_metrobus_code(route_code) else {"bus"}
    if transit_mode == "mixed":
        return {"bus", "metro"}
    return set()


def _is_absurd_transit_option(
    option: Dict,
    *,
    origin_lon: float,
    dest_lon: float,
    direct_walk_min: float,
    direct_walk_m: float,
) -> bool:
    """
    Bariz anlamsiz toplu tasima turlarini (uzun detour + zayif kazanc) eler.
    """
    total_time = float(option.get("total_time_min", 10**9) or 10**9)
    total_distance = float(option.get("total_distance_m", 0) or 0)
    transfer_count = int(option.get("transfer_count", 0) or 0)
    if total_time <= 0 or total_distance <= 0:
        return True

    has_ferry = any(
        str(seg.get("mode") or "").lower() == "ferry"
        for seg in (option.get("segments") or [])
    )
    same_side = (
        _bosphorus_side(float(origin_lon)) != 0
        and _bosphorus_side(float(origin_lon)) == _bosphorus_side(float(dest_lon))
    )
    saved_min = float(direct_walk_min) - total_time
    detour_ratio = total_distance / max(1.0, float(direct_walk_m))

    # Kisa/orta mesafede asiri karmasik transfer turlari.
    if direct_walk_min <= 120 and transfer_count >= 3 and detour_ratio >= 2.4 and saved_min < 28:
        return True

    # Ayni yakada vapurlu rota sadece ciddi fayda veriyorsa kalsin.
    if has_ferry and same_side and detour_ratio >= 1.8 and saved_min < 24:
        return True

    # Vapur + coklu aktarma + neredeyse yurume suresine yakin rota.
    if has_ferry and transfer_count >= 2 and total_time > (direct_walk_min * 0.78) and detour_ratio >= 2.0:
        return True

    return False


def _find_one_transfer_candidates(origin_stop_code: int, dest_stop_code: int, limit: int = 30) -> List[Dict]:
    """
    Tek aktarmali secenekler icin (hat A -> transfer duragi -> hat B) adaylarini bulur.
    """
    origin_routes = _get_routes_at_stop(origin_stop_code)
    dest_routes = _get_routes_at_stop(dest_stop_code)

    if not origin_routes or not dest_routes:
        return []

    # IN (...) parametreleri
    ph_origin = ",".join(["?"] * len(origin_routes))
    ph_dest = ",".join(["?"] * len(dest_routes))

    query = f"""
        SELECT DISTINCT
            a.route_code AS route_a,
            b.route_code AS route_b,
            a.stop_code AS transfer_stop_code,
            s.name AS transfer_stop_name,
            s.lat AS transfer_lat,
            s.lon AS transfer_lon
        FROM route_stops a
        JOIN route_stops b ON a.stop_code = b.stop_code
        LEFT JOIN stops s ON s.code = a.stop_code
        WHERE a.route_code IN ({ph_origin})
          AND b.route_code IN ({ph_dest})
          AND a.route_code != b.route_code
          AND a.stop_code != ?
          AND a.stop_code != ?
        LIMIT ?
    """

    params = origin_routes + dest_routes + [origin_stop_code, dest_stop_code, limit]

    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def _get_route_stop_candidates_after(route_code: str, from_stop_code: int, limit: int = 24) -> List[Dict]:
    """
    Verilen hatta, baslangic duragindan sonra gelebilecek aday duraklari dondurur.
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT rs.stop_code, rs.stop_order, rs.direction, s.name, s.lat, s.lon
        FROM route_stops rs
        LEFT JOIN stops s ON s.code = rs.stop_code
        WHERE rs.route_code = ?
        ORDER BY rs.direction, rs.stop_order
        """,
        (route_code,),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not rows:
        return []

    by_dir: Dict[str, List[Dict]] = defaultdict(list)
    for row in rows:
        by_dir[str(row.get("direction") or "")].append(row)

    out: List[Dict] = []
    seen: set[int] = set()
    for _, items in by_dir.items():
        start_idx = None
        for i, r in enumerate(items):
            if int(r.get("stop_code") or -1) == int(from_stop_code):
                start_idx = i
                break
        if start_idx is None:
            continue
        # Her 2-3 durakta bir aday al; cok fazla secenegi patlatmasin.
        for j in range(start_idx + 1, len(items), 3):
            cand = items[j]
            code = int(cand.get("stop_code") or -1)
            if code <= 0 or code in seen:
                continue
            if cand.get("lat") is None or cand.get("lon") is None:
                continue
            seen.add(code)
            out.append(cand)
            if len(out) >= limit:
                return out
    return out[:limit]


def _get_route_stop_candidates_before(
    route_code: str,
    to_stop_code: int,
    limit: int = 24,
    lookback_window: int = 24,
) -> List[Dict]:
    """
    Verilen hatta, hedef duraktan once gelebilecek aday duraklari dondurur.
    (metro/tram -> bus/matrobus karmasi icin)
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT rs.stop_code, rs.stop_order, rs.direction, s.name, s.lat, s.lon
        FROM route_stops rs
        LEFT JOIN stops s ON s.code = rs.stop_code
        WHERE rs.route_code = ?
        ORDER BY rs.direction, rs.stop_order
        """,
        (route_code,),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not rows:
        return []

    by_dir: Dict[str, List[Dict]] = defaultdict(list)
    for row in rows:
        by_dir[str(row.get("direction") or "")].append(row)

    out: List[Dict] = []
    seen: set[int] = set()
    for _, items in by_dir.items():
        end_idx = None
        for i, r in enumerate(items):
            if int(r.get("stop_code") or -1) == int(to_stop_code):
                end_idx = i
                break
        if end_idx is None or end_idx <= 0:
            continue
        # Hedefe gelirken onceki duraklardan ornekle (hedefe yakin olanlari oncele).
        start = max(0, end_idx - max(8, int(lookback_window)))
        for j in range(end_idx - 1, start - 1, -2):
            cand = items[j]
            code = int(cand.get("stop_code") or -1)
            if code <= 0 or code in seen:
                continue
            if cand.get("lat") is None or cand.get("lon") is None:
                continue
            seen.add(code)
            out.append(cand)
            if len(out) >= limit:
                return out
    return out[:limit]


def _build_bus_metro_mixed_options(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    direct_walk_min: float,
    direct_walk_m: float,
    max_results: int = 3,
) -> List[Dict]:
    """
    Karma secenekler: otobus + metro (tek/çok aktarmalı metro bacağı dahil).
    """
    mixed: List[Dict] = []
    metro_leg_cache: Dict[int, Optional[Dict]] = {}
    started = _time.time()
    budget_sec = 2.5
    target_pool = max(8, max_results * 6)
    max_walk_to_stop_m = _effective_walk_to_stop_limit_m(direct_walk_m)

    origin_stops: List[Dict] = []
    for radius in [700, 1100, 1600]:
        origin_stops = _cached_get_stops_in_area(origin_lat, origin_lon, radius)
        origin_stops = sorted(origin_stops, key=lambda s: float(s.get("distance_m", 10**9)))
        origin_stops = [s for s in origin_stops if float(s.get("distance_m", 10**9)) <= max_walk_to_stop_m][:8]
        if origin_stops:
            break
    if not origin_stops:
        return []

    for o_stop in origin_stops:
        if (_time.time() - started) > budget_sec or len(mixed) >= target_pool:
            break
        routes_at_origin = [
            r for r in _get_routes_at_stop(int(o_stop["code"]))
            if not _is_rail_route_code(str(r))
        ][:5]
        if not routes_at_origin:
            continue

        for route_code in routes_at_origin:
            if (_time.time() - started) > budget_sec or len(mixed) >= target_pool:
                break
            is_metrobus = _is_metrobus_code(route_code)
            transfer_stop_candidates = _get_route_stop_candidates_after(route_code, int(o_stop["code"]), limit=8)
            if not transfer_stop_candidates:
                continue

            for t_stop in transfer_stop_candidates:
                if (_time.time() - started) > budget_sec or len(mixed) >= target_pool:
                    break
                t_lat = float(t_stop["lat"])
                t_lon = float(t_stop["lon"])

                # Otobus duragindan metroyla baglanabilecek istasyonlar
                near_metro = _cached_get_metro_stations_in_area(t_lat, t_lon, 500)[:2]
                near_metro = sorted(near_metro, key=lambda s: float(s.get("distance_m", 10**9)))[:2]
                if not near_metro:
                    continue

                # Otobus bacağı
                bus_stop_coords = _get_route_stop_coords(route_code, int(o_stop["code"]), int(t_stop["stop_code"]))
                if len(bus_stop_coords) < 2:
                    continue
                bus_road_coords = _get_bus_road_coords(bus_stop_coords)
                bus_distance_m = _path_distance_m(bus_stop_coords)
                bus_time_min = _bus_travel_time_minutes(bus_distance_m / 1000.0)
                if is_metrobus and bus_time_min < 4.0:
                    # Metrobusu tek duraklik "son dokunus" olarak kullanmak
                    # genelde anlamsiz ve kullanici acisindan kotu bir secenek oluyor.
                    continue

                walk_to_bus_seg = _build_walk_leg(
                    origin_lat, origin_lon, float(o_stop["lat"]), float(o_stop["lon"]),
                    max_distance_m=900,
                    allow_fallback_if_short=False,
                )
                if not walk_to_bus_seg:
                    continue
                walk_to_bus_min = float(walk_to_bus_seg["duration_min"])
                walk_to_bus_coords = walk_to_bus_seg["coords"]

                for metro_station in near_metro:
                    if (_time.time() - started) > budget_sec or len(mixed) >= target_pool:
                        break
                    m_lat = float(metro_station["lat"])
                    m_lon = float(metro_station["lon"])
                    transfer_walk_seg = _build_walk_leg(
                        t_lat, t_lon, m_lat, m_lon,
                        max_distance_m=450,
                        allow_fallback_if_short=False,
                    )
                    if not transfer_walk_seg:
                        continue
                    transfer_walk_coords = transfer_walk_seg["coords"]
                    transfer_walk_m = float(transfer_walk_seg["distance_m"])
                    transfer_walk_min = float(transfer_walk_seg["duration_min"])

                    # Metro bacağı (transfer istasyonundan hedefe)
                    local_direct_m = _haversine_distance(m_lat, m_lon, dest_lat, dest_lon)
                    local_direct_min = _walking_time_minutes(local_direct_m)
                    station_id = int(metro_station.get("id") or 0)
                    if station_id in metro_leg_cache:
                        metro_leg = metro_leg_cache[station_id]
                    else:
                        metro_leg = _build_graph_metro_option(
                            origin_lat=m_lat,
                            origin_lon=m_lon,
                            dest_lat=dest_lat,
                            dest_lon=dest_lon,
                            direct_walk_min=local_direct_min,
                            direct_walk_m=local_direct_m,
                        )
                        metro_leg_cache[station_id] = metro_leg
                    if not metro_leg:
                        continue

                    metro_segments = list(metro_leg.get("segments") or [])
                    # Metro başlangıcındaki "istasyona yürü" segmenti çok kısa/tekrarlıysa çıkar.
                    if metro_segments and metro_segments[0].get("mode") == "walk":
                        if float(metro_segments[0].get("duration_min", 0) or 0) <= 1.0:
                            metro_segments = metro_segments[1:]

                    total_time_min = (
                        walk_to_bus_min
                        + AVG_BUS_WAIT_MIN
                        + bus_time_min
                        + transfer_walk_min
                        + float(metro_leg.get("total_time_min", 0) or 0)
                    )
                    if total_time_min > max(direct_walk_min * 2.8, 130):
                        continue

                    total_distance_m = (
                        float(walk_to_bus_seg["distance_m"])
                        + float(bus_distance_m)
                        + float(transfer_walk_m)
                        + float(metro_leg.get("total_distance_m", 0) or 0)
                    )

                    mix_route_code = f"{route_code}->{metro_leg.get('route_code','Metro')}"
                    mix_route_name = f"{route_code} + {metro_leg.get('route_name','Metro')}"
                    key = (str(route_code), str(metro_leg.get("route_code", "")))

                    segments = [
                        {
                            "mode": "walk",
                            "description": f"Duraga yuru: {o_stop['name']}",
                            "distance_m": round(float(walk_to_bus_seg["distance_m"])),
                            "duration_min": walk_to_bus_min,
                            "coords": walk_to_bus_coords,
                        },
                        {
                            "mode": "bus",
                            "description": f"{route_code} hatti",
                            "route_code": route_code,
                            "from_stop": o_stop["name"],
                            "to_stop": t_stop.get("name") or "Transfer duragi",
                            "distance_m": round(bus_distance_m),
                            "duration_min": bus_time_min,
                            "wait_min": AVG_BUS_WAIT_MIN,
                            "coords": bus_road_coords,
                            "stop_coords": bus_stop_coords,
                        },
                        {
                            "mode": "walk",
                            "description": f"Metroya gecis: {metro_station.get('description') or metro_station.get('name') or ''}",
                            "distance_m": round(transfer_walk_m),
                            "duration_min": transfer_walk_min,
                            "coords": transfer_walk_coords,
                        },
                    ]
                    segments.extend(metro_segments)

                    mixed.append(
                        {
                            "type": "transit",
                            "transit_mode": "mixed",
                            "icon": "transfer",
                            "name": f"{route_code} + {metro_leg.get('route_name', 'Metro')} Aktarmali",
                            "description": f"{o_stop['name']} -> {t_stop.get('name') or ''} -> {metro_station.get('description') or metro_station.get('name') or ''}",
                            "total_time_min": round(total_time_min, 1),
                            "total_distance_m": round(total_distance_m),
                            "total_walk_m": round(
                                float(walk_to_bus_seg["distance_m"])
                                + float(transfer_walk_m)
                                + float(metro_leg.get("total_walk_m", 0) or 0)
                            ),
                            "route_code": mix_route_code,
                            "route_name": mix_route_name,
                            "transfer_count": 1 + int(metro_leg.get("transfer_count", 0) or 0),
                            "selection_reason": "multimodal_mix",
                            "segments": segments,
                            "_dedupe_key": key,
                            "_transfer_walk_m": transfer_walk_m,
                        }
                    )
                    if len(mixed) >= target_pool:
                        break

    best_by_key: Dict[Tuple[str, str], Dict] = {}
    for opt in mixed:
        dedupe_key = tuple(opt.get("_dedupe_key") or ())
        if not dedupe_key:
            dedupe_key = (str(opt.get("route_code") or ""), str(opt.get("route_name") or ""))
        old = best_by_key.get(dedupe_key)
        score = (
            float(opt.get("total_time_min", 10**9)),
            float(opt.get("_transfer_walk_m", 10**9)),
            float(opt.get("total_distance_m", 10**9)),
        )
        if old is None:
            best_by_key[dedupe_key] = opt
            continue
        old_score = (
            float(old.get("total_time_min", 10**9)),
            float(old.get("_transfer_walk_m", 10**9)),
            float(old.get("total_distance_m", 10**9)),
        )
        if score < old_score:
            best_by_key[dedupe_key] = opt

    merged = list(best_by_key.values())
    for opt in merged:
        opt.pop("_dedupe_key", None)
        opt.pop("_transfer_walk_m", None)

    merged.sort(key=lambda x: float(x.get("total_time_min", 10**9)))
    keep_n = max(24, max_results * 5)
    return merged[:keep_n]


def _build_metro_bus_mixed_options(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    direct_walk_min: float,
    direct_walk_m: float,
    max_results: int = 3,
) -> List[Dict]:
    """
    Karma secenekler: metro/tram + bus/metrobus.
    Ozellikle T1 + metrobus gibi senaryolari yakalamak icin.
    """
    mixed: List[Dict] = []
    metro_leg_cache: Dict[int, List[Dict]] = {}
    started = _time.time()
    budget_sec = 35.0
    target_pool = max(10, max_results * 8)
    max_walk_to_stop_m = _effective_walk_to_stop_limit_m(direct_walk_m)

    # Hedefe yakin inis duraklari
    dest_stops: List[Dict] = []
    for radius in [700, 1100, 1600]:
        dest_stops = _cached_get_stops_in_area(dest_lat, dest_lon, radius)
        dest_stops = sorted(dest_stops, key=lambda s: float(s.get("distance_m", 10**9)))
        dest_stops = [s for s in dest_stops if float(s.get("distance_m", 10**9)) <= max_walk_to_stop_m][:10]
        if dest_stops:
            break
    if not dest_stops:
        return []

    # Metrobus (34*) barindiran hedef duraklari one al; aksi halde erken havuz dolumunda
    # iyi metrobus kombinasyonlari (ornek T1 + 34) hic degerlendirilmeden elenebiliyor.
    def _dest_has_metrobus(stop: Dict) -> bool:
        try:
            routes = _get_routes_at_stop(int(stop.get("code", 0)))
        except Exception:
            return False
        return any(_is_metrobus_code(str(r)) for r in routes)

    dest_stops = sorted(
        dest_stops,
        key=lambda s: (
            0 if _dest_has_metrobus(s) else 1,
            float(s.get("distance_m", 10**9)),
        ),
    )

    for d_stop in dest_stops:
        if (_time.time() - started) > budget_sec:
            break
        routes_to_dest = _get_routes_at_stop(int(d_stop["code"]))
        if not routes_to_dest:
            continue
        routes_to_dest = [r for r in routes_to_dest if not _is_rail_route_code(str(r))]
        if not routes_to_dest:
            continue
        # Metrobusu oncele (34*), sonra diger bus hatlari.
        routes_to_dest = sorted(
            routes_to_dest,
            key=lambda r: (0 if str(r).startswith("34") else 1, str(r))
        )[:6]

        for route_code in routes_to_dest:
            if (_time.time() - started) > budget_sec:
                break
            is_metrobus = _is_metrobus_code(route_code)
            board_candidates = _get_route_stop_candidates_before(
                route_code,
                int(d_stop["code"]),
                limit=24 if is_metrobus else 10,
                lookback_window=180 if is_metrobus else 24,
            )
            if not board_candidates:
                continue

            for b_stop in board_candidates:
                if (_time.time() - started) > budget_sec:
                    break
                b_lat = float(b_stop["lat"])
                b_lon = float(b_stop["lon"])

                near_metro: List[Dict] = []
                near_radii = [900, 1500, 2400] if is_metrobus else [700, 1200, 1800]
                near_limit = 10 if is_metrobus else 4
                for mr in near_radii:
                    near_metro = _cached_get_metro_stations_in_area(b_lat, b_lon, mr)
                    near_metro = sorted(
                        near_metro,
                        key=lambda s: float(s.get("distance_m", 10**9))
                    )[:near_limit]
                    if near_metro:
                        break
                if not near_metro:
                    continue

                bus_stop_coords = _get_route_stop_coords(route_code, int(b_stop["stop_code"]), int(d_stop["code"]))
                if len(bus_stop_coords) < 2:
                    continue
                bus_road_coords = _get_bus_road_coords(bus_stop_coords)
                bus_distance_m = _path_distance_m(bus_stop_coords)
                bus_time_min = _bus_travel_time_minutes(bus_distance_m / 1000.0)
                if is_metrobus and bus_time_min < 4.0:
                    # Metrobusu 1-2 duraklik "geri toplama" olarak eklemek
                    # rotayi gereksiz karmasiklastiriyor.
                    continue

                walk_from_bus_seg = _build_walk_leg(
                    float(d_stop["lat"]), float(d_stop["lon"]), dest_lat, dest_lon,
                    max_distance_m=2400,
                    allow_fallback_if_short=True,
                    fallback_max_m=1400,
                    max_ratio=8.0,
                )
                if not walk_from_bus_seg:
                    continue
                walk_from_bus_min = float(walk_from_bus_seg["duration_min"])
                walk_from_bus_coords = walk_from_bus_seg["coords"]

                for metro_station in near_metro:
                    if (_time.time() - started) > budget_sec:
                        break
                    m_lat = float(metro_station["lat"])
                    m_lon = float(metro_station["lon"])
                    transfer_walk_seg = _build_walk_leg(
                        m_lat, m_lon, b_lat, b_lon,
                        max_distance_m=1800,
                        allow_fallback_if_short=True,
                        fallback_max_m=1500,
                        max_ratio=8.0,
                    )
                    if not transfer_walk_seg:
                        continue
                    transfer_walk_coords = transfer_walk_seg["coords"]
                    transfer_walk_m = float(transfer_walk_seg["distance_m"])
                    transfer_walk_min = float(transfer_walk_seg["duration_min"])

                    # Metro istasyonundan hedefe yaya erisimi zaten iyi ise,
                    # ekstra bus/metrobus "geri-donus" bacagini ekleme.
                    walk_from_metro_direct = _build_walk_leg(
                        m_lat, m_lon, dest_lat, dest_lon,
                        max_distance_m=2200,
                        allow_fallback_if_short=True,
                        fallback_max_m=1300,
                        max_ratio=8.0,
                    )
                    if walk_from_metro_direct:
                        direct_metro_to_dest_min = float(walk_from_metro_direct["duration_min"])
                        with_bus_tail_min = transfer_walk_min + AVG_BUS_WAIT_MIN + bus_time_min + walk_from_bus_min
                        # Bus bacagi yaya erisimden anlamli kazanctan yoksunsa ele.
                        if with_bus_tail_min >= (direct_metro_to_dest_min - 1.5):
                            continue

                    # Metro bacagi (baslangictan transfer istasyonuna)
                    local_direct_m = _haversine_distance(origin_lat, origin_lon, m_lat, m_lon)
                    local_direct_min = _walking_time_minutes(local_direct_m)
                    station_id = int(metro_station.get("id") or 0)
                    if station_id in metro_leg_cache:
                        metro_leg_candidates = metro_leg_cache[station_id]
                    else:
                        metro_leg_candidates: List[Dict] = []
                        metro_candidates = _build_metro_options(
                            origin_lat=origin_lat,
                            origin_lon=origin_lon,
                            dest_lat=m_lat,
                            dest_lon=m_lon,
                            direct_walk_min=local_direct_min,
                            direct_walk_m=local_direct_m,
                            max_results=12 if is_metrobus else 5,
                        )
                        if metro_candidates:
                            if is_metrobus:
                                no_ferry = [
                                    c for c in metro_candidates
                                    if not any(str(s.get("mode") or "").lower() == "ferry" for s in (c.get("segments") or []))
                                ]
                                pool = no_ferry if no_ferry else metro_candidates
                                pool = sorted(
                                    pool,
                                    key=lambda c: (
                                        sum(
                                            1 for s in (c.get("segments") or [])
                                            if str(s.get("mode") or "").lower() == "rail"
                                        ),
                                        int(c.get("transfer_count", 0) or 0),
                                        float(c.get("total_time_min", 10**9)),
                                    ),
                                )
                                seen_route_codes = set()
                                for cand in pool:
                                    cand_route_code = str(cand.get("route_code") or "")
                                    if cand_route_code in seen_route_codes:
                                        continue
                                    metro_leg_candidates.append(cand)
                                    seen_route_codes.add(cand_route_code)
                                    if len(metro_leg_candidates) >= 3:
                                        break
                            else:
                                metro_leg_candidates = [metro_candidates[0]]

                        if not metro_leg_candidates:
                            fallback_metro_leg = _build_graph_metro_option(
                                origin_lat=origin_lat,
                                origin_lon=origin_lon,
                                dest_lat=m_lat,
                                dest_lon=m_lon,
                                direct_walk_min=local_direct_min,
                                direct_walk_m=local_direct_m,
                            )
                            if fallback_metro_leg:
                                metro_leg_candidates = [fallback_metro_leg]
                        metro_leg_cache[station_id] = metro_leg_candidates

                    for metro_leg in metro_leg_candidates:
                        metro_segments = list(metro_leg.get("segments") or [])
                        if is_metrobus and any(str(s.get("mode") or "").lower() == "ferry" for s in metro_segments):
                            # Metrobus odakli secenekte metroyu vapurla dolastirma:
                            # kullaniciya daha tutarli (karasal) alternatifler sun.
                            continue
                        # Metro sonundaki "hedefe yuru" bu akista transfer yuruyusu ile degisecek.
                        if metro_segments and metro_segments[-1].get("mode") == "walk":
                            metro_segments = metro_segments[:-1]

                        total_time_min = (
                            float(metro_leg.get("total_time_min", 0) or 0)
                            + transfer_walk_min
                            + AVG_BUS_WAIT_MIN
                            + bus_time_min
                            + walk_from_bus_min
                        )
                        if total_time_min > max(direct_walk_min * 2.8, 130):
                            continue

                        total_distance_m = (
                            float(metro_leg.get("total_distance_m", 0) or 0)
                            + float(transfer_walk_m)
                            + float(bus_distance_m)
                            + float(walk_from_bus_seg["distance_m"])
                        )
                        # Metrobus alternatifleri tamamen filtrelenmesin;
                        # hizli olmasa bile kullaniciya secenek olarak sunulsun.

                        mix_route_code = f"{metro_leg.get('route_code','Metro')}->{route_code}"
                        mix_route_name = f"{metro_leg.get('route_name','Metro')} + {route_code}"
                        key = (str(metro_leg.get("route_code", "")), str(route_code))

                        segments = []
                        segments.extend(metro_segments)
                        segments.append(
                            {
                                "mode": "walk",
                                "description": f"Metrobuse gecis: {b_stop.get('name') or 'Durak'}",
                                "distance_m": round(transfer_walk_m),
                                "duration_min": transfer_walk_min,
                                "coords": transfer_walk_coords,
                            }
                        )
                        segments.append(
                            {
                                "mode": "bus",
                                "description": f"{route_code} hatti",
                                "route_code": route_code,
                                "from_stop": b_stop.get("name") or "Durak",
                                "to_stop": d_stop.get("name") or "Durak",
                                "distance_m": round(bus_distance_m),
                                "duration_min": bus_time_min,
                                "wait_min": AVG_BUS_WAIT_MIN,
                                "coords": bus_road_coords,
                                "stop_coords": bus_stop_coords,
                            }
                        )
                        segments.append(
                            {
                                "mode": "walk",
                                "description": "Duraktan hedefe yuru",
                                "distance_m": round(float(walk_from_bus_seg["distance_m"])),
                                "duration_min": walk_from_bus_min,
                                "coords": walk_from_bus_coords,
                            }
                        )

                        mixed.append(
                            {
                                "type": "transit",
                                "transit_mode": "mixed",
                                "icon": "transfer",
                                "name": f"{metro_leg.get('route_name', 'Metro')} + {route_code} Aktarmali",
                                "description": f"{metro_station.get('description') or metro_station.get('name') or ''} -> {b_stop.get('name') or ''} -> {d_stop.get('name') or ''}",
                                "total_time_min": round(total_time_min, 1),
                                "total_distance_m": round(total_distance_m),
                                "total_walk_m": round(
                                    float(metro_leg.get("total_walk_m", 0) or 0)
                                    + float(transfer_walk_m)
                                    + float(walk_from_bus_seg["distance_m"])
                                ),
                                "route_code": mix_route_code,
                                "route_name": mix_route_name,
                                "transfer_count": 1 + int(metro_leg.get("transfer_count", 0) or 0),
                                "selection_reason": "multimodal_mix",
                                "segments": segments,
                                "_dedupe_key": key,
                                "_transfer_walk_m": transfer_walk_m,
                            }
                        )
                        continue

    best_by_key: Dict[Tuple[str, str], Dict] = {}
    for opt in mixed:
        dedupe_key = tuple(opt.get("_dedupe_key") or ())
        if not dedupe_key:
            dedupe_key = (str(opt.get("route_code") or ""), str(opt.get("route_name") or ""))
        old = best_by_key.get(dedupe_key)
        score = (
            float(opt.get("total_time_min", 10**9)),
            float(opt.get("_transfer_walk_m", 10**9)),
            float(opt.get("total_distance_m", 10**9)),
        )
        if old is None:
            best_by_key[dedupe_key] = opt
            continue
        old_score = (
            float(old.get("total_time_min", 10**9)),
            float(old.get("_transfer_walk_m", 10**9)),
            float(old.get("total_distance_m", 10**9)),
        )
        if score < old_score:
            best_by_key[dedupe_key] = opt

    merged = list(best_by_key.values())
    for opt in merged:
        opt.pop("_dedupe_key", None)
        opt.pop("_transfer_walk_m", None)

    merged.sort(key=lambda x: float(x.get("total_time_min", 10**9)))
    keep_n = max(24, max_results * 6)
    return merged[:keep_n]


# ============================================================================
# MULTIMODAL ROTA HESAPLAMA
# ============================================================================

def find_transit_routes(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    max_results: int = 8,
    allowed_modes: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Iki nokta arasi toplu tasima seceneklerini bulur.

    Algoritma:
    1. Baslangic noktasina yakin duraklari bul
    2. Bitis noktasina yakin duraklari bul
    3. Ortak hat ara (artan yaricaplarla)
    4. Her secenegin toplam suresini hesapla
    5. En iyi secenekleri dondur
    """

    max_transit_options = max(1, int(ROUTE_CONFIG.get("MULTIMODAL_MAX_TRANSIT_OPTIONS", max_results)))

    # Direkt yurume mesafesi (OSRM foot bazli)
    direct_walk_m, direct_walk_min, walking_road_coords = _direct_walk_metrics(
        origin_lat, origin_lon, dest_lat, dest_lon
    )
    max_walk_to_stop_m = _effective_walk_to_stop_limit_m(direct_walk_m)
    allowed_user_modes = _normalize_allowed_modes(allowed_modes)
    walking_option = {
        "type": "walking",
        "icon": "walking",
        "name": "Yuruyus",
        "description": f"Direkt yurume ({round(direct_walk_m)}m)",
        "total_time_min": round(direct_walk_min, 1),
        "total_distance_m": round(direct_walk_m),
        "segments": [{
            "mode": "walk",
            "description": "Direkt yurume",
            "distance_m": round(direct_walk_m),
            "duration_min": round(direct_walk_min, 1),
            "coords": walking_road_coords,
        }],
    }

    # Transit cizimini/senaryosunu yalnizca vapur istendiginde bus/metro akisiyla karistirma.
    if allowed_user_modes == {"ferry"}:
        ferry_options = _build_ferry_only_options(
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            dest_lat=dest_lat,
            dest_lon=dest_lon,
            direct_walk_min=direct_walk_min,
            max_results=max_results,
        )
        ferry_diverse = _diversify_transit_options(ferry_options, max_options=max_results)
        return [walking_option] + ferry_diverse

    # Artan yaricaplarla dene
    transit_options = []
    # En yakin 16 durak bazen dogru hatti kacirabiliyor (orta siradaki ama etkili bir durak gibi).
    # Kisa/orta mesafede aday havuzunu bir miktar genisletiyoruz.
    if direct_walk_m <= 12000:
        stop_pair_scan_limit = 28
    elif direct_walk_m <= 22000:
        stop_pair_scan_limit = 24
    else:
        stop_pair_scan_limit = 20

    for radius_idx, radius in enumerate(SEARCH_RADII):
        # Baslangica yakin duraklar
        origin_stops = _cached_get_stops_in_area(origin_lat, origin_lon, radius)
        # Hedefe yakin duraklar
        dest_stops = _cached_get_stops_in_area(dest_lat, dest_lon, radius)
        origin_stops = sorted(origin_stops, key=lambda s: float(s.get("distance_m", 10**9)))
        dest_stops = sorted(dest_stops, key=lambda s: float(s.get("distance_m", 10**9)))

        if not origin_stops or not dest_stops:
            continue

        # Her baslangic duragi icin
        for o_stop in origin_stops[:stop_pair_scan_limit]:
            if o_stop["distance_m"] > max_walk_to_stop_m:
                continue

            for d_stop in dest_stops[:stop_pair_scan_limit]:
                if d_stop["distance_m"] > max_walk_to_stop_m:
                    continue

                # Ortak hat bul
                connections = _cached_find_connecting_routes(o_stop["code"], d_stop["code"])

                for conn in connections:
                    walk_to_seg = _build_walk_leg(
                        origin_lat, origin_lon, float(o_stop["lat"]), float(o_stop["lon"]),
                        max_distance_m=1400,
                        allow_fallback_if_short=True,
                        fallback_max_m=1200,
                        max_ratio=6.0,
                    )
                    walk_from_seg = _build_walk_leg(
                        float(d_stop["lat"]), float(d_stop["lon"]), dest_lat, dest_lon,
                        max_distance_m=1700,
                        allow_fallback_if_short=True,
                        fallback_max_m=1300,
                        max_ratio=6.0,
                    )
                    if not walk_to_seg or not walk_from_seg:
                        continue
                    walk_to_stop = float(walk_to_seg["duration_min"])
                    wait_time = AVG_BUS_WAIT_MIN

                    direct_leg_stop_coords = _get_route_stop_coords(
                        conn.get("route_code", conn.get("code", "")),
                        o_stop["code"],
                        d_stop["code"],
                    )
                    # Yon/sira dogrulanamayan direkt bacaklari ele:
                    # fallback kus-ucusu hesapla devam etmek haritada yaniltici
                    # A->B->A benzeri artefaktlar uretebiliyor.
                    if len(direct_leg_stop_coords) < 2:
                        continue
                    bus_distance_m = _path_distance_m(direct_leg_stop_coords)
                    bus_time = _bus_travel_time_minutes(bus_distance_m / 1000)
                    walk_from_stop = float(walk_from_seg["duration_min"])

                    total_time = walk_to_stop + wait_time + bus_time + walk_from_stop
                    total_distance_m = float(walk_to_seg["distance_m"]) + bus_distance_m + float(walk_from_seg["distance_m"])

                    # Asiri kotu secenekleri ele
                    if (
                        _is_reasonable_transit_time(total_time, direct_walk_min)
                        and _is_reasonable_transit_distance(total_distance_m, direct_walk_m)
                    ):
                        transit_options.append({
                            "type": "transit",
                            "transit_mode": "bus",
                            "route_code": conn.get("route_code", conn.get("code", "")),
                            "route_name": conn.get("name", ""),
                            "origin_stop": {
                                "code": o_stop["code"],
                                "name": o_stop["name"],
                                "lat": o_stop["lat"],
                                "lon": o_stop["lon"],
                                "walk_distance_m": o_stop["distance_m"],
                                "walk_time_min": walk_to_stop,
                                "walk_coords": walk_to_seg["coords"],
                            },
                            "dest_stop": {
                                "code": d_stop["code"],
                                "name": d_stop["name"],
                                "lat": d_stop["lat"],
                                "lon": d_stop["lon"],
                                "walk_distance_m": d_stop["distance_m"],
                                "walk_time_min": walk_from_stop,
                                "walk_coords": walk_from_seg["coords"],
                            },
                            "wait_time_min": wait_time,
                            "bus_time_min": bus_time,
                            "total_time_min": round(total_time, 1),
                            "total_walk_m": float(walk_to_seg["distance_m"]) + float(walk_from_seg["distance_m"]),
                            "bus_distance_m": round(bus_distance_m),
                            "transfer_count": 0,
                        })

                # Tek aktarmali secenekler (A hatti -> transfer -> B hatti)
                transfer_candidates = _find_one_transfer_candidates(
                    o_stop["code"], d_stop["code"], limit=35
                )
                for candidate in transfer_candidates:
                    route_a = candidate.get("route_a")
                    route_b = candidate.get("route_b")
                    transfer_stop_code = candidate.get("transfer_stop_code")

                    if not route_a or not route_b or not transfer_stop_code:
                        continue

                    # Yon uygun mu? (origin -> transfer) ve (transfer -> dest)
                    leg1_stop_coords = _get_route_stop_coords(route_a, o_stop["code"], transfer_stop_code)
                    leg2_stop_coords = _get_route_stop_coords(route_b, transfer_stop_code, d_stop["code"])
                    if len(leg1_stop_coords) < 2 or len(leg2_stop_coords) < 2:
                        continue

                    transfer_lat = candidate.get("transfer_lat")
                    transfer_lon = candidate.get("transfer_lon")
                    if transfer_lat is None or transfer_lon is None:
                        continue

                    walk_to_seg = _build_walk_leg(
                        origin_lat, origin_lon, float(o_stop["lat"]), float(o_stop["lon"]),
                        max_distance_m=1400,
                        allow_fallback_if_short=True,
                        fallback_max_m=1200,
                        max_ratio=6.0,
                    )
                    walk_from_seg = _build_walk_leg(
                        float(d_stop["lat"]), float(d_stop["lon"]), dest_lat, dest_lon,
                        max_distance_m=1700,
                        allow_fallback_if_short=True,
                        fallback_max_m=1300,
                        max_ratio=6.0,
                    )
                    if not walk_to_seg or not walk_from_seg:
                        continue
                    walk_to_stop = float(walk_to_seg["duration_min"])
                    walk_from_stop = float(walk_from_seg["duration_min"])
                    wait1 = AVG_BUS_WAIT_MIN
                    wait2 = max(3, int(AVG_BUS_WAIT_MIN * 0.8))

                    bus1_distance_m = _path_distance_m(leg1_stop_coords)
                    bus2_distance_m = _path_distance_m(leg2_stop_coords)
                    bus1_time = _bus_travel_time_minutes(bus1_distance_m / 1000)
                    bus2_time = _bus_travel_time_minutes(bus2_distance_m / 1000)

                    total_time = walk_to_stop + wait1 + bus1_time + wait2 + bus2_time + walk_from_stop
                    total_distance_m = float(walk_to_seg["distance_m"]) + bus1_distance_m + bus2_distance_m + float(walk_from_seg["distance_m"])
                    if (
                        not _is_reasonable_transit_time(total_time, direct_walk_min, with_transfer=True)
                        or not _is_reasonable_transit_distance(total_distance_m, direct_walk_m, with_transfer=True)
                    ):
                        continue

                    route_a_info = _cached_get_route_info(route_a) or {}
                    route_b_info = _cached_get_route_info(route_b) or {}

                    transit_options.append({
                        "type": "transit_transfer",
                        "transit_mode": "bus",
                        "route_code": f"{route_a}->{route_b}",
                        "route_codes": [route_a, route_b],
                        "route_name": f"{route_a_info.get('name', route_a)} + {route_b_info.get('name', route_b)}",
                        "origin_stop": {
                            "code": o_stop["code"],
                            "name": o_stop["name"],
                            "lat": o_stop["lat"],
                            "lon": o_stop["lon"],
                                "walk_distance_m": o_stop["distance_m"],
                                "walk_time_min": walk_to_stop,
                                "walk_coords": walk_to_seg["coords"],
                            },
                        "transfer_stop": {
                            "code": transfer_stop_code,
                            "name": candidate.get("transfer_stop_name", "Transfer"),
                            "lat": transfer_lat,
                            "lon": transfer_lon,
                        },
                        "dest_stop": {
                            "code": d_stop["code"],
                            "name": d_stop["name"],
                            "lat": d_stop["lat"],
                            "lon": d_stop["lon"],
                                "walk_distance_m": d_stop["distance_m"],
                                "walk_time_min": walk_from_stop,
                                "walk_coords": walk_from_seg["coords"],
                            },
                        "wait_time_min": wait1 + wait2,
                        "bus_time_min": bus1_time + bus2_time,
                        "total_time_min": round(total_time, 1),
                        "total_walk_m": float(walk_to_seg["distance_m"]) + float(walk_from_seg["distance_m"]),
                        "bus_distance_m": round(bus1_distance_m + bus2_distance_m),
                        "transfer_count": 1,
                        "transfer_routes": [
                            {
                                "route_code": route_a,
                                "from_code": o_stop["code"],
                                "to_code": transfer_stop_code,
                                "from_name": o_stop["name"],
                                "to_name": candidate.get("transfer_stop_name", "Transfer"),
                                "wait_min": wait1,
                            },
                            {
                                "route_code": route_b,
                                "from_code": transfer_stop_code,
                                "to_code": d_stop["code"],
                                "from_name": candidate.get("transfer_stop_name", "Transfer"),
                                "to_name": d_stop["name"],
                                "wait_min": wait2,
                            },
                        ],
                    })

        # Ilk dar yaricapta erken cikis, 700-900m civarindaki duraklari kacirabiliyor.
        # En az ikinci yaricapi da (>=1000m) tarayalim.
        if transit_options and len(transit_options) >= (max_results * 2) and radius_idx >= 1:
            break

    unique_options = _diversify_transit_options(transit_options, max_options=max_results)

    # Yurume secenegi her zaman ekle
    result = [walking_option]

    # Transit secenekleri ekle
    for opt in unique_options:
        walk_to_stop_coords = opt.get("origin_stop", {}).get("walk_coords") or _get_walk_road_coords(
            origin_lat, origin_lon,
            opt["origin_stop"]["lat"], opt["origin_stop"]["lon"]
        )
        walk_from_stop_coords = opt.get("dest_stop", {}).get("walk_coords") or _get_walk_road_coords(
            opt["dest_stop"]["lat"], opt["dest_stop"]["lon"],
            dest_lat, dest_lon
        )

        if opt.get("transfer_count") == 1 and opt.get("transfer_routes"):
            transfer_legs = opt["transfer_routes"]
            bus_segments = []
            for idx, leg in enumerate(transfer_legs):
                leg_stop_coords = _get_route_stop_coords(
                    leg["route_code"], leg["from_code"], leg["to_code"]
                )
                if not leg_stop_coords:
                    continue
                leg_road_coords = _get_bus_road_coords(leg_stop_coords)
                leg_distance_m = _path_distance_m(leg_stop_coords)
                bus_segments.append({
                    "mode": "bus",
                    "description": f"{leg['route_code']} hatti",
                    "route_code": leg["route_code"],
                    "from_stop": leg["from_name"],
                    "to_stop": leg["to_name"],
                    "distance_m": round(leg_distance_m),
                    "duration_min": _bus_travel_time_minutes(leg_distance_m / 1000),
                    "wait_min": leg.get("wait_min", AVG_BUS_WAIT_MIN),
                    "coords": leg_road_coords,
                    "stop_coords": leg_stop_coords,
                })

            if not bus_segments:
                continue

            transfer_wait_total = 0.0
            for seg in bus_segments:
                transfer_wait_total += float(seg.get("wait_min", 0))
            bus_total_time = 0.0
            for seg in bus_segments:
                bus_total_time += float(seg.get("duration_min", 0))
            final_total_time = (
                float(opt["origin_stop"]["walk_time_min"])
                + transfer_wait_total
                + bus_total_time
                + float(opt["dest_stop"]["walk_time_min"])
            )

            segments = [{
                "mode": "walk",
                "description": f"Duraga yuru: {opt['origin_stop']['name']}",
                "distance_m": opt["origin_stop"]["walk_distance_m"],
                "duration_min": opt["origin_stop"]["walk_time_min"],
                "coords": walk_to_stop_coords,
            }]
            segments.extend(bus_segments)
            segments.append({
                "mode": "walk",
                "description": "Duraktan hedefe yuru",
                "distance_m": opt["dest_stop"]["walk_distance_m"],
                "duration_min": opt["dest_stop"]["walk_time_min"],
                "coords": walk_from_stop_coords,
            })

            result.append({
                "type": "transit",
                "icon": "bus",
                "transit_mode": "bus",
                "name": f"{transfer_legs[0]['route_code']} + {transfer_legs[1]['route_code']} Aktarmali",
                "description": (
                    f"{opt['origin_stop']['name']} -> {opt['transfer_stop']['name']} -> "
                    f"{opt['dest_stop']['name']}"
                ),
                "total_time_min": round(final_total_time, 1),
                "total_distance_m": opt["total_walk_m"] + opt["bus_distance_m"],
                "route_code": opt["route_code"],
                "route_name": opt.get("route_name", ""),
                "transfer_count": 1,
                "selection_reason": opt.get("selection_reason"),
                "segments": segments,
            })
        else:
            route_display = opt["route_code"]
            bus_stop_coords = _get_route_stop_coords(
                opt["route_code"],
                opt["origin_stop"]["code"],
                opt["dest_stop"]["code"],
            )
            if not bus_stop_coords:
                continue
            bus_road_coords = _get_bus_road_coords(bus_stop_coords)

            result.append({
                "type": "transit",
                "icon": "bus",
                "transit_mode": "bus",
                "name": f"{route_display} Otobus",
                "description": f"{opt['origin_stop']['name']} -> {opt['dest_stop']['name']}",
                "total_time_min": opt["total_time_min"],
                "total_distance_m": opt["total_walk_m"] + opt["bus_distance_m"],
                "route_code": opt["route_code"],
                "route_name": opt.get("route_name", ""),
                "transfer_count": int(opt.get("transfer_count", 0) or 0),
                "selection_reason": opt.get("selection_reason"),
                "segments": [
                    {
                        "mode": "walk",
                        "description": f"Duraga yuru: {opt['origin_stop']['name']}",
                        "distance_m": opt["origin_stop"]["walk_distance_m"],
                        "duration_min": opt["origin_stop"]["walk_time_min"],
                        "coords": walk_to_stop_coords,
                    },
                    {
                        "mode": "bus",
                        "description": f"{route_display} hatti",
                        "route_code": opt["route_code"],
                        "from_stop": opt["origin_stop"]["name"],
                        "to_stop": opt["dest_stop"]["name"],
                        "distance_m": opt["bus_distance_m"],
                        "duration_min": opt["bus_time_min"],
                        "wait_min": opt["wait_time_min"],
                        "coords": bus_road_coords,
                        "stop_coords": bus_stop_coords,
                    },
                    {
                        "mode": "walk",
                        "description": "Duraktan hedefe yuru",
                        "distance_m": opt["dest_stop"]["walk_distance_m"],
                        "duration_min": opt["dest_stop"]["walk_time_min"],
                        "coords": walk_from_stop_coords,
                    },
                ],
            })

    metro_options = _build_metro_options(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        direct_walk_min=direct_walk_min,
        direct_walk_m=direct_walk_m,
        max_results=5,
    )

    # Direkt/tek aktarma metro secenekleri cikmazsa cok aktarmali ag fallback'i dene.
    if not metro_options and allowed_user_modes != {"ferry"}:
        graph_metro = _build_graph_metro_option(
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            dest_lat=dest_lat,
            dest_lon=dest_lon,
            direct_walk_min=direct_walk_min,
            direct_walk_m=direct_walk_m,
        )
        if graph_metro:
            metro_options = [graph_metro]

    mixed_options = _build_bus_metro_mixed_options(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        direct_walk_min=direct_walk_min,
        direct_walk_m=direct_walk_m,
        max_results=3,
    )
    reverse_mixed_options = _build_metro_bus_mixed_options(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        direct_walk_min=direct_walk_min,
        direct_walk_m=direct_walk_m,
        max_results=6,
    )
    ferry_options = _build_ferry_only_options(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        direct_walk_min=direct_walk_min,
        max_results=2,
    )

    result.extend(metro_options)
    result.extend(mixed_options)
    result.extend(reverse_mixed_options)
    result.extend(ferry_options)

    # Yurumeyi sabit ilk eleman olarak koru; toplu tasimayi cesitlendir.
    walking = result[0]
    transit = []
    for opt in result[1:]:
        if opt.get("type") != "transit":
            continue
        user_modes = _option_user_modes(opt)
        # Kullanici secimi disindaki modlari iceren kombinasyonlari ele.
        if user_modes and not user_modes.issubset(allowed_user_modes):
            continue
        if _is_absurd_transit_option(
            opt,
            origin_lon=origin_lon,
            dest_lon=dest_lon,
            direct_walk_min=direct_walk_min,
            direct_walk_m=direct_walk_m,
        ):
            continue
        if _has_implausible_segment_jump(opt):
            continue
        transit.append(opt)
    merged = _diversify_transit_options(transit, max_options=max_transit_options)
    result = [walking] + merged
    return result


def compare_routes(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    allowed_modes: Optional[List[str]] = None,
) -> Dict:
    """
    Yuruyus ve toplu tasima seceneklerini karsilastirir.
    Direkt baglanti bulunamazsa yakin hatlari bilgi olarak dondurur.
    """
    compare_start = _time.perf_counter()
    telemetry: Dict[str, object] = {"stage_ms": {}}
    stage_ms = telemetry["stage_ms"]
    allowed_modes_norm = sorted(_normalize_allowed_modes(allowed_modes))
    cache_key = (
        round(float(origin_lat), 6),
        round(float(origin_lon), 6),
        round(float(dest_lat), 6),
        round(float(dest_lon), 6),
        tuple(allowed_modes_norm),
    )
    cached = _compare_cache_get(cache_key)
    if cached is not None:
        cached_telemetry = cached.get("telemetry")
        if not isinstance(cached_telemetry, dict):
            cached_telemetry = {}
        cached_telemetry["compare_cache_hit"] = True
        cached["telemetry"] = cached_telemetry
        return cached

    t0 = _time.perf_counter()
    options = find_transit_routes(
        origin_lat, origin_lon, dest_lat, dest_lon,
        allowed_modes=allowed_modes_norm,
    )
    stage_ms["find_transit_routes_ms"] = round((_time.perf_counter() - t0) * 1000, 2)

    t0 = _time.perf_counter()
    walking = options[0]
    transit = sorted(
        [o for o in options if o["type"] == "transit"],
        key=lambda x: float(x.get("total_time_min", 10**9))
    )
    stage_ms["rank_options_ms"] = round((_time.perf_counter() - t0) * 1000, 2)

    # Oneri
    t0 = _time.perf_counter()
    recommended = "walking"
    reason = "Yuruyus en hizli secenek"

    if transit:
        best_transit = transit[0]
        if best_transit["total_time_min"] < walking["total_time_min"]:
            recommended = "transit"
            saved = round(walking["total_time_min"] - best_transit["total_time_min"], 1)
            reason = f"Toplu tasima {saved} dk daha hizli"
        else:
            reason = "Yuruyus daha hizli veya benzer surede"
    stage_ms["recommendation_ms"] = round((_time.perf_counter() - t0) * 1000, 2)

    # Yakin hatlari bilgi olarak ekle (direkt baglanti olmasa bile)
    t0 = _time.perf_counter()
    nearby_origin = _get_nearby_routes(origin_lat, origin_lon, 500)
    nearby_dest = _get_nearby_routes(dest_lat, dest_lon, 500)
    stage_ms["nearby_routes_ms"] = round((_time.perf_counter() - t0) * 1000, 2)
    stage_ms["total_ms"] = round((_time.perf_counter() - compare_start) * 1000, 2)
    telemetry["compare_cache_hit"] = False
    telemetry["option_counts"] = {
        "total_options": len(options),
        "transit_options": len(transit),
    }

    output = {
        "options": options,
        "walking": walking,
        "transit_options": transit,
        "recommended": recommended,
        "recommendation_reason": reason,
        "applied_modes": allowed_modes_norm,
        "nearby_routes": {
            "origin": [{"route_code": r["route_code"], "stop_name": r["stop_name"], "distance_m": r["distance_m"]} for r in nearby_origin[:5]],
            "destination": [{"route_code": r["route_code"], "stop_name": r["stop_name"], "distance_m": r["distance_m"]} for r in nearby_dest[:5]],
        },
        "telemetry": telemetry,
    }
    _compare_cache_put(cache_key, output)
    return output


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("Multimodal Rota Test")
    print("=" * 50)

    # Kadikoy -> Moda arasi
    result = compare_routes(40.9903, 29.0291, 40.9835, 29.0344)

    print(f"\nOneri: {result['recommended']}")
    print(f"Neden: {result['recommendation_reason']}")
    print(f"\nSecenekler:")
    for opt in result["options"]:
        print(f"  {opt['icon']} {opt['name']} - {opt['total_time_min']} dk")
        for seg in opt.get("segments", []):
            print(f"    [{seg['mode']}] {seg.get('description', '')} - {seg['duration_min']} dk")

    # Yakin hatlar
    nr = result.get("nearby_routes", {})
    print(f"\nBaslangic yakin hatlar: {[r['route_code'] for r in nr.get('origin', [])]}")
    print(f"Hedef yakin hatlar: {[r['route_code'] for r in nr.get('destination', [])]}")
