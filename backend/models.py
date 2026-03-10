"""
models.py - Pydantic Data Models for Request/Response Validation

Tüm API request ve response'ları için tip güvenliği ve validation.
Pydantic modelleri otomatik validation, type coercion ve JSON serialization sağlar.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class RouteType(str, Enum):
    """Rota tipi enum"""
    ROUTE_1 = "route_1"
    ROUTE_2 = "route_2"
    ROUTE_3 = "route_3"


class IconType(str, Enum):
    """Lokasyon icon tipi"""
    STAR = "star"
    HOME = "home"
    WORK = "work"
    PARK = "park"
    SHOP = "shop"
    CAFE = "cafe"
    RESTAURANT = "restaurant"
    OTHER = "other"


class WeatherCategory(str, Enum):
    """Hava durumu kategorisi"""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    FOGGY = "foggy"
    RAINY = "rainy"
    SNOWY = "snowy"
    STORMY = "stormy"
    UNKNOWN = "unknown"


# =============================================================================
# COMMON MODELS
# =============================================================================

class Coordinate(BaseModel):
    """Koordinat modeli - enlem ve boylam validation"""
    lat: float = Field(..., ge=-90, le=90, description="Enlem (-90 ile 90 arası)")
    lon: float = Field(..., ge=-180, le=180, description="Boylam (-180 ile 180 arası)")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"lat": 41.0082, "lon": 28.9784},  # İstanbul
                {"lat": 39.9334, "lon": 32.8597},  # Ankara
            ]
        }
    )


class PointWithName(BaseModel):
    """İsimli nokta modeli"""
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    name: str = Field(default="", description="Nokta adı (opsiyonel)")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"lat": 41.0082, "lon": 28.9784, "name": "Kadıköy"},
            ]
        }
    )


class PaginationParams(BaseModel):
    """Pagination parametreleri"""
    page: int = Field(default=1, ge=1, description="Sayfa numarası (1'den başlar)")
    per_page: int = Field(default=20, ge=1, le=100, description="Her sayfadaki eleman sayısı")
    sort_by: str = Field(default="created_at", description="Sıralama alanı")


# =============================================================================
# ROUTE MODELS
# =============================================================================

class RouteCalculateRequest(BaseModel):
    """Rota hesaplama isteği"""
    points: List[Coordinate] = Field(..., min_length=2, description="En az 2 nokta gerekli")
    num_routes: int = Field(default=3, ge=1, le=10, description="Kaç alternatif rota hesaplansın")
    route_type: RouteType = Field(default=RouteType.ROUTE_1, description="Rota tipi")

    @field_validator('points')
    @classmethod
    def validate_unique_points(cls, v: List[Coordinate]) -> List[Coordinate]:
        """Aynı nokta tekrar ediyorsa uyar"""
        unique_coords = set((p.lat, p.lon) for p in v)
        if len(unique_coords) != len(v):
            # Duplicate var ama engellemiyoruz, sadece log atıyoruz
            pass
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "points": [
                        {"lat": 41.0082, "lon": 28.9784},
                        {"lat": 41.0422, "lon": 29.0067},
                        {"lat": 41.0580, "lon": 28.9874}
                    ],
                    "num_routes": 3
                }
            ]
        }
    )


class RouteSegment(BaseModel):
    """Rota segmenti"""
    distance_km: float
    duration_minutes: int
    path: List[List[float]]  # [[lat, lon], ...]


class RouteData(BaseModel):
    """Rota verisi"""
    id: str
    name: str
    points: List[List[float]]
    route_coords: List[List[float]]
    distance_km: float
    duration_minutes: int
    route_type: str
    alternative_index: int = 0


class RouteResponse(BaseModel):
    """Rota hesaplama response"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None


# =============================================================================
# SAVED ROUTE MODELS
# =============================================================================

