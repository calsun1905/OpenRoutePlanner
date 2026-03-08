"""
location_storage.py - Kullanıcı Lokasyon Kaydetme ve Yükleme Sistemi

Kullanıcıların harita üzerinden özel isimlerle ("Ev", "Okul", vb.)
konum kaydetmesini ve bu listeyi yönetmesini sağlar.
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
LOCATIONS_FILE = os.path.join(STORAGE_DIR, "saved_locations.json")


def _row_to_location(row) -> Dict:
    """SQLite satırını lokasyon dict'ine çevirir."""
    return {
        "id": row["id"],
        "name": row["name"],
        "lat": row["lat"],
        "lon": row["lon"],
        "icon_type": row["icon_type"] or "star",
        "address": row["address"] or "",
        "favorite": bool(row["favorite"]),
        "times_used": row["times_used"] or 0,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _migrate_from_json_if_needed() -> None:
    """Mevcut JSON verisi varsa SQLite'a taşır."""
    if not os.path.exists(LOCATIONS_FILE):
        return

    try:
        with open(LOCATIONS_FILE, "r", encoding="utf-8") as f:
            locations = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return

    if not locations:
        return

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM locations")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return  # Zaten veri var

    for loc in locations:
        cursor.execute(
            """
            INSERT OR IGNORE INTO locations
            (id, name, lat, lon, icon_type, address, favorite, times_used, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                loc.get("id", str(uuid.uuid4())[:8]),
                loc.get("name", ""),
                loc.get("lat", 0),
                loc.get("lon", 0),
                loc.get("icon_type", "star"),
                loc.get("address", ""),
                1 if loc.get("favorite") else 0,
                loc.get("times_used", 0),
                loc.get("created_at", datetime.now().isoformat()),
                loc.get("updated_at", datetime.now().isoformat()),
            ),
        )

    conn.commit()
    conn.close()
    print(f"[LocationStorage] JSON'dan {len(locations)} lokasyon migrate edildi.")


def save_location(
    name: str,
    lat: float,
    lon: float,
    icon_type: str = "star",
    address: str = ""
) -> Dict:
    """Yeni bir lokasyon kaydeder."""
    ensure_db()
    _migrate_from_json_if_needed()

    location_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO locations
        (id, name, lat, lon, icon_type, address, favorite, times_used, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, ?)
        """,
        (location_id, name, lat, lon, icon_type, address, now, now),
    )
    conn.commit()
    conn.close()

    print(f"[LocationStorage] Lokasyon kaydedildi: {location_id} - {name} ({icon_type})")
    return {
        "id": location_id,
        "name": name,
        "lat": lat,
        "lon": lon,
        "icon_type": icon_type,
        "address": address,
        "favorite": False,
        "times_used": 0,
        "created_at": now,
        "updated_at": now,
    }


def toggle_location_favorite(location_id: str) -> Optional[Dict]:
    """Lokasyonun favori durumunu değiştirir."""
    ensure_db()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT favorite FROM locations WHERE id = ?", (location_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    new_fav = 0 if row["favorite"] else 1
    cursor.execute(
        "UPDATE locations SET favorite = ?, updated_at = ? WHERE id = ?",
        (new_fav, datetime.now().isoformat(), location_id),
    )
    conn.commit()
    conn.close()

    print(f"[LocationStorage] Favori güncellendi: {location_id} -> {bool(new_fav)}")
    return _get_location_by_id(location_id)


def _get_location_by_id(location_id: str) -> Optional[Dict]:
    """ID ile tek lokasyon getirir."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM locations WHERE id = ?", (location_id,))
    row = cursor.fetchone()
    conn.close()
    return _row_to_location(row) if row else None


def get_all_locations(sort_by: str = "created_at", limit: int = None) -> List[Dict]:
    """Tüm lokasyonları getirir."""
    ensure_db()
    _migrate_from_json_if_needed()

    order = {
        "created_at": "created_at DESC",
        "name": "LOWER(name) ASC",
        "times_used": "times_used DESC",
        "favorite": "favorite DESC, created_at DESC",
    }.get(sort_by, "created_at DESC")

    conn = get_connection()
    cursor = conn.cursor()
    sql = f"SELECT * FROM locations ORDER BY {order}"
    if limit:
        sql += f" LIMIT {int(limit)}"
    cursor.execute(sql)
    rows = cursor.fetchall()
    conn.close()

    return [_row_to_location(row) for row in rows]


def increment_usage(location_id: str) -> Optional[Dict]:
    """Lokasyonun kullanım sayısını artırır."""
    ensure_db()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE locations SET times_used = times_used + 1, updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(), location_id),
    )
    conn.commit()
    conn.close()

    return _get_location_by_id(location_id)


def update_location(location_id: str, updates: Dict) -> Optional[Dict]:
    """Mevcut lokasyonu günceller."""
    ensure_db()

    allowed = {"name", "lat", "lon", "icon_type", "address"}
    updates = {k: v for k, v in updates.items() if k in allowed}

    if not updates:
        return _get_location_by_id(location_id)

    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [location_id]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE locations SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()

    if cursor.rowcount > 0:
        print(f"[LocationStorage] Lokasyon güncellendi: {location_id}")
        return _get_location_by_id(location_id)
    return None


def delete_location(location_id: str) -> bool:
    """Lokasyonu siler."""
    ensure_db()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM locations WHERE id = ?", (location_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()

    if deleted:
        print(f"[LocationStorage] Lokasyon silindi: {location_id}")
    return deleted


def search_locations_by_name(query: str) -> List[Dict]:
    """Lokasyon adında arama yapar."""
    ensure_db()
    _migrate_from_json_if_needed()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM locations WHERE LOWER(name) LIKE ? ORDER BY name",
        (f"%{query.lower()}%",),
    )
    rows = cursor.fetchall()
    conn.close()

    return [_row_to_location(row) for row in rows]
