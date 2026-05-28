"""
API Endpoint Smoke Tests

OpenRoutePlanner API endpoint'lerinin temel işlevselliğini test eder.
"""

import pytest
import sys
import os
import importlib

# Backend modüllerini path'e ekle
backend_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, backend_dir)


@pytest.fixture
def client(monkeypatch):
    """Flask test client fixture (external dependency stubs enabled)."""
    monkeypatch.setenv("ORP_BERT_FORCE_GPU", "0")
    monkeypatch.setenv("ORP_BERT_STRICT_GPU", "0")
    monkeypatch.setenv("ORP_BERT_PARSE_TRACE", "0")
    monkeypatch.setenv("ORP_BERT_USE_OSM", "0")
    monkeypatch.setenv("ORP_BERT_SEED_DYNAMIC", "0")

    app_module = importlib.import_module("app")

    class _StubNlpEngine:
        def parse(self, query, include_trace=False):
            result = {
                "type": "route",
                "confidence": 0.91,
                "origin": "Istanbul",
                "destination": "Ankara",
                "locations": [],
                "detected_places": [
                    {"place": "Istanbul", "similarity": 0.9},
                    {"place": "Ankara", "similarity": 0.89},
                ],
            }
            if include_trace:
                result["trace"] = {"query": query}
            return result

    monkeypatch.setattr(app_module, "BERT_NLP_AVAILABLE", True, raising=False)
    monkeypatch.setattr(app_module, "get_bert_nlp_engine", lambda: _StubNlpEngine(), raising=False)
    monkeypatch.setattr(
        app_module,
        "geocode",
        lambda address: {
            "status": "success",
            "lat": 41.0284,
            "lon": 29.0244,
            "display_name": address,
        },
        raising=False,
    )
    monkeypatch.setattr(
        app_module,
        "reverse_geocode",
        lambda lat, lon: {"status": "success", "address": "Kadikoy, Istanbul"},
        raising=False,
    )
    if hasattr(app_module, "_route_response_cache_manager"):
        app_module._route_response_cache_manager.clear()

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as test_client:
        yield test_client


def test_health_endpoint(client):
    """Health check endpoint testi"""
    rv = client.get('/api/health')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['status'] == 'ok'
    assert rv.headers.get('X-Request-ID')
    assert rv.headers.get('X-Correlation-ID')


def test_trace_headers_preserve_incoming_request_id(client):
    """Gelen X-Request-ID/X-Correlation-ID response'ta korunmalı"""
    rv = client.get(
        '/api/health',
        headers={
            'X-Request-ID': 'test-req-123',
            'X-Correlation-ID': 'test-corr-999',
        },
    )
    assert rv.status_code == 200
    assert rv.headers.get('X-Request-ID') == 'test-req-123'
    assert rv.headers.get('X-Correlation-ID') == 'test-corr-999'


def test_nlp_status(client):
    """NLP engine status endpoint testi"""
    rv = client.get('/api/nlp/status')
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'available' in data
    assert 'engine' in data
    assert data.get('available') == data.get('bert_available')
    assert 'queue' in data
    assert 'bert_runtime' in data


def test_nlp_parse_with_query(client):
    """NLP parse endpoint testi - basit sorgu"""
    rv = client.post('/api/nlp/parse',
                    json={'query': 'İstanbul\'dan Ankara\'ya rota çiz'},
                    content_type='application/json')
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'type' in data
    assert 'confidence' in data
    assert 'trace_policy' in data
    assert data['trace_policy'].get('request_id')
    assert data['trace_policy'].get('correlation_id')
    assert data['trace_policy'].get('retention_days')


def test_nlp_parse_empty_query(client):
    """NLP parse endpoint testi - boş sorgu"""
    rv = client.post('/api/nlp/parse',
                    json={'query': ''},
                    content_type='application/json')
    assert rv.status_code == 400


def test_nlp_parse_non_string_query(client):
    """NLP parse endpoint testi - query string olmalı"""
    rv = client.post('/api/nlp/parse',
                    json={'query': 123},
                    content_type='application/json')
    assert rv.status_code == 400
    data = rv.get_json()
    assert 'error' in data


