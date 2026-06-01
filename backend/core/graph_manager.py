"""
graph_manager.py - OSMnx ile harita verisi yönetimi

Harita verilerini OpenStreetMap'ten indirir, .graphml olarak cache'ler,
ve POI (Points of Interest) aramalarını gerçekleştirir.
"""

import os
import math
import sqlite3
import json
import hashlib
import threading
from datetime import datetime, timezone
import osmnx as ox

try:
    import pandas as pd
except ImportError:
    pd = None
import networkx as nx
from route_config import ROUTE_CONFIG
from text_utils import tr_lower
from cache_manager import get_point_graph_memory_cache

try:
    from geocoder import geocode
except ImportError:
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        from geocoder import geocode
    except ImportError:
        geocode = None

# Cache dizini
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
POI_DB_PATH = os.path.join(DATA_DIR, "pois.db")


def _init_poi_db():
    conn = sqlite3.connect(POI_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pois (
            place_name TEXT,
            category TEXT,
            data_json TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (place_name, category)
        )
    ''')
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pois_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            place_name TEXT NOT NULL,
            category TEXT NOT NULL,
            data_json TEXT NOT NULL,
            original_timestamp TEXT,
            archived_at TEXT NOT NULL,
            reason TEXT DEFAULT 'before_replace'
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_pois_archive_place_cat "
        "ON pois_archive(place_name, category, archived_at DESC)"
    )
    conn.commit()
    conn.close()

_init_poi_db()

_POI_REFRESH_LOCK = threading.Lock()
_POI_REFRESH_INFLIGHT = set()
_POINT_GRAPH_MEMORY_CACHE = get_point_graph_memory_cache()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_sqlite_timestamp(raw_ts: str) -> datetime | None:
    if not raw_ts:
        return None
    text = str(raw_ts).strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    try:
        dt = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _read_poi_cache_entry(place_name: str, cache_category: str):
    """
    Yerel DB'den cache kaydini metadata ile okur.
    """
    try:
        conn = sqlite3.connect(POI_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT data_json, timestamp FROM pois WHERE place_name = ? AND category = ?",
            (place_name.lower(), cache_category),
        )
        row = cursor.fetchone()
        conn.close()
    except Exception as e:
        print(f"[POI] Yerel veritabani okuma hatasi: {e}")
        return None

    if not row:
        return None

    raw_json, raw_ts = row
    try:
        pois = json.loads(raw_json or "[]")
        if not isinstance(pois, list):
            pois = []
    except Exception:
        pois = []

    ts_dt = _parse_sqlite_timestamp(raw_ts)
    age_seconds = None
    if ts_dt is not None:
        age_seconds = max(0.0, (_utc_now() - ts_dt).total_seconds())

    return {
        "pois": pois,
        "timestamp_raw": raw_ts,
        "timestamp_dt": ts_dt,
        "age_seconds": age_seconds,
        "is_empty": len(pois) == 0,
    }


def _prune_poi_archive(cursor, place_name_lower: str, cache_category: str) -> None:
    """Ayni yer+kategori icin arsiv satir sayisini sinirlar."""
    max_keep = int(ROUTE_CONFIG.get("POI_ARCHIVE_MAX_PER_KEY", 5))
    max_keep = max(1, min(50, max_keep))
    cursor.execute(
        "SELECT id FROM pois_archive WHERE place_name = ? AND category = ? ORDER BY archived_at DESC",
        (place_name_lower, cache_category),
    )
    ids = [row[0] for row in cursor.fetchall()]
    for old_id in ids[max_keep:]:
        cursor.execute("DELETE FROM pois_archive WHERE id = ?", (old_id,))


def _write_poi_cache_entry(place_name: str, cache_category: str, pois: list) -> None:
    """
    Yerel DB cache kaydini gunceller.
    Eski surum varsa once pois_archive'a kopyalanir (silmeden once tekrar kullanima acik).
    """
    try:
        conn = sqlite3.connect(POI_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT data_json, timestamp FROM pois WHERE place_name = ? AND category = ?",
            (place_name.lower(), cache_category),
        )
        row = cursor.fetchone()
        if row is not None:
            old_json, old_ts = row[0], row[1]
            cursor.execute(
                """
                INSERT INTO pois_archive (place_name, category, data_json, original_timestamp, archived_at, reason)
                VALUES (?, ?, ?, ?, datetime('now'), ?)
                """,
                (
                    place_name.lower(),
                    cache_category,
                    old_json if old_json is not None else "[]",
                    str(old_ts) if old_ts is not None else "",
                    "before_replace",
                ),
            )
            _prune_poi_archive(cursor, place_name.lower(), cache_category)

        cursor.execute(
            """
            INSERT OR REPLACE INTO pois (place_name, category, data_json)
            VALUES (?, ?, ?)
            """,
            (place_name.lower(), cache_category, json.dumps(pois, ensure_ascii=False)),
        )
        conn.commit()
        conn.close()
        print(f"[POI] Cache'e kaydedildi: {place_name} ({cache_category})")
    except Exception as e:
        print(f"[POI] Yerel veritabani yazma hatasi: {e}")


def _start_background_poi_refresh(place_name: str, normalized_tags: dict, cache_category: str, category_hint: str, search_mode: str) -> bool:
    """
    Ayni sorgu icin birden fazla background refresh acilmasini engeller.
    """
    key = f"{place_name.lower()}::{cache_category}"
    with _POI_REFRESH_LOCK:
        if key in _POI_REFRESH_INFLIGHT:
            return False
        _POI_REFRESH_INFLIGHT.add(key)

    def _runner():
        try:
            gdf, had_error = _fetch_pois_with_fallback(place_name, normalized_tags, search_mode=search_mode)
            if gdf is None:
                if had_error:
                    print(f"[POI] Background refresh hatasi: {place_name} ({cache_category})")
                return
            pois = _rows_to_poi_list(gdf, category_hint or "semantic")
            _write_poi_cache_entry(place_name, cache_category, pois)
            print(f"[POI] Background refresh tamamlandi: {place_name} ({cache_category}) -> {len(pois)}")
        except Exception as e:
            print(f"[POI] Background refresh exception: {e}")
        finally:
            with _POI_REFRESH_LOCK:
                _POI_REFRESH_INFLIGHT.discard(key)

    threading.Thread(target=_runner, daemon=True).start()
    return True


def _build_tags_cache_suffix(tags: dict) -> str:
    """
    Tag sozlugunu deterministic bir cache suffix'ine cevirir.
    Ayni tag kombinasyonu her zaman ayni anahtari uretir.
    """
    normalized = {str(k): str(v) for k, v in (tags or {}).items() if k and v}
    if not normalized:
        return "notags"
    canonical = json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:12]
    return digest


def _cache_path(place_name: str, network_type: str | None = None) -> str:
    """Verilen yer adi + network tipi icin cache dosya yolunu doner."""
    safe_name = place_name.replace(",", "").replace(" ", "_").lower()
    if not network_type:
        return os.path.join(DATA_DIR, f"{safe_name}.graphml")
    safe_network = str(network_type).replace("-", "_").replace(" ", "_").lower()
    return os.path.join(DATA_DIR, f"{safe_name}_{safe_network}.graphml")

def _osm_values(value) -> set[str]:
    """Normalize an OSM edge value that may be scalar or list-like."""
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        return {str(item).strip().lower() for item in value if str(item).strip()}
    return {str(value).strip().lower()}


def _is_bridge_edge(data: dict) -> bool:
    """Return True if edge is tagged as a bridge-like crossing."""
    bridge_values = _osm_values((data or {}).get("bridge"))
    if not bridge_values:
        return False
    return any(value not in {"", "no", "false", "0", "none"} for value in bridge_values)


def _is_blocked_walk_edge(data: dict) -> bool:
    """Return True for edges that should not be used by outdoor routes."""
    # Bridge edges are explicitly kept so sea crossings remain routable.
    if _is_bridge_edge(data):
        return False

    tunnel_values = _osm_values(data.get("tunnel"))
    if any("building_passage" in value for value in tunnel_values):
        return True

    indoor_values = _osm_values(data.get("indoor"))
    if indoor_values and not indoor_values.issubset({"no", "false", "outdoor"}):
        return True

    highway_values = _osm_values(data.get("highway"))
    if "corridor" in highway_values:
        return True

    access_values = _osm_values(data.get("access"))
    return bool(access_values & {"no", "private", "customers"})


def _graph_network_type() -> str:
    """
    Resolve and validate OSMnx network type from config.
    Defaults to `all_public` to keep bridge connectivity available.
    """
    raw = str(ROUTE_CONFIG.get("OSM_NETWORK_TYPE", "all_public") or "").strip().lower()
    allowed = {
        "walk",
        "drive",
        "drive_service",
        "bike",
        "all",
        "all_public",
        "all_private",
    }
    if raw in allowed:
        return raw
    return "all_public"


def _filter_outdoor_walk_graph(G):
    """
    Remove indoor/private shortcuts while keeping public outdoor walkways.

    OSMnx's walk network intentionally includes passages through buildings.
    The product routes outdoor sightseeing trips, so those edges must not
    participate in shortest-path or alternative-route calculations.
    """
    blocked_edges = [
        (u, v, key)
        for u, v, key, data in G.edges(keys=True, data=True)
        if _is_blocked_walk_edge(data)
    ]
    if not blocked_edges:
        return G

    G.remove_edges_from(blocked_edges)
    isolated_nodes = list(nx.isolates(G))
    if isolated_nodes:
        G.remove_nodes_from(isolated_nodes)
    print(f"[GraphManager] Outdoor routing filtresi: {len(blocked_edges)} kapali/ozel kenar cikarildi")
    return G


def get_graph(place_name: str = "Kadikoy, Istanbul, Turkey"):
    """
    Belirtilen bölgenin yürüyüş grafiğini döner.
    İlk çağrıda internetten indirir ve .graphml olarak cache'ler.
    Sonraki çağrılarda dosyadan okur (çok daha hızlı).
    """
    network_type = _graph_network_type()
    cache_file = _cache_path(place_name, network_type)

    if os.path.exists(cache_file):
        print(f"[GraphManager] Cache'den okunuyor: {cache_file}")
        G = ox.load_graphml(cache_file)
    else:
        print(f"[GraphManager] OSM'den indiriliyor: {place_name} ({network_type})")
        G = ox.graph_from_place(place_name, network_type=network_type)
        ox.save_graphml(G, cache_file)
        print(f"[GraphManager] Cache'e kaydedildi: {cache_file}")

    return _apply_routing_edge_weights(_filter_outdoor_walk_graph(G))




def _bosphorus_side(lon: float) -> int:
    if lon <= 29.010:
        return -1
    if lon >= 29.014:
        return 1
    return 0


def get_graph_for_points(points: list, radius_multiplier: float = 1.0):
    """
    Seçilen noktaların merkezinden, tüm noktaları kapsayacak
    yarıçapla graf indirir. graph_from_point kullanır (bbox'tan çok daha hızlı).
    
    Args:
        points: [(lat, lon), ...] koordinat listesi
        radius_multiplier: Yarıçap çarpanı (1.0 = varsayılan, 1.8 = köprü deturları için)
    
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
    max_radius = ROUTE_CONFIG.get("GRAPH_RADIUS_MAX_M", 20000)

    # Minimum yarıçap + padding uygula. Radius multiplier ile çarp.
    raw_radius = max(min_radius, max_dist + padding)
    radius = min(max_radius, raw_radius * radius_multiplier)
    
    # retain_all: radius_multiplier > 1 ise köprü deturları yakalanacak,
    # tüm bileşenleri tut.
    retain_all = radius_multiplier > 1.0
    
    # Bogaz gecisi tespiti
    crosses_bosphorus = False
    if len(points) >= 2:
        sides = [_bosphorus_side(p[1]) for p in points]
        if -1 in sides and 1 in sides:
            crosses_bosphorus = True

    configured_type = _graph_network_type()
    net_type = configured_type
    # Kullanicinin network tipi walk olsa bile, deniz asiri geciste kopru baglantilarini
    # kacirmamak icin all_public'a yukseltilir.
    if crosses_bosphorus and configured_type == "walk":
        net_type = "all_public"
    
    # Cache key: merkez + yarıçap + net_type
    cache_key = f"point_{center_lat:.4f}_{center_lon:.4f}_{int(radius)}_{net_type}"
    cache_file = os.path.join(DATA_DIR, f"{cache_key}.graphml")

    # Disk cache oncesi RAM katmani
    cached_graph = _POINT_GRAPH_MEMORY_CACHE.get(cache_key)
    if cached_graph is not None:
        print(f"[GraphManager] RAM cache hit: {cache_key} ({net_type})")
        return cached_graph

    if os.path.exists(cache_file):
        print(f"[GraphManager] Cache'den okunuyor: {cache_file} ({net_type})")
        try:
            G = ox.load_graphml(cache_file)
            processed = _apply_routing_edge_weights(_filter_outdoor_walk_graph(G))
            _POINT_GRAPH_MEMORY_CACHE.put(cache_key, processed)
            return processed
        except Exception as e:
            print(f"[GraphManager WARNING] Failed to load cached graph: {e}. Re-downloading...")
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except:
                    pass

    print(f"[GraphManager] Graf indiriliyor: merkez=({center_lat:.4f}, {center_lon:.4f}), yarıçap={int(radius)}m ({net_type})")
    try:
        G = ox.graph_from_point(
            (center_lat, center_lon),
            dist=radius,
            network_type=net_type,
            retain_all=retain_all,
        )
        ox.save_graphml(G, cache_file)
        print(f"[GraphManager] Cache'e kaydedildi: {cache_file}")
        _prune_point_graph_cache()
        processed = _apply_routing_edge_weights(_filter_outdoor_walk_graph(G))
        _POINT_GRAPH_MEMORY_CACHE.put(cache_key, processed)
        return processed
    except Exception as e:
        print(f"[GraphManager ERROR] OSMnx failed to load graph for point ({center_lat:.4f}, {center_lon:.4f}) with radius {radius} and type {net_type}: {e}")
        # Gelişmiş hata kurtarma (Fallback): Kadıköy merkezli varsayılan grafiği yükle
        fallback_place = "Kadikoy, Istanbul, Turkey"
        print(f"[GraphManager] Fallback devrede: {fallback_place} grafiği yükleniyor...")
        fallback_file = _cache_path(fallback_place, net_type)
        if os.path.exists(fallback_file):
            try:
                G = ox.load_graphml(fallback_file)
                processed = _apply_routing_edge_weights(_filter_outdoor_walk_graph(G))
                _POINT_GRAPH_MEMORY_CACHE.put(cache_key, processed)
                return processed
            except:
                pass
        
        # Kadıköy cache'i de yoksa sıfırdan çekmeyi dene
        try:
            G = ox.graph_from_place(fallback_place, network_type=net_type)
            ox.save_graphml(G, fallback_file)
            processed = _apply_routing_edge_weights(_filter_outdoor_walk_graph(G))
            _POINT_GRAPH_MEMORY_CACHE.put(cache_key, processed)
            return processed
        except Exception as fallback_exc:
            print(f"[GraphManager CRITICAL] Fallback graph fetch failed: {fallback_exc}. Returning empty MultiDiGraph.")
            import networkx as nx
            G = nx.MultiDiGraph()
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
        node_id, _ = find_nearest_node_with_distance(G, lat, lon)
        return int(node_id)
    except Exception as e:
        # Fallback: nearest_nodes kullan
        print(f"[GraphManager] Manuel nearest node hatası, fallback kullanılıyor: {e}")
        return ox.nearest_nodes(G, X=lon, Y=lat)


def _edge_semantic_penalty_m(data: dict) -> float:
    """Return extra penalty distance (metres) for a given edge based on its tags.

    Currently adds penalty for bridge-tagged edges so that snap-to-graph logic
    prefers non-bridge neighbours.
    """
    penalty = 0.0
    if _is_bridge_edge(data or {}):
        penalty += float(ROUTE_CONFIG.get("SNAP_BRIDGE_PENALTY_M", 45.0))
    return penalty


def find_nearest_node_with_distance(G, lat: float, lon: float) -> tuple:
    """
    Verilen koordinata en yakın graf düğümünü bulur ve snap mesafesini (metre)
    döndürür.  Köprü kenarı üzerindeki düğümlere ceza ekleyerek kara komşularını
    tercih eder.  snap mesafesi, sorgu noktasının kenar geometrisine (çizgiye)
    olan en kısa mesafesidir.

    Returns:
        (node_id, snap_distance_m)
    """
    import math
    max_candidates = int(ROUTE_CONFIG.get("SNAP_MAX_NEIGHBOR_CANDIDATES", 4))
    gap_max_m = float(ROUTE_CONFIG.get("SNAP_NODE_EDGE_GAP_MAX_M", 110.0))
    edge_near_threshold_m = float(ROUTE_CONFIG.get("SNAP_EDGE_NEAR_THRESHOLD_M", 25.0))
    cross_shore_penalty_m = float(ROUTE_CONFIG.get("SNAP_CROSS_SHORE_PENALTY_M", 2000.0))

    def _haversine_m(lat1, lon1, lat2, lon2):
        R = 6_371_000
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + (
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        )
        return R * 2 * math.asin(math.sqrt(a))

    def _point_to_segment_m(plat, plon, alat, alon, blat, blon):
        """Sorgu noktasının (plat, plon) bir kenar segmentine (a->b) olan minimum mesafesi."""
        # Segment vektörü
        dx = blon - alon
        dy = blat - alat
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq < 1e-18:
            return _haversine_m(plat, plon, alat, alon)
        # Projeksiyon parametresi t ∈ [0, 1]
        t = ((plon - alon) * dx + (plat - alat) * dy) / seg_len_sq
        t = max(0.0, min(1.0, t))
        proj_lon = alon + t * dx
        proj_lat = alat + t * dy
        return _haversine_m(plat, plon, proj_lat, proj_lon)

    def _edge_snap_distance(plat, plon, edata, u_data, v_data):
        """Kenar geometrisine veya uç noktalarına olan en kısa mesafe."""
        geom = getattr(edata.get("geometry"), "coords", None)
        if geom and len(geom) >= 2:
            best = float("inf")
            coords = list(geom)
            for i in range(len(coords) - 1):
                # geometry coords are (x=lon, y=lat)
                d = _point_to_segment_m(
                    plat, plon,
                    coords[i][1], coords[i][0],
                    coords[i + 1][1], coords[i + 1][0],
                )
                if d < best:
                    best = d
            return best
        # Geometri yoksa uç noktalar arası segment
        return _point_to_segment_m(
            plat, plon,
            u_data["y"], u_data["x"],
            v_data["y"], v_data["x"],
        )

    try:
        u, v, key = ox.nearest_edges(G, X=lon, Y=lat)
    except Exception:
        node = ox.nearest_nodes(G, X=lon, Y=lat)
        nd = G.nodes[node]
        return node, _haversine_m(lat, lon, nd["y"], nd["x"])

    # Nearest-edge'den snap mesafesini hesapla.
    u_data = G.nodes[u]
    v_data = G.nodes[v]
    edata = G.get_edge_data(u, v)
    if edata:
        edata = edata.get(key, edata.get(0, {})) if isinstance(edata, dict) else {}
    else:
        edata = {}
    edge_snap_m = _edge_snap_distance(lat, lon, edata, u_data, v_data)

    # Kenar uç noktalarını + yakın komşuları aday olarak topla.
    candidates = {u, v}
    for n in (u, v):
        for nbr in list(G.successors(n))[:max_candidates]:
            candidates.add(nbr)
        for nbr in list(G.predecessors(n))[:max_candidates]:
            candidates.add(nbr)

    best_node = u
    best_score = float("inf")
    best_raw_dist = float("inf")
    query_side = _bosphorus_side(lon)

    for c in candidates:
        nd = G.nodes[c]
        raw_dist = _haversine_m(lat, lon, nd["y"], nd["x"])
        # Kenar noktaya yakınsa, node bu kenar geometrisinden aşırı uzakta olmamalı.
        if edge_snap_m <= edge_near_threshold_m and (raw_dist - edge_snap_m) > gap_max_m:
            continue

        # Komşu kenarlardan semantik ceza hesapla.
        penalty = 0.0
        for _, _, ed in G.edges(c, data=True):
            penalty = max(penalty, _edge_semantic_penalty_m(ed))

        # Kullanıcı noktası belirgin bir yakadaysa, karşı yakaya snap'i caydır.
        cand_side = _bosphorus_side(float(nd.get("x", lon)))
        if query_side != 0 and cand_side != 0 and cand_side != query_side:
            penalty += cross_shore_penalty_m

        score = raw_dist + penalty
        if score < best_score:
            best_score = score
            best_node = c
            best_raw_dist = raw_dist

    # snap_m: kenar geometrisine olan mesafe (daha doğru) veya node mesafesi
    # (hangisi küçükse)
    snap_m = min(edge_snap_m, best_raw_dist)
    return best_node, snap_m


def _apply_routing_edge_weights(G):
    """
    Graf kenarlarına routing ağırlığı atar.  Köprü kenarlarına
    BRIDGE_PENALTY_FACTOR çarpanı uygulanır.

    Returns:
        G (aynı graf, yerinde güncellenir)
    """
    weight_key = str(ROUTE_CONFIG.get("ROUTING_WEIGHT_KEY", "routing_length"))
    penalty_factor = float(ROUTE_CONFIG.get("BRIDGE_PENALTY_FACTOR", 1.8))

    for u, v, k, data in G.edges(keys=True, data=True):
        length = float(data.get("length", 0.0))
        if _is_bridge_edge(data):
            data[weight_key] = length * penalty_factor
        else:
            data[weight_key] = length

    return G


def _prune_point_graph_cache():
    """
    DATA_DIR içindeki point_*.graphml dosyalarını tarih sırasına göre
    sıralayıp, GRAPH_POINT_CACHE_MAX_FILES sınırının üzerindeki en eski
    dosyaları siler.
    """
    import glob
    max_files = int(ROUTE_CONFIG.get("GRAPH_POINT_CACHE_MAX_FILES", 20))
    pattern = os.path.join(DATA_DIR, "point_*.graphml")
    files = sorted(glob.glob(pattern), key=os.path.getmtime)

    while len(files) > max_files:
        oldest = files.pop(0)
        try:
            os.remove(oldest)
        except OSError:
            pass


def _rows_to_poi_list(gdf, category_label: str) -> list:
    """OSMnx dataframe satırlarını API POI listesine dönüştürür."""
    pois = []
    for _, row in gdf.iterrows():
        try:
            centroid = row.geometry.centroid
            name = row.get("name", "İsimsiz")
            if name is None or (hasattr(name, "__len__") and len(str(name)) == 0):
                name = "İsimsiz"

            website = row.get("website", "") or ""
            wikipedia = row.get("wikipedia", "") or ""
            opening_hours = row.get("opening_hours", "") or ""
            description = row.get("description", "") or ""
            image = row.get("image", "") or ""

            wiki_url = ""
            if wikipedia and isinstance(wikipedia, str) and ":" in wikipedia:
                lang, title = wikipedia.split(":", 1)
                wiki_url = f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"

            pois.append({
                "name": str(name),
                "lat": centroid.y,
                "lon": centroid.x,
                "category": category_label,
                "website": str(website) if website else "",
                "wikipedia_url": wiki_url,
                "opening_hours": str(opening_hours) if opening_hours else "",
                "description": str(description) if description else "",
                "image": str(image) if image else "",
            })
        except Exception as e:
            print(f"[POI] POI verisi hatası (atlanıyor): {e}")
            continue
    return pois


def _resolve_search_center(place_name: str):
    """Yer adını merkez koordinata çevirir (geo-bound zorunluluğu)."""
    if not geocode or not place_name:
        return None

    try:
        result = geocode(place_name)
    except Exception as e:
        print(f"[POI] Geocode hatası: {e}")
        return None

    if not isinstance(result, dict) or result.get("status") != "success":
        return None

    try:
        lat = float(result.get("lat"))
        lon = float(result.get("lon"))
        return lat, lon
    except (TypeError, ValueError):
        return None


def _bbox_span_km(minx: float, miny: float, maxx: float, maxy: float) -> float:
    """Yaklasik en/boy (km) -” genis bbox tespiti icin."""
    center_lat = (miny + maxy) / 2.0
    lat_km = max(1e-6, (maxy - miny)) * 111.0
    lon_km = max(1e-6, (maxx - minx)) * 111.0 * max(0.15, math.cos(math.radians(center_lat)))
    return max(lat_km, lon_km)


def _merge_geo_frames(gdfs):
    """Parcali sorgu GeoDataFrame birlestirme + tekrar satir dusurme."""
    if pd is None or not gdfs:
        return None
    parts = [g for g in gdfs if g is not None and len(g) > 0]
    if not parts:
        return None
    merged = pd.concat(parts, ignore_index=True)
    if "osmid" in merged.columns:
        merged = merged.drop_duplicates(subset=["osmid"], keep="first")
    else:
        merged = merged.drop_duplicates()
    return merged


def _is_no_matching_features_error(exc: Exception) -> bool:
    """
    OSMnx/Overpass tarafinda "sonuc yok" durumunu teknik hata degil, bos sonuc kabul eder.
    """
    msg = str(exc or "").lower()
    markers = (
        "no matching features",
        "found no results",
        "no data elements in server response",
        "nothing returned",
    )
    return any(m in msg for m in markers)


def _fetch_pois_chunked_grid(place_name: str, normalized_tags: dict, gdf_place) -> object:
    """
    Buyuk idari alan icin bbox'i hucrelere bolup features_from_point ile tarar.
    Overpass tek buyuk poligon sorgusunda zaman asimi/eksik sonuc riskini azaltir.
    """
    if pd is None or gdf_place is None or len(gdf_place) == 0:
        return None

    minx, miny, maxx, maxy = gdf_place.total_bounds
    span_km = _bbox_span_km(minx, miny, maxx, maxy)
    cell_km = float(ROUTE_CONFIG.get("POI_CHUNK_CELL_KM", 4.0))
    max_cells = int(ROUTE_CONFIG.get("POI_CHUNK_MAX_CELLS", 36))

    lat_deg = maxy - miny
    lon_deg = maxx - minx
    center_lat = (miny + maxy) / 2.0
    lat_km = lat_deg * 111.0
    lon_km = lon_deg * 111.0 * max(0.15, math.cos(math.radians(center_lat)))

    n_lat = max(1, int(math.ceil(lat_km / cell_km)))
    n_lon = max(1, int(math.ceil(lon_km / cell_km)))
    safety = 0
    while n_lat * n_lon > max_cells and safety < 12:
        cell_km *= 1.35
        n_lat = max(1, int(math.ceil(lat_km / cell_km)))
        n_lon = max(1, int(math.ceil(lon_km / cell_km)))
        safety += 1

    print(
        f"[POI] Parcali grid: ~{span_km:.1f} km span, hucre ~{cell_km:.1f} km, "
        f"izgara {n_lat}x{n_lon} (<= {max_cells} hucre)"
    )

    collected = []
    total_cells = n_lat * n_lon
    no_match_cells = 0
    error_cells = 0
    for i in range(n_lat):
        for j in range(n_lon):
            lo_lat = miny + (i / n_lat) * lat_deg
            hi_lat = miny + ((i + 1) / n_lat) * lat_deg
            lo_lon = minx + (j / n_lon) * lon_deg
            hi_lon = minx + ((j + 1) / n_lon) * lon_deg
            clat = (lo_lat + hi_lat) / 2.0
            clon = (lo_lon + hi_lon) / 2.0
            dlat_m = ((hi_lat - lo_lat) * 111000.0) / 2.0
            dlon_m = ((hi_lon - lo_lon) * 111000.0 * max(0.15, math.cos(math.radians(clat)))) / 2.0
            dist = int(min(8000, max(1200, math.sqrt(dlat_m**2 + dlon_m**2))))
            try:
                gdf_cell = ox.features_from_point((clat, clon), tags=normalized_tags, dist=dist)
                if gdf_cell is not None and len(gdf_cell) > 0:
                    collected.append(gdf_cell)
            except Exception as exc:
                if _is_no_matching_features_error(exc):
                    no_match_cells += 1
                    continue
                error_cells += 1
                print(f"[POI] Parca ({i},{j}) teknik hata: {exc}")

    print(
        f"[POI] Parcali grid ozet: dolu_hucre={len(collected)}, "
        f"bos_hucre={no_match_cells}, teknik_hata={error_cells}, toplam={total_cells}"
    )

    return _merge_geo_frames(collected)


def _fetch_pois_with_fallback(
    place_name: str,
    normalized_tags: dict,
    search_mode: str = "auto",
):
    """
    Overpass sorgularini kontrollu fallback plani ile calistirir.

    Returns:
        tuple[gdf_or_none, had_error]
    """
    search_mode = (search_mode or "auto").strip().lower()

    # Idari sinir (il veya ilce): once tek place-boundary sorgu.
    # Sadece teknik hata olursa (timeout/provider vb.) buyuk bbox icin parcali grid fallback calisir.
    if search_mode == "place_boundary_only":
        gdf_place = None
        try:
            gdf_place = ox.geocode_to_gdf(place_name)
        except Exception as exc:
            print(f"[POI] geocode_to_gdf: {exc}")

        min_km = float(ROUTE_CONFIG.get("POI_BOUNDARY_CHUNK_MIN_KM", 12.0))
        span_km = 0.0
        if gdf_place is not None and len(gdf_place) > 0:
            bx = gdf_place.total_bounds
            span_km = _bbox_span_km(bx[0], bx[1], bx[2], bx[3])

        had_error = False
        try:
            print("[POI] Search mode: place_boundary_only (idari sinir, tek sorgu)")
            gdf = ox.features_from_place(place_name, tags=normalized_tags)
            if gdf is not None and len(gdf) > 0:
                return gdf, False
            print("[POI] place_boundary_only: tek sorgu tamamlandi, sonuc bos")
            return None, False
        except Exception as exc:
            print(f"[POI] place-boundary tek sorgu hatasi: {exc}")
            had_error = True

        if had_error and span_km > min_km and gdf_place is not None and len(gdf_place) > 0 and pd is not None:
            print(f"[POI] place_boundary_only: teknik hata -> parcali fallback (~{span_km:.1f} km)")
            gdf_chunked = _fetch_pois_chunked_grid(place_name, normalized_tags, gdf_place)
            if gdf_chunked is not None and len(gdf_chunked) > 0:
                return gdf_chunked, False
        return None, had_error

    center = _resolve_search_center(place_name)
    if center is None:
        print(f"[POI] Geo-bound center bulunamadi, global sorgu iptal: {place_name}")
        return None, True

    strict_radius = int(ROUTE_CONFIG.get("POI_SEARCH_RADIUS_M", 2500))
    relaxed_radius = int(ROUTE_CONFIG.get("POI_SEARCH_RELAXED_RADIUS_M", 5000))
    max_steps = int(ROUTE_CONFIG.get("POI_FALLBACK_MAX_STEPS", 3))
    max_steps = max(1, min(3, max_steps))

    attempts = []
    attempts.append(("A", "point", strict_radius))
    if max_steps >= 2:
        attempts.append(("B", "point", relaxed_radius))
    if max_steps >= 3:
        attempts.append(("C", "place", None))

    had_error = False
    for label, mode, dist in attempts:
        try:
            if mode == "point":
                print(f"[POI] Fallback-{label}: point query dist={dist}m")
                gdf = ox.features_from_point(center, tags=normalized_tags, dist=dist)
            else:
                print(f"[POI] Fallback-{label}: place-boundary query")
                gdf = ox.features_from_place(place_name, tags=normalized_tags)

            if gdf is not None and len(gdf) > 0:
                return gdf, had_error
        except Exception as e:
            print(f"[POI] Fallback-{label} hatasi: {e}")
            had_error = True
            continue

    return None, had_error
def search_pois_by_tags(
    place_name: str,
    tags: dict,
    category_hint: str = "semantic",
    search_mode: str = "auto",
    force_refresh: bool = False,
    return_meta: bool = False,
):
    """
    Belirtilen bolgede dogrudan OSM tag filtresi ile POI arar.

    Cache stratejisi:
    - Soft TTL (default 7 gun): cache don, arkada yenile
    - Hard TTL (default 30 gun): cache gecersiz, canli sorgu zorunlu
    - Empty TTL (default 24 saat): bos sonuc daha kisa sureli
    """
    normalized_tags = {str(k): str(v) for k, v in (tags or {}).items() if k and v}
    if not normalized_tags:
        empty_meta = {
            "status": "invalid_tags",
            "source": "none",
            "last_updated": None,
            "age_seconds": None,
        }
        return ([], empty_meta) if return_meta else []

    category_hint = tr_lower(category_hint or "semantic")
    search_mode = (search_mode or "auto").strip().lower()
    cache_category = f"{category_hint}|{_build_tags_cache_suffix(normalized_tags)}|mode:{search_mode}"
    print(
        f"[POI] arama baslatildi (tags): {place_name}, "
        f"tags={normalized_tags}, hint={category_hint}, mode={search_mode}, force={force_refresh}"
    )

    soft_ttl_days = int(ROUTE_CONFIG.get("POI_CACHE_SOFT_TTL_DAYS", 7))
    hard_ttl_days = int(ROUTE_CONFIG.get("POI_CACHE_HARD_TTL_DAYS", 30))
    empty_ttl_hours = int(ROUTE_CONFIG.get("POI_CACHE_EMPTY_TTL_HOURS", 24))

    soft_ttl_seconds = max(3600, soft_ttl_days * 86400)
    hard_ttl_seconds = max(soft_ttl_seconds, hard_ttl_days * 86400)
    empty_ttl_seconds = max(300, empty_ttl_hours * 3600)

    entry = None if force_refresh else _read_poi_cache_entry(place_name, cache_category)

    if entry is not None:
        age_seconds = entry.get("age_seconds")
        last_updated = entry.get("timestamp_dt")
        last_updated_iso = last_updated.isoformat() if last_updated is not None else None
        is_empty = bool(entry.get("is_empty"))

        if is_empty and (age_seconds is None or age_seconds <= empty_ttl_seconds):
            meta = {
                "status": "empty_cache_hit",
                "source": "db_cache",
                "last_updated": last_updated_iso,
                "age_seconds": age_seconds,
                "soft_ttl_seconds": soft_ttl_seconds,
                "hard_ttl_seconds": hard_ttl_seconds,
                "empty_ttl_seconds": empty_ttl_seconds,
                "background_refresh": False,
                "force_refresh": force_refresh,
            }
            print(f"[POI] Cache hit (empty): {place_name} ({cache_category})")
            return (entry["pois"], meta) if return_meta else entry["pois"]

        if (not is_empty) and (age_seconds is None or age_seconds <= soft_ttl_seconds):
            meta = {
                "status": "fresh_cache_hit",
                "source": "db_cache",
                "last_updated": last_updated_iso,
                "age_seconds": age_seconds,
                "soft_ttl_seconds": soft_ttl_seconds,
                "hard_ttl_seconds": hard_ttl_seconds,
                "empty_ttl_seconds": empty_ttl_seconds,
                "background_refresh": False,
                "force_refresh": force_refresh,
            }
            print(f"[POI] Cache hit (fresh): {place_name} ({cache_category})")
            return (entry["pois"], meta) if return_meta else entry["pois"]

        if (not is_empty) and age_seconds is not None and age_seconds <= hard_ttl_seconds:
            started = _start_background_poi_refresh(
                place_name,
                normalized_tags,
                cache_category,
                category_hint,
                search_mode,
            )
            meta = {
                "status": "stale_cache_served",
                "source": "db_cache",
                "last_updated": last_updated_iso,
                "age_seconds": age_seconds,
                "soft_ttl_seconds": soft_ttl_seconds,
                "hard_ttl_seconds": hard_ttl_seconds,
                "empty_ttl_seconds": empty_ttl_seconds,
                "background_refresh": started,
                "force_refresh": force_refresh,
            }
            print(f"[POI] Cache stale-soft: {place_name} ({cache_category}) -> background_refresh={started}")
            return (entry["pois"], meta) if return_meta else entry["pois"]

    # Canli sorgu (ilk sorgu, force refresh veya hard-expired)
    gdf, had_error = _fetch_pois_with_fallback(
        place_name,
        normalized_tags,
        search_mode=search_mode,
    )

    if gdf is None:
        if had_error:
            if entry is not None:
                age_seconds = entry.get("age_seconds")
                last_updated = entry.get("timestamp_dt")
                meta = {
                    "status": "fallback_on_error",
                    "source": "db_cache",
                    "last_updated": last_updated.isoformat() if last_updated else None,
                    "age_seconds": age_seconds,
                    "soft_ttl_seconds": soft_ttl_seconds,
                    "hard_ttl_seconds": hard_ttl_seconds,
                    "empty_ttl_seconds": empty_ttl_seconds,
                    "background_refresh": False,
                    "force_refresh": force_refresh,
                    "error": "live_query_failed",
                }
                print(f"[POI] Canli sorgu hatasi, eski cache donuldu: {place_name} ({cache_category})")
                return (entry["pois"], meta) if return_meta else entry["pois"]

            meta = {
                "status": "error_live_fetch",
                "source": "live",
                "last_updated": None,
                "age_seconds": None,
                "soft_ttl_seconds": soft_ttl_seconds,
                "hard_ttl_seconds": hard_ttl_seconds,
                "empty_ttl_seconds": empty_ttl_seconds,
                "background_refresh": False,
                "force_refresh": force_refresh,
                "error": "live_query_failed",
            }
            return ([], meta) if return_meta else []

        # Hata yok, sonuc yok
        pois = []
    else:
        pois = _rows_to_poi_list(gdf, category_hint or "semantic")

    _write_poi_cache_entry(place_name, cache_category, pois)

    now_iso = _utc_now().isoformat()
    meta = {
        "status": "forced_live_refresh" if force_refresh else ("live_refresh_after_expiry" if entry is not None else "live_fetch"),
        "source": "live",
        "last_updated": now_iso,
        "age_seconds": 0,
        "soft_ttl_seconds": soft_ttl_seconds,
        "hard_ttl_seconds": hard_ttl_seconds,
        "empty_ttl_seconds": empty_ttl_seconds,
        "background_refresh": False,
        "force_refresh": force_refresh,
    }

    print(f"[POI] {len(pois)} POI bulundu: {place_name} (tags={normalized_tags})")
    return (pois, meta) if return_meta else pois


def search_pois(
    place_name: str,
    category: str,
    search_mode: str = "auto",
    force_refresh: bool = False,
    return_meta: bool = False,
):
    """
    Belirtilen bolgede POI arar.

    Returns:
        - return_meta=False: list
        - return_meta=True: tuple[list, dict]
    """
    print(f"[POI] arama baslatildi: {place_name}, kategori={category}")
    from osm_poi_dictionary import POI_MAPPING

    normalized_category = category.lower().strip()
    if normalized_category in POI_MAPPING:
        tags = POI_MAPPING[normalized_category]
    else:
        tags = {"tourism": normalized_category}

    return search_pois_by_tags(
        place_name,
        tags,
        category_hint=normalized_category,
        search_mode=search_mode,
        force_refresh=force_refresh,
        return_meta=return_meta,
    )
def search_poi_by_name_fuzzy(query_name: str, place_name: str = None) -> list:
    """
    Yerel POI veritabanında 'query_name' (Örn: "Fener Stadyumu") değerini
    yaklaşık (fuzzy) olarak arar. Bulunursa döndürür.
    """
    import sqlite3
    import json
    import difflib

    query_name_lower = query_name.lower().strip()
    results = []

    try:
        conn = sqlite3.connect(POI_DB_PATH)
        cursor = conn.cursor()
        
        if place_name:
            cursor.execute('SELECT data_json FROM pois WHERE place_name = ?', (place_name.lower(),))
        else:
            cursor.execute('SELECT data_json FROM pois')
            
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            pois_list = json.loads(row[0])
            for poi in pois_list:
                name = poi.get("name", "").lower()
                if not name or name == "isimsiz": continue
                
                # Basit kapsama (substring)
                if query_name_lower in name:
                    results.append((1.0, poi))
                    continue
                    
                # fuzzy matching (benzerlik oranı)
                ratio = difflib.SequenceMatcher(None, query_name_lower, name).ratio()
                if ratio > 0.65:  # %65 benzerlik sınırı
                    results.append((ratio, poi))
                    
        # Benzerliğe göre sırala
        results.sort(key=lambda x: x[0], reverse=True)
        
        unique_pois = []
        seen = set()
        for _, poi in results:
            key = (poi["lat"], poi["lon"])
            if key not in seen:
                seen.add(key)
                unique_pois.append(poi)
                
        if unique_pois:
            print(f"[POI] fuzzy match başarılı. '{query_name}' için {len(unique_pois)} sonuç.")
            return unique_pois
    except Exception as e:
        print(f"[POI] fuzzy arama hatası: {e}")
        
    print(f"[POI] fuzzy match bulunamadı: '{query_name}'.")
    return []


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


