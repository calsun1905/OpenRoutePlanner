"""
nlp_audit.py - NLP parse audit kayitlari.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from storage_db import ensure_db, get_connection


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _retention_days() -> int:
    raw = os.getenv("ORP_NLP_AUDIT_RETENTION_DAYS", "21").strip()
    try:
        days = int(raw)
    except (TypeError, ValueError):
        days = 21
    return max(7, days)


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return "{}"


def ensure_nlp_audit_schema() -> None:
    ensure_db()
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nlp_parse_audit (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                request_id TEXT DEFAULT '',
                correlation_id TEXT DEFAULT '',
                engine TEXT DEFAULT '',
                query_redacted TEXT NOT NULL,
                query_type TEXT DEFAULT '',
                confidence REAL DEFAULT 0.0,
                parse_time_ms REAL DEFAULT 0.0,
                origin_place TEXT DEFAULT '',
                destination_place TEXT DEFAULT '',
                location_place TEXT DEFAULT '',
                locations_json TEXT DEFAULT '[]',
                detected_places_json TEXT DEFAULT '[]',
                poi_concept TEXT DEFAULT '',
                poi_tags_hint_json TEXT DEFAULT '{}',
                poi_resolution_source TEXT DEFAULT '',
                poi_resolution_confidence REAL DEFAULT 0.0,
                poi_resolution_status TEXT DEFAULT '',
                poi_osm_queries_json TEXT DEFAULT '[]',
                trace_json TEXT DEFAULT '{}',
                error_text TEXT DEFAULT ''
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_nlp_parse_audit_created_at ON nlp_parse_audit(created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_nlp_parse_audit_query_type ON nlp_parse_audit(query_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_nlp_parse_audit_engine ON nlp_parse_audit(engine)"
        )
        conn.commit()
    finally:
        conn.close()


def _cleanup_old_rows(conn) -> None:
    retention = _retention_days()
    cutoff_ts = time.time() - (retention * 86400)
    cutoff_iso = datetime.fromtimestamp(cutoff_ts, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    conn.execute(
        "DELETE FROM nlp_parse_audit WHERE created_at < ?",
        (cutoff_iso,),
    )


def log_nlp_parse_audit(
    *,
    query_redacted: str,
    result: dict[str, Any] | None,
    request_id: str = "",
    correlation_id: str = "",
    error_text: str = "",
) -> str:
    """
    Parse sonucunu audit tablosuna kaydeder.
    """
    ensure_nlp_audit_schema()
    result = result or {}
    row_id = str(uuid.uuid4())
    created_at = _now_iso()

    locations = result.get("locations")
    if not isinstance(locations, list):
        locations = []
    detected_places = result.get("detected_places")
    if not isinstance(detected_places, list):
        detected_places = []
    poi_tags_hint = result.get("poi_tags_hint")
    if not isinstance(poi_tags_hint, dict):
        poi_tags_hint = {}
    poi_osm_queries = result.get("poi_osm_queries")
    if not isinstance(poi_osm_queries, list):
        poi_osm_queries = []
    trace = result.get("trace")
    if not isinstance(trace, dict):
        trace = {}

    parse_time = result.get("parse_time")
    parse_time_ms = 0.0
    try:
        parse_time_ms = round(float(parse_time or 0.0) * 1000.0, 2)
    except (TypeError, ValueError):
        parse_time_ms = 0.0

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO nlp_parse_audit (
                id, created_at, request_id, correlation_id, engine,
                query_redacted, query_type, confidence, parse_time_ms,
                origin_place, destination_place, location_place,
                locations_json, detected_places_json,
                poi_concept, poi_tags_hint_json,
                poi_resolution_source, poi_resolution_confidence, poi_resolution_status,
                poi_osm_queries_json, trace_json, error_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                created_at,
                str(request_id or ""),
                str(correlation_id or ""),
                str(result.get("engine") or ""),
                str(query_redacted or ""),
                str(result.get("type") or "unknown"),
                float(result.get("confidence") or 0.0),
                float(parse_time_ms),
                str(result.get("origin") or ""),
                str(result.get("destination") or ""),
                str(result.get("location") or ""),
                _safe_json(locations),
                _safe_json(detected_places),
                str(result.get("poi_concept") or ""),
                _safe_json(poi_tags_hint),
                str(result.get("poi_resolution_source") or ""),
                float(result.get("poi_resolution_confidence") or 0.0),
                str(result.get("poi_resolution_status") or ""),
                _safe_json(poi_osm_queries),
                _safe_json(trace),
                str(error_text or ""),
            ),
        )
        _cleanup_old_rows(conn)
        conn.commit()
    finally:
        conn.close()

    return row_id


def list_recent_nlp_parse_audits(limit: int = 50) -> list[dict[str, Any]]:
    ensure_nlp_audit_schema()
    safe_limit = max(1, min(int(limit), 500))
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, created_at, request_id, correlation_id, engine, query_redacted,
                   query_type, confidence, parse_time_ms, origin_place, destination_place,
                   location_place, locations_json, detected_places_json, poi_concept,
                   poi_tags_hint_json, poi_resolution_source, poi_resolution_confidence,
                   poi_resolution_status, poi_osm_queries_json, error_text
            FROM nlp_parse_audit
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

        out: list[dict[str, Any]] = []
        for row in rows:
            def _loads_or(raw: Any, fallback: Any):
                try:
                    if raw is None or raw == "":
                        return fallback
                    return json.loads(raw)
                except Exception:
                    return fallback

            out.append(
                {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "request_id": row["request_id"] or "",
                    "correlation_id": row["correlation_id"] or "",
                    "engine": row["engine"] or "",
                    "query_redacted": row["query_redacted"] or "",
                    "query_type": row["query_type"] or "unknown",
                    "confidence": float(row["confidence"] or 0.0),
                    "parse_time_ms": float(row["parse_time_ms"] or 0.0),
                    "origin_place": row["origin_place"] or "",
                    "destination_place": row["destination_place"] or "",
                    "location_place": row["location_place"] or "",
                    "locations": _loads_or(row["locations_json"], []),
                    "detected_places": _loads_or(row["detected_places_json"], []),
                    "poi_concept": row["poi_concept"] or "",
                    "poi_tags_hint": _loads_or(row["poi_tags_hint_json"], {}),
                    "poi_resolution_source": row["poi_resolution_source"] or "",
                    "poi_resolution_confidence": float(row["poi_resolution_confidence"] or 0.0),
                    "poi_resolution_status": row["poi_resolution_status"] or "",
                    "poi_osm_queries": _loads_or(row["poi_osm_queries_json"], []),
                    "error_text": row["error_text"] or "",
                }
            )
        return out
    finally:
        conn.close()