def test_geocode_forward(client):
    """Forward geocoding testi"""
    rv = client.get('/api/geocode/forward',
                   query={'address': 'Kadıköy, İstanbul'})
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'lat' in data
    assert 'lon' in data


def test_geocode_reverse(client):
    """Reverse geocoding testi"""
    rv = client.get('/api/geocode/reverse',
                   query={'lat': '41.0284', 'lon': '29.0244'})
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'address' in data


def test_get_route_rejects_outside_istanbul(client):
    rv = client.post(
        '/api/get-route',
        json={'points': [[41.0284, 29.0244], [39.9208, 32.8541]]},
        content_type='application/json',
    )
    assert rv.status_code == 400
    data = rv.get_json()
    assert data.get('code') == 'outside_istanbul'
    assert data.get('field') == 'points'


def test_locations_list(client):
    """Kayıtlı konumlar listesi endpoint testi"""
    rv = client.get('/api/locations')
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'locations' in data


def test_routes_list(client):
    """Kayıtlı rotalar listesi endpoint testi"""
    rv = client.get('/api/routes')
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'routes' in data


def test_routes_statistics(client):
    """Rota istatistikleri endpoint testi"""
    rv = client.get('/api/routes/statistics')
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'total_routes' in data
    assert 'total_distance_km' in data


def test_get_route_returns_unreachable_waypoints_contract(client, monkeypatch):
    """Optimize TSP cagrisi baglanti yoksa acik hata sozlesmesi donmeli."""
    app_module = importlib.import_module("app")
    from route_engine import UnreachableWaypointsError

    monkeypatch.setattr(
        app_module,
        "solve_tsp",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(UnreachableWaypointsError([(0, 2), (1, 2)])),
        raising=False,
    )

    rv = client.post(
        "/api/get-route",
        json={
            "optimize": True,
            "points": [[41.0284, 29.0244], [41.05, 29.02], [41.08, 29.01]],
        },
        content_type="application/json",
    )
    assert rv.status_code == 400
    data = rv.get_json()
    assert data.get("error_code") == "UNREACHABLE_WAYPOINTS"
    assert data.get("details", {}).get("unreachable_pairs") == [[0, 2], [1, 2]]


def test_route_response_cache_key_rounds_points_deterministically():
    app_module = importlib.import_module("app")

    points_a = [[41.0284004, 29.0244004], [41.0384004, 29.0344004]]
    points_b = [[41.02840049, 29.02440049], [41.03840049, 29.03440049]]

    key_a = app_module._route_response_cache_key("/api/get-route", points_a, False, "route_1")
    key_b = app_module._route_response_cache_key("/api/get-route", points_b, False, "route_1")
    key_c = app_module._route_response_cache_key("/api/get-route", points_b, True, "route_1")
    key_d = app_module._route_response_cache_key("/api/get-route", points_b, False, "route_2")

    assert key_a == key_b
    assert key_a != key_c
    assert key_a != key_d


def test_cache_stats_endpoint(client, monkeypatch):
    app_module = importlib.import_module("app")

    monkeypatch.setattr(app_module, "_multimodal_available", True, raising=False)
    monkeypatch.setattr(
        app_module,
        "get_all_cache_stats",
        lambda: {
            "graph": {"memory_cache": {"size": 9, "maxsize": 10, "hits": 2, "misses": 28}},
            "poi": {"size": 45, "maxsize": 50, "hits": 4, "misses": 24},
            "route_response_cache": {
                "enabled": True,
                "size": 120,
                "max_items": 500,
                "hits": 40,
                "misses": 80,
                "hit_rate": "33.3%",
                "ttl_sec": 180,
            },
            "point_graph_memory_cache": {
                "size": 22,
                "maxsize": 24,
                "hits": 10,
                "misses": 15,
                "hit_rate": "40.0%",
                "ttl_sec": 900,
            },
        },
        raising=False,
    )
    monkeypatch.setattr(
        app_module,
        "multimodal_compare_cache_stats",
        lambda: {"enabled": False, "size": 0, "max_items": 220, "hits": 0, "misses": 0, "hit_rate": "0.0%"},
        raising=False,
    )
    monkeypatch.setattr(
        app_module,
        "multimodal_transit_lookup_cache_stats",
        lambda: {"enabled": True, "size": 12, "max_items": 2500, "hits": 4, "misses": 8, "hit_rate": "33.3%"},
        raising=False,
    )
    monkeypatch.setattr(
        app_module,
        "multimodal_segment_cache_stats",
        lambda: {"enabled": True, "size": 6, "max_items": 1800, "hits": 2, "misses": 4, "hit_rate": "33.3%"},
        raising=False,
    )

    rv = client.get("/api/cache/stats")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "graph" in data
    assert "poi" in data
    assert "multimodal_compare" in data
    assert "multimodal_transit_lookup" in data
    assert "multimodal_segment_cache" in data
    assert "route_response_cache" in data
    assert "point_graph_memory_cache" in data
    assert "queue" in data
    assert "policy" in data
    assert data["policy"].get("status") == "warn"
    assert isinstance(data["policy"].get("warnings"), list)
    assert "generated_at_utc" in data


