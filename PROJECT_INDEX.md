# OpenRoutePlanner - Live Project Index

Last updated: 2026-05-27

This index reflects the current codebase state in `OpenRoutePlanner` and is intended as a working map for future feature add/remove/refactor tasks.

## 1) Top-Level Structure

- `backend/`: Flask API, route engine, NLP/BERT, weather, storage, caching.
- `frontend/`: Main web UI (`index.html`) + JS/CSS + BERT test lab.
- `tests/`: Pytest suites (`test_api`, `test_core`) + BERT gold data.
- `scripts/`: Utility scripts (`tools`, `fix`, debugging helpers).
- `docs/`: Design notes, plans, reports, OSM references.
- `backend/data/`: SQLite app DB + GraphML map caches.
- `backend/cache/`: geocode + district DB + hashed API/cache artifacts.

## 2) Runtime Architecture (High Level)

1. `backend/app.py` boots Flask and runs startup init (`ensure_db`, sqlite maintenance, geocode purge, graph preload).
2. Frontend calls API endpoints for route, geocode, NLP, storage, timeline.
3. Route calculations use `graph_manager.py` + `route_engine.py` (OSMnx + NetworkX).
4. NLP parse path uses BERT stack (`bert_engine.py` + `bert_nlp_engine.py`).
5. Weather endpoints call `weather_service.py` (Open-Meteo) + `weather_utils.py`.
6. Persistence is SQLite via `storage_db.py`, `route_storage.py`, `location_storage.py`.

## 3) Backend Module Index

### Core Entry + Service Files

| File | Lines | Responsibility |
|---|---:|---|
| `backend/app.py` | 1520 | Flask app, endpoint registry, startup lifecycle, API wiring |
| `backend/route_engine.py` | 1030 | Shortest path, TSP, alternative routes, overlap/penalty/via-node logic |
| `backend/graph_manager.py` | 227 | Graph download/load/cache, nearest node, POI search, preload regions |
| `backend/geocoder.py` | 523 | Forward/reverse/suggest geocoding + sqlite cache + rate limit |
| `backend/route_storage.py` | 330 | Route CRUD/statistics/favorite/search |
| `backend/location_storage.py` | 221 | Saved location CRUD/favorite/search/usage |
| `backend/time_planner.py` | 269 | Timeline generation/conflict check/schedule optimize |
| `backend/storage_db.py` | 239 | SQLite pooled connection + schema + maintenance |
| `backend/cache_manager.py` | 228 | In-memory LRU caches (graph + POI) |

### NLP / BERT / Weather Focus Files

| File | Lines | Responsibility |
|---|---:|---|
| `backend/bert_engine.py` | 310 | BERT model load/encode/similarity + runtime metrics |
| `backend/bert_nlp_engine.py` | 1062 | Query classification, place extraction, OSM-backed place DB, parse orchestration |
| `backend/nlp_engine.py` | 373 | Legacy regex parser (still present, not active primary parse path) |
| `backend/weather_service.py` | 981 | Open-Meteo current/forecast/route weather, cache, health/status |
| `backend/weather_utils.py` | 923 | Weather code maps, validation, formatting, alerts/suggestions |

### Support / Schema / Utilities

| File | Lines | Responsibility |
|---|---:|---|
| `backend/models.py` | 372 | Pydantic request/response/domain schemas |
| `backend/response_utils.py` | 514 | Standardized API responses and helpers |
| `backend/spatial_index.py` | 415 | POI spatial indexing/cache helpers |
| `backend/route_config.py` | 117 | Route and cache tuning constants |
| `backend/local_places.py` | 201 | Seed + dynamic local place store |
| `backend/turkey_places.py` | 105 | Static Turkey places dataset helper |
| `backend/osm_poi_dictionary.py` | 225 | Turkish keyword -> OSM tag mapping |
| `backend/districts_db.py` | 193 | District sqlite helper + search |

## 4) Actual API Endpoint Index (`backend/app.py`)

### Route + POI

- `POST /api/get-route`
- `POST /api/get-route-steps`
- `POST /api/get-alternative-routes`
- `POST /api/search-pois`

### Health + Geocode

- `GET /api/health`
- `GET /api/cache/stats`
- `GET /api/geocode/suggest`
- `POST /api/geocode`
- `POST /api/reverse-geocode`
- `POST /api/geocode/batch`

### Frontend Serving

- `GET /`
- `GET /<path:filepath>`

### Routes Storage

- `POST /api/routes/save`
- `GET /api/routes`
- `GET /api/routes/<route_id>`
- `PUT /api/routes/<route_id>`
- `DELETE /api/routes/<route_id>`
- `POST /api/routes/<route_id>/favorite`
- `GET /api/routes/search`
- `GET /api/routes/statistics`

### Timeline

- `POST /api/timeline/create`
- `POST /api/timeline/check-conflicts`
- `POST /api/timeline/optimize`

### Locations Storage

- `GET /api/locations`
- `POST /api/locations`
- `DELETE /api/locations/<location_id>`
- `PUT /api/locations/<location_id>`
- `POST /api/locations/<location_id>/favorite`

### NLP / BERT

- `POST /api/nlp/parse`
- `GET /api/nlp/status`
- `POST /api/nlp/similarity`
- `POST /api/nlp/best-match`

### Weather

- `GET /api/weather`
- `GET /api/weather/forecast`
- `POST /api/weather/check-route`
- `GET /api/weather/status`
- `GET /api/weather/health`
- `POST /api/weather/clear-cache`

### Multimodal

- `POST /api/multimodal/compare`

## 5) BERT-Focused Deep Index

### Main BERT files

