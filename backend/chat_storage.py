"""
chat_storage.py - LLM sohbet oturumu ve mesaj kaliciligi
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from storage_db import DATA_DIR, ensure_db, get_connection
from text_utils import repair_text

CHAT_SYNC_JSON_PATH = os.path.join(DATA_DIR, "chat_history.sync.json")
_SYNC_LOCK = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _session_title_from_text(text: str, fallback: str = "Yeni Sohbet") -> str:
    cleaned = repair_text(text)
    if not cleaned:
        return fallback
    normalized = " ".join(cleaned.split())
    if len(normalized) > 60:
        return normalized[:57].rstrip() + "..."
    return normalized


def ensure_chat_schema() -> None:
    ensure_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0,
                message_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model TEXT DEFAULT '',
                token_total INTEGER,
                error_type TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES chat_sessions(id)
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON chat_messages(session_id, created_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_sessions_archived ON chat_sessions(archived)"
        )
        conn.commit()
    finally:
        conn.close()


def _dump_history_locked(conn) -> dict[str, Any]:
    sessions_rows = conn.execute(
        """
        SELECT id, title, created_at, updated_at, archived, message_count
        FROM chat_sessions
        ORDER BY archived ASC, updated_at DESC, created_at DESC, id ASC
        """
    ).fetchall()
    messages_rows = conn.execute(
        """
        SELECT id, session_id, role, content, model, token_total, error_type, created_at
        FROM chat_messages
        ORDER BY session_id ASC, created_at ASC, id ASC
        """
    ).fetchall()

    sessions = [
        {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "archived": int(row["archived"] or 0),
            "message_count": int(row["message_count"] or 0),
        }
        for row in sessions_rows
    ]
    messages = [
        {
            "id": row["id"],
            "session_id": row["session_id"],
            "role": row["role"],
            "content": row["content"],
            "model": row["model"] or "",
            "token_total": row["token_total"],
            "error_type": row["error_type"] or "",
            "created_at": row["created_at"],
        }
        for row in messages_rows
    ]
    return {
        "version": 1,
        "updated_at": _now_iso(),
        "sessions": sessions,
        "messages": messages,
    }


def _write_sync_json_atomic(payload: dict[str, Any]) -> None:
    directory = os.path.dirname(CHAT_SYNC_JSON_PATH)
    os.makedirs(directory, exist_ok=True)
    temp_path = CHAT_SYNC_JSON_PATH + ".tmp"
    with open(temp_path, "w", encoding="utf-8", newline="\n") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(temp_path, CHAT_SYNC_JSON_PATH)


def sync_json_from_db() -> None:
    ensure_chat_schema()
    with _SYNC_LOCK:
        conn = get_connection()
        try:
            payload = _dump_history_locked(conn)
            _write_sync_json_atomic(payload)
        finally:
            conn.close()


def rebuild_db_from_sync_json(force: bool = False) -> bool:
    """
    JSON mirror dosyasindan SQLite chat tablolarini doldurur.
    force=False ise DB'de sohbet verisi varsa dokunmaz.
    """
    ensure_chat_schema()
    if not os.path.exists(CHAT_SYNC_JSON_PATH):
        return False

    with _SYNC_LOCK:
        try:
            with open(CHAT_SYNC_JSON_PATH, "r", encoding="utf-8") as fp:
                payload = json.load(fp)
        except (OSError, json.JSONDecodeError):
            return False

        sessions = payload.get("sessions")
        messages = payload.get("messages")
        if not isinstance(sessions, list) or not isinstance(messages, list):
            return False

        conn = get_connection()
        try:
            cursor = conn.cursor()
            existing_count = cursor.execute("SELECT COUNT(*) FROM chat_sessions").fetchone()[0]
            if existing_count > 0 and not force:
                return False

            cursor.execute("DELETE FROM chat_messages")
            cursor.execute("DELETE FROM chat_sessions")

            for session in sessions:
                sid = str(session.get("id", "")).strip()
                if not sid:
                    continue
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO chat_sessions
                    (id, title, created_at, updated_at, archived, message_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sid,
                        _session_title_from_text(str(session.get("title", ""))),
                        str(session.get("created_at") or _now_iso()),
                        str(session.get("updated_at") or _now_iso()),
                        int(session.get("archived") or 0),
                        int(session.get("message_count") or 0),
                    ),
                )

            for message in messages:
                mid = str(message.get("id", "")).strip() or str(uuid.uuid4())
                sid = str(message.get("session_id", "")).strip()
                role = str(message.get("role", "")).strip().lower()
                if not sid or role not in {"system", "user", "assistant"}:
                    continue
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO chat_messages
                    (id, session_id, role, content, model, token_total, error_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mid,
                        sid,
                        role,
                        repair_text(str(message.get("content", ""))),
                        repair_text(str(message.get("model", ""))),
                        message.get("token_total"),
                        repair_text(str(message.get("error_type", ""))),
                        str(message.get("created_at") or _now_iso()),
                    ),
                )

            cursor.execute(
                """
                UPDATE chat_sessions
                SET message_count = (
                    SELECT COUNT(*)
                    FROM chat_messages m
                    WHERE m.session_id = chat_sessions.id
                )
                """
            )
            conn.commit()
            return True
        finally:
            conn.close()


def create_session(title: str | None = None) -> dict[str, Any]:
    ensure_chat_schema()
    session_id = str(uuid.uuid4())
    now = _now_iso()
    safe_title = _session_title_from_text(title or "", fallback="Yeni Sohbet")
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO chat_sessions (id, title, created_at, updated_at, archived, message_count)
            VALUES (?, ?, ?, ?, 0, 0)
            """,
            (session_id, safe_title, now, now),
        )
        conn.commit()
    finally:
        conn.close()
    sync_json_from_db()
    return {
        "id": session_id,
        "title": safe_title,
        "created_at": now,
        "updated_at": now,
        "archived": 0,
        "message_count": 0,
    }


