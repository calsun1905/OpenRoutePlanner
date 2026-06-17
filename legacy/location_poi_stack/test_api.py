"""
test_api.py - Flask API test suite for Location + POI endpoints.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

STACK_ROOT = Path(__file__).resolve().parent
if str(STACK_ROOT) not in sys.path:
    sys.path.insert(0, str(STACK_ROOT))

from flask_api import app


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def _json(response) -> dict[str, Any]:
    data = response.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def test_health(client):
    resp = client.get("/api/health")
    data = _json(resp)

    assert resp.status_code == 200
    assert data.get("status") == "ok"
    assert data.get("version") == "1.0"
    assert isinstance(data.get("message"), str)


def test_stats(client):
    resp = client.get("/api/stats")
    data = _json(resp)
    stats = data.get("stats")

    assert resp.status_code == 200
    assert data.get("success") is True
    assert isinstance(stats, dict)
    assert stats.get("districts") == 37
    assert stats.get("poi_types") == 15
    assert stats.get("total_pois") == 123


def test_locations(client):
    resp = client.get("/api/locations")
    data = _json(resp)
    districts = data.get("districts")

    assert resp.status_code == 200
    assert data.get("success") is True
    assert data.get("count") == 37
    assert isinstance(districts, list)
    assert len(districts) == 37


def test_poi_types(client):
    resp = client.get("/api/poi/types")
    data = _json(resp)
    poi_types = data.get("types")

    assert resp.status_code == 200
    assert data.get("success") is True
    assert data.get("count") == 15
    assert isinstance(poi_types, list)
    assert len(poi_types) == 15


def test_parse_query_success(client):
    resp = client.post("/api/nlp/parse", json={"query": "Kadikoyde kafe"})
    data = _json(resp)

    assert resp.status_code == 200
    assert data.get("success") is True
    assert data.get("poi_type") == "kafe"
    assert isinstance(data.get("pois"), list)
    assert isinstance(data.get("result_count"), int)


def test_parse_query_missing_query(client):
    resp = client.post("/api/nlp/parse", json={})
    data = _json(resp)

    assert resp.status_code == 400
    assert data.get("success") is False
    assert data.get("error_code") == "invalid_input"


def test_parse_query_empty_query(client):
    resp = client.post("/api/nlp/parse", json={"query": "   "})
    data = _json(resp)

    assert resp.status_code == 400
    assert data.get("success") is False
    assert data.get("error_code") == "invalid_input"


def test_parse_query_invalid_json_body(client):
    resp = client.post("/api/nlp/parse", data="not-json", content_type="text/plain")
    data = _json(resp)

    assert resp.status_code == 400
    assert data.get("success") is False
    assert data.get("error_code") == "invalid_input"


def test_parse_query_no_body(client):
    resp = client.post("/api/nlp/parse", content_type="application/json")
    data = _json(resp)

    assert resp.status_code == 400
    assert data.get("success") is False
    assert data.get("error_code") == "invalid_input"


def test_poi_search_success(client):
    resp = client.post("/api/poi/search", json={"location": "besiktas", "poi_type": "kafe"})
    data = _json(resp)

    assert resp.status_code == 200
    assert data.get("success") is True
    assert isinstance(data.get("pois"), list)
    assert isinstance(data.get("result_count"), int)


def test_poi_search_missing_filters(client):
    resp = client.post("/api/poi/search", json={})
    data = _json(resp)

    assert resp.status_code == 400
    assert data.get("success") is False
    assert data.get("error_code") == "invalid_input"


def test_poi_search_invalid_json(client):
    resp = client.post("/api/poi/search", data="bad", content_type="application/octet-stream")
    data = _json(resp)

    assert resp.status_code == 400
    assert data.get("success") is False
    assert data.get("error_code") == "invalid_input"


def test_poi_search_limit_type_validation(client):
    resp = client.post("/api/poi/search", json={"location": "kadikoy", "poi_type": "kafe", "limit": "abc"})
    data = _json(resp)

    assert resp.status_code == 400
    assert data.get("success") is False
    assert data.get("error_code") == "invalid_input"


def test_poi_search_limit_range_validation(client):
    resp = client.post("/api/poi/search", json={"location": "kadikoy", "poi_type": "kafe", "limit": 0})
    data = _json(resp)

    assert resp.status_code == 400
    assert data.get("success") is False
    assert data.get("error_code") == "invalid_input"


def test_unknown_endpoint(client):
    resp = client.get("/api/unknown")
    assert resp.status_code == 404
