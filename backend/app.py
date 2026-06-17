"""
app.py - Flask API Sunucusu

Frontend ile Backend arasÃındaki kÃƒöprÃƒü.
Rota optimizasyonu ve POI arama endpoint'leri saÃşlar.
"""
import os
import sys
import io

# Force UTF-8 stdout/stderr on Windows to avoid CP1254 terminal and redirect encoding mojibakes
# Skip inside pytest environments to prevent standard output stream capturing issues
if sys.platform.startswith('win') and "pytest" not in sys.argv[0] and "PYTEST_CURRENT_TEST" not in os.environ:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

    # Auto-re-execute using virtual environment python if running globally on Windows
    import subprocess
    venv_python = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".venv", "Scripts", "python.exe"))
    if os.path.exists(venv_python) and os.path.abspath(sys.executable).lower() != venv_python.lower():
        print(f"[app.py] Sanal ortam disinda calistirildi. Otomatik olarak .venv (GPU/CUDA) ortaminda yeniden baslatiliyor...")
        sys.exit(subprocess.call([venv_python] + sys.argv))

import json
import time
import hashlib
import builtins
import uuid
import re
import threading
import difflib
from datetime import datetime, timezone
from functools import partial
from typing import Any
from route_config import ROUTE_CONFIG


def _env_flag(name: str, default: bool) -> bool:
    """ENV'den bool deÃşer okur."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    """ENV'den float deÃşer okur."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return default


ISTANBUL_GEOFENCE_BBOX = {
    "min_lat": 40.78,
    "max_lat": 41.40,
    "min_lon": 28.30,
    "max_lon": 29.70,
}


def _to_lat_lon_pair(raw: Any) -> tuple[float, float] | None:
    """
    [lat, lon] formatindaki veriyi guvenli float ciftine cevirir.
    """
    if not (isinstance(raw, list) and len(raw) == 2):
        return None
    try:
        lat = float(raw[0])
        lon = float(raw[1])
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def _is_in_istanbul_bbox(lat: float, lon: float) -> bool:
    return (
        ISTANBUL_GEOFENCE_BBOX["min_lat"] <= lat <= ISTANBUL_GEOFENCE_BBOX["max_lat"]
        and ISTANBUL_GEOFENCE_BBOX["min_lon"] <= lon <= ISTANBUL_GEOFENCE_BBOX["max_lon"]
    )


def _outside_istanbul_response(detail: str | None = None, *, field: str | None = None):
    payload = {
        "error": "Bu ozellik su an sadece Istanbul sinirlari icin kullanilabilir.",
        "code": "outside_istanbul",
        "geofence": ISTANBUL_GEOFENCE_BBOX,
    }
    if detail:
        payload["detail"] = detail
    if field:
        payload["field"] = field
    return jsonify(payload), 400


def _first_outside_point(points: list[Any]) -> tuple[int, float, float] | None:
    for idx, raw in enumerate(points or []):
        pair = _to_lat_lon_pair(raw)
        if pair is None:
            continue
        lat, lon = pair
        if not _is_in_istanbul_bbox(lat, lon):
            return idx, lat, lon
    return None


def _route_radius_multipliers(points: list[tuple[float, float]]) -> list[float]:
    """
    Noktalarin yayilimina gore denenmesi gereken graf yaricap carpani listesi.
    Iki yaka gibi uzun gecislerde daha genis grafi onde dener.
    """
    import math

    base = list(ROUTE_CONFIG.get("ROUTE_GRAPH_RADIUS_MULTIPLIERS", [1.0, 2.8, 4.2]))
    if not points or len(points) < 2:
        return base

    def haversine_m(lat1, lon1, lat2, lon2):
        r = 6_371_000.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
        return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    max_dist = 0.0
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            dist = haversine_m(points[i][0], points[i][1], points[j][0], points[j][1])
            if dist > max_dist:
                max_dist = dist

    pref = float(ROUTE_CONFIG.get("ROUTE_GRAPH_PREF_MULTIPLIER", 2.8))
    force_wide_m = float(ROUTE_CONFIG.get("ROUTE_GRAPH_FORCE_WIDE_IF_MAX_DISTANCE_M", 2000.0))
    if max_dist >= force_wide_m and pref in base:
        base.remove(pref)
        base.insert(0, pref)
    return base


def _get_graph_for_points_with_multiplier(point_tuples: list[tuple[float, float]], radius_multiplier: float):
    try:
        return get_graph_for_points(point_tuples, radius_multiplier=radius_multiplier)
    except TypeError:
        # Test monkeypatch'lerinde eski imza olabilir.
        return get_graph_for_points(point_tuples)


def _collect_snap_metrics(
    G,
    point_tuples: list[tuple[float, float]],
) -> tuple[list[dict[str, float]], float]:
    infos: list[dict[str, float]] = []
    worst = 0.0
    for lat, lon in point_tuples:
        try:
            _, snap_m = find_nearest_node_with_distance(G, float(lat), float(lon))
            snap_m = float(snap_m)
        except Exception:
            # Test graphleri veya eksik OSM metadata durumunda snap analizi atlanir.
            snap_m = 0.0
        infos.append({"lat": float(lat), "lon": float(lon), "snap_m": snap_m})
        if snap_m > worst:
            worst = snap_m
    return infos, worst


def _route_index_from_type(route_type: str) -> int:
    return {"route_1": 0, "route_2": 1, "route_3": 2}.get(route_type, 0)


def _round_point_pairs(points: list[Any], digits: int = 6) -> list[list[float]]:
    rounded: list[list[float]] = []
    for raw in points or []:
        pair = _to_lat_lon_pair(raw)
        if pair is None:
            continue
        rounded.append([round(float(pair[0]), digits), round(float(pair[1]), digits)])
    return rounded