def list_sessions(include_archived: bool = False, limit: int = 200) -> list[dict[str, Any]]:
    ensure_chat_schema()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if include_archived:
            rows = cursor.execute(
                """
                SELECT id, title, created_at, updated_at, archived, message_count
                FROM chat_sessions
                ORDER BY archived ASC, updated_at DESC, created_at DESC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
        else:
            rows = cursor.execute(
                """
                SELECT id, title, created_at, updated_at, archived, message_count
                FROM chat_sessions
                WHERE archived = 0
                ORDER BY updated_at DESC, created_at DESC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "archived": int(row["archived"] or 0),
                "message_count": int(row["message_count"] or 0),
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_session(session_id: str) -> dict[str, Any] | None:
    ensure_chat_schema()
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, title, created_at, updated_at, archived, message_count
            FROM chat_sessions
            WHERE id = ?
            """,
            (session_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "archived": int(row["archived"] or 0),
            "message_count": int(row["message_count"] or 0),
        }
    finally:
        conn.close()


def archive_session(session_id: str) -> bool:
    ensure_chat_schema()
    now = _now_iso()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chat_sessions SET archived = 1, updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        changed = cursor.rowcount > 0
        conn.commit()
    finally:
        conn.close()
    if changed:
        sync_json_from_db()
    return changed


def list_messages(session_id: str, limit: int | None = None) -> list[dict[str, Any]]:
    ensure_chat_schema()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if limit is None:
            rows = cursor.execute(
                """
                SELECT id, session_id, role, content, model, token_total, error_type, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (session_id,),
            ).fetchall()
        else:
            take = max(1, int(limit))
            rows = cursor.execute(
                """
                SELECT id, session_id, role, content, model, token_total, error_type, created_at
                FROM (
                    SELECT id, session_id, role, content, model, token_total, error_type, created_at
                    FROM chat_messages
                    WHERE session_id = ?
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                )
                ORDER BY created_at ASC, id ASC
                """,
                (session_id, take),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "session_id": row["session_id"],
                "role": row["role"],
                "content": row["content"],
                "model": row["model"] or "",
                "token_total": row["token_total"],
                "error_type": row["error_type"] or "",
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    finally:
        conn.close()


def save_turn(
    *,
    session_id: str,
    user_text: str,
    assistant_text: str,
    model: str = "",
    token_total: int | None = None,
    error_type: str = "",
) -> None:
    ensure_chat_schema()
    now = _now_iso()
    user_mid = str(uuid.uuid4())
    assistant_mid = str(uuid.uuid4())
    clean_user_text = repair_text(user_text)
    clean_assistant_text = repair_text(assistant_text)
    clean_model = repair_text(model)
    clean_error_type = repair_text(error_type)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Session title'ini ilk mesaja gore insana okunur tut.
        row = cursor.execute(
            "SELECT title, message_count FROM chat_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            raise ValueError("Sohbet oturumu bulunamadi")

        title = row["title"] or "Yeni Sohbet"
        msg_count = int(row["message_count"] or 0)
        if msg_count == 0 and clean_user_text:
            title = _session_title_from_text(clean_user_text)

        cursor.execute(
            """
            INSERT INTO chat_messages
            (id, session_id, role, content, model, token_total, error_type, created_at)
            VALUES (?, ?, 'user', ?, ?, ?, '', ?)
            """,
            (user_mid, session_id, clean_user_text, clean_model, token_total, now),
        )
        cursor.execute(
            """
            INSERT INTO chat_messages
            (id, session_id, role, content, model, token_total, error_type, created_at)
            VALUES (?, ?, 'assistant', ?, ?, ?, ?, ?)
            """,
            (assistant_mid, session_id, clean_assistant_text, clean_model, token_total, clean_error_type, now),
        )
        cursor.execute(
            """
            UPDATE chat_sessions
            SET title = ?, updated_at = ?, message_count = message_count + 2
            WHERE id = ?
            """,
            (title, now, session_id),
        )
        conn.commit()
    finally:
        conn.close()

    sync_json_from_db()