def test_multimodal_compare_returns_busy_when_concurrency_exhausted(client, monkeypatch):
    app_module = importlib.import_module("app")

    class _BusySemaphore:
        def acquire(self, blocking=True, timeout=None):
            return False

        def release(self):
            return None

    monkeypatch.setattr(app_module, "_multimodal_available", True, raising=False)
    monkeypatch.setattr(app_module, "_MULTIMODAL_COMPARE_SEMAPHORE", _BusySemaphore(), raising=False)
    monkeypatch.setattr(app_module, "_MULTIMODAL_COMPARE_MAX_CONCURRENCY", 1, raising=False)

    rv = client.post(
        "/api/multimodal/compare",
        json={
            "origin": [41.0284, 29.0244],
            "destination": [41.0384, 29.0344],
            "allowed_modes": ["bus", "metro"],
        },
        content_type="application/json",
    )
    assert rv.status_code == 429
    data = rv.get_json()
    assert data.get("error_code") == "MULTIMODAL_QUEUE_TIMEOUT"
    assert data.get("max_concurrency") == 1
    assert isinstance(data.get("retry_after_sec"), int)
    assert "queue_wait_ms" in data


def test_nlp_parse_returns_queue_timeout_when_concurrency_exhausted(client, monkeypatch):
    app_module = importlib.import_module("app")

    class _BusySemaphore:
        def acquire(self, blocking=True, timeout=None):
            return False

        def release(self):
            return None

    monkeypatch.setattr(app_module, "BERT_NLP_AVAILABLE", True, raising=False)
    monkeypatch.setattr(app_module, "_NLP_PARSE_SEMAPHORE", _BusySemaphore(), raising=False)
    monkeypatch.setattr(app_module, "_NLP_PARSE_MAX_CONCURRENCY", 1, raising=False)
    monkeypatch.setattr(app_module, "_NLP_QUEUE_TIMEOUT_SEC", 0.25, raising=False)

    rv = client.post(
        "/api/nlp/parse",
        json={"query": "Kadikoy'den Besiktas'a rota ciz"},
        content_type="application/json",
    )
    assert rv.status_code == 429
    data = rv.get_json()
    assert data.get("error_code") == "NLP_QUEUE_TIMEOUT"
    assert data.get("max_concurrency") == 1
    assert isinstance(data.get("retry_after_sec"), int)
    assert "queue_wait_ms" in data


