"""
geocoder.py - Yer ismi <-> Koordinat dönüşüm modülü

Nominatim API (OpenStreetMap) kullanarak:
- Yer ismi -> koordinat (geocode)
- Koordinat -> yer ismi (reverse_geocode)

Çift katmanlı cache (memory + SQLite) ve rate limiting desteği.
"""

import os
import time
import sqlite3
import hashlib
import requests
from typing import List, Dict, Optional

# Cache dizini
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# SQLite cache dosyasÄ±
CACHE_DB = os.path.join(CACHE_DIR, "geocodes.db")

# Nominatim API ayarlarÄ±
NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
NOMINATIM_SEARCH_URL = f"{NOMINATIM_BASE_URL}/search"
NOMINATIM_REVERSE_URL = f"{NOMINATIM_BASE_URL}/reverse"

# Rate limiting: 1 request/saniye (Nominatim kullanÄ±m ÅŸartÄ±)
RATE_LIMIT_SECONDS = 1.0
_last_request_time = 0.0

# Memory cache (uygulama Ã¶mrÃ¼ boyunca)
_geocode_cache: Dict[str, dict] = {}
_reverse_geocode_cache: Dict[str, dict] = {}


# =============================================================================
# Exception SÄ±nÄ±flarÄ±
# =============================================================================

class LocationNotFoundError(Exception):
    """Yer bulunamadÄ±ÄŸÄ±nda fÄ±rlatÄ±lÄ±r."""
    pass


class NetworkError(Exception):
    """AÄŸ hatasÄ±nda fÄ±rlatÄ±lÄ±r."""
    pass


class InvalidQueryError(Exception):
    """GeÃ§ersiz sorguda fÄ±rlatÄ±lÄ±r."""
    pass


# =============================================================================
# Cache FonksiyonlarÄ±
# =============================================================================

