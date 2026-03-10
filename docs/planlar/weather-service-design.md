# Hava Durumu Servisi - Tasarım Belgesi

## Sürüm
- **Version:** 1.0
- **Tarih:** 2026-03-10
- **Durum:** Faz 1 Implementation

---

## 1. Genel Bakış

### 1.1 Amaç
OpenRoutePlanner uygulamasına hava durumu bilgisi entegrasyonu sağlamak. Kullanıcıların rota planlaması sırasında hava koşullarını görebilmelerini ve akıllı öneriler alabilmelerini sağlamak.

### 1.2 API Seçimi: OpenMeteo
- **URL:** https://api.open-meteo.com/v1/forecast
- **Lisans:** Non-commercial use (10.000 günlük API call limiti)
- **API Key:** Gerekmiyor
- **Türkiye Coverage:** ✅ Yeterli

### 1.3 Faz 1 Kapsamı
- Güncel hava durumu (current weather)
- Saatlik forecast (hourly forecast)
- Cache mekanizması (memory + SQLite)
- Temel endpoint'ler

---

## 2. Mimari Tasarım

### 2.1 Modül Yapısı

```
backend/
├── weather_service.py      # Ana servis modülü
├── weather_utils.py         # Yardımcı fonksiyonlar
└── cache/
    └── weather_cache.db     # SQLite cache (opsiyonel)
```

### 2.2 Veri Akışı

```
Frontend Request
    ↓
Flask app.py (endpoint)
    ↓
weather_service.py (business logic)
    ↓
[Cache Check] → Hit: Return Cached Data
    ↓ Miss
weather_utils.py (API call)
    ↓
OpenMeteo API
    ↓
Parse & Cache Response
    ↓
Return to Frontend
```

---

## 3. API Tasarımı

### 3.1 Endpoint 1: Güncel Hava Durumu

**Endpoint:** `GET /api/weather`

**Query Parameters:**
| Parametre | Tip | Zorunlu | Açıklama |
|-----------|-----|---------|----------|
| `lat` | float | Evet | Enlem (örn: 41.0082) |
| `lon` | float | Evet | Boylam (örn: 28.9784) |

**Response Format:**
```json
{
  "success": true,
  "data": {
    "location": {
      "lat": 41.0082,
      "lon": 28.9784,
      "name": "Istanbul, Turkey"
    },
    "current": {
      "timestamp": "2026-03-10T14:00:00Z",
      "temperature": 15.5,
      "apparent_temperature": 14.2,
      "humidity": 65,
      "precipitation": 0.0,
      "rain": 0.0,
      "showers": 0.0,
      "snowfall": 0.0,
      "weather_code": 0,
      "weather_description": "Clear sky",
      "cloud_cover": 20,
      "wind_speed": 12.5,
      "wind_direction": 180,
      "wind_gusts": 18.0
    },
    "cache_hit": false
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Invalid coordinates",
  "message": "Latitude must be between -90 and 90"
}
```

---

### 3.2 Endpoint 2: Saatlik Forecast

**Endpoint:** `GET /api/weather/forecast`

**Query Parameters:**
| Parametre | Tip | Zorunlu | Açıklama |
|-----------|-----|---------|----------|
| `lat` | float | Evet | Enlem |
| `lon` | float | Evet | Boylam |
| `hours` | int | Hayır (24) | Forecast saati (max 168) |
| `timezone` | string | Hayır (auto) | Timezone (örn: Europe/Istanbul) |

**Response Format:**
```json
{
  "success": true,
  "data": {
    "location": {
      "lat": 41.0082,
      "lon": 28.9784,
      "timezone": "Europe/Istanbul"
    },
    "hourly": {
      "time": ["2026-03-10T14:00", "2026-03-10T15:00", ...],
      "temperature": [15.5, 16.2, ...],
      "precipitation": [0.0, 0.0, ...],
      "precipitation_probability": [0, 5, ...],
      "weather_code": [0, 0, ...],
      "wind_speed": [12.5, 14.0, ...]
    },
    "cache_hit": false
  }
}
```

---

### 3.3 Endpoint 3: Rota Kontrolü

**Endpoint:** `POST /api/weather/check-route`

**Request Body:**
```json
{
  "points": [
    {"lat": 41.0082, "lon": 28.9784, "name": "Kadikoy"},
    {"lat": 41.0422, "lon": 29.0067, "name": "Besiktas"}
  ],
  "start_time": "2026-03-10T14:00:00"
}
```

**Response Format:**
```json
{
  "success": true,
  "data": {
    "route_weather": [
      {
        "point": "Kadikoy",
        "lat": 41.0082,
        "lon": 28.9784,
        "weather": {
          "temperature": 15.5,
          "precipitation": 0.0,
          "weather_code": 0,
          "wind_speed": 12.5
        }
      },
      {
        "point": "Besiktas",
        "lat": 41.0422,
        "lon": 29.0067,
        "weather": {
          "temperature": 16.0,
          "precipitation": 0.2,
          "weather_code": 61,
          "wind_speed": 15.0
        }
      }
    ],
    "warnings": [
      "Besiktas'ta hafif yağmur bekleniyor"
    ],
    "overall_conditions": "partly_cloudy"
  }
}
```

