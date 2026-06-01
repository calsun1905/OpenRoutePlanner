"""
llm_health.py - LLM model health tracking and cooldown logic.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

from storage_db import ensure_db, get_connection


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_provider(provider: str) -> str:
    p = str(provider or "").strip().lower()
    if p not in {"openrouter", "gemini"}:
        return "openrouter"
    return p


def _normalize_model(model: str) -> str:
    return str(model or "").strip()


def _cooldown_seconds() -> int:
    raw = os.getenv("ORP_LLM_COOLDOWN_SECONDS", "900").strip()
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 900
    return max(60, value)


def _failure_threshold() -> int:
    raw = os.getenv("ORP_LLM_FAILURE_THRESHOLD", "3").strip()
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 3
    return max(2, value)


def ensure_llm_health_schema() -> None:
    ensure_db()
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_model_health (
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                success_count INTEGER NOT NULL DEFAULT 0,
                failure_count INTEGER NOT NULL DEFAULT 0,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                last_error_type TEXT DEFAULT '',
                last_error TEXT DEFAULT '',
                last_success_at TEXT DEFAULT '',
                last_failure_at TEXT DEFAULT '',
                cooldown_until INTEGER NOT NULL DEFAULT 0,
                last_latency_ms INTEGER,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(provider, model)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_llm_health_provider ON llm_model_health(provider)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_llm_health_cooldown ON llm_model_health(provider, cooldown_until)"
        )
        conn.commit()
    finally:
        conn.close()


def record_attempt(
    *,
    provider: str,
    model: str,
    success: bool,
    error_type: str = "",
    error_text: str = "",
    latency_ms: int | None = None,
) -> None:
    prov = _normalize_provider(provider)
    mdl = _normalize_model(model)
    if not mdl:
        return

    ensure_llm_health_schema()
    now_ts = int(time.time())
    now_iso = _now_iso()
    cooldown = _cooldown_seconds()
    threshold = _failure_threshold()

    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT success_count, failure_count, consecutive_failures
            FROM llm_model_health
            WHERE provider = ? AND model = ?
            """,
            (prov, mdl),
        ).fetchone()

        success_count = int(row["success_count"] or 0) if row else 0
        failure_count = int(row["failure_count"] or 0) if row else 0
        consecutive_failures = int(row["consecutive_failures"] or 0) if row else 0

        if success:
            success_count += 1
            consecutive_failures = 0
            cooldown_until = 0
            last_error_type = ""
            last_error = ""
            last_success_at = now_iso
            last_failure_at = ""
        else:
            failure_count += 1
            consecutive_failures += 1
            cooldown_until = now_ts + cooldown if consecutive_failures >= threshold else 0
            last_error_type = str(error_type or "")
            last_error = str(error_text or "")[:500]
            last_success_at = ""
            last_failure_at = now_iso

        conn.execute(
            """
            INSERT INTO llm_model_health (
                provider, model, success_count, failure_count, consecutive_failures,
                last_error_type, last_error, last_success_at, last_failure_at,
                cooldown_until, last_latency_ms, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider, model) DO UPDATE SET
                success_count = excluded.success_count,
                failure_count = excluded.failure_count,
                consecutive_failures = excluded.consecutive_failures,
                last_error_type = excluded.last_error_type,
                last_error = excluded.last_error,
                last_success_at = CASE
                    WHEN excluded.last_success_at != '' THEN excluded.last_success_at
                    ELSE llm_model_health.last_success_at
                END,
                last_failure_at = CASE
                    WHEN excluded.last_failure_at != '' THEN excluded.last_failure_at
                    ELSE llm_model_health.last_failure_at
                END,
                cooldown_until = excluded.cooldown_until,
                last_latency_ms = excluded.last_latency_ms,
                updated_at = excluded.updated_at
            """,
            (
                prov,
                mdl,
                success_count,
                failure_count,
                consecutive_failures,
                last_error_type,
                last_error,
                last_success_at,
                last_failure_at,
                int(cooldown_until),
                latency_ms,
                now_iso,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_provider_health(provider: str) -> list[dict[str, Any]]:
    prov = _normalize_provider(provider)
    ensure_llm_health_schema()
    now_ts = int(time.time())
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT provider, model, success_count, failure_count, consecutive_failures,
                   last_error_type, last_error, last_success_at, last_failure_at,
                   cooldown_until, last_latency_ms, updated_at
            FROM llm_model_health
            WHERE provider = ?
            ORDER BY updated_at DESC, model ASC
            """,
            (prov,),
        ).fetchall()

        result: list[dict[str, Any]] = []
        for row in rows:
            cooldown_until = int(row["cooldown_until"] or 0)
            blocked = cooldown_until > now_ts
            result.append(
                {
                    "provider": row["provider"],
                    "model": row["model"],
                    "success_count": int(row["success_count"] or 0),
                    "failure_count": int(row["failure_count"] or 0),
                    "consecutive_failures": int(row["consecutive_failures"] or 0),
                    "last_error_type": row["last_error_type"] or "",
                    "last_error": row["last_error"] or "",
                    "last_success_at": row["last_success_at"] or "",
                    "last_failure_at": row["last_failure_at"] or "",
                    "cooldown_until": cooldown_until,
                    "blocked": blocked,
                    "remaining_cooldown_sec": max(0, cooldown_until - now_ts),
                    "last_latency_ms": row["last_latency_ms"],
                    "updated_at": row["updated_at"],
                }
            )
        return result
    finally:
        conn.close()


def is_model_blocked(provider: str, model: str) -> bool:
    prov = _normalize_provider(provider)
    mdl = _normalize_model(model)
    if not mdl:
        return False
    ensure_llm_health_schema()
    now_ts = int(time.time())
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT cooldown_until
            FROM llm_model_health
            WHERE provider = ? AND model = ?
            """,
            (prov, mdl),
        ).fetchone()
        if not row:
            return False
        return int(row["cooldown_until"] or 0) > now_ts
    finally:
        conn.close()

