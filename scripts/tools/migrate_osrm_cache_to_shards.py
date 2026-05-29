"""
Migrate multimodal OSRM SQLite cache from a single DB file into sharded DB files.

Design goals:
- No data loss: source rows are copied with all columns preserved.
- Deterministic placement: shard index is derived from key_hash.
- Verifiable output: row/key counts are compared after migration.

Usage:
  python scripts/tools/migrate_osrm_cache_to_shards.py
  python scripts/tools/migrate_osrm_cache_to_shards.py --shard-count 16 --vacuum
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS osrm_route_cache (
    key_hash TEXT PRIMARY KEY,
    route_kind TEXT NOT NULL,
    key_json TEXT NOT NULL,
    coords_json TEXT NOT NULL,
    point_count INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
)
"""

INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_osrm_route_cache_created ON osrm_route_cache(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_osrm_route_cache_kind ON osrm_route_cache(route_kind);",
]

UPSERT_SQL = """
INSERT INTO osrm_route_cache
    (key_hash, route_kind, key_json, coords_json, point_count, created_at, updated_at)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(key_hash) DO UPDATE SET
    route_kind = excluded.route_kind,
    key_json = excluded.key_json,
    coords_json = excluded.coords_json,
    point_count = excluded.point_count,
    created_at = excluded.created_at,
    updated_at = excluded.updated_at
"""


@dataclass
class Stats:
    rows: int
    unique_keys: int


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(SCHEMA_SQL)
    for sql in INDEX_SQL:
        conn.execute(sql)
    conn.commit()


def _count_stats(conn: sqlite3.Connection) -> Stats:
    row_total = conn.execute("SELECT COUNT(*) AS n FROM osrm_route_cache").fetchone()
    row_unique = conn.execute("SELECT COUNT(DISTINCT key_hash) AS n FROM osrm_route_cache").fetchone()
    return Stats(
        rows=int(row_total["n"] if row_total else 0),
        unique_keys=int(row_unique["n"] if row_unique else 0),
    )


def _shard_width(shard_count: int) -> int:
    return max(2, len(f"{int(shard_count) - 1:x}"))


def _shard_path(shard_dir: Path, shard_count: int, shard_idx: int) -> Path:
    return shard_dir / f"{int(shard_idx):0{_shard_width(shard_count)}x}" / "osrm_cache.db"


def _shard_idx_from_key_hash(key_hash: str, shard_count: int) -> int:
    return int(key_hash[:8], 16) % int(shard_count)


def _parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Migrate single osrm_cache.db into sharded cache DBs")
    parser.add_argument(
        "--source-db",
        default=str(root / "backend" / "cache" / "osrm_cache.db"),
        help="Source single SQLite DB path",
    )
    parser.add_argument(
        "--shard-dir",
        default=str(root / "backend" / "cache" / "osrm_shards"),
        help="Target shard directory",
    )
    parser.add_argument("--shard-count", type=int, default=16, help="Number of shards")
    parser.add_argument("--batch-size", type=int, default=1000, help="Fetch batch size")
    parser.add_argument("--vacuum", action="store_true", help="Run VACUUM on each shard at end")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    source_db = Path(args.source_db).resolve()
    shard_dir = Path(args.shard_dir).resolve()
    shard_count = max(1, int(args.shard_count))
    batch_size = max(100, int(args.batch_size))

    if shard_count <= 1:
        print("[migrate] shard-count must be > 1 for sharded layout")
        return 1
    if not source_db.exists():
        print(f"[migrate] source DB missing: {source_db}")
        return 1

    print(f"[migrate] source={source_db}")
    print(f"[migrate] shard_dir={shard_dir}")
    print(f"[migrate] shard_count={shard_count}")
    print(f"[migrate] batch_size={batch_size}")

    src_conn = _connect(source_db)
    try:
        table_row = src_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='osrm_route_cache'"
        ).fetchone()
        if table_row is None:
            print("[migrate] source table osrm_route_cache not found")
            return 1

        src_stats = _count_stats(src_conn)
        print(f"[migrate] source rows={src_stats.rows} unique_keys={src_stats.unique_keys}")
        if src_stats.rows == 0:
            print("[migrate] source is empty, nothing to migrate")
            return 0

        shard_conns: Dict[int, sqlite3.Connection] = {}
        shard_paths: Dict[int, Path] = {}
        per_shard_inserts: Dict[int, int] = {}
        for i in range(shard_count):
            p = _shard_path(shard_dir, shard_count, i)
            c = _connect(p)
            _ensure_schema(c)
            shard_conns[i] = c
            shard_paths[i] = p
            per_shard_inserts[i] = 0

        try:
            cursor = src_conn.execute(
                """
                SELECT key_hash, route_kind, key_json, coords_json, point_count, created_at, updated_at
                FROM osrm_route_cache
                """
            )
            moved = 0
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                for row in rows:
                    key_hash = str(row["key_hash"])
                    idx = _shard_idx_from_key_hash(key_hash, shard_count)
                    shard_conns[idx].execute(
                        UPSERT_SQL,
                        (
                            key_hash,
                            row["route_kind"],
                            row["key_json"],
                            row["coords_json"],
                            int(row["point_count"]),
                            float(row["created_at"]),
                            float(row["updated_at"]),
                        ),
                    )
                    per_shard_inserts[idx] += 1
                    moved += 1
                for c in shard_conns.values():
                    c.commit()
                if moved % (batch_size * 10) == 0:
                    print(f"[migrate] moved {moved}/{src_stats.rows}")

            for c in shard_conns.values():
                c.commit()

            shard_total_rows = 0
            shard_total_unique = 0
            for i, c in shard_conns.items():
                st = _count_stats(c)
                shard_total_rows += st.rows
                shard_total_unique += st.unique_keys
                if args.vacuum:
                    c.execute("VACUUM")
                print(
                    f"[migrate] shard={i:0{_shard_width(shard_count)}x} "
                    f"rows={st.rows} unique={st.unique_keys} path={shard_paths[i]}"
                )

            result = {
                "source": {"rows": src_stats.rows, "unique_keys": src_stats.unique_keys, "path": str(source_db)},
                "target": {
                    "rows": shard_total_rows,
                    "unique_keys": shard_total_unique,
                    "shard_count": shard_count,
                    "shard_dir": str(shard_dir),
                },
                "per_shard_inserts": per_shard_inserts,
            }
            print("[migrate] summary")
            print(json.dumps(result, ensure_ascii=True, indent=2))

            if shard_total_rows != src_stats.rows or shard_total_unique != src_stats.unique_keys:
                print("[migrate] verification failed: source/target counts differ")
                return 2
            print("[migrate] verification ok: no row/key loss detected")
            return 0
        finally:
            for c in shard_conns.values():
                c.close()
    finally:
        src_conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
