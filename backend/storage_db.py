"""
storage_db.py - SQLite veritabani baglantisi ve sema

Rota ve lokasyon verileri icin ortak app_data.db kullanir.
"""

import os
import sqlite3
import threading

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "app_data.db")

os.makedirs(DATA_DIR, exist_ok=True)

_SCHEMA_READY = False
_SCHEMA_LOCK = threading.Lock()


def get_connection() -> sqlite3.Connection:
    """Veritabani baglantisi doner."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Performans optimizasyonlari
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -1048576;")   # 1 GB RAM cache ust siniri
    conn.execute("PRAGMA mmap_size = 1073741824;")  # 1 GB memory-mapped I/O
    conn.execute("PRAGMA temp_store = MEMORY;")

    return conn


def init_schema(conn: sqlite3.Connection, run_analyze: bool = False) -> None:
    """Tablolari olusturur (yoksa)."""
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS routes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            points TEXT NOT NULL,
            route_coords TEXT NOT NULL,
            distance_km REAL NOT NULL,
            duration_minutes INTEGER NOT NULL,
            route_type TEXT DEFAULT 'route_1',
            tags TEXT DEFAULT '[]',
            favorite INTEGER DEFAULT 0,
            times_used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS locations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            icon_type TEXT DEFAULT 'star',
            address TEXT DEFAULT '',
            favorite INTEGER DEFAULT 0,
            times_used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    # Indeksler
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_routes_favorite ON routes(favorite);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_routes_created_at ON routes(created_at DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_routes_favorite_created ON routes(favorite, created_at DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_routes_name ON routes(name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_favorite ON locations(favorite);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_created_at ON locations(created_at DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_favorite_created ON locations(favorite, created_at DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_name ON locations(name);")

    # Yerel yerler (geocoder fallback)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS local_places (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            display_name TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            place_type TEXT DEFAULT 'semt',
            search_terms TEXT DEFAULT ''
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_local_places_name ON local_places(name);")

    conn.commit()

    # ANALYZE pahali bir islem; sadece startup/bakimda calistir.
    if run_analyze:
        cursor.execute("ANALYZE;")
        conn.commit()


def ensure_db(run_analyze: bool = False, force: bool = False) -> None:
    """Veritabanini baslatir (surec basina bir kez)."""
    global _SCHEMA_READY

    if _SCHEMA_READY and not force:
        return

    with _SCHEMA_LOCK:
        if _SCHEMA_READY and not force:
            return

        conn = get_connection()
        try:
            init_schema(conn, run_analyze=run_analyze)
            _SCHEMA_READY = True
        finally:
            conn.close()


def run_sqlite_maintenance(checkpoint_mode: str = "PASSIVE") -> None:
    """WAL checkpoint calistirir."""
    allowed_modes = {"PASSIVE", "FULL", "RESTART", "TRUNCATE"}
    mode = checkpoint_mode.upper()
    if mode not in allowed_modes:
        mode = "PASSIVE"

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA wal_checkpoint({mode});")
    finally:
        conn.close()
