"""
app.py - Flask API Sunucusu

Frontend ile Backend arasÄ±ndaki kÃ¶prÃ¼.
Rota optimizasyonu ve POI arama endpoint'leri saÄŸlar.
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
from typing import Any


def _env_flag(name: str, default: bool) -> bool:
    """ENV'den bool deÄŸer okur."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    """ENV'den float deÄŸer okur."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except (TypeError, ValueError):
        return default


def _openrouter_system_prompt() -> str:
    """
    OpenRouter uzerinden giden tum sohbetler icin global system prompt.
    ENV ile override edilebilir: OPENROUTER_SYSTEM_PROMPT
    """
    prompt = os.getenv("OPENROUTER_SYSTEM_PROMPT", "").strip()
    if prompt:
        return prompt

    return (
        "Sen yardimci bir asistansin. "
        "Mumkun oldugunca Turkce cevap ver. "
        "Kisa, net ve dogru ol. "
        "Metni temiz UTF-8 olarak uret; bozuk karakter, emoji kodu veya mojibake uretme. "
        "Markdown kullanacaksan sade kullan. "
        "Kullanici istemedikce gereksiz uzun aciklama yapma."
    )


def _inject_system_message(messages: list[dict]) -> list[dict]:
    """
    Mesaj listesinde en basta system rolu yoksa global system prompt ekler.
    """
    if not isinstance(messages, list):
        return messages
    if messages and isinstance(messages[0], dict) and messages[0].get("role") == "system":
        return messages

    return [{"role": "system", "content": _openrouter_system_prompt()}] + messages


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _normalize_messages(messages: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for item in messages or []:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        content = repair_text(item.get("content"))
        if role not in {"system", "user", "assistant"}:
            continue
        if not content:
            continue
        normalized.append({"role": role, "content": content})
    return normalized


def _extract_latest_user_text(messages: list[dict]) -> str:
    for item in reversed(messages or []):
        if not isinstance(item, dict):
            continue
        if str(item.get("role", "")).strip().lower() != "user":
            continue
        content = repair_text(item.get("content"))
        if content:
            return content
    return ""


def _classify_llm_error(text: str) -> str:
    lowered = (text or "").lower()
    if "(429)" in lowered or "rate-limit" in lowered or "temporarily rate-limited" in lowered:
        return "limit_429"
    if "(402)" in lowered or "insufficient credits" in lowered:
        return "credit_402"
    if "(400)" in lowered and ("embedding model" in lowered or "chat/completions endpoint" in lowered):
        return "incompat_400"
    if "(404)" in lowered and "guardrail restrictions" in lowered:
        return "privacy_404"
    return "other"


def _unique_models(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in items or []:
        model = str(raw or "").strip()
        if not model or model in seen:
            continue
        seen.add(model)
        out.append(model)
    return out


def _llm_candidate_models(provider: str, preferred_model: str | None = None) -> list[str]:
    prov = str(provider or "").strip().lower()
    first = str(preferred_model or "").strip()
    if prov == "gemini":
        st = gemini_status()
    else:
        st = openrouter_status()
    defaults = [first, st.get("default_model", "")]
    fallbacks = list(st.get("fallback_models") or [])
    return _unique_models(defaults + fallbacks)


def _chat_context_from_session(session_id: str, context_limit: int = 40) -> list[dict]:
    history = list_chat_messages(session_id, limit=context_limit)
    context: list[dict] = []
    for item in history:
        role = str(item.get("role", "")).strip().lower()
        if role not in {"user", "assistant", "system"}:
            continue
        content = repair_text(item.get("content"))
        if not content:
            continue
        context.append({"role": role, "content": content})
    return context


def _configure_live_console_output() -> None:
    """
    Console stream buffering'i azaltÄ±r ve print'i anlÄ±k flush edecek ÅŸekilde ayarlar.
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

from flask import Flask, request, jsonify, send_from_directory, g, Response, stream_with_context
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
from chat_storage import (
    ensure_chat_schema,
    rebuild_db_from_sync_json,
    create_session as create_chat_session,
    list_sessions as list_chat_sessions,
    get_session as get_chat_session,
    archive_session as archive_chat_session,
    list_messages as list_chat_messages,
    save_turn as save_chat_turn,
)
from llm_health import (
    ensure_llm_health_schema,
    record_attempt as record_llm_attempt,
    list_provider_health,
    is_model_blocked,
)
from nlp_audit import (
    ensure_nlp_audit_schema,
    log_nlp_parse_audit,
    list_recent_nlp_parse_audits,
)
from text_utils import repair_text
from nlp_engine import parse_query as regex_parse_query
try:
    from nlp_concept_resolver import resolve_poi_concept
except ImportError:
    resolve_poi_concept = None
from cache_manager import get_graph_cache, get_poi_cache
try:
    from openrouter_service import (
        is_openrouter_configured,
        openrouter_status,
        openrouter_list_text_models,
        openrouter_chat_completion,
        openrouter_chat_completion_with_fallback,
        openrouter_chat_completion_stream,
        openrouter_chat_completion_stream_with_fallback,
    )
    OPENROUTER_SERVICE_AVAILABLE = True
except ImportError:
    OPENROUTER_SERVICE_AVAILABLE = False

try:
    from gemini_service import (
        is_gemini_configured,
        gemini_status,
        gemini_chat_completion,
        gemini_chat_completion_with_fallback,
        gemini_chat_completion_stream,
        gemini_chat_completion_stream_with_fallback,
    )
    GEMINI_SERVICE_AVAILABLE = True
except ImportError:
    GEMINI_SERVICE_AVAILABLE = False

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
    print("[app.py] Hava durumu servisi yÃ¼klendi")
except ImportError as e:
    WEATHER_SERVICE_AVAILABLE = False
    print(f"[app.py] Hava durumu servisi bulunamadÄ±: {str(e)} [WARN]")

# BERT NLP Engine (opsiyonel - kurulu deÄŸilse regex fallback kullanÄ±lÄ±r)
try:
    from bert_nlp_engine import get_bert_nlp_engine, is_bert_available
    BERT_NLP_AVAILABLE = is_bert_available()
    _BERT_NLP_ERROR = None
    if BERT_NLP_AVAILABLE:
        print("[app.py] BERT NLP Engine yÃ¼klendi")
    else:
        print("[app.py] BERT NLP Engine bulunamadÄ±, regex fallback aktif [WARN]")
except ImportError as e:
    BERT_NLP_AVAILABLE = False
    _BERT_NLP_ERROR = str(e)
    print("[app.py] BERT NLP Engine modÃ¼lÃ¼ bulunamadÄ±, regex fallback aktif [WARN]")

# Frontend klasÃ¶rÃ¼nÃ¼n yolu
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)  # Frontend'den gelen isteklere izin ver
Compress(app)  # gzip compression aktif et - %60-70 bandwidth tasarrufu

# BERT Ã¶n-yÃ¼kleme (opsiyonel). ENV: ORP_BERT_PRELOAD_ON_STARTUP=1
_PRELOAD_BERT_ON_STARTUP = _env_flag("ORP_BERT_PRELOAD_ON_STARTUP", True)

def _preload_bert_async(force: bool = False) -> None:
    """Arka planda BERT NLP engine'i yÃ¼kler (lazy warm-up).

    Args:
        force: True ise ORP_BERT_PRELOAD_ON_STARTUP kontrolÃ¼ atlanÄ±r ve yÃ¼kleme baÅŸlatÄ±lÄ±r.
    """
    if not force and not _PRELOAD_BERT_ON_STARTUP:
        return

    import threading

    def _target():
        try:
            print("[app.py] BaÅŸlatÄ±lÄ±yor: BERT warmup (background)...")
            # import burada yapÄ±lÄ±r; hata yakalanÄ±rsa uygulama Ã§alÄ±ÅŸmaya devam eder
            from bert_nlp_engine import get_bert_nlp_engine
            get_bert_nlp_engine()
            print("[app.py] BERT warmup tamamlandÄ±")
        except Exception as exc:
            print(f"[app.py] BERT warmup hatasÄ±: {exc}")

    t = threading.Thread(target=_target, daemon=True)
    t.start()

# EÄŸer ORP_BERT_PRELOAD_ON_STARTUP set ise arka planda baÅŸlat
_preload_bert_async()

# Global deÄŸiÅŸkenler: LRU cache manager
_graph_cache_manager = get_graph_cache()
_poi_cache_manager = get_poi_cache()
_runtime_initialized = False
_graph_preload_initialized = False
_last_bert_metrics_log_ts = 0.0

# BERT donanÄ±m metrik loglarÄ±:
# ORP_BERT_LOG_METRICS=1/0
# ORP_BERT_METRICS_INTERVAL_SEC=float (default 0.5s)
_BERT_METRICS_LOG_ENABLED = _env_flag("ORP_BERT_LOG_METRICS", True)
_BERT_METRICS_INTERVAL_SEC = max(0.0, _env_float("ORP_BERT_METRICS_INTERVAL_SEC", 0.5))
_PRELOAD_POPULAR_REGIONS_ON_STARTUP = _env_flag("ORP_PRELOAD_POPULAR_REGIONS_ON_STARTUP", True)
_BERT_PARSE_TRACE_LOG_ENABLED = _env_flag("ORP_BERT_PARSE_TRACE", False)

# POI resolver/caching version pinleri
_POI_DICT_VERSION = os.getenv("ORP_POI_DICT_VERSION", "dict-v1").strip() or "dict-v1"
_POI_THRESHOLD_PROFILE = os.getenv("ORP_POI_THRESHOLD_PROFILE", "default").strip() or "default"
_POI_PLAN_VERSION = os.getenv("ORP_POI_PLAN_VERSION", "phase2").strip() or "phase2"
_TRACE_RETENTION_DAYS = int(os.getenv("ORP_TRACE_RETENTION_DAYS", "14") or 14)


def _poi_version_token() -> str:
    return f"dict:{_POI_DICT_VERSION}|thr:{_POI_THRESHOLD_PROFILE}|plan:{_POI_PLAN_VERSION}"


def _should_log_bert_metrics(force: bool = False) -> bool:
    """BERT metrik loglarÄ±nÄ±n hÄ±zÄ±nÄ± sÄ±nÄ±rlar."""
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
    BERT runtime donanÄ±m kullanÄ±mÄ±nÄ± loglar.
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
        plan = trace.get("poi_resolution_plan") or {}
        attempts = plan.get("attempts") or []
        if attempts:
            preview = attempts[:3]
            print(f"[BERT TRACE] POI plan denemeleri (ilk {len(preview)}): {json.dumps(preview, ensure_ascii=False)}")
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
    ensure_chat_schema()
    ensure_llm_health_schema()
    ensure_nlp_audit_schema()
    rebuild_db_from_sync_json(force=False)
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



def _get_cached_graph(place_name: str):
    """
    Graf objesini LRU cache'te alÄ±r (uygulama iÃ§i).
    Ã–nce preload kontrolÃ¼ yapar, sonra LRU cache'e bakar, en son disk'ten okur.
    """
    # Ã–nce LRU cache'ten kontrol et
    graph = _graph_cache_manager.get(place_name)
    if graph is not None:
        return graph

    # Disk'ten yÃ¼kle ve cache'e ekle
    graph = get_graph(place_name)
    _graph_cache_manager.put(place_name, graph)
    return graph


def _redact_pii_text(value: str) -> str:
    """Loglarda temel PII redaction uygular (telefon/e-posta/sayÄ±sal kimlik)."""
    text = str(value or "")
    text = re.sub(r"[\w.%-]+@[\w.-]+\.[A-Za-z]{2,}", "[redacted-email]", text)
    text = re.sub(r"\b(?:\+?90\s*)?(?:\d[\s-]?){10,}\b", "[redacted-phone]", text)
    text = re.sub(r"\b\d{11}\b", "[redacted-id]", text)
    return text


def _request_trace_prefix() -> str:
    req_id = getattr(g, "request_id", "-")
    corr_id = getattr(g, "correlation_id", "-")
    return f"[req:{req_id} corr:{corr_id}]"


@app.before_request
def _ensure_runtime_initialized():
    """
    WSGI/moduler import senaryolarinda runtime gorevlerini lazy baslatir.
    Ayrica request/correlation id baglar.
    """
    req_id = (request.headers.get("X-Request-ID") or "").strip()
    corr_id = (request.headers.get("X-Correlation-ID") or "").strip()

    if not req_id:
        req_id = uuid.uuid4().hex[:12]
    if not corr_id:
        corr_id = req_id

    g.request_id = req_id
    g.correlation_id = corr_id

    initialize_runtime()


@app.after_request
def _attach_trace_headers(response):
    """Trace header'larini tum response'lara ekler."""
    try:
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        response.headers["X-Correlation-ID"] = getattr(g, "correlation_id", "")
    except Exception:
        pass

    try:
        content_type = response.headers.get("Content-Type", "")
        if (
            content_type
            and "charset=" not in content_type.lower()
            and (
                content_type.startswith("application/json")
                or content_type.startswith("application/x-ndjson")
                or content_type.startswith("text/")
            )
        ):
            response.headers["Content-Type"] = f"{content_type}; charset=utf-8"
    except Exception:
        pass
    return response


def _disable_bert_runtime(exc: Exception) -> None:
    """Runtime'da BERT kullanÄ±lamaz hale geldiÄŸinde fallback moduna geÃ§."""
    global BERT_NLP_AVAILABLE, _BERT_NLP_ERROR
    BERT_NLP_AVAILABLE = False
    _BERT_NLP_ERROR = str(exc)
    print(f"[NLP WARN] BERT devre dÄ±ÅŸÄ± bÄ±rakÄ±ldÄ±: {_BERT_NLP_ERROR}")


def _build_regex_fallback_result(query: str) -> dict:
    """Regex parser sonucunu BERT endpoint sÃ¶zleÅŸmesine uyarlar."""
    result = regex_parse_query(query)
    result["detected_places"] = result.get("detected_places", [])
    result["parse_time"] = float(result.get("parse_time", 0.0) or 0.0)
    result["engine"] = "regex-fallback"
    return result



@app.route("/api/get-route", methods=["POST"])
def api_get_route():
    """
    Koordinat listesi alÄ±r, optimize edilmiÅŸ rota dÃ¶ner.
    
    Request Body:
        {
            "points": [[lat, lon], [lat, lon], ...],
            "place": "Kadikoy, Istanbul, Turkey"  (opsiyonel, varsayÄ±lan KadÄ±kÃ¶y),
            "route_type": "route_1" | "route_2" | "route_3"  (opsiyonel, varsayÄ±lan route_1)
        }
    
    Response:
        {
            "optimized_order": [0, 2, 1, ...],
            "route_coords": [[lat, lon], ...],
            "total_distance_km": 4.5,
            "estimated_walk_minutes": 55,
            "google_maps_link": "https://..."
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data or "points" not in data:
            return jsonify({"error": "GeÃ§ersiz istek: 'points' alanÄ± gerekli."}), 400

        points = data["points"]
        optimize = data.get("optimize", False)  # VarsayÄ±lan: sÄ±ralÄ± baÄŸla
        route_type = data.get("route_type", "route_1")  # route_1, route_2, route_3

        print(f"[API] Get-route: {len(points)} nokta, optimize={optimize}, route_type={route_type}")

        # Eski tip compatibility
        if route_type == "shortest": route_type = "route_1"
        elif route_type == "fastest": route_type = "route_2"
        elif route_type == "balanced": route_type = "route_3"

        # Validasyon
        if not isinstance(points, list) or len(points) < 2:
            return jsonify({"error": "En az 2 nokta gereklidir."}), 400

        for i, p in enumerate(points):
            if not isinstance(p, list) or len(p) != 2:
                return jsonify({"error": f"Nokta {i} geÃ§ersiz format. [lat, lon] olmalÄ±."}), 400
            try:
                float(p[0])
                float(p[1])
            except (ValueError, TypeError):
                return jsonify({"error": f"Nokta {i} geÃ§ersiz koordinat."}), 400

        # 1) SeÃ§ilen noktalarÄ± kapsayan grafÄ± al (otomatik bÃ¶lge algÄ±lama)
        point_tuples = [(p[0], p[1]) for p in points]
        # print(f"[API] Noktalar iÃ§in graf alÄ±nÄ±yor: {len(points)} nokta"))
        G = get_graph_for_points(point_tuples)

        # 2) SÄ±ralama: TSP optimizasyonu veya kullanÄ±cÄ± sÄ±rasÄ±
        if optimize and len(point_tuples) > 2:
            # print(f"[API] TSP Ã§Ã¶zÃ¼lÃ¼yor: {len(points)} nokta"))
            optimized_order = solve_tsp(G, point_tuples)
        else:
            # print(f"[API] SÄ±ralÄ± rota: {len(points)} nokta"))
            optimized_order = list(range(len(point_tuples)))

        # 3) SÄ±ralanmÄ±ÅŸ noktalar
        ordered_points = [point_tuples[i] for i in optimized_order]

        # 4) Tam rotayÄ± oluÅŸtur (alternatif rota tipi ile)
        # route_type "route_1"|"route_2"|"route_3" string -> route_index 0|1|2 int (build_alternative_routes int bekliyor)
        route_index = {"route_1": 0, "route_2": 1, "route_3": 2}.get(route_type, 0)
        route_nodes = build_alternative_routes(G, ordered_points, route_index)

        if not route_nodes:
            return jsonify({"error": "Rota hesaplanamadÄ±. Noktalar harita alanÄ± dÄ±ÅŸÄ±nda olabilir."}), 400

        # 5) Koordinatlara Ã§evir
        route_coords = nodes_to_coords(G, route_nodes)

        # 6) Ä°statistikler
        stats = calculate_route_stats(G, route_nodes)

        # 7) Google Maps linki
        maps_link = generate_google_maps_link(ordered_points)

        response = {
            "optimized_order": optimized_order,
            "route_coords": route_coords,
            "total_distance_km": stats["total_distance_km"],
            "estimated_walk_minutes": stats["estimated_walk_minutes"],
            "google_maps_link": maps_link,
            "route_type": route_type,
        }

        print(f"[API] Rota tamamlandi: {stats['total_distance_km']}km, {stats['estimated_walk_minutes']}dk")
        return jsonify(response)

    except Exception as e:
        print(f"[API] Hata: {e}")
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/get-route-steps", methods=["POST"])
def api_get_route_steps():
    """
    Verilen noktalar iÃ§in adÄ±m adÄ±m yÃ¶nlendirme (basitleÅŸtirilmiÅŸ).

    Request Body:
        { "points": [[lat, lon], ...], "optimize": true/false, "route_type": "route_1" }

    Response:
        { "steps": [{"instruction": str, "distance_m": int, "duration_min": int}, ...] }
    """
    try:
        data = request.get_json(silent=True)
        if not data or 'points' not in data:
            return jsonify({"error": "'points' alanÄ± gerekli."}), 400

        points = data['points']
        optimize = bool(data.get('optimize', False))
        route_type = data.get('route_type', 'route_1')

        if not isinstance(points, list) or len(points) < 2:
            return jsonify({"error": "En az 2 nokta gerekli."}), 400

        point_tuples = [(p[0], p[1]) for p in points]
        G = get_graph_for_points(point_tuples)

        if optimize and len(point_tuples) > 2:
            optimized_order = solve_tsp(G, point_tuples)
        else:
            optimized_order = list(range(len(point_tuples)))

        ordered_points = [point_tuples[i] for i in optimized_order]
        route_index = {"route_1": 0, "route_2": 1, "route_3": 2}.get(route_type, 0)
        route_nodes = build_alternative_routes(G, ordered_points, route_index)

        if not route_nodes:
            return jsonify({"error": "Rota hesaplanamadÄ±."}), 400

        # Basit step extractor: kenar Ã¼zerindeki 'name' veya 'ref' attribute'una gÃ¶re adÄ±m oluÅŸtur
        def build_turn_by_turn_steps(G, nodes):
            steps = []
            if not nodes or len(nodes) < 2:
                return steps

            current_name = None
            current_dist = 0.0
            for i in range(len(nodes)-1):
                u = nodes[i]
                v = nodes[i+1]
                edge_data = G.get_edge_data(u, v) or {}
                best = None
                if edge_data:
                    try:
                        best = min(edge_data.values(), key=lambda d: d.get('length', float('inf')))
                    except Exception:
                        best = list(edge_data.values())[0]

                length = 0.0
                name = None
                if best:
                    length = float(best.get('length', 0) or 0)
                    name = best.get('name') or best.get('ref') or best.get('highway')

                if not name:
                    name = 'yol'

                if current_name is None:
                    current_name = name
                    current_dist = length
                elif name == current_name:
                    current_dist += length
                else:
                    # flush
                    minutes = round((current_dist/1000) / float(ROUTE_CONFIG.get('WALK_SPEED_KMH', 5.0)) * 60)
                    instr = f"{int(round(current_dist))} metre boyunca {current_name} Ã¼zerinde ilerleyin."
                    steps.append({"instruction": instr, "distance_m": int(round(current_dist)), "duration_min": minutes})
                    current_name = name
                    current_dist = length

            # flush last
            if current_name is not None:
                minutes = round((current_dist/1000) / float(ROUTE_CONFIG.get('WALK_SPEED_KMH', 5.0)) * 60)
                instr = f"{int(round(current_dist))} metre boyunca {current_name} Ã¼zerinde ilerleyin."
                steps.append({"instruction": instr, "distance_m": int(round(current_dist)), "duration_min": minutes})

            return steps

        steps = build_turn_by_turn_steps(G, route_nodes)
        return jsonify({"steps": steps, "route_coords": nodes_to_coords(G, route_nodes)})

    except Exception as e:
        print(f"[API] get-route-steps hata: {e}")
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500



@app.route("/api/get-alternative-routes", methods=["POST"])
def api_get_alternative_routes():
    """
    AynÄ± noktalar iÃ§in 3 farklÄ± alternatif rota dÃ¶ner.

    Basit sistem:
    - 3 rota: "Rota 1", "Rota 2", "Rota 3"
    - Hepsi kÄ±sa rotaya yakÄ±n mesafede
    - Geometrik olarak farklÄ± sokaklardan geÃ§er

    Request Body:
        {
            "points": [[lat, lon], [lat, lon], ...],
            "optimize": true/false
        }

    Response:
        {
            "alternatives": [
                {
                    "type": "route_1",
                    "name": "Rota 1",
                    "icon": "@",
                    "route_coords": [[lat, lon], ...],
                    "distance_km": 4.5,
                    "duration_minutes": 55,
                    "description": "4.5 km"
                },
                {
                    "type": "route_2",
                    "name": "Rota 2",
                    "icon": "@",
                    ...
                },
                {
                    "type": "route_3",
                    "name": "Rota 3",
                    "icon": "@",
                    ...
                }
            ]
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data or "points" not in data:
            return jsonify({"error": "GeÃ§ersiz istek: 'points' alanÄ± gerekli."}), 400

        points = data["points"]
        optimize = data.get("optimize", False)

        print(f"[API] Get-alternative-routes: {len(points)} nokta, optimize={optimize}")

        # Validasyon
        if not isinstance(points, list) or len(points) < 2:
            return jsonify({"error": "En az 2 nokta gereklidir."}), 400

        point_tuples = [(p[0], p[1]) for p in points]

        G = get_graph_for_points(point_tuples)

        # TSP optimizasyonu
        if optimize and len(point_tuples) > 2:
            optimized_order = solve_tsp(G, point_tuples)
        else:
            optimized_order = list(range(len(point_tuples)))

        ordered_points = [point_tuples[i] for i in optimized_order]

        # PERFORMANS: Segment alternatifleri tek seferde hesaplanÄ±r (3x yerine 1x)
        try:
            batch_results = build_all_alternative_routes_batch(G, ordered_points)
        except Exception as e:
            print(f"[API] Alternatif rota batch hatasÄ±: {e}")
            batch_results = []

        alternatives = []
        for alt in batch_results:
            route_coords = nodes_to_coords(G, alt["nodes"])
            alternatives.append({
                "type": alt["type"],
                "name": alt["name"],
                "icon": alt["icon"],
                "route_coords": route_coords,
                "distance_km": alt["distance_km"],
                "duration_minutes": alt["duration_minutes"],
                "description": alt["description"],
                "google_maps_link": generate_google_maps_link(ordered_points)
            })

        if not alternatives:
            return jsonify({"error": "HiÃ§bir alternatif rota hesaplanamadÄ±."}), 400

        # AynÄ± rotalarÄ± filtrele: Birebir aynÄ± koordinat listesi = tek rota
        def _coords_equal(a, b):
            if len(a) != len(b):
                return False
            for i in range(len(a)):
                if abs(a[i][0] - b[i][0]) > 1e-6 or abs(a[i][1] - b[i][1]) > 1e-6:
                    return False
            return True

        unique = []
        for alt in alternatives:
            if not any(_coords_equal(alt["route_coords"], u["route_coords"]) for u in unique):
                unique.append(alt)

        print(f"[API] {len(unique)} alternatif rota")
        return jsonify({"alternatives": unique})

    except Exception as e:
        print(f"[API] Hata: {e}")
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/search-pois", methods=["POST"])
def api_search_pois():
    """
    Belirtilen bÃ¶lgede POI arar.
    
    Request Body:
        {
            "place": "Kadikoy, Istanbul, Turkey",
            "category": "museum"
        }
    
    Response:
        {
            "pois": [
                {"name": "...", "lat": ..., "lon": ..., "category": "museum"},
                ...
            ]
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data or "category" not in data:
            return jsonify({"error": "'category' alanÄ± gerekli."}), 400

        place = data.get("place", "Kadikoy, Istanbul, Turkey")
        raw_category = data["category"]
        search_mode = (data.get("search_mode", "auto") or "auto").strip().lower()
        if search_mode not in {"auto", "place_boundary_only"}:
            search_mode = "auto"
        force_refresh_raw = data.get("force_refresh", False)
        if isinstance(force_refresh_raw, bool):
            force_refresh = force_refresh_raw
        elif isinstance(force_refresh_raw, str):
            force_refresh = force_refresh_raw.strip().lower() in {"1", "true", "yes", "on"}
        else:
            force_refresh = bool(force_refresh_raw)

        # GÃ¼venlik aÄŸÄ±: il/ilÃ§e seviyesinde idari yer adlarÄ±nda
        # fallback yerine doÄŸrudan place-boundary sorgusu zorunlu olsun.
        if search_mode == "auto" and isinstance(place, str):
            place_parts = [p.strip() for p in place.split(",") if p.strip()]
            place_tail = place_parts[-1].lower() if place_parts else ""
            is_city_level = (
                len(place_parts) == 1
                or (len(place_parts) == 2 and place_tail in {"turkey", "turkiye", "tÃ¼rkiye"})
            )
            is_district_level = (
                len(place_parts) == 3 and place_tail in {"turkey", "turkiye", "tÃ¼rkiye"}
            )
            if is_city_level or is_district_level:
                search_mode = "place_boundary_only"
                print(f"{_request_trace_prefix()} [API] Search-pois mode forced: place_boundary_only (admin-level place)")

        resolved_category = raw_category
        category_resolution = {
            "input": raw_category,
            "resolved": raw_category,
            "source": "raw",
            "confidence": 0.0,
            "status": "unknown",
        }

        # Faz-1: POI kategori canonicalization (morph+dict)
        if resolve_poi_concept is not None and isinstance(raw_category, str):
            resolved = resolve_poi_concept(raw_category)
            if resolved and getattr(resolved, "concept", None):
                resolved_category = resolved.concept
                category_resolution = {
                    "input": raw_category,
                    "resolved": resolved.concept,
                    "source": getattr(resolved, "source", "morph+dict"),
                    "confidence": float(getattr(resolved, "confidence", 0.0) or 0.0),
                    "status": getattr(resolved, "status", "success"),
                }

        print(
            f"{_request_trace_prefix()} [API] Search-pois: "
            f"place={_redact_pii_text(place)}, "
            f"kategori={_redact_pii_text(raw_category)}, "
            f"resolved={_redact_pii_text(resolved_category)}, "
            f"mode={search_mode}, "
            f"force={force_refresh}"
        )

        from osm_poi_dictionary import POI_MAPPING

        # Validasyon: ASCII serbest, TÃ¼rkÃ§e sÃ¶zlÃ¼kten canonicalize edilen ifadeler de serbest.
        if isinstance(resolved_category, str) and resolved_category.lower() not in POI_MAPPING and not resolved_category.isascii():
            pass

        cache_version_token = _poi_version_token()

        search_result = search_pois(
            place,
            resolved_category,
            search_mode=search_mode,
            force_refresh=force_refresh,
            return_meta=True,
        )
        if isinstance(search_result, tuple) and len(search_result) == 2:
            pois, poi_cache = search_result
        else:
            pois = search_result if isinstance(search_result, list) else []
            poi_cache = {
                "status": "legacy_no_meta",
                "source": "unknown",
                "last_updated": None,
                "age_seconds": None,
                "force_refresh": force_refresh,
            }

        print(f"[API] {len(pois)} POI bulundu")
        return jsonify({
            "pois": pois,
            "category": resolved_category,
            "search_mode": search_mode,
            "force_refresh": force_refresh,
            "poi_cache": poi_cache,
            "category_resolution": category_resolution,
            "version_profile": {
                "dict_version": _POI_DICT_VERSION,
                "threshold_profile": _POI_THRESHOLD_PROFILE,
                "plan_version": _POI_PLAN_VERSION,
                "cache_token": cache_version_token,
            },
        })

    except Exception as e:
        # print(f"[API] POI arama hatasÄ±: {e}"))
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """Sunucu saÄŸlÄ±k kontrolÃ¼."""
    return jsonify({"status": "ok", "message": "OpenTrip API Ã§alÄ±ÅŸÄ±yor!"})


@app.route("/api/geocode/suggest", methods=["GET"])
def api_geocode_suggest():
    """
    Yazarken Ã¶neri iÃ§in: KÄ±smi yer ismi -> coklu sonuc doner (autocomplete).

    Query: ?q=KadÄ±kÃ¶y&limit=6
    """
    try:
        q = request.args.get("q", "").strip()
        limit = min(int(request.args.get("limit", 6)), 10)
        result = geocode_suggest(q, limit=limit)
        return jsonify(result)
    except Exception as e:
        print(f"[API] Geocode suggest hatasÄ±: {e}")
        return jsonify({"status": "success", "suggestions": []})


@app.route("/api/geocode/forward", methods=["GET"])
def api_geocode_forward_get():
    """Compatibility GET endpoint for forward geocoding (query param: address)

    Returns the same shape as POST /api/geocode but accepts GET for tests.
    """
    try:
        address = request.args.get("address") or request.args.get("q")
        if not address:
            return jsonify({"error": "'address' parametre gerekli."}), 400
        result = geocode(address)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/geocode/reverse", methods=["GET"])
def api_geocode_reverse_get():
    """Compatibility GET endpoint for reverse geocoding (query params: lat, lon)"""
    try:
        lat = request.args.get("lat")
        lon = request.args.get("lon")
        if lat is None or lon is None:
            return jsonify({"error": "'lat' ve 'lon' parametreleri gerekli."}), 400
        result = reverse_geocode(float(lat), float(lon))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/geocode", methods=["POST"])
def api_geocode():
    """
    Yer ismini koordinata Ã§evirir.

    Request Body:
        {
            "place": "KadÄ±kÃ¶y ParkÄ±, Ä°stanbul"
        }

    Response:
        {
            "status": "success",
            "lat": 40.990,
            "lon": 29.029,
            "display_name": "KadÄ±kÃ¶y ParkÄ±, Ä°stanbul, TÃ¼rkiye",
            "cached": false
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data or "place" not in data:
            return jsonify({"error": "'place' alanÄ± gerekli."}), 400

        place_name = data["place"]

        print(f"[API] Geocode: {place_name}")

        result = geocode(place_name)

        if result["status"] == "error":
            print(f"[API] Geocode HATA: {result['message']}")
            return jsonify(result), 404

        print(f"[API] Geocode Sonuc: ({result['lat']:.6f}, {result['lon']:.6f})")
        return jsonify(result)

    except Exception as e:
        print(f"[API] Geocode hatasÄ±: {e}")
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/reverse-geocode", methods=["POST"])
def api_reverse_geocode():
    """
    KoordinatÄ± yer ismine Ã§evirir.

    Request Body:
        {
            "lat": 40.990,
            "lon": 29.029
        }

    Response:
        {
            "status": "success",
            "display_name": "KadÄ±kÃ¶y, Ä°stanbul, TÃ¼rkiye",
            "address": "{...}",
            "cached": false
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data or "lat" not in data or "lon" not in data:
            return jsonify({"error": "'lat' ve 'lon' alanlarÄ± gerekli."}), 400

        lat = data["lat"]
        lon = data["lon"]
        result = reverse_geocode(lat, lon)

        if result["status"] == "error":
            return jsonify(result), 404

        return jsonify(result)

    except Exception as e:
        print(f"[API] Reverse geocode hatasÄ±: {e}")
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/geocode/batch", methods=["POST"])
def api_geocode_batch():
    """
    Toplu geocoding iÅŸlemi.

    Request Body:
        {
            "places": ["KadÄ±kÃ¶y", "BeÅŸiktaÅŸ", "Taksim"]
        }

    Response:
        {
            "results": [
                {"status": "success", "lat": 40.99, "lon": 29.03, ...},
                {"status": "success", "lat": 41.04, "lon": 29.00, ...},
                ...
            ]
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data or "places" not in data:
            return jsonify({"error": "'places' alanÄ± gerekli (liste)."}), 400

        places = data["places"]

        if not isinstance(places, list):
            return jsonify({"error": "'places' bir liste olmalÄ±."}), 400

        if len(places) > 10:
            return jsonify({"error": "En fazla 10 yer adÄ± aynÄ± anda iÅŸlenebilir."}), 400

        results = geocode_batch(places)
        return jsonify({"results": results})

    except Exception as e:
        print(f"[API] Batch geocode hatasÄ±: {e}")
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/")
def serve_frontend():
    """Ana sayfa - Frontend'i sun."""
    response = send_from_directory(FRONTEND_DIR, "index.html")
    # HTML dosyasÄ± iÃ§in cache header (kÄ±sa sÃ¼re)
    response.headers["Cache-Control"] = "public, max-age=300"  # 5 dakika
    return response


@app.route("/<path:filepath>")
def serve_static_files(filepath):
    """
    Statik dosyalarÄ± sun (CSS, JS, gÃ¶rseller vb.).
    Cache headers ile daha hÄ±zlÄ± yÃ¼klenme.
    """
    response = send_from_directory(FRONTEND_DIR, filepath)

    # Dosya uzantÄ±sÄ±na gÃ¶re cache sÃ¼resi belirle
    if filepath.endswith((".css", ".js")):
        # CSS/JS dosyalarÄ± 1 saat cache
        response.headers["Cache-Control"] = "public, max-age=3600"
    elif filepath.endswith((".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp")):
        # GÃ¶rsel dosyalar 1 gÃ¼n cache
        response.headers["Cache-Control"] = "public, max-age=86400"
    else:
        # DiÄŸer dosyalar 5 dakika cache
        response.headers["Cache-Control"] = "public, max-age=300"

    return response


# =============================================================================
# ROTA KAYDETME VE YÃœKLEME API'LERÄ°
# =============================================================================

@app.route("/api/routes/save", methods=["POST"])
def api_save_route():
    """
    RotayÄ± kaydeder.
    
    Request Body:
        {
            "name": "KadÄ±kÃ¶y Turu",
            "description": "KadÄ±kÃ¶y'de gezilecek yerler",
            "points": [[lat, lon], ...],
            "route_coords": [[lat, lon], ...],
            "distance_km": 4.5,
            "duration_minutes": 55,
            "route_type": "shortest",
            "tags": ["tarihi", "kÃ¼ltÃ¼rel"]
        }
    
    Response:
        {
            "status": "success",
            "route": {...},
            "message": "Rota kaydedildi"
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "GeÃ§ersiz veya eksik JSON gÃ¶vdesi."}), 400
        
        # Zorunlu alanlar
        required_fields = ["name", "points", "route_coords", "distance_km", "duration_minutes"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"'{field}' alanÄ± gerekli."}), 400
        
        # RotayÄ± kaydet
        route = save_route(
            name=data["name"],
            points=data["points"],
            route_coords=data["route_coords"],
            distance_km=data["distance_km"],
            duration_minutes=data["duration_minutes"],
            route_type=data.get("route_type", "route_1"),
            description=data.get("description", ""),
            tags=data.get("tags", [])
        )
        
        return jsonify({
            "status": "success",
            "route": route,
            "message": f"'{route['name']}' rotasÄ± kaydedildi!"
        })
    
    except Exception as e:
        print(f"[API] Rota kaydetme hatasÄ±: {e}")
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/routes", methods=["GET"])
def api_get_routes():
    """
    TÃ¼m kaydedilmiÅŸ rotalarÄ± getirir (Pagination destekli).

    Query Parameters:
        sort_by: created_at, name, distance_km, times_used, favorite
        limit: Maksimum rota sayÄ±sÄ± (varsayÄ±lan 20)
        offset: BaÅŸlangÄ±Ã§ index'i (varsayÄ±lan 0)
        page: Sayfa numarasÄ± (limit ile hesaplanÄ±r, offset alternatifi)

    Response:
        {
            "routes": [...],
            "count": 5,
            "total": 150,
            "page": 1,
            "pages": 8
        }
    """
    try:
        sort_by = request.args.get("sort_by", "created_at")

        # Pagination parametreleri
        limit = request.args.get("limit", 20, type=int)
        offset = request.args.get("offset", 0, type=int)
        page = request.args.get("page", 1, type=int)

        # Page parametresini offset'e Ã§evir
        if page > 1:
            offset = (page - 1) * limit

        # Toplam sayÄ±yÄ± al
        total = get_routes_count()

        # RotalarÄ± getir
        routes = get_all_routes(sort_by=sort_by, limit=limit, offset=offset)

        # Sayfa bilgisi
        pages = (total + limit - 1) // limit if total > 0 else 1
        current_page = (offset // limit) + 1

        return jsonify({
            "routes": routes,
            "count": len(routes),
            "total": total,
            "page": current_page,
            "pages": pages,
            "limit": limit,
            "offset": offset
        })
    
    except Exception as e:
        # print(f"[API] Rota listeleme hatasÄ±: {e}"))
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/routes/<route_id>", methods=["GET"])
def api_get_route_by_id(route_id):
    """
    Belirli bir rotayÄ± getirir.
    
    Response:
        {
            "route": {...}
        }
    """
    try:
        route = get_route(route_id)
        
        if not route:
            return jsonify({"error": "Rota bulunamadÄ±"}), 404
        
        return jsonify({"route": route})
    
    except Exception as e:
        # print(f"[API] Rota getirme hatasÄ±: {e}"))
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/routes/<route_id>", methods=["PUT"])
def api_update_route(route_id):
    """
    RotayÄ± gÃ¼nceller.
    
    Request Body:
        {
            "name": "Yeni Ä°sim",
            "description": "Yeni aÃ§Ä±klama",
            "tags": ["yeni", "etiketler"]
        }
    
    Response:
        {
            "status": "success",
            "route": {...}
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "GeÃ§ersiz veya eksik JSON gÃ¶vdesi."}), 400
        
        route = update_route(route_id, data)
        
        if not route:
            return jsonify({"error": "Rota bulunamadÄ±"}), 404
        
        return jsonify({
            "status": "success",
            "route": route,
            "message": "Rota gÃ¼ncellendi"
        })
    
    except Exception as e:
        print(f"[API] Rota gÃ¼ncelleme hatasÄ±: {e}")
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/routes/<route_id>", methods=["DELETE"])
def api_delete_route(route_id):
    """
    RotayÄ± siler.
    
    Response:
        {
            "status": "success",
            "message": "Rota silindi"
        }
    """
    try:
        success = delete_route(route_id)
        
        if not success:
            return jsonify({"error": "Rota bulunamadÄ±"}), 404
        
        return jsonify({
            "status": "success",
            "message": "Rota silindi"
        })
    
    except Exception as e:
        # print(f"[API] Rota silme hatasÄ±: {e}"))
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/routes/<route_id>/favorite", methods=["POST"])
def api_toggle_favorite(route_id):
    """
    RotayÄ± favorilere ekler/Ã§Ä±karÄ±r.
    
    Response:
        {
            "status": "success",
            "route": {...},
            "is_favorite": true
        }
    """
    try:
        route = toggle_favorite(route_id)
        
        if not route:
            return jsonify({"error": "Rota bulunamadÄ±"}), 404
        
        return jsonify({
            "status": "success",
            "route": route,
            "is_favorite": route.get("favorite", False)
        })
    
    except Exception as e:
        # print(f"[API] Favori iÅŸlemi hatasÄ±: {e}"))
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/routes/search", methods=["GET"])
def api_search_routes():
    """
    Rota arama.
    
    Query Parameters:
        q: Arama sorgusu
    
    Response:
        {
            "routes": [...],
            "count": 3
        }
    """
    try:
        query = request.args.get("q", "")
        
        if not query:
            return jsonify({"error": "Arama sorgusu gerekli"}), 400
        
        routes = search_routes(query)
        
        return jsonify({
            "routes": routes,
            "count": len(routes)
        })
    
    except Exception as e:
        print(f"[API] Rota arama hatasÄ±: {e}")
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/routes/statistics", methods=["GET"])
def api_route_statistics():
    """
    Rota istatistikleri.
    
    Response:
        {
            "total_routes": 10,
            "total_distance_km": 45.2,
            "total_duration_minutes": 550,
            "favorite_count": 3,
            "most_used_route": {...}
        }
    """
    try:
        stats = get_statistics()
        return jsonify(stats)
    
    except Exception as e:
        # print(f"[API] Ä°statistik hatasÄ±: {e}"))
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


# =============================================================================
# ZAMAN PLANLAMA API'LERÄ°
# =============================================================================

@app.route("/api/timeline/create", methods=["POST"])
def api_create_timeline():
    """
    Rota iÃ§in zaman Ã§izelgesi oluÅŸturur.
    
    Request Body:
        {
            "points": [
                {"name": "KadÄ±kÃ¶y", "lat": 40.99, "lon": 29.03},
                {"name": "Moda", "lat": 40.98, "lon": 29.04}
            ],
            "segment_distances": [1.2, 0.8],  # km cinsinden
            "start_time": "09:00",
            "visit_duration": 30,  # dakika (varsayÄ±lan)
            "transport_mode": "walking",
            "custom_durations": {0: 45, 1: 60}  # Ãƒâ€“zel sÃ¼reler (opsiyonel)
        }
    
    Response:
        {
            "start_time": "09:00",
            "end_time": "14:30",
            "total_duration_minutes": 330,
            "schedule": [...]
        }
    """
    try:
        data = request.get_json(silent=True)
        
        # Zorunlu alanlar
        if not data or "points" not in data:
            return jsonify({"error": "'points' alanÄ± gerekli"}), 400
        
        points = data["points"]
        segment_distances = data.get("segment_distances", [])
        start_time = data.get("start_time", "09:00")
        visit_duration = data.get("visit_duration", 30)
        transport_mode = data.get("transport_mode", "walking")
        custom_durations = data.get("custom_durations", {})
        include_weather = bool(data.get("include_weather", False) and WEATHER_SERVICE_AVAILABLE)
        
        # String key'leri int'e Ã§evir
        if custom_durations:
            custom_durations = {int(k): v for k, v in custom_durations.items()}
        
        timeline = create_timeline(
            points=points,
            segment_distances=segment_distances,
            start_time=start_time,
            visit_duration=visit_duration,
            transport_mode=transport_mode,
            custom_durations=custom_durations,
            include_weather=include_weather
        )
        
        if "error" in timeline:
            return jsonify(timeline), 400

        if include_weather:
            timeline["weather_included"] = True

        return jsonify(timeline)

    except Exception as e:
        # print(f"[API] Timeline oluÅŸturma hatasÄ±: {e}"))
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/timeline/check-conflicts", methods=["POST"])
def api_check_conflicts():
    """
    Zaman Ã§izelgesinde Ã§akÄ±ÅŸmalarÄ± kontrol eder.
    
    Request Body:
        {
            "schedule": [...],
            "opening_hours": {
                0: {"open": "09:00", "close": "18:00"},
                1: {"open": "10:00", "close": "20:00"}
            }
        }
    
    Response:
        {
            "warnings": [
                {
                    "point_index": 2,
                    "warning": "Bu saat kapalÄ± olabilir",
                    "arrival_time": "20:00"
                }
            ]
        }
    """
    try:
        data = request.get_json(silent=True)
        
        if not data or "schedule" not in data:
            return jsonify({"error": "'schedule' alanÄ± gerekli"}), 400
        
        schedule = data["schedule"]
        opening_hours = data.get("opening_hours", {})
        
        # String key'leri int'e Ã§evir
        if opening_hours:
            opening_hours = {int(k): v for k, v in opening_hours.items()}
        
        warnings = check_time_conflicts(schedule, opening_hours)
        
        return jsonify({"warnings": warnings})
    
    except Exception as e:
        print(f"[API] Ã‡akÄ±ÅŸma kontrolÃ¼ hatasÄ±: {e}")
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/timeline/optimize", methods=["POST"])
def api_optimize_timeline():
    """
    Zaman Ã§izelgesini optimize eder ve Ã¶neriler sunar.
    
    Request Body:
        {
            "schedule": [...],
            "max_duration_minutes": 360,  # 6 saat
            "preferred_end_time": "18:00"
        }
    
    Response:
        {
            "suggestions": [
                {
                    "type": "duration_exceeded",
                    "message": "Toplam sÃ¼re 1s 30dk fazla",
                    "suggestion": "Ziyaret sÃ¼relerini azaltÄ±n"
                }
            ]
        }
    """
    try:
        data = request.get_json(silent=True)
        
        if not data or "schedule" not in data:
            return jsonify({"error": "'schedule' alanÄ± gerekli"}), 400
        
        schedule = data["schedule"]
        max_duration = data.get("max_duration_minutes")
        preferred_end = data.get("preferred_end_time")
        
        result = optimize_schedule(schedule, max_duration, preferred_end)
        
        return jsonify(result)
    
    except Exception as e:
        # print(f"[API] Optimizasyon hatasÄ±: {e}"))
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


# =============================================================================
# KULLANICI LOKASYON API'LERÄ°
# =============================================================================

@app.route("/api/locations", methods=["GET"])
def api_get_locations():
    """
    KaydedilmiÅŸ tÃ¼m lokasyonlarÄ± getirir.
    Pagination desteÄŸi eklenmiÅŸtir (limit, offset, page).
    """
    try:
        sort_by = request.args.get("sort_by", "created_at")
        limit = request.args.get("limit", 20, type=int)
        offset = request.args.get("offset", 0, type=int)
        page = request.args.get("page", 1, type=int)

        # Page parametresi varsa offset'i hesapla
        if page > 1:
            offset = (page - 1) * limit

        total = get_locations_count()
        locations = get_all_locations(sort_by=sort_by, limit=limit, offset=offset)

        # Toplam sayfa sayÄ±sÄ±nÄ± hesapla
        pages = (total + limit - 1) // limit if total > 0 else 1
        current_page = (offset // limit) + 1

        return jsonify({
            "locations": locations,
            "count": len(locations),
            "total": total,
            "page": current_page,
            "pages": pages,
            "limit": limit,
            "offset": offset
        })
    except Exception as e:
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/locations", methods=["POST"])
def api_save_location():
    """
    Yeni bir lokasyon kaydeder.
    """
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "GeÃ§ersiz veya eksik JSON gÃ¶vdesi."}), 400
        
        required_fields = ["name", "lat", "lon"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"'{field}' alanÄ± gerekli."}), 400
                
        location = save_location(
            name=data["name"],
            lat=data["lat"],
            lon=data["lon"],
            icon_type=data.get("icon_type", "star"),
            address=data.get("address", "")
        )
        
        return jsonify({
            "status": "success",
            "location": location,
            "message": f"'{location['name']}' konumu kaydedildi!"
        })
    except Exception as e:
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/locations/<location_id>", methods=["DELETE"])
def api_delete_location(location_id):
    """
    Lokasyonu siler.
    """
    try:
        success = delete_location(location_id)
        
        if not success:
            return jsonify({"error": "Lokasyon bulunamadÄ±"}), 404
            
        return jsonify({
            "status": "success",
            "message": "Lokasyon silindi"
        })
    except Exception as e:
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/locations/<location_id>", methods=["PUT"])
def api_update_location(location_id):
    """
    Lokasyonu gÃ¼nceller.
    """
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "GeÃ§ersiz veya eksik JSON gÃ¶vdesi."}), 400

        location = update_location(location_id, data)
        
        if not location:
            return jsonify({"error": "Lokasyon bulunamadÄ±"}), 404
            
        return jsonify({
            "status": "success",
            "location": location,
            "message": "Lokasyon gÃ¼ncellendi"
        })
    except Exception as e:
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


