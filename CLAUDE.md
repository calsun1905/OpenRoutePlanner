# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenRoutePlanner is a Turkish-optimized, AI-powered route planning application built with Flask/Python backend and vanilla JavaScript frontend. It uses OpenStreetMap data via OSMnx/NetworkX for routing, and BERT (Transformers/PyTorch) for Turkish natural language query processing.

**Key Architecture Points:**
- Backend: Flask API in `OpenRoutePlanner/backend/app.py` (~1300 lines)
- Route Engine: Dijkstra, TSP, via-node alternative routes in `route_engine.py`
- NLP: Dual engine - BERT (`bert_nlp_engine.py`) + regex fallback (`nlp_engine.py`)
- Graph Management: OSMnx graph caching with LRU + TTL in `graph_manager.py`
- Storage: SQLite for routes/locations with `route_storage.py` and `location_storage.py`

## Common Commands

```bash
# Development setup
cd OpenRoutePlanner
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Run backend server
cd backend
python app.py  # Runs on http://localhost:5000

# Run tests
pytest                           # All tests with coverage
pytest tests/test_api/           # API tests only
pytest tests/test_core/          # Core module tests only
pytest --cov=backend --cov-report=html  # HTML coverage report

# BERT testing
cd backend
python bert_engine.py            # Test BERT embedding engine
python bert_nlp_engine.py        # Test full NLP parser
python -c "from bert_nlp_engine import test_bert_nlp; test_bert_nlp()"

# Gold dataset evaluation
python scripts/tools/evaluate_bert_gold.py --limit 10
```

## Route Engine Architecture (v3.0)

The route engine (`route_engine.py`) implements a sophisticated multi-route algorithm:

1. **Main Route:** Dijkstra's algorithm for shortest path
2. **Alternative Routes:** Via-node method - finds intermediate junctions away from main route, creates paths through them
3. **Overlap Control:** Asymmetric overlap calculation - "what % of new route is same as old?" (not Jaccard)
4. **Body-only Penalty:** Only penalizes middle 80% of route, preserves first/last 10%

Key functions:
- `solve_tsp(G, points)` - Traveling Salesman for multiple destinations
- `build_alternative_routes(G, route, num_routes=3)` - Via-node alternatives
- `calculate_route_stats(G, route)` - Distance, duration, Google Maps link

Configuration is centralized in `route_config.py` (31 keys for overlap thresholds, cache settings, walk speed).

## NLP Architecture (Dual Engine)

The system has two NLP engines with automatic fallback:

1. **BERT Engine** (`bert_nlp_engine.py`):
   - Model: `dbmdz/bert-base-turkish-uncased`
   - Semantic similarity for typo tolerance ("Kadıköy" ≈ "Kadiköy")
   - Query type classification: route, poi, multi, single
   - Place extraction with Turkish suffix parsing (-den, -dan, -ye, -ya, etc.)
   - OpenStreetMap API integration for dynamic place lookup
   - Thread-safe singleton with `get_bert_nlp_engine()`

2. **Regex Fallback** (`nlp_engine.py`):
   - Activates when BERT unavailable
   - Pattern matching for route queries
   - Simple keyword extraction

**Important:** When adding NLP features, update BOTH engines or document BERT-only behavior.

## Graph Management

`graph_manager.py` handles OSMnx graph operations:

- `get_graph(center_lat, center_lon, radius_m)` - LRU cached graph retrieval
- `get_graph_for_points(points)` - Auto-calculated bounding box
- `search_pois(query, lat, lon, category)` - POI search via Overpass API

Graph caching uses:
- LRU cache with max 10 graphs in memory
- TTL of 1 hour (3600s)
- Disk cache in `backend/data/`

## Database Schema

SQLite databases in `backend/data/`:

**routes.db:**
- `routes` table: id, name, origin_lat, origin_lon, destination_lat/lon, waypoints_json, distance, duration, created_at
- `route_points` table: route_id, point_order, lat, lon

**locations.db:**
- `saved_locations` table: id, name, lat, lon, icon, is_favorite, note
- `local_places` table: Dynamic OSM cache with search_terms, display_name

## API Response Format

