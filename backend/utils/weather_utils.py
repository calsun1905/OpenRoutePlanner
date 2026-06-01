"""
weather_utils.py - Hava durumu yardımcı fonksiyonları

WMO weather code parsing, koordinat validasyonu, cache utilities
ve hava durumu analiz fonksiyonları.

Author: OpenRoutePlanner
Created: 2026-03-10
"""

from typing import Any, Dict, Optional, Tuple
from datetime import datetime
import math


# =============================================================================
# WMO Weather Code Mapping
# =============================================================================

WMO_WEATHER_CODES = {
    0: {
        "description": "Clear sky",
        "tr": "Acik gokyuzu",
        "icon": "sun",
        "category": "clear"
    },
    1: {
        "description": "Mainly clear",
        "tr": "Genellikle acik",
        "icon": "sun_cloud",
        "category": "partly_cloudy"
    },
    2: {
        "description": "Partly cloudy",
        "tr": "Parcali bulutlu",
        "icon": "partly_cloudy",
        "category": "partly_cloudy"
    },
    3: {
        "description": "Overcast",
        "tr": "Kapali",
        "icon": "cloud",
        "category": "cloudy"
    },
    45: {
        "description": "Fog",
        "tr": "Sis",
        "icon": "fog",
        "category": "fog"
    },
    48: {
        "description": "Depositing rime fog",
        "tr": "Kiran sis",
        "icon": "fog",
        "category": "fog"
    },
    51: {
        "description": "Light drizzle",
        "tr": "Hafif ciseleme",
        "icon": "drizzle",
        "category": "drizzle"
    },
    53: {
        "description": "Moderate drizzle",
        "tr": "Orta ciseleme",
        "icon": "drizzle",
        "category": "drizzle"
    },
    55: {
        "description": "Dense drizzle",
        "tr": "Yogun ciseleme",
        "icon": "drizzle",
        "category": "drizzle"
    },
    56: {
        "description": "Light freezing drizzle",
        "tr": "Hafif donan ciseleme",
        "icon": "drizzle_cold",
        "category": "freezing_drizzle"
    },
    57: {
        "description": "Dense freezing drizzle",
        "tr": "Yogun donan ciseleme",
        "icon": "drizzle_cold",
        "category": "freezing_drizzle"
    },
    61: {
        "description": "Slight rain",
        "tr": "Hafif yagmur",
        "icon": "rain_light",
        "category": "rain"
    },
    63: {
        "description": "Moderate rain",
        "tr": "Orta yagmur",
        "icon": "rain",
        "category": "rain"
    },
    65: {
        "description": "Heavy rain",
        "tr": "Yogun yagmur",
        "icon": "rain_heavy",
        "category": "rain"
    },
    66: {
        "description": "Light freezing rain",
        "tr": "Hafif donan yagmur",
        "icon": "rain_cold",
        "category": "freezing_rain"
    },
    67: {
        "description": "Heavy freezing rain",
        "tr": "Yogun donan yagmur",
        "icon": "rain_cold",
        "category": "freezing_rain"
    },
    71: {
        "description": "Slight snow fall",
        "tr": "Hafif kar",
        "icon": "snow_light",
        "category": "snow"
    },
    73: {
        "description": "Moderate snow fall",
        "tr": "Orta kar",
        "icon": "snow",
        "category": "snow"
    },
    75: {
        "description": "Heavy snow fall",
        "tr": "Yogun kar",
        "icon": "snow_heavy",
        "category": "snow"
    },
    77: {
        "description": "Snow grains",
        "tr": "Kar taneleri",
        "icon": "snow_grains",
        "category": "snow"
    },
    80: {
        "description": "Slight rain showers",
        "tr": "Hafif sagacak yagmur",
        "icon": "rain_shower_light",
        "category": "rain_showers"
    },
    81: {
        "description": "Moderate rain showers",
        "tr": "Orta sagacak yagmur",
        "icon": "rain_shower",
        "category": "rain_showers"
    },
    82: {
        "description": "Violent rain showers",
        "tr": "Siddetli sagacak yagmur",
        "icon": "rain_shower_heavy",
        "category": "rain_showers"
    },
    85: {
        "description": "Slight snow showers",
        "tr": "Hafif sagacak kar",
        "icon": "snow_shower_light",
        "category": "snow_showers"
    },
    86: {
        "description": "Heavy snow showers",
        "tr": "Yogun sagacak kar",
        "icon": "snow_shower_heavy",
        "category": "snow_showers"
    },
    95: {
        "description": "Thunderstorm",
        "tr": "Firtina",
        "icon": "thunderstorm",
        "category": "thunderstorm"
    },
    96: {
        "description": "Thunderstorm with slight hail",
        "tr": "Hafif dolu firtinasi",
        "icon": "thunderstorm_hail",
        "category": "thunderstorm"
    },
    99: {
        "description": "Thunderstorm with heavy hail",
        "tr": "Yogun dolu firtinasi",
        "icon": "thunderstorm_hail_heavy",
        "category": "thunderstorm"
    }
}


# =============================================================================
# Validation Functions
# =============================================================================