@app.route("/api/locations/<location_id>/favorite", methods=["POST"])
def api_toggle_location_favorite(location_id):
    """
    Lokasyonun favori durumunu deÄŸiÅŸtirir.
    """
    try:
        location = toggle_location_favorite(location_id)
        
        if not location:
            return jsonify({"error": "Lokasyon bulunamadÄ±"}), 404
            
        return jsonify({
            "status": "success",
            "location": location,
            "is_favorite": location.get("favorite", False),
            "message": "Favorilere eklendi *" if location.get("favorite") else "Favorilerden cikarildi"
        })
    except Exception as e:
        return jsonify({"error": f"Sunucu hatasÄ±: {str(e)}"}), 500


# =============================================================================
# BERT NLP ENDPOINTS
# =============================================================================

@app.route("/api/nlp/parse", methods=["POST"])
def api_nlp_parse():
    """
    DoÄŸal dil sorgusunu analiz eder ve yapÄ±landÄ±rÄ±lmÄ±ÅŸ veri dÃ¶ner.

    Request Body:
        {
            "query": "KadÄ±kÃ¶y'den BeÅŸiktaÅŸ'a rota Ã§iz"
        }

    Response:
        {
            "type": "route",           # route | poi | multi | single | unknown
            "confidence": 0.85,
            "origin": "KadÄ±kÃ¶y",
            "destination": "BeÅŸiktaÅŸ",
            "locations": null,         # multi iÃ§in
            "location": null,          # poi iÃ§in
            "detected_places": [
                {"place": "KadÄ±kÃ¶y", "similarity": 0.92},
                {"place": "BeÅŸiktaÅŸ", "similarity": 0.88}
            ],
            "parse_time": 0.15,
            "error": null
        }
    """
    query = ""
    try:
        trace_prefix = _request_trace_prefix()
        print(f"\n{'='*60}")
        print(f"{trace_prefix} [NLP API] Parse Ã§aÄŸrÄ±sÄ± alÄ±ndÄ±")
        global BERT_NLP_AVAILABLE
        data = request.get_json(silent=True)

        if not data or "query" not in data:
            print(f"[NLP API] ? Eksik parametreler")
            return jsonify({"error": "'query' alanÄ± gerekli"}), 400

        query_value = data["query"]
        if not isinstance(query_value, str):
            print(f"[NLP API] ? Query metin olmalÄ±")
            return jsonify({"error": "'query' alanÄ± metin olmalÄ±"}), 400

        query = query_value.strip()
        debug_trace_requested = bool(data.get("debug", False)) or _BERT_PARSE_TRACE_LOG_ENABLED

        if not query or len(query) < 2:
            print(f"[NLP API] ? Sorgu Ã§ok kÄ±sa")
            return jsonify({"error": "Sorgu Ã§ok kÄ±sa"}), 400

        print(f"{trace_prefix} [NLP API] ?? Sorgu: '{_redact_pii_text(query)}'")
        print(f"{trace_prefix} [NLP API] ?? BERT_NLP_AVAILABLE: {BERT_NLP_AVAILABLE}")

        if not BERT_NLP_AVAILABLE:
            print(f"[NLP API] ? BERT motoru ZORUNLU! Regex fallback KALDIRILDI.")
            return jsonify({"error": "BERT motoru gereklidir. Transformers ve PyTorch kurun."}), 503

        print(f"[NLP API] ?? BERT motoru kullanÄ±lÄ±yor...")
        try:
            nlp_engine = get_bert_nlp_engine()
            _log_bert_runtime_metrics(
                stage="parse:before",
                bert_engine_instance=getattr(nlp_engine, "bert", None)
            )
            result = nlp_engine.parse(query, include_trace=debug_trace_requested)
            result["engine"] = "bert-nlp"
            result["trace_policy"] = {
                "request_id": getattr(g, "request_id", None),
                "correlation_id": getattr(g, "correlation_id", None),
                "pii_redaction": True,
                "retention_days": _TRACE_RETENTION_DAYS,
            }
            _log_bert_runtime_metrics(
                stage="parse:after",
                bert_engine_instance=getattr(nlp_engine, "bert", None)
            )
            print(f"{trace_prefix} [NLP API] ? BERT parse baÅŸarÄ±lÄ±")
        except Exception as bert_exc:
            print(f"{trace_prefix} [NLP API] ? BERT hatasÄ±: {bert_exc}")
            return jsonify({"error": f"BERT motoru hatasÄ±: {str(bert_exc)}"}), 500

        confidence = float(result.get("confidence", 0.0) or 0.0)
        print(f"{trace_prefix} [NLP API] ?? SonuÃ§:")
        print(f"{trace_prefix} [NLP API]    - Tip: {result.get('type', 'unknown')}")
        print(f"{trace_prefix} [NLP API]    - Confidence: {confidence:.2f}")
        print(f"{trace_prefix} [NLP API]    - Engine: {result.get('engine', 'unknown')}")
        if result.get('origin'):
            print(f"{trace_prefix} [NLP API]    - Rota: {result['origin']} â€º {result.get('destination', '?')}")
        if result.get('detected_places'):
            print(f"{trace_prefix} [NLP API]    - Tespit edilen yerler: {[p['place'] for p in result['detected_places']]}")
        if debug_trace_requested:
            _log_bert_parse_trace(result.get("trace") or {})

        safe_result = dict(result)
        if "raw_query" in safe_result:
            safe_result["raw_query"] = _redact_pii_text(safe_result.get("raw_query"))
        print(f"{trace_prefix} [NLP API] ?? DÃ¶nen response: {safe_result}")
        print(f"{'='*60}\n")
        try:
            audit_id = log_nlp_parse_audit(
                query_redacted=_redact_pii_text(query),
                result=result,
                request_id=getattr(g, "request_id", "") or "",
                correlation_id=getattr(g, "correlation_id", "") or "",
                error_text="",
            )
            result["audit_id"] = audit_id
        except Exception as audit_exc:
            print(f"{trace_prefix} [NLP API] audit yazilamadi: {audit_exc}")

        return jsonify(result)

    except Exception as e:
        err_text = str(e)
        print(f"{_request_trace_prefix()} [NLP ERROR] {err_text}")
        try:
            log_nlp_parse_audit(
                query_redacted=_redact_pii_text(query),
                result={"type": "unknown", "engine": "bert-nlp", "confidence": 0.0, "parse_time": 0.0},
                request_id=getattr(g, "request_id", "") or "",
                correlation_id=getattr(g, "correlation_id", "") or "",
                error_text=err_text,
            )
        except Exception:
            pass
        return jsonify({"error": f"NLP hatasÄ±: {str(e)}"}), 500


