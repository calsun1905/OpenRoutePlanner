"""
app.py - Flask API Sunucusu

Frontend ile Backend arasındaki köprü.
Rota optimizasyonu ve POI arama endpoint'leri sağlar.
"""
import os
import sys
import json
import time
import builtins
import uuid
import re
from datetime import datetime
from functools import partial


def _env_flag(name: str, default: bool) -> bool:
    """ENV'den bool değer okur."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    """ENV'den float değer okur."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except (TypeError, ValueError):
        return default


def _configure_live_console_output() -> None:
    """
    Console stream buffering'i azaltır ve print'i anlık flush edecek şekilde ayarlar.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(line_buffering=True, write_through=True)
            except TypeError:
                reconfigure(line_buffering=True)

    if _env_flag("ORP_LOG_FORCE_PRINT_FLUSH", True):
        if not getattr(builtins.print, "__orp_forced_flush__", False):
            forced_print = partial(builtins.print, flush=True)
            setattr(forced_print, "__orp_forced_flush__", True)
            builtins.print = forced_print


_configure_live_console_output()

from flask import Flask, request, jsonify, send_from_directory, g
# Compatibility: allow test client to pass 'query' kw -> map to 'query_string'
try:
    from flask.testing import EnvironBuilder as _EnvironBuilder
    _orig_environbuilder_init = _EnvironBuilder.__init__
    def _environbuilder_init(self, *args, **kwargs):
        if 'query' in kwargs:
            kwargs['query_string'] = kwargs.pop('query')
        return _orig_environbuilder_init(self, *args, **kwargs)
    _EnvironBuilder.__init__ = _environbuilder_init
except Exception:
    pass
from flask_cors import CORS
from flask_compress import Compress
from graph_manager import (
    get_graph,
    get_graph_for_points,
    search_pois,
    preload_popular_regions,
    is_preloaded,
    get_preloaded_graph
)
from geocoder import geocode, reverse_geocode, geocode_batch, geocode_suggest, purge_old_geocodes
from route_engine import (
    solve_tsp,
    build_full_route,
    build_alternative_routes,
    build_all_alternative_routes_batch,
    nodes_to_coords,
    calculate_route_stats,
    generate_google_maps_link,
)
from route_storage import (
    save_route,
    get_route,
    get_all_routes,
    get_routes_count,
    update_route,
    delete_route,
    toggle_favorite,
    search_routes,
    get_statistics,
)
from time_planner import (
    create_timeline,
    format_duration,
    check_time_conflicts,
    optimize_schedule,
)
from location_storage import (
    save_location,
    get_all_locations,
    get_locations_count,
    update_location,
    delete_location,
    toggle_location_favorite,
)
from storage_db import ensure_db, run_sqlite_maintenance
from nlp_engine import parse_query as regex_parse_query
try:
    from nlp_concept_resolver import resolve_poi_concept
except ImportError:
    resolve_poi_concept = None
from cache_manager import get_graph_cache, get_poi_cache

# Hava durumu servisi (OpenMeteo API entegrasyonu)
try:
    from weather_service import (
        get_current_weather,
        get_hourly_forecast,
        check_route_weather,
        get_service_status,
        clear_cache as clear_weather_cache,
        health_check as weather_health_check
    )
    WEATHER_SERVICE_AVAILABLE = True
    print("[app.py] Hava durumu servisi yüklendi")
except ImportError as e:
    WEATHER_SERVICE_AVAILABLE = False
    print(f"[app.py] Hava durumu servisi bulunamadı: {str(e)} [WARN]")

# BERT NLP Engine (opsiyonel - kurulu değilse regex fallback kullanılır)
try:
    from bert_nlp_engine import get_bert_nlp_engine, is_bert_available
    BERT_NLP_AVAILABLE = is_bert_available()
    _BERT_NLP_ERROR = None
    if BERT_NLP_AVAILABLE:
        print("[app.py] BERT NLP Engine yüklendi")
    else:
        print("[app.py] BERT NLP Engine bulunamadı, regex fallback aktif [WARN]")
except ImportError as e:
    BERT_NLP_AVAILABLE = False
    _BERT_NLP_ERROR = str(e)
    print("[app.py] BERT NLP Engine modülü bulunamadı, regex fallback aktif [WARN]")

# Frontend klasörünün yolu
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)  # Frontend'den gelen isteklere izin ver
Compress(app)  # gzip compression aktif et - %60-70 bandwidth tasarrufu

# BERT ön-yükleme (opsiyonel). ENV: ORP_BERT_PRELOAD_ON_STARTUP=1
_PRELOAD_BERT_ON_STARTUP = _env_flag("ORP_BERT_PRELOAD_ON_STARTUP", True)

def _preload_bert_async(force: bool = False) -> None:
    """Arka planda BERT NLP engine'i yükler (lazy warm-up).

    Args:
        force: True ise ORP_BERT_PRELOAD_ON_STARTUP kontrolü atlanır ve yükleme başlatılır.
    """
    if not force and not _PRELOAD_BERT_ON_STARTUP:
        return

    import threading

    def _target():
        try:
            print("[app.py] Başlatılıyor: BERT warmup (background)...")
            # import burada yapılır; hata yakalanırsa uygulama çalışmaya devam eder
            from bert_nlp_engine import get_bert_nlp_engine
            get_bert_nlp_engine()
            print("[app.py] BERT warmup tamamlandı")
        except Exception as exc:
            print(f"[app.py] BERT warmup hatası: {exc}")

    t = threading.Thread(target=_target, daemon=True)
    t.start()

# Eğer ORP_BERT_PRELOAD_ON_STARTUP set ise arka planda başlat
_preload_bert_async()

# Global değişkenler: LRU cache manager
_graph_cache_manager = get_graph_cache()
_poi_cache_manager = get_poi_cache()
_runtime_initialized = False
_graph_preload_initialized = False
_last_bert_metrics_log_ts = 0.0

# BERT donanım metrik logları:
# ORP_BERT_LOG_METRICS=1/0
# ORP_BERT_METRICS_INTERVAL_SEC=float (default 0.5s)
_BERT_METRICS_LOG_ENABLED = _env_flag("ORP_BERT_LOG_METRICS", True)
_BERT_METRICS_INTERVAL_SEC = max(0.0, _env_float("ORP_BERT_METRICS_INTERVAL_SEC", 0.5))
_PRELOAD_POPULAR_REGIONS_ON_STARTUP = _env_flag("ORP_PRELOAD_POPULAR_REGIONS_ON_STARTUP", True)
_BERT_PARSE_TRACE_LOG_ENABLED = _env_flag("ORP_BERT_PARSE_TRACE", True)

# POI resolver/caching version pinleri
_POI_DICT_VERSION = os.getenv("ORP_POI_DICT_VERSION", "dict-v1").strip() or "dict-v1"
_POI_THRESHOLD_PROFILE = os.getenv("ORP_POI_THRESHOLD_PROFILE", "default").strip() or "default"
_POI_PLAN_VERSION = os.getenv("ORP_POI_PLAN_VERSION", "phase2").strip() or "phase2"
_TRACE_RETENTION_DAYS = int(os.getenv("ORP_TRACE_RETENTION_DAYS", "14") or 14)


def _poi_version_token() -> str:
    return f"dict:{_POI_DICT_VERSION}|thr:{_POI_THRESHOLD_PROFILE}|plan:{_POI_PLAN_VERSION}"


def _should_log_bert_metrics(force: bool = False) -> bool:
    """BERT metrik loglarının hızını sınırlar."""
    global _last_bert_metrics_log_ts
    if not _BERT_METRICS_LOG_ENABLED:
        return False
    now = time.time()
    if force or (now - _last_bert_metrics_log_ts) >= _BERT_METRICS_INTERVAL_SEC:
        _last_bert_metrics_log_ts = now
        return True
    return False


def _log_bert_runtime_metrics(stage: str, bert_engine_instance=None, force: bool = False) -> None:
    """
    BERT runtime donanım kullanımını loglar.
    """
    if not _should_log_bert_metrics(force=force):
        return

    try:
        engine = bert_engine_instance
        if engine is None:
            from bert_engine import get_bert_engine
            engine = get_bert_engine()

        if engine is None or not hasattr(engine, "get_runtime_metrics"):
            print(f"[BERT METRICS] {stage} | metrik API mevcut degil")
            return

        metrics = engine.get_runtime_metrics()
        print(f"[BERT METRICS] {stage} | {json.dumps(metrics, ensure_ascii=False)}")
    except Exception as metric_exc:
        print(f"[BERT METRICS] {stage} | toplanamadi: {metric_exc}")


def _log_bert_parse_trace(trace: dict) -> None:
    """
    BERT parse trace bilgisini okunabilir satirlar halinde yazdirir.
    """
    try:
        if not trace:
            print("[BERT TRACE] Trace verisi yok")
            return

        print("[BERT TRACE] --- Parse Karar Akisi ---")
        print(
            "[BERT TRACE] Tip: %s (%.2f) -> %s (%.2f)" % (
                trace.get("query_type_initial", "unknown"),
                float(trace.get("confidence_initial", 0.0)),
                trace.get("query_type_final", "unknown"),
                float(trace.get("confidence_final", 0.0)),
            )
        )

        scores = trace.get("type_scores") or {}
        if scores:
            ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
            score_text = ", ".join(f"{k}={float(v)*100:.1f}%" for k, v in ordered)
            print(f"[BERT TRACE] Type scorelari: {score_text}")

        signals = trace.get("intent_signals") or {}
        print(
            "[BERT TRACE] Sinyaller: poi_cue=%s | multi_cue=%s | role_hints=%s"
            % (
                bool(signals.get("has_poi_cue")),
                bool(signals.get("has_multi_cue")),
                signals.get("role_hints", []),
            )
        )

        span_rows = trace.get("candidate_spans") or []
        for idx, row in enumerate(span_rows, start=1):
            best_place = row.get("best_place") or "-"
            sim_percent = row.get("best_similarity_percent")
            sim_text = "-" if sim_percent is None else f"{float(sim_percent):.2f}%"
            threshold = float(row.get("threshold", 0.0)) * 100.0
            print(
                "[BERT TRACE] Span#%s '%s' -> %s | sim=%s | esik=%.2f%% | kabul=%s | sebep=%s | kaynak=%s"
                % (
                    idx,
                    row.get("surface", ""),
                    best_place,
                    sim_text,
                    threshold,
                    bool(row.get("accepted")),
                    row.get("reason", "-"),
                    row.get("match_source", "-"),
                )
            )

        selected = trace.get("selected") or {}
        print(f"[BERT TRACE] Secilen cikti: {json.dumps(selected, ensure_ascii=False)}")
        print(f"[BERT TRACE] Parse sure: {trace.get('parse_time_ms', '-') } ms")
        print("[BERT TRACE] --------------------------")
    except Exception as trace_exc:
        print(f"[BERT TRACE] log yazdirilamadi: {trace_exc}")


def initialize_runtime() -> None:
    """
    Calisma zamani temel baslangic gorevlerini bir kez calistirir.
    """
    global _runtime_initialized
    if _runtime_initialized:
        return

    ensure_db(run_analyze=True)
    run_sqlite_maintenance(checkpoint_mode="PASSIVE")
    purge_old_geocodes(days=90)

    _runtime_initialized = True


def initialize_graph_preload() -> None:
    """
    Populer bolgelerin grafilerini bir kez on yukler.
    """
    global _graph_preload_initialized
    if _graph_preload_initialized:
        return

    preload_popular_regions()
    _graph_preload_initialized = True