def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Koordinatlarin gecerli olup olmadigini kontrol eder.

    AÇIKLAMA:
    Bu fonksiyon, verilen enlem ve boylam degerlerinin dunya koordinat sisteminde
    gecerli olup olmadigini kontrol eder. Enlem -90 ile 90 arasinda olmalidir (ekvator 0,
    kuzey kutbu 90, guney kutbu -90). Boylam ise -180 ile 180 arasindadir (greenwich 0).

    Örnegin:
    - validate_coordinates(41.0082, 28.9784) -> True (Istanbul icin gecerli)
    - validate_coordinates(91, 0) -> False (enlem 90'dan buyuk olamaz)
    - validate_coordinates(41, 181) -> False (boylam 180'den buyuk olamaz)

    KULLANIM ALANI:
    Hava durumu API'sine istek yapmadan once kullanici tarafindan gelen veya
    API'den donen koordinatlarin dogrulugunu kontrol etmek icin kullanilir.

    Args:
        lat: Enlem (-90 ile 90 arasi)
        lon: Boylam (-180 ile 180 arasi)

    Returns:
        bool: Koordinatlar gecerliyse True, degilse False
    """
    try:
        lat_float = float(lat)
        lon_float = float(lon)
        return -90 <= lat_float <= 90 and -180 <= lon_float <= 180
    except (ValueError, TypeError):
        return False


def validate_hours(hours: int) -> bool:
    """
    Forecast saat sayisinin gecerli olup olmadigini kontrol eder.

    AÇIKLAMA:
    Bu fonksiyon, kullanici tarafindan istenen saatlik forecast suresinin OpenMeteo API'sinin
    destekledigi aralikta olup olmadigini kontrol eder. OpenMeteo API'si minimum 1 saat,
    maksimum 168 saat (7 gun) forecast suresi destekler.

    Ornekler:
    - validate_hours(24) -> True (varsayilan 24 saat, gecerli)
    - validate_hours(168) -> True (maksimum 7 gun, gecerli)
    - validate_hours(169) -> False (API 168 saatten fazla desteklemez)
    - validate_hours(0) -> False (en az 1 saat gerekli)

    NASIL CALISIR:
    1. Gelen hours degerini integer'a cevirir (string veya float gelebilir)
    2. 1 ile 168 arasinda olup olmadigini kontrol eder
    3. Deger aralik disindaysa veya cevirilemezse False doner

    KULLANIM ALANI:
    Saatlik forecast istegi yapmadan once, kullanicinin girdigi saat
    degerinin API limitleri icinde oldugunu dogrulamak icin kullanilir.

    Args:
        hours: Forecast saati (1-168 arasi)

    Returns:
        bool: Saat gecerliyse True, degilse False
    """
    try:
        hours_int = int(hours)
        return 1 <= hours_int <= 168
    except (ValueError, TypeError):
        return False


def validate_temperature(temp: float) -> bool:
    """
    Sicaklik degerinin mantikli olup olmadigini kontrol eder.

    AÇIKLAMA:
    Bu fonksiyon, gelen sicaklik degerinin dunya uzerinde olabilecek mantikli
    bir sicaklik araliginda olup olmadigini kontrol eder. Dunya uzerinde kayitlanmis
    en sicak sicaklik +56.7°C, en soguk sicaklik -89.2°C'dir. Biz -100 ile +100
    araligini kabul ediyoruz ki ekstrem durumlar da cover edilsin.

    Ornekler:
    - validate_temperature(25) -> True (normal oda sicakligi)
    - validate_temperature(-5) -> True (kis gunleri, mantikli)
    - validate_temperature(50) -> True (cok sicak ama mumkun)
    - validate_temperature(150) -> False (bu sicaklik dunyada mumkun degil)
    - validate_temperature(-200) -> False (mutlak sifirdan daha soguk imkansiz)

    NASIL CALISIR:
    1. Gelen temp degerini float'a cevirir
    2. -100 ile +100 Celsius arasinda oldugunu kontrol eder
    3. Ceviris hatasi veya aralik disi ise False doner

    KULLANIM ALANI:
    API'den gelen veya kullanici tarafindan girilen sicaklik degerlerinin
    dogrulugunu kontrol etmek ve hatali verileri filtrelemek icin kullanilir.

    Args:
        temp: Sicaklik (Celsius, -50 ile 60 arasi beklenir)

    Returns:
        bool: Sicaklik mantikliysa True, degilse False
    """
    try:
        temp_float = float(temp)
        return -100 <= temp_float <= 100  # Genis aralik, extrem durumlar icin
    except (ValueError, TypeError):
        return False


# =============================================================================
# Cache Utilities
# =============================================================================

def build_cache_key(prefix: str, lat: float, lon: float, **kwargs) -> str:
    """
    Cache anahtari olusturur.

    AÇIKLAMA:
    Bu fonksiyon, verilen parametrelerden (prefix, koordinatlar, ek parametreler)
    benzersiz bir cache anahtari olusturur. Anahtar formati "prefix:lat:lon:ek_parametreler"
    seklindedir. Koordinatlar 4 ondalik hassasiyetle yuvarlanir, bu yaklasik 11 metre
    hassasiyet demektir - ayni konumdan gelen istekler ayni cache anahtara sahip olur.

    Ornekler:
    - build_cache_key("current", 41.0082, 28.9784) -> "current:41.0082:28.9784"
    - build_cache_key("hourly", 41.0082, 28.9784, hours=24) -> "hourly:41.0082:28.9784:24"
    - build_cache_key("hourly", 41.0082, 28.9784, hours=48) -> "hourly:41.0082:28.9784:48"

    NASIL CALISIR:
    1. Gelen lat ve lon degerlerini float'a cevirir ve 4 ondalik yuvarlar
    2. Prefix, lat, lon degerlerinden anahtar parcalari olusturur
    3. **kwargs ile gelen ek parametreleri siralar ve ekler (hours gibi)
    4. Tum parcalari ":" ile birlestirir ve anahtar doner

    KULLANIM ALANI:
    Hava durumu verilerini cache'lerken her istek icin benzersiz bir anahtar
    olusturmak icin kullanilir. Ayni konum ve ayni parametreler icin ayni anahtar
    olusur, boylece cache'te ayni veriyi bulmak kolay olur.

    Args:
        prefix: Cache on eki (orn: 'current', 'hourly')
        lat: Enlem
        lon: Boylam
        **kwargs: Ek parametreler (orn: hours=24)

    Returns:
        str: Cache anahtari
    """
    # Koordinatlari 4 ondalik hassasiyetle yuvarla
    try:
        lat_rounded = round(float(lat), 4)
        lon_rounded = round(float(lon), 4)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid coordinates for cache key: lat={lat!r}, lon={lon!r}")

    key_parts = [prefix, str(lat_rounded), str(lon_rounded)]

    # Ek parametreleri ekle
    for k, v in sorted(kwargs.items()):
        key_parts.append(str(v))

    return ":".join(key_parts)


def parse_cache_key(key: str) -> Dict[str, Any]:
    """
    Cache anahtarini bilesenlerine ayirir.

    AÇIKLAMA:
    Bu fonksiyon, build_cache_key ile olusturulan cache anahtarini orijinal
    bilesenlerine ayirir. Böylece anahtarin hangi konum ve parametreler icin
    olusturuldugu anlasilabilir.

    Ornekler:
    - parse_cache_key("current:41.0082:28.9784")
      -> {"prefix": "current", "lat": 41.0082, "lon": 28.9784, "params": []}
    - parse_cache_key("hourly:41.0082:28.9784:24")
      -> {"prefix": "hourly", "lat": 41.0082, "lon": 28.9784, "params": ["24"]}

    NASIL CALISIR:
    1. Anahtari ":" karakterinden boler
    2. Ilk bolum prefix olarak atanir
    3. Ikinci ve ucuncu bolumler enlem ve boylam olarak float'a cevrilir
    4. Kalan bolumler (varsa) params listesine eklenir

    KULLANIM ALANI:
    Cache anahtarlarini analiz etmek, cache icerigini anlamak ve debug
    islemleri icin kullanilir.

    Args:
        key: Cache anahtari

    Returns:
        dict: Bilesenler (prefix, lat, lon, params)
    """
    parts = key.split(":")

    result = {
        "prefix": parts[0],
        "lat": float(parts[1]) if len(parts) > 1 else None,
        "lon": float(parts[2]) if len(parts) > 2 else None,
        "params": parts[3:] if len(parts) > 3 else []
    }

    return result


# =============================================================================
# Weather Code Parsing
# =============================================================================

def parse_weather_code(code: int) -> Dict[str, str]:
    """
    WMO hava durum kodunu aciklamaya cevirir.

    AÇIKLAMA:
    Bu fonksiyon, Dunya Meteoroloji Orgutu (WMO) tarafindan tanimlanan
    hava durumu kodlarini (0-99 arasi) insani okunabilir aciklamalara,
    Turkce karsiliklarina, ikon adlarina ve kategorilere donusturur.
    Toplam 46 farkli kod tanimlanmistir ve WMO_WEATHER_CODES sozlugunde
    tutulur. Kod listede yoksa "Unknown" (Bilinmiyor) doner.

    Ornekler:
    - parse_weather_code(0) -> {'description': 'Clear sky', 'tr': 'Acik gokyuzu',
                                'icon': 'sun', 'category': 'clear'}
    - parse_weather_code(61) -> {'description': 'Slight rain', 'tr': 'Hafif yagmur',
                                  'icon': 'rain_light', 'category': 'rain'}
    - parse_weather_code(95) -> {'description': 'Thunderstorm', 'tr': 'Firtina',
                                  'icon': 'thunderstorm', 'category': 'thunderstorm'}
    - parse_weather_code(999) -> {'description': 'Unknown', 'tr': 'Bilinmiyor',
                                   'icon': 'question', 'category': 'unknown'}

    NASIL CALISIR:
    1. Gelen kodu integer'a cevirir (None gelirse 0 kabul eder)
    2. WMO_WEATHER_CODES sozlugunda kodu arar
    3. Kod varsa ilgili bilgiyi doner, yoksa varsayilan "Unknown" bilgiyi doner

    KULLANIM ALANI:
    OpenMeteo API'sinden donen ham sayisal hava durum kodlarini kullanicinin
    anlayacagi sekilde gostermek icin kullanilir. Frontend'de ikon secimi,
    Turkce aciklama gosterme ve kategoriye gore renklendirme icin kullanilir.

    Args:
        code: WMO weather code (0-99 arasi)

    Returns:
        dict: Aciklama, Turkce aciklama, icon, kategori
    """
    code_int = int(code) if code is not None else 0

    # Kod harici bir durum icin varsayilan
    if code_int not in WMO_WEATHER_CODES:
        return {
            "description": "Unknown",
            "tr": "Bilinmiyor",
            "icon": "question",
            "category": "unknown"
        }

    return WMO_WEATHER_CODES[code_int]


def get_weather_emoji(code: int) -> str:
    """
    WMO kodu icin emoji icon dondurur.

    AÇIKLAMA:
    Bu fonksiyon, WMO hava durum koduna karsilik gelen emoji ikonunu dondurur.
    Emoji'ler frontend'de hava durumunu gorsel olarak gostermek icin kullanilir.
    Kod tanimli degilse soru isareti emoji doner.

    Ornekler:
    - get_weather_emoji(0) -> "☀️" (Acik gokyuzu - gunes)
    - get_weather_emoji(61) -> "🌧️" (Yagmur)
    - get_weather_emoji(95) -> "⛈️" (Firtina)
    - get_weather_emoji(999) -> "❓" (Bilinmeyen kod)

    NASIL CALISIR:
    1. Gelen kodu integer'a cevirir
    2. emoji_map sozlugunda kodu arar
    3. Kod varsa ilgili emoji'yi doner, yoksa "❓" doner

    KULLANIM ALANI:
    Kullanicilara hava durumunu hizli ve gorsel olarak gostermek icin
    kullanilir. Mobil uygulamalarda ve web arayuzlerinde emoji'ler
    kucuk boyutlariyla bilgiyi hizli aktarirlar.

    Args:
        code: WMO weather code

    Returns:
        str: Emoji icon
    """
    emoji_map = {
        0: "☀️",  # Clear sky
        1: "🌤️",  # Mainly clear
        2: "⛅",  # Partly cloudy
        3: "☁️",  # Overcast
        45: "🌫️",  # Fog
        48: "🌫️",  # Depositing rime fog
        51: "🌧️",  # Light drizzle
        53: "🌧️",  # Moderate drizzle
        55: "🌧️",  # Dense drizzle
        56: "🌨️",  # Light freezing drizzle
        57: "🌨️",  # Dense freezing drizzle
        61: "🌧️",  # Slight rain
        63: "🌧️",  # Moderate rain
        65: "🌧️",  # Heavy rain
        66: "🌨️",  # Light freezing rain
        67: "🌨️",  # Heavy freezing rain
        71: "❄️",  # Slight snow fall
        73: "❄️",  # Moderate snow fall
        75: "❄️",  # Heavy snow fall
        77: "❄️",  # Snow grains
        80: "🌦️",  # Slight rain showers
        81: "🌦️",  # Moderate rain showers
        82: "🌦️",  # Violent rain showers
        85: "🌨️",  # Slight snow showers
        86: "🌨️",  # Heavy snow showers
        95: "⛈️",  # Thunderstorm
        96: "⛈️",  # Thunderstorm with slight hail
        99: "⛈️",  # Thunderstorm with heavy hail
    }

    try:
        return emoji_map.get(int(code) if code is not None else -1, "❓")
    except (ValueError, TypeError):
        return "❓"


# =============================================================================
# Temperature Utilities
# =============================================================================

def format_temperature(temp: float, unit: str = "celsius") -> str:
    """
    Sicaklik degerini formatlar.

    AÇIKLAMA:
    Bu fonksiyon, sicaklik degerini istenen birimde formatlayarak gorsel olarak
    temiz bir sekilde dondurur. Varsayilan birim Celsius'tir, ancak Fahrenheit
    secenegi de vardir. Cikis bir ondalik hassasiyetindedir ve birim sembolunu
    icerir.

    Ornekler:
    - format_temperature(15.5) -> "15.5°C"
    - format_temperature(15.5, "fahrenheit") -> "59.9°F"
    - format_temperature(-3.2) -> "-3.2°C"
    - format_temperature(0) -> "0.0°C"

    NASIL CALISIR:
    1. Gelen temp degerini float'a cevirir (None gelirse 0.0 kabul eder)
    2. Birim "fahrenheit" ise Celsius -> Fahrenheit cevirir yapar
    3. Sonucu bir ondalik hassasiyetle formatlar ve birim sembolunu ekler

    KULLANIM ALANI:
    Kullanicilara sicaklik degerini gosterirken kullanilir. Arayuzde
    gorsel olarak temiz ve tutarli bir format saglar.

    Args:
        temp: Sicaklik degeri
        unit: Birim (celsius veya fahrenheit)

    Returns:
        str: Formatlanmis sicaklik (orn: "15°C")
    """
    try:
        t = float(temp) if temp is not None else 0.0
    except (ValueError, TypeError):
        t = 0.0
    if unit == "fahrenheit":
        temp_f = t * 9/5 + 32
        return f"{temp_f:.1f}°F"
    return f"{t:.1f}°C"


def celsius_to_fahrenheit(celsius: float) -> float:
    """
    Celsius'i Fahrenheit'a cevirir.

    AÇIKLAMA:
    Bu fonksiyon, Celsius cinsinden verilen sicaklik degerini Fahrenheit
    birimine cevirir. Celsius - Fahrenheit arasindaki iliski lineer'dir:
    F = C * 9/5 + 32

    Ornekler:
    - celsius_to_fahrenheit(0) -> 32.0 (donma noktasi)
    - celsius_to_fahrenheit(100) -> 212.0 (kaynama noktasi)
    - celsius_to_fahrenheit(20) -> 68.0 (oda sicakligi)
    - celsius_to_fahrenheit(-10) -> 14.0 (donuk hava)

    NASIL CALISIR:
    1. Gelen Celsius degerini 9/5 ile carpar
    2. Sonuca 32 ekler
    3. Fahrenheit degerini doner

    KULLANIM ALANI:
    Amerikan kaynaklilarindan gelen sicaklik verilerini
    Celsius'a veya Fahrenheit'a cevirmek icin kullanilir.
    """
    return celsius * 9/5 + 32


def fahrenheit_to_celsius(fahrenheit: float) -> float:
    """
    Fahrenheit'i Celsius'a cevirir.

    AÇIKLAMA:
    Bu fonksiyon, Fahrenheit cinsinden verilen sicaklik degerini Celsius
    birimine cevirir. Ters formul: C = (F - 32) * 5/9

    Ornekler:
    - fahrenheit_to_celsius(32) -> 0.0 (donma noktasi)
    - fahrenheit_to_celsius(212) -> 100.0 (kaynama noktasi)
    - fahrenheit_to_celsius(68) -> 20.0 (oda sicakligi)
    - fahrenheit_to_celsius(14) -> -10.0 (donuk hava)

    NASIL CALISIR:
    1. Gelen Fahrenheit degerinden 32 cikarir
    2. Sonucu 5/9 ile carpar
    3. Celsius degerini doner

    KULLANIM ALANI:
    Amerikan kaynaklilarindan gelen sicaklik verilerini
    TUrkiye'de kullanilan Celsius birimine cevirmek icin kullanilir.
    """
    return (fahrenheit - 32) * 5/9


def calculate_heat_index(temp: float, humidity: int) -> float:
    """
    Hissedilen sicaklik (heat index) hesaplar.

    AÇIKLAMA:
    Bu fonksiyon, sicaklik ve nem oranini kullanarak insan vucudunun
    hissettigi sicakligi hesaplar. Yüksek nemde, terleme ile soguma
    zorlastigi icin insan sicakligi daha hisseder. Heat Index sadece
    sicaklik >= 27°C (80°F) ve nem >= 40% durumunda gecerlidir,
    altinda sicakligi ayni doner. Rothfusz regression formulu kullanir.

    Ornekler:
    - calculate_heat_index(30, 50) -> ~32°C (biraz daha sicak hissedilir)
    - calculate_heat_index(35, 70) -> ~45°C (cok rahatsiz edici)
    - calculate_heat_index(40, 80) -> ~60°C (tehlikeli!)
    - calculate_heat_index(20, 60) -> 20°C (cok soguk, formul uygulanmaz)

    NASIL CALISIR:
    1. Sicaklik < 27°C veya nem < 40% ise dogrudan sicaklik doner
    2. Celsius'u Fahrenheit'a cevirir (formul Fahrenheit icin)
    3. Rothfusz regression ile heat index hesaplar (karmasik cok terimli formul)
    4. Heat index < sicaklik ise sicaklik doner (negatif olmamali)
    5. Sonucu tekrar Celsius'a cevirir ve doner

    KULLANIM ALANI:
    Yaz aylarinda kullaniciya "hissedilen sicaklik" bilgisini vermek
    icin kullanilir. Yüksek sicaklik ve nem kombnasyonunda tehlike seviyesini
    belirlemek icin onemlidir.

    Args:
        temp: Sicaklik (Celsius)
        humidity: Nem (%)

    Returns:
        float: Hissedilen sicaklik (Celsius)
    """
    try:
        t_val = float(temp) if temp is not None else 0
        h_val = int(humidity) if humidity is not None else 0
    except (ValueError, TypeError):
        return temp if isinstance(temp, (int, float)) else 0

    if t_val < 27 or h_val < 40:
        return t_val

    # Fahrenheit'a cevir ve heat index hesapla
    t = celsius_to_fahrenheit(t_val)
    rh = h_val

    # Rothfusz regression
    hi = (-42.379 + 2.04901523*t + 10.14333127*rh
          - 0.22475541*t*rh - 0.00683783*t*t
          - 0.05481717*rh*rh + 0.00122874*t*t*rh
          + 0.00085282*t*rh*rh - 0.00000199*t*t*rh*rh)

    # Heat index'i sinirla
    if hi < t:
        hi = t

    return fahrenheit_to_celsius(hi)


def calculate_wind_chill(temp: float, wind_speed: float) -> float:
    """
    Ruzgar etkisi (wind chill) hesaplar.

    AÇIKLAMA:
    Bu fonksiyon, soguk hava ve ruzgar kombinasyonunda insan vucudunun
    hissettigi sicakligi hesaplar. Ruzgar soguk havada vucuttan isi daha hizli
    alir, bu yuzden hissedilen sicaklik gerçek sicakliktan daha dusuk olur.
    Wind Chill sadece sicaklik <= 10°C ve ruzgar >= 4.8 km/h icin gecerlidir.

    Ornekler:
    - calculate_wind_chill(0, 20) -> ~-6°C (ruzgarla daha soguk hissedilir)
    - calculate_wind_chill(-5, 30) -> ~-13°C (dondurucu)
    - calculate_wind_chill(5, 10) -> 5°C (cok hafif ruzgar, etki yok)
    - calculate_wind_chill(15, 20) -> 15°C (cok sicak, formul uygulanmaz)

    NASIL CALISIR:
    1. Sicaklik > 10°C veya ruzgar < 4.8 km/h ise dogrudan sicaklik doner
    2. Metric wind chill formulu uygular:
       WC = 13.12 + 0.6215*T - 11.37*V^0.16 + 0.3965*T*V^0.16
       Burada T = sicaklik (C), V = ruzgar hizi (km/h)
    3. Sonucu doner (hisli sicaklik her zaman gerçek sicakliktan sogukuktur)

    KULLANIM ALANI:
    Kis aylarinda kullaniciya "hissedilen sicaklik" bilgisini vermek
    icin kullanilir. Donma riski belirlemede onemlidir.

    Args:
        temp: Sicaklik (Celsius)
        wind_speed: Ruzgar hizi (km/h)

    Returns:
        float: Hissedilen sicaklik (Celsius)
    """
    try:
        t_val = float(temp) if temp is not None else 0
        w_val = float(wind_speed) if wind_speed is not None else 0
    except (ValueError, TypeError):
        return temp if isinstance(temp, (int, float)) else 0

    if t_val > 10 or w_val < 4.8:
        return t_val

    # Wind chill formula (Metric)
    wc = (13.12 + 0.6215 * t_val - 11.37 * math.pow(w_val, 0.16)
          + 0.3965 * t_val * math.pow(w_val, 0.16))

    return wc


# =============================================================================
# Weather Analysis Functions
# =============================================================================

def get_weather_alert(weather_data: Dict) -> Optional[str]:
    """
    Hava durumunda uyari varligini kontrol eder.

    Args:
        weather_data: Hava durumu verisi

    Returns:
        str or None: Uyari mesaji veya None
    """
    if not weather_data:
        return None

    # Yagmur kontrolu
    precipitation = weather_data.get("precipitation", 0)
    if precipitation > 2.5:
        return "Yogun yagmur bekleniyor, semsiye almayi unutmayin"

    # Sicaklik kontrolu
    temp = weather_data.get("temperature", 20)
    if temp > 35:
        return "Cok sicak, bol su icin ve golgede kalin"
    elif temp < 0:
        return "Donmak riski var, dikkatli olun"

    # Ruzgar kontrolu
    wind_gusts = weather_data.get("wind_gusts", 0)
    if wind_gusts > 50:
        return "Guclu ruzgar, dikkatli olun"

    # Sis kontrolu
    weather_code = weather_data.get("weather_code", 0)
    if weather_code in [45, 48]:
        return "Sisli, suruslerde dikkatli olun"

    return None


def get_activity_suggestion(weather_data: Dict) -> Dict[str, str]:
    """
    Hava durumuna gore aktivite onerisi uretir.

    Args:
        weather_data: Hava durumu verisi

    Returns:
        dict: Aktivite onerileri
    """
    if not weather_data:
        return {"general": "Hava durumu bilinmiyor"}

    suggestions = {
        "general": "",
        "outdoor": "",
        "clothing": ""
    }

    weather_code = weather_data.get("weather_code", 0)
    temp = weather_data.get("temperature", 20)
    precipitation = weather_data.get("precipitation", 0)

    # Genel oneri
    if weather_code in [0, 1]:
        suggestions["general"] = "Harika hava, disari cikmak icin ideal"
    elif weather_code in [2, 3]:
        suggestions["general"] = "Bulutlu ama hos bir hava"
    elif weather_code in [45, 48]:
        suggestions["general"] = "Sisli, gorus mesafesi dusuk"
    elif 51 <= weather_code <= 67 or 80 <= weather_code <= 82:
        suggestions["general"] = "Yagmurlu, disari cikmak icin uygun degil"
    elif 71 <= weather_code <= 77 or 85 <= weather_code <= 86:
        suggestions["general"] = "Kar yagiyor, dikkatli olun"
    elif weather_code >= 95:
        suggestions["general"] = "Firtinali, kesinlikle disari cikmayin"

    # Dis mekan onerisi
    if precipitation > 1:
        suggestions["outdoor"] = "Kapali mekanlari tercih edin (AVM, kafe, muzeler)"
    elif temp > 30:
        suggestions["outdoor"] = "Klimali veya golgeli alanlari tercih edin"
    elif temp < 5:
        suggestions["outdoor"] = "Korumakli alanlari tercih edin"
    else:
        suggestions["outdoor"] = "Dis mekanlar icin uygun hava"

    # Kiyafet onerisi
    if temp < 5:
        suggestions["clothing"] = "Kis kiyafeti, mont, atki, eldiven"
    elif temp < 15:
        suggestions["clothing"] = "Ceket veya hirka"
    elif temp < 25:
        suggestions["clothing"] = "Hafif giysiler"
    else:
        suggestions["clothing"] = "Ince, nefes alan giysiler"

    if precipitation > 0:
        suggestions["clothing"] += ", semsiye veya yagmurluk"

    return suggestions


def calculate_uv_index_risk(uv_index: float) -> Dict[str, str]:
    """
    UV indeksine gore risk seviyesini belirler.

    AÇIKLAMA:
    Bu fonksiyon, Dunya Saglik Orgutu (WHO) standardlarina gore UV indeksini
    5 risk seviyesinde siniflandirir. UV indeksi, gunesin UV isinlarinin
    gucunu gosterir ve cilt sagligi icin onemlidir. Her seviye icin
    bir renk kodu ve oneri mesaji doner.

    Ornekler:
    - calculate_uv_index_risk(1) -> {"level": "Low", "tr": "Dusuk", ...}
    - calculate_uv_index_risk(6) -> {"level": "High", "tr": "Yuksek", ...}
    - calculate_uv_index_risk(11) -> {"level": "Extreme", "tr": "Ekstrem", ...}

    NASIL CALISIR:
    1. UV indeks degerine gore seviyeyi belirler (0-2 Dusuk, 3-5 Orta, vb.)
    2. Her seviye icin risk adini, Turkce karsiligini, renk kodunu
       ve oneri mesajini doner

    KULLANIM ALANI:
    Kullanicilara guneste kalma suresi ve korunma onlemleri hakkinda
    bilgi vermek icin kullanilir. Ozelikle yaz aylarinda onemlidir.

    Args:
        uv_index: UV indeks degeri

    Returns:
        dict: Risk seviyesi, Turkce aciklama, renk kodu, oneri
    """
    if uv_index <= 2:
        return {
            "level": "Low",
            "tr": "Dusuk",
            "color": "green",
            "advice": "Korumaya gerek yok"
        }
    elif uv_index <= 5:
        return {
            "level": "Moderate",
            "tr": "Orta",
            "color": "yellow",
            "advice": "Ogle gunleri gogus koruyucu kullanin"
        }
    elif uv_index <= 7:
        return {
            "level": "High",
            "tr": "Yuksek",
            "color": "orange",
            "advice": "Gunes kremi surun ve sikigi giyin"
        }
    elif uv_index <= 10:
        return {
            "level": "Very High",
            "tr": "Cok Yuksek",
            "color": "red",
            "advice": "Ekstra onlem alın, 10-16 arasi disari cikmayin"
        }
    else:
        return {
            "level": "Extreme",
            "tr": "Ekstrem",
            "color": "purple",
            "advice": "Guneslenmekten tamamen kaçinin"
        }


# =============================================================================
# Summary Functions
# =============================================================================

def summarize_weather_data(weather_data: Dict) -> str:
    """
    Hava durumu verisini ozetler.

    AÇIKLAMA:
    Bu fonksiyon, karmasik hava durumu verisini basit ve anlasilir bir
    metin olarak ozetler. Sicaklik ve hava durumu aciklamasini birlestirir.

    Ornekler:
    - summarize_weather_data({"temperature": 15.5, "weather_code": 2})
      -> "15.5°C, Parçalı bulutlu"
    - summarize_weather_data({"temperature": -3, "weather_code": 71})
      -> "-3.0°C, Hafif kar"
    - summarize_weather_data({}) -> "Bilinmiyor"

    NASIL CALISIR:
    1. Hava durumu verisi yoksa "Bilinmiyor" doner
    2. Sicaklik degerini alir ve formatlar
    3. Hava durum kodunu aciklamaya donusturur
    4. Ikisini birlestirip doner

    KULLANIM ALANI:
    Kullaniciya hava durumunu hizli ve ozet bir sekilde
    gostermek icin kullanilir.

    Args:
        weather_data: Hava durumu verisi

    Returns:
        str: Ozet metin (orn: "15°C, Parçalı bulutlu")
    """
    if not weather_data:
        return "Bilinmiyor"

    temp = weather_data.get("temperature", 0)
    weather_code = weather_data.get("weather_code", 0)

    parsed = parse_weather_code(weather_code)

    temp_str = format_temperature(temp)
    desc_str = parsed.get("tr", "Bilinmiyor")

    return f"{temp_str}, {desc_str}"


def compare_weather(weather1: Dict, weather2: Dict) -> Dict[str, Any]:
    """
    Iki hava durumunu karsilastirir.

    AÇIKLAMA:
    Bu fonksiyon, iki farkli konum veya zamanin hava durumunu
    karsilastirir. Sicaklik farki, yagmur farki ve hangisinin daha sicak
    veya daha yagmurlu oldugunu doner.

    Ornekler:
    - compare_weather({"temperature": 20, "precipitation": 0},
                      {"temperature": 25, "precipitation": 1})
      -> {"temperature_diff": 5.0, "precipitation_diff": 1.0,
          "warmer": true, "wetter": true}
    - compare_weather({"temperature": 30, ...}, {"temperature": 15, ...})
      -> {"temperature_diff": -15.0, "warmer": false, ...}

    NASIL CALISIR:
    1. Iki hava durumu verisi de yoksa hata doner
    2. Ilk ve ikinci hava durumundan sicaklik farkini hesaplar
    3. Yagmur farkini hesaplar
    4. Ikinci ilkinden daha sicak mi kontrol eder
    5. Ikinci ilkinden daha yagmurlu mu kontrol eder
    6. Tum sonuclari sozluk olarak doner

    KULLANIM ALANI:
    Kullanicinin iki konum arasinda secim yapmasina yardimci olmak
    veya hava degisimini gostermek icin kullanilir.

    Args:
        weather1: Ilk hava durumu
        weather2: Ikinci hava durumu

    Returns:
        dict: Karsilastirma sonuclari
    """
    if not weather1 or not weather2:
        return {"error": "Gecersiz hava durumu verisi"}

    temp1 = weather1.get("temperature", 0)
    temp2 = weather2.get("temperature", 0)

    precip1 = weather1.get("precipitation", 0)
    precip2 = weather2.get("precipitation", 0)

    return {
        "temperature_diff": round(temp2 - temp1, 1),
        "precipitation_diff": round(precip2 - precip1, 2),
        "warmer": temp2 > temp1,
        "wetter": precip2 > precip1
    }


# =============================================================================
# Utility Functions for Frontend Display
# =============================================================================

def get_weather_color_code(weather_code: int) -> str:
    """
    Hava durumuna gore renk kodu dondurur (UI icin).

    AÇIKLAMA:
    Bu fonksiyon, WMO hava durum koduna karsilik gelen bir renk kodu doner.
    Renk kodlari, kullanici arayuzunde hava durumunu gorsel olarak temsil
    etmek icin kullanilir (orn: arka plan rengi, ikon rengi, vb.).
    Tanimsiz kodlar icin varsayilan gri renk doner.

    Ornekler:
    - get_weather_color_code(0) -> "#FFD700" (Altin - Acik gokyuzu)
    - get_weather_color_code(61) -> "#4682B4" (Celik mavisi - Yagmur)
    - get_weather_color_code(95) -> "#8B0000" (Koyu kirmizi - Firtina)
    - get_weather_color_code(999) -> "#CCCCCC" (Varsayilan gri)

    NASIL CALISIR:
    1. Gelen hava durum kodunu integer'a cevirir
    2. color_map sozlugunda kodu arar
    3. Kod varsa ilgili renk kodunu doner, yoksa "#CCCCCC" doner

    KULLANIM ALANI:
    Frontend'de hava durumunu gorsel olarak temsil etmek icin
    kullanilir. Arka plan renkleri, ikon renkleri, grafikler vb.

    Args:
        weather_code: WMO weather code

    Returns:
        str: Hex renk kodu (orn: "#FFD700")
    """
    color_map = {
        0: "#FFD700",  # Gold - Clear sky
        1: "#FFEC8B",  # Light gold - Mainly clear
        2: "#B0C4DE",  # Light steel blue - Partly cloudy
        3: "#708090",  # Slate gray - Overcast
        45: "#A9A9A9",  # Dark gray - Fog
        48: "#808080",  # Gray - Depositing rime fog
        61: "#4682B4",  # Steel blue - Rain
        71: "#E0FFFF",  # Light cyan - Snow
        95: "#8B0000",  # Dark red - Thunderstorm
    }

    try:
        return color_map.get(int(weather_code) if weather_code is not None else -1, "#CCCCCC")
    except (ValueError, TypeError):
        return "#CCCCCC"


def _extract_hhmm(context_time: Optional[str]) -> Optional[str]:
    """Verilen zaman bilgisinden HH:MM formatını çıkarır."""
    if not context_time:
        return None

    raw = str(context_time).strip()
    if not raw:
        return None

    # "09:30" veya "09:30:00" formatı
    if len(raw) >= 5 and raw[2] == ":":
        return raw[:5]

    # ISO datetime formatları (örn: 2026-03-15T09:30:00)
    try:
        dt = datetime.fromisoformat(raw.replace("Z", ""))
        return dt.strftime("%H:%M")
    except ValueError:
        return None


def _build_context_prefix(context_time: Optional[str], point_name: Optional[str]) -> Optional[str]:
    """Öneri metinlerine eklenecek bağlam önekini üretir."""
    hhmm = _extract_hhmm(context_time)
    clean_point = (point_name or "").strip()

    if hhmm and clean_point:
        return f"{clean_point} için {hhmm} civarı"
    if hhmm:
        return f"{hhmm} civarı"
    if clean_point:
        return f"{clean_point} için"
    return None


def get_weather_advice(
    weather_data: Dict,
    context_time: Optional[str] = None,
    point_name: Optional[str] = None
) -> Dict:
    """
    Hava durumuna göre akıllı ve zaman-bağlamlı tavsiyeler üretir.

    Args:
        weather_data: Hava verisi sözlüğü
        context_time: Saat bağlamı ("09:30" veya ISO datetime)
        point_name: Nokta adı (opsiyonel)

    Returns:
        dict: {
            "alert_level": "info" | "warning" | "danger",
            "items": [{"emoji": str, "text": str, "type": str}, ...],
            "context_time": "HH:MM" | None
        }
    """
    if not weather_data:
        return {"alert_level": "info", "items": [], "context_time": _extract_hhmm(context_time)}

    temp = weather_data.get("temperature", 20)
    precipitation = weather_data.get("precipitation", 0) or 0
    precip_prob = weather_data.get("precipitation_probability", 0) or 0
    wind_speed = weather_data.get("wind_speed", 0) or 0
    wind_gusts = weather_data.get("wind_gusts", 0) or 0
    weather_code = weather_data.get("weather_code", 0) or 0

    items = []
    alert_level = "info"

    # --- Yağış uyarıları ---
    if weather_code >= 95:
        items.append({"emoji": "⛈️", "text": "Fırtına var, dışarı çıkmaktan kaçının", "type": "storm"})
        alert_level = "danger"
    elif weather_code in [71, 73, 75, 77, 85, 86]:
        items.append({"emoji": "❄️", "text": "Kar yağıyor, kaygan zemine dikkat edin", "type": "snow"})
        alert_level = "warning"
    elif weather_code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
        if precipitation > 5 or precip_prob > 70:
            items.append({"emoji": "🌧️", "text": "Yoğun yağmur, şemsiye şart", "type": "umbrella"})
            alert_level = "warning"
        else:
            items.append({"emoji": "☂️", "text": "Yağmur bekleniyor, şemsiye alın", "type": "umbrella"})
            if alert_level == "info":
                alert_level = "warning"
    elif precip_prob >= 50:
        items.append({"emoji": "🌂", "text": f"Yağış ihtimali %{precip_prob}, yanınıza şemsiye alın", "type": "umbrella"})
        if alert_level == "info":
            alert_level = "warning"

    # --- Sıcaklık uyarıları ---
    if temp <= -5:
        items.append({"emoji": "🥶", "text": "Çok soğuk! Mont, bere, eldiven şart", "type": "cold"})
        alert_level = "danger"
    elif temp < 5:
        items.append({"emoji": "🧥", "text": "Soğuk hava, kalın mont giyin", "type": "cold"})
        if alert_level == "info":
            alert_level = "warning"
    elif temp < 12:
        items.append({"emoji": "🧣", "text": "Serin hava, ceket veya hırka alın", "type": "cold"})
    elif temp >= 38:
        items.append({"emoji": "🌡️", "text": "Aşırı sıcak! Bol su için, güneşten kaçının", "type": "heat"})
        alert_level = "danger"
    elif temp >= 32:
        items.append({"emoji": "☀️", "text": "Çok sıcak, bol su için ve gölgede kalın", "type": "heat"})
        if alert_level == "info":
            alert_level = "warning"
    elif temp >= 26:
        items.append({"emoji": "😎", "text": "Güneşli ve sıcak, güneş kremi öneririz", "type": "sun"})

    # --- Rüzgar uyarıları ---
    if wind_gusts > 70 or wind_speed > 55:
        items.append({"emoji": "💨", "text": "Çok güçlü rüzgar, şemsiye işe yaramaz", "type": "wind"})
        alert_level = "danger"
    elif wind_gusts > 45 or wind_speed > 35:
        items.append({"emoji": "🌬️", "text": "Kuvvetli rüzgar, dikkatli olun", "type": "wind"})
        if alert_level == "info":
            alert_level = "warning"

    # --- Sis uyarısı ---
    if weather_code in [45, 48]:
        items.append({"emoji": "🌫️", "text": "Sisli hava, görüş mesafesi düşük", "type": "fog"})
        if alert_level == "info":
            alert_level = "warning"

    # İki olumsuz durum varsa seviyeyi warning'e çek
    if len(items) >= 2 and alert_level == "info":
        alert_level = "warning"

    # Zaman/nokta bağlamı ekle (örn: "Kadıköy için 09:30 civarı ...")
    context_prefix = _build_context_prefix(context_time, point_name)
    context_hhmm = _extract_hhmm(context_time)
    if context_prefix:
        for item in items:
            item["text"] = f"{context_prefix}: {item['text']}"
            if context_hhmm:
                item["time"] = context_hhmm
            if point_name:
                item["point"] = point_name

    return {"alert_level": alert_level, "items": items, "context_time": context_hhmm}


def get_weather_background_class(weather_code: int) -> str:
    """
    Hava durumuna gore CSS class adi dondurur.

    AÇIKLAMA:
    Bu fonksiyon, WMO hava durum kodunun kategorisine gore CSS class adi
    doner. Bu class'lar frontend'de hava durumuna gore arayuzu stillendirmek
    icin kullanilir (orn: "weather-clear", "weather-rain" gibi).
    Her kategori icin bir class tanimlanmistir.

    Ornekler:
    - get_weather_background_class(0) -> "weather-clear"
    - get_weather_background_class(61) -> "weather-rain"
    - get_weather_background_class(95) -> "weather-thunderstorm"
    - get_weather_background_class(999) -> "weather-unknown"

    NASIL CALISIR:
    1. Hava durum kodunu aciklayarak kategorisini alir
    2. Kategoriyi class_map sozlugunda arar
    3. Kategori varsa ilgili class adini doner, yoksa "weather-unknown" doner

    KULLANIM ALANI:
    Frontend CSS stilinde hava durumuna gore dinamik arayuz
    stillendirmesi icin kullanilir. Örnegin yagmurlu havalarda mavi,
    firtinali havalarda kirmizi arka plan.

    Args:
        weather_code: WMO weather code

    Returns:
        str: CSS class adi
    """
    code_info = parse_weather_code(weather_code)
    category = code_info.get("category", "unknown")

    class_map = {
        "clear": "weather-clear",
        "partly_cloudy": "weather-partly-cloudy",
        "cloudy": "weather-cloudy",
        "fog": "weather-fog",
        "drizzle": "weather-drizzle",
        "rain": "weather-rain",
        "freezing_rain": "weather-freezing-rain",
        "snow": "weather-snow",
        "rain_showers": "weather-rain-showers",
        "snow_showers": "weather-snow-showers",
        "thunderstorm": "weather-thunderstorm",
        "unknown": "weather-unknown"
    }

    return class_map.get(category, "weather-unknown")
