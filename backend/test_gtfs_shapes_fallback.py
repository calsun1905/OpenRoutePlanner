from __future__ import annotations

import json
import sqlite3

import gtfs_shapes


def _write_route_file(tmp_path, payload: dict) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    route_file = cache_dir / "gtfs_route_shapes.json"
    route_file.write_text(json.dumps(payload), encoding="utf-8")


def test_gtfs_precedence_for_normal_line(monkeypatch, tmp_path):
    payload = {
        "M3": {
            "shape_id": "M3",
            "coords": [[41.0, 28.9], [41.01, 28.91], [41.02, 28.92], [41.03, 28.93], [41.04, 28.94],
                       [41.05, 28.95], [41.06, 28.96], [41.07, 28.97], [41.08, 28.98], [41.09, 28.99]],
        }
    }
    _write_route_file(tmp_path, payload)
    monkeypatch.setattr(gtfs_shapes, "CACHE_DIR", str(tmp_path / "cache"))

    coords = gtfs_shapes.get_metro_line_shape("M3")
    assert len(coords) == 10
    assert coords[0] == (41.0, 28.9)


def test_sparse_lines_keep_gtfs_even_when_short(monkeypatch, tmp_path):
    payload = {
        "F1": {"shape_id": "F1", "coords": [[41.03, 28.98], [41.02, 28.99]]},
        "M2A": {"shape_id": "M2A", "coords": [[41.01, 28.95], [41.02, 28.96]]},
        "TF1": {"shape_id": "TF1", "coords": [[41.04, 28.99], [41.03, 29.0], [41.02, 29.01]]},
        "TF2": {"shape_id": "TF2", "coords": [[41.04, 28.93], [41.03, 28.94], [41.02, 28.95]]},
    }
    _write_route_file(tmp_path, payload)
    monkeypatch.setattr(gtfs_shapes, "CACHE_DIR", str(tmp_path / "cache"))

    f1_coords = gtfs_shapes.get_metro_line_shape("F1")
    m2a_coords = gtfs_shapes.get_metro_line_shape("M2A")
    tf1_coords = gtfs_shapes.get_metro_line_shape("TF1")
    tf2_coords = gtfs_shapes.get_metro_line_shape("TF2")

    assert f1_coords == [(41.03, 28.98), (41.02, 28.99)]
    assert m2a_coords == [(41.01, 28.95), (41.02, 28.96)]
    assert tf1_coords == [(41.04, 28.99), (41.03, 29.0), (41.02, 29.01)]
    assert tf2_coords == [(41.04, 28.93), (41.03, 28.94), (41.02, 28.95)]


def test_sparse_line_keeps_gtfs_when_enough_points(monkeypatch, tmp_path):
    payload = {
        "F2": {
            "shape_id": "F2",
            "coords": [[41.03, 28.98], [41.029, 28.981], [41.028, 28.982], [41.027, 28.983], [41.026, 28.984],
                       [41.025, 28.985], [41.024, 28.986], [41.023, 28.987], [41.022, 28.988], [41.021, 28.989]],
        }
    }
    _write_route_file(tmp_path, payload)
    monkeypatch.setattr(gtfs_shapes, "CACHE_DIR", str(tmp_path / "cache"))

    coords = gtfs_shapes.get_metro_line_shape("F2")
    assert len(coords) == 10
    assert coords[0] == (41.03, 28.98)


