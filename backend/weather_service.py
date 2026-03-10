"""
weather_service.py - OpenMeteo API entegrasyonu

Güncel hava durumu, saatlik forecast ve rota boyunca hava kontrolü.
Cache mekanizması ile performans optimizasyonu.

Author: OpenRoutePlanner
Created: 2026-03-10
"""

import time
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

# Local imports
import logging
from weather_utils import (
    validate_coordinates,
    validate_hours,
    parse_weather_code,
    get_weather_emoji,
    build_cache_key,
    get_weather_alert,
    summarize_weather_data
)

# =============================================================================
# Constants
# =============================================================================

OPENMETEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL_SECONDS = 900  # 15 dakika
REQUEST_TIMEOUT = 10  # saniye

# Current weather variables
CURRENT_WEATHER_PARAMS = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "showers",
    "snowfall",
    "weather_code",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m"
]

# Hourly weather variables
HOURLY_WEATHER_PARAMS = [
    "temperature_2m",
    "precipitation",
    "precipitation_probability",
    "weather_code",
    "wind_speed_10m",
    "wind_gusts_10m"
]

# =============================================================================
# Logger Setup
# =============================================================================

logger = logging.getLogger(__name__)

# =============================================================================
# Global Cache
# =============================================================================

_weather_cache: Dict[str, dict] = {}

# =============================================================================
# Exception Classes
# =============================================================================

class WeatherServiceError(Exception):
    """Base exception for weather service"""
    pass


class InvalidCoordinatesError(WeatherServiceError):
    """Invalid coordinates provided"""
    pass


class NetworkError(WeatherServiceError):
    """Network error occurred"""
    pass


class RateLimitError(WeatherServiceError):
    """Rate limit exceeded"""
    pass


class ParseError(WeatherServiceError):
    """Failed to parse API response"""
    pass


# =============================================================================
# Cache Functions
# =============================================================================

def _get_from_cache(key: str) -> Optional[dict]:
    """
    Memory cache'ten veri cekme.

    AÇIKLAMA:
    Bu ozel (private) fonksiyon, global _weather_cache sozlugundan veri cekmek
    icin kullanilir. Verinin TTL (time-to-live) suresi gecmis mi kontrol eder,
    gectiyse cache'i temizler. Bu fonksiyon sadece modul icerisinden cagrilir.

    Ornekler:
    - Cache var ve gecerli ise: {"data": {...}, "timestamp": ..., "cache_hit": True}
    - Cache yok veya gecmis ise: None

    NASIL CALISIR:
    1. Verilen anahtar cache'te var mi kontrol eder
    2. Varsa, zaman damgasini kontrol eder (TTL 900 saniye = 15 dakika)
    3. Gecerli ise cache_hit=True ile veriyi doner
    4. Gecmis ise cache'ten siler ve None doner
    5. Cache'te yoksa None doner

    KULLANIM ALANI:
    Hava durumu isteklerinde API cagrisi yapmadan once cache kontrolu
    yapmak icin kullanilir. API yukunu azaltir.

    Args:
        key: Cache anahtari

    Returns:
        dict or None: Cache verisi veya None (miss)
    """
    global _weather_cache

    if key in _weather_cache:
        cached_data = _weather_cache[key]

        # TTL kontrolu
        if _is_cache_valid(cached_data.get("timestamp", 0)):
            logger.debug(f"Cache hit for key: {key}")
            cached_data["cache_hit"] = True
            return cached_data
        else:
            # Expired cache'i sil
            del _weather_cache[key]
            logger.debug(f"Cache expired for key: {key}")

    logger.debug(f"Cache miss for key: {key}")
    return None


def _save_to_cache(key: str, data: dict) -> None:
    """
    Memory cache'e veri kaydetme.

    AÇIKLAMA:
    Bu ozel (private) fonksiyon, API'den gelen hava durumu verisini global
    _weather_cache sozlugune kaydetmek icin kullanilir. Kaydederken zaman
    damgasini da ekler, boylece TTL kontrolu yapilabilir.

    Ornekler:
    - _save_to_cache("current:41.0082:28.9784", {"temp": 20, ...})
      -> Cache'e yeni kayit ekler

    NASIL CALISIR:
    1. Su anki zaman damgasini alir (time.time())
    2. timestamp, data ve cache_hit=False iceren bir cache_entry olusturur
    3. Bu entry'yi _weather_cache sozlugune ekler
    4. Debug log yazar

    KULLANIM ALANI:
    API'den yeni veri cekildikten sonra bu veriyi cache'e kaydetmek
    icin kullanilir. Sonraki isteklerde ayni veriyi API'ye gitmeden doner.

    Args:
        key: Cache anahtari
        data: Kaydedilecek veri
    """
    global _weather_cache

    cache_entry = {
        "timestamp": time.time(),
        "data": data,
        "cache_hit": False
    }

    _weather_cache[key] = cache_entry
    logger.debug(f"Saved to cache: {key}")


