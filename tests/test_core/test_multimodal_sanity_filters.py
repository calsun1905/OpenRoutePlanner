"""
Multimodal secenekler icin absurt rota eleme testleri.
"""

import os
import sqlite3
import sys

import pytest


backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

from multimodal_engine import (
    _effective_walk_to_stop_limit_m,
    _find_metro_transfer_pairs,
    _is_absurd_transit_option,
    _is_allowed_water_crossing_walk,
    _diversify_transit_options,
    _is_likely_alibey_crossing,
    _is_major_water_crossing_straight,
    compare_routes,
    get_compare_cache_stats,
)


def _build_option(total_time_min, total_distance_m, transfer_count, modes):
    return {
        "type": "transit",
        "total_time_min": total_time_min,
        "total_distance_m": total_distance_m,
        "transfer_count": transfer_count,
        "segments": [{"mode": mode} for mode in modes],
    }


def _has_metrobus_fixture_data() -> bool:
    db_path = os.path.join(backend_dir, "cache", "transit.db")
    if not os.path.exists(db_path):
        return False
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        row = cur.execute(
            """
            SELECT COUNT(*)
            FROM route_stops
            WHERE route_code = '34G'
              AND stop_code IN (900192, 900101, 900102)
            """
        ).fetchone()
        conn.close()
        return bool(row and int(row[0]) >= 3)
    except Exception:
        return False


def test_effective_walk_to_stop_limit_expands_for_long_trips():
    assert _effective_walk_to_stop_limit_m(12000) == pytest.approx(800.0)
    assert _effective_walk_to_stop_limit_m(25000) == pytest.approx(1000.0)
    assert _effective_walk_to_stop_limit_m(80000) == pytest.approx(1200.0)


def test_name_based_metro_transfer_requires_physical_proximity():
    line_a = [
        {"id": 1, "description": "Yenimahalle", "lat": 41.0837, "lon": 28.8931},
    ]
    line_b = [
        {"id": 10, "description": "Yenimahalle", "lat": 40.9817, "lon": 28.8810},  # uzak, yalanci isim eslesmesi
        {"id": 11, "description": "Baglanti Adayi", "lat": 41.0839, "lon": 28.8933},  # yakin, fiziksel eslesme
    ]

    pairs = _find_metro_transfer_pairs(line_a, line_b, max_distance_m=260.0)
    pair_ids = {(a["id"], b["id"]) for a, b in pairs}

    assert (1, 10) not in pair_ids
    assert (1, 11) in pair_ids


def test_same_side_ferry_detour_is_filtered():
    option = _build_option(
        total_time_min=73.2,
        total_distance_m=20769,
        transfer_count=3,
        modes=["walk", "rail", "ferry", "rail", "rail", "walk"],
    )

    assert _is_absurd_transit_option(
        option,
        origin_lon=28.9458,
        dest_lon=28.9208,
        direct_walk_min=91.7,
        direct_walk_m=7640,
    )


def test_same_side_ferry_with_strong_gain_is_kept():
    option = _build_option(
        total_time_min=68.0,
        total_distance_m=16000,
        transfer_count=2,
        modes=["walk", "rail", "ferry", "rail", "walk"],
    )

    assert not _is_absurd_transit_option(
        option,
        origin_lon=28.91,
        dest_lon=28.88,
        direct_walk_min=128.0,
        direct_walk_m=8600,
    )


def test_multi_transfer_detour_without_ferry_is_filtered():
    option = _build_option(
        total_time_min=84.0,
        total_distance_m=19000,
        transfer_count=3,
        modes=["walk", "rail", "rail", "walk"],
    )

    assert _is_absurd_transit_option(
        option,
        origin_lon=28.95,
        dest_lon=28.93,
        direct_walk_min=97.0,
        direct_walk_m=7600,
    )


def test_alibey_fallback_straight_crossing_is_rejected():
    start = (41.0575, 28.9458)
    end = (41.0587590005632, 28.9503349999882)
    coords = [[start[0], start[1]], [end[0], end[1]]]

    assert _is_likely_alibey_crossing(start[0], start[1], end[0], end[1])
    assert _is_major_water_crossing_straight(start[0], start[1], end[0], end[1])
    assert not _is_allowed_water_crossing_walk(
        start[0], start[1], end[0], end[1], coords, is_fallback=True
    )