def _route_response_cache_key(
    endpoint: str,
    points: list[Any],
    optimize: bool,
    route_type: str,
) -> str:
    payload = {
        "endpoint": str(endpoint),
        "points": _round_point_pairs(points, digits=6),
        "optimize": bool(optimize),
        "route_type": str(route_type or ""),
        "config_version": _ROUTE_RESPONSE_CACHE_CONFIG_VERSION,
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _route_response_cache_get(key: str) -> dict | None:
    cached = _route_response_cache_manager.get(key)
    if cached is None or not isinstance(cached, dict):
        return None
    return dict(cached)


def _route_response_cache_put(key: str, payload: dict) -> None:
    if not isinstance(payload, dict):
        return
    _route_response_cache_manager.put(key, dict(payload))


def _unreachable_waypoints_response(payload: dict):
    details = payload.get("details") or {}
    pairs = details.get("unreachable_pairs") or []
    pair_text = ", ".join([f"[{p[0]},{p[1]}]" for p in pairs]) if pairs else "bilinmiyor"
    return jsonify({
        "error": "Nokta ciftlerinden bazilari arasinda baglanti yok.",
        "error_code": payload.get("error_code", "UNREACHABLE_WAYPOINTS"),
        "details": details,
        "message": f"Ulasilamayan waypoint ciftleri: {pair_text}",
    }), 400


def _build_primary_route_with_retries(
    point_tuples: list[tuple[float, float]],
    optimize: bool,
    route_type: str,
):
    """
    Giderek genisleyen graflarda rota dener.
    Kabul icin hem rota bulunmasi hem de snap kalitesinin esik altinda olmasi beklenir.
    """
    multipliers = _route_radius_multipliers(point_tuples)
    snap_limit_m = float(ROUTE_CONFIG.get("ROUTE_SNAP_MAX_DISTANCE_M", 900.0))
    route_index = _route_index_from_type(route_type)
    unreachable_payload = None

    best_ctx = None
    for multiplier in multipliers:
        G = _get_graph_for_points_with_multiplier(point_tuples, float(multiplier))
        _, worst_snap_m = _collect_snap_metrics(G, point_tuples)

        if optimize and len(point_tuples) > 2:
            try:
                optimized_order = solve_tsp(G, point_tuples)
            except UnreachableWaypointsError as exc:
                unreachable_payload = exc.to_payload()
                print(
                    f"[API] Route denemesi: multiplier={float(multiplier):.2f}, "
                    f"unreachable_pairs={unreachable_payload.get('details', {}).get('unreachable_pairs', [])}"
                )
                continue
        else:
            optimized_order = list(range(len(point_tuples)))
        ordered_points = [point_tuples[i] for i in optimized_order]
        route_nodes = build_alternative_routes(G, ordered_points, route_index)

        if route_nodes:
            ctx = {
                "graph": G,
                "optimized_order": optimized_order,
                "ordered_points": ordered_points,
                "route_nodes": route_nodes,
                "radius_multiplier": float(multiplier),
                "worst_snap_m": worst_snap_m,
            }
            if best_ctx is None or worst_snap_m < best_ctx["worst_snap_m"]:
                best_ctx = ctx
            if worst_snap_m <= snap_limit_m:
                print(f"[API] Route graph secildi: multiplier={float(multiplier):.2f}, worst_snap={worst_snap_m:.1f}m")
                return ctx

        print(
            f"[API] Route denemesi: multiplier={float(multiplier):.2f}, "
            f"worst_snap={worst_snap_m:.1f}m, route_found={bool(route_nodes)}"
        )

    if best_ctx is not None:
        print(
            f"[API] Route fallback secildi: multiplier={best_ctx['radius_multiplier']:.2f}, "
            f"worst_snap={best_ctx['worst_snap_m']:.1f}m (limit={snap_limit_m:.1f}m)"
        )
    if unreachable_payload is not None:
        return {"unreachable_error": unreachable_payload}
    return best_ctx


def _build_alternative_batch_with_retries(
    point_tuples: list[tuple[float, float]],
    optimize: bool,
):
    multipliers = _route_radius_multipliers(point_tuples)
    snap_limit_m = float(ROUTE_CONFIG.get("ROUTE_SNAP_MAX_DISTANCE_M", 900.0))
    unreachable_payload = None
    best_ctx = None

    for multiplier in multipliers:
        G = _get_graph_for_points_with_multiplier(point_tuples, float(multiplier))
        _, worst_snap_m = _collect_snap_metrics(G, point_tuples)

        if optimize and len(point_tuples) > 2:
            try:
                optimized_order = solve_tsp(G, point_tuples)
            except UnreachableWaypointsError as exc:
                unreachable_payload = exc.to_payload()
                print(
                    f"[API] Alt-route denemesi: multiplier={float(multiplier):.2f}, "
                    f"unreachable_pairs={unreachable_payload.get('details', {}).get('unreachable_pairs', [])}"
                )
                continue
        else:
            optimized_order = list(range(len(point_tuples)))
        ordered_points = [point_tuples[i] for i in optimized_order]

        try:
            batch_results = build_all_alternative_routes_batch(G, ordered_points)
        except Exception as e:
            print(f"[API] Alternatif rota batch hatasi (multiplier={float(multiplier):.2f}): {e}")
            batch_results = []

        if batch_results:
            ctx = {
                "graph": G,
                "optimized_order": optimized_order,
                "ordered_points": ordered_points,
                "batch_results": batch_results,
                "radius_multiplier": float(multiplier),
                "worst_snap_m": worst_snap_m,
            }
            if best_ctx is None or worst_snap_m < best_ctx["worst_snap_m"]:
                best_ctx = ctx
            if worst_snap_m <= snap_limit_m:
                print(f"[API] Alt-route graph secildi: multiplier={float(multiplier):.2f}, worst_snap={worst_snap_m:.1f}m")
                return ctx

        print(
            f"[API] Alt-route denemesi: multiplier={float(multiplier):.2f}, "
            f"worst_snap={worst_snap_m:.1f}m, alternatives={len(batch_results)}"
        )

    if best_ctx is not None:
        print(
            f"[API] Alt-route fallback secildi: multiplier={best_ctx['radius_multiplier']:.2f}, "
            f"worst_snap={best_ctx['worst_snap_m']:.1f}m (limit={snap_limit_m:.1f}m)"
        )
    if unreachable_payload is not None:
        return {"unreachable_error": unreachable_payload}
    return best_ctx


def _is_place_text_in_istanbul(place_text: Any) -> tuple[bool | None, dict[str, Any]]:
    text = str(place_text or "").strip()
    if not text:
        return None, {"status": "empty"}

    try:
        resolved = geocode(text)
    except Exception as exc:
        return None, {"status": "resolve_error", "message": str(exc)}

    if not isinstance(resolved, dict) or resolved.get("status") != "success":
        return None, {
            "status": "unresolved",
            "error_type": resolved.get("error_type") if isinstance(resolved, dict) else "unknown",
            "message": resolved.get("message") if isinstance(resolved, dict) else "Yer cozumlenemedi",
        }

    try:
        lat = float(resolved.get("lat"))
        lon = float(resolved.get("lon"))
    except (TypeError, ValueError):
        return None, {"status": "invalid_coordinates"}

    in_istanbul = _is_in_istanbul_bbox(lat, lon)
    return in_istanbul, {
        "status": "resolved",
        "lat": lat,
        "lon": lon,
        "display_name": resolved.get("display_name", text),
        "cached": bool(resolved.get("cached", False)),
    }


def _extract_nlp_places_for_scope_check(parse_result: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    intent_type = str(parse_result.get("type", "") or "").strip().lower()

    # POI sorgularinda sadece ana "location" alanini scope-check'e sok.
    # BERT'in "locations" yan adayi bazen alakasiz ilce/sehir (ornegin Kiraz/Izmir)
    # uretebiliyor ve gereksiz geofence blokuna sebep oluyor.
    if intent_type == "poi":
        raw_location = parse_result.get("location")
        if isinstance(raw_location, str) and raw_location.strip():
            candidates.append(raw_location.strip())
    else:
        for key in ("origin", "destination", "location"):
            raw = parse_result.get(key)
            if isinstance(raw, str) and raw.strip():
                candidates.append(raw.strip())

        raw_locations = parse_result.get("locations")
        if isinstance(raw_locations, list):
            for item in raw_locations:
                if isinstance(item, str) and item.strip():
                    candidates.append(item.strip())
                elif isinstance(item, dict):
                    place = item.get("place")
                    if isinstance(place, str) and place.strip():
                        candidates.append(place.strip())

    seen: set[str] = set()
    unique: list[str] = []
    for place in candidates:
        place_key = place.casefold()
        if place_key in seen:
            continue
        seen.add(place_key)
        unique.append(place)
    return unique[:4]


def _is_route_intent_query_text(query: str) -> bool:
    q = str(query or "").strip().lower()
    if not q:
        return False
    route_cues = (
        "rota", "git", "giderim", "gider", "ulas", "ulaş", "varis", "varış",
        "aktarma", "nasil giderim", "nasıl giderim", "nereden", "nereye",
    )
    if any(cue in q for cue in route_cues):
        return True
    # "x'den y'ye" benzeri yön kalıpları
    if re.search(r"\b\w+(?:'?(?:den|dan))\b.*\b\w+(?:'?(?:e|a|ye|ya))\b", q):
        return True
    return False


def _has_poi_concept_cue(query: str) -> bool:
    q = str(query or "").strip().lower()
    if not q:
        return False
    poi_cues = (
        "pastane", "kafe", "cafe", "restoran", "restaurant", "eczane", "hastane",
        "market", "avm", "otel", "müze", "muze", "kasap", "firin", "fırın", "park",
    )
    return any(c in q for c in poi_cues)


def _has_single_location_style_cue(query: str) -> bool:
    q = str(query or "").strip().lower()
    if not q:
        return False
    # "maltepede", "kadikoy'de", "besiktasta" vb.
    return bool(re.search(r"\b\w+(?:'?(?:de|da|te|ta))\b", q))


def _postprocess_nlp_result_for_poi(query: str, result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict):
        return result
    query_type = str(result.get("type", "") or "").strip().lower()
    if query_type != "route":
        return result
    if _is_route_intent_query_text(query):
        return result
    if not _has_poi_concept_cue(query):
        return result
    if not _has_single_location_style_cue(query):
        return result

    origin = result.get("origin")
    destination = result.get("destination")
    location = result.get("location")
    resolved_location = None
    for cand in (location, origin, destination):
        if isinstance(cand, str) and cand.strip():
            resolved_location = cand.strip()
            break
    if not resolved_location:
        return result

    patched = dict(result)
    patched["type"] = "poi"
    patched["location"] = resolved_location
    patched["origin"] = None
    patched["destination"] = None
    patched["locations"] = None
    patched["postprocess_note"] = "route_to_poi_single_location_guard"
    return patched


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


def _local_llm_system_prompt() -> str:
    prompt = os.getenv("LOCAL_LLM_SYSTEM_PROMPT", "").strip()
    if prompt:
        return prompt
    return (
        "Sen yardimci bir asistansin. "
        "Her zaman Turkce cevap ver. "
        "Kisa, net ve dogru ol. "
        "Yalnizca son kullanici sorusunu cevapla; onceki yanitlari tekrar etme. "
        "Kullanici selamlasma/genel sohbet yapiyorsa dogal cevap ver; konu disi bilgi uydurma. "
        "Emin olmadigin olgusal detaylarda tahmin yurutup uydurma bilgi verme; belirsizligi acikca belirt. "
        "Metni temiz UTF-8 olarak uret."
    )


def _inject_local_system_message(messages: list[dict]) -> list[dict]:
    if not isinstance(messages, list):
        return messages
    if messages and isinstance(messages[0], dict) and messages[0].get("role") == "system":
        return messages

    prompt = _local_llm_system_prompt()
    if not prompt:
        return messages
    return [{"role": "system", "content": prompt}] + messages


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


def _local_llm_max_tokens(raw_value: Any) -> int:
    default_value = _env_int("ORP_LOCAL_LLM_MAX_TOKENS_DEFAULT", 2048)
    hard_cap = _env_int("ORP_LOCAL_LLM_MAX_TOKENS_HARD_CAP", 8192)
    if hard_cap < 64:
        hard_cap = 64
    if default_value < 32:
        default_value = 32
    default_value = min(default_value, hard_cap)

    if raw_value is None:
        return default_value

    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return default_value

    if parsed < 1:
        return default_value
    return min(parsed, hard_cap)


def _local_llm_float_param(data: dict[str, Any], key: str, env_name: str, default: float) -> float:
    raw_value = data.get(key)
    if raw_value is None:
        return _env_float(env_name, default)
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return _env_float(env_name, default)


def _local_llm_int_param(data: dict[str, Any], key: str, env_name: str, default: int) -> int:
    raw_value = data.get(key)
    if raw_value is None:
        return _env_int(env_name, default)
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return _env_int(env_name, default)


_RAG_LINE_CODE_RE = re.compile(r"\b(?:m\d{1,2}[ab]?|t\d{1,2}|f\d{1,2}|mr\d?|bn\d{1,2}|34[a-z]{0,2})\b", re.IGNORECASE)


def _normalize_common_turkish_glitches(text: str) -> str:
    if not text:
        return ""
    out = str(text)
    fixes = {
        "duraklar? s?ras?yla": "duraklari sirasiyla",
        "duraklar?": "duraklari",
        "s?ras?yla": "sirasiyla",
        "?skudar": "uskudar",
        "?stanbul": "istanbul",
        "samand?ra": "samandira",
        "?mraniye": "umraniye",
        "?ekmekoy": "cekmekoy",
        "?ar?i": "carsi",
        "?ar?amba": "carsamba",
        "?": "?",
    }
    lowered = out.lower()
    for src, dst in fixes.items():
        if src in lowered:
            out = re.sub(re.escape(src), dst, out, flags=re.IGNORECASE)
            lowered = out.lower()
    return out


def _normalize_for_match(text: str) -> str:
    raw = _normalize_common_turkish_glitches(repair_text(text)).lower()
    tr_map = str.maketrans({
        "i": "i",
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
        "â": "a",
        "î": "i",
        "û": "u",
    })
    raw = raw.translate(tr_map)
    raw = re.sub(r"[^a-z0-9\s]", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


def _contains_route_relation(text: str) -> bool:
    q = _normalize_for_match(text)
    return bool(
        re.search(r"\b\w+(?:den|dan|tan|ten)\b", q)
        and re.search(r"\b\w+(?:e|a|ye|ya)\b", q)
    )


def _is_dynamic_route_request(text: str) -> bool:
    q = _normalize_for_match(text)
    if not q:
        return False
    if not _contains_route_relation(q):
        return False
    if "durak" in q or "uzerinde" in q or "hattinda" in q:
        return False
    return True


def _is_poi_request(text: str) -> bool:
    q = _normalize_for_match(text)
    poi_tokens = (
        "eczane", "kafe", "cafe", "kasap", "restoran", "restaurant", "muze",
        "market", "bakkal", "hastane", "otel", "bar", "pub",
    )
    return any(tok in q for tok in poi_tokens)


def _should_use_rag_for_query_with_reason(text: str) -> tuple[bool, str]:
    q = _normalize_for_match(text)
    if not q:
        return False, "empty_query"

    greeting_like = {
        "selam", "merhaba", "naber", "nasilsin", "iyi misin",
        "gunaydin", "iyi aksamlar", "tesekkurler", "sag ol", "tamam", "ok", "eyvallah",
    }
    if q in greeting_like:
        return False, "smalltalk_query"

    transit_keywords = (
        "rota", "durak", "hat", "metro", "metrobus", "marmaray", "vapur",
        "otobus", "tramvay", "istanbulkart", "aktarma", "sefer", "ucret",
        "dakika", "km", "yurume", "yurumek", "kalkis", "varis", "nereden",
        "nasil giderim", "nasil gider", "hangi durak", "toplu tasima", "havalimani",
    )
    poi_keywords = (
        "eczane", "kafe", "cafe", "kasap", "restoran", "restaurant", "muze", "müze",
        "bakkal", "market", "hastane", "otel", "otel", "bar", "pub",
    )

    if _RAG_LINE_CODE_RE.search(q):
        return True, "line_code_detected"
    if any(k in q for k in transit_keywords):
        return True, "transit_keyword"
    if any(k in q for k in poi_keywords):
        return True, "poi_keyword"
    if _contains_route_relation(q):
        return True, "from_to_pattern"

    non_istanbul_city_markers = (
        "ankara", "izmir", "bursa", "antalya", "adana", "konya", "kocaeli",
        "gaziantep", "trabzon", "eskisehir", "samsun", "kayseri",
    )
    if any(city in q for city in non_istanbul_city_markers):
        return False, "non_istanbul_general_query"

    return False, "non_transit_or_general_query"


def _should_use_rag_for_query(text: str) -> bool:
    return _should_use_rag_for_query_with_reason(text)[0]


def _resolve_rag_min_similarity(payload: dict[str, Any]) -> float:
    raw = payload.get("rag_min_similarity")
    if raw is None:
        raw = payload.get("min_similarity")
    if raw is None:
        raw = os.getenv("ORP_RAG_MIN_SIMILARITY", "0.43")
    try:
        val = float(raw)
    except (TypeError, ValueError):
        val = 0.43
    return max(-1.0, min(1.0, val))


def _should_fallback_from_rag(rag_result: dict[str, Any], min_similarity: float) -> tuple[bool, str]:
    count = int(rag_result.get("count") or 0)
    if count <= 0:
        return True, "empty_rag_result"
    top_sim = rag_result.get("top_similarity")
    if isinstance(top_sim, (int, float)):
        sim = float(top_sim)
        if sim < min_similarity:
            return True, f"low_similarity_fallback:{sim:.3f}<{min_similarity:.3f}"
        return False, ""
    return False, ""


def _extract_stop_names_from_text(text: str) -> list[str]:
    raw = _normalize_common_turkish_glitches(repair_text(text)).strip()
    if not raw:
        return []

    lower = raw.lower()
    marker_idx = lower.find("duraklari")
    if marker_idx < 0:
        marker_idx = lower.find("duraklar")
    if marker_idx >= 0:
        colon_idx = raw.find(":", marker_idx)
        if colon_idx >= 0:
            raw = raw[colon_idx + 1 :]

    raw = raw.replace("\n", " ").strip().rstrip(". ")
    raw = re.sub(r"\s+", " ", raw)
    if not raw:
        return []

    parts = [p.strip(" .") for p in raw.split(",")]
    out: list[str] = []
    seen: set[str] = set()
    for item in parts:
        if not item:
            continue
        item = re.sub(r"^\s*ve\s+", "", item, flags=re.IGNORECASE)
        if len(item) < 2:
            continue
        key = _normalize_for_match(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _extract_query_line_code(user_text: str) -> str:
    q = _normalize_for_match(user_text)
    m = _RAG_LINE_CODE_RE.search(q)
    return (m.group(0).upper() if m else "").strip()


def _extract_station_candidate_for_line_query(user_text: str, line_code: str) -> str:
    q = _normalize_common_turkish_glitches(repair_text(user_text))
    if not line_code:
        return ""
    m = re.search(rf"(.+?)\b{re.escape(line_code)}\b", q, flags=re.IGNORECASE)
    if not m:
        return ""
    candidate = m.group(1).strip(" ?.,:;!-")
    candidate = re.sub(r"\b(uzatmasi|uzatması|uzantisi|uzantısı|uzerinde|üzerinde|mi|mı|mu|mü)\b", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\s+", " ", candidate).strip()
    if len(candidate) < 2:
        return ""
    return candidate


def _try_direct_rag_structured_answer(user_text: str, rag_result: dict[str, Any]) -> str | None:
    qn = _normalize_for_match(user_text)
    chunks = rag_result.get("chunks", [])
    if not isinstance(chunks, list) or not chunks:
        return None

    line_code = _extract_query_line_code(user_text)

    # 1) "M5 duraklarini say" turu sorulari LLM'e birakmadan deterministic yanitla.
    if "durak" in qn and (line_code or any(tok in qn for tok in ("kac", "say", "liste"))):
        best_stops: list[str] = []
        best_line = line_code
        for ch in chunks:
            if not isinstance(ch, dict):
                continue
            meta = ch.get("meta") or {}
            text = _normalize_common_turkish_glitches(repair_text(ch.get("text")))
            rtype = str(ch.get("record_type") or meta.get("record_type") or "").strip().upper()
            line_meta = str(meta.get("hat_kodlari") or meta.get("hat_kodu") or "").upper()
            if line_code and line_code not in line_meta and line_code not in text.upper():
                continue
            if rtype and "DURAK" not in rtype and "HAT" not in rtype:
                continue
            stops = _extract_stop_names_from_text(text)
            if len(stops) > len(best_stops):
                best_stops = stops
                if line_meta:
                    best_line = line_meta.split(",")[0].strip()
        if best_stops:
            header = f"{best_line} hattinda toplam {len(best_stops)} durak var." if best_line else f"Toplam {len(best_stops)} durak var."
            body = "\n".join(f"{idx}. {name}" for idx, name in enumerate(best_stops, start=1))
            return f"{header}\n\n{body}"
        if line_code:
            return f"{line_code} icin baglamda net durak listesi bulunamadi. Uydurma bilgi vermemek icin kesin sayi paylasmiyorum."

    # 2) "Samandira Merkez M5 uzerinde mi?" turu sorular.
    if line_code and re.search(r"(uzerinde|zerinde|hattinda)\s*(mi|mi\?)?", qn):
        station = _extract_station_candidate_for_line_query(user_text, line_code)
        if station:
            station_norm = _normalize_for_match(station)
            best_stops: list[str] = []
            for ch in chunks:
                if not isinstance(ch, dict):
                    continue
                text = _normalize_common_turkish_glitches(repair_text(ch.get("text")))
                stops = _extract_stop_names_from_text(text)
                if len(stops) > len(best_stops):
                    best_stops = stops
            if best_stops:
                stop_norms = {_normalize_for_match(s) for s in best_stops}
                if station_norm in stop_norms:
                    return f"Evet, {station} {line_code} hattinin duraklari arasindadir."
                station_compact = station_norm.replace(" ", "")
                for stop_norm in stop_norms:
                    stop_compact = stop_norm.replace(" ", "")
                    if station_compact in stop_compact or stop_compact in station_compact:
                        return f"Evet, {station} {line_code} hattinin duraklari arasindadir."
                    if difflib.SequenceMatcher(a=station_compact, b=stop_compact).ratio() >= 0.86:
                        return f"Evet, {station} {line_code} hattinin duraklari arasindadir."
                return f"Hayir, {station} {line_code} durak listesinde gorunmuyor."

    # 3) "X hangi metro hattinda?" sorulari.
    if "hangi metro hatt" in qn or "hangi hat" in qn:
        codes: list[str] = []
        for ch in chunks:
            if not isinstance(ch, dict):
                continue
            meta = ch.get("meta") or {}
            hats = str(meta.get("hat_kodlari") or meta.get("hat_kodu") or "")
            for piece in hats.split(","):
                c = piece.strip().upper()
                if c and c not in codes:
                    codes.append(c)
            text_codes = _RAG_LINE_CODE_RE.findall(str(ch.get("text") or ""))
            for c in text_codes:
                cc = str(c).upper().strip()
                if cc and cc not in codes:
                    codes.append(cc)
        if line_code:
            return f"Bu soru icin baglamdaki hat kodu: {line_code}."
        if codes:
            return f"Bu soru icin baglamdaki en ilgili hat: {codes[0]}."

    return None


_RAG_EXTRACTIVE_STOPWORDS = {
    "ve", "ile", "icin", "için", "ama", "fakat", "gibi", "olan", "olarak",
    "nedir", "nasil", "nasil", "nerede", "hangi", "kac", "kaç", "midir",
    "midir", "mi", "mu", "mü", "mı", "veya", "sadece", "lütfen", "lutfen",
    "istanbul", "hakkinda", "hattinda", "uzerinde", "sorusu", "soru",
}


def _split_text_sentences(text: str) -> list[str]:
    raw = _normalize_common_turkish_glitches(repair_text(text))
    if not raw:
        return []
    raw = raw.replace("\r", "\n")
    parts = re.split(r"[.!?\n;]+", raw)
    out: list[str] = []
    for p in parts:
        s = re.sub(r"\s+", " ", p).strip(" -\t")
        if len(s) < 12:
            continue
        out.append(s)
    return out


def _query_tokens_for_extractive(user_text: str) -> list[str]:
    qn = _normalize_for_match(user_text)
    tokens = re.findall(r"[a-z0-9]+", qn)
    out = [t for t in tokens if len(t) >= 3 and t not in _RAG_EXTRACTIVE_STOPWORDS]
    # sirayi koru, tekrarli tokenleri ele
    seen: set[str] = set()
    uniq: list[str] = []
    for t in out:
        if t in seen:
            continue
        seen.add(t)
        uniq.append(t)
    return uniq


def _build_extractive_rag_answer(user_text: str, rag_result: dict[str, Any], *, max_sentences: int = 4) -> str:
    chunks = rag_result.get("chunks", [])
    if not isinstance(chunks, list) or not chunks:
        return "Baglamda ilgili kayit bulunamadi."

    q_tokens = _query_tokens_for_extractive(user_text)
    line_code = _extract_query_line_code(user_text)
    qn = _normalize_for_match(user_text)

    must_have_tokens: list[str] = []
    for tok in ("istanbulkart", "eczane", "havalimani", "marmaray", "metrobus", "vapur", "tramvay"):
        if tok in qn:
            must_have_tokens.append(tok)

    candidates: list[tuple[float, str]] = []
    for ch in chunks:
        if not isinstance(ch, dict):
            continue
        text = str(ch.get("text") or "")
        for sent in _split_text_sentences(text):
            sn = _normalize_for_match(sent)
            if not sn:
                continue
            s_tokens = set(re.findall(r"[a-z0-9]+", sn))
            if not s_tokens:
                continue
            if must_have_tokens and not any(mt in sn for mt in must_have_tokens):
                continue
            overlap = 0
            if q_tokens:
                overlap = sum(1 for t in q_tokens if t in s_tokens)
            score = float(overlap)
            if line_code and line_code.lower() in sn:
                score += 1.5
            if "durak" in _normalize_for_match(user_text) and "durak" in sn:
                score += 1.0
            if score <= 0:
                continue
            candidates.append((score, sent.strip()))

    if not candidates:
        return "Baglamda bu soruyu dogrudan yanitlayacak acik bilgi yok."

    candidates.sort(key=lambda x: x[0], reverse=True)
    picked: list[str] = []
    seen_norm: set[str] = set()
    for _, sent in candidates:
        norm = _normalize_for_match(sent)
        if norm in seen_norm:
            continue
        seen_norm.add(norm)
        picked.append(sent)
        if len(picked) >= max_sentences:
            break

    if not picked:
        return "Baglamda bu soruyu dogrudan yanitlayacak acik bilgi yok."

    lines = [f"{idx}. {p}" for idx, p in enumerate(picked, start=1)]
    return "Baglamdan dogrudan bulunan bilgiler:\n" + "\n".join(lines)


def _is_rag_context_relevant(user_text: str, rag_context: str) -> bool:
    q = _normalize_for_match(user_text)
    c = _normalize_for_match(rag_context)
    if not q or not c:
        return False
    if "istanbulkart" in q and "istanbulkart" not in c and "istanbul kart" not in c:
        return False

    tokens = re.findall(r"[a-z0-9]+", q)
    stop = {
        "icin", "neden", "nasil", "mi", "mi", "mu", "ve", "ile", "bir", "olan",
        "olur", "olabilir", "mantikli", "gezebilir", "yurumek", "gitmek", "nedir",
    }
    keys = [t for t in tokens if len(t) >= 4 and t not in stop]
    if not keys:
        return True
    hit = sum(1 for k in keys if k in c)
    ratio = hit / max(1, len(keys))
    return ratio >= 0.20


def _local_llm_generation_options(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "temperature": _local_llm_float_param(data, "temperature", "ORP_LOCAL_LLM_TEMPERATURE_DEFAULT", 0.8),
        "max_tokens": _local_llm_max_tokens(data.get("max_tokens")),
        "top_p": _local_llm_float_param(data, "top_p", "ORP_LOCAL_LLM_TOP_P_DEFAULT", 0.95),
        "top_k": _local_llm_int_param(data, "top_k", "ORP_LOCAL_LLM_TOP_K_DEFAULT", 40),
        "min_p": _local_llm_float_param(data, "min_p", "ORP_LOCAL_LLM_MIN_P_DEFAULT", 0.05),
        "repeat_penalty": _local_llm_float_param(
            data,
            "repeat_penalty",
            "ORP_LOCAL_LLM_REPEAT_PENALTY_DEFAULT",
            1.1,
        ),
    }


def _is_repetition_loop(text: str) -> bool:
    if not text:
        return False
    normalized = re.sub(r"\s+", " ", str(text).lower()).strip()
    if len(normalized) < 180:
        return False

    words = normalized.split(" ")
    if len(words) >= 40:
        unique_ratio = len(set(words)) / max(1, len(words))
        if unique_ratio < 0.24:
            return True

    if len(words) >= 24:
        tail = words[-24:]
        half = len(tail) // 2
        if tail[:half] == tail[half:]:
            return True

    sentences = [s.strip() for s in re.split(r"[.!?]+", normalized) if s.strip()]
    if len(sentences) >= 3 and sentences[-1] == sentences[-2] == sentences[-3]:
        return True

    return False


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
    elif prov == "local":
        st = local_llm_status()
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
    Console stream buffering'i azaltÃır ve print'i anlÃık flush edecek Ã…şekilde ayarlar.
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
    find_nearest_node_with_distance,
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
    UnreachableWaypointsError,
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
from cache_manager import (
    get_graph_cache,
    get_poi_cache,
    get_route_response_cache,
    get_all_cache_stats,
    evaluate_cache_policy,
)
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

try:
    from local_llm_service import (
        is_local_llm_configured,
        local_llm_status,
        local_llm_list_models,
        local_llm_chat_completion,
        local_llm_chat_completion_with_fallback,
        local_llm_chat_completion_stream,
    )
    LOCAL_LLM_SERVICE_AVAILABLE = True
except ImportError:
    LOCAL_LLM_SERVICE_AVAILABLE = False

try:
    from rag_service import (
        is_rag_available,
        rag_status,
        rag_list_collections,
        rag_query,
    )
    RAG_SERVICE_AVAILABLE = True
except ImportError:
    RAG_SERVICE_AVAILABLE = False

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
    print("[app.py] Hava durumu servisi yuklendi")
except ImportError as e:
    WEATHER_SERVICE_AVAILABLE = False
    print(f"[app.py] Hava durumu servisi bulunamadi: {str(e)} [WARN]")

# BERT NLP Engine (opsiyonel - kurulu degilse regex fallback kullanilir)
try:
    from bert_nlp_engine import get_bert_nlp_engine, is_bert_available
    BERT_NLP_AVAILABLE = is_bert_available()
    _BERT_NLP_ERROR = None
    if BERT_NLP_AVAILABLE:
        print("[app.py] BERT NLP Engine yuklendi")
    else:
        print("[app.py] BERT NLP Engine bulunamadi, regex fallback aktif [WARN]")
except ImportError as e:
    BERT_NLP_AVAILABLE = False
    _BERT_NLP_ERROR = str(e)
    print("[app.py] BERT NLP Engine modulu bulunamadi, regex fallback aktif [WARN]")

# Frontend klasÃƒörÃƒünÃƒün yolu
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)  # Frontend'den gelen isteklere izin ver
Compress(app)  # gzip compression aktif et - %60-70 bandwidth tasarrufu

# BERT Ãƒön-yÃƒükleme (opsiyonel). ENV: ORP_BERT_PRELOAD_ON_STARTUP=1
_PRELOAD_BERT_ON_STARTUP = _env_flag("ORP_BERT_PRELOAD_ON_STARTUP", False)

def _preload_bert_async(force: bool = False) -> None:
    """Arka planda BERT NLP engine'i yukler (lazy warm-up).

    Args:
        force: True ise ORP_BERT_PRELOAD_ON_STARTUP kontrolu atlanir ve yukleme baslatilir.
    """
    if not force and not _PRELOAD_BERT_ON_STARTUP:
        return

    def _target():
        try:
            print("[app.py] Baslatiliyor: BERT warmup (background)...")
            # import burada yapilir; hata olursa uygulama calismaya devam eder
            from bert_nlp_engine import get_bert_nlp_engine
            get_bert_nlp_engine()
            print("[app.py] BERT warmup tamamlandi")
        except Exception as exc:
            print(f"[app.py] BERT warmup hatasi: {exc}")

    t = threading.Thread(target=_target, daemon=True)
    t.start()

# Eger ORP_BERT_PRELOAD_ON_STARTUP set ise arka planda baslat
_preload_bert_async()

# Global degiskenler: LRU cache manager
_graph_cache_manager = get_graph_cache()
_poi_cache_manager = get_poi_cache()
_route_response_cache_manager = get_route_response_cache()
_runtime_initialized = False
_graph_preload_initialized = False
_last_bert_metrics_log_ts = 0.0

# BERT donanÃım metrik loglarÃı:
# ORP_BERT_LOG_METRICS=1/0
# ORP_BERT_METRICS_INTERVAL_SEC=float (default 0.5s)
_BERT_METRICS_LOG_ENABLED = _env_flag("ORP_BERT_LOG_METRICS", True)
_BERT_METRICS_INTERVAL_SEC = max(0.0, _env_float("ORP_BERT_METRICS_INTERVAL_SEC", 0.5))
_PRELOAD_POPULAR_REGIONS_ON_STARTUP = _env_flag("ORP_PRELOAD_POPULAR_REGIONS_ON_STARTUP", True)
_BERT_PARSE_TRACE_LOG_ENABLED = _env_flag("ORP_BERT_PARSE_TRACE", False)
_ROUTE_RESPONSE_CACHE_CONFIG_VERSION = (
    os.getenv("ROUTE_RESPONSE_CACHE_CONFIG_VERSION")
    or os.getenv("ORP_ROUTE_RESPONSE_CACHE_CONFIG_VERSION")
    or str(ROUTE_CONFIG.get("ROUTE_RESPONSE_CACHE_CONFIG_VERSION", "v1"))
).strip() or "v1"
_NLP_PARSE_MAX_CONCURRENCY = max(1, _env_int("ORP_NLP_PARSE_MAX_CONCURRENCY", 2))
_NLP_PARSE_SEMAPHORE = threading.BoundedSemaphore(_NLP_PARSE_MAX_CONCURRENCY)
_NLP_QUEUE_TIMEOUT_SEC = max(
    0.1,
    _env_float(
        "NLP_QUEUE_TIMEOUT_SEC",
        _env_float(
            "ORP_NLP_QUEUE_TIMEOUT_SEC",
            float(ROUTE_CONFIG.get("NLP_QUEUE_TIMEOUT_SEC", 20)),
        ),
    ),
)
_MULTIMODAL_COMPARE_MAX_CONCURRENCY = max(
    1,
    _env_int(
        "ORP_MULTIMODAL_COMPARE_MAX_CONCURRENCY",
        int(ROUTE_CONFIG.get("MULTIMODAL_COMPARE_MAX_CONCURRENCY", 2)),
    ),
)
_MULTIMODAL_COMPARE_SEMAPHORE = threading.BoundedSemaphore(_MULTIMODAL_COMPARE_MAX_CONCURRENCY)
_MULTIMODAL_QUEUE_TIMEOUT_SEC = max(
    0.1,
    _env_float(
        "MULTIMODAL_QUEUE_TIMEOUT_SEC",
        _env_float(
            "ORP_MULTIMODAL_QUEUE_TIMEOUT_SEC",
            float(ROUTE_CONFIG.get("MULTIMODAL_QUEUE_TIMEOUT_SEC", 25)),
        ),
    ),
)
_QUEUE_STATS_LOCK = threading.Lock()
_NLP_QUEUE_TIMEOUT_COUNT = 0
_MULTIMODAL_QUEUE_TIMEOUT_COUNT = 0

# POI resolver/caching version pinleri
_POI_DICT_VERSION = os.getenv("ORP_POI_DICT_VERSION", "dict-v1").strip() or "dict-v1"
_POI_THRESHOLD_PROFILE = os.getenv("ORP_POI_THRESHOLD_PROFILE", "default").strip() or "default"
_POI_PLAN_VERSION = os.getenv("ORP_POI_PLAN_VERSION", "phase2").strip() or "phase2"
_TRACE_RETENTION_DAYS = int(os.getenv("ORP_TRACE_RETENTION_DAYS", "14") or 14)


def _poi_version_token() -> str:
    return f"dict:{_POI_DICT_VERSION}|thr:{_POI_THRESHOLD_PROFILE}|plan:{_POI_PLAN_VERSION}"


def _increment_queue_timeout_counter(kind: str) -> None:
    global _NLP_QUEUE_TIMEOUT_COUNT, _MULTIMODAL_QUEUE_TIMEOUT_COUNT
    with _QUEUE_STATS_LOCK:
        if kind == "nlp":
            _NLP_QUEUE_TIMEOUT_COUNT += 1
        elif kind == "multimodal":
            _MULTIMODAL_QUEUE_TIMEOUT_COUNT += 1


def _semaphore_snapshot(limit: int, semaphore: threading.BoundedSemaphore) -> dict[str, int | None]:
    available = getattr(semaphore, "_value", None)
    if isinstance(available, int):
        inflight = max(0, int(limit) - int(available))
        return {"limit": int(limit), "inflight": inflight, "available": int(available)}
    return {"limit": int(limit), "inflight": None, "available": None}


def _queue_stats_payload() -> dict:
    with _QUEUE_STATS_LOCK:
        nlp_timeout_count = int(_NLP_QUEUE_TIMEOUT_COUNT)
        multimodal_timeout_count = int(_MULTIMODAL_QUEUE_TIMEOUT_COUNT)

    return {
        "nlp": {
            **_semaphore_snapshot(_NLP_PARSE_MAX_CONCURRENCY, _NLP_PARSE_SEMAPHORE),
            "timeout_sec": float(_NLP_QUEUE_TIMEOUT_SEC),
            "timeouts": nlp_timeout_count,
        },
        "multimodal": {
            **_semaphore_snapshot(_MULTIMODAL_COMPARE_MAX_CONCURRENCY, _MULTIMODAL_COMPARE_SEMAPHORE),
            "timeout_sec": float(_MULTIMODAL_QUEUE_TIMEOUT_SEC),
            "timeouts": multimodal_timeout_count,
        },
    }


def _should_log_bert_metrics(force: bool = False) -> bool:
    """BERT metrik loglarÃınÃın hÃızÃınÃı sÃınÃırlar."""
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
    BERT runtime donanÃım kullanÃımÃınÃı loglar.
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
    Graf objesini LRU cache'te alÃır (uygulama iÃƒçi).
    Ãƒ "nce preload kontrolÃƒü yapar, sonra LRU cache'e bakar, en son disk'ten okur.
    """
    # Ãƒ "nce LRU cache'ten kontrol et
    graph = _graph_cache_manager.get(place_name)
    if graph is not None:
        return graph

    # Disk'ten yÃƒükle ve cache'e ekle
    graph = get_graph(place_name)
    _graph_cache_manager.put(place_name, graph)
    return graph


def _redact_pii_text(value: str) -> str:
    """Loglarda temel PII redaction uygular (telefon/e-posta/sayÃısal kimlik)."""
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
    """Runtime'da BERT kullanÃılamaz hale geldiÃşinde fallback moduna geÃƒç."""
    global BERT_NLP_AVAILABLE, _BERT_NLP_ERROR
    BERT_NLP_AVAILABLE = False
    _BERT_NLP_ERROR = str(exc)
    print(f"[NLP WARN] BERT devre dÃıÃ…şÃı bÃırakÃıldÃı: {_BERT_NLP_ERROR}")


def _build_regex_fallback_result(query: str) -> dict:
    """Regex parser sonucunu BERT endpoint sÃƒözleÃ…şmesine uyarlar."""
    result = regex_parse_query(query)
    result["detected_places"] = result.get("detected_places", [])
    result["parse_time"] = float(result.get("parse_time", 0.0) or 0.0)
    result["engine"] = "regex-fallback"
    return result



@app.route("/api/get-route", methods=["POST"])
def api_get_route():
    """
    Koordinat listesi alÃır, optimize edilmiÃ…ş rota dÃƒöner.
    
    Request Body:
        {
            "points": [[lat, lon], [lat, lon], ...],
            "place": "Kadikoy, Istanbul, Turkey"  (opsiyonel, varsayÃılan KadÃıkÃƒöy),
            "route_type": "route_1" | "route_2" | "route_3"  (opsiyonel, varsayÃılan route_1)
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
        # Bu endpoint yaya rota omurgasini verir.
        # Akis: request dogrulama -> Istanbul geofence -> cache kontrolu ->
        # graph/rota hesaplama -> koordinat+istatistik cevap.
        data = request.get_json(silent=True)

        if not data or "points" not in data:
            return jsonify({"error": "GeÃƒçersiz istek: 'points' alanÃı gerekli."}), 400

        points = data["points"]
        optimize = data.get("optimize", False)  # VarsayÃılan: sÃıralÃı baÃşla
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
                return jsonify({"error": f"Nokta {i} geÃƒçersiz format. [lat, lon] olmalÃı."}), 400
            try:
                float(p[0])
                float(p[1])
            except (ValueError, TypeError):
                return jsonify({"error": f"Nokta {i} geÃƒçersiz koordinat."}), 400

        # Geofence zorunlu: uygulama Istanbul disi rotalari bilincli olarak reddeder.
        outside_point = _first_outside_point(points)
        if outside_point is not None:
            idx, lat, lon = outside_point
            return _outside_istanbul_response(
                detail=f"points[{idx}] koordinati Istanbul disinda: ({lat:.6f}, {lon:.6f})",
                field="points",
            )

        # Tekrarlanan istekleri hizlandirmak icin response seviyesinde cache kullanilir.
        route_cache_key = _route_response_cache_key(
            endpoint="/api/get-route",
            points=points,
            optimize=bool(optimize),
            route_type=str(route_type),
        )
        cached_response = _route_response_cache_get(route_cache_key)
        if cached_response is not None:
            cached_response["cache_hit"] = True
            return jsonify(cached_response)

        # Asil rota uretimi burada: retry/fallback politikasi
        # _build_primary_route_with_retries icerisinde yonetilir.
        point_tuples = [(float(p[0]), float(p[1])) for p in points]
        route_ctx = _build_primary_route_with_retries(point_tuples, bool(optimize), route_type)
        if isinstance(route_ctx, dict) and route_ctx.get("unreachable_error"):
            return _unreachable_waypoints_response(route_ctx["unreachable_error"])
        if not route_ctx:
            return jsonify({"error": "Rota hesaplanamadi. Noktalar icin uygun yol bulunamadi."}), 400

        G = route_ctx["graph"]
        optimized_order = route_ctx["optimized_order"]
        ordered_points = route_ctx["ordered_points"]
        route_nodes = route_ctx["route_nodes"]

        if not route_nodes:
            return jsonify({"error": "Rota hesaplanamadÃı. Noktalar harita alanÃı dÃıÃ…şÃında olabilir."}), 400

        # Node ID listesini cizim icin [lat, lon] akisina cevir.
        route_coords = nodes_to_coords(G, route_nodes)

        # 6) Ãİstatistikler
        stats = calculate_route_stats(G, route_nodes)

        # 7) Google Maps linki
        maps_link = generate_google_maps_link(ordered_points)

        response = {
            "optimized_order": optimized_order,
            "route_coords": route_coords,
            "total_distance_km": stats["total_distance_km"],
            "estimated_walk_minutes": stats["estimated_walk_minutes"],
            "estimated_route_minutes": stats["estimated_walk_minutes"],
            "google_maps_link": maps_link,
            "route_type": route_type,
            "cache_hit": False,
        }

        _route_response_cache_put(route_cache_key, response)
        print(f"[API] Rota tamamlandi: {stats['total_distance_km']}km, {stats['estimated_walk_minutes']}dk")
        return jsonify(response)

    except Exception as e:
        print(f"[API] Hata: {e}")
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/api/get-route-steps", methods=["POST"])
def api_get_route_steps():
    """
    Verilen noktalar iÃƒçin adÃım adÃım yÃƒönlendirme (basitleÃ…ştirilmiÃ…ş).

    Request Body:
        { "points": [[lat, lon], ...], "optimize": true/false, "route_type": "route_1" }

    Response:
        { "steps": [{"instruction": str, "distance_m": int, "duration_min": int}, ...] }
    """
    try:
        data = request.get_json(silent=True)
        if not data or 'points' not in data:
            return jsonify({"error": "'points' alanÃı gerekli."}), 400

        points = data['points']
        optimize = bool(data.get('optimize', False))
        route_type = data.get('route_type', 'route_1')

        if not isinstance(points, list) or len(points) < 2:
            return jsonify({"error": "En az 2 nokta gerekli."}), 400

        for i, p in enumerate(points):
            if _to_lat_lon_pair(p) is None:
                return jsonify({"error": f"Nokta {i} gecersiz format. [lat, lon] olmali."}), 400

        outside_point = _first_outside_point(points)
        if outside_point is not None:
            idx, lat, lon = outside_point
            return _outside_istanbul_response(
                detail=f"points[{idx}] koordinati Istanbul disinda: ({lat:.6f}, {lon:.6f})",
                field="points",
            )

        route_cache_key = _route_response_cache_key(
            endpoint="/api/get-route-steps",
            points=points,
            optimize=bool(optimize),
            route_type=str(route_type),
        )
        cached_response = _route_response_cache_get(route_cache_key)
        if cached_response is not None:
            cached_response["cache_hit"] = True
            return jsonify(cached_response)

        point_tuples = [(float(p[0]), float(p[1])) for p in points]
        route_ctx = _build_primary_route_with_retries(point_tuples, bool(optimize), route_type)
        if isinstance(route_ctx, dict) and route_ctx.get("unreachable_error"):
            return _unreachable_waypoints_response(route_ctx["unreachable_error"])
        if not route_ctx:
            return jsonify({"error": "Rota hesaplanamadi."}), 400

        G = route_ctx["graph"]
        optimized_order = route_ctx["optimized_order"]
        ordered_points = route_ctx["ordered_points"]
        route_nodes = route_ctx["route_nodes"]

        if not route_nodes:
            return jsonify({"error": "Rota hesaplanamadÃı."}), 400

        # Step extractor: yol ismi/junction bilgisinden UI uyumlu adimlar uret.
        def build_turn_by_turn_steps(G, nodes):
            steps = []
            if not nodes or len(nodes) < 2:
                return steps

            current_name = None
            current_dist = 0.0
            current_coords = []
            cumulative_dist = 0.0
            current_junction = None

            def get_node_coords(node_id):
                node_data = G.nodes.get(node_id) or {}
                if "y" in node_data and "x" in node_data:
                    return [float(node_data["y"]), float(node_data["x"])]
                return [0.0, 0.0]

            for i in range(len(nodes) - 1):
                u = nodes[i]
                v = nodes[i + 1]

                if i == 0:
                    current_coords.append(get_node_coords(u))
                current_coords.append(get_node_coords(v))

                edge_data = G.get_edge_data(u, v) or {}
                best = None
                if edge_data:
                    try:
                        best = min(edge_data.values(), key=lambda d: d.get("length", float("inf")))
                    except Exception:
                        best = list(edge_data.values())[0]

                length = 0.0
                name = None
                junction = None
                if best:
                    length = float(best.get("length", 0) or 0)
                    name = best.get("name") or best.get("ref") or best.get("highway")
                    junction = best.get("junction")

                if not name:
                    name = "yol"

                if current_name is None:
                    current_name = name
                    current_dist = length
                    current_junction = junction
                elif name == current_name:
                    current_dist += length
                    if junction:
                        current_junction = junction
                else:
                    minutes = round((current_dist / 1000) / float(ROUTE_CONFIG.get("WALK_SPEED_KMH", 5.0)) * 60)
                    duration_s = int(minutes * 60)
                    cumulative_dist += current_dist
                    turn_type = "roundabout" if current_junction == "roundabout" else "straight"
                    instr = f"{int(round(current_dist))} metre boyunca {current_name} uzerinde ilerleyin."
                    if turn_type == "roundabout":
                        instr = f"Kavsaktan gecerek {current_name} uzerinde ilerleyin."

                    steps.append({
                        "step_id": len(steps) + 1,
                        "instruction": instr,
                        "distance_m": int(round(current_dist)),
                        "duration_s": duration_s,
                        "duration_min": minutes,
                        "street_name": current_name,
                        "turn_type": turn_type,
                        "coords": list(current_coords[:-1]),
                        "cumulative_distance_m": int(round(cumulative_dist)),
                    })

                    current_name = name
                    current_dist = length
                    current_junction = junction
                    current_coords = [get_node_coords(u), get_node_coords(v)]

            if current_name is not None:
                minutes = round((current_dist / 1000) / float(ROUTE_CONFIG.get("WALK_SPEED_KMH", 5.0)) * 60)
                duration_s = int(minutes * 60)
                cumulative_dist += current_dist
                turn_type = "roundabout" if current_junction == "roundabout" else "straight"
                instr = f"{int(round(current_dist))} metre boyunca {current_name} uzerinde ilerleyin."
                if turn_type == "roundabout":
                    instr = f"Kavsaktan gecerek {current_name} uzerinde ilerleyin."

                steps.append({
                    "step_id": len(steps) + 1,
                    "instruction": instr,
                    "distance_m": int(round(current_dist)),
                    "duration_s": duration_s,
                    "duration_min": minutes,
                    "street_name": current_name,
                    "turn_type": turn_type,
                    "coords": list(current_coords),
                    "cumulative_distance_m": int(round(cumulative_dist)),
                })

            return steps

        steps = build_turn_by_turn_steps(G, route_nodes)
        response = {
            "steps": steps,
            "route_coords": nodes_to_coords(G, route_nodes),
            "cache_hit": False,
        }
        _route_response_cache_put(route_cache_key, response)
        return jsonify(response)

    except Exception as e:
        print(f"[API] get-route-steps hata: {e}")
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500



@app.route("/api/get-alternative-routes", methods=["POST"])
def api_get_alternative_routes():
    """
    AynÃı noktalar iÃƒçin 3 farklÃı alternatif rota dÃƒöner.

    Basit sistem:
    - 3 rota: "Rota 1", "Rota 2", "Rota 3"
    - Hepsi kÃısa rotaya yakÃın mesafede
    - Geometrik olarak farklÃı sokaklardan geÃƒçer

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
        # Bu endpoint ayni giris noktasi icin birden fazla geometri
        # alternatifi dondurur; amac UI'da rota karsilastirmasini acmak.
        data = request.get_json(silent=True)

        if not data or "points" not in data:
            return jsonify({"error": "GeÃƒçersiz istek: 'points' alanÃı gerekli."}), 400

        points = data["points"]
        optimize = data.get("optimize", False)
        route_type = data.get("route_type", "")

        print(f"[API] Get-alternative-routes: {len(points)} nokta, optimize={optimize}")

        # Validasyon
        if not isinstance(points, list) or len(points) < 2:
            return jsonify({"error": "En az 2 nokta gereklidir."}), 400

        for i, p in enumerate(points):
            if _to_lat_lon_pair(p) is None:
                return jsonify({"error": f"Nokta {i} gecersiz format. [lat, lon] olmali."}), 400

        outside_point = _first_outside_point(points)
        if outside_point is not None:
            idx, lat, lon = outside_point
            return _outside_istanbul_response(
                detail=f"points[{idx}] koordinati Istanbul disinda: ({lat:.6f}, {lon:.6f})",
                field="points",
            )

        # Alternatif rota da cache'lenir; ayni noktalarda tekrar hesaplama azaltilir.
        route_cache_key = _route_response_cache_key(
            endpoint="/api/get-alternative-routes",
            points=points,
            optimize=bool(optimize),
            route_type=str(route_type),
        )
        cached_response = _route_response_cache_get(route_cache_key)
        if cached_response is not None:
            cached_response["cache_hit"] = True
            return jsonify(cached_response)

        # Batch alternatif hesaplama segment bazli calisir
        # (her segmentte birden fazla rota adayi uretilir).
        point_tuples = [(float(p[0]), float(p[1])) for p in points]
        alt_ctx = _build_alternative_batch_with_retries(point_tuples, bool(optimize))
        if isinstance(alt_ctx, dict) and alt_ctx.get("unreachable_error"):
            return _unreachable_waypoints_response(alt_ctx["unreachable_error"])
        if not alt_ctx:
            return jsonify({"error": "Hicbir alternatif rota hesaplanamadi."}), 400

        G = alt_ctx["graph"]
        optimized_order = alt_ctx["optimized_order"]
        ordered_points = alt_ctx["ordered_points"]
        batch_results = alt_ctx["batch_results"]

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
            return jsonify({"error": "HiÃƒçbir alternatif rota hesaplanamadÃı."}), 400

        # UI'da kopya kartlari engellemek icin geometri bazli dedup uygulanir.
        # Esik degeri rota uzunluguna gore dinamik tutulur.
        def _coords_equal(a, b, distance_km: float):
            if len(a) != len(b):
                return False
            min_eps = float(ROUTE_CONFIG.get("ALT_ROUTE_DEDUP_EPSILON_MIN_DEG", 1e-6))
            max_eps = float(ROUTE_CONFIG.get("ALT_ROUTE_DEDUP_EPSILON_MAX_DEG", 2.5e-5))
            eps = min(max_eps, min_eps * (1.0 + max(float(distance_km), 0.0)))
            for i in range(len(a)):
                if abs(a[i][0] - b[i][0]) > eps or abs(a[i][1] - b[i][1]) > eps:
                    return False
            return True

        unique = []
        for alt in alternatives:
            max_distance_km = max(float(alt.get("distance_km", 0.0) or 0.0), 0.0)
            if not any(
                _coords_equal(
                    alt["route_coords"],
                    u["route_coords"],
                    max(max_distance_km, float(u.get("distance_km", 0.0) or 0.0)),
                )
                for u in unique
            ):
                unique.append(alt)

        response = {
            "alternatives": unique,
            "cache_hit": False,
        }
        _route_response_cache_put(route_cache_key, response)
        print(f"[API] {len(unique)} alternatif rota")
        return jsonify(response)

    except Exception as e:
        print(f"[API] Hata: {e}")
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/api/search-pois", methods=["POST"])
def api_search_pois():
    """
    Belirtilen bÃƒölgede POI arar.
    
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
        # POI akisi:
        # 1) kategori ve bolge dogrulama
        # 2) Istanbul geofence
        # 3) search_mode'a gore boundary veya auto stratejisi
        # 4) cache + canli sorgu
        data = request.get_json(silent=True)

        if not data or "category" not in data:
            return jsonify({"error": "'category' alanÃı gerekli."}), 400

        place = data.get("place", "Kadikoy, Istanbul, Turkey")
        raw_category = data["category"]
        place_in_istanbul, place_geofence_meta = _is_place_text_in_istanbul(place)
        if place_in_istanbul is False:
            return _outside_istanbul_response(
                detail=f"POI aramasi Istanbul disinda bir konumu hedefliyor: {place_geofence_meta.get('display_name', place)}",
                field="place",
            )
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

        # Il/ilce seviyesinde belirsiz "yakina gore" arama yerine
        # idari sinir (place boundary) stratejisini zorlariz.
        if search_mode == "auto" and isinstance(place, str):
            place_parts = [p.strip() for p in place.split(",") if p.strip()]
            place_tail = place_parts[-1].lower() if place_parts else ""
            is_city_level = (
                len(place_parts) == 1
                or (len(place_parts) == 2 and place_tail in {"turkey", "turkiye", "tÃƒürkiye"})
            )
            is_district_level = (
                len(place_parts) == 3 and place_tail in {"turkey", "turkiye", "tÃƒürkiye"}
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

        # Validasyon: ASCII serbest, TÃƒürkÃƒçe sÃƒözlÃƒükten canonicalize edilen ifadeler de serbest.
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
            "place_geofence": place_geofence_meta,
            "version_profile": {
                "dict_version": _POI_DICT_VERSION,
                "threshold_profile": _POI_THRESHOLD_PROFILE,
                "plan_version": _POI_PLAN_VERSION,
                "cache_token": cache_version_token,
            },
        })

    except Exception as e:
        # print(f"[API] POI arama hatasÃı: {e}"))
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """Sunucu saÃşlÃık kontrolÃƒü."""
    return jsonify({"status": "ok", "message": "OpenTrip API ÃƒçalÃıÃ…şÃıyor!"})


@app.route("/api/cache/stats", methods=["GET"])
def api_cache_stats():
    """Graph/POI ve multimodal compare cache istatistiklerini dondurur."""
    try:
        payload = get_all_cache_stats()
        if _multimodal_available:
            payload["multimodal_compare"] = multimodal_compare_cache_stats()
            payload["multimodal_transit_lookup"] = multimodal_transit_lookup_cache_stats()
            payload["multimodal_segment_cache"] = multimodal_segment_cache_stats()
            payload["multimodal_osrm_cache"] = multimodal_osrm_cache_stats()
        payload["queue"] = _queue_stats_payload()
        payload["policy"] = evaluate_cache_policy(payload)
        payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
        return jsonify(payload)
    except Exception as exc:
        return jsonify({"error": f"Cache stats okunamadi: {exc}"}), 500


@app.route("/api/geocode/suggest", methods=["GET"])
def api_geocode_suggest():
    """
    Yazarken Ãƒöneri iÃƒçin: KÃısmi yer ismi -> coklu sonuc doner (autocomplete).

    Query: ?q=KadÃıkÃƒöy&limit=6
    """
    try:
        q = request.args.get("q", "").strip()
        limit = min(int(request.args.get("limit", 6)), 10)
        result = geocode_suggest(q, limit=limit)
        return jsonify(result)
    except Exception as e:
        print(f"[API] Geocode suggest hatasÃı: {e}")
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
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


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
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/api/geocode", methods=["POST"])
def api_geocode():
    """
    Yer ismini koordinata Ãƒçevirir.

    Request Body:
        {
            "place": "KadÃıkÃƒöy ParkÃı, Ãİstanbul"
        }

    Response:
        {
            "status": "success",
            "lat": 40.990,
            "lon": 29.029,
            "display_name": "KadÃıkÃƒöy ParkÃı, Ãİstanbul, TÃƒürkiye",
            "cached": false
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data or "place" not in data:
            return jsonify({"error": "'place' alanÃı gerekli."}), 400

        place_name = data["place"]

        print(f"[API] Geocode: {place_name}")

        result = geocode(place_name)

        if result["status"] == "error":
            print(f"[API] Geocode HATA: {result['message']}")
            return jsonify(result), 404

        print(f"[API] Geocode Sonuc: ({result['lat']:.6f}, {result['lon']:.6f})")
        return jsonify(result)

    except Exception as e:
        print(f"[API] Geocode hatasÃı: {e}")
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/api/reverse-geocode", methods=["POST"])
def api_reverse_geocode():
    """
    KoordinatÃı yer ismine Ãƒçevirir.

    Request Body:
        {
            "lat": 40.990,
            "lon": 29.029
        }

    Response:
        {
            "status": "success",
            "display_name": "KadÃıkÃƒöy, Ãİstanbul, TÃƒürkiye",
            "address": "{...}",
            "cached": false
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data or "lat" not in data or "lon" not in data:
            return jsonify({"error": "'lat' ve 'lon' alanlarÃı gerekli."}), 400

        lat = data["lat"]
        lon = data["lon"]
        result = reverse_geocode(lat, lon)

        if result["status"] == "error":
            return jsonify(result), 404

        return jsonify(result)

    except Exception as e:
        print(f"[API] Reverse geocode hatasÃı: {e}")
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/api/geocode/batch", methods=["POST"])
def api_geocode_batch():
    """
    Toplu geocoding iÃ…şlemi.

    Request Body:
        {
            "places": ["KadÃıkÃƒöy", "BeÃ…şiktaÃ…ş", "Taksim"]
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
            return jsonify({"error": "'places' alanÃı gerekli (liste)."}), 400

        places = data["places"]

        if not isinstance(places, list):
            return jsonify({"error": "'places' bir liste olmalÃı."}), 400

        if len(places) > 10:
            return jsonify({"error": "En fazla 10 yer adÃı aynÃı anda iÃ…şlenebilir."}), 400

        results = geocode_batch(places)
        return jsonify({"results": results})

    except Exception as e:
        print(f"[API] Batch geocode hatasÃı: {e}")
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/")
def serve_frontend():
    """Ana sayfa - Frontend'i sun."""
    response = send_from_directory(FRONTEND_DIR, "index.html")
    # Dev ortaminda eski UI'nin cache'ten gelmesini onle
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/<path:filepath>")
def serve_static_files(filepath):
    """
    Statik dosyalarÃı sun (CSS, JS, gÃƒörseller vb.).
    Cache headers ile daha hÃızlÃı yÃƒüklenme.
    """
    response = send_from_directory(FRONTEND_DIR, filepath)

    # Dev ortaminda stale CSS/JS cache'ini engelle
    if filepath.endswith((".css", ".js")):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    elif filepath.endswith((".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp")):
        # GÃƒörsel dosyalar 1 gÃƒün cache
        response.headers["Cache-Control"] = "public, max-age=86400"
    else:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    return response


# =============================================================================
# ROTA KAYDETME VE YÃƒÅKLEME API'LERÃİ
# =============================================================================

@app.route("/api/routes/save", methods=["POST"])
def api_save_route():
    """
    RotayÃı kaydeder.
    
    Request Body:
        {
            "name": "KadÃıkÃƒöy Turu",
            "description": "KadÃıkÃƒöy'de gezilecek yerler",
            "points": [[lat, lon], ...],
            "route_coords": [[lat, lon], ...],
            "distance_km": 4.5,
            "duration_minutes": 55,
            "route_type": "shortest",
            "tags": ["tarihi", "kÃƒültÃƒürel"]
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
            return jsonify({"error": "GeÃƒçersiz veya eksik JSON gÃƒövdesi."}), 400

        route_payload = data.get("route_payload")
        if route_payload is not None and not isinstance(route_payload, dict):
            return jsonify({"error": "'route_payload' alanÃı obje formatÄ±nda olmalÄ±."}), 400
        
        # Zorunlu alanlar
        required_fields = ["name", "points", "route_coords", "distance_km", "duration_minutes"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"'{field}' alanÃı gerekli."}), 400
        
        # RotayÃı kaydet
        route = save_route(
            name=data["name"],
            points=data["points"],
            route_coords=data["route_coords"],
            distance_km=data["distance_km"],
            duration_minutes=data["duration_minutes"],
            route_type=data.get("route_type", "route_1"),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            route_payload=route_payload,
        )
        
        return jsonify({
            "status": "success",
            "route": route,
            "message": f"'{route['name']}' rotasÃı kaydedildi!"
        })
    
    except Exception as e:
        print(f"[API] Rota kaydetme hatasÃı: {e}")
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/api/routes", methods=["GET"])
def api_get_routes():
    """
    TÃƒüm kaydedilmiÃ…ş rotalarÃı getirir (Pagination destekli).

    Query Parameters:
        sort_by: created_at, name, distance_km, times_used, favorite
        limit: Maksimum rota sayÃısÃı (varsayÃılan 20)
        offset: BaÃ…şlangÃıÃƒç index'i (varsayÃılan 0)
        page: Sayfa numarasÃı (limit ile hesaplanÃır, offset alternatifi)

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

        # Page parametresini offset'e Ãƒçevir
        if page > 1:
            offset = (page - 1) * limit

        # Toplam sayÃıyÃı al
        total = get_routes_count()

        # RotalarÃı getir
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
        # print(f"[API] Rota listeleme hatasÃı: {e}"))
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/api/routes/<route_id>", methods=["GET"])
def api_get_route_by_id(route_id):
    """
    Belirli bir rotayÃı getirir.
    
    Response:
        {
            "route": {...}
        }
    """
    try:
        route = get_route(route_id)
        
        if not route:
            return jsonify({"error": "Rota bulunamadÃı"}), 404
        
        return jsonify({"route": route})
    
    except Exception as e:
        # print(f"[API] Rota getirme hatasÃı: {e}"))
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/api/routes/<route_id>", methods=["PUT"])
def api_update_route(route_id):
    """
    RotayÃı gÃƒünceller.
    
    Request Body:
        {
            "name": "Yeni Ãİsim",
            "description": "Yeni aÃƒçÃıklama",
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
            return jsonify({"error": "GeÃƒçersiz veya eksik JSON gÃƒövdesi."}), 400
        
        route = update_route(route_id, data)
        
        if not route:
            return jsonify({"error": "Rota bulunamadÃı"}), 404
        
        return jsonify({
            "status": "success",
            "route": route,
            "message": "Rota gÃƒüncellendi"
        })
    
    except Exception as e:
        print(f"[API] Rota gÃƒüncelleme hatasÃı: {e}")
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/api/routes/<route_id>", methods=["DELETE"])
def api_delete_route(route_id):
    """
    RotayÃı siler.
    
    Response:
        {
            "status": "success",
            "message": "Rota silindi"
        }
    """
    try:
        success = delete_route(route_id)
        
        if not success:
            return jsonify({"error": "Rota bulunamadÃı"}), 404
        
        return jsonify({
            "status": "success",
            "message": "Rota silindi"
        })
    
    except Exception as e:
        # print(f"[API] Rota silme hatasÃı: {e}"))
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/api/routes/<route_id>/favorite", methods=["POST"])
def api_toggle_favorite(route_id):
    """
    RotayÃı favorilere ekler/ÃƒçÃıkarÃır.
    
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
            return jsonify({"error": "Rota bulunamadÃı"}), 404
        
        return jsonify({
            "status": "success",
            "route": route,
            "is_favorite": route.get("favorite", False)
        })
    
    except Exception as e:
        # print(f"[API] Favori iÃ…şlemi hatasÃı: {e}"))
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


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
        print(f"[API] Rota arama hatasÃı: {e}")
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


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
        # print(f"[API] Ãİstatistik hatasÃı: {e}"))
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


# =============================================================================
# ZAMAN PLANLAMA API'LERÃİ
# =============================================================================

@app.route("/api/timeline/create", methods=["POST"])
def api_create_timeline():
    """
    Rota iÃƒçin zaman Ãƒçizelgesi oluÃ…şturur.
    
    Request Body:
        {
            "points": [
                {"name": "KadÃıkÃƒöy", "lat": 40.99, "lon": 29.03},
                {"name": "Moda", "lat": 40.98, "lon": 29.04}
            ],
            "segment_distances": [1.2, 0.8],  # km cinsinden
            "start_time": "09:00",
            "visit_duration": 30,  # dakika (varsayÃılan)
            "transport_mode": "walking",
            "custom_durations": {0: 45, 1: 60}  # ÃƒÆ’aa‚¬ œzel sÃƒüreler (opsiyonel)
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
            return jsonify({"error": "'points' alanÃı gerekli"}), 400
        
        points = data["points"]
        segment_distances = data.get("segment_distances", [])
        start_time = data.get("start_time", "09:00")
        visit_duration = data.get("visit_duration", 30)
        transport_mode = data.get("transport_mode", "walking")
        custom_durations = data.get("custom_durations", {})
        include_weather = bool(data.get("include_weather", False) and WEATHER_SERVICE_AVAILABLE)
        
        # String key'leri int'e Ãƒçevir
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
        # print(f"[API] Timeline oluÃ…şturma hatasÃı: {e}"))
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/api/timeline/check-conflicts", methods=["POST"])
def api_check_conflicts():
    """
    Zaman Ãƒçizelgesinde ÃƒçakÃıÃ…şmalarÃı kontrol eder.
    
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
                    "warning": "Bu saat kapalÃı olabilir",
                    "arrival_time": "20:00"
                }
            ]
        }
    """
    try:
        data = request.get_json(silent=True)
        
        if not data or "schedule" not in data:
            return jsonify({"error": "'schedule' alanÃı gerekli"}), 400
        
        schedule = data["schedule"]
        opening_hours = data.get("opening_hours", {})
        
        # String key'leri int'e Ãƒçevir
        if opening_hours:
            opening_hours = {int(k): v for k, v in opening_hours.items()}
        
        warnings = check_time_conflicts(schedule, opening_hours)
        
        return jsonify({"warnings": warnings})
    
    except Exception as e:
        print(f"[API] Ãƒ ¡akÃıÃ…şma kontrolÃƒü hatasÃı: {e}")
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/api/timeline/optimize", methods=["POST"])
def api_optimize_timeline():
    """
    Zaman Ãƒçizelgesini optimize eder ve Ãƒöneriler sunar.
    
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
                    "message": "Toplam sÃƒüre 1s 30dk fazla",
                    "suggestion": "Ziyaret sÃƒürelerini azaltÃın"
                }
            ]
        }
    """
    try:
        data = request.get_json(silent=True)
        
        if not data or "schedule" not in data:
            return jsonify({"error": "'schedule' alanÃı gerekli"}), 400
        
        schedule = data["schedule"]
        max_duration = data.get("max_duration_minutes")
        preferred_end = data.get("preferred_end_time")
        
        result = optimize_schedule(schedule, max_duration, preferred_end)
        
        return jsonify(result)
    
    except Exception as e:
        # print(f"[API] Optimizasyon hatasÃı: {e}"))
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


# =============================================================================
# KULLANICI LOKASYON API'LERÃİ
# =============================================================================

@app.route("/api/locations", methods=["GET"])
def api_get_locations():
    """
    KaydedilmiÃ…ş tÃƒüm lokasyonlarÃı getirir.
    Pagination desteÃşi eklenmiÃ…ştir (limit, offset, page).
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

        # Toplam sayfa sayÃısÃınÃı hesapla
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
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/api/locations", methods=["POST"])
def api_save_location():
    """
    Yeni bir lokasyon kaydeder.
    """
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "GeÃƒçersiz veya eksik JSON gÃƒövdesi."}), 400
        
        required_fields = ["name", "lat", "lon"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"'{field}' alanÃı gerekli."}), 400
                
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
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/api/locations/<location_id>", methods=["DELETE"])
def api_delete_location(location_id):
    """
    Lokasyonu siler.
    """
    try:
        success = delete_location(location_id)
        
        if not success:
            return jsonify({"error": "Lokasyon bulunamadÃı"}), 404
            
        return jsonify({
            "status": "success",
            "message": "Lokasyon silindi"
        })
    except Exception as e:
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/api/locations/<location_id>", methods=["PUT"])
def api_update_location(location_id):
    """
    Lokasyonu gÃƒünceller.
    """
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "GeÃƒçersiz veya eksik JSON gÃƒövdesi."}), 400

        location = update_location(location_id, data)
        
        if not location:
            return jsonify({"error": "Lokasyon bulunamadÃı"}), 404
            
        return jsonify({
            "status": "success",
            "location": location,
            "message": "Lokasyon gÃƒüncellendi"
        })
    except Exception as e:
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