@app.route("/api/nlp/status", methods=["GET"])
def api_nlp_status():
    """
    NLP engine durumunu kontrol eder.

    Response:
        {
            "available": true,
            "engine": "bert-nlp",
            "model": "dbmdz/bert-base-turkish-uncased"
        }
    """
    return jsonify({
        "available": BERT_NLP_AVAILABLE,
        "engine": "bert-nlp" if BERT_NLP_AVAILABLE else "regex-fallback",
        "model": "dbmdz/bert-base-turkish-uncased" if BERT_NLP_AVAILABLE else None,
        "bert_available": BERT_NLP_AVAILABLE,
        "last_error": _BERT_NLP_ERROR
    })


@app.route("/api/nlp/audit/recent", methods=["GET"])
def api_nlp_audit_recent():
    """Son NLP parse audit kayitlarini dondurur."""
    try:
        limit = int(request.args.get("limit", 50))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Gecersiz limit"}), 400

    try:
        rows = list_recent_nlp_parse_audits(limit=limit)
        return jsonify({"ok": True, "count": len(rows), "items": rows})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Sunucu hatasi: {str(e)}", "items": []}), 500


@app.route("/api/nlp/similarity", methods=["POST"])
def api_nlp_similarity():
    """
    Ä°ki metin arasÄ±ndaki semantic similarity'yi hesaplar.

    Request Body:
        {
            "text1": "KadÄ±kÃ¶y",
            "text2": "KadikÃ¶y"
        }

    Response:
        {
            "similarity": 0.92,
            "text1": "KadÄ±kÃ¶y",
            "text2": "KadikÃ¶y"
        }
    """
    try:
        print(f"\n{'='*60}")
        print(f"[NLP API] Similarity Ã§aÄŸrÄ±sÄ± alÄ±ndÄ±")
        if not BERT_NLP_AVAILABLE:
            print(f"[NLP API] ? BERT engine aktif deÄŸil!")
            return jsonify({"error": "BERT engine aktif deÄŸil"}), 503

        data = request.get_json(silent=True)
        print(f"[NLP API] ?? Gelen request: {data}")

        if not data or "text1" not in data or "text2" not in data:
            print(f"[NLP API] ? Eksik parametreler")
            return jsonify({"error": "'text1' ve 'text2' alanlarÄ± gerekli"}), 400

        text1 = data["text1"].strip()
        text2 = data["text2"].strip()
        print(f"[NLP API] ?? Text1: '{text1}' | Text2: '{text2}'")

        if not text1 or not text2:
            print(f"[NLP API] ? BoÅŸ metin")
            return jsonify({"error": "Metinler boÅŸ olamaz"}), 400

        print(f"[NLP API] ?? BERT engine yÃ¼kleniyor...")
        from bert_engine import get_bert_engine
        engine = get_bert_engine()
        _log_bert_runtime_metrics(stage="similarity:before", bert_engine_instance=engine)
        print(f"[NLP API] ? BERT engine hazÄ±r")

        print(f"[NLP API] ?? Benzerlik hesaplanÄ±yor...")
        similarity = engine.similarity(text1, text2)
        _log_bert_runtime_metrics(stage="similarity:after", bert_engine_instance=engine)
        print(f"[NLP API] ? SonuÃ§: {similarity:.4f}")

        result = {
            "similarity": float(similarity),
            "text1": text1,
            "text2": text2
        }
        print(f"[NLP API] ?? DÃ¶nen response: {result}")
        print(f"{'='*60}\n")

        return jsonify(result)

    except Exception as e:
        print(f"[NLP ERROR] Similarity: {str(e)}")
        return jsonify({"error": f"Benzerlik hesaplanamadÄ±: {str(e)}"}), 500


