"""
API Endpoint Smoke Tests

OpenRoutePlanner API endpoint'lerinin temel işlevselliğini test eder.
"""

import pytest
import sys
import os
import importlib
from copy import deepcopy

# Backend modüllerini path'e ekle
backend_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, backend_dir)


def _stub_nlp_engine(monkeypatch, result, *, audit_id="audit-test-1"):
    app_module = importlib.import_module("app")
    template = deepcopy(result)

    class _StubNlpEngine:
        def parse(self, query, include_trace=False):
            payload = deepcopy(template)
            payload.setdefault("detected_places", [])
            if include_trace:
                payload.setdefault("trace", {"query": query, "source": "stub"})
            return payload

    monkeypatch.setattr(app_module, "BERT_NLP_AVAILABLE", True, raising=False)
    monkeypatch.setattr(app_module, "get_bert_nlp_engine", lambda: _StubNlpEngine(), raising=False)
    monkeypatch.setattr(app_module, "log_nlp_parse_audit", lambda **_kwargs: audit_id, raising=False)
    return app_module


def _stub_geocode(monkeypatch, mapping=None):
    app_module = importlib.import_module("app")
    mapping = mapping or {}

    def _fake_geocode(address):
        if address in mapping:
            return deepcopy(mapping[address])
        return {
            "status": "success",
            "lat": 41.0284,
            "lon": 29.0244,
            "display_name": address,
        }

    monkeypatch.setattr(app_module, "geocode", _fake_geocode, raising=False)
    return app_module


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


@pytest.mark.parametrize(
    ("query", "nlp_result", "expected_fields", "expected_scope_places"),
    [
        (
            "Kadikoy'den Besiktas'a rota ciz",
            {
                "type": "route",
                "confidence": 0.93,
                "origin": "Kadikoy",
                "destination": "Besiktas",
                "detected_places": [
                    {"place": "Kadikoy", "similarity": 0.99},
                    {"place": "Besiktas", "similarity": 0.98},
                ],
            },
            {"type": "route", "origin": "Kadikoy", "destination": "Besiktas"},
            ["Kadikoy", "Besiktas"],
        ),
        (
            "Kadikoyde kafe",
            {
                "type": "poi",
                "confidence": 0.88,
                "location": "Kadikoy",
                "locations": ["Izmir"],
                "detected_places": [{"place": "Kadikoy", "similarity": 0.96}],
            },
            {"type": "poi", "location": "Kadikoy"},
            ["Kadikoy"],
        ),
        (
            "Maltepeye git",
            {
                "type": "single",
                "confidence": 0.84,
                "destination": "Maltepe",
                "detected_places": [{"place": "Maltepe", "similarity": 0.94}],
            },
            {"type": "single", "destination": "Maltepe"},
            ["Maltepe"],
        ),
        (
            "Kadikoy Moda Bostanci gez",
            {
                "type": "multi",
                "confidence": 0.82,
                "locations": ["Kadikoy", "Moda", "Bostanci"],
                "detected_places": [
                    {"place": "Kadikoy", "similarity": 0.95},
                    {"place": "Moda", "similarity": 0.93},
                    {"place": "Bostanci", "similarity": 0.92},
                ],
            },
            {"type": "multi", "locations": ["Kadikoy", "Moda", "Bostanci"]},
            ["Kadikoy", "Moda", "Bostanci"],
        ),
        (
            "Merhaba nasilsin",
            {
                "type": "unknown",
                "confidence": 0.41,
                "error": "Sorgu anlasilamadi",
                "detected_places": [],
            },
            {"type": "unknown", "error": "Sorgu anlasilamadi"},
            [],
        ),
    ],
)
def test_nlp_parse_preserves_intent_contracts(client, monkeypatch, query, nlp_result, expected_fields, expected_scope_places):
    _stub_nlp_engine(monkeypatch, nlp_result, audit_id="audit-contract-1")
    _stub_geocode(monkeypatch)

    rv = client.post("/api/nlp/parse", json={"query": query}, content_type="application/json")

    assert rv.status_code == 200
    data = rv.get_json()
    assert data["engine"] == "bert-nlp"
    assert data["audit_id"] == "audit-contract-1"
    assert "queue_wait_ms" in data
    assert "queue_timeout_sec" in data
    assert data["trace_policy"].get("request_id")
    assert data["trace_policy"].get("correlation_id")
    assert data["trace_policy"].get("pii_redaction") is True
    assert data["istanbul_scope"]["enforced"] is True
    assert [item["place"] for item in data["istanbul_scope"]["checks"]] == expected_scope_places

    for key, value in expected_fields.items():
        assert data[key] == value


