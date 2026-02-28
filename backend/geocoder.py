"""
geocoder.py - Yer ismi ⇄ Koordinat dönüşüm modülü

Nominatim API (OpenStreetMap) kullanarak:
- Yer ismi → koordinat (geocode)
- Koordinat → yer ismi (reverse_geocode)

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

# SQLite cache dosyası
CACHE_DB = os.path.join(CACHE_DIR, "geocodes.db")

# Nominatim API ayarları
NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
NOMINATIM_SEARCH_URL = f"{NOMINATIM_BASE_URL}/search"
NOMINATIM_REVERSE_URL = f"{NOMINATIM_BASE_URL}/reverse"

# Rate limiting: 1 request/saniye (Nominatim kullanım şartı)
RATE_LIMIT_SECONDS = 1.0
_last_request_time = 0.0

# Memory cache (uygulama ömrü boyunca)
_geocode_cache: Dict[str, dict] = {}
_reverse_geocode_cache: Dict[str, dict] = {}


# =============================================================================
# Exception Sınıfları
# =============================================================================

class LocationNotFoundError(Exception):
    """Yer bulunamadığında fırlatılır."""
    pass


class NetworkError(Exception):
    """Ağ hatasında fırlatılır."""
    pass


class InvalidQueryError(Exception):
    """Geçersiz sorguda fırlatılır."""
    pass


# =============================================================================
# Cache Fonksiyonları
# =============================================================================

def _init_cache_db() -> sqlite3.Connection:
    """
    SQLite cache veritabanını başlatır.

    Returns:
        sqlite3.Connection: Veritabanı bağlantısı
    """
    conn = sqlite3.connect(CACHE_DB)
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

    conn.commit()
    return conn


def _query_hash(query: str) -> str:
    """Sorgu string'i için hash üretir."""
    return hashlib.md5(query.encode("utf-8")).hexdigest()


def _lat_lon_key(lat: float, lon: float) -> str:
    """Koordinat için cache anahtarı üretir."""
    return f"{lat:.6f}_{lon:.6f}"


def _get_from_cache(query_hash: str, table: str = "geocodes") -> Optional[dict]:
    """
    SQLite cache'ten veri çeker.

    Args:
        query_hash: Cache anahtarı
        table: Tablo adı ("geocodes" veya "reverse_geocodes")

    Returns:
        dict veya None
    """
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

        conn.close()
    except Exception as e:
        print(f"[Geocoder] Cache okuma hatası: {e}")

    return None


def _save_to_cache(query_hash: str, data: dict, table: str = "geocodes") -> None:
    """
    Veriyi SQLite cache'e kaydeder.

    Args:
        query_hash: Cache anahtarı
        data: Kaydedilecek veri
        table: Tablo adı
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
        print(f"[Geocoder] Cache yazma hatası: {e}")


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
# API Fonksiyonları
# =============================================================================

def geocode(place_name: str) -> dict:
    """
    Yer ismini koordinata çevirir.

    Args:
        place_name: Yer ismi (örn: "Kadıköy, İstanbul")

    Returns:
        dict: Success veya error response
        - Success: {"status": "success", "lat": 40.99, "lon": 29.03, "display_name": "..."}
        - Error: {"status": "error", "error_type": "...", "message": "...", "suggestions": []}
    """
    if not place_name or not isinstance(place_name, str):
        return {
            "status": "error",
            "error_type": "invalid_query",
            "message": "Yer ismi boş olamaz."
        }

    place_name = place_name.strip()

    if len(place_name) < 2:
        return {
            "status": "error",
            "error_type": "invalid_query",
            "message": "Yer ismi çok kısa."
        }

    # 1) Memory cache kontrol
    cache_key = place_name.lower()
    if cache_key in _geocode_cache:
        print(f"[Geocoder] Memory cache hit: {place_name}")
        return {
            "status": "success",
            **_geocode_cache[cache_key],
            "cached": True
        }

    # 2) SQLite cache kontrol
    qhash = _query_hash(place_name)
    cached_data = _get_from_cache(qhash, "geocodes")
    if cached_data:
        print(f"[Geocoder] SQLite cache hit: {place_name}")
        _geocode_cache[cache_key] = cached_data
        return {
            "status": "success",
            **cached_data,
            "cached": True
        }

    # 3) Nominatim API çağrısı
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
        print(f"[Geocoder] Nominatim API çağrısı: {place_name}")
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
                "message": "API limit aşımı. Lütfen birkaç saniye bekleyin."
            }

        response.raise_for_status()
        data = response.json()

        if not data or len(data) == 0:
            return {
                "status": "error",
                "error_type": "not_found",
                "message": f"'{place_name}' bulunamadı.",
                "suggestions": []
            }

        # İlk sonucu al
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

        print(f"[Geocoder] Bulundu: {display_name} → ({lat:.6f}, {lon:.6f})")

        return {
            "status": "success",
            **geo_data,
            "cached": False
        }

    except requests.Timeout:
        return {
            "status": "error",
            "error_type": "network",
            "message": "API yanıt vermedi (timeout)."
        }
    except requests.ConnectionError:
        return {
            "status": "error",
            "error_type": "network",
            "message": "İnternet bağlantısı yok."
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "unknown",
            "message": f"Beklenmeyen hata: {str(e)}"
        }


def reverse_geocode(lat: float, lon: float) -> dict:
    """
    Koordinatı yer ismine çevirir.

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
            "message": "Geçersiz koordinat formatı."
        }

    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return {
            "status": "error",
            "error_type": "invalid_query",
            "message": "Koordinat aralığı dışında."
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

    # 3) Nominatim API çağrısı
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
        print(f"[Geocoder] Reverse geocode API çağrısı: ({lat:.6f}, {lon:.6f})")
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
                "message": "Bu koordinat için yer bilgisi bulunamadı."
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
            "message": "API yanıt vermedi (timeout)."
        }
    except requests.ConnectionError:
        return {
            "status": "error",
            "error_type": "network",
            "message": "İnternet bağlantısı yok."
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "unknown",
            "message": f"Beklenmeyen hata: {str(e)}"
        }


def geocode_batch(place_names: List[str]) -> List[dict]:
    """
    Toplu geocoding işlemi. Her sorgu arası rate limit uygular.

    Args:
        place_names: Yer isimleri listesi

    Returns:
        list[dict]: Her bir sorgu için response
    """
    if not place_names:
        return []

    results = []
    for i, place_name in enumerate(place_names):
        print(f"[Geocoder] Batch işleniyor: {i+1}/{len(place_names)} - {place_name}")
        result = geocode(place_name)
        results.append(result)

    return results
