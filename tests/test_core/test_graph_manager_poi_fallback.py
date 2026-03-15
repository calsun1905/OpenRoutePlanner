"""
Graph manager POI fallback/geo-bound testleri.
"""

import os
import sys

backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

import graph_manager


class DummyGDF:
    def __init__(self, count: int):
        self._count = count

    def __len__(self):
        return self._count


def test_fetch_pois_requires_geobound_center(monkeypatch):
    monkeypatch.setattr(graph_manager, "geocode", lambda place: {"status": "error"})

    # osmnx çağrıları hiç yapılmamalı
    called = {"point": 0, "place": 0}
    monkeypatch.setattr(graph_manager.ox, "features_from_point", lambda *a, **k: called.__setitem__("point", called["point"] + 1))
    monkeypatch.setattr(graph_manager.ox, "features_from_place", lambda *a, **k: called.__setitem__("place", called["place"] + 1))

    gdf = graph_manager._fetch_pois_with_fallback("Malatya, Turkey", {"amenity": "restaurant"})
    assert gdf is None
    assert called["point"] == 0
    assert called["place"] == 0


def test_fetch_pois_fallback_order_a_then_b(monkeypatch):
    monkeypatch.setattr(graph_manager, "geocode", lambda place: {"status": "success", "lat": 38.35, "lon": 38.31})

    calls = []

    def fake_point(center, tags, dist):
        calls.append(("point", dist))
        # İlk deneme boş, ikinci deneme dolu
        return DummyGDF(0 if len(calls) == 1 else 2)

    monkeypatch.setattr(graph_manager.ox, "features_from_point", fake_point)
    monkeypatch.setattr(graph_manager.ox, "features_from_place", lambda *a, **k: DummyGDF(0))

    gdf = graph_manager._fetch_pois_with_fallback("Malatya, Turkey", {"amenity": "restaurant"})
    assert gdf is not None
    assert len(gdf) == 2
    assert calls[0][0] == "point"
    assert calls[1][0] == "point"


def test_search_pois_by_tags_returns_empty_when_all_fallbacks_fail(monkeypatch):
    monkeypatch.setattr(graph_manager, "geocode", lambda place: {"status": "success", "lat": 38.35, "lon": 38.31})
    monkeypatch.setattr(graph_manager.ox, "features_from_point", lambda *a, **k: DummyGDF(0))
    monkeypatch.setattr(graph_manager.ox, "features_from_place", lambda *a, **k: DummyGDF(0))

    result = graph_manager.search_pois_by_tags("Malatya, Turkey", {"amenity": "restaurant"}, category_hint="pilavcı")
    assert result == []
