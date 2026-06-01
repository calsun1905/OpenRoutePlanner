"""
response_utils.py - Standart API Response Fonksiyonları

Tüm Flask endpoint'leri için tutarlı response formatı sağlar.
Success, error ve paginated response'ları standardize eder.

KULLANIM:
    from response_utils import success_response, error_response, paginated_response

    @app.route('/api/routes')
    def get_routes():
        routes = get_all_routes()
        return success_response(routes)

    @app.route('/api/routes/<id>')
    def get_route(id):
        route = get_route(id)
        if not route:
            return error_response("Rota bulunamadı", 404, "ROUTE_NOT_FOUND")
        return success_response(route)
"""

from typing import Any, Optional, Dict, List, Union
from flask import jsonify, Response
from datetime import datetime


# =============================================================================
# SUCCESS RESPONSES
# =============================================================================

def success_response(
    data: Any,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200
) -> Response:
    """
    Başarılı response döner.

    Args:
        data: Response verisi (dict, list, object)
        message: Opsiyonel mesaj
        meta: Opsiyonel meta veri
        status_code: HTTP status code (varsayılan 200)

    Returns:
        Flask Response object

    Examples:
        >>> success_response({"id": 123, "name": "Test"})
        {"success": True, "data": {"id": 123, "name": "Test"}}

        >>> success_response(routes, message="5 rota bulundu")
        {"success": True, "data": [...], "message": "5 rota bulundu"}
    """
    response_data = {
        "success": True,
        "data": data
    }

    if message is not None:
        response_data["message"] = message

    if meta:
        response_data["meta"] = meta

    response = jsonify(response_data)
    response.status_code = status_code
    return response


def created_response(
    data: Any,
    message: str = "Kayıt oluşturuldu",
    resource_id: Optional[str] = None
) -> Response:
    """
    201 Created response döner (yeni kayıt oluşturma).

    Args:
        data: Oluşturulan veri
        message: Başarı mesajı
        resource_id: Yeni kayıt ID'si (opsiyonel)

    Examples:
        >>> created_response(route, "Rota kaydedildi", route_id="abc123")
        {"success": True, "data": {...}, "message": "Rota kaydedildi", "resource_id": "abc123"}
    """
    response_data = {
        "success": True,
        "data": data,
        "message": message
    }

    if resource_id:
        response_data["resource_id"] = resource_id

    response = jsonify(response_data)
    response.status_code = 201
    return response


def no_content_response() -> Response:
    """
    204 No Content response döner (başarılı silme/güncelleme).

    Examples:
        >>> no_content_response()
        (Empty response, status 204)
    """
    response = jsonify({})
    response.status_code = 204
    return response


# =============================================================================
# ERROR RESPONSES
# =============================================================================

class ErrorResponse:
    """Error code'ları için sabitler"""

    # Validation Errors (400)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_COORDINATES = "INVALID_COORDINATES"
    INVALID_FORMAT = "INVALID_FORMAT"

    # Not Found Errors (404)
    NOT_FOUND = "NOT_FOUND"
    ROUTE_NOT_FOUND = "ROUTE_NOT_FOUND"
    LOCATION_NOT_FOUND = "LOCATION_NOT_FOUND"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"

    # Server Errors (500)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    GRAPH_LOAD_ERROR = "GRAPH_LOAD_ERROR"

    # Service Unavailable (503)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    WEATHER_SERVICE_DOWN = "WEATHER_SERVICE_DOWN"

    # Rate Limiting (429)
    RATE_LIMITED = "RATE_LIMITED"


