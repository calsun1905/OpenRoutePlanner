from __future__ import annotations

import json

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


def test_sparse_lines_fallback_to_manual(monkeypatch, tmp_path):
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

    assert len(f1_coords) >= gtfs_shapes.MIN_GTFS_POINTS_FOR_DIRECT_USE
    assert len(m2a_coords) >= gtfs_shapes.MIN_GTFS_POINTS_FOR_DIRECT_USE
    assert len(tf1_coords) >= gtfs_shapes.MIN_GTFS_POINTS_FOR_DIRECT_USE
    assert len(tf2_coords) >= gtfs_shapes.MIN_GTFS_POINTS_FOR_DIRECT_USE


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


def test_manual_only_line_when_gtfs_missing(monkeypatch, tmp_path):
    payload = {}
    _write_route_file(tmp_path, payload)
    monkeypatch.setattr(gtfs_shapes, "CACHE_DIR", str(tmp_path / "cache"))

    t5_coords = gtfs_shapes.get_metro_line_shape("T5")
    # GTFS verisi yokken T5 manuel shape birebir donmeli.
    assert t5_coords == gtfs_shapes.METRO_LINE_SHAPES["T5"]


def test_unknown_line_returns_empty(monkeypatch, tmp_path):
    payload = {}
    _write_route_file(tmp_path, payload)
    monkeypatch.setattr(gtfs_shapes, "CACHE_DIR", str(tmp_path / "cache"))

    coords = gtfs_shapes.get_metro_line_shape("NO_SUCH_LINE")
    assert coords == []
