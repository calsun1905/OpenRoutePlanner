import multimodal_engine as me


def _walking_option():
    return {
        "type": "walking",
        "icon": "walking",
        "name": "Yuruyus",
        "description": "Direkt yurume",
        "total_time_min": 300.0,
        "total_distance_m": 20000,
        "segments": [
            {"mode": "walk", "duration_min": 300.0, "distance_m": 20000, "coords": []}
        ],
    }


def test_compare_routes_keeps_explicit_mode_filter_strict(monkeypatch):
    monkeypatch.setattr(me, "_compare_cache_get", lambda _key: None)
    monkeypatch.setattr(me, "_compare_cache_put", lambda _key, _value: None)
    monkeypatch.setattr(me, "_get_nearby_routes", lambda *_args, **_kwargs: [])

    calls = {"count": 0}

    def fake_find_transit_routes(_olat, _olon, _dlat, _dlon, allowed_modes=None):
        calls["count"] += 1
        allowed = set(allowed_modes or [])
        if "bus" not in allowed:
            return [_walking_option()]
        # If the filter were relaxed, these options would leak into the response.
        return [
            _walking_option(),
            {
                "type": "transit",
                "name": "Bus only",
                "transit_mode": "bus",
                "total_time_min": 140.0,
                "segments": [{"mode": "bus", "route_code": "17"}],
            },
            {
                "type": "transit",
                "name": "Metro + bus connector",
                "transit_mode": "mixed",
                "total_time_min": 120.0,
                "segments": [
                    {"mode": "rail", "route_code": "M4"},
                    {"mode": "bus", "route_code": "132B"},
                ],
            },
        ]

    monkeypatch.setattr(me, "find_transit_routes", fake_find_transit_routes)
    monkeypatch.setattr(
        me, "_is_absurd_transit_option", lambda *_args, **_kwargs: False
    )
    monkeypatch.setattr(
        me, "_has_implausible_segment_jump", lambda *_args, **_kwargs: False
    )

    result = me.compare_routes(
        40.0, 29.0, 41.0, 29.5, allowed_modes=["metro", "metrobus"]
    )

    transit = [o for o in result["options"] if o.get("type") == "transit"]
    assert calls["count"] == 1
    assert len(transit) == 0
    assert result["telemetry"]["fallback_bus_connector_applied"] is False
    assert result["telemetry"]["fallback_guaranteed_transit_applied"] is False
    assert "seçili ulaşım modlarıyla" in result["recommendation_reason"].lower()


def test_compare_routes_reports_no_transit_when_preferred_mode_still_missing(
    monkeypatch,
):
    monkeypatch.setattr(me, "_compare_cache_get", lambda _key: None)
    monkeypatch.setattr(me, "_compare_cache_put", lambda _key, _value: None)
    monkeypatch.setattr(me, "_get_nearby_routes", lambda *_args, **_kwargs: [])

    def fake_find_transit_routes(_olat, _olon, _dlat, _dlon, allowed_modes=None):
        # Even in relaxed mode, only plain bus exists.
        allowed = set(allowed_modes or [])
        if "bus" not in allowed:
            return [_walking_option()]
        return [
            _walking_option(),
            {
                "type": "transit",
                "name": "Bus only",
                "transit_mode": "bus",
                "total_time_min": 140.0,
                "segments": [{"mode": "bus", "route_code": "17"}],
            },
        ]

    monkeypatch.setattr(me, "find_transit_routes", fake_find_transit_routes)
    monkeypatch.setattr(
        me, "_is_absurd_transit_option", lambda *_args, **_kwargs: False
    )
    monkeypatch.setattr(
        me, "_has_implausible_segment_jump", lambda *_args, **_kwargs: False
    )

    result = me.compare_routes(40.0, 29.0, 41.0, 29.5, allowed_modes=["metrobus"])
    transit = [o for o in result["options"] if o.get("type") == "transit"]

    assert len(transit) == 0
    assert result["telemetry"]["fallback_bus_connector_applied"] is False
    assert result["telemetry"]["fallback_guaranteed_transit_applied"] is False


def test_compare_routes_guarantees_transit_with_mode_relaxation(monkeypatch):
    monkeypatch.setattr(me, "_compare_cache_get", lambda _key: None)
    monkeypatch.setattr(me, "_compare_cache_put", lambda _key, _value: None)
    monkeypatch.setattr(me, "_get_nearby_routes", lambda *_args, **_kwargs: [])

    calls = {"count": 0}

    def fake_find_transit_routes(_olat, _olon, _dlat, _dlon, allowed_modes=None):
        calls["count"] += 1
        allowed = set(allowed_modes or [])
        # Ilk deneme bos, tum modlar acikken garanti fallback transit bulsun.
        if calls["count"] > 1 and allowed == {"bus", "metro", "metrobus", "ferry"}:
            return [
                _walking_option(),
                {
                    "type": "transit",
                    "name": "Guaranteed transit",
                    "transit_mode": "bus",
                    "total_time_min": 90.0,
                    "segments": [{"mode": "bus", "route_code": "17"}],
                },
            ]
        return [_walking_option()]

    monkeypatch.setattr(me, "find_transit_routes", fake_find_transit_routes)
    monkeypatch.setattr(
        me, "_is_absurd_transit_option", lambda *_args, **_kwargs: False
    )
    monkeypatch.setattr(
        me, "_has_implausible_segment_jump", lambda *_args, **_kwargs: False
    )

    result = me.compare_routes(
        40.0,
        29.0,
        41.0,
        29.5,
        allowed_modes=["bus", "metro", "metrobus", "ferry"],
    )
    transit = [o for o in result["options"] if o.get("type") == "transit"]

    assert calls["count"] >= 2
    assert len(transit) == 1
    assert transit[0]["name"] == "Guaranteed transit"
    assert result["telemetry"]["fallback_guaranteed_transit_applied"] is True