class SaveRouteRequest(BaseModel):
    """Rota kaydetme isteği"""
    name: str = Field(..., min_length=1, max_length=200, description="Rota adı")
    points: List[List[float]] = Field(..., min_length=2)
    route_coords: List[List[float]] = Field(..., min_length=2)
    distance_km: float = Field(..., ge=0)
    duration_minutes: int = Field(..., ge=0)
    route_type: str = Field(default="route_1")
    description: str = Field(default="", max_length=1000)
    tags: List[str] = Field(default_factory=list)


class UpdateRouteRequest(BaseModel):
    """Rota güncelleme isteği"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    tags: Optional[List[str]] = None
    favorite: Optional[bool] = None


class RouteListItem(BaseModel):
    """Rota listesi elemanı"""
    id: str
    name: str
    description: str
    distance_km: float
    duration_minutes: int
    route_type: str
    tags: List[str]
    favorite: bool
    times_used: int
    created_at: str
    updated_at: str


# =============================================================================
# LOCATION MODELS
# =============================================================================

class SaveLocationRequest(BaseModel):
    """Lokasyon kaydetme isteği"""
    name: str = Field(..., min_length=1, max_length=200)
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    icon_type: IconType = Field(default=IconType.STAR)
    address: str = Field(default="", max_length=500)


class UpdateLocationRequest(BaseModel):
    """Lokasyon güncelleme isteği"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)
    icon_type: Optional[IconType] = None
    address: Optional[str] = Field(None, max_length=500)


class LocationItem(BaseModel):
    """Lokasyon elemanı"""
    id: str
    name: str
    lat: float
    lon: float
    icon_type: str
    address: str
    favorite: bool
    times_used: int
    created_at: str
    updated_at: str


# =============================================================================
# GEOCODING MODELS
# =============================================================================

class GeocodeRequest(BaseModel):
    """Geocoding isteği"""
    query: str = Field(..., min_length=2, max_length=500, description="Aranacak yer adı")


class ReverseGeocodeRequest(BaseModel):
    """Reverse geocoding isteği"""
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class GeocodeSuggestion(BaseModel):
    """Geocode önerisi"""
    display_name: str
    lat: float
    lon: float
    place_type: str  # "city", "town", "suburb", etc.


class GeocodeResponse(BaseModel):
    """Geocoding response"""
    status: str
    display_name: str
    lat: float
    lon: float
    address: Optional[Dict[str, str]] = None
    bbox: Optional[List[float]] = None  # [min_lon, min_lat, max_lon, max_lat]


class GeocodeSuggestResponse(BaseModel):
    """Geocode suggest response"""
    status: str
    suggestions: List[GeocodeSuggestion]


# =============================================================================
# WEATHER MODELS
# =============================================================================

class WeatherRequest(BaseModel):
    """Hava durumu isteği"""
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class WeatherForecastRequest(WeatherRequest):
    """Hava durumu forecast isteği"""
    hours: int = Field(default=24, ge=1, le=168, description="Kaç saatlik forecast (1-168)")


class WeatherAlert(BaseModel):
    """Hava durumu uyarısı"""
    level: str  # "info", "warning", "danger"
    message: str
    icon: str


class CurrentWeather(BaseModel):
    """Güncel hava durumu"""
    temperature: float  # Celsius
    humidity: int  # Percentage
    wind_speed: float  # km/h
    weather_code: int
    description: str  # "Clear sky", "Rain", etc.
    tr_description: str  # "Açık gökyüzü", "Yağmurlu", etc.
    icon: str  # "sun", "cloud", "rain", etc.
    emoji: str  # "☀️", "☁️", "🌧️"
    category: WeatherCategory
    alert: Optional[WeatherAlert] = None


class HourlyWeatherItem(BaseModel):
    """Saatlik hava durumu elemanı"""
    time: str  # ISO format
    temperature: float
    humidity: int
    precipitation: float  # mm
    weather_code: int
    description: str
    emoji: str