def _init_cache_db() -> sqlite3.Connection:
    """
    SQLite cache veritabanÄ±nÄ± baÅŸlatÄ±r.
    PRAGMA optimizasyonlarÄ± uygulanÄ±r (WAL, cache, mmap).

    Returns:
        sqlite3.Connection: VeritabanÄ± baÄŸlantÄ±sÄ±
    """
    conn = sqlite3.connect(CACHE_DB)

    # Performans optimizasyonlarÄ± (PERFORMANS_OPTIMIZASYON_PLANI.md â€” Faz 1)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -1048576;")   # 1 GB RAM cache
    conn.execute("PRAGMA mmap_size = 1073741824;")  # 1 GB memory-mapped I/O
    conn.execute("PRAGMA temp_store = MEMORY;")

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS geocodes (
            query_hash TEXT PRIMARY KEY,
            lat REAL,
            lon REAL,
            display_name TEXT,
            address TEXT,
            timestamp REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reverse_geocodes (
            lat_lon_key TEXT PRIMARY KEY,
            display_name TEXT,
            address TEXT,
            timestamp REAL
        )
    """)

    # TTL purge icin timestamp indeksleri
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_geocodes_timestamp ON geocodes(timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reverse_geocodes_timestamp ON reverse_geocodes(timestamp);")

    conn.commit()
    return conn


def purge_old_geocodes(days: int = 90) -> int:
    """
    Belirtilen gunden eski geocode cache kayitlarini siler.
    geocodes.db'nin suresiz buyumesini onler.

    Args:
        days: Silinecek kayitlarin yasi (gun). Varsayilan 90.

    Returns:
        int: Silinen toplam kayit sayisi
    """
    ttl_days = max(1, int(days))
    cutoff = time.time() - (ttl_days * 24 * 60 * 60)
    deleted = 0
    conn = None
    try:
        conn = _init_cache_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM geocodes WHERE timestamp < ?", (cutoff,))
        deleted += cursor.rowcount
        cursor.execute("DELETE FROM reverse_geocodes WHERE timestamp < ?", (cutoff,))
        deleted += cursor.rowcount
        conn.commit()
        if deleted > 0:
            print(f"[Geocoder] TTL purge: {deleted} eski kayit silindi ({ttl_days} gunden eski)")
    except Exception as e:
        print(f"[Geocoder] Purge hatasi: {e}")
    finally:
        if conn is not None:
            conn.close()
    return deleted

def _query_hash(query: str) -> str:
    """Sorgu string'i iÃ§in hash Ã¼retir."""
    return hashlib.md5(query.encode("utf-8")).hexdigest()


def _lat_lon_key(lat: float, lon: float) -> str:
    """Koordinat iÃ§in cache anahtarÄ± Ã¼retir."""
    return f"{lat:.6f}_{lon:.6f}"


def _get_from_cache(query_hash: str, table: str = "geocodes") -> Optional[dict]:
    """
    SQLite cache'ten veri Ã§eker.

    Args:
        query_hash: Cache anahtarÄ±
        table: Tablo adÄ± ("geocodes" veya "reverse_geocodes")

    Returns:
        dict veya None
    """
    conn = None
    try:
        conn = _init_cache_db()
        cursor = conn.cursor()

        if table == "geocodes":
            cursor.execute(
                "SELECT lat, lon, display_name, address FROM geocodes WHERE query_hash = ?",
                (query_hash,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "lat": float(row[0]),
                    "lon": float(row[1]),
                    "display_name": row[2],
                    "address": row[3]
                }
        else:  # reverse_geocodes
            cursor.execute(
                "SELECT display_name, address FROM reverse_geocodes WHERE lat_lon_key = ?",
                (query_hash,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "display_name": row[0],
                    "address": row[1]
                }
    except Exception as e:
        print(f"[Geocoder] Cache okuma hatasÄ±: {e}")
    finally:
        if conn is not None:
            conn.close()

    return None


def _save_to_cache(query_hash: str, data: dict, table: str = "geocodes") -> None:
    """
    Veriyi SQLite cache'e kaydeder.

    Args:
        query_hash: Cache anahtarÄ±
        data: Kaydedilecek veri
        table: Tablo adÄ±
    """
    try:
        conn = _init_cache_db()
        cursor = conn.cursor()
        current_time = time.time()

        if table == "geocodes":
            cursor.execute(
                """
                INSERT OR REPLACE INTO geocodes
                (query_hash, lat, lon, display_name, address, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    query_hash,
                    data.get("lat"),
                    data.get("lon"),
                    data.get("display_name"),
                    data.get("address", ""),
                    current_time
                )
            )
        else:  # reverse_geocodes
            cursor.execute(
                """
                INSERT OR REPLACE INTO reverse_geocodes
                (lat_lon_key, display_name, address, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (
                    query_hash,
                    data.get("display_name"),
                    data.get("address", ""),
                    current_time
                )
            )

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Geocoder] Cache yazma hatasÄ±: {e}")


# =============================================================================
# Rate Limiter
# =============================================================================

def _rate_limit() -> None:
    """
    Nominatim API rate limitini uygular (1 req/s).
    Gerekirse bekler.
    """
    global _last_request_time

    current_time = time.time()
    elapsed = current_time - _last_request_time

    if elapsed < RATE_LIMIT_SECONDS:
        sleep_time = RATE_LIMIT_SECONDS - elapsed
        time.sleep(sleep_time)

    _last_request_time = time.time()


# =============================================================================
# API FonksiyonlarÄ±
# =============================================================================

def geocode(place_name: str) -> dict:
    """
    Yer ismini koordinata Ã§evirir.

    Args:
        place_name: Yer ismi (Ã¶rn: "KadÄ±kÃ¶y, Ä°stanbul")

    Returns:
        dict: Success veya error response
        - Success: {"status": "success", "lat": 40.99, "lon": 29.03, "display_name": "..."}
        - Error: {"status": "error", "error_type": "...", "message": "...", "suggestions": []}
    """
    print(f"[GEOCODER] Arama baslatildi: {place_name}")

    if not place_name or not isinstance(place_name, str):
        return {
            "status": "error",
            "error_type": "invalid_query",
            "message": "Yer ismi boÅŸ olamaz."
        }

    place_name = place_name.strip()

    if len(place_name) < 2:
        return {
            "status": "error",
            "error_type": "invalid_query",
            "message": "Yer ismi Ã§ok kÄ±sa."
        }

    # 1) Memory cache kontrol
    cache_key = place_name.lower()
    if cache_key in _geocode_cache:
        print(f"[GEOCODER] Memory CACHE HIT: {place_name}")
        return {
            "status": "success",
            **_geocode_cache[cache_key],
            "cached": True
        }

    # 2) Local places (Ã¶nceden tanÄ±mlÄ± yerler â€” API'ye gitmeden)
    from local_places import lookup as local_places_lookup
    local_result = local_places_lookup(place_name)
    if local_result:
        print(f"[GEOCODER] LOCAL PLACES HIT: {place_name}")
        _geocode_cache[cache_key] = local_result
        return {
            "status": "success",
            **local_result,
            "cached": True
        }

    # 3) SQLite cache kontrol
    qhash = _query_hash(place_name)
    cached_data = _get_from_cache(qhash, "geocodes")
    if cached_data:
        print(f"[GEOCODER] SQLite CACHE HIT: {place_name}")
        _geocode_cache[cache_key] = cached_data
        return {
            "status": "success",
            **cached_data,
            "cached": True
        }

    # 3) Nominatim API Ã§aÄŸrÄ±sÄ±
    _rate_limit()

    headers = {
        "User-Agent": "OpenRoutePlanner/1.0 (https://github.com/openrouteplanner)",
        "Accept": "application/json"
    }

    params = {
        "q": place_name,
        "format": "json",
        "limit": 1,
        "addressdetails": 1
    }

    try:
        print(f"[Geocoder] Nominatim API Ã§aÄŸrÄ±sÄ±: {place_name}")
        response = requests.get(
            NOMINATIM_SEARCH_URL,
            params=params,
            headers=headers,
            timeout=10
        )

        if response.status_code == 429:
            return {
                "status": "error",
                "error_type": "rate_limit",
                "message": "API limit aÅŸÄ±mÄ±. LÃ¼tfen birkaÃ§ saniye bekleyin."
            }

        response.raise_for_status()
        data = response.json()

        if not data or len(data) == 0:
            return {
                "status": "error",
                "error_type": "not_found",
                "message": f"'{place_name}' bulunamadÄ±.",
                "suggestions": []
            }

        # Ä°lk sonucu al
        result = data[0]
        lat = float(result.get("lat", 0))
        lon = float(result.get("lon", 0))
        display_name = result.get("display_name", "")

        # Response verisi
        geo_data = {
            "lat": lat,
            "lon": lon,
            "display_name": display_name,
            "address": str(result.get("address", {}))
        }

        # Cache'e kaydet
        _geocode_cache[cache_key] = geo_data
        _save_to_cache(qhash, geo_data, "geocodes")

        print(f"[GEOCODER] Bulundu: {display_name} -> ({lat:.6f}, {lon:.6f})")

        return {
            "status": "success",
            **geo_data,
            "cached": False
        }

    except requests.Timeout:
        return {
            "status": "error",
            "error_type": "network",
            "message": "API yanÄ±t vermedi (timeout)."
        }
    except requests.ConnectionError:
        return {
            "status": "error",
            "error_type": "network",
            "message": "Ä°nternet baÄŸlantÄ±sÄ± yok."
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "unknown",
            "message": f"Beklenmeyen hata: {str(e)}"
        }


def geocode_suggest(place_name: str, limit: int = 6) -> dict:
    """
    Yazarken Ã¶neri iÃ§in: Yer ismine gÃ¶re Ã§oklu sonuÃ§ dÃ¶ner (autocomplete).

    Args:
        place_name: KÄ±smi veya tam yer ismi (Ã¶rn: "KadÄ±kÃ¶y", "Taksim M")
        limit: Maksimum Ã¶neri sayÄ±sÄ± (varsayÄ±lan 6)

    Returns:
        dict: {"status": "success", "suggestions": [{"lat": 40.99, "lon": 29.03, "display_name": "..."}, ...]}
        veya {"status": "error", "message": "..."}
    """
    if not place_name or not isinstance(place_name, str):
        return {"status": "success", "suggestions": []}

    place_name = place_name.strip()
    if len(place_name) < 2:
        return {"status": "success", "suggestions": []}

    _rate_limit()

    headers = {
        "User-Agent": "OpenRoutePlanner/1.0 (https://github.com/openrouteplanner)",
        "Accept": "application/json"
    }
    params = {
        "q": place_name,
        "format": "json",
        "limit": min(limit, 10),
        "addressdetails": 0,
    }

    try:
        response = requests.get(
            NOMINATIM_SEARCH_URL,
            params=params,
            headers=headers,
            timeout=5
        )
        if response.status_code == 429:
            return {"status": "error", "message": "API limit. Bekleyin.", "suggestions": []}
        response.raise_for_status()
        data = response.json()

        suggestions = []
        for item in data:
            suggestions.append({
                "lat": float(item.get("lat", 0)),
                "lon": float(item.get("lon", 0)),
                "display_name": item.get("display_name", ""),
            })
        return {"status": "success", "suggestions": suggestions}
    except Exception as e:
        print(f"[Geocoder] Suggest hatasÄ±: {e}")
        return {"status": "success", "suggestions": []}


def reverse_geocode(lat: float, lon: float) -> dict:
    """
    KoordinatÄ± yer ismine Ã§evirir.

    Args:
        lat: Enlem
        lon: Boylam

    Returns:
        dict: Success veya error response
        - Success: {"status": "success", "display_name": "...", "address": {...}}
    """
    # Validasyon
    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return {
            "status": "error",
            "error_type": "invalid_query",
            "message": "GeÃ§ersiz koordinat formatÄ±."
        }

    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return {
            "status": "error",
            "error_type": "invalid_query",
            "message": "Koordinat aralÄ±ÄŸÄ± dÄ±ÅŸÄ±nda."
        }

    # 1) Memory cache kontrol
    cache_key = _lat_lon_key(lat, lon)
    if cache_key in _reverse_geocode_cache:
        print(f"[Geocoder] Reverse memory cache hit: ({lat:.6f}, {lon:.6f})")
        return {
            "status": "success",
            **_reverse_geocode_cache[cache_key],
            "cached": True
        }

    # 2) SQLite cache kontrol
    cached_data = _get_from_cache(cache_key, "reverse_geocodes")
    if cached_data:
        print(f"[Geocoder] Reverse SQLite cache hit: ({lat:.6f}, {lon:.6f})")
        _reverse_geocode_cache[cache_key] = cached_data
        return {
            "status": "success",
            **cached_data,
            "cached": True
        }

    # 3) Nominatim API Ã§aÄŸrÄ±sÄ±
    _rate_limit()

    headers = {
        "User-Agent": "OpenRoutePlanner/1.0 (https://github.com/openrouteplanner)",
        "Accept": "application/json"
    }

    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1
    }

    try:
        print(f"[Geocoder] Reverse geocode API Ã§aÄŸrÄ±sÄ±: ({lat:.6f}, {lon:.6f})")
        response = requests.get(
            NOMINATIM_REVERSE_URL,
            params=params,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()
        data = response.json()

        if "error" in data:
            return {
                "status": "error",
                "error_type": "not_found",
                "message": "Bu koordinat iÃ§in yer bilgisi bulunamadÄ±."
            }

        display_name = data.get("display_name", "")
        address = data.get("address", {})

        # Response verisi
        rev_data = {
            "display_name": display_name,
            "address": str(address) if address else ""
        }

        # Cache'e kaydet
        _reverse_geocode_cache[cache_key] = rev_data
        _save_to_cache(cache_key, rev_data, "reverse_geocodes")

        print(f"[Geocoder] Reverse geocode: {display_name}")

        return {
            "status": "success",
            **rev_data,
            "cached": False
        }

    except requests.Timeout:
        return {
            "status": "error",
            "error_type": "network",
            "message": "API yanÄ±t vermedi (timeout)."
        }
    except requests.ConnectionError:
        return {
            "status": "error",
            "error_type": "network",
            "message": "Ä°nternet baÄŸlantÄ±sÄ± yok."
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "unknown",
            "message": f"Beklenmeyen hata: {str(e)}"
        }


def geocode_batch(place_names: List[str]) -> List[dict]:
    """
    Toplu geocoding iÅŸlemi. Her sorgu arasÄ± rate limit uygular.

    Args:
        place_names: Yer isimleri listesi

    Returns:
        list[dict]: Her bir sorgu iÃ§in response
    """
    if not place_names:
        return []

    results = []
    for i, place_name in enumerate(place_names):
        print(f"[Geocoder] Batch iÅŸleniyor: {i+1}/{len(place_names)} - {place_name}")
        result = geocode(place_name)
        results.append(result)

    return results

