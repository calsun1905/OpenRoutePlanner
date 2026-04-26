"""
POI API kategori canonicalization testleri.
"""

import os
import sys

import pytest

backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)


@pytest.fixture
def client():
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_search_pois_resolves_category_with_morph_dict(client, monkeypatch):
    captured = {}

    def fake_search_pois(place, category, **kwargs):
        search_mode = kwargs.get("search_mode", "auto")
        captured["place"] = place
        captured["category"] = category
        captured["search_mode"] = search_mode
        return [{"name": "Ornek Pilavci", "lat": 0.0, "lon": 0.0, "category": category}]

    monkeypatch.setattr("app.search_pois", fake_search_pois)
    monkeypatch.setattr("app._is_place_text_in_istanbul", lambda _place: (True, {"status": "mock"}))

    rv = client.post(
        "/api/search-pois",
        json={"place": "Kadikoy, Istanbul, Turkey", "category": "pilavcilardan"},
        content_type="application/json",
    )

    assert rv.status_code == 200
    data = rv.get_json()
    assert data["category"] == "pilavcı"
    assert data["category_resolution"]["status"] == "success"
    assert data.get("version_profile", {}).get("dict_version")
    assert data.get("version_profile", {}).get("threshold_profile")
    assert data.get("version_profile", {}).get("plan_version")
    assert data.get("version_profile", {}).get("cache_token")
    assert captured["category"] == "pilavcı"
    assert data["search_mode"] == "place_boundary_only"
    assert captured["search_mode"] == "place_boundary_only"


def test_search_pois_keeps_unknown_category(client, monkeypatch):
    captured = {}

    def fake_search_pois(place, category, **kwargs):
        search_mode = kwargs.get("search_mode", "auto")
        captured["category"] = category
        captured["search_mode"] = search_mode
        return []

    monkeypatch.setattr("app.search_pois", fake_search_pois)
    monkeypatch.setattr("app._is_place_text_in_istanbul", lambda _place: (True, {"status": "mock"}))

    rv = client.post(
        "/api/search-pois",
        json={"place": "Kadikoy, Istanbul, Turkey", "category": "xzy-bilinmeyen"},
        content_type="application/json",
    )

    assert rv.status_code == 200
    data = rv.get_json()
    assert data["category"] == "xzy-bilinmeyen"
    assert data["category_resolution"]["status"] in {"unknown", "success"}
    assert captured["category"] == "xzy-bilinmeyen"
    assert data["search_mode"] == "place_boundary_only"
    assert captured["search_mode"] == "place_boundary_only"


def test_search_pois_rejects_outside_istanbul(client, monkeypatch):
    monkeypatch.setattr(
        "app._is_place_text_in_istanbul",
        lambda _place: (
            False,
            {"status": "resolved", "display_name": "Ankara, Turkiye", "lat": 39.93, "lon": 32.85},
        ),
    )

    rv = client.post(
        "/api/search-pois",
        json={"place": "Ankara, Turkey", "category": "cafe"},
        content_type="application/json",
    )

    assert rv.status_code == 400
    data = rv.get_json()
    assert data["code"] == "outside_istanbul"
    assert data["field"] == "place"