class WeatherResponse(BaseModel):
    """Hava durumu response"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class RouteWeatherCheckRequest(BaseModel):
    """Rota boyunca hava kontrolü isteği"""
    points: List[PointWithName] = Field(..., min_length=1)


class RouteWeatherItem(BaseModel):
    """Rota noktası hava durumu"""
    name: str
    lat: float
    lon: float
    weather: CurrentWeather
    warning: Optional[str] = None


# =============================================================================
# POI MODELS
# =============================================================================

class POISearchRequest(BaseModel):
    """POI arama isteği"""
    place_name: str = Field(..., min_length=2, max_length=200)
    category: str = Field(..., min_length=2, description="Kategori (museum, cafe, park, etc.)")


class POIItem(BaseModel):
    """POI elemanı"""
    name: str
    lat: float
    lon: float
    category: str
    website: Optional[str] = None
    wikipedia_url: Optional[str] = None
    opening_hours: Optional[str] = None


# =============================================================================
# NLP MODELS
# =============================================================================

class NLPQueryRequest(BaseModel):
    """NLP sorgusu isteği"""
    query: str = Field(..., min_length=2, max_length=1000)


class ExtractedEntity(BaseModel):
    """Çıkarılan entity"""
    type: str  # "location", "poi_type", "action", etc.
    value: str
    confidence: float


class NLPQueryResponse(BaseModel):
    """NLP sorgusu response"""
    success: bool
    entities: List[ExtractedEntity]
    interpreted_query: Optional[str] = None
    suggested_points: Optional[List[Dict[str, Any]]] = None


# =============================================================================
# TIMELINE MODELS
# =============================================================================

class TimelineEvent(BaseModel):
    """Zaman çizelgesi olayı"""
    id: str
    name: str
    start_time: str  # "HH:MM" format
    end_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    location: Optional[Coordinate] = None
    type: str  # "visit", "travel", "break"


class TimelineRequest(BaseModel):
    """Timeline oluşturma isteği"""
    points: List[PointWithName] = Field(..., min_length=2)
    start_time: str = Field(..., description="Başlangıç saati (HH:MM format)")
    visit_duration: int = Field(default=60, ge=5, description="Her noktada kalma süresi (dakika)")


class TimelineResponse(BaseModel):
    """Timeline response"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    conflicts: Optional[List[str]] = None


# =============================================================================
# PAGINATED RESPONSE
# =============================================================================

class PaginationMeta(BaseModel):
    """Pagination meta verisi"""
    total: int = Field(..., description="Toplam eleman sayısı")
    page: int = Field(..., ge=1, description="Mevcut sayfa")
    per_page: int = Field(..., ge=1, description="Sayfa başına eleman")
    pages: int = Field(..., description="Toplam sayfa sayısı")
    has_next: bool = Field(..., description="Sonraki sayfa var mı?")
    has_prev: bool = Field(..., description="Önceki sayfa var mı?")


class PaginatedResponse(BaseModel):
    """Paginated response"""
    success: bool = True
    data: List[Any]
    pagination: PaginationMeta


# =============================================================================
# HEALTH CHECK
# =============================================================================

class HealthCheckStatus(str, Enum):
    """Health check durumu"""
    HEALTHY = "ok"
    DEGRADED = "degraded"
    UNHEALTHY = "error"


class ServiceStatus(BaseModel):
    """Servis durumu"""
    status: HealthCheckStatus
    message: Optional[str] = None
    response_time_ms: Optional[float] = None


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: HealthCheckStatus
    timestamp: str
    services: Dict[str, ServiceStatus]
    uptime_seconds: float


# =============================================================================
# ERROR RESPONSE
# =============================================================================

class ErrorResponse(BaseModel):
    """Standart hata response"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# =============================================================================
# VALIDATION ERROR
# =============================================================================

class ValidationErrorDetail(BaseModel):
    """Validation detayı"""
    field: str
    message: str
    value: Optional[Any] = None


class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    success: bool = False
    error: str = "Validation error"
    errors: List[ValidationErrorDetail]