All route endpoints return this structure:
```python
{
    "route": [[lat, lon], ...],      # GeoJSON-like coordinates
    "distance_km": float,
    "duration_min": float,
    "google_maps_link": str,
    "alternative_routes": [           # If requested
        {"route": [...], "distance_km": ..., "type": "fastest|balanced|scenic"}
    ]
}
```

NLP parse response:
```python
{
    "type": "route|poi|multi|single|unknown",
    "confidence": float,
    "origin": str | None,
    "destination": str | None,
    "location": str | None,            # For POI queries
    "locations": [str],                # For multi-destination
    "detected_places": [{"place": str, "similarity": float, ...}],
    "parse_time": float,
    "error": str | None
}
```

## Environment Variables

Control BERT behavior at runtime:
- `ORP_BERT_USE_OSM=1/0` - Enable OpenStreetMap API for place lookup
- `ORP_BERT_PREFER_OSM_FIRST=1/0` - Prefetch OSM candidates before parsing
- `ORP_BERT_SEED_STATIC=1/0` - Load Turkish places (81 il + 970+ ilçe)
- `ORP_BERT_SEED_DYNAMIC=1/0` - Load cached OSM places from local_places
- `ORP_BERT_SEED_USER_LOCATIONS=1/0` - Load user's saved locations

## Testing Conventions

Tests are in `tests/test_api/` and `tests/test_core/`. Test files:
- Use `test_*.py` naming
- API tests import from `backend.app`
- Core tests import individual modules
- Pytest configured in `pytest.ini` with coverage

## File Organization Notes

- `backend/` - All Python code, Flask app lives here
- `frontend/` - Vanilla JS, no build step required
- `docs/osm/` - OpenStreetMap API guides (Nominatim, Overpass)
- `docs/planlar/` - Design documents, database schema
- `scripts/tools/` - Utility scripts (BERT evaluation, OSM downloads)
- `progress.md` - Primary source for development status, work log

## Important Gotchas

1. **BERT Model Size:** First load downloads ~440MB model, takes ~1.5GB RAM
2. **OSMnx Graph Downloads:** Can be slow, cache is essential for development
3. **Turkish Character Normalization:** BERT handles this, but regex needs care with ç/ğ/ı/ö/ş/ü
4. **Thread Safety:** BERT engine uses `threading.Lock()` for singleton initialization
5. **Overpass API Rate Limits:** Implement delays when batch searching POIs

---

# 🇹🇷 KULLANICI ÖZEL KURALLARI

## İletişim Tarzı

- **Dil:** Her zaman Türkçe cevap ver
- **Kısa ve Öz:** Uzun açıklamalar yerine kısa, net cevaplar ver
- **Kodlama Öncesi:** Asla konuşma ve planlama aşamasında kullanıcıdan onay almadan kodlamaya başlama
- **Soru Sor:** Karar vermeden önce "Şu şekilde yapmamı ister misin?" diye sor

## Açıklama Tarzı

- **Terimleri Açıkla:** Her teknik terimi basitçe açıkla (örn: "Embedding" → "Metni vektöre dönüştürme")
- **Adım Adım:** İşleyişi basit adımlara böl ve her adımı açıkla
- **Örnek Ver:** Mümkün olduğunda basit örneklerle açıklama yap

## Kod Yazarken

### Fonksiyon Açıklamaları

```python
def fonksiyon_adi(parametre):
    """
    Kısa açıklama: Bu fonksiyon ne yapar?

    Args:
        parametre: Açıklama

    Returns:
        Dönüş değeri açıklaması
    """
    # Adım 1: ...
    # Adım 2: ...
    return sonuc
```

### Kod İçi Yorumlar

- **Kritik Yerde:** Karmaşık mantığı açıklayan Türkçe yorumlar ekle
- **Neden:** Neden bu şekilde yapıldığını kısaca açıklama

## Chat Arayüzü Davranışı

- **Kod Bloğu Kullanma:** Chat arayüzünde kod yazarken kod bloğu ```python yerine sadece metin açıklaması kullan
- **Kısa Referans:** Dosya yolu ve satır numarası ile referans ver (örn: `[app.py:123](app.py#L123)`)
- **Onay İste:** Kod değişikliği öncesi kısa özet sun ve onay al