@app.route("/api/nlp/best-match", methods=["POST"])
def api_nlp_best_match():
    """
    Sorguya en yakÄ±n adayÄ± bulur (typo tolerant).

    Request Body:
        {
            "query": "kadikoy",
            "candidates": ["KadÄ±kÃ¶y", "BeÅŸiktaÅŸ", "Taksim"],
            "threshold": 0.75
        }

    Response:
        {
            "match": "KadÄ±kÃ¶y",
            "similarity": 0.92,
            "index": 0
        }
    """
    try:
        print(f"\n{'='*60}")
        print(f"[NLP API] Best Match Ã§aÄŸrÄ±sÄ± alÄ±ndÄ±")
        if not BERT_NLP_AVAILABLE:
            print(f"[NLP API] ? BERT engine aktif deÄŸil!")
            return jsonify({"error": "BERT engine aktif deÄŸil"}), 503

        data = request.get_json(silent=True)
        print(f"[NLP API] ?? Gelen request: query='{data.get('query')}', {len(data.get('candidates', []))} aday")

        if not data or "query" not in data or "candidates" not in data:
            print(f"[NLP API] ? Eksik parametreler")
            return jsonify({"error": "'query' ve 'candidates' alanlarÄ± gerekli"}), 400

        query = data["query"].strip()
        candidates = data["candidates"]
        threshold = data.get("threshold", 0.75)
        print(f"[NLP API] ?? Query: '{query}' | Threshold: {threshold}")
        print(f"[NLP API] ?? Adaylar: {candidates}")

        if not query:
            print(f"[NLP API] ? BoÅŸ sorgu")
            return jsonify({"error": "Sorgu boÅŸ olamaz"}), 400

        if not isinstance(candidates, list) or len(candidates) == 0:
            print(f"[NLP API] ? GeÃ§ersiz adaylar")
            return jsonify({"error": "'candidates' bir liste olmalÄ±"}), 400

        print(f"[NLP API] ?? BERT engine yÃ¼kleniyor...")
        from bert_engine import get_bert_engine
        engine = get_bert_engine()
        _log_bert_runtime_metrics(stage="best-match:before", bert_engine_instance=engine)
        print(f"[NLP API] ? BERT engine hazÄ±r")

        print(f"[NLP API] ?? En iyi eÅŸleÅŸme aranÄ±yor...")
        result = engine.find_best_match(query, candidates, threshold=threshold)
        _log_bert_runtime_metrics(stage="best-match:after", bert_engine_instance=engine)

        if result:
            print(f"[NLP API] ? EÅŸleÅŸme bulundu: {result['match']} (benzerlik: {result['similarity']:.4f})")
            print(f"[NLP API] ?? DÃ¶nen response: {result}")
        else:
            print(f"[NLP API] ? EÅŸleÅŸme bulunamadÄ±")
            result = {
                "match": None,
                "similarity": 0.0,
                "index": -1,
                "message": f"EÅŸleÅŸme bulunamadÄ± (threshold: {threshold})"
            }
        print(f"{'='*60}\n")

        return jsonify(result)

    except Exception as e:
        print(f"[NLP ERROR] Best match: {str(e)}")
        return jsonify({"error": f"EÅŸleÅŸme bulunamadÄ±: {str(e)}"}), 500