def test_station_geometry_used_when_gtfs_missing(monkeypatch, tmp_path):
    payload = {}
    _write_route_file(tmp_path, payload)
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr(gtfs_shapes, "CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(gtfs_shapes, "build_gtfs_route_shapes_cache", lambda force=False, shapes=None: {})
    db_path = _write_transit_db(
        tmp_path,
        lines=[(14, "T5", "M-T05", 1)],
        stations=[
            (173, "EMINONU", 41.0183, 28.9702),
            (174, "KUCUKPAZAR", 41.0211, 28.9630),
            (175, "CIBALI", 41.0243, 28.9602),
        ],
        line_stations=[
            (14, 173, 1),
            (14, 174, 2),
            (14, 175, 3),
        ],
    )
    monkeypatch.setattr(gtfs_shapes, "TRANSIT_DB", db_path)

    t5_coords = gtfs_shapes.get_metro_line_shape("T5")
    assert t5_coords == [(41.0183, 28.9702), (41.0211, 28.9630), (41.0243, 28.9602)]


def test_unknown_line_returns_empty(monkeypatch, tmp_path):
    payload = {}
    _write_route_file(tmp_path, payload)
    monkeypatch.setattr(gtfs_shapes, "CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(gtfs_shapes, "build_gtfs_route_shapes_cache", lambda force=False, shapes=None: {})

    coords = gtfs_shapes.get_metro_line_shape("NO_SUCH_LINE")
    assert coords == []


def _write_transit_db(tmp_path, lines=None, stations=None, line_stations=None) -> str:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    db_path = cache_dir / "transit.db"

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE metro_lines (
            id INTEGER PRIMARY KEY,
            name TEXT,
            functional_code TEXT,
            is_active INTEGER
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE metro_stations (
            id INTEGER PRIMARY KEY,
            name TEXT,
            lat REAL,
            lon REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE metro_line_stations (
            line_id INTEGER,
            station_id INTEGER,
            station_order INTEGER
        )
        """
    )
    lines = lines or [(9000, "Marmaray", "GTFS-MARMARAY", 1)]
    stations = stations or []
    line_stations = line_stations or []
    conn.executemany(
        "INSERT INTO metro_lines (id, name, functional_code, is_active) VALUES (?, ?, ?, ?)",
        lines,
    )
    if stations:
        conn.executemany(
            "INSERT INTO metro_stations (id, name, lat, lon) VALUES (?, ?, ?, ?)",
            stations,
        )
    if line_stations:
        conn.executemany(
            "INSERT INTO metro_line_stations (line_id, station_id, station_order) VALUES (?, ?, ?)",
            line_stations,
        )
    conn.commit()
    conn.close()
    return str(db_path)


def test_match_shapes_to_metro_lines_uses_routes_and_trips(monkeypatch, tmp_path):
    db_path = _write_transit_db(tmp_path)
    monkeypatch.setattr(gtfs_shapes, "TRANSIT_DB", db_path)

    route_csv = "\n".join(
        [
            "route_id,agency_id,route_short_name,route_long_name,route_desc,route_type",
            "26615,6,Marmaray,GEBZE-HALKALI,,1",
            "26727,6,Marmaray1,SOGUTLUCESME-ZEYTINBURNU,,1",
        ]
    )
    trips_csv = "\n".join(
        [
            "route_id,service_id,trip_id,trip_headsign,trip_short_name,direction_id,block_id,shape_id,wheelchair_accessible,bikes_allowed",
            "26615,1,10,,Marmaray,0,,55574,1,1",
            "26727,1,11,,Marmaray1,0,,55764,1,1",
        ]
    )

    def _fake_download(csv_name: str, force: bool = False) -> str | None:
        if csv_name == "routes":
            return route_csv
        if csv_name == "trips":
            return trips_csv
        return None

    monkeypatch.setattr(gtfs_shapes, "download_gtfs_csv", _fake_download)

    shapes = {
        "55574": [(40.7842, 29.4095), (41.0178, 28.7664)],
        "55764": [(40.9929, 29.0227), (41.0354, 28.9942)],
    }

    matched = gtfs_shapes.match_shapes_to_metro_lines(shapes)
    assert matched == {"Marmaray": "55574"}


def test_get_metro_line_shape_builds_cache_when_missing(monkeypatch, tmp_path):
    cache_dir = tmp_path / "cache"
    db_path = _write_transit_db(tmp_path)
    monkeypatch.setattr(gtfs_shapes, "CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(gtfs_shapes, "TRANSIT_DB", db_path)

    route_csv = "\n".join(
        [
            "route_id,agency_id,route_short_name,route_long_name,route_desc,route_type",
            "26615,6,Marmaray,GEBZE-HALKALI,,1",
        ]
    )
    trips_csv = "\n".join(
        [
            "route_id,service_id,trip_id,trip_headsign,trip_short_name,direction_id,block_id,shape_id,wheelchair_accessible,bikes_allowed",
            "26615,1,10,,Marmaray,0,,55574,1,1",
        ]
    )

    def _fake_download(csv_name: str, force: bool = False) -> str | None:
        if csv_name == "routes":
            return route_csv
        if csv_name == "trips":
            return trips_csv
        return None

    monkeypatch.setattr(gtfs_shapes, "download_gtfs_csv", _fake_download)
    monkeypatch.setattr(
        gtfs_shapes,
        "download_and_parse_shapes",
        lambda force=False: {
            "55574": [(40.7842492519915, 29.4095634828195), (41.0178427940864, 28.7664382511562)],
        },
    )

    coords = gtfs_shapes.get_metro_line_shape("Marmaray")

    assert coords == [
        (40.7842492519915, 29.4095634828195),
        (41.0178427940864, 28.7664382511562),
    ]
    assert (cache_dir / "gtfs_route_shapes.json").exists()


def test_build_cache_backfills_missing_lines_with_station_geometry(monkeypatch, tmp_path):
    cache_dir = tmp_path / "cache"
    db_path = _write_transit_db(
        tmp_path,
        lines=[
            (9000, "Marmaray", "GTFS-MARMARAY", 1),
            (20, "F4", "M-F04", 1),
        ],
        stations=[
            (225, "ASIYAN", 41.0815, 29.0542),
            (226, "RUMELI HISARUSTU", 41.0848, 29.0510),
        ],
        line_stations=[
            (20, 226, 1),
            (20, 225, 2),
        ],
    )
    monkeypatch.setattr(gtfs_shapes, "CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(gtfs_shapes, "TRANSIT_DB", db_path)

    route_csv = "\n".join(
        [
            "route_id,agency_id,route_short_name,route_long_name,route_desc,route_type",
            "26615,6,Marmaray,GEBZE-HALKALI,,1",
        ]
    )
    trips_csv = "\n".join(
        [
            "route_id,service_id,trip_id,trip_headsign,trip_short_name,direction_id,block_id,shape_id,wheelchair_accessible,bikes_allowed",
            "26615,1,10,,Marmaray,0,,55574,1,1",
        ]
    )

    def _fake_download(csv_name: str, force: bool = False) -> str | None:
        if csv_name == "routes":
            return route_csv
        if csv_name == "trips":
            return trips_csv
        return None

    monkeypatch.setattr(gtfs_shapes, "download_gtfs_csv", _fake_download)

    cache = gtfs_shapes.build_gtfs_route_shapes_cache(
        shapes={
            "55574": [(40.7842, 29.4095), (41.0178, 28.7664)],
        }
    )

    assert cache["Marmaray"]["source"] == "gtfs"
    assert cache["F4"]["source"] == "stations"
    assert cache["F4"]["coords"] == [[41.0848, 29.0510], [41.0815, 29.0542]]
