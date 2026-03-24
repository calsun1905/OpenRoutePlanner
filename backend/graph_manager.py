"""
graph_manager.py - OSMnx ile harita verisi yÃ¶netimi

Harita verilerini OpenStreetMap'ten indirir, .graphml olarak cache'ler,
ve POI (Points of Interest) aramalarÄ±nÄ± gerÃ§ekleÅŸtirir.
"""

import os
import sqlite3
import json
import hashlib
import threading
from datetime import datetime, timezone
import osmnx as ox
import networkx as nx
from route_config import ROUTE_CONFIG

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
    conn.commit()
    conn.close()

_init_poi_db()

_POI_REFRESH_LOCK = threading.Lock()
_POI_REFRESH_INFLIGHT = set()


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


def _write_poi_cache_entry(place_name: str, cache_category: str, pois: list) -> None:
    """
    Yerel DB cache kaydini gunceller.
    """
    try:
        conn = sqlite3.connect(POI_DB_PATH)
        cursor = conn.cursor()
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


def _cache_path(place_name: str) -> str:
    """Verilen yer adÄ± iÃ§in cache dosya yolunu dÃ¶ner."""
    safe_name = place_name.replace(",", "").replace(" ", "_").lower()
    return os.path.join(DATA_DIR, f"{safe_name}.graphml")


def get_graph(place_name: str = "Kadikoy, Istanbul, Turkey"):
    """
    Belirtilen bÃ¶lgenin yÃ¼rÃ¼yÃ¼ÅŸ grafiÄŸini dÃ¶ner.
    Ä°lk Ã§aÄŸrÄ±da internetten indirir ve .graphml olarak cache'ler.
    Sonraki Ã§aÄŸrÄ±larda dosyadan okur (Ã§ok daha hÄ±zlÄ±).
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
    SeÃ§ilen noktalarÄ±n merkezinden, tÃ¼m noktalarÄ± kapsayacak
    yarÄ±Ã§apla graf indirir. graph_from_point kullanÄ±r (bbox'tan Ã§ok daha hÄ±zlÄ±).
    
    Args:
        points: [(lat, lon), ...] koordinat listesi
    
    Returns:
        networkx.MultiDiGraph: YÃ¼rÃ¼yÃ¼ÅŸ grafiÄŸi
    """
    import math
    
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    
    # Merkez noktayÄ± hesapla
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)
    
    # En uzak noktaya olan mesafeyi hesapla (metre cinsinden)
    max_dist = 0
    for lat, lon in points:
        # Haversine yaklaÅŸÄ±mÄ± (basit)
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

    # Minimum yarÄ±Ã§ap + padding uygula. Maksimum deÄŸeri config yÃ¶netir.
    radius = min(max_radius, max(min_radius, max_dist + padding))
    
    # Cache key: merkez + yarÄ±Ã§ap
    cache_key = f"point_{center_lat:.4f}_{center_lon:.4f}_{int(radius)}"
    cache_file = os.path.join(DATA_DIR, f"{cache_key}.graphml")
    
    if os.path.exists(cache_file):
        print(f"[GraphManager] Cache'den okunuyor: {cache_file}")
        G = ox.load_graphml(cache_file)
    else:
        print(f"[GraphManager] Graf indiriliyor: merkez=({center_lat:.4f}, {center_lon:.4f}), yarÄ±Ã§ap={int(radius)}m")
        G = ox.graph_from_point((center_lat, center_lon), dist=radius, network_type="walk")
        ox.save_graphml(G, cache_file)
        print(f"[GraphManager] Cache'e kaydedildi: {cache_file}")
    
    return G


def find_nearest_node(G, lat: float, lon: float) -> int:
    """
    Verilen koordinata (lat, lon) en yakÄ±n graf dÃ¼ÄŸÃ¼mÃ¼nÃ¼ bulur.
    
    nearest_edges kullanarak en yakÄ±n yol kenarÄ±nÄ± bulur, sonra
    o kenarÄ±n uÃ§ noktalarÄ±ndan kullanÄ±cÄ±ya en yakÄ±n olanÄ± seÃ§er.
    Bu sayede ana caddeye deÄŸil, gerÃ§ekten en yakÄ±n sokaÄŸa snap edilir.
    
    Args:
        G: NetworkX grafiÄŸi
        lat: Enlem
        lon: Boylam
    
    Returns:
        int: En yakÄ±n dÃ¼ÄŸÃ¼m ID'si
    """
    try:
        # En yakÄ±n yol kenarÄ±nÄ± bul (u, v, key)
        u, v, _ = ox.nearest_edges(G, X=lon, Y=lat)
        
        # KenarÄ±n iki uÃ§ noktasÄ±ndan kullanÄ±cÄ±ya en yakÄ±n olanÄ± seÃ§
        u_data = G.nodes[u]
        v_data = G.nodes[v]

        dist_u = ((u_data["y"] - lat) ** 2 + (u_data["x"] - lon) ** 2)
        dist_v = ((v_data["y"] - lat) ** 2 + (v_data["x"] - lon) ** 2)

        return u if dist_u <= dist_v else v
    except Exception as e:
        # Fallback: nearest_nodes kullan
        print(f"[GraphManager] Manuel nearest node hatasÄ±, fallback kullanÄ±lÄ±yor: {e}")
        return ox.nearest_nodes(G, X=lon, Y=lat)