# =============================================================================
# HAVA DURUMU ENDPOINTS (OpenMeteo API)
# =============================================================================

@app.route("/api/weather", methods=["GET"])
def api_get_weather():
    """
    Belirli bir konum iÃ§in gÃ¼ncel hava durumunu getirir.

    Query Parameters:
        lat (float, required): Enlem (-90 ile 90 arasi)
        lon (float, required): Boylam (-180 ile 180 arasi)

    Response:
        {
            "success": true,
            "data": {
                "location": {"lat": 41.0082, "lon": 28.9784, "timezone": "Europe/Istanbul"},
                "current": {
                    "timestamp": "2026-03-10T14:00:00+00:00",
                    "temperature": 15.5,
                    "apparent_temperature": 14.2,
                    "humidity": 65,
                    "precipitation": 0.0,
                    "weather_code": 0,
                    "weather_description": "Clear sky",
                    "weather_tr": "Acik gokyuzu",
                    "weather_emoji": "??",
                    "wind_speed": 12.5,
                    "wind_direction": 180
                },
                "cache_hit": false
            }
        }
    """
    if not WEATHER_SERVICE_AVAILABLE:
        return jsonify({"error": "Hava durumu servisi mevcut degil"}), 503

    try:
        # Query parameters
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)

        if lat is None or lon is None:
            return jsonify({"error": "'lat' ve 'lon' parametreleri gerekli"}), 400

        print(f"[Weather] Current weather request: lat={lat}, lon={lon}")

        result = get_current_weather(lat, lon)

        if result.get("success"):
            return jsonify(result)
        else:
            return jsonify({"error": "Hava durumu alinamadi"}), 500

    except Exception as e:
        print(f"[Weather ERROR] {str(e)}")
        return jsonify({"error": f"Sunucu hatasi: {str(e)}"}), 500


