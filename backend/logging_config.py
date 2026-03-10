"""
logging_config.py - Structured JSON Logging Configuration

Tüm uygulama loglarını JSON formatında, parse edilebilir şekilde output eder.
Production debugging için elverişli, log aggregation araçlarıyla uyumlu.

KULLANIM:
    from logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("Rota hesaplandı", extra={
        "route_id": route_id,
        "distance_km": distance,
        "user_id": user_id
    })
"""

import logging
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from contextvars import ContextVar

# =============================================================================
# REQUEST CONTEXT - Her istek için otomatik eklenecek veriler
# =============================================================================

# Request context for distributed tracing
_request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
_user_id: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
_client_ip: ContextVar[Optional[str]] = ContextVar('client_ip', default=None)


class RequestContext:
    """Request context yönetimi için helper sınıf"""

    @staticmethod
    def set_request_id(request_id: str) -> None:
        """Request ID atar (distributed tracing için)"""
        _request_id.set(request_id)

    @staticmethod
    def set_user_id(user_id: str) -> None:
        """User ID atar"""
        _user_id.set(user_id)

    @staticmethod
    def set_client_ip(ip: str) -> None:
        """Client IP atar"""
        _client_ip.set(ip)

    @staticmethod
    def get_context() -> Dict[str, Any]:
        """Mevcut context verilerini döner"""
        context = {}
        if req_id := _request_id.get():
            context['request_id'] = req_id
        if user := _user_id.get():
            context['user_id'] = user
        if ip := _client_ip.get():
            context['client_ip'] = ip
        return context

    @staticmethod
    def clear() -> None:
        """Context'i temizler"""
        _request_id.set(None)
        _user_id.set(None)
        _client_ip.set(None)


# =============================================================================
# JSON FORMATTER
# =============================================================================

class JSONFormatter(logging.Formatter):
    """
    Log mesajlarını JSON formatında output eder.

    Output formatı:
    {
        "timestamp": "2026-03-10T14:30:45.123Z",
        "level": "INFO",
        "logger": "route_engine",
        "function": "solve_tsp",
        "line": 245,
        "message": "Rota hesaplandı",
        "request_id": "req-abc123",
        "extra": {
            "route_id": "abc123",
            "distance_km": 4.5
        }
    }
    """

    def __init__(self, service_name: str = "openrouteplanner"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Log record'u JSON formatına çevirir"""

        # Base log data
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "service": self.service_name,
        }

        # Source location (opsiyonel - production'da overhead oluşturabilir)
        if record.pathname:
            log_data["file"] = Path(record.pathname).name
            log_data["line"] = record.lineno
        if record.funcName:
            log_data["function"] = record.funcName

        # Message
        log_data["message"] = record.getMessage()

        # Exception varsa stack trace ekle
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }

        # Request context (otomatik eklenir)
        context = RequestContext.get_context()
        if context:
            log_data.update(context)

        # Extra fields (kullanıcı tanımlı)
        # Pydantic validation gibi durumlarda reserved keys conflicts olmasın diye
        extra_keys = {
            k: v for k, v in record.__dict__.items()
            if k not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                'relativeCreated', 'thread', 'threadName', 'processName',
                'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info'
            }
        }
        if extra_keys:
            log_data["extra"] = extra_keys

        return json.dumps(log_data, ensure_ascii=False, default=str)