def error_response(
    error: str,
    status_code: int = 400,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Response:
    """
    Hata response döner.

    Args:
        error: Hata mesajı (kullanıcıya gösterilecek)
        status_code: HTTP status code (varsayılan 400)
        error_code: Error code (client-side filtering için)
        details: Ek hata detayları

    Returns:
        Flask Response object

    Examples:
        >>> error_response("Geçersiz koordinat", 400, "INVALID_COORDINATES")
        {"success": False, "error": "Geçersiz koordinat", "error_code": "INVALID_COORDINATES"}
    """
    response_data = {
        "success": False,
        "error": error
    }

    if error_code:
        response_data["error_code"] = error_code

    if details:
        response_data["details"] = details

    # Timestamp ekle (debugging için)
    response_data["timestamp"] = datetime.utcnow().isoformat() + "Z"

    response = jsonify(response_data)
    response.status_code = status_code
    return response


def validation_error(
    field: str,
    message: str,
    value: Optional[Any] = None
) -> Response:
    """
    Validation hatası response döner.

    Args:
        field: Hatalı alan adı
        message: Hata mesajı
        value: Hatalı değer (opsiyonel)

    Examples:
        >>> validation_error("lat", "Enlem -90 ile 90 arasında olmalı", 95.0)
        {"success": False, "error": "Validation failed", "errors": [...]}
    """
    return error_response(
        error="Validation failed",
        status_code=400,
        error_code=ErrorResponse.VALIDATION_ERROR,
        details={
            "field": field,
            "message": message,
            "value": value
        }
    )


def not_found_response(
    resource_type: str = "Kaynak",
    resource_id: Optional[str] = None
) -> Response:
    """
    404 Not Found response döner.

    Args:
        resource_type: Kaynak tipi (Rota, Lokasyon, vb.)
        resource_id: Bulunamayan kaynak ID'si (opsiyonel)

    Examples:
        >>> not_found_response("Rota", "abc123")
        {"success": False, "error": "Rota bulunamadı", "error_code": "ROUTE_NOT_FOUND"}
    """
    message = f"{resource_type} bulunamadı"
    if resource_id:
        message += f" (ID: {resource_id})"

    return error_response(
        error=message,
        status_code=404,
        error_code=ErrorResponse.RESOURCE_NOT_FOUND
    )


def internal_error_response(
    error: str = "Sunucu hatası",
    details: Optional[Dict[str, Any]] = None
) -> Response:
    """
    500 Internal Server Error response döner.

    Args:
        error: Hata mesajı
        details: Ek detaylar (production'da kullanıcuya gösterilmez!)

    Examples:
        >>> internal_error_response("Veritabanı hatası")
        {"success": False, "error": "Sunucu hatası", "error_code": "INTERNAL_ERROR"}
    """
    return error_response(
        error=error,
        status_code=500,
        error_code=ErrorResponse.INTERNAL_ERROR,
        details=details
    )


def service_unavailable_response(
    service_name: str = "Servis"
) -> Response:
    """
    503 Service Unavailable response döner.

    Args:
        service_name: Kullanılamayan servis adı

    Examples:
        >>> service_unavailable_response("Hava Durumu Servisi")
        {"success": False, "error": "Hava Durumu Servisi kullanılamıyor"}
    """
    return error_response(
        error=f"{service_name} şu anda kullanılamıyor",
        status_code=503,
        error_code=ErrorResponse.SERVICE_UNAVAILABLE
    )


# =============================================================================
# PAGINATED RESPONSES
# =============================================================================

def paginated_response(
    items: List[Any],
    total: int,
    page: int = 1,
    per_page: int = 20
) -> Response:
    """
    Paginated response döner.

    Args:
        items: Mevcut sayfanın elemanları
        total: Toplam eleman sayısı
        page: Mevcut sayfa (1'den başlar)
        per_page: Sayfa başına eleman sayısı

    Returns:
        Flask Response object with pagination metadata

    Examples:
        >>> paginated_response([route1, route2], total=100, page=1, per_page=20)
        {
            "success": True,
            "data": [...],
            "pagination": {
                "total": 100,
                "count": 2,
                "page": 1,
                "per_page": 20,
                "pages": 5,
                "has_next": true,
                "has_prev": false
            }
        }
    """
    pages = (total + per_page - 1) // per_page if total > 0 else 1
    has_next = page < pages
    has_prev = page > 1

    return jsonify({
        "success": True,
        "data": items,
        "pagination": {
            "total": total,
            "count": len(items),
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }
    })


# =============================================================================
# CONDITIONAL RESPONSES
# =============================================================================

def conditional_response(
    condition: bool,
    success_data: Any,
    error_message: str = "İşlem başarısız",
    error_code: Optional[str] = None
) -> Response:
    """
    Koşula göre success veya error response döner.

    Args:
        condition: True ise success, False ise error
        success_data: Başarılı olduğunda dönecek veri
        error_message: Hata mesajı
        error_code: Error code

    Examples:
        >>> conditional_response(len(points) >= 2, routes, "En az 2 nokta gerekli")
        # Eğer points >= 2: success_response(routes)
        # Else: error_response("En az 2 nokta gerekli")
    """
    if condition:
        return success_response(success_data)
    return error_response(error_message, error_code=error_code)


# =============================================================================
# SPECIAL RESPONSES
# =============================================================================

def health_check_response(
    services: Optional[Dict[str, Dict[str, Any]]] = None,
    uptime_seconds: Optional[float] = None
) -> Response:
    """
    Health check response döner.

    Args:
        services: Servis durumları {service_name: {status, message}}
        uptime_seconds: Uptime (saniye)

    Examples:
        >>> health_check_response({
        ...     "database": {"status": "ok", "response_time_ms": 5.2},
        ...     "cache": {"status": "ok"}
        ... })
    """
    all_healthy = all(
        s.get("status") == "ok" for s in (services or {}).values()
    )

    response_data = {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": services or {}
    }

    if uptime_seconds is not None:
        response_data["uptime_seconds"] = uptime_seconds

    status_code = 200 if all_healthy else 503

    return jsonify(response_data), status_code


def options_response(
    allowed_methods: List[str],
    allow_headers: Optional[List[str]] = None
) -> Response:
    """
    OPTIONS preflight request response döner.

    Args:
        allowed_methods: İzin verilen HTTP metodları
        allow_headers: İzin verilen headers

    Examples:
        >>> options_response(["GET", "POST", "DELETE"], ["Content-Type", "Authorization"])
    """
    response = jsonify({})
    response.headers["Allow"] = ", ".join(allowed_methods)
    response.headers["Access-Control-Allow-Methods"] = ", ".join(allowed_methods)

    if allow_headers:
        response.headers["Access-Control-Allow-Headers"] = ", ".join(allow_headers)

    response.status_code = 200
    return response


# =============================================================================
# BATCH RESPONSES
# =============================================================================

def batch_response(
    results: List[Dict[str, Any]],
    total_count: Optional[int] = None,
    success_count: Optional[int] = None,
    error_count: Optional[int] = None
) -> Response:
    """
    Batch operation response döner.

    Args:
        results: Sonuç listesi
        total_count: Toplam işlem sayısı
        success_count: Başarılı işlem sayısı
        error_count: Başarısız işlem sayısı

    Examples:
        >>> batch_response([
        ...     {"index": 0, "success": True, "data": {...}},
        ...     {"index": 1, "success": False, "error": "..."}
        ... ], total_count=2, success_count=1, error_count=1)
    """
    if success_count is None:
        success_count = sum(1 for r in results if r.get("success"))
    if error_count is None:
        error_count = len(results) - success_count
    if total_count is None:
        total_count = len(results)

    return jsonify({
        "success": error_count == 0,
        "results": results,
        "summary": {
            "total": total_count,
            "success": success_count,
            "errors": error_count
        }
    })


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_pagination_params(
    default_page: int = 1,
    default_per_page: int = 20,
    max_per_page: int = 100
) -> tuple:
    """
    Flask request'ten pagination parametrelerini çeker ve valid eder.

    Args:
        default_page: Varsayılan sayfa
        default_per_page: Varsayılan sayfa başına eleman
        max_per_page: Maksimum sayfa başına eleman

    Returns:
        (page, per_page, offset) tuple

    Note:
        Bu fonksiyonu kullanmak için Flask request context içinde olmalısınız.
    """
    from flask import request

    # Query parametrelerini al
    page = request.args.get('page', default_page, type=int)
    per_page = request.args.get('per_page', request.args.get('limit', default_per_page), type=int)
    offset = request.args.get('offset', 0, type=int)

    # Validation
    if page < 1:
        page = default_page
    if per_page < 1:
        per_page = default_per_page
    if per_page > max_per_page:
        per_page = max_per_page
    if offset < 0:
        offset = 0

    # Page varsa offset hesapla
    if 'page' in request.args:
        offset = (page - 1) * per_page

    return page, per_page, offset


def extract_request_data(
    required_fields: Optional[List[str]] = None,
    optional_fields: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    Flask request'ten JSON verisini çeker ve valid eder.

    Args:
        required_fields: Zorunlu alan listesi
        optional_fields: Opsiyonel alanlar ve varsayılan değerleri

    Returns:
        (data, error) tuple
        - Eğer valid ise: (data, None)
        - Eğer hata varsa: (None, error_response)

    Examples:
        >>> data, err = extract_request_data(
        ...     required_fields=['name', 'points'],
        ...     optional_fields={'optimize': False, 'route_type': 'route_1'}
        ... )
        >>> if err:
        ...     return err
    """
    from flask import request

    # JSON parse
    try:
        data = request.get_json(silent=True)
    except Exception:
        return None, error_response("Geçersiz JSON formatı", 400, ErrorResponse.INVALID_FORMAT)

    if data is None:
        return None, error_response("Request body gerekli", 400, ErrorResponse.INVALID_INPUT)

    # Zorunlu alan kontrolü
    if required_fields:
        missing = [f for f in required_fields if f not in data or data[f] is None]
        if missing:
            return None, error_response(
                f"Eksik alanlar: {', '.join(missing)}",
                400,
                ErrorResponse.MISSING_REQUIRED_FIELD
            )

    # Opsiyonel alanları ekle
    if optional_fields:
        for field, default_value in optional_fields.items():
            if field not in data or data[field] is None:
                data[field] = default_value

    return data, None


# =============================================================================
# RESPONSE WRAPPERS (Decorator)
# =============================================================================

def handle_exceptions(
    default_error_message: str = "İşlem başarısız",
    log_errors: bool = True
):
    """
    Exception handling decorator.

    Args:
        default_error_message: Varsayılan hata mesajı
        log_errors: Hataları log'la

    Examples:
        @app.route('/api/route/calculate')
        @handle_exceptions("Rota hesaplanamadı")
        def calculate_route():
            return success_response(route)
    """
    from functools import wraps
    from logging_config import get_logger
    logger = get_logger(__name__)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ValueError as e:
                if log_errors:
                    logger.warning(f"Validation error in {func.__name__}: {e}")
                return error_response(str(e), 400, ErrorResponse.VALIDATION_ERROR)
            except KeyError as e:
                if log_errors:
                    logger.warning(f"Missing field in {func.__name__}: {e}")
                return error_response(
                    f"Eksik alan: {str(e)}",
                    400,
                    ErrorResponse.MISSING_REQUIRED_FIELD
                )
            except Exception as e:
                if log_errors:
                    logger.error(f"Error in {func.__name__}", exc_info=True)
                return internal_error_response(default_error_message)

        return wrapper
    return decorator
