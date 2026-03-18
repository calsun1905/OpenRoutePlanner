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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