def test_nlp_parse_debug_returns_trace(client, monkeypatch):
    _stub_nlp_engine(
        monkeypatch,
        {
            "type": "route",
            "confidence": 0.9,
            "origin": "Kadikoy",
            "destination": "Besiktas",
            "detected_places": [
                {"place": "Kadikoy", "similarity": 0.98},
                {"place": "Besiktas", "similarity": 0.97},
            ],
            "trace": {"decision": "route-pattern", "candidate_dedup": True},
        },
        audit_id="audit-debug-1",
    )
    _stub_geocode(monkeypatch)

    rv = client.post(
        "/api/nlp/parse",
        json={"query": "Kadikoy'den Besiktas'a rota ciz", "debug": True},
        content_type="application/json",
    )

    assert rv.status_code == 200
    data = rv.get_json()
    assert data["audit_id"] == "audit-debug-1"
    assert data["trace"] == {"decision": "route-pattern", "candidate_dedup": True}


def test_nlp_parse_rejects_outside_istanbul_locations(client, monkeypatch):
    _stub_nlp_engine(
        monkeypatch,
        {
            "type": "route",
            "confidence": 0.91,
            "origin": "Kadikoy",
            "destination": "Ankara",
            "detected_places": [
                {"place": "Kadikoy", "similarity": 0.98},
                {"place": "Ankara", "similarity": 0.97},
            ],
        },
        audit_id="audit-scope-1",
    )
    _stub_geocode(
        monkeypatch,
        {
            "Kadikoy": {
                "status": "success",
                "lat": 41.0284,
                "lon": 29.0244,
                "display_name": "Kadikoy, Istanbul",
            },
            "Ankara": {
                "status": "success",
                "lat": 39.9208,
                "lon": 32.8541,
                "display_name": "Ankara, Turkey",
            },
        },
    )

    rv = client.post(
        "/api/nlp/parse",
        json={"query": "Kadikoy'den Ankara'ya rota ciz"},
        content_type="application/json",
    )

    assert rv.status_code == 400
    data = rv.get_json()
    assert data["code"] == "outside_istanbul"
    assert data["field"] == "query"
    assert "Ankara" in data["detail"]


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


def test_routes_save_and_load_transit_payload(client):
    """Toplu ulasim rotasi payload'i round-trip korunmali."""
    payload = {
        "name": "Metro ile deneme rota",
        "description": "Kayitli transit rota",
        "points": [[41.0284, 29.0244], [41.0422, 29.0083]],
        "route_coords": [[41.0284, 29.0244], [41.0350, 29.0165], [41.0422, 29.0083]],
        "distance_km": 3.8,
        "duration_minutes": 19,
        "route_type": "transit",
        "tags": ["transit", "metro"],
        "route_payload": {
            "kind": "transit",
            "version": 1,
            "recommendation_reason": "Kayitli test payload",
            "selected_option": {
                "type": "transit",
                "transit_mode": "metro",
                "name": "M4 ile rota",
                "total_time_min": 19,
                "total_distance_m": 3800,
                "segments": [
                    {
                        "mode": "walk",
                        "description": "Istasyona yuru",
                        "duration_min": 4,
                        "coords": [[41.0284, 29.0244], [41.0300, 29.0210]],
                    },
                    {
                        "mode": "rail",
                        "route_code": "M4",
                        "description": "Metroya bin",
                        "duration_min": 15,
                        "coords": [[41.0300, 29.0210], [41.0422, 29.0083]],
                    },
                ],
            },
            "applied_modes": ["metro"],
        },
    }

    save_rv = client.post('/api/routes/save', json=payload, content_type='application/json')
    assert save_rv.status_code == 200
    save_data = save_rv.get_json()
    route_id = save_data["route"]["id"]

    try:
        get_rv = client.get(f'/api/routes/{route_id}')
        assert get_rv.status_code == 200
        route = get_rv.get_json()["route"]
        assert route["route_type"] == "transit"
        assert route["route_payload"]["kind"] == "transit"
        assert route["route_payload"]["selected_option"]["transit_mode"] == "metro"
        assert route["points"] == payload["points"]
    finally:
        client.delete(f'/api/routes/{route_id}')


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
    monkeypatch.setattr(
        app_module,
        "multimodal_osrm_cache_stats",
        lambda: {
            "base_url": "http://router.project-osrm.org",
            "memory_route": {"size": 2, "max_items": 800, "hits": 3, "misses": 4, "hit_rate": "42.9%"},
            "memory_multi": {"size": 1, "max_items": 800, "hits": 2, "misses": 3, "hit_rate": "40.0%"},
            "sqlite": {"enabled": True, "size": 5, "max_rows": 50000, "hits": 1, "misses": 2, "writes": 1, "errors": 0},
            "requests": {"route": 2, "multi": 1, "route_fallbacks": 0, "multi_fallbacks": 0},
            "coalescing": {"leaders": 1, "waits": 0, "timeouts": 0, "inflight": 0},
        },
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
    assert "multimodal_osrm_cache" in data
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