def test_alibey_bridge_path_is_allowed_when_not_fallback():
    start = (41.0575, 28.9458)
    end = (41.0587590005632, 28.9503349999882)
    # Miniaturk/Sutluce kopru noktasi yakinindan gectigini varsayan yol.
    coords = [
        [start[0], start[1]],
        [41.0584, 28.9497],
        [end[0], end[1]],
    ]

    assert _is_allowed_water_crossing_walk(
        start[0], start[1], end[0], end[1], coords, is_fallback=False
    )


def test_diversify_limits_single_bus_line_domination():
    options = [
        {
            "type": "transit",
            "transit_mode": "bus",
            "route_code": "55Y",
            "total_time_min": 31.0,
            "transfer_count": 0,
            "total_walk_m": 300,
            "segments": [{"mode": "bus", "route_code": "55Y"}],
        },
        {
            "type": "transit",
            "transit_mode": "bus",
            "route_code": "50G->55Y",
            "total_time_min": 32.0,
            "transfer_count": 1,
            "total_walk_m": 350,
            "segments": [
                {"mode": "bus", "route_code": "50G"},
                {"mode": "bus", "route_code": "55Y"},
            ],
        },
        {
            "type": "transit",
            "transit_mode": "bus",
            "route_code": "55Y->36CY",
            "total_time_min": 33.0,
            "transfer_count": 1,
            "total_walk_m": 420,
            "segments": [
                {"mode": "bus", "route_code": "55Y"},
                {"mode": "bus", "route_code": "36CY"},
            ],
        },
        {
            "type": "transit",
            "transit_mode": "bus",
            "route_code": "41AT",
            "total_time_min": 35.0,
            "transfer_count": 0,
            "total_walk_m": 410,
            "segments": [{"mode": "bus", "route_code": "41AT"}],
        },
        {
            "type": "transit",
            "transit_mode": "bus",
            "route_code": "73F",
            "total_time_min": 36.0,
            "transfer_count": 0,
            "total_walk_m": 430,
            "segments": [{"mode": "bus", "route_code": "73F"}],
        },
    ]

    diversified = _diversify_transit_options(options, max_options=4)
    with_55y = 0
    for opt in diversified:
        for seg in (opt.get("segments") or []):
            if str(seg.get("mode") or "").lower() == "bus" and str(seg.get("route_code") or "").upper() == "55Y":
                with_55y += 1
                break

    assert with_55y <= 2


