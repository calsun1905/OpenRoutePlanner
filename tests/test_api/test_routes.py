"""
API Endpoint Smoke Tests

OpenRoutePlanner API endpoint'lerinin temel işlevselliğini test eder.
"""

import pytest
import sys
import os

# Backend modüllerini path'e ekle
backend_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, backend_dir)


@pytest.fixture
def client():
    """Flask test client fixture"""
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    """Health check endpoint testi"""
    rv = client.get('/api/health')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['status'] == 'ok'


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