- `backend/bert_engine.py`: model lifecycle, embedding generation, similarity API, runtime GPU metrics.
- `backend/bert_nlp_engine.py`: end-to-end NLP parsing with semantic templates and place matching.
- `frontend/bert-test-lab.html`: dedicated BERT test UI hitting `/api/nlp/*`.
- `tests/data/bert_gold_tr_v1.jsonl`: gold dataset for BERT evaluation scripts.
- `scripts/tools/evaluate_bert_gold.py`: BERT gold evaluation utility.

### BERT runtime behavior (current)

- Model: `dbmdz/bert-base-turkish-uncased`.
- Default policy: GPU required (`ORP_BERT_FORCE_GPU=1` by default).
- If GPU is not available and force mode is on, engine raises runtime error.
- Runtime metrics available via `BERTEngine.get_runtime_metrics()`.

### BERT parse pipeline (current)

1. Query type classification via semantic template embeddings (`route/poi/multi/single`).
2. Candidate span extraction with Turkish suffix role hints (`from/to/loc`).
3. Place matching against in-memory place DB embeddings.
4. Optional OSM-backed dynamic enrichment and local dynamic cache write.
5. Intent refinement based on role hints and cue words.
6. Structured response assembly (`type`, `confidence`, entities, parse_time).

### BERT place data sources (ordered by config)

- dynamic OSM cache (`local_places` dynamic entries),
- local seed places (`local_places`),
- user-saved locations (`location_storage`),
- static Turkey places (`turkey_places`).

### BERT-related env flags

- `ORP_BERT_FORCE_GPU`
- `ORP_BERT_LOG_METRICS`
- `ORP_BERT_METRICS_INTERVAL_SEC`
- `ORP_BERT_USE_OSM`
- `ORP_BERT_PREFER_OSM_FIRST`
- `ORP_BERT_SEED_DYNAMIC`
- `ORP_BERT_SEED_LOCAL`
- `ORP_BERT_SEED_STATIC`
- `ORP_BERT_SEED_USER_LOCATIONS`

### Important note

- `POST /api/nlp/parse` currently requires BERT availability and returns `503` if unavailable.
- Legacy regex parser still exists (`backend/nlp_engine.py`) but is not the active parse path.

## 6) Weather-Focused Deep Index

### Main weather files

- `backend/weather_service.py`: API client + parser + cache + service status/health.
- `backend/weather_utils.py`: weather code parsing, data checks, helper formatting/alerts.
- `backend/app.py`: weather endpoint surface under `/api/weather*`.
- `backend/test_weather_service.py`: standalone weather test script (not in `tests/` package).

### Weather service behavior

- Provider: Open-Meteo (`https://api.open-meteo.com/v1/forecast`).
- In-memory cache TTL: `900s` (15 minutes).
- Request timeout: `10s`.
- Supported operations:
  - current weather by coordinates,
  - hourly forecast (`1..168` hours),
  - route weather checks for multiple points,
  - service status and health,
  - cache clear.

### Route weather output model

- `route_weather`: per-point weather records.
- `warnings`: weather alerts synthesized from utility rules.
- `overall_conditions`: aggregate route condition label.

### Important note

- Weather endpoints are integrated in frontend (`frontend/js/app.js`) via:
  - widget fetch (`/api/weather`),
  - route weather check (`/api/weather/check-route`),
  - forecast simulator (`/api/weather/forecast`).

## 7) Frontend Index

### Files

- `frontend/index.html` (435): main app shell.
- `frontend/js/app.js` (1616): app logic for map, routes, POI, saved entities, NLP.
- `frontend/css/style.css` (1613): style system including NLP block styles.
- `frontend/bert-test-lab.html` (829): BERT diagnostic playground.

### Main frontend modules in `app.js`

- Point management + drag/sort.
- Route calculation + rendering.
- Alternative routes UI.
- POI search/render.
- Geocode search + suggestions.
- NLP query flow (`/api/nlp/parse`) + apply/focus actions.
- Saved routes and saved locations CRUD UI.
- Timeline generation UI.

### Current frontend integration snapshot

- NLP integrated in main UI.
- Weather integrated in main UI (widget + route banner + simulator).

## 8) Data and Persistence Map

- Main app DB: `backend/data/app_data.db`
- Graph caches: `backend/data/*.graphml`
- Geocode/district caches: `backend/cache/geocodes.db`, `backend/cache/districts_turkey.db`
- Weather cache: in-memory process cache (not persisted to disk by default)

## 9) Test and Quality Snapshot (2026-05-27)

Command run:

`.\venv_test\Scripts\python.exe -m pytest -q`

Result:

- 96 tests collected
- 96 passed
- 0 failed

Current status:

- Frontend transit UI contract tests are passing.
- Route-engine regression tests include:
  - direction-sensitive overlap,
  - unreachable waypoint contract behavior,
  - dynamic via-node sampling bounds,
  - MultiDiGraph edge-key penalty handling.

## 10) Change Entry Points (for next tasks)

If a change request is about:

- **BERT parse behavior**: start from `backend/bert_nlp_engine.py` (`classify_query_type`, `extract_places`, `parse`).
- **BERT model/runtime policy**: `backend/bert_engine.py` (`__init__`, `get_runtime_metrics`).
- **Weather data and alerts**: `backend/weather_service.py` + `backend/weather_utils.py`.
- **Weather endpoint contracts**: `backend/app.py` weather routes (`/api/weather*`).
- **Main UI behavior**: `frontend/js/app.js` + `frontend/index.html`.
- **Route algorithm changes**: `backend/route_engine.py` + `backend/route_config.py`.
- **Storage behavior**: `backend/route_storage.py`, `backend/location_storage.py`, `backend/storage_db.py`.