def _rows_to_poi_list(gdf, category_label: str) -> list:
    """OSMnx dataframe satÄ±rlarÄ±nÄ± API POI listesine dÃ¶nÃ¼ÅŸtÃ¼rÃ¼r."""
    pois = []
    for _, row in gdf.iterrows():
        try:
            centroid = row.geometry.centroid
            name = row.get("name", "Ä°simsiz")
            if name is None or (hasattr(name, "__len__") and len(str(name)) == 0):
                name = "Ä°simsiz"

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
            print(f"[POI] POI verisi hatasÄ± (atlanÄ±yor): {e}")
            continue
    return pois


def _resolve_search_center(place_name: str):
    """Yer adÄ±nÄ± merkez koordinata Ã§evirir (geo-bound zorunluluÄŸu)."""
    if not geocode or not place_name:
        return None

    try:
        result = geocode(place_name)
    except Exception as e:
        print(f"[POI] Geocode hatasÄ±: {e}")
        return None

    if not isinstance(result, dict) or result.get("status") != "success":
        return None

    try:
        lat = float(result.get("lat"))
        lon = float(result.get("lon"))
        return lat, lon
    except (TypeError, ValueError):
        return None


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

    # Il/genis alan sorgularinda dogrudan tum place siniri taransin.
    if search_mode == "place_boundary_only":
        try:
            print("[POI] Search mode: place_boundary_only (tum il siniri)")
            gdf = ox.features_from_place(place_name, tags=normalized_tags)
            if gdf is None:
                return None, False
            return gdf, False
        except Exception as e:
            print(f"[POI] place-boundary sorgu hatasi: {e}")
            return None, True

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

    category_hint = (category_hint or "semantic").lower()
    search_mode = (search_mode or "auto").strip().lower()
    cache_category = f"{category_hint}|{_build_tags_cache_suffix(normalized_tags)}|mode:{search_mode}"
    print(
        f"[POI] Arama baslatildi (tags): {place_name}, "
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
    print(f"[POI] Arama baslatildi: {place_name}, kategori={category}")
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
    Yerel POI veritabanÄ±nda 'query_name' (Ã–rn: "Fener Stadyumu") deÄŸerini
    yaklaÅŸÄ±k (fuzzy) olarak arar. Bulunursa dÃ¶ndÃ¼rÃ¼r.
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
                    
                # Fuzzy matching (benzerlik oranÄ±)
                ratio = difflib.SequenceMatcher(None, query_name_lower, name).ratio()
                if ratio > 0.65:  # %65 benzerlik sÄ±nÄ±rÄ±
                    results.append((ratio, poi))
                    
        # BenzerliÄŸe gÃ¶re sÄ±rala
        results.sort(key=lambda x: x[0], reverse=True)
        
        unique_pois = []
        seen = set()
        for _, poi in results:
            key = (poi["lat"], poi["lon"])
            if key not in seen:
                seen.add(key)
                unique_pois.append(poi)
                
        if unique_pois:
            print(f"[POI] Fuzzy match baÅŸarÄ±lÄ±. '{query_name}' iÃ§in {len(unique_pois)} sonuÃ§.")
            return unique_pois
    except Exception as e:
        print(f"[POI] Fuzzy arama hatasÄ±: {e}")
        
    print(f"[POI] Fuzzy match bulunamadÄ±: '{query_name}'.")
    return []


# =============================================================================
# GRAPH PRELOADING - PopÃ¼ler bÃ¶lgeler iÃ§in hÄ±zlÄ± eriÅŸim
# =============================================================================

# PopÃ¼ler bÃ¶lgeler (TÃ¼rkiye'nin en Ã§ok kullanÄ±lan bÃ¶lgeleri)
# Uygulama baÅŸladÄ±ÄŸÄ±nda bu bÃ¶lgelerin grafileri Ã¶n yÃ¼klenir
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
    PopÃ¼ler bÃ¶lgelerin grafilerini Ã¶n yÃ¼kler.
    Uygulama baÅŸlangÄ±cÄ±nda Ã§aÄŸrÄ±lmalÄ±dÄ±r.
    Ä°lk rota hesaplamalarÄ±nÄ± %80 daha hÄ±zlÄ± yapar.
    """
    import threading

    def _preload_region(place_name):
        try:
            print(f"[GraphPreload] Ã–n yÃ¼kleniyor: {place_name}")
            G = get_graph(place_name)
            _preloaded_graphs[place_name] = G

            # LRU cache'e de ekle (preload Ã¶nceliÄŸi yÃ¼ksek)
            from cache_manager import get_graph_cache
            cache = get_graph_cache()
            cache.put(place_name, G, preloaded=True)

            print(f"[GraphPreload] YÃ¼klendi: {place_name}")
        except Exception as e:
            print(f"[GraphPreload] Hata {place_name}: {e}")

    # Paralel yÃ¼klemeyi baÅŸlat
    threads = []
    for region in POPULAR_REGIONS:
        t = threading.Thread(target=_preload_region, args=(region,))
        t.start()
        threads.append(t)

    # TÃ¼m thread'lerin tamamlanmasÄ±nÄ± bekle
    for t in threads:
        t.join()

    print(f"[GraphPreload] {len(_preloaded_graphs)} bÃ¶lge Ã¶n yÃ¼klendi")


def is_preloaded(place_name: str) -> bool:
    """
    Belirtilen bÃ¶lgenin grafiklerinin Ã¶nceden yÃ¼klenip yÃ¼klenmediÄŸini kontrol eder.
    """
    return place_name in _preloaded_graphs


def get_preloaded_graph(place_name: str):
    """
    Ã–nceden yÃ¼klenmiÅŸ grafÄ± dÃ¶ner. Varsa cache'ten alÄ±r, yoksa None dÃ¶ner.
    """
    return _preloaded_graphs.get(place_name)