---

## 4. OpenMeteo API Entegrasyonu

### 4.1 Base URL
```
https://api.open-meteo.com/v1/forecast
```

### 4.2 Current Weather İstek Parametreleri

```
?latitude={lat}
&longitude={lon}
&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,showers,snowfall,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m,wind_gusts_10m
&timezone=auto
```

### 4.3 Hourly Forecast İstek Parametreleri

```
?latitude={lat}
&longitude={lon}
&hourly=temperature_2m,precipitation,precipitation_probability,weather_code,wind_speed_10m,wind_gusts_10m
&forecast_hours={hours}
&timezone=auto
```

---

## 5. WMO Weather Code Mapping

| Code | Description | Turkish | Icon |
|------|-------------|---------|------|
| 0 | Clear sky | Açık gökyüzü | ☀️ |
| 1, 2, 3 | Partly cloudy | Parçalı bulutlu | ⛅ |
| 45, 48 | Fog | Sis | 🌫️ |
| 51-55 | Drizzle | Çiseleme | 🌧️ |
| 61-65 | Rain | Yağmur | 🌧️ |
| 71-75 | Snow fall | Kar | ❄️ |
| 80-82 | Rain showers | Sağanak yağmur | ⛈️ |
| 95-99 | Thunderstorm | Fırtına | ⛈️ |

---

## 6. Cache Stratejisi

### 6.1 Cache Türleri

**Memory Cache (Python dict)**
- Ana cache katmanı
- Uygulama ömrü boyunca
- Hızlı erişim

**SQLite Cache (opsiyonel)**
- Persist cache
- Uygulama restart'larında veri korunur
- 15 dakika TTL

### 6.2 Cache Key Formatı

```
current:{lat}:{lon}
hourly:{lat}:{lon}:{hours}:{date}
```

### 6.3 Cache Invalidation

- **Time-based:** 15 dakika sonra expire
- **Manual:** Cache temizleme endpoint'i (opsiyonel)

---

## 7. Error Handling

### 7.1 Hata Türleri

| Exception | Açıklama | HTTP Status |
|-----------|----------|-------------|
| `InvalidCoordinatesError` | Geçersiz koordinat | 400 |
| `NetworkError` | API bağlantı hatası | 503 |
| `RateLimitError` | Rate limit aşıldı | 429 |
| `ParseError` | Response parse hatası | 500 |

### 7.2 Fallback Stratejisi

1. **Cache Fallback:** API hatasında cache'den dön
2. **Partial Response:** Kısmi veri dön, kullanıcı bilgilendir
3. **Graceful Degradation:** Hava durumu alınamazsa rota hesaplamaya devam et

---

## 8. Kod Yapısı

### 8.1 weather_service.py

```python
"""
weather_service.py - OpenMeteo API entegrasyonu

Güncel hava durumu ve saatlik forecast sağlar.
Cache mekanizması ile performans optimizasyonu.
"""

# Imports
import time
import hashlib
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

# Local imports
from logging_config import get_logger
from weather_utils import (
    parse_weather_code,
    validate_coordinates,
    build_cache_key
)

# Constants
OPENMETEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL_SECONDS = 900  # 15 dakika

# Global cache
_weather_cache: Dict[str, dict] = {}

# Exception classes
class WeatherServiceError(Exception):
    """Base exception for weather service"""
    pass

class InvalidCoordinatesError(WeatherServiceError):
    """Invalid coordinates provided"""
    pass

class NetworkError(WeatherServiceError):
    """Network error"""
    pass

# Functions
def get_current_weather(lat: float, lon: float) -> dict:
    """Get current weather for location"""

def get_hourly_forecast(lat: float, lon: float, hours: int = 24) -> dict:
    """Get hourly weather forecast"""

def check_route_weather(points: List[dict], start_time: str = None) -> dict:
    """Check weather conditions along a route"""

def _get_from_cache(key: str) -> Optional[dict]:
    """Get data from memory cache"""

def _save_to_cache(key: str, data: dict) -> None:
    """Save data to memory cache"""

def _is_cache_valid(timestamp: float) -> bool:
    """Check if cache entry is still valid"""
```

### 8.2 weather_utils.py