@app.route("/api/locations/<location_id>/favorite", methods=["POST"])
def api_toggle_location_favorite(location_id):
    """
    Lokasyonun favori durumunu deÃşiÃ…ştirir.
    """
    try:
        location = toggle_location_favorite(location_id)
        
        if not location:
            return jsonify({"error": "Lokasyon bulunamadÃı"}), 404
            
        return jsonify({
            "status": "success",
            "location": location,
            "is_favorite": location.get("favorite", False),
            "message": "Favorilere eklendi *" if location.get("favorite") else "Favorilerden cikarildi"
        })
    except Exception as e:
        return jsonify({"error": f"Sunucu hatasÃı: {str(e)}"}), 500


# =============================================================================
# BERT NLP ENDPOINTS
# =============================================================================

@app.route("/api/nlp/parse", methods=["POST"])
def api_nlp_parse():
    """
    DoÃşal dil sorgusunu analiz eder ve yapÃılandÃırÃılmÃıÃ…ş veri dÃƒöner.

    Request Body:
        {
            "query": "KadÃıkÃƒöy'den BeÃ…şiktaÃ…ş'a rota Ãƒçiz"
        }

    Response:
        {
            "type": "route",           # route | poi | multi | single | unknown
            "confidence": 0.85,
            "origin": "KadÃıkÃƒöy",
            "destination": "BeÃ…şiktaÃ…ş",
            "locations": null,         # multi iÃƒçin
            "location": null,          # poi iÃƒçin
            "detected_places": [
                {"place": "KadÃıkÃƒöy", "similarity": 0.92},
                {"place": "BeÃ…şiktaÃ…ş", "similarity": 0.88}
            ],
            "parse_time": 0.15,
            "error": null
        }
    """
    query = ""
    permit_acquired = False
    queue_wait_ms = 0.0
    try:
        # BERT NLP endpoint'i regex fallback olmadan calisir.
        # Akis: input dogrulama -> queue/concurrency -> parse -> scope kontrol -> audit log.
        trace_prefix = _request_trace_prefix()
        print(f"\n{'='*60}")
        print(f"{trace_prefix} [NLP API] Parse ÃƒçaÃşrÃısÃı alÃındÃı")
        global BERT_NLP_AVAILABLE
        data = request.get_json(silent=True)

        if not data or "query" not in data:
            print(f"[NLP API] ? Eksik parametreler")
            return jsonify({"error": "'query' alanÃı gerekli"}), 400

        query_value = data["query"]
        if not isinstance(query_value, str):
            print(f"[NLP API] ? Query metin olmalÃı")
            return jsonify({"error": "'query' alanÃı metin olmalÃı"}), 400

        query = query_value.strip()
        debug_trace_requested = bool(data.get("debug", False)) or _BERT_PARSE_TRACE_LOG_ENABLED

        if not query or len(query) < 2:
            print(f"[NLP API] ? Sorgu Ãƒçok kÃısa")
            return jsonify({"error": "Sorgu Ãƒçok kÃısa"}), 400

        print(f"{trace_prefix} [NLP API] ?? Sorgu: '{_redact_pii_text(query)}'")
        print(f"{trace_prefix} [NLP API] ?? BERT_NLP_AVAILABLE: {BERT_NLP_AVAILABLE}")

        if not BERT_NLP_AVAILABLE:
            print(f"[NLP API] ? BERT motoru ZORUNLU! Regex fallback KALDIRILDI.")
            return jsonify({"error": "BERT motoru gereklidir. Transformers ve PyTorch kurun."}), 503

        # NLP istekleri bounded semaphore ile korunur:
        # model asiri yukte oldugunda tutarli 429 donmek icin.
        queue_wait_start = time.perf_counter()
        permit_acquired = _NLP_PARSE_SEMAPHORE.acquire(timeout=_NLP_QUEUE_TIMEOUT_SEC)
        queue_wait_ms = round((time.perf_counter() - queue_wait_start) * 1000, 2)
        if not permit_acquired:
            _increment_queue_timeout_counter("nlp")
            return jsonify({
                "error": "NLP kuyruk bekleme suresi asildi. Lutfen tekrar deneyin.",
                "error_code": "NLP_QUEUE_TIMEOUT",
                "max_concurrency": _NLP_PARSE_MAX_CONCURRENCY,
                "retry_after_sec": max(1, int(round(_NLP_QUEUE_TIMEOUT_SEC))),
                "queue_wait_ms": queue_wait_ms,
            }), 429

        print(f"[NLP API] ?? BERT motoru kullanÃılÃıyor...")
        try:
            nlp_engine = get_bert_nlp_engine()
            _log_bert_runtime_metrics(
                stage="parse:before",
                bert_engine_instance=getattr(nlp_engine, "bert", None)
            )
            result = nlp_engine.parse(query, include_trace=debug_trace_requested)
            result = _postprocess_nlp_result_for_poi(query, result)
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
            print(f"{trace_prefix} [NLP API] ? BERT parse baÃ…şarÃılÃı")
        except Exception as bert_exc:
            print(f"{trace_prefix} [NLP API] ? BERT hatasÃı: {bert_exc}")
            return jsonify({"error": f"BERT motoru hatasÃı: {str(bert_exc)}"}), 500

        # NLP sonucu lokasyon iceriyorsa Istanbul kapsami burada zorlanir.
        # Boylece parser dogru olsa bile out-of-scope hedefler engellenir.
        scope_checks = []
        for place in _extract_nlp_places_for_scope_check(result):
            in_istanbul, meta = _is_place_text_in_istanbul(place)
            scope_checks.append({"place": place, "in_istanbul": in_istanbul, "meta": meta})
            if in_istanbul is False:
                return _outside_istanbul_response(
                    detail=f"NLP sorgusu Istanbul disi bir lokasyon iceriyor: {meta.get('display_name', place)}",
                    field="query",
                )
        result["istanbul_scope"] = {
            "enforced": True,
            "checks": scope_checks,
        }

        confidence = float(result.get("confidence", 0.0) or 0.0)
        print(f"{trace_prefix} [NLP API] ?? SonuÃƒç:")
        print(f"{trace_prefix} [NLP API]    - Tip: {result.get('type', 'unknown')}")
        print(f"{trace_prefix} [NLP API]    - Confidence: {confidence:.2f}")
        print(f"{trace_prefix} [NLP API]    - Engine: {result.get('engine', 'unknown')}")
        if result.get('origin'):
            print(f"{trace_prefix} [NLP API]    - Rota: {result['origin']} aa‚¬Âº {result.get('destination', '?')}")
        if result.get('detected_places'):
            print(f"{trace_prefix} [NLP API]    - Tespit edilen yerler: {[p['place'] for p in result['detected_places']]}")
        if debug_trace_requested:
            _log_bert_parse_trace(result.get("trace") or {})

        safe_result = dict(result)
        if "raw_query" in safe_result:
            safe_result["raw_query"] = _redact_pii_text(safe_result.get("raw_query"))
        print(f"{trace_prefix} [NLP API] ?? DÃƒönen response: {safe_result}")
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

        result["queue_wait_ms"] = queue_wait_ms
        result["queue_timeout_sec"] = float(_NLP_QUEUE_TIMEOUT_SEC)
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
        return jsonify({"error": f"NLP hatasÃı: {str(e)}"}), 500
    finally:
        if permit_acquired:
            _NLP_PARSE_SEMAPHORE.release()


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
    runtime_metrics = {}
    model_loaded = False
    if BERT_NLP_AVAILABLE:
        try:
            import bert_nlp_engine as bert_nlp_module

            nlp_singleton = getattr(bert_nlp_module, "_bert_nlp_engine", None)
            bert_instance = getattr(nlp_singleton, "bert", None) if nlp_singleton is not None else None
            if bert_instance is not None and hasattr(bert_instance, "get_runtime_metrics"):
                runtime_metrics = bert_instance.get_runtime_metrics() or {}
                model_loaded = True
        except Exception:
            runtime_metrics = {}

    queue_stats = _queue_stats_payload()
    return jsonify({
        "available": BERT_NLP_AVAILABLE,
        "engine": "bert-nlp" if BERT_NLP_AVAILABLE else "regex-fallback",
        "model": "dbmdz/bert-base-turkish-uncased" if BERT_NLP_AVAILABLE else None,
        "bert_available": BERT_NLP_AVAILABLE,
        "last_error": _BERT_NLP_ERROR,
        "queue": {
            "nlp": queue_stats.get("nlp", {}),
            "multimodal": queue_stats.get("multimodal", {}),
        },
        "bert_runtime": {
            "loaded": model_loaded,
            "device": runtime_metrics.get("device"),
            "gpu_allocated_mb": runtime_metrics.get("gpu_allocated_mb"),
            "gpu_reserved_mb": runtime_metrics.get("gpu_reserved_mb"),
            "gpu_max_allocated_mb": runtime_metrics.get("gpu_max_allocated_mb"),
            "cache_hit_rate": runtime_metrics.get("cache_hit_rate"),
            "cache_size": runtime_metrics.get("cache_size"),
            "cache_hits": runtime_metrics.get("cache_hits"),
            "cache_misses": runtime_metrics.get("cache_misses"),
        },
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
    Ãİki metin arasÃındaki semantic similarity'yi hesaplar.

    Request Body:
        {
            "text1": "KadÃıkÃƒöy",
            "text2": "KadikÃƒöy"
        }

    Response:
        {
            "similarity": 0.92,
            "text1": "KadÃıkÃƒöy",
            "text2": "KadikÃƒöy"
        }
    """
    try:
        print(f"\n{'='*60}")
        print(f"[NLP API] Similarity ÃƒçaÃşrÃısÃı alÃındÃı")
        if not BERT_NLP_AVAILABLE:
            print(f"[NLP API] ? BERT engine aktif deÃşil!")
            return jsonify({"error": "BERT engine aktif deÃşil"}), 503

        data = request.get_json(silent=True)
        print(f"[NLP API] ?? Gelen request: {data}")

        if not data or "text1" not in data or "text2" not in data:
            print(f"[NLP API] ? Eksik parametreler")
            return jsonify({"error": "'text1' ve 'text2' alanlarÃı gerekli"}), 400

        text1 = data["text1"].strip()
        text2 = data["text2"].strip()
        print(f"[NLP API] ?? Text1: '{text1}' | Text2: '{text2}'")

        if not text1 or not text2:
            print(f"[NLP API] ? BoÃ…ş metin")
            return jsonify({"error": "Metinler boÃ…ş olamaz"}), 400

        print(f"[NLP API] ?? BERT engine yÃƒükleniyor...")
        from bert_engine import get_bert_engine
        engine = get_bert_engine()
        _log_bert_runtime_metrics(stage="similarity:before", bert_engine_instance=engine)
        print(f"[NLP API] ? BERT engine hazÃır")

        print(f"[NLP API] ?? Benzerlik hesaplanÃıyor...")
        similarity = engine.similarity(text1, text2)
        _log_bert_runtime_metrics(stage="similarity:after", bert_engine_instance=engine)
        print(f"[NLP API] ? SonuÃƒç: {similarity:.4f}")

        result = {
            "similarity": float(similarity),
            "text1": text1,
            "text2": text2
        }
        print(f"[NLP API] ?? DÃƒönen response: {result}")
        print(f"{'='*60}\n")

        return jsonify(result)

    except Exception as e:
        print(f"[NLP ERROR] Similarity: {str(e)}")
        return jsonify({"error": f"Benzerlik hesaplanamadÃı: {str(e)}"}), 500


@app.route("/api/nlp/best-match", methods=["POST"])
def api_nlp_best_match():
    """
    Sorguya en yakÃın adayÃı bulur (typo tolerant).

    Request Body:
        {
            "query": "kadikoy",
            "candidates": ["KadÃıkÃƒöy", "BeÃ…şiktaÃ…ş", "Taksim"],
            "threshold": 0.75
        }

    Response:
        {
            "match": "KadÃıkÃƒöy",
            "similarity": 0.92,
            "index": 0
        }
    """
    try:
        print(f"\n{'='*60}")
        print(f"[NLP API] Best Match ÃƒçaÃşrÃısÃı alÃındÃı")
        if not BERT_NLP_AVAILABLE:
            print(f"[NLP API] ? BERT engine aktif deÃşil!")
            return jsonify({"error": "BERT engine aktif deÃşil"}), 503

        data = request.get_json(silent=True)
        print(f"[NLP API] ?? Gelen request: query='{data.get('query')}', {len(data.get('candidates', []))} aday")

        if not data or "query" not in data or "candidates" not in data:
            print(f"[NLP API] ? Eksik parametreler")
            return jsonify({"error": "'query' ve 'candidates' alanlarÃı gerekli"}), 400

        query = data["query"].strip()
        candidates = data["candidates"]
        threshold = data.get("threshold", 0.75)
        print(f"[NLP API] ?? Query: '{query}' | Threshold: {threshold}")
        print(f"[NLP API] ?? Adaylar: {candidates}")

        if not query:
            print(f"[NLP API] ? BoÃ…ş sorgu")
            return jsonify({"error": "Sorgu boÃ…ş olamaz"}), 400

        if not isinstance(candidates, list) or len(candidates) == 0:
            print(f"[NLP API] ? GeÃƒçersiz adaylar")
            return jsonify({"error": "'candidates' bir liste olmalÃı"}), 400

        print(f"[NLP API] ?? BERT engine yÃƒükleniyor...")
        from bert_engine import get_bert_engine
        engine = get_bert_engine()
        _log_bert_runtime_metrics(stage="best-match:before", bert_engine_instance=engine)
        print(f"[NLP API] ? BERT engine hazÃır")

        print(f"[NLP API] ?? En iyi eÃ…şleÃ…şme aranÃıyor...")
        result = engine.find_best_match(query, candidates, threshold=threshold)
        _log_bert_runtime_metrics(stage="best-match:after", bert_engine_instance=engine)

        if result:
            print(f"[NLP API] ? EÃ…şleÃ…şme bulundu: {result['match']} (benzerlik: {result['similarity']:.4f})")
            print(f"[NLP API] ?? DÃƒönen response: {result}")
        else:
            print(f"[NLP API] ? EÃ…şleÃ…şme bulunamadÃı")
            result = {
                "match": None,
                "similarity": 0.0,
                "index": -1,
                "message": f"EÃ…şleÃ…şme bulunamadÃı (threshold: {threshold})"
            }
        print(f"{'='*60}\n")

        return jsonify(result)

    except Exception as e:
        print(f"[NLP ERROR] Best match: {str(e)}")
        return jsonify({"error": f"EÃ…şleÃ…şme bulunamadÃı: {str(e)}"}), 500


# =============================================================================
# HAVA DURUMU ENDPOINTS (OpenMeteo API)
# =============================================================================

@app.route("/api/weather", methods=["GET"])
def api_get_weather():
    """
    Belirli bir konum iÃƒçin gÃƒüncel hava durumunu getirir.

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
    Belirli bir konum iÃƒçin saatlik hava tahmini getirir.

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

        print(f"[Weather] Route check: {len(points)} noktalar, forecast={'evet' if start_time and 'T' in str(start_time) else 'hayÃır'}")

        result = check_route_weather(points, start_time, segment_distances, transport_mode)

        if result.get("success"):
            return jsonify(result)
        else:
            return jsonify({"error": "Rota hava kontrolÃƒü basarisiz"}), 500

    except Exception as e:
        print(f"[Weather ERROR] {str(e)}")
        return jsonify({"error": f"Sunucu hatasi: {str(e)}"}), 500


@app.route("/api/weather/status", methods=["GET"])
def api_weather_status():
    """
    Hava durumu servisi durumunu dondurÃƒür.

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
    Hava durumu servisi saglik kontrolÃƒü.

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
    if provider not in {"openrouter", "gemini", "local"}:
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


@app.route("/api/llm/local/status", methods=["GET"])
def api_local_llm_status():
    """Local OpenAI-compatible LLM entegrasyon durumunu dondurur."""
    if not LOCAL_LLM_SERVICE_AVAILABLE:
        return jsonify({
            "available": False,
            "configured": False,
            "error": "Local LLM servisi yuklenemedi",
        }), 503

    status = local_llm_status()
    health_rows = list_provider_health("local")
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


@app.route("/api/llm/local/models", methods=["GET"])
def api_local_llm_models():
    if not LOCAL_LLM_SERVICE_AVAILABLE:
        return jsonify({"error": "Local LLM servisi mevcut degil"}), 503
    try:
        models = local_llm_list_models()
        return jsonify({"ok": True, "models": models})
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc), "models": []}), 502
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Sunucu hatasi: {exc}", "models": []}), 500


@app.route("/api/llm/rag/status", methods=["GET"])
def api_rag_status():
    if not RAG_SERVICE_AVAILABLE:
        return jsonify({
            "available": False,
            "configured": False,
            "error": "RAG servisi mevcut degil (rag_service import edilemedi)",
        }), 503
    try:
        st = rag_status()
        collections = []
        if st.get("available"):
            collections = rag_list_collections()
        return jsonify({
            "available": bool(st.get("available")),
            "enabled": bool(st.get("enabled")),
            "db_path": st.get("db_path"),
            "collection": st.get("collection"),
            "embed_model": st.get("embed_model"),
            "top_k_default": st.get("top_k_default"),
            "collections": collections,
        })
    except Exception as exc:
        return jsonify({"available": False, "error": f"RAG status hatasi: {exc}"}), 500


@app.route("/api/llm/local/chat/rag", methods=["POST"])
def api_local_llm_chat_rag():
    if not LOCAL_LLM_SERVICE_AVAILABLE:
        return jsonify({"error": "Local LLM servisi mevcut degil"}), 503
    if not is_local_llm_configured():
        return jsonify({"error": "LOCAL_LLM_ENABLED/BASE_URL ayari eksik"}), 503

    # Local chat endpoint'i iki modda calisir:
    # 1) RAG uygun/guvenilir ise extractive veya structured cevap
    # 2) RAG uygun degilse normal LLM chat (fallback modeli dahil)
    data = request.get_json(silent=True) or {}

    session_id = str(data.get("session_id", "") or "").strip()
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

    rag_top_k_raw = data.get("rag_top_k", data.get("top_k", 5))
    try:
        top_k = int(rag_top_k_raw)
    except (TypeError, ValueError):
        top_k = 5
    top_k = max(1, min(top_k, 12))

    rag_collection = str(data.get("rag_collection", "") or "").strip() or None
    rag_min_similarity = _resolve_rag_min_similarity(data)
    include_chunks = _as_bool(data.get("include_chunks", False), default=False)
    rag_debug = _as_bool(data.get("rag_debug", False), default=False)
    rag_marker = repair_text(data.get("rag_marker")).strip()
    rag_result = {
        "collection": rag_collection or "",
        "top_k": top_k,
        "count": 0,
        "sources": [],
        "chunks": [],
    }
    rag_context = ""
    rag_used = False
    rag_skip_reason = ""

    # RAG "her soruda zorunlu" degildir; intent tabanli karar verilir.
    use_rag_for_query, rag_reason = _should_use_rag_for_query_with_reason(user_text)
    if use_rag_for_query:
        if not RAG_SERVICE_AVAILABLE or not is_rag_available():
            return jsonify({"error": "RAG servisi aktif degil veya bagimliliklar eksik"}), 503
        try:
            rag_result = rag_query(user_text, top_k=top_k, collection=rag_collection)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503
        except Exception as exc:
            return jsonify({"error": f"RAG sorgu hatasi: {exc}"}), 500

        rag_context = _normalize_common_turkish_glitches(repair_text(rag_result.get("context", "")))
        if not rag_context:
            rag_context = "[Baglam bulunamadi]"
        # Similarity/kalite dusukse RAG baglami guvenilmez kabul edilir
        # ve modelin genel cevap moduna gecilir.
        fallback_from_rag, fallback_reason = _should_fallback_from_rag(
            rag_result,
            rag_min_similarity,
        )
        if fallback_from_rag:
            rag_used = False
            rag_skip_reason = fallback_reason
            rag_context = ""
        else:
            rag_used = True
    else:
        rag_skip_reason = rag_reason

    marker_prefix = f"RAG_MARKER: {rag_marker}\n\n" if rag_marker else ""
    user_prompt = user_text
    if rag_used:
        user_prompt = (
            f"{marker_prefix}"
            f"Soru: {user_text}\n\n"
            f"Baglam:\n{rag_context}\n\n"
            "Yalnizca verilen baglama dayanarak cevap ver. "
            "Sadece bu son soruya cevap ver; onceki konusma icerigini tekrar etme. "
            "Baglamda acikca yoksa 'Bu bilgi baglamda yok' diye belirt ve uydurma yapma. "
            "Kesin olmayan saat/ucret/sefer bilgilerini garanti etme; "
            "gerektiginde guncel kontrol notu ekle."
        )

    # Context bleed'i engellemek icin varsayilan tek mesaj politikasi:
    # sadece son kullanici sorusu modele verilir.
    use_session_context = _as_bool(data.get("use_session_context", False), default=False)
    if use_session_context and session_id and not rag_used:
        messages = _chat_context_from_session(session_id, context_limit=6) + [{"role": "user", "content": user_prompt}]
    elif use_session_context and not session_id and not rag_used:
        base_messages = provided_messages[:-1] if provided_messages else []
        messages = base_messages + [{"role": "user", "content": user_prompt}]
    else:
        messages = [{"role": "user", "content": user_prompt}]
    messages = _inject_local_system_message(messages)

    model = data.get("model")
    generation_data = dict(data)
    if "top_k" in generation_data and "llm_top_k" not in generation_data:
        generation_data.pop("top_k", None)
    if "llm_top_k" in generation_data:
        generation_data["top_k"] = generation_data.get("llm_top_k")
    generation_options = _local_llm_generation_options(generation_data)
    use_fallback = _as_bool(data.get("use_fallback", True), default=True)

    try:
        if rag_used:
            # RAG tarafinda once deterministic cevabi dene (hallucination riskini azaltir).
            direct_answer = _try_direct_rag_structured_answer(user_text, rag_result)
            if direct_answer:
                assistant_text = _normalize_common_turkish_glitches(repair_text(direct_answer))
                if session_id:
                    save_chat_turn(
                        session_id=session_id,
                        user_text=user_text,
                        assistant_text=assistant_text or "[Bos yanit]",
                        model="rag-direct-structured",
                        token_total=0,
                        error_type="",
                    )
                payload = {
                    "ok": True,
                    "model": "rag-direct-structured",
                    "text": assistant_text,
                    "usage": {"total_tokens": 0},
                    "id": None,
                    "tried_models": ["rag-direct-structured"],
                    "rag": {
                        "used": True,
                        "skip_reason": "",
                        "min_similarity": rag_min_similarity,
                        "top_similarity": rag_result.get("top_similarity"),
                        "collection": rag_result.get("collection"),
                        "top_k": rag_result.get("top_k"),
                        "count": rag_result.get("count"),
                        "sources": rag_result.get("sources", []),
                    },
                }
                if include_chunks:
                    payload["rag"]["chunks"] = rag_result.get("chunks", [])
                return jsonify(payload)

            assistant_text = _normalize_common_turkish_glitches(
                repair_text(_build_extractive_rag_answer(user_text, rag_result))
            )
            if session_id:
                save_chat_turn(
                    session_id=session_id,
                    user_text=user_text,
                    assistant_text=assistant_text or "[Bos yanit]",
                    model="rag-extractive",
                    token_total=0,
                    error_type="",
                )
            payload = {
                "ok": True,
                "model": "rag-extractive",
                "text": assistant_text,
                "usage": {"total_tokens": 0},
                "id": None,
                "tried_models": ["rag-extractive"],
                "rag": {
                    "used": True,
                    "skip_reason": "",
                    "min_similarity": rag_min_similarity,
                    "top_similarity": rag_result.get("top_similarity"),
                    "collection": rag_result.get("collection"),
                    "top_k": rag_result.get("top_k"),
                    "count": rag_result.get("count"),
                    "sources": rag_result.get("sources", []),
                },
            }
            if rag_marker:
                payload["rag"]["marker_echo"] = rag_marker
            if rag_debug:
                payload["rag"]["debug"] = {
                    "context_char_len": len(rag_context),
                    "context_sha256": hashlib.sha256(rag_context.encode("utf-8")).hexdigest(),
                    "chunk_count": len(rag_result.get("chunks", [])),
                    "chunk_record_types": [
                        str((c.get("record_type") or "")) for c in (rag_result.get("chunks", [])[:10])
                    ],
                }
            if include_chunks:
                payload["rag"]["chunks"] = rag_result.get("chunks", [])
            return jsonify(payload)

        if use_fallback:
            result = local_llm_chat_completion_with_fallback(
                messages=messages,
                model=model,
                **generation_options,
            )
        else:
            result = local_llm_chat_completion(
                messages=messages,
                model=model,
                **generation_options,
            )
            result["tried_models"] = [result.get("model") or model or ""]

        assistant_text = _normalize_common_turkish_glitches(repair_text(result.get("text", "")))

        if session_id:
            save_chat_turn(
                session_id=session_id,
                user_text=user_text,
                assistant_text=assistant_text or "[Bos yanit]",
                model=repair_text(result.get("model")) or "",
                token_total=(result.get("usage") or {}).get("total_tokens"),
                error_type="",
            )

        payload = {
            "ok": True,
            "model": repair_text(result.get("model")),
            "text": assistant_text,
            "usage": result.get("usage", {}),
            "id": result.get("id"),
            "tried_models": result.get("tried_models", []),
            "rag": {
                "used": rag_used,
                "skip_reason": rag_skip_reason,
                "min_similarity": rag_min_similarity,
                "top_similarity": rag_result.get("top_similarity"),
                "collection": rag_result.get("collection"),
                "top_k": rag_result.get("top_k"),
                "count": rag_result.get("count"),
                "sources": rag_result.get("sources", []),
            },
        }
        if rag_marker:
            payload["rag"]["marker_echo"] = rag_marker
        if rag_debug:
            payload["rag"]["debug"] = {
                "context_char_len": len(rag_context),
                "context_sha256": hashlib.sha256(rag_context.encode("utf-8")).hexdigest(),
                "chunk_count": len(rag_result.get("chunks", [])),
                "chunk_record_types": [
                    str((c.get("record_type") or "")) for c in (rag_result.get("chunks", [])[:10])
                ],
            }
        if include_chunks:
            payload["rag"]["chunks"] = rag_result.get("chunks", [])
        return jsonify(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        return jsonify({"error": f"Sunucu hatasi: {exc}"}), 500


@app.route("/api/llm/local/chat", methods=["POST"])
def api_local_llm_chat():
    if not LOCAL_LLM_SERVICE_AVAILABLE:
        return jsonify({"error": "Local LLM servisi mevcut degil"}), 503
    if not is_local_llm_configured():
        return jsonify({"error": "LOCAL_LLM_ENABLED/BASE_URL ayari eksik"}), 503

    data = request.get_json(silent=True) or {}

    session_id = str(data.get("session_id", "") or "").strip()
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
        messages = _chat_context_from_session(session_id, context_limit=40) + [{"role": "user", "content": user_text}]
    else:
        messages = provided_messages or [{"role": "user", "content": user_text}]
    messages = _inject_local_system_message(messages)

    model = data.get("model")
    generation_options = _local_llm_generation_options(data)
    use_fallback = _as_bool(data.get("use_fallback", True), default=True)

    try:
        if use_fallback:
            result = local_llm_chat_completion_with_fallback(
                messages=messages,
                model=model,
                **generation_options,
            )
        else:
            result = local_llm_chat_completion(
                messages=messages,
                model=model,
                **generation_options,
            )
            result["tried_models"] = [result.get("model") or model or ""]
        assistant_text = repair_text(result.get("text", ""))
        if session_id:
            save_chat_turn(
                session_id=session_id,
                user_text=user_text,
                assistant_text=assistant_text or "[Bos yanit]",
                model=repair_text(result.get("model")) or "",
                token_total=(result.get("usage") or {}).get("total_tokens"),
                error_type="",
            )
        return jsonify({
            "ok": True,
            "model": repair_text(result.get("model")),
            "text": assistant_text,
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


@app.route("/api/llm/local/chat/stream", methods=["POST"])
def api_local_llm_chat_stream():
    if not LOCAL_LLM_SERVICE_AVAILABLE:
        return jsonify({"error": "Local LLM servisi mevcut degil"}), 503
    if not is_local_llm_configured():
        return jsonify({"error": "LOCAL_LLM_ENABLED/BASE_URL ayari eksik"}), 503

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
        llm_messages = _inject_local_system_message(
            _chat_context_from_session(session_id, context_limit=40) + [{"role": "user", "content": user_text}]
        )
    else:
        llm_messages = provided_messages or [{"role": "user", "content": user_text}]
        llm_messages = _inject_local_system_message(llm_messages)

    model = data.get("model")
    generation_options = _local_llm_generation_options(data)
    use_fallback = _as_bool(data.get("use_fallback", True), default=True)
    default_model = local_llm_status().get("default_model", "")
    requested_model = str(model or "").strip()
    if use_fallback:
        candidate_models = _llm_candidate_models("local", requested_model or default_model)
        candidate_models = [m for m in candidate_models if not is_model_blocked("local", m)]
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
                stream_iter = local_llm_chat_completion_stream(
                    messages=llm_messages,
                    model=candidate,
                    **generation_options,
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
                            if _is_repetition_loop("".join(collected_tokens)):
                                stream_error = "Tekrar dongusu algilandi, yanit erken durduruldu"
                                error_type = "loop_guard"
                                yield json.dumps(
                                    {"type": "meta", "phase": "guard_stop", "model": candidate, "error": stream_error, "tried_models": tried_models},
                                    ensure_ascii=False,
                                ) + "\n"
                                break
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
                        provider="local",
                        model=candidate,
                        success=True,
                        latency_ms=latency_ms,
                    )
                    if error_type != "loop_guard":
                        yield json.dumps(
                            {"type": "meta", "phase": "success", "model": candidate, "tried_models": tried_models},
                            ensure_ascii=False,
                        ) + "\n"
                    yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"
                    if error_type != "loop_guard":
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
                    provider="local",
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
                    provider="local",
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
                    provider="local",
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
    from multimodal_engine import (
        compare_routes as multimodal_compare,
        get_compare_cache_stats as multimodal_compare_cache_stats,
        get_transit_lookup_cache_stats as multimodal_transit_lookup_cache_stats,
        get_segment_cache_stats as multimodal_segment_cache_stats,
        get_osrm_cache_stats as multimodal_osrm_cache_stats,
    )
    _multimodal_available = True
except ImportError:
    _multimodal_available = False
    multimodal_compare_cache_stats = lambda: {}
    multimodal_transit_lookup_cache_stats = lambda: {}
    multimodal_segment_cache_stats = lambda: {}
    multimodal_osrm_cache_stats = lambda: {}
    print("[API] multimodal_engine yuklenemedi")


@app.route("/api/multimodal/compare", methods=["POST"])
def api_multimodal_compare():
    """
    Yuruyus ve toplu tasima seceneklerini karsilastirir.

    Request Body:
        {
            "origin": [lat, lon],
            "destination": [lat, lon],
            "allowed_modes": ["bus", "metro", "metrobus", "ferry"]  # opsiyonel
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

    permit_acquired = False
    queue_wait_ms = 0.0
    try:
        # Multimodal endpoint:
        # input + geofence + allowed_modes normalize -> queue ->
        # compare engine -> telemetry ile response.
        request_start = time.perf_counter()
        stage_ms = {}

        stage_start = time.perf_counter()
        data = request.get_json(silent=True)
        stage_ms["parse_json_ms"] = round((time.perf_counter() - stage_start) * 1000, 2)

        if not data or "origin" not in data or "destination" not in data:
            return jsonify({"error": "'origin' ve 'destination' alanlari gerekli"}), 400

        stage_start = time.perf_counter()
        origin = data["origin"]
        destination = data["destination"]
        allowed_modes = data.get("allowed_modes")

        if allowed_modes is not None and not isinstance(allowed_modes, list):
            return jsonify({"error": "allowed_modes liste formatinda olmali"}), 400

        if isinstance(allowed_modes, list):
            max_modes = int(ROUTE_CONFIG.get("MULTIMODAL_ALLOWED_MODES_MAX", 4))
            normalized_modes = []
            seen_modes = set()
            for mode in allowed_modes:
                mode_norm = str(mode).strip().lower()
                if not mode_norm or mode_norm in seen_modes:
                    continue
                seen_modes.add(mode_norm)
                normalized_modes.append(mode_norm)
                if len(normalized_modes) >= max_modes:
                    break
            allowed_modes = normalized_modes
        stage_ms["validate_input_ms"] = round((time.perf_counter() - stage_start) * 1000, 2)

        stage_start = time.perf_counter()
        origin_pair = _to_lat_lon_pair(origin)
        destination_pair = _to_lat_lon_pair(destination)
        if origin_pair is None:
            return jsonify({"error": "origin [lat, lon] formatinda olmali"}), 400
        if destination_pair is None:
            return jsonify({"error": "destination [lat, lon] formatinda olmali"}), 400

        origin_lat, origin_lon = origin_pair
        destination_lat, destination_lon = destination_pair

        # Asama 3 geofence: su an uygulama sadece Istanbul icin.
        if not (_is_in_istanbul_bbox(origin_lat, origin_lon) and _is_in_istanbul_bbox(destination_lat, destination_lon)):
            return _outside_istanbul_response(detail="Origin veya destination Istanbul disinda.", field="origin,destination")
        stage_ms["normalize_geofence_ms"] = round((time.perf_counter() - stage_start) * 1000, 2)

        # Transit hesaplari maliyetli oldugu icin semaphore ile sinirlanir.
        queue_wait_start = time.perf_counter()
        permit_acquired = _MULTIMODAL_COMPARE_SEMAPHORE.acquire(timeout=_MULTIMODAL_QUEUE_TIMEOUT_SEC)
        queue_wait_ms = round((time.perf_counter() - queue_wait_start) * 1000, 2)
        if not permit_acquired:
            _increment_queue_timeout_counter("multimodal")
            return jsonify({
                "error": "Multimodal kuyruk bekleme suresi asildi. Lutfen tekrar deneyin.",
                "error_code": "MULTIMODAL_QUEUE_TIMEOUT",
                "max_concurrency": _MULTIMODAL_COMPARE_MAX_CONCURRENCY,
                "retry_after_sec": max(1, int(round(_MULTIMODAL_QUEUE_TIMEOUT_SEC))),
                "queue_wait_ms": queue_wait_ms,
            }), 429

        stage_start = time.perf_counter()
        result = multimodal_compare(
            origin_lat, origin_lon,
            destination_lat, destination_lon,
            allowed_modes=allowed_modes,
        )
        stage_ms["engine_compare_ms"] = round((time.perf_counter() - stage_start) * 1000, 2)
        stage_ms["total_ms"] = round((time.perf_counter() - request_start) * 1000, 2)

        if isinstance(result, dict):
            telemetry = result.get("telemetry")
            if not isinstance(telemetry, dict):
                telemetry = {}
            telemetry["api_compare_stage_ms"] = stage_ms
            telemetry["api_compare_allowed_modes"] = allowed_modes
            telemetry["queue_wait_ms"] = queue_wait_ms
            telemetry["queue_timeout_sec"] = float(_MULTIMODAL_QUEUE_TIMEOUT_SEC)
            result["telemetry"] = telemetry

        return jsonify(result)

    except Exception as e:
        print(f"[API] Multimodal hatasi: {e}")
        return jsonify({"error": f"Sunucu hatasi: {str(e)}"}), 500
    finally:
        if permit_acquired:
            _MULTIMODAL_COMPARE_SEMAPHORE.release()


if __name__ == "__main__":
    # Transit verilerini arka planda yukle
    if _transit_available:
        try:
            initialize_transit_data()
        except Exception as e:
            print(f"[Transit] Baslangic yukleme hatasi: {e}")

    # Port dinamik secimi (komut satiri parametresi veya env)
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[-1])
        except ValueError:
            pass
    env_port = os.getenv("PORT")
    if env_port:
        try:
            port = int(env_port)
        except ValueError:
            pass

    print("=" * 50)
    print("  OpenTrip API Sunucusu Baslatiliyor...")
    print(f"  http://localhost:{port}")
    print("=" * 50)
    initialize_runtime()
    if _PRELOAD_POPULAR_REGIONS_ON_STARTUP:
        initialize_graph_preload()
    app.run(debug=False, port=port)

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

        _preload_bert_async(force=True)
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