def test_multimodal_compare_caps_allowed_modes(client, monkeypatch):
    app_module = importlib.import_module("app")
    captured = {}

    def _fake_compare(_olat, _olon, _dlat, _dlon, allowed_modes=None):
        captured["allowed_modes"] = allowed_modes
        return {
            "options": [
                {
                    "type": "walking",
                    "icon": "walking",
                    "name": "Yuruyus",
                    "total_time_min": 10.0,
                    "total_distance_m": 700.0,
                    "segments": [],
                }
            ],
            "walking": {"type": "walking", "total_time_min": 10.0},
            "transit_options": [],
            "recommended": "walking",
            "recommendation_reason": "Yuruyus en hizli secenek",
            "applied_modes": allowed_modes or [],
        }

    monkeypatch.setattr(app_module, "_multimodal_available", True, raising=False)
    monkeypatch.setattr(app_module, "multimodal_compare", _fake_compare, raising=False)
    monkeypatch.setitem(app_module.ROUTE_CONFIG, "MULTIMODAL_ALLOWED_MODES_MAX", 3)

    rv = client.post(
        "/api/multimodal/compare",
        json={
            "origin": [41.0284, 29.0244],
            "destination": [41.0384, 29.0344],
            "allowed_modes": ["BUS", "metro", "ferry", "metro", "tram", "bus"],
        },
        content_type="application/json",
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert captured["allowed_modes"] == ["bus", "metro", "ferry"]
    assert data.get("telemetry", {}).get("api_compare_allowed_modes") == ["bus", "metro", "ferry"]


def test_get_route_response_cache_hits_second_call(client, monkeypatch):
    app_module = importlib.import_module("app")
    import networkx as nx

    if hasattr(app_module, "_route_response_cache_manager"):
        app_module._route_response_cache_manager.clear()

    call_counter = {"count": 0}
    graph = nx.MultiDiGraph()
    graph.add_node(1, y=41.0284, x=29.0244)
    graph.add_node(2, y=41.0384, x=29.0344)

    def _fake_build_route(point_tuples, optimize, route_type):
        call_counter["count"] += 1
        return {
            "graph": graph,
            "optimized_order": [0, 1],
            "ordered_points": point_tuples,
            "route_nodes": [1, 2],
        }

    monkeypatch.setattr(app_module, "_build_primary_route_with_retries", _fake_build_route, raising=False)
    monkeypatch.setattr(app_module, "nodes_to_coords", lambda *_args, **_kwargs: [[41.0284, 29.0244], [41.0384, 29.0344]], raising=False)
    monkeypatch.setattr(
        app_module,
        "calculate_route_stats",
        lambda *_args, **_kwargs: {"total_distance_km": 1.2, "estimated_walk_minutes": 14},
        raising=False,
    )
    monkeypatch.setattr(app_module, "generate_google_maps_link", lambda *_args, **_kwargs: "https://maps.example", raising=False)

    payload = {
        "points": [[41.0284, 29.0244], [41.0384, 29.0344]],
        "optimize": False,
        "route_type": "route_1",
    }
    first = client.post("/api/get-route", json=payload, content_type="application/json")
    second = client.post("/api/get-route", json=payload, content_type="application/json")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.get_json().get("cache_hit") is False
    assert second.get_json().get("cache_hit") is True
    assert call_counter["count"] == 1


def test_get_alternative_routes_response_cache_hits_second_call(client, monkeypatch):
    app_module = importlib.import_module("app")
    import networkx as nx

    if hasattr(app_module, "_route_response_cache_manager"):
        app_module._route_response_cache_manager.clear()

    call_counter = {"count": 0}
    graph = nx.MultiDiGraph()
    graph.add_node(1, y=41.0284, x=29.0244)
    graph.add_node(2, y=41.0384, x=29.0344)

    def _fake_alt_batch(point_tuples, optimize):
        call_counter["count"] += 1
        return {
            "graph": graph,
            "optimized_order": [0, 1],
            "ordered_points": point_tuples,
            "batch_results": [
                {
                    "type": "route_1",
                    "name": "Rota 1",
                    "icon": "@",
                    "nodes": [1, 2],
                    "distance_km": 1.2,
                    "duration_minutes": 14,
                    "description": "1.2 km",
                }
            ],
        }

    monkeypatch.setattr(app_module, "_build_alternative_batch_with_retries", _fake_alt_batch, raising=False)
    monkeypatch.setattr(app_module, "nodes_to_coords", lambda *_args, **_kwargs: [[41.0284, 29.0244], [41.0384, 29.0344]], raising=False)
    monkeypatch.setattr(app_module, "generate_google_maps_link", lambda *_args, **_kwargs: "https://maps.example", raising=False)

    payload = {
        "points": [[41.0284, 29.0244], [41.0384, 29.0344]],
        "optimize": False,
    }
    first = client.post("/api/get-alternative-routes", json=payload, content_type="application/json")
    second = client.post("/api/get-alternative-routes", json=payload, content_type="application/json")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.get_json().get("cache_hit") is False
    assert second.get_json().get("cache_hit") is True
    assert call_counter["count"] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