```python
"""
weather_utils.py - Hava durumu yardımcı fonksiyonları

WMO code parsing, validasyon, cache utilities
"""

# Constants
WMO_WEATHER_CODES = {
    0: {"description": "Clear sky", "tr": "Açık gökyüzü", "icon": "sun"},
    # ...
}

# Functions
def parse_weather_code(code: int) -> dict:
    """Parse WMO weather code to description"""

def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate latitude and longitude"""

def build_cache_key(prefix: str, lat: float, lon: float, **kwargs) -> str:
    """Build cache key from parameters"""

def format_temperature(temp: float, unit: str = "celsius") -> str:
    """Format temperature for display"""

def calculate_apparent_temperature(temp: float, humidity: int, wind_speed: float) -> float:
    """Calculate apparent temperature (feels like)"""

def get_weather_alert(weather_data: dict) -> Optional[str]:
    """Generate weather alert if conditions warrant it"""
```

---

## 9. Logging

### 9.1 Log Seviyeleri

| Olay | Seviye | Mesaj |
|------|--------|-------|
| API isteği | INFO | `Fetching weather for {lat}, {lon}` |
| Cache hit | DEBUG | `Cache hit for key: {key}` |
| Cache miss | DEBUG | `Cache miss for key: {key}` |
| API hatası | ERROR | `OpenMeteo API error: {error}` |
| Rate limit | WARNING | `Rate limit approached` |

### 9.2 Structured Logging

```python
logger.info_data("Weather fetched",
                lat=lat,
                lon=lon,
                cache_hit=False,
                response_time_ms=response_time)
```

---

## 10. Test Senaryoları

### 10.1 Unit Tests

```python
# test_weather_service.py

def test_validate_coordinates():
    assert validate_coordinates(41.0082, 28.9784) == True
    assert validate_coordinates(91, 0) == False
    assert validate_coordinates(-91, 0) == False

def test_parse_weather_code():
    result = parse_weather_code(0)
    assert result["description"] == "Clear sky"

def test_cache_key_building():
    key = build_cache_key("current", 41.0082, 28.9784)
    assert key == "current:41.0082:28.9784"

def test_get_current_weather_cache():
    # First call - cache miss
    result1 = get_current_weather(41.0082, 28.9784)
    # Second call - cache hit
    result2 = get_current_weather(41.0082, 28.9784)
    assert result1 == result2

def test_get_current_weather_invalid_coords():
    with pytest.raises(InvalidCoordinatesError):
        get_current_weather(91, 0)
```

### 10.2 Integration Tests

```python
def test_api_integration():
    """Test actual OpenMeteo API call"""
    result = get_current_weather(41.0082, 28.9784)
    assert "current" in result
    assert "temperature" in result["current"]

def test_hourly_forecast():
    """Test hourly forecast endpoint"""
    result = get_hourly_forecast(41.0082, 28.9784, hours=24)
    assert len(result["hourly"]["time"]) == 24

def test_route_weather_check():
    """Test route weather check"""
    points = [
        {"lat": 41.0082, "lon": 28.9784, "name": "Kadikoy"},
        {"lat": 41.0422, "lon": 29.0067, "name": "Besiktas"}
    ]
    result = check_route_weather(points)
    assert len(result["route_weather"]) == 2
```

---

## 11. Performans Hedefleri

| Metrik | Hedef | Ölçüm |
|--------|-------|-------|
| Cache hit response time | ≤ 250ms (p95) | Zaman ölçümü |
| Cache miss response time | ≤ 1200ms (p95) | Zaman ölçümü |
| Cache hit rate | ≥ 60% | Cache hit sayacı |
| Memory usage | ≤ 50MB | Memory profiling |

---

## 12. Güvenlik

### 12.1 Rate Limiting
- OpenMeteo: 10.000 günlük limit
- İç rate limiting: İsteğe bağlı

### 12.2 Input Validation
- Koordinat aralığı kontrolü
- Saat aralığı kontrolü (max 168)
- SQL injection koruması (SQLite kullanılıyor)

---

## 13. Faz 2 ve Faz 3 için Hazırlık

### 13.1 Timeline Entegrasyonu (Faz 2)
- `time_planner.py` ile entegrasyon noktası
- Her segment için hava bilgisi ekleme

### 13.2 Akıllı Öneriler (Faz 3)
- `weather_recommendations.py` için veri yapısı
- Hava durumuna göre mekan önerisi mantığı

---

## 14. Deployment Checklist

- [ ] weather_service.py oluşturuldu
- [ ] weather_utils.py oluşturuldu
- [ ] app.py endpoint'leri eklendi
- [ ] Cache mekanizması test edildi
- [ ] Error handling test edildi
- [ ] Logging yapılandırıldı
- [ ] Unit tests yazıldı
- [ ] Integration tests geçti
- [ ] Dokümantasyon güncellendi
- [ ] progress.md güncellendi

---

## Kaynaklar

- OpenMeteo API Docs: https://open-meteo.com/en/docs
- WMO Weather Codes: https://www.nodc.noaa.gov/archive/arc0021/0002199/1.1/data/0-data/HTML/WMO-CODE/WMO4677.HTM
- Proje Planı: `docs/planlar/hava-durumu-entegrasyon-plani.md`
