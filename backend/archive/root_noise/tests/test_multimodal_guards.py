import multimodal_engine


def test_bosphorus_walk_guard_disabled_by_default(monkeypatch):
    monkeypatch.setitem(multimodal_engine.ROUTE_CONFIG, "MULTIMODAL_ENFORCE_WATER_CROSSING_GUARDS", False)
    # Besiktas -> Uskudar civari (karsi yaka)
    blocked = multimodal_engine._is_forbidden_bosphorus_walk(41.0430, 29.0042, 41.0257, 29.0169)
    assert blocked is False


def test_bosphorus_walk_guard_can_be_enabled(monkeypatch):
    monkeypatch.setitem(multimodal_engine.ROUTE_CONFIG, "MULTIMODAL_ENFORCE_WATER_CROSSING_GUARDS", True)
    blocked = multimodal_engine._is_forbidden_bosphorus_walk(41.0430, 29.0042, 41.0257, 29.0169)
    assert blocked is True
