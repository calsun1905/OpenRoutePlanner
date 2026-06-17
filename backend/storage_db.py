"""
storage_db.py - SQLite veritabani baglantisi ve sema

Rota ve lokasyon verileri icin ortak app_data.db kullanir.
Connection pooling ile performans iyilestirmesi.
"""

import os
import sqlite3
import threading
import time
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "app_data.db")

os.makedirs(DATA_DIR, exist_ok=True)

_SCHEMA_READY = False
_SCHEMA_LOCK = threading.Lock()

# Connection pooling: Her thread icin tek bir connection
# Bu sayede ayni thread'deki istekler ayni baglantiyi tekrar kullanir
_thread_local = threading.local()

# Connection pool yapilandirmasi
_MAX_CONNECTION_AGE_SECONDS = 300  # 5 dakika sonra baglanti yenilensin
_POOL_ENABLED = True  # Connection pooling aktif/pasif


class _PooledConnection:
    """
    Connection wrapper sınıfı.
    close() çağrıldığında bağlantıyı gerçekten kapatmak yerine
    pool'a geri döndürür. Bu sayede mevcut kodla uyumludur.
    """

    def __init__(self, conn: sqlite3.Connection, pool_key: str = 'default'):
        self._conn = conn
        self._pool_key = pool_key
        self._closed = False

    def __getattr__(self, name):
        """Tüm çağrıları gerçek bağlantıya yönlendir."""
        if self._closed:
            raise sqlite3.ProgrammingError("Connection is closed")
        return getattr(self._conn, name)

    def cursor(self):
        """Cursor döndür."""
        if self._closed:
            raise sqlite3.ProgrammingError("Connection is closed")
        return self._conn.cursor()

    def execute(self, sql, parameters=()):
        """SQL çalıştır."""
        if self._closed:
            raise sqlite3.ProgrammingError("Connection is closed")
        return self._conn.execute(sql, parameters)

    def executemany(self, sql, seq_of_parameters=()):
        """Çoklu SQL çalıştır."""
        if self._closed:
            raise sqlite3.ProgrammingError("Connection is closed")
        return self._conn.executemany(sql, seq_of_parameters)

    def commit(self):
        """Transaction commit."""
        if self._closed:
            raise sqlite3.ProgrammingError("Connection is closed")
        return self._conn.commit()

    def rollback(self):
        """Transaction rollback."""
        if self._closed:
            raise sqlite3.ProgrammingError("Connection is closed")
        return self._conn.rollback()

    def close(self):
        """
        Baglantiyi kapatir.
        Pool modunda: Gerçekten kapatmaz, sadece işaretler.
        Normal modunda: Gerçekten kapatır.
        """
        if self._closed:
            return

        self._closed = True
        # Pool'da tutulan referansı temizle
        if hasattr(_thread_local, 'connection') and _thread_local.connection is self._conn:
            _thread_local.connection = None

    @property
    def row_factory(self):
        return self._conn.row_factory

    @row_factory.setter
    def row_factory(self, value):
        self._conn.row_factory = value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def _create_connection() -> sqlite3.Connection:
    """Yeni bir baglanti olusturur ve performans ayarlarini yapar."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Performans optimizasyonlari
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -1048576;")   # 1 GB RAM cache ust siniri
    conn.execute("PRAGMA mmap_size = 1073741824;")  # 1 GB memory-mapped I/O
    conn.execute("PRAGMA temp_store = MEMORY;")

    return conn


def get_connection() -> sqlite3.Connection:
    """
    Veritabani baglantisi doner.
    Connection pooling: Ayni thread'deki cagrilarda ayni baglantiyi tekrar kullanir.

    Not: close() çağrıldığında bağlantı pool'a döner, gerçekten kapanmaz.
    """
    if not _POOL_ENABLED:
        return _create_connection()

    current_time = time.time()

    # Thread-local connection kontrol et
    if not hasattr(_thread_local, 'raw_connection') or _thread_local.raw_connection is None:
        _thread_local.raw_connection = _create_connection()
        _thread_local.connection_created_at = current_time
        return _PooledConnection(_thread_local.raw_connection)

    # Baglanti yaslanmis mi kontrol et
    conn_age = current_time - _thread_local.connection_created_at
    if conn_age > _MAX_CONNECTION_AGE_SECONDS:
        # Eski baglantiyi kapat ve yenisini olustur
        try:
            _thread_local.raw_connection.close()
        except Exception:
            pass  # Zaten kapali olabilir
        _thread_local.raw_connection = _create_connection()
        _thread_local.connection_created_at = current_time
        return _PooledConnection(_thread_local.raw_connection)

    # Baglanti hala gecerli mi kontrol et
    try:
        _thread_local.raw_connection.execute("SELECT 1")
    except sqlite3.Error:
        # Baglanti bozulmus, yenisini olustur
        _thread_local.raw_connection = _create_connection()
        _thread_local.connection_created_at = current_time

    return _PooledConnection(_thread_local.raw_connection)


def close_connection() -> None:
    """
    Mevcut thread'in baglantisini kapatir.
    Connection pool'u temizlemek icin kullanilabilir.
    """
    if hasattr(_thread_local, 'raw_connection') and _thread_local.raw_connection is not None:
        try:
            _thread_local.raw_connection.close()
        except Exception:
            pass
        _thread_local.raw_connection = None


def close_all_connections() -> None:
    """
    Tum thread'lerin baglantilarini kapatir.
    Uygulama kapatilirken cagrilmalidir.
    """
    global _thread_local
    close_connection()
    _thread_local = threading.local()


def _get_table_columns(cursor: sqlite3.Cursor, table_name: str) -> set[str]:
    """Tablodaki mevcut kolon adlarini doner."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    rows = cursor.fetchall()
    columns = set()
    for row in rows:
        try:
            columns.add(str(row["name"]))
        except (TypeError, KeyError, IndexError):
            columns.add(str(row[1]))
    return columns


def _ensure_column(cursor: sqlite3.Cursor, table_name: str, column_name: str, ddl: str) -> None:
    """Kolon yoksa ekler."""
    if column_name in _get_table_columns(cursor, table_name):
        return
    cursor.execute(ddl)


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
            route_payload TEXT DEFAULT NULL,
            tags TEXT DEFAULT '[]',
            favorite INTEGER DEFAULT 0,
            times_used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    _ensure_column(
        cursor,
        "routes",
        "route_payload",
        "ALTER TABLE routes ADD COLUMN route_payload TEXT DEFAULT NULL",
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

    # LLM sohbet kaliciligi
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
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON chat_messages(session_id, created_at);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_sessions_archived ON chat_sessions(archived);"
    )

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