def _is_cache_valid(timestamp: float) -> bool:
    """
    Cache gecerlilik kontrolu.

    AÇIKLAMA:
    Bu ozel (private) fonksiyon, verilen zaman damgasinin hala gecerli
    olup olmadigini kontrol eder. Cache TTL'si 900 saniye (15 dakika)
    olarak ayarlanmistir. Zaman damgasi su anki zamandan 900 saniye daha
    eski ise cache gecersiz sayilir.

    Ornekler:
    - Su anki zaman = 1000, timestamp = 900 -> True (gecerli, 100 saniye icinde)
    - Su anki zaman = 2000, timestamp = 1000 -> False (gecersiz, 1000 saniye gecmis)

    NASIL CALISIR:
    1. Su anki zaman damgasini alir (time.time())
    2. Su anki zamandan timestamp'i cikarir
    3. Fark 900 saniyeden kucukse True, yoksa False doner

    KULLANIM ALANI:
    Cache entry'lerinin TTL kontrolunu yapmak icin kullanilir.
    _get_from_cache fonksiyonu tarafindan cagrilir.

    Args:
        timestamp: Cache zaman damgasi

    Returns:
        bool: True if cache is still valid
    """
    current_time = time.time()
    return (current_time - timestamp) < CACHE_TTL_SECONDS


def clear_cache() -> int:
    """
    Tum cache'i temizler.

    AÇIKLAMA:
    Bu fonksiyon, global _weather_cache sozlugunu tamamen temizler.
    Tum kayitlari siler ve temizlenen kayit sayisini doner.
    Genellikle test veya bakim amaclariyla kullanilir.

    Ornekler:
    - Cache'te 10 kayit varken clear_cache() -> 10 doner, cache bosalir
    - Bos cache'te clear_cache() -> 0 doner

    NASIL CALISIR:
    1. Su anki cache boyutunu alir
    2. _weather_cache.clear() ile tumunu siler
    3. Bilgi log yazar ve temizlenen sayiyi doner

    KULLANIM ALANI:
    Testlerde, debug'da veya manuel cache invalidate
    isteklerinde kullanilir. Ayrica /api/weather/clear-cache
    endpoint'i tarafindan cagrilir.

    Returns:
        int: Temizlenen cache entry sayisi
    """
    global _weather_cache
    count = len(_weather_cache)
    _weather_cache.clear()
    logger.info(f"Cleared {count} cache entries")
    return count


def get_cache_stats() -> dict:
    """
    Cache istatistiklerini dondurur.

    AÇIKLAMA:
    Bu fonksiyon, mevcut cache durumunu ozetleyen istatistikler doner.
    Toplam kayit sayisi, gecerli kayit sayisi, gecmis kayit sayisi ve
    TTL suresi gibi bilgileri icerir.

    Ornekler:
    - get_cache_stats()
      -> {"total_entries": 5, "valid_entries": 3, "expired_entries": 2,
          "ttl_seconds": 900}

    NASIL CALISIR:
    1. Su anki cache boyutunu alir
    2. Her entry icin TTL kontrolu yapar
    3. Gecerli ve gecmis kayit sayilarini hesaplar
    4. Tum istatistikleri sozluk olarak doner

    KULLANIM ALANI:
    Cache performansini izlemek, debug etmek ve monitor etmek
    icin kullanilir. /api/weather/status endpoint'i tarafindan
    donulen bilginin bir parcasidir.

    Returns:
        dict: Cache istatistikleri
    """
    global _weather_cache

    valid_count = sum(
        1 for entry in _weather_cache.values()
        if _is_cache_valid(entry.get("timestamp", 0))
    )

    return {
        "total_entries": len(_weather_cache),
        "valid_entries": valid_count,
        "expired_entries": len(_weather_cache) - valid_count,
        "ttl_seconds": CACHE_TTL_SECONDS
    }


# =============================================================================
# API Request Functions
# =============================================================================