@app.route("/api/weather/forecast", methods=["GET"])
def api_get_weather_forecast():
    """
    Belirli bir konum iÃ§in saatlik hava tahmini getirir.

    Query Parameters:
        lat (float, required): Enlem
        lon (float, required): Boylam
        hours (int, optional): Forecast saati (varsayilan 24, max 168)
        timezone (string, optional): Timezone (varsayilan auto)

    Response:
        {
            "success": true,
            "data": {
                "location": {"lat": 41.0082, "lon": 28.9784, "timezone": "Europe/Istanbul"},
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
    """
    if not WEATHER_SERVICE_AVAILABLE:
        return jsonify({"error": "Hava durumu servisi mevcut degil"}), 503

    try:
        # Query parameters
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        hours = request.args.get("hours", 24, type=int)
        timezone = request.args.get("timezone", "auto")

        if lat is None or lon is None:
            return jsonify({"error": "'lat' ve 'lon' parametreleri gerekli"}), 400

        print(f"[Weather] Forecast request: lat={lat}, lon={lon}, hours={hours}")

        result = get_hourly_forecast(lat, lon, hours, timezone_name=timezone)

        if result.get("success"):
            return jsonify(result)
        else:
            return jsonify({"error": "Hava tahmini alinamadi"}), 500

    except ValueError as e:
        return jsonify({"error": f"Gecersiz parametre: {str(e)}"}), 400
    except Exception as e:
        print(f"[Weather ERROR] {str(e)}")
        return jsonify({"error": f"Sunucu hatasi: {str(e)}"}), 500


@app.route("/api/weather/check-route", methods=["POST"])
def api_check_route_weather():
    """
    Rota boyunca hava durumunu kontrol eder.

    Request Body:
        {
            "points": [
                {"lat": 41.0082, "lon": 28.9784, "name": "Kadikoy"},
                {"lat": 41.0422, "lon": 29.0067, "name": "Besiktas"}
            ],
            "start_time": "2026-03-10T14:00:00"  # optional
        }

    Response:
        {
            "success": true,
            "data": {
                "route_weather": [
                    {
                        "point": "Kadikoy",
                        "lat": 41.0082,
                        "lon": 28.9784,
                        "weather": {...}
                    },
                    ...
                ],
                "warnings": ["Besiktas'ta hafif yagmur bekleniyor"],
                "overall_conditions": "clear"
            }
        }
    """
    if not WEATHER_SERVICE_AVAILABLE:
        return jsonify({"error": "Hava durumu servisi mevcut degil"}), 503

    try:
        data = request.get_json(silent=True)

        if not data or "points" not in data:
            return jsonify({"error": "'points' alani gerekli"}), 400

        points = data["points"]
        start_time = data.get("start_time")
        segment_distances = data.get("segment_distances")
        transport_mode = data.get("transport_mode", "walking")

        if not points or len(points) == 0:
            return jsonify({"error": "En az bir nokta gerekli"}), 400

        print(f"[Weather] Route check: {len(points)} noktalar, forecast={'evet' if start_time and 'T' in str(start_time) else 'hayÄ±r'}")

        result = check_route_weather(points, start_time, segment_distances, transport_mode)

        if result.get("success"):
            return jsonify(result)
        else:
            return jsonify({"error": "Rota hava kontrolÃ¼ basarisiz"}), 500

    except Exception as e:
        print(f"[Weather ERROR] {str(e)}")
        return jsonify({"error": f"Sunucu hatasi: {str(e)}"}), 500


@app.route("/api/weather/status", methods=["GET"])
def api_weather_status():
    """
    Hava durumu servisi durumunu dondurÃ¼r.

    Response:
        {
            "service": "weather_service",
            "status": "operational",
            "cache_stats": {...},
            "config": {...}
        }
    """
    if not WEATHER_SERVICE_AVAILABLE:
        return jsonify({
            "service": "weather_service",
            "status": "unavailable",
            "error": "Servis bulunamadi"
        }), 503

    try:
        status = get_service_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({
            "service": "weather_service",
            "status": "error",
            "error": str(e)
        }), 500


@app.route("/api/weather/health", methods=["GET"])
def api_weather_health():
    """
    Hava durumu servisi saglik kontrolÃ¼.

    Response:
        {"healthy": true}
    """
    if not WEATHER_SERVICE_AVAILABLE:
        return jsonify({"healthy": False, "error": "Servis mevcut degil"}), 503

    try:
        is_healthy = weather_health_check()
        return jsonify({"healthy": is_healthy})
    except Exception as e:
        return jsonify({"healthy": False, "error": str(e)}), 500


@app.route("/api/weather/clear-cache", methods=["POST"])
def api_weather_clear_cache():
    """
    Hava durumu cache'ini temizler.

    Response:
        {"status": "success", "cleared": 5}
    """
    if not WEATHER_SERVICE_AVAILABLE:
        return jsonify({"error": "Hava durumu servisi mevcut degil"}), 503

    try:
        count = clear_weather_cache()
        return jsonify({
            "status": "success",
            "cleared": count,
            "message": f"{count} cache entry silindi"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/llm/chat/sessions", methods=["GET"])
def api_llm_chat_sessions():
    """
    Sohbet oturumlarini listeler.
    Query:
      include_archived=1/0 (default: 0)
      limit=200
    """
    include_archived = _as_bool(request.args.get("include_archived"), default=False)
    raw_limit = request.args.get("limit")
    try:
        limit = int(raw_limit) if raw_limit is not None else 200
    except (TypeError, ValueError):
        limit = 200
    limit = max(1, min(limit, 1000))
    sessions = list_chat_sessions(include_archived=include_archived, limit=limit)
    return jsonify({"ok": True, "sessions": sessions})


@app.route("/api/llm/chat/sessions", methods=["POST"])
def api_create_llm_chat_session():
    """
    Yeni sohbet oturumu olusturur.
    Body:
      { "title": "opsiyonel baslik" }
    """
    data = request.get_json(silent=True) or {}
    title = repair_text(data.get("title"))
    session = create_chat_session(title=title or None)
    return jsonify({"ok": True, "session": session}), 201


@app.route("/api/llm/chat/sessions/<session_id>/messages", methods=["GET"])
def api_llm_chat_session_messages(session_id: str):
    """
    Verilen oturumun mesajlarini getirir.
    Query:
      limit=opsiyonel
    """
    session = get_chat_session(session_id)
    if not session:
        return jsonify({"ok": False, "error": "Oturum bulunamadi"}), 404

    raw_limit = request.args.get("limit")
    if raw_limit is None or str(raw_limit).strip() == "":
        limit = None
    else:
        try:
            limit = max(1, min(int(raw_limit), 2000))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "Gecersiz limit"}), 400

    messages = list_chat_messages(session_id, limit=limit)
    return jsonify({"ok": True, "session": session, "messages": messages})


@app.route("/api/llm/chat/sessions/<session_id>/archive", methods=["POST"])
def api_archive_llm_chat_session(session_id: str):
    """
    Oturumu arsivler (silmez).
    """
    ok = archive_chat_session(session_id)
    if not ok:
        return jsonify({"ok": False, "error": "Oturum bulunamadi"}), 404
    return jsonify({"ok": True, "session_id": session_id, "archived": True})


@app.route("/api/llm/model-health", methods=["GET"])
def api_llm_model_health():
    provider = str(request.args.get("provider", "openrouter") or "openrouter").strip().lower()
    if provider not in {"openrouter", "gemini"}:
        return jsonify({"ok": False, "error": "Gecersiz provider"}), 400
    rows = list_provider_health(provider)
    blocked = [r["model"] for r in rows if r.get("blocked")]
    return jsonify({
        "ok": True,
        "provider": provider,
        "blocked_models": blocked,
        "models": rows,
    })


@app.route("/api/llm/openrouter/status", methods=["GET"])
def api_openrouter_status():
    """
    OpenRouter entegrasyon durumunu dondurur.
    """
    if not OPENROUTER_SERVICE_AVAILABLE:
        return jsonify({
            "available": False,
            "configured": False,
            "error": "OpenRouter servisi yuklenemedi",
        }), 503

    status = openrouter_status()
    health_rows = list_provider_health("openrouter")
    blocked = [r["model"] for r in health_rows if r.get("blocked")]
    return jsonify({
        "available": True,
        "configured": status["configured"],
        "base_url": status["base_url"],
        "default_model": status["default_model"],
        "fallback_models": status.get("fallback_models", []),
        "timeout_sec": status["timeout_sec"],
        "blocked_models": blocked,
        "health_count": len(health_rows),
    })