def test_metro_transfer_considers_all_candidate_pairs(monkeypatch):
    import multimodal_engine as me

    origin = {"id": 100, "lat": 10.0, "lon": 10.0, "description": "Origin"}
    dest = {"id": 200, "lat": 20.0, "lon": 20.0, "description": "Dest"}

    line_a = {"id": 1, "name": "M1B", "long_description": "Line A"}
    line_b = {"id": 2, "name": "M1A", "long_description": "Line B"}

    transfer_pairs = [
        ({"id": 301, "description": "T1", "lat": 1.0, "lon": 1.0}, {"id": 401, "description": "T1", "lat": 1.0, "lon": 1.0}),
        ({"id": 302, "description": "T2", "lat": 2.0, "lon": 2.0}, {"id": 402, "description": "T2", "lat": 2.0, "lon": 2.0}),
        ({"id": 303, "description": "T3", "lat": 3.0, "lon": 3.0}, {"id": 403, "description": "T3", "lat": 3.0, "lon": 3.0}),
        ({"id": 304, "description": "T4-best", "lat": 4.0, "lon": 4.0}, {"id": 404, "description": "T4-best", "lat": 4.0, "lon": 4.0}),
    ]

    # Ilk 3 aday daha kotu, 4. aday en iyi olacak sekilde sentetik mesafe kur.
    leg_distance_by_transfer = {
        301: 9000.0,
        302: 8000.0,
        303: 7000.0,
        304: 1200.0,
        401: 9000.0,
        402: 8000.0,
        403: 7000.0,
        404: 1200.0,
    }

    def fake_get_metro_stations_in_area(lat, lon, radius):
        if abs(lat - 10.0) < 1e-6 and abs(lon - 10.0) < 1e-6:
            return [origin]
        if abs(lat - 20.0) < 1e-6 and abs(lon - 20.0) < 1e-6:
            return [dest]
        return []

    def fake_get_metro_lines_for_station(station_id):
        if station_id == 100:
            return [line_a]
        if station_id == 200:
            return [line_b]
        return []

    def fake_get_metro_line_stations(line_id):
        if line_id == 1:
            return [origin] + [pair[0] for pair in transfer_pairs]
        if line_id == 2:
            return [pair[1] for pair in transfer_pairs] + [dest]
        return []

    def fake_get_line_path_between_stations(line_id, from_station_id, to_station_id):
        marker = leg_distance_by_transfer.get(to_station_id, 5000.0)
        if to_station_id == 200:
            marker = leg_distance_by_transfer.get(from_station_id, 5000.0)
        return [
            {"id": from_station_id, "lat": marker, "lon": 0.0},
            {"id": to_station_id, "lat": marker, "lon": 0.0},
        ]

    monkeypatch.setattr(me, "get_metro_stations_in_area", fake_get_metro_stations_in_area)
    monkeypatch.setattr(me, "get_metro_lines_for_station", fake_get_metro_lines_for_station)
    monkeypatch.setattr(me, "get_metro_line_stations", fake_get_metro_line_stations)
    monkeypatch.setattr(me, "_find_metro_transfer_pairs", lambda a, b: transfer_pairs)
    monkeypatch.setattr(me, "_get_line_path_between_stations", fake_get_line_path_between_stations)
    monkeypatch.setattr(
        me,
        "_build_walk_leg",
        lambda *args, **kwargs: {"coords": [[0.0, 0.0], [0.0, 0.0]], "distance_m": 0.0, "duration_min": 0.0},
    )
    monkeypatch.setattr(me, "_path_distance_m", lambda coords: float(coords[0][0]) if coords else 0.0)
    monkeypatch.setattr(me, "_metro_travel_time_minutes", lambda km: float(km) * 1.0)

    options = me._build_metro_options(
        origin_lat=10.0,
        origin_lon=10.0,
        dest_lat=20.0,
        dest_lon=20.0,
        direct_walk_min=999.0,
        direct_walk_m=999999.0,
        max_results=3,
    )

    assert options, "En az bir metro secenegi bekleniyor"
    transfer_opts = [o for o in options if str(o.get("route_code")) == "M1B->M1A"]
    assert transfer_opts, "M1B->M1A aktarimli secenek bekleniyor"
    best = transfer_opts[0]
    assert "T4-best" in str(best.get("description") or "")


def test_compare_routes_emits_telemetry(monkeypatch):
    import multimodal_engine as me

    walking = {
        "type": "walking",
        "icon": "walking",
        "name": "Yuruyus",
        "total_time_min": 15.0,
        "total_distance_m": 1200.0,
        "segments": [],
    }
    transit = {
        "type": "transit",
        "icon": "bus",
        "name": "Bus",
        "total_time_min": 12.0,
        "total_distance_m": 2200.0,
        "segments": [{"mode": "bus", "route_code": "10A"}],
    }

    monkeypatch.setattr(me, "find_transit_routes", lambda *args, **kwargs: [walking, transit])
    monkeypatch.setattr(me, "_get_nearby_routes", lambda *_args, **_kwargs: [])

    result = compare_routes(41.0, 29.0, 41.01, 29.01, allowed_modes=["bus", "metro"])
    telemetry = result.get("telemetry") or {}
    stage_ms = telemetry.get("stage_ms") or {}

    assert telemetry.get("compare_cache_hit") is False
    assert "find_transit_routes_ms" in stage_ms
    assert "total_ms" in stage_ms
    assert telemetry.get("option_counts", {}).get("transit_options") == 1

    cache_stats = get_compare_cache_stats()
    assert "enabled" in cache_stats
    assert "size" in cache_stats


@pytest.mark.skipif(not _has_metrobus_fixture_data(), reason="Transit fixture data unavailable")
def test_route_stop_coords_resolve_directional_aliases_for_metrobus():
    import multimodal_engine as me

    coords = me._get_route_stop_coords("34G", 900192, 900101)
    assert len(coords) >= 8
    assert coords[0][0] == pytest.approx(41.0157, abs=0.003)
    assert coords[-1][0] == pytest.approx(41.0674, abs=0.003)
    assert any(abs(lat - 41.0337) < 0.015 for lat, _ in coords)


@pytest.mark.skipif(not _has_metrobus_fixture_data(), reason="Transit fixture data unavailable")
def test_route_stop_coords_reject_opposite_direction_same_station_codes():
    import multimodal_engine as me

    coords = me._get_route_stop_coords("34", 900101, 900102)
    assert coords == []