class ColoredFormatter(logging.Formatter):
    """
    Development için colored console formatter.
    JSON yerine human-readable output.
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        # Color the level name
        levelcolor = self.COLORS.get(record.levelname, '')
        record.levelname = f"{levelcolor}{record.levelname}{self.RESET}"

        # Format message
        formatted = super().format(record)

        # Add context if available
        context = RequestContext.get_context()
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            formatted = f"{formatted} | {context_str}"

        return formatted


# =============================================================================
# LOGGER FACTORY
# =============================================================================

_loggers: Dict[str, logging.Logger] = {}
_initialized = False


def _setup_logging(
    level: str = "INFO",
    json_output: bool = True,
    service_name: str = "openrouteplanner"
) -> None:
    """
    Logging sistemini yapılandırır.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: True ise JSON format, False ise colored console output
        service_name: Servis adı (log'larda eklenir)
    """
    global _initialized
    if _initialized:
        return

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    if json_output:
        # JSON formatter - Production için
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter(service_name=service_name))
    else:
        # Colored formatter - Development için
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColoredFormatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))

    root_logger.addHandler(handler)

    # External library log seviyelerini azalt
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('osmnx').setLevel(logging.INFO)

    _initialized = True


def get_logger(
    name: str,
    level: Optional[str] = None,
    json_output: bool = True,
    service_name: str = "openrouteplanner"
) -> logging.Logger:
    """
    İsimlendirilmiş logger döner.

    Args:
        name: Logger adı (genellikle __name__)
        level: Log level (opsiyonel)
        json_output: JSON output (opsiyonel)
        service_name: Servis adı (opsiyonel)

    Returns:
        Configured logger instance

    Examples:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing started")

        >>> # Extra data ile
        >>> logger.info("Route calculated", extra={
        ...     "route_id": "abc123",
        ...     "distance_km": 4.5,
        ...     "duration_minutes": 55
        ... })
    """
    if not _initialized:
        _setup_logging(level=level or "INFO", json_output=json_output, service_name=service_name)

    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)

    logger = _loggers[name]

    # Runtime level değişikliği
    if level:
        logger.setLevel(getattr(logging, level.upper()))

    return logger


# =============================================================================
# FLASK INTEGRATION
# =============================================================================

class FlaskLoggingMiddleware:
    """
    Flask request/response logging middleware.

    Kullanım:
        app = Flask(__name__)
        middleware = FlaskLoggingMiddleware(app, logger=get_logger(__name__))
        app.wsgi_app = middleware
    """

    def __init__(self, app, logger: Optional[logging.Logger] = None):
        self.app = app
        self.logger = logger or get_logger("flask")

    def __call__(self, environ, start_response):
        """
        WSGI middleware callback.
        Her request için otomatik logging yapar.
        """
        import time
        import uuid

        # Request başlangıcı
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Request bilgisini al
        path = environ.get('PATH_INFO', '/')
        method = environ.get('REQUEST_METHOD', 'GET')
        client_ip = environ.get('REMOTE_ADDR', '-')
        user_agent = environ.get('HTTP_USER_AGENT', '-')

        # Context'e request bilgisini ekle
        RequestContext.set_request_id(request_id)
        RequestContext.set_client_ip(client_ip)

        # Log request
        self.logger.info("Incoming request", extra={
            "method": method,
            "path": path,
            "user_agent": user_agent[:100] if user_agent else None
        })

        # Response'i intercept et
        def custom_start_response(status, headers, exc_info=None):
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            status_code = int(status.split()[0]) if status else 0
            level = logging.WARNING if status_code >= 400 else logging.INFO

            self.logger.log(level, "Request completed", extra={
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
                "path": path
            })

            # Slow request warning
            if duration_ms > 1000:
                self.logger.warning("Slow request detected", extra={
                    "path": path,
                    "duration_ms": round(duration_ms, 2)
                })

            # Context'i temizle
            RequestContext.clear()

            return start_response(status, headers, exc_info)

        return self.app(environ, custom_start_response)


def init_flask_logging(app, logger: Optional[logging.Logger] = None) -> None:
    """
    Flask uygulamasına logging middleware ekler.

    Args:
        app: Flask uygulaması
        logger: Logger instance (opsiyonel)

    Examples:
        from flask import Flask
        from logging_config import init_flask_logging, get_logger

        app = Flask(__name__)
        logger = get_logger(__name__)
        init_flask_logging(app, logger)
    """
    middleware = FlaskLoggingMiddleware(app, logger)
    app.wsgi_app = middleware


# =============================================================================
# LOGGING DECORATORS
# =============================================================================

def log_execution(logger: Optional[logging.Logger] = None):
    """
    Fonksiyon execution logging decorator.

    Args:
        logger: Logger instance (opsiyonel)

    Examples:
        @log_execution()
        def calculate_route(points):
            # ...
            pass

        Output:
        {"event": "function_call", "function": "calculate_route", "args": {...}}
        {"event": "function_return", "function": "calculate_route", "duration_ms": 123}
    """
    import time
    import functools

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger or get_logger(func.__module__)

            # Fonksiyon çağrısı log
            _logger.debug(f"Calling {func.__name__}", extra={
                "event": "function_call",
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            })

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                _logger.debug(f"Finished {func.__name__}", extra={
                    "event": "function_return",
                    "function": func.__name__,
                    "duration_ms": round(duration_ms, 2)
                })

                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                _logger.error(f"Error in {func.__name__}", extra={
                    "event": "function_error",
                    "function": func.__name__,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "duration_ms": round(duration_ms, 2)
                })
                raise

        return wrapper
    return decorator


def log_slow_calls(threshold_ms: float = 100.0, logger: Optional[logging.Logger] = None):
    """
    Yavaş fonksiyon çağrılarını loglayan decorator.

    Args:
        threshold_ms: Slow call eşiği (milisaniye)
        logger: Logger instance (opsiyonel)

    Examples:
        @log_slow_calls(threshold_ms=500)
        def fetch_from_api(url):
            # API call
            pass
    """
    import time
    import functools

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger or get_logger(func.__module__)
            start_time = time.time()
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            if duration_ms > threshold_ms:
                _logger.warning(f"Slow call to {func.__name__}", extra={
                    "function": func.__name__,
                    "duration_ms": round(duration_ms, 2),
                    "threshold_ms": threshold_ms
                })

            return result
        return wrapper
    return decorator


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def log_request_data(logger: logging.Logger, request_data: Dict[str, Any]) -> None:
    """
    Request verisini loglar (duyarlı - password gibi hassas verileri gizler).

    Args:
        logger: Logger instance
        request_data: Request verisi
    """
    # Hassas field'ları maskele
    SENSITIVE_FIELDS = {'password', 'token', 'api_key', 'secret', 'pin'}

    safe_data = {}
    for key, value in request_data.items():
        if key.lower() in SENSITIVE_FIELDS:
            safe_data[key] = "***REDACTED***"
        elif isinstance(value, dict):
            safe_data[key] = {k: "***" if k.lower() in SENSITIVE_FIELDS else v
                             for k, v in value.items()}
        else:
            safe_data[key] = value

    logger.info("Request data", extra={"request_data": safe_data})


# =============================================================================
# MODULE INIT - Default logger'ı başlat
# =============================================================================

# Development mode detection
import os
DEBUG_MODE = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')

# Initialize logging
_setup_logging(
    level=os.environ.get('LOG_LEVEL', 'INFO' if not DEBUG_MODE else 'DEBUG'),
    json_output=not DEBUG_MODE  # Debug mode'da colored output
)

# Export default logger
default_logger = get_logger('openrouteplanner')