@app.route("/api/llm/openrouter/chat", methods=["POST"])
def api_openrouter_chat():
    """
    OpenRouter uzerinden chat completion cagrisi yapar.

    Request body:
    {
      "query": "Merhaba",  # opsiyonel, messages ile alternatif
      "messages": [{"role":"user","content":"Merhaba"}],  # opsiyonel
      "model": "google/gemma-3-27b-it:free",  # opsiyonel
      "temperature": 0.2,  # opsiyonel
      "max_tokens": 512  # opsiyonel
    }
    """
    if not OPENROUTER_SERVICE_AVAILABLE:
        return jsonify({"error": "OpenRouter servisi mevcut degil"}), 503

    if not is_openrouter_configured():
        return jsonify({"error": "OPENROUTER_API_KEY tanimli degil"}), 503

    data = request.get_json(silent=True) or {}

    messages = data.get("messages")
    query = repair_text(data.get("query"))
    if messages is None:
        if not query:
            return jsonify({"error": "'query' veya 'messages' zorunlu"}), 400
        messages = [{"role": "user", "content": query}]

    if not isinstance(messages, list):
        return jsonify({"error": "'messages' bos olmayan liste olmali"}), 400
    messages = _normalize_messages(messages)
    if not messages:
        return jsonify({"error": "'messages' bos olmayan liste olmali"}), 400
    messages = _inject_system_message(messages)

    model = data.get("model")
    temperature = data.get("temperature")
    max_tokens = data.get("max_tokens")
    use_fallback = _as_bool(data.get("use_fallback", True), default=True)

    try:
        if use_fallback:
            result = openrouter_chat_completion_with_fallback(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            result = openrouter_chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            result["tried_models"] = [result.get("model") or model or ""]
        return jsonify({
            "ok": True,
            "model": repair_text(result.get("model")),
            "text": repair_text(result.get("text", "")),
            "usage": result.get("usage", {}),
            "id": result.get("id"),
            "tried_models": result.get("tried_models", []),
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        return jsonify({"error": f"Sunucu hatasi: {exc}"}), 500


@app.route("/api/llm/openrouter/chat/stream", methods=["POST"])
def api_openrouter_chat_stream():
    """
    OpenRouter chat cagrisini canli akis (stream) olarak dondurur.

    Response format: application/x-ndjson
    Her satir bir JSON objesidir.
    """
    if not OPENROUTER_SERVICE_AVAILABLE:
        return jsonify({"error": "OpenRouter servisi mevcut degil"}), 503

    if not is_openrouter_configured():
        return jsonify({"error": "OPENROUTER_API_KEY tanimli degil"}), 503

    data = request.get_json(silent=True) or {}

    session_id = str(data.get("session_id", "") or "").strip()
    session = None
    if session_id:
        session = get_chat_session(session_id)
        if not session:
            return jsonify({"error": "Gecerli bir session_id gerekli"}), 404
        if int(session.get("archived") or 0) == 1:
            return jsonify({"error": "Arsivlenmis oturuma mesaj yazilamaz"}), 400

    raw_messages = data.get("messages")
    query = repair_text(data.get("query"))

    provided_messages: list[dict] = []
    if raw_messages is not None:
        if not isinstance(raw_messages, list):
            return jsonify({"error": "'messages' bos olmayan liste olmali"}), 400
        provided_messages = _normalize_messages(raw_messages)

    if not query and not provided_messages:
        return jsonify({"error": "'query' veya 'messages' zorunlu"}), 400

    user_text = query or _extract_latest_user_text(provided_messages)
    if not user_text:
        return jsonify({"error": "Kullanici mesaji bos olamaz"}), 400

    if session_id:
        llm_messages = _inject_system_message(
            _chat_context_from_session(session_id, context_limit=40) + [{"role": "user", "content": user_text}]
        )
    else:
        llm_messages = provided_messages or [{"role": "user", "content": user_text}]
        llm_messages = _inject_system_message(llm_messages)

    model = data.get("model")
    temperature = data.get("temperature")
    max_tokens = data.get("max_tokens")
    use_fallback = _as_bool(data.get("use_fallback", True), default=True)
    default_model = openrouter_status().get("default_model", "")
    requested_model = str(model or "").strip()
    if use_fallback:
        candidate_models = _llm_candidate_models("openrouter", requested_model or default_model)
        candidate_models = [m for m in candidate_models if not is_model_blocked("openrouter", m)]
        if not candidate_models:
            return jsonify({"error": "Kullanilabilir model yok (cooldown aktif)"}), 503
    else:
        candidate_models = [requested_model or default_model]

    @stream_with_context
    def _generator():
        collected_tokens: list[str] = []
        final_model = repair_text(requested_model or default_model)
        token_total = None
        stream_error = ""
        error_type = ""
        tried_models: list[str] = []
        for idx, candidate in enumerate(candidate_models):
            tried_models.append(candidate)
            final_model = repair_text(candidate)
            attempt_start = time.time()

            yield json.dumps(
                {"type": "meta", "phase": "start", "model": candidate, "tried_models": tried_models},
                ensure_ascii=False,
            ) + "\n"

            try:
                stream_iter = openrouter_chat_completion_stream(
                    messages=llm_messages,
                    model=candidate,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                attempt_done = False
                got_tokens = False
                for chunk in stream_iter:
                    ctype = chunk.get("type")
                    if ctype == "done":
                        attempt_done = True
                        continue
                    if ctype == "token":
                        clean_text = repair_text(chunk.get("text"))
                        if clean_text:
                            collected_tokens.append(clean_text)
                            got_tokens = True
                        chunk = {"type": "token", "text": clean_text}
                    elif ctype == "meta":
                        if chunk.get("model"):
                            final_model = repair_text(chunk.get("model"))
                        usage = chunk.get("usage") or {}
                        try:
                            if usage.get("total_tokens") is not None:
                                token_total = int(usage.get("total_tokens"))
                        except (TypeError, ValueError):
                            token_total = None
                        chunk = dict(chunk)
                        if final_model:
                            chunk["model"] = final_model
                        chunk["tried_models"] = tried_models
                    yield json.dumps(chunk, ensure_ascii=False) + "\n"

                if attempt_done or got_tokens:
                    latency_ms = int((time.time() - attempt_start) * 1000)
                    record_llm_attempt(
                        provider="openrouter",
                        model=candidate,
                        success=True,
                        latency_ms=latency_ms,
                    )
                    yield json.dumps(
                        {"type": "meta", "phase": "success", "model": candidate, "tried_models": tried_models},
                        ensure_ascii=False,
                    ) + "\n"
                    yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"
                    stream_error = ""
                    error_type = ""
                    break

                stream_error = "Model bos dondu"
                error_type = "other"
                raise RuntimeError(stream_error)
            except ValueError as exc:
                stream_error = repair_text(str(exc))
                error_type = _classify_llm_error(stream_error)
                record_llm_attempt(
                    provider="openrouter",
                    model=candidate,
                    success=False,
                    error_type=error_type,
                    error_text=stream_error,
                    latency_ms=int((time.time() - attempt_start) * 1000),
                )
                has_next = use_fallback and (idx < len(candidate_models) - 1)
                if has_next:
                    yield json.dumps(
                        {"type": "meta", "phase": "fallback", "model": candidate, "error": stream_error, "tried_models": tried_models},
                        ensure_ascii=False,
                    ) + "\n"
                    continue
                yield json.dumps({"type": "error", "error": stream_error}, ensure_ascii=False) + "\n"
            except RuntimeError as exc:
                stream_error = repair_text(str(exc))
                error_type = _classify_llm_error(stream_error)
                record_llm_attempt(
                    provider="openrouter",
                    model=candidate,
                    success=False,
                    error_type=error_type,
                    error_text=stream_error,
                    latency_ms=int((time.time() - attempt_start) * 1000),
                )
                has_next = use_fallback and (idx < len(candidate_models) - 1)
                if has_next:
                    yield json.dumps(
                        {"type": "meta", "phase": "fallback", "model": candidate, "error": stream_error, "tried_models": tried_models},
                        ensure_ascii=False,
                    ) + "\n"
                    continue
                yield json.dumps({"type": "error", "error": stream_error}, ensure_ascii=False) + "\n"
            except Exception as exc:
                stream_error = repair_text(f"Sunucu hatasi: {exc}")
                error_type = _classify_llm_error(stream_error)
                record_llm_attempt(
                    provider="openrouter",
                    model=candidate,
                    success=False,
                    error_type=error_type,
                    error_text=stream_error,
                    latency_ms=int((time.time() - attempt_start) * 1000),
                )
                has_next = use_fallback and (idx < len(candidate_models) - 1)
                if has_next:
                    yield json.dumps(
                        {"type": "meta", "phase": "fallback", "model": candidate, "error": stream_error, "tried_models": tried_models},
                        ensure_ascii=False,
                    ) + "\n"
                    continue
                yield json.dumps({"type": "error", "error": stream_error}, ensure_ascii=False) + "\n"

            # This attempt failed and no fallback remains.
            break

        if not session_id:
            return
        assistant_text = repair_text("".join(collected_tokens))
        if stream_error and not assistant_text:
            assistant_text = f"[Hata] {stream_error}"
        if not assistant_text:
            assistant_text = "[Bos yanit]"
        try:
            save_chat_turn(
                session_id=session_id,
                user_text=user_text,
                assistant_text=assistant_text,
                model=final_model or "",
                token_total=token_total,
                error_type=error_type,
            )
        except Exception as persist_exc:
            warn_text = repair_text(f"Sohbet kaydi yazilamadi: {persist_exc}")
            yield json.dumps({"type": "meta", "phase": "persist_warn", "error": warn_text}, ensure_ascii=False) + "\n"

    return Response(_generator(), mimetype="application/x-ndjson")


@app.route("/api/llm/openrouter/models", methods=["GET"])
def api_openrouter_models():
    """
    OpenRouter'dan text modelleri listeler (image/video agirlikli modeller filtrelenir).
    """
    if not OPENROUTER_SERVICE_AVAILABLE:
        return jsonify({"error": "OpenRouter servisi mevcut degil"}), 503

    try:
        models = openrouter_list_text_models()
        return jsonify({"ok": True, "models": models})
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc), "models": []}), 502
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Sunucu hatasi: {exc}", "models": []}), 500


@app.route("/api/llm/gemini/status", methods=["GET"])
def api_gemini_status():
    """Google Gemini entegrasyon durumunu dondurur."""
    if not GEMINI_SERVICE_AVAILABLE:
        return jsonify({
            "available": False,
            "configured": False,
            "error": "Gemini servisi yuklenemedi",
        }), 503

    status = gemini_status()
    health_rows = list_provider_health("gemini")
    blocked = [r["model"] for r in health_rows if r.get("blocked")]
    return jsonify({
        "available": True,
        "configured": status["configured"],
        "api_base": status["api_base"],
        "default_model": status["default_model"],
        "fallback_models": status.get("fallback_models", []),
        "timeout_sec": status["timeout_sec"],
        "blocked_models": blocked,
        "health_count": len(health_rows),
    })


@app.route("/api/llm/gemini/chat", methods=["POST"])
def api_gemini_chat():
    """
    Gemini uzerinden uretim (tek seferde tam yanit).
    Istek govdesi OpenRouter ile ayni sembolik.
    """
    if not GEMINI_SERVICE_AVAILABLE:
        return jsonify({"error": "Gemini servisi mevcut degil"}), 503

    if not is_gemini_configured():
        return jsonify({"error": "GEMINI_API_KEY veya GOOGLE_API_KEY tanimli degil"}), 503

    data = request.get_json(silent=True) or {}

    messages = data.get("messages")
    query = repair_text(data.get("query"))
    if messages is None:
        if not query:
            return jsonify({"error": "'query' veya 'messages' zorunlu"}), 400
        messages = [{"role": "user", "content": query}]

    if not isinstance(messages, list):
        return jsonify({"error": "'messages' bos olmayan liste olmali"}), 400
    messages = _normalize_messages(messages)
    if not messages:
        return jsonify({"error": "'messages' bos olmayan liste olmali"}), 400
    messages = _inject_system_message(messages)

    model = data.get("model")
    temperature = data.get("temperature")
    max_tokens = data.get("max_tokens")
    use_fallback = _as_bool(data.get("use_fallback", True), default=True)

    try:
        if use_fallback:
            result = gemini_chat_completion_with_fallback(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            result = gemini_chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            result["tried_models"] = [result.get("model") or model or ""]
        return jsonify({
            "ok": True,
            "model": repair_text(result.get("model")),
            "text": repair_text(result.get("text", "")),
            "usage": result.get("usage", {}),
            "id": result.get("id"),
            "tried_models": result.get("tried_models", []),
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        return jsonify({"error": f"Sunucu hatasi: {exc}"}), 500


@app.route("/api/llm/gemini/chat/stream", methods=["POST"])
def api_gemini_chat_stream():
    """Gemini canli akis (NDJSON), OpenRouter stream ile ayni satir formati."""
    if not GEMINI_SERVICE_AVAILABLE:
        return jsonify({"error": "Gemini servisi mevcut degil"}), 503

    if not is_gemini_configured():
        return jsonify({"error": "GEMINI_API_KEY veya GOOGLE_API_KEY tanimli degil"}), 503

    data = request.get_json(silent=True) or {}

    session_id = str(data.get("session_id", "") or "").strip()
    session = None
    if session_id:
        session = get_chat_session(session_id)
        if not session:
            return jsonify({"error": "Gecerli bir session_id gerekli"}), 404
        if int(session.get("archived") or 0) == 1:
            return jsonify({"error": "Arsivlenmis oturuma mesaj yazilamaz"}), 400

    raw_messages = data.get("messages")
    query = repair_text(data.get("query"))

    provided_messages: list[dict] = []
    if raw_messages is not None:
        if not isinstance(raw_messages, list):
            return jsonify({"error": "'messages' bos olmayan liste olmali"}), 400
        provided_messages = _normalize_messages(raw_messages)

    if not query and not provided_messages:
        return jsonify({"error": "'query' veya 'messages' zorunlu"}), 400

    user_text = query or _extract_latest_user_text(provided_messages)
    if not user_text:
        return jsonify({"error": "Kullanici mesaji bos olamaz"}), 400

    if session_id:
        llm_messages = _inject_system_message(
            _chat_context_from_session(session_id, context_limit=40) + [{"role": "user", "content": user_text}]
        )
    else:
        llm_messages = provided_messages or [{"role": "user", "content": user_text}]
        llm_messages = _inject_system_message(llm_messages)

    model = data.get("model")
    temperature = data.get("temperature")
    max_tokens = data.get("max_tokens")
    use_fallback = _as_bool(data.get("use_fallback", True), default=True)
    default_model = gemini_status().get("default_model", "")
    requested_model = str(model or "").strip()
    if use_fallback:
        candidate_models = _llm_candidate_models("gemini", requested_model or default_model)
        candidate_models = [m for m in candidate_models if not is_model_blocked("gemini", m)]
        if not candidate_models:
            return jsonify({"error": "Kullanilabilir model yok (cooldown aktif)"}), 503
    else:
        candidate_models = [requested_model or default_model]

    @stream_with_context
    def _generator():
        collected_tokens: list[str] = []
        final_model = repair_text(requested_model or default_model)
        token_total = None
        stream_error = ""
        error_type = ""
        tried_models: list[str] = []
        for idx, candidate in enumerate(candidate_models):
            tried_models.append(candidate)
            final_model = repair_text(candidate)
            attempt_start = time.time()

            yield json.dumps(
                {"type": "meta", "phase": "start", "model": candidate, "tried_models": tried_models},
                ensure_ascii=False,
            ) + "\n"

            try:
                stream_iter = gemini_chat_completion_stream(
                    messages=llm_messages,
                    model=candidate,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                attempt_done = False
                got_tokens = False
                for chunk in stream_iter:
                    ctype = chunk.get("type")
                    if ctype == "done":
                        attempt_done = True
                        continue
                    if ctype == "token":
                        clean_text = repair_text(chunk.get("text"))
                        if clean_text:
                            collected_tokens.append(clean_text)
                            got_tokens = True
                        chunk = {"type": "token", "text": clean_text}
                    elif ctype == "meta":
                        if chunk.get("model"):
                            final_model = repair_text(chunk.get("model"))
                        usage = chunk.get("usage") or {}
                        try:
                            if usage.get("total_tokens") is not None:
                                token_total = int(usage.get("total_tokens"))
                        except (TypeError, ValueError):
                            token_total = None
                        chunk = dict(chunk)
                        if final_model:
                            chunk["model"] = final_model
                        chunk["tried_models"] = tried_models
                    yield json.dumps(chunk, ensure_ascii=False) + "\n"

                if attempt_done or got_tokens:
                    latency_ms = int((time.time() - attempt_start) * 1000)
                    record_llm_attempt(
                        provider="gemini",
                        model=candidate,
                        success=True,
                        latency_ms=latency_ms,
                    )
                    yield json.dumps(
                        {"type": "meta", "phase": "success", "model": candidate, "tried_models": tried_models},
                        ensure_ascii=False,
                    ) + "\n"
                    yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"
                    stream_error = ""
                    error_type = ""
                    break

                stream_error = "Model bos dondu"
                error_type = "other"
                raise RuntimeError(stream_error)
            except ValueError as exc:
                stream_error = repair_text(str(exc))
                error_type = _classify_llm_error(stream_error)
                record_llm_attempt(
                    provider="gemini",
                    model=candidate,
                    success=False,
                    error_type=error_type,
                    error_text=stream_error,
                    latency_ms=int((time.time() - attempt_start) * 1000),
                )
                has_next = use_fallback and (idx < len(candidate_models) - 1)
                if has_next:
                    yield json.dumps(
                        {"type": "meta", "phase": "fallback", "model": candidate, "error": stream_error, "tried_models": tried_models},
                        ensure_ascii=False,
                    ) + "\n"
                    continue
                yield json.dumps({"type": "error", "error": stream_error}, ensure_ascii=False) + "\n"
            except RuntimeError as exc:
                stream_error = repair_text(str(exc))
                error_type = _classify_llm_error(stream_error)
                record_llm_attempt(
                    provider="gemini",
                    model=candidate,
                    success=False,
                    error_type=error_type,
                    error_text=stream_error,
                    latency_ms=int((time.time() - attempt_start) * 1000),
                )
                has_next = use_fallback and (idx < len(candidate_models) - 1)
                if has_next:
                    yield json.dumps(
                        {"type": "meta", "phase": "fallback", "model": candidate, "error": stream_error, "tried_models": tried_models},
                        ensure_ascii=False,
                    ) + "\n"
                    continue
                yield json.dumps({"type": "error", "error": stream_error}, ensure_ascii=False) + "\n"
            except Exception as exc:
                stream_error = repair_text(f"Sunucu hatasi: {exc}")
                error_type = _classify_llm_error(stream_error)
                record_llm_attempt(
                    provider="gemini",
                    model=candidate,
                    success=False,
                    error_type=error_type,
                    error_text=stream_error,
                    latency_ms=int((time.time() - attempt_start) * 1000),
                )
                has_next = use_fallback and (idx < len(candidate_models) - 1)
                if has_next:
                    yield json.dumps(
                        {"type": "meta", "phase": "fallback", "model": candidate, "error": stream_error, "tried_models": tried_models},
                        ensure_ascii=False,
                    ) + "\n"
                    continue
                yield json.dumps({"type": "error", "error": stream_error}, ensure_ascii=False) + "\n"

            break

        if not session_id:
            return
        assistant_text = repair_text("".join(collected_tokens))
        if stream_error and not assistant_text:
            assistant_text = f"[Hata] {stream_error}"
        if not assistant_text:
            assistant_text = "[Bos yanit]"
        try:
            save_chat_turn(
                session_id=session_id,
                user_text=user_text,
                assistant_text=assistant_text,
                model=final_model or "",
                token_total=token_total,
                error_type=error_type,
            )
        except Exception as persist_exc:
            warn_text = repair_text(f"Sohbet kaydi yazilamadi: {persist_exc}")
            yield json.dumps({"type": "meta", "phase": "persist_warn", "error": warn_text}, ensure_ascii=False) + "\n"

    return Response(_generator(), mimetype="application/x-ndjson")


@app.route("/api/llm/gemini/models", methods=["GET"])
def api_gemini_models():
    """ENV'deki varsayilan + fallback Gemini model id'lerini listeler."""
    if not GEMINI_SERVICE_AVAILABLE:
        return jsonify({"error": "Gemini servisi mevcut degil"}), 503

    try:
        st = gemini_status()
        seen: set[str] = set()
        models: list[str] = []
        for mid in [st["default_model"]] + list(st.get("fallback_models") or []):
            m = str(mid or "").strip()
            if m and m not in seen:
                seen.add(m)
                models.append(m)
        return jsonify({"ok": True, "models": models})
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Sunucu hatasi: {exc}", "models": []}), 500


# =============================================================================
# TOPLU ULASIM API'LERI
# =============================================================================

try:
    from ibb_transit import (
        initialize_transit_data,
        get_stops_in_area,
        search_stops as search_transit_stops,
        get_route_info as get_transit_route_info,
        get_routes_for_stop,
        get_statistics as get_transit_statistics,
    )
    _transit_available = True
except ImportError:
    _transit_available = False
    print("[API] ibb_transit modulu yuklenemedi, transit API devre disi")


@app.route("/api/transit/stops", methods=["GET"])
def api_transit_stops():
    """
    Belirtilen koordinat etrafindaki toplu tasima duraklarini doner.

    Query Parameters:
        lat: Enlem
        lon: Boylam
        radius: Yaricap (metre, varsayilan 500)
    """
    if not _transit_available:
        return jsonify({"error": "Transit modulu yuklu degil"}), 503

    try:
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        radius = request.args.get("radius", 500, type=float)

        if lat is None or lon is None:
            return jsonify({"error": "'lat' ve 'lon' parametreleri gerekli"}), 400

        stops = get_stops_in_area(lat, lon, radius)

        return jsonify({
            "stops": stops,
            "count": len(stops),
            "center": {"lat": lat, "lon": lon},
            "radius_m": radius,
        })

    except Exception as e:
        print(f"[API] Transit stops hatasi: {e}")
        return jsonify({"error": f"Sunucu hatasi: {str(e)}"}), 500


@app.route("/api/transit/search", methods=["GET"])
def api_transit_search():
    """
    Durak adi ile arama yapar.

    Query Parameters:
        q: Arama metni
        limit: Maks sonuc (varsayilan 20)
    """
    if not _transit_available:
        return jsonify({"error": "Transit modulu yuklu degil"}), 503

    try:
        query = request.args.get("q", "")
        limit = request.args.get("limit", 20, type=int)

        if not query or len(query) < 2:
            return jsonify({"error": "En az 2 karakter gerekli"}), 400

        results = search_transit_stops(query, limit)

        return jsonify({
            "stops": results,
            "count": len(results),
            "query": query,
        })

    except Exception as e:
        print(f"[API] Transit arama hatasi: {e}")
        return jsonify({"error": f"Sunucu hatasi: {str(e)}"}), 500


@app.route("/api/transit/route", methods=["GET"])
def api_transit_route():
    """
    Hat detay bilgisi doner.

    Query Parameters:
        code: Hat kodu (orn: 500T)
    """
    if not _transit_available:
        return jsonify({"error": "Transit modulu yuklu degil"}), 503

    try:
        code = request.args.get("code", "")

        if not code:
            return jsonify({"error": "'code' parametresi gerekli"}), 400

        route = get_transit_route_info(code)

        if not route:
            return jsonify({"error": f"Hat bulunamadi: {code}"}), 404

        return jsonify({"route": route})

    except Exception as e:
        print(f"[API] Transit route hatasi: {e}")
        return jsonify({"error": f"Sunucu hatasi: {str(e)}"}), 500


@app.route("/api/transit/stop-routes", methods=["GET"])
def api_transit_stop_routes():
    """
    Bir duraktan gecen hatlari doner.

    Query Parameters:
        code: Durak kodu
    """
    if not _transit_available:
        return jsonify({"error": "Transit modulu yuklu degil"}), 503

    try:
        code = request.args.get("code", type=int)

        if code is None:
            return jsonify({"error": "'code' parametresi gerekli"}), 400

        routes = get_routes_for_stop(code)

        return jsonify({
            "routes": routes,
            "count": len(routes),
            "stop_code": code,
        })

    except Exception as e:
        print(f"[API] Transit stop-routes hatasi: {e}")
        return jsonify({"error": f"Sunucu hatasi: {str(e)}"}), 500


@app.route("/api/transit/stats", methods=["GET"])
def api_transit_stats():
    """Transit veri istatistikleri."""
    if not _transit_available:
        return jsonify({"error": "Transit modulu yuklu degil"}), 503

    try:
        stats = get_transit_statistics()
        return jsonify(stats)

    except Exception as e:
        print(f"[API] Transit stats hatasi: {e}")
        return jsonify({"error": f"Sunucu hatasi: {str(e)}"}), 500


@app.route("/api/transit/init", methods=["POST"])
def api_transit_init():
    """
    Transit verilerini baslatir/gunceller.
    Ilk calistirmada ~30 saniye surebilir.
    """
    if not _transit_available:
        return jsonify({"error": "Transit modulu yuklu degil"}), 503

    try:
        force = request.args.get("force", "false").lower() == "true"
        result = initialize_transit_data(force=force)

        return jsonify({
            "status": "success",
            "message": f"{result['stops']} durak, {result['routes']} hat yuklendi",
            **result,
        })

    except Exception as e:
        print(f"[API] Transit init hatasi: {e}")
        return jsonify({"error": f"Sunucu hatasi: {str(e)}"}), 500


# =============================================================================
# MULTIMODAL ROTA API
# =============================================================================

try:
    from multimodal_engine import compare_routes as multimodal_compare
    _multimodal_available = True
except ImportError:
    _multimodal_available = False
    print("[API] multimodal_engine yuklenemedi")


@app.route("/api/multimodal/compare", methods=["POST"])
def api_multimodal_compare():
    """
    Yuruyus ve toplu tasima seceneklerini karsilastirir.

    Request Body:
        {
            "origin": [lat, lon],
            "destination": [lat, lon]
        }

    Response:
        {
            "options": [...],
            "recommended": "transit" | "walking",
            "recommendation_reason": "..."
        }
    """
    if not _multimodal_available:
        return jsonify({"error": "Multimodal motor yuklu degil"}), 503

    try:
        data = request.get_json()

        if not data or "origin" not in data or "destination" not in data:
            return jsonify({"error": "'origin' ve 'destination' alanlari gerekli"}), 400

        origin = data["origin"]
        destination = data["destination"]

        if not (isinstance(origin, list) and len(origin) == 2):
            return jsonify({"error": "origin [lat, lon] formatinda olmali"}), 400
        if not (isinstance(destination, list) and len(destination) == 2):
            return jsonify({"error": "destination [lat, lon] formatinda olmali"}), 400

        result = multimodal_compare(
            origin[0], origin[1],
            destination[0], destination[1],
        )

        return jsonify(result)

    except Exception as e:
        print(f"[API] Multimodal hatasi: {e}")
        return jsonify({"error": f"Sunucu hatasi: {str(e)}"}), 500


if __name__ == "__main__":
    # Transit verilerini arka planda yukle
    if _transit_available:
        try:
            initialize_transit_data()
        except Exception as e:
            print(f"[Transit] Baslangic yukleme hatasi: {e}")

    print("=" * 50)
    print("  OpenTrip API Sunucusu Baslatiliyor...")
    print("  http://localhost:5000")
    print("=" * 50)
    initialize_runtime()
    if _PRELOAD_POPULAR_REGIONS_ON_STARTUP:
        initialize_graph_preload()
    app.run(debug=False, port=5000)

# Management endpoints for BERT: warmup and place seeding
@app.route("/api/nlp/warmup", methods=["GET", "POST"]) 
def api_nlp_warmup():
    """Trigger BERT warmup in background. POST body or ?force=1 to force.
    """
    try:
        force = False
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            force = bool(data.get("force", False))
        else:
            force = str(request.args.get("force", "0")).lower() in ("1", "true", "yes")

        _preload_bert_async(force=True if force else True)
        return jsonify({"started": True, "force": force, "message": "BERT warmup started in background."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/nlp/seed-places", methods=["POST"]) 
def api_nlp_seed_places():
    """Start place DB seeding and embedding computation.

    Body JSON (all optional): {"static":true, "local":true, "dynamic":false, "user":true, "background":true}
    """
    try:
        data = request.get_json(silent=True) or {}
        static = bool(data.get("static", True))
        local = bool(data.get("local", True))
        dynamic = bool(data.get("dynamic", False))
        user = bool(data.get("user", True))
        background = bool(data.get("background", True))

        script_path = os.path.join(os.getcwd(), "OpenRoutePlanner", "scripts", "tools", "seed_places.py")
        cmd_parts = [sys.executable, script_path, "--out-dir", os.path.join("OpenRoutePlanner", "backend", "data")]
        if static:
            cmd_parts.append("--static")
        if local:
            cmd_parts.append("--local")
        if dynamic:
            cmd_parts.append("--dynamic")
        if user:
            cmd_parts.append("--user")

        # Build a safely quoted command string
        cmd = " ".join([f'"{p}"' for p in cmd_parts])

        def _run_cmd():
            import subprocess
            print("[api_nlp_seed_places] running:", cmd)
            subprocess.run(cmd, shell=True)
            print("[api_nlp_seed_places] finished")

        if background:
            import threading
            t = threading.Thread(target=_run_cmd, daemon=True)
            t.start()
            return jsonify({"started": True, "cmd": cmd}), 202
        else:
            import subprocess
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return jsonify({"ok": proc.returncode == 0, "stdout": proc.stdout, "stderr": proc.stderr}), (200 if proc.returncode == 0 else 500)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/nlp/optimize-model', methods=['POST'])
def api_nlp_optimize_model():
    """Trigger model optimization (ONNX export). Body: {"mode":"onnx" , "background": true}
    """
    try:
        data = request.get_json(silent=True) or {}
        mode = data.get('mode', 'onnx')
        background = bool(data.get('background', True))

        script_path = os.path.join(os.getcwd(), 'OpenRoutePlanner', 'scripts', 'tools', 'optimize_model.py')
        cmd_parts = [sys.executable, script_path, '--mode', str(mode), '--out-dir', os.path.join('OpenRoutePlanner','backend','data')]
        cmd = ' '.join([f'"{p}"' for p in cmd_parts])

        def _run_cmd():
            import subprocess
            print('[api_nlp_optimize_model] running:', cmd)
            subprocess.run(cmd, shell=True)
            print('[api_nlp_optimize_model] finished')

        if background:
            import threading
            t = threading.Thread(target=_run_cmd, daemon=True)
            t.start()
            return jsonify({'started': True, 'cmd': cmd}), 202
        else:
            import subprocess
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return jsonify({'ok': proc.returncode == 0, 'stdout': proc.stdout, 'stderr': proc.stderr}), (200 if proc.returncode == 0 else 500)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