def _fetch_from_openmeteo(url: str) -> dict:
    """
    OpenMeteo API'sinden veri cekme.

    AÇIKLAMA:
    Bu ozel (private) fonksiyon, OpenMeteo API'sine HTTP GET istegi gonderir
    ve response'u doner. Hata durumlarini yakalar ve ozel exception'lar
    firlatir. Response suresini de log'lar.

    Ornekler:
    - _fetch_from_openmeteo("https://api.open-meteo.com/v1/forecast?...")
      -> JSON response doner veya exception firlatir

    NASIL CALISIR:
    1. URL'i log'lar ve baslangic zamanini kaydeder
    2. requests.get() ile API'ye istek atar (10 saniye timeout)
    3. Response suresini hesaplar ve log'lar
    4. Status code 429 ise RateLimitError firlatir
    5. Status code 200 degilse NetworkError veya ParseError firlatir
    6. JSON olarak response'u doner

    HATA DURUMLARI:
    - Timeout (10 saniye) -> NetworkError
    - Baglanti hatasi -> NetworkError
    - Rate limit (429) -> RateLimitError
    - Server hatasi (5xx) -> NetworkError
    - Client hatasi (4xx) -> ParseError
    - JSON parse hatasi -> ParseError

    KULLANIM ALANI:
    get_current_weather ve get_hourly_forecast fonksiyonlari
    tarafindan API'ye istek atmak icin kullanilir.

    Args:
        url: API URL

    Returns:
        dict: API response

    Raises:
        NetworkError: Baglanti hatasi
        RateLimitError: Rate limit asimi
        ParseError: Response parse hatasi
    """
    try:
        logger.info(f"Fetching from OpenMeteo: {url}")
        start_time = time.time()

        response = requests.get(url, timeout=REQUEST_TIMEOUT)

        response_time_ms = (time.time() - start_time) * 1000
        logger.info(
            "OpenMeteo response received: status=%s, response_time_ms=%s",
            response.status_code, round(response_time_ms, 2)
        )

        # Rate limit kontrolu
        if response.status_code == 429:
            raise RateLimitError("OpenMeteo rate limit exceeded")

        # Hata kontrolu
        if response.status_code != 200:
            error_msg = f"OpenMeteo API error: {response.status_code}"
            if response.status_code >= 500:
                raise NetworkError(error_msg)
            else:
                raise ParseError(error_msg)

        return response.json()

    except requests.exceptions.Timeout:
        raise NetworkError("Request timeout")
    except requests.exceptions.ConnectionError:
        raise NetworkError("Connection error")
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"Request failed: {str(e)}")
    except ValueError as e:
        raise ParseError(f"Failed to parse JSON: {str(e)}")


def _build_url_current(lat: float, lon: float) -> str:
    """
    Güncel hava durumu URL'i olusturur.

    AÇIKLAMA:
    Bu ozel (private) fonksiyon, OpenMeteo API'sinde guncel hava durumu
    cekmek icin gerekli URL'i olusturur. URL, enlem, boylam ve istenen
    hava durumu parametrelerini icerir.

    Ornekler:
    - _build_url_current(41.0082, 28.9784)
      -> "https://api.open-meteo.com/v1/forecast?latitude=41.0082&longitude=28.9784
         &current=temperature_2m,relative_humidity_2m,...&timezone=auto"

    NASIL CALISIR:
    1. Latitude ve longitude parametrelerini ekler
    2. CURRENT_WEATHER_PARAMS listesindeki tum parametreleri ekler
    3. Timezone=auto ekler (otomatik zaman dilimi)
    4. Tam URL'i doner

    KULLANIM ALANI:
    get_current_weather fonksiyonu tarafindan API URL'i olusturmak
    icin kullanilir.

    Args:
        lat: Enlem
        lon: Boylam

    Returns:
        str: OpenMeteo API URL
    """
    params = f"latitude={lat}&longitude={lon}"
    params += f"&current={','.join(CURRENT_WEATHER_PARAMS)}"
    params += "&timezone=auto"

    return f"{OPENMETEO_BASE_URL}?{params}"


def _build_url_hourly(lat: float, lon: float, hours: int = 24) -> str:
    """
    Saatlik forecast URL'i olusturur.

    AÇIKLAMA:
    Bu ozel (private) fonksiyon, OpenMeteo API'sinde saatlik forecast cekmek
    icin gerekli URL'i olusturur. URL, enlem, boylam, forecast saati ve
    istenen hava durumu parametrelerini icerir.

    Ornekler:
    - _build_url_hourly(41.0082, 28.9784, 48)
      -> "https://api.open-meteo.com/v1/forecast?latitude=41.0082&longitude=28.9784
         &hourly=temperature_2m,precipitation,...&forecast_hours=48&timezone=auto"

    NASIL CALISIR:
    1. Latitude ve longitude parametrelerini ekler
    2. HOURLY_WEATHER_PARAMS listesindeki tum parametreleri ekler
    3. Forecast hours parametresini ekler (varsayilan 24)
    4. Timezone=auto ekler
    5. Tam URL'i doner

    KULLANIM ALANI:
    get_hourly_forecast fonksiyonu tarafindan API URL'i olusturmak
    icin kullanilir.

    Args:
        lat: Enlem
        lon: Boylam
        hours: Forecast saati

    Returns:
        str: OpenMeteo API URL
    """
    params = f"latitude={lat}&longitude={lon}"
    params += f"&hourly={','.join(HOURLY_WEATHER_PARAMS)}"
    params += f"&forecast_hours={hours}"
    params += "&timezone=auto"

    return f"{OPENMETEO_BASE_URL}?{params}"


# =============================================================================
# Data Parsing Functions
# =============================================================================

