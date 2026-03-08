"""
route_storage.py - Rota Kaydetme ve Yükleme Sistemi

Kullanıcıların rotalarını kaydetmesini ve yüklemesini sağlar.
SQLite tabanlı depolama sistemi.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from storage_db import get_connection, ensure_db

# Eski JSON dosyası (migrasyon için)
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "data")
ROUTES_FILE = os.path.join(STORAGE_DIR, "saved_routes.json")


def _row_to_route(row) -> Dict:
    """SQLite satırını rota dict'ine çevirir."""
    try:
        points = json.loads(row["points"])
    except (json.JSONDecodeError, TypeError):
        points = []

    try:
        route_coords = json.loads(row["route_coords"])
    except (json.JSONDecodeError, TypeError):
        route_coords = []

    try:
        tags = json.loads(row["tags"]) if row["tags"] else []
    except (json.JSONDecodeError, TypeError):
        tags = []

    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"] or "",
        "points": points,
        "route_coords": route_coords,
        "distance_km": row["distance_km"],
        "duration_minutes": row["duration_minutes"],
        "route_type": row["route_type"] or "route_1",
        "tags": tags,
        "favorite": bool(row["favorite"]),
        "times_used": row["times_used"] or 0,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _migrate_from_json_if_needed() -> None:
    """Mevcut JSON verisi varsa SQLite'a taşır."""
    if not os.path.exists(ROUTES_FILE):
        return

    try:
        with open(ROUTES_FILE, "r", encoding="utf-8") as f:
            routes = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return

    if not routes:
        return

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM routes")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return  # Zaten veri var, migrate etme

    for route in routes:
        cursor.execute(
            """
            INSERT OR IGNORE INTO routes
            (id, name, description, points, route_coords, distance_km, duration_minutes,
             route_type, tags, favorite, times_used, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                route.get("id", str(uuid.uuid4())[:8]),
                route.get("name", ""),
                route.get("description", ""),
                json.dumps(route.get("points", [])),
                json.dumps(route.get("route_coords", [])),
                route.get("distance_km", 0),
                route.get("duration_minutes", 0),
                route.get("route_type", "route_1"),
                json.dumps(route.get("tags", [])),
                1 if route.get("favorite") else 0,
                route.get("times_used", 0),
                route.get("created_at", datetime.now().isoformat()),
                route.get("updated_at", datetime.now().isoformat()),
            ),
        )

    conn.commit()
    conn.close()
    print(f"[RouteStorage] JSON'dan {len(routes)} rota migrate edildi.")


def simplify_coords(coords: List[List[float]], tolerance: int = 3) -> List[List[float]]:
    """
    Koordinat listesini sıkıştırır — her N noktadan birini alır.
    Rota kaydetme hızını artırır.
    """
    if not coords or len(coords) <= 10:
        return coords
    return coords[::tolerance]


def save_route(
    name: str,
    points: List[List[float]],
    route_coords: List[List[float]],
    distance_km: float,
    duration_minutes: int,
    route_type: str = "route_1",
    description: str = "",
    tags: List[str] = None
) -> Dict:
    """Yeni bir rota kaydeder."""
    ensure_db()
    _migrate_from_json_if_needed()

    route_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    compact_route_coords = simplify_coords(route_coords)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO routes
        (id, name, description, points, route_coords, distance_km, duration_minutes,
         route_type, tags, favorite, times_used, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?)
        """,
        (
            route_id,
            name,
            description,
            json.dumps(points),
            json.dumps(compact_route_coords),
            distance_km,
            duration_minutes,
            route_type,
            json.dumps(tags or []),
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()

    print(f"[RouteStorage] Rota kaydedildi: {route_id} - {name}")
    return {
        "id": route_id,
        "name": name,
        "description": description,
        "points": points,
        "route_coords": compact_route_coords,
        "distance_km": distance_km,
        "duration_minutes": duration_minutes,
        "route_type": route_type,
        "tags": tags or [],
        "created_at": now,
        "updated_at": now,
        "favorite": False,
        "times_used": 0,
    }


def _get_route_by_id(route_id: str) -> Optional[Dict]:
    """ID'ye göre rota getirir (kullanım sayısını artırmadan)."""
    ensure_db()
    _migrate_from_json_if_needed()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM routes WHERE id = ?", (route_id,))
    row = cursor.fetchone()
    conn.close()

    return _row_to_route(row) if row else None


def get_route(route_id: str) -> Optional[Dict]:
    """ID'ye göre rota getirir (kullanım sayısını artırır)."""
    ensure_db()
    _migrate_from_json_if_needed()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM routes WHERE id = ?", (route_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    # Kullanım sayısını artır
    cursor.execute(
        "UPDATE routes SET times_used = times_used + 1, updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(), route_id),
    )
    conn.commit()
    cursor.execute("SELECT * FROM routes WHERE id = ?", (route_id,))
    row = cursor.fetchone()
    conn.close()

    return _row_to_route(row) if row else None


def get_all_routes(sort_by: str = "created_at", limit: int = None) -> List[Dict]:
    """Tüm rotaları getirir."""
    ensure_db()
    _migrate_from_json_if_needed()

    order = {
        "created_at": "created_at DESC",
        "name": "LOWER(name) ASC",
        "distance_km": "distance_km ASC",
        "times_used": "times_used DESC",
        "favorite": "favorite DESC, created_at DESC",
    }.get(sort_by, "created_at DESC")

    conn = get_connection()
    cursor = conn.cursor()
    sql = f"SELECT * FROM routes ORDER BY {order}"
    if limit:
        sql += f" LIMIT {int(limit)}"
    cursor.execute(sql)
    rows = cursor.fetchall()
    conn.close()

    return [_row_to_route(row) for row in rows]


def update_route(route_id: str, updates: Dict) -> Optional[Dict]:
    """Mevcut rotayı günceller."""
    ensure_db()

    # Güncellenebilir alanlar
    allowed = {"name", "description", "points", "route_coords", "distance_km",
               "duration_minutes", "route_type", "tags", "favorite"}
    updates = updates or {}
    updates = {k: v for k, v in updates.items() if k in allowed}

    if not updates:
        return _get_route_by_id(route_id)

    updates["updated_at"] = datetime.now().isoformat()

    # JSON alanları
    if "points" in updates:
        updates["points"] = json.dumps(updates["points"])
    if "route_coords" in updates:
        updates["route_coords"] = json.dumps(simplify_coords(updates["route_coords"]))
    if "tags" in updates:
        updates["tags"] = json.dumps(updates["tags"])
    if "favorite" in updates:
        updates["favorite"] = 1 if updates["favorite"] else 0

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [route_id]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE routes SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()

    if cursor.rowcount > 0:
        print(f"[RouteStorage] Rota güncellendi: {route_id}")
        return _get_route_by_id(route_id)
    return None


def delete_route(route_id: str) -> bool:
    """Rotayı siler."""
    ensure_db()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM routes WHERE id = ?", (route_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()

    if deleted:
        print(f"[RouteStorage] Rota silindi: {route_id}")
    return deleted


def toggle_favorite(route_id: str) -> Optional[Dict]:
    """Rotayı favorilere ekler/çıkarır."""
    ensure_db()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT favorite FROM routes WHERE id = ?", (route_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    new_fav = 0 if row["favorite"] else 1
    cursor.execute(
        "UPDATE routes SET favorite = ?, updated_at = ? WHERE id = ?",
        (new_fav, datetime.now().isoformat(), route_id),
    )
    conn.commit()
    conn.close()

    status = "eklendi" if new_fav else "çıkarıldı"
    print(f"[RouteStorage] Rota favorilerden {status}: {route_id}")
    return _get_route_by_id(route_id)


def search_routes(query: str) -> List[Dict]:
    """Rota adı veya açıklamasında arama yapar."""
    ensure_db()
    _migrate_from_json_if_needed()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM routes
        WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR tags LIKE ?
        ORDER BY created_at DESC
        """,
        (f"%{query.lower()}%", f"%{query.lower()}%", f"%{query.lower()}%"),
    )
    rows = cursor.fetchall()
    conn.close()

    return [_row_to_route(row) for row in rows]


def get_statistics() -> Dict:
    """Rota istatistiklerini döner."""
    ensure_db()
    _migrate_from_json_if_needed()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) as cnt, SUM(distance_km) as dist, SUM(duration_minutes) as dur, SUM(favorite) as fav FROM routes"
    )
    row = cursor.fetchone()
    cursor.execute("SELECT id, name, times_used FROM routes ORDER BY times_used DESC LIMIT 1")
    most_row = cursor.fetchone()
    conn.close()

    if not row or row["cnt"] == 0:
        return {
            "total_routes": 0,
            "total_distance_km": 0,
            "total_duration_minutes": 0,
            "favorite_count": 0,
            "most_used_route": None,
        }

    return {
        "total_routes": row["cnt"],
        "total_distance_km": round(row["dist"] or 0, 2),
        "total_duration_minutes": row["dur"] or 0,
        "favorite_count": row["fav"] or 0,
        "most_used_route": {
            "id": most_row["id"],
            "name": most_row["name"],
            "times_used": most_row["times_used"],
        } if most_row and (most_row["times_used"] or 0) > 0 else None,
    }