def _parse_current_weather(response: dict) -> dict:
    """
    OpenMeteo current weather response'unu parse eder.

    AÇIKLAMA:
    Bu ozel (private) fonksiyon, OpenMeteo API'sinden donen JSON response'u
    uygulamamizin ic formatina donusturur. Ham API verisini alir, weather
    code'unu aciklar, timestamp'i formatlar ve Turkce aciklamalar ekler.

    Ornekler:
    - Input: {"current": {"temperature_2m": 15.5, "weather_code": 0, ...}, ...}
    - Output: {"timestamp": "2026-03-10T09:00:00Z", "temperature": 15.5,
              "weather_tr": "Acik gokyuzu", "weather_emoji": "☀️", ...}

    NASIL CALISIR:
    1. Response'ta "current" alaninin oldugunu kontrol eder, yoksa hata firlatir
    2. Weather code'u parse_weather_code ile aciklar
    3. Timestamp'i ISO 8601 formatina donusturur (zaman dilimi ile)
    4. Tum hava durumu parametrelerini alir ve duzenli bir sozluk olusturur:
       - Sicakliklar (temperature, apparent_temperature)
       - Nem ve yagis (humidity, precipitation, rain, showers, snowfall)
       - Hava durumu bilgisi (weather_code, description, tr, emoji)
       - Bulut ve ruzgar (cloud_cover, wind_speed, wind_direction, wind_gusts)

    KULLANIM ALANI:
    get_current_weather fonksiyonu tarafindan API response'unu
    uygulamamizin formatina donusturmek icin kullanilir.

    Args:
        response: API response

    Returns:
        dict: Parsed hava durumu verisi
    """
    if "current" not in response:
        raise ParseError("Missing 'current' field in response")

    current = response["current"]
    units = response.get("current_units", {})

    # Weather code parse
    weather_code = current.get("weather_code", 0)
    parsed_code = parse_weather_code(weather_code)

    # OpenMeteo returns time as ISO 8601 string (e.g. "2026-03-10T09:00"), not Unix timestamp
    time_val = current.get("time", "")
    try:
        if isinstance(time_val, (int, float)):
            timestamp_str = datetime.fromtimestamp(time_val, tz=timezone.utc).isoformat()
        elif isinstance(time_val, str) and time_val:
            # ISO format: parse and ensure timezone
            dt = datetime.fromisoformat(time_val.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            timestamp_str = dt.isoformat()
        else:
            timestamp_str = ""
    except (ValueError, TypeError):
        timestamp_str = str(time_val) if time_val else ""

    return {
        "timestamp": timestamp_str,
        "temperature": current.get("temperature_2m", 0),
        "apparent_temperature": current.get("apparent_temperature", 0),
        "humidity": current.get("relative_humidity_2m", 0),
        "precipitation": current.get("precipitation", 0),
        "rain": current.get("rain", 0),
        "showers": current.get("showers", 0),
        "snowfall": current.get("snowfall", 0),
        "weather_code": weather_code,
        "weather_description": parsed_code.get("description", "Unknown"),
        "weather_tr": parsed_code.get("tr", "Bilinmiyor"),
        "weather_emoji": get_weather_emoji(weather_code),
        "cloud_cover": current.get("cloud_cover", 0),
        "wind_speed": current.get("wind_speed_10m", 0),
        "wind_direction": current.get("wind_direction_10m", 0),
        "wind_gusts": current.get("wind_gusts_10m", 0)
    }


def _parse_hourly_forecast(response: dict) -> dict:
    """
    OpenMeteo hourly forecast response'unu parse eder.

    AÇIKLAMA:
    Bu ozel (private) fonksiyon, OpenMeteo API'sinden donen saatlik forecast
    JSON response'unu uygulamamizin ic formatina donusturur. Saatlik veriler
    liste (array) formatinda gelir ve her bir indeks bir saate karsilik gelir.

    Ornekler:
    - Input: {"hourly": {"time": ["2026-03-10T09:00", "2026-03-10T10:00", ...],
                        "temperature_2m": [15.5, 16.2, ...], ...}, ...}
    - Output: {"time": ["2026-03-10T09:00", "2026-03-10T10:00", ...],
               "temperature": [15.5, 16.2, ...], ...}

    NASIL CALISIR:
    1. Response'ta "hourly" alaninin oldugunu kontrol eder, yoksa hata firlatir
    2. Hourly verilerinden istenen parametreleri cikarir:
       - time: Zaman damgalari listesi
       - temperature: Sicakliklar listesi
       - precipitation: Yagis miktari listesi
       - precipitation_probability: Yagis olasiligi listesi
       - weather_code: Hava durumu kodlari listesi
       - wind_speed: Ruzgar hizi listesi
       - wind_gusts: Ruzgar gust listesi
    3. Tum listeleri iceren bir sozluk doner

    KULLANIM ALANI:
    get_hourly_forecast fonksiyonu tarafindan API response'unu
    uygulamamizin formatina donusturmek icin kullanilir.

    Args:
        response: API response

    Returns:
        dict: Parsed forecast verisi
    """
    if "hourly" not in response:
        raise ParseError("Missing 'hourly' field in response")

    hourly = response["hourly"]

    return {
        "time": hourly.get("time", []),
        "temperature": hourly.get("temperature_2m", []),
        "precipitation": hourly.get("precipitation", []),
        "precipitation_probability": hourly.get("precipitation_probability", []),
        "weather_code": hourly.get("weather_code", []),
        "wind_speed": hourly.get("wind_speed_10m", []),
        "wind_gusts": hourly.get("wind_gusts_10m", [])
    }


# =============================================================================
# Main Service Functions
# =============================================================================

def get_current_weather(lat: float, lon: float, use_cache: bool = True) -> dict:
    """
    Belirli bir konum için güncel hava durumunu getirir.

    AÇIKLAMA:
    Bu genel (public) fonksiyon, verilen enlem ve boylam icin guncel hava
    durumunu getirir. Oncelikle cache kontrolu yapar, veri cache'te yoksa
    OpenMeteo API'sine istek atar. Sonucu standart bir formatta doner.

    Ornekler:
    - get_current_weather(41.0082, 28.9784)
      -> {"success": True, "data": {"location": {...}, "current": {...},
          "cache_hit": False}}
    - get_current_weather(41.0082, 28.9784) # Ikinci cagri
      -> {"success": True, "data": {...}, "cache_hit": True} # Cache'ten doner
    - get_current_weather(91, 0) -> InvalidCoordinatesError firlatir

    NASIL CALISIR:
    1. Koordinatlari valid eder (-90 <= lat <= 90, -180 <= lon <= 180)
    2. Cache anahtari olusturur (orn: "current:41.0082:28.9784")
    3. use_cache=True ise cache'te veri var mi kontrol eder
    4. Cache'te varsa dogrudan doner (cache_hit=True)
    5. Cache'te yoksa OpenMeteo API'sine istek atar
    6. API response'unu parse eder
    7. Sonucu cache'e kaydeder ve doner

    RESPONSE FORMATI:
    {
        "success": true,
        "data": {
            "location": {"lat": 41.0082, "lon": 28.9784, "timezone": "Europe/Istanbul"},
            "current": {
                "timestamp": "2026-03-10T09:00:00Z",
                "temperature": 15.5,
                "weather_tr": "Acik gokyuzu",
                "weather_emoji": "☀️",
                ...
            },
            "cache_hit": false
        }
    }

    KULLANIM ALANI:
    Flask endpoint'leri (/api/weather) tarafindan kullaniciya hava
    durumu gostermek icin cagrilir. Ayrica rota planlamada da
    kullanilir.

    Args:
        lat: Enlem (-90 ile 90 arasi)
        lon: Boylam (-180 ile 180 arasi)
        use_cache: Cache kullanilsin mi (varsayilan True)

    Returns:
        dict: Basari durumu ve hava durumu verisi

    Raises:
        InvalidCoordinatesError: Gecersiz koordinatlar
        NetworkError: API baglanti hatasi
    """
    # Validation
    if not validate_coordinates(lat, lon):
        raise InvalidCoordinatesError(
            f"Invalid coordinates: lat={lat}, lon={lon}"
        )

    # Cache kontrolu
    cache_key = build_cache_key("current", lat, lon)
    if use_cache:
        cached = _get_from_cache(cache_key)
        if cached:
            cached["data"]["cache_hit"] = True
            return {
                "success": True,
                "data": cached["data"]
            }

    try:
        # API'den veri cek
        url = _build_url_current(lat, lon)
        response = _fetch_from_openmeteo(url)

        # Parse response
        current_weather = _parse_current_weather(response)

        # Response yapisi
        result = {
            "location": {
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "timezone": response.get("timezone", "GMT")
            },
            "current": current_weather,
            "cache_hit": False
        }

        # Cache'e kaydet
        if use_cache:
            _save_to_cache(cache_key, result)

        logger.info(
            "Current weather fetched: lat=%s, lon=%s, temp=%s, weather_code=%s",
            lat, lon, current_weather.get("temperature"),
            current_weather.get("weather_code")
        )

        return {
            "success": True,
            "data": result
        }

    except (NetworkError, RateLimitError, ParseError) as e:
        logger.error(f"Failed to fetch current weather: {str(e)}")
        raise


def get_hourly_forecast(
    lat: float,
    lon: float,
    hours: int = 24,
    use_cache: bool = True
) -> dict:
    """
    Belirli bir konum için saatlik forecast getirir.

    AÇIKLAMA:
    Bu genel (public) fonksiyon, verilen enlem ve boylam icin saatlik hava
    durumu forecast'i getirir. Ileriye yonelik 1-168 saat (1-7 gun) arasi
    forecast alinabilir. get_current_weather gibi once cache kontrolu yapar.

    Ornekler:
    - get_hourly_forecast(41.0082, 28.9784, 24)
      -> {"success": True, "data": {"location": {...}, "hourly": {...},
          "cache_hit": False}}
    - get_hourly_forecast(41.0082, 28.9784, 48)
      -> 48 saatlik forecast doner
    - get_hourly_forecast(41.0082, 28.9784, 200) -> ValueError (max 168 saat)

    NASIL CALISIR:
    1. Koordinatlari valid eder
    2. Saat sayisini valid eder (1-168 arasi)
    3. Cache anahtari olusturur (orn: "hourly:41.0082:28.9784:24")
    4. use_cache=True ise cache'te veri var mi kontrol eder
    5. Cache'te varsa dogrudan doner
    6. Cache'te yoksa OpenMeteo API'sine istek atar
    7. API response'unu parse eder
    8. Sonucu cache'e kaydeder ve doner

    RESPONSE FORMATI:
    {
        "success": true,
        "data": {
            "location": {"lat": 41.0082, "lon": 28.9784, "timezone": "Europe/Istanbul"},
            "hourly": {
                "time": ["2026-03-10T09:00", "2026-03-10T10:00", ...],  // 24 saat
                "temperature": [15.5, 16.2, ...],
                "precipitation": [0.0, 0.1, ...],
                "precipitation_probability": [0, 5, ...],
                "weather_code": [0, 0, ...],
                "wind_speed": [12.5, 14.0, ...],
                "wind_gusts": [18.0, 20.0, ...]
            },
            "cache_hit": false
        }
    }

    KULLANIM ALANI:
    Flask endpoint'leri (/api/weather/forecast) tarafindan kullaniciya
    ileriye yonelik hava durumu gostermek icin cagrilir. Ayrica rota
    planlamada seyahat suresinceki hava durumunu gostermek icin de kullanilir.

    Args:
        lat: Enlem
        lon: Boylam
        hours: Forecast saati (1-168 arasi, varsayilan 24)
        use_cache: Cache kullanilsin mi (varsayilan True)

    Returns:
        dict: Basari durumu ve forecast verisi

    Raises:
        InvalidCoordinatesError: Gecersiz koordinatlar
        ValueError: Gecersiz saat sayisi
    """
    # Validation
    if not validate_coordinates(lat, lon):
        raise InvalidCoordinatesError(
            f"Invalid coordinates: lat={lat}, lon={lon}"
        )

    if not validate_hours(hours):
        raise ValueError(f"Invalid hours: {hours} (must be 1-168)")

    # Cache kontrolu
    cache_key = build_cache_key("hourly", lat, lon, hours=hours)
    if use_cache:
        cached = _get_from_cache(cache_key)
        if cached:
            cached["data"]["cache_hit"] = True
            return {
                "success": True,
                "data": cached["data"]
            }

    try:
        # API'den veri cek
        url = _build_url_hourly(lat, lon, hours)
        response = _fetch_from_openmeteo(url)

        # Parse response
        hourly_forecast = _parse_hourly_forecast(response)

        # Response yapisi
        result = {
            "location": {
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "timezone": response.get("timezone", "GMT")
            },
            "hourly": hourly_forecast,
            "cache_hit": False
        }

        # Cache'e kaydet
        if use_cache:
            _save_to_cache(cache_key, result)

        logger.info(
            "Hourly forecast fetched: lat=%s, lon=%s, hours=%s",
            lat, lon, hours
        )

        return {
            "success": True,
            "data": result
        }

    except (NetworkError, RateLimitError, ParseError) as e:
        logger.error(f"Failed to fetch hourly forecast: {str(e)}")
        raise


def check_route_weather(
    points: List[Dict],
    start_time: Optional[str] = None
) -> dict:
    """
    Rota boyunca hava durumunu kontrol eder.

    AÇIKLAMA:
    Bu genel (public) fonksiyon, verilen rota noktalari (waypoints) icin
    guncel hava durumunu kontrol eder. Her nokta icin hava durumunu cekar,
    uyari olusturur ve genel bir durum degerlendirmesi yapar. Rota
    planlamada kullaniciya hava kosullari hakkinda bilgi vermek icin
    kullanilir.

    Ornekler:
    - check_route_weather([{"lat": 41.0082, "lon": 28.9784, "name": "Kadikoy"},
                          {"lat": 41.0422, "lon": 29.0067, "name": "Besiktas"}])
      -> {
          "success": True,
          "data": {
              "route_weather": [
                  {"point": "Kadikoy", "lat": 41.0082, "lon": 28.9784,
                   "weather": {"temperature": 15, ...}},
                  ...
              ],
              "warnings": [],
              "overall_conditions": "clear"
          }
      }

    NASIL CALISIR:
    1. En az bir nokta verilip verilmedigini kontrol eder
    2. Her nokta icin:
       a. Koordinatlari cikarir (hem lat/lon hem latitude/longitude destekler)
       b. Koordinat eksikse hata mesaji ekler ve bir sonrakine gecer
       c. get_current_weather ile hava durumunu cekar
       d. Hava durumunu analiz eder ve uyari olusturur
       e. Sonucu route_weather listesine ekler
    3. Tum noktalar icin genel durum degerlendirmesi yapar
    4. Tum sonuclari doner

    GENEL DURUM KATEGORILERI:
    - clear: Acik gokyuzu (kod 0-3)
    - foggy: Sisli (kod 45-48)
    - rainy: Yagmurlu (kod 51-67, 80-82)
    - snowy: Karli (kod 71-77, 85-86)
    - stormy: Firtinali (kod 95-99)
    - unknown: Bilinmiyor

    KULLANIM ALANI:
    Flask endpoint'leri (/api/weather/check-route) tarafindan rota
    planlamada kullaniciya hava durumu bilgisini gostermek icin cagrilir.
    Ayrica rota hesaplama modulleri tarafindan da kullanilabilir.

    Args:
        points: Nokta listesi [{"lat": float, "lon": float, "name": str}, ...]
        start_time: Baslangic zamani (ISO 8601 format, opsiyonel, Faz 2'de kullanilacak)

    Returns:
        dict: Basari durumu ve rota hava durumu bilgileri
    """
    if not points or len(points) < 1:
        raise ValueError("At least one point is required")

    route_weather = []
    warnings = []

    for point in points:
        # Support both "lat"/"lon" and "latitude"/"longitude" (common API conventions)
        lat = point.get("lat") or point.get("latitude")
        lon = point.get("lon") or point.get("longitude")
        name = point.get("name", point.get("label", "Bilinmeyen"))

        if lat is None or lon is None:
            logger.warning(f"Skipping point {name}: missing lat/lon coordinates")
            route_weather.append({
                "point": name,
                "lat": lat,
                "lon": lon,
                "weather": None,
                "error": "Koordinat eksik (lat/lon veya latitude/longitude gerekli)"
            })
            continue

        try:
            result = get_current_weather(lat, lon)
            current = result["data"]["current"]

            # Uyari kontrolu
            alert = get_weather_alert(current)
            if alert:
                warnings.append(f"{name}: {alert}")

            route_weather.append({
                "point": name,
                "lat": lat,
                "lon": lon,
                "weather": current
            })

        except Exception as e:
            logger.warning(f"Failed to get weather for {name}: {str(e)}")
            route_weather.append({
                "point": name,
                "lat": lat,
                "lon": lon,
                "weather": None,
                "error": str(e)
            })

    # Genel durum degerlendirmesi
    overall_conditions = _evaluate_overall_conditions(route_weather)

    return {
        "success": True,
        "data": {
            "route_weather": route_weather,
            "warnings": warnings,
            "overall_conditions": overall_conditions
        }
    }


def _evaluate_overall_conditions(route_weather: List[dict]) -> str:
    """
    Rota genelindeki hava durumunu degerlendirir.

    AÇIKLAMA:
    Bu ozel (private) fonksiyon, rota boyunca tum noktalarin hava durumunu
    analiz eder ve genel bir durum kategorisi doner. "En kotu durum"
    mantigiyla calisir - yani rota icinde herhangi bir noktada firtina
    varsa genel durum "stormy" doner. Bu, kullaniciya rota boyunca karsilasacagi
    en kotu hava kosulunu haber vermek icin yapilir.

    Ornekler:
    - _evaluate_overall_conditions([{"weather": {"weather_code": 0}}, ...])
      -> "clear" (tum noktalar acik)
    - _evaluate_overall_conditions([{"weather": {"weather_code": 0}},
                                     {"weather": {"weather_code": 61}}])
      -> "rainy" (bir noktada yagmur var)
    - _evaluate_overall_conditions([{"weather": {"weather_code": 95}}])
      -> "stormy" (firtina)

    NASIL CALISIR:
    1. Rota hava durumu listesi bos ise "unknown" doner
    2. Her noktanin weather_code'unu toplar
    3. Hic kod yoksa "unknown" doner
    4. En yuksek kodu bulur (max)
    5. Max koda gore kategori doner:
       - 0-3: clear (Acik)
       - 45-48: foggy (Sisli)
       - 51-82: rainy (Yagmurlu)
       - 71-86: snowy (Karli) - not: kod 71-86 hem yagmur hem kar icerir
       - 95-99: stormy (Firtinali)

    KULLANIM ALANI:
    check_route_weather fonksiyonu tarafindan rota genelindeki hava
    durumunu ozetlemek icin kullanilir. Frontend'de rota bilgisi
    gosterirken kullanilabilir.

    Args:
        route_weather: Rota hava durumu listesi

    Returns:
        str: Genel durum (clear, foggy, rainy, snowy, stormy, unknown)
    """
    if not route_weather:
        return "unknown"

    # Hava kodlarini topla
    weather_codes = []
    for item in route_weather:
        if item.get("weather"):
            code = item["weather"].get("weather_code", 0)
            weather_codes.append(code)

    if not weather_codes:
        return "unknown"

    # En kotu durum belirle (WMO kod sirasina gore)
    max_code = max(weather_codes)

    # Durum kategorizasyonu - oncelik: storm > snow > rain > fog > clear
    if max_code >= 95:
        return "stormy"
    elif max_code >= 85 or (71 <= max_code <= 77):
        return "snowy"
    elif max_code >= 51:
        return "rainy"
    elif max_code >= 45:
        return "foggy"
    else:
        return "clear"


# =============================================================================
# Batch Functions
# =============================================================================

def get_multiple_locations_weather(
    locations: List[Tuple[float, float]]
) -> List[dict]:
    """
    Birden fazla konum için hava durumu getirir.

    AÇIKLAMA:
    Bu fonksiyon, birden fazla konum icin ayni anda hava durumu getirir.
    Her konum icin get_current_weather cagirir ve sonuclari liste olarak doner.
    Hata durumunda bir konum hata verirse digerlerini getirmeye devam eder
    (fault-tolerant). Batch islemler icin kullanilir.

    Ornekler:
    - get_multiple_locations_weather([(41.0082, 28.9784), (41.0422, 29.0067)])
      -> [
          {"success": True, "data": {"location": {...}, "current": {...}, ...}},
          {"success": True, "data": {"location": {...}, "current": {...}, ...}}
        ]

    NASIL CALISIR:
    1. Bos bir results listesi olusturur
    2. Her (lat, lon) tuple'i icin:
       a. get_current_weather(lat, lon) cagirir
       b. Basariysa sonucu listeye ekler
       c. Hata olusursa hata mesaji iceren bir entry ekler
    3. Tum sonuclari doner

    KULLANIM ALANI:
    Ayni anda birden fazla konumun hava durumunu getirmek icin
    kullanilir. Ozelikle coklu rota noktalari veya favori konumlar
    icin hava durumu gosterirken kullanisli.

    Args:
        locations: (lat, lon) tuple listesi

    Returns:
        list: Hava durumu verileri listesi (basarili veya hatali)
    """
    results = []

    for lat, lon in locations:
        try:
            result = get_current_weather(lat, lon)
            results.append(result)
        except Exception as e:
            logger.warning(f"Failed for {lat}, {lon}: {str(e)}")
            results.append({
                "success": False,
                "error": str(e),
                "lat": lat,
                "lon": lon
            })

    return results


# =============================================================================
# Utility Functions
# =============================================================================

def get_service_status() -> dict:
    """
    Hava durumu servisi durumunu dondurur.

    AÇIKLAMA:
    Bu fonksiyon, hava durumu servisinin mevcut durumunu ozetleyen bilgiler
    doner. Servis adi, durumu, cache istatistikleri ve konfigurasyon bilgilerini
    icerir. Monitoring ve debug amacli kullanilir.

    Ornekler:
    - get_service_status()
      -> {
          "service": "weather_service",
          "status": "operational",
          "cache_stats": {
              "total_entries": 5,
              "valid_entries": 3,
              "expired_entries": 2,
              "ttl_seconds": 900
          },
          "config": {
              "cache_ttl_seconds": 900,
              "request_timeout": 10,
              "api_url": "https://api.open-meteo.com/v1/forecast"
          }
      }

    NASIL CALISIR:
    1. Servis adini ve durumunu belirler (her zaman "operational")
    2. get_cache_stats() ile cache istatistiklerini alir
    3. Konfigurasyon bilgilerini toplar:
       - Cache TTL (saniye)
       - Request timeout (saniye)
       - OpenMeteo API URL
    4. Tum bilgileri sozluk olarak doner

    KULLANIM ALANI:
    /api/weather/status endpoint'i tarafindan kullaniciya ve
    monitoring sistemlerine servis durumu bilgisini gostermek icin
    kullanilir. Ayrica debug ve performans izleme icin de kullanilabilir.

    Returns:
        dict: Servis durumu bilgileri
    """
    return {
        "service": "weather_service",
        "status": "operational",
        "cache_stats": get_cache_stats(),
        "config": {
            "cache_ttl_seconds": CACHE_TTL_SECONDS,
            "request_timeout": REQUEST_TIMEOUT,
            "api_url": OPENMETEO_BASE_URL
        }
    }


def health_check() -> bool:
    """
    Servis saglik kontrolu.

    AÇIKLAMA:
    Bu fonksiyon, hava durumu servisinin saglikli olup olmadigini kontrol
    eder. Bunu yapmak icin Istanbul icin (bilinen gecerli koordinatlar)
    gerçek bir API istegi yapar ve sonucu kontrol eder. Basariyla tamamlanirs
    True, herhangi bir hata olusursa False doner.

    Ornekler:
    - health_check() -> True (servis saglikli)
    - health_check() -> False (API baglanti hatasi, timeout, vb.)

    NASIL CALISIR:
    1. Istanbul koordinatlari ile get_current_weather cagirir
    2. use_cache=False parametresi ile cache'i atlar (gercek API testi)
    3. Sonucun "success": True icerip icermedigini kontrol eder
    4. Herhangi bir exception olusursa yakalar ve False doner
    5. Hatayi log'lar

    KULLANIM ALANI:
    /api/weather/health endpoint'i tarafindan monitoring sistemleri,
    load balancer'lar ve deployment scriptleri tarafindan servisin
    calistigini kontrol etmek icin kullanilir. Ayrica Docker
    HEALTHCHECK direktifi olarak da kullanilabilir.

    Returns:
        bool: True if service is healthy, False otherwise
    """
    try:
        # Test call with minimal data
        result = get_current_weather(41.0082, 28.9784, use_cache=False)
        return result.get("success", False)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return False
