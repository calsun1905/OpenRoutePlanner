# Route API Contract & Smoke Test Dok�mantasyonu

> **Tarih:** 2026-05-24  
> **Ama�:** QA smoke test script'i i�in Route API contract analizi

---

## 📋 ?�indekiler

1. [Endpoint Özeti](#1-endpoint-�zeti)
2. [Request/Response Formatlar?](#2-requestresponse-formatlar?)
3. [Error Response Schema'lar?](#3-error-response-schemalar?)
4. [Validation Kurallar?](#4-validation-kurallar?)
5. [Smoke Test Script Kullan?m?](#5-smoke-test-script-kullan?m?)
6. [Test Senaryolar?](#6-test-senaryolar?)

---

## 1. Endpoint Özeti

| Endpoint | Method | A�?klama |
|----------|--------|----------|
| `/api/get-route` | POST | Ana rota oluşturma endpoint'i |
| `/api/get-route-steps` | POST | Ad?m-ad?m y�nlendirme |
| `/api/get-alternative-routes` | POST | 3 alternatif rota d�ner |
| `/api/routes/save` | POST | Rotay? kaydet |
| `/api/routes` | GET | Kay?tl? rotalar? listele |
| `/api/routes/<route_id>` | GET/PUT/DELETE | ID ile rota işlemleri |
| `/api/routes/<route_id>/favorite` | POST | Favori toggle |
| `/api/routes/search` | GET | Rota arama |
| `/api/routes/statistics` | GET | ?statistikler |

---

## 2. Request/Response Formatlar?

### POST `/api/get-route`

#### Request Body

```json
{
  "points": [[lat, lon], [lat, lon], ...],
  "optimize": true | false,       // varsay?lan: false
  "route_type": "route_1" | "route_2" | "route_3"  // varsay?lan: route_1
}
```

| Alan | Tip | Zorunlu | A�?klama |
|------|-----|---------|----------|
| `points` | array[array[float, float]] | Evet | Enlem/boylam koordinatlar? |
| `optimize` | boolean | Hay?r | TSP optimizasyonu (2+ nokta) |
| `route_type` | string | Hay?r | route_1, route_2, route_3 |

#### Başar?l? Response (HTTP 200)

```json
{
  "optimized_order": [0, 2, 1, ...],
  "route_coords": [[lat, lon], ...],
  "total_distance_km": 4.5,
  "estimated_walk_minutes": 55,
  "google_maps_link": "https://www.google.com/maps/dir/...",
  "route_type": "route_1"
}
```

| Alan | Tip | A�?klama |
|------|-----|----------|
| `optimized_order` | int[] | TSP sonras? s?ra |
| `route_coords` | float[][] | Rota geometrisi |
| `total_distance_km` | float | Toplam mesafe (km) |
| `estimated_walk_minutes` | int | Tahmini y�r�me s�resi (dk) |
| `google_maps_link` | string | Google Maps linki |
| `route_type` | string | Kullan?lan rota tipi |

---

### POST `/api/get-route-steps`

#### Request Body

```json
{
  "points": [[lat, lon], ...],
  "optimize": true | false,
  "route_type": "route_1"
}
```

#### Başar?l? Response (HTTP 200)

```json
{
  "steps": [
    {
      "instruction": "1200 metre boyunca yol uzerinde ilerleyin.",
      "distance_m": 1200,
      "duration_min": 14
    }
  ],
  "route_coords": [[lat, lon], ...]
}
```

---

### POST `/api/get-alternative-routes`

#### Request Body

```json
{
  "points": [[lat, lon], [lat, lon], ...],
  "optimize": true | false
}
```

#### Başar?l? Response (HTTP 200)

```json
{
  "alternatives": [
    {
      "type": "route_1",
      "name": "Rota 1",
      "icon": "@",
      "route_coords": [[lat, lon], ...],
      "distance_km": 4.5,
      "duration_minutes": 55,
      "description": "4.5 km",
      "google_maps_link": "https://..."
    }
  ]
}
```

---

## 3. Error Response Schema'lar?

### no_pedestrian_path (HTTP 400)

```json
{
  "error": "Yaya agi uzerinde baglantili rota bulunamadi.",
  "code": "no_pedestrian_path",
  "suggestion": {
    "action": "adjust_points",
    "message": "Noktalari yaya yollarina yakin secip tekrar deneyin."
  }
}
```

**Tetikleyici:** `build_alternative_routes()` boş node listesi d�nd�ğ�nde

**Ç�z�m:** Noktalar? yaya yollar?na yak?n se�ip tekrar deneyin

---

### no_route_geometry (HTTP 400)

```json
{
  "error": "Rota geometrisi olusturulamadi. Yaya agi baglantisi olmayan bir gecis olabilir.",
  "code": "no_route_geometry",
  "suggestion": {
    "action": "adjust_points",
    "message": "Noktalari yaya yollarina yakin secip tekrar deneyin."
  }
}
```

**Tetikleyici:** `nodes_to_coords()` boş koordinat listesi d�nd�ğ�nde

**Ç�z�m:** Noktalar? yaya yollar?na yak?n se�ip tekrar deneyin

---

### outside_istanbul (HTTP 400)

```json
{
  "error": "Bu ozellik su an sadece Istanbul sinirlari icin kullanilabilir.",
  "code": "outside_istanbul",
  "geofence": {
    "min_lat": 40.78,
    "max_lat": 41.40,
    "min_lon": 28.30,
    "max_lon": 29.70
  },
  "detail": "points[0] koordinati Istanbul disinda: (39.9208, 32.8541)",
  "field": "points"
}
```

**Tetikleyici:** Herhangi bir koordinat Istanbul bounding box'? d?ş?nda

**Istanbul Bounding Box:**
- min_lat: 40.78
- max_lat: 41.40
- min_lon: 28.30
- max_lon: 29.70

---

### no_alternative_route (HTTP 400)

```json
{
  "error": "Alternatif yaya rota bulunamadi.",
  "code": "no_alternative_route",
  "suggestion": {
    "action": "retry_primary_route",
    "message": "Bu nokta kombinasyonu icin ana rotayi deneyin veya noktalari yakinlastirin."
  }
}
```

**Tetikleyici:** `build_all_alternative_routes_batch()` boş sonu� d�nd�ğ�nde

---

## 4. Validation Kurallar?

| Kural | Endpoint | HTTP Code |
|-------|----------|-----------|
| `points` zorunlu | T�m route endpoint'leri | 400 |
| En az 2 nokta gerekli | `/api/get-route`, `/api/get-route-steps` | 400 |
| Her nokta `[lat, lon]` format?nda olmal? | T�m route endpoint'leri | 400 |
| Enlem: -90 ≤ lat ≤ 90 | T�m route endpoint'leri | 400 |
| Boylam: -180 ≤ lon ≤ 180 | T�m route endpoint'leri | 400 |
| Koordinatlar Istanbul s?n?rlar? i�inde olmal? | T�m route endpoint'leri | 400 |

### Istanbul Geofence Kontrol� Ak?ş?

```
Request → _first_outside_point(points) 
         → _is_in_istanbul_bbox(lat, lon)
         → outside_istanbul response (400)
```

---

## 5. Smoke Test Script Kullan?m?

### Gereksinimler

- Windows PowerShell 5.1+
- Flask sunucusunun �al?ş?yor olmas?

### Kullan?m

```powershell
# Varsay?lan ayarlarla �al?şt?r
.\scripts\qa_route_contract.ps1

# Farkl? base URL ile �al?şt?r
.\scripts\qa_route_contract.ps1 -BaseUrl http://localhost:5000

# JSON format?nda �?kt?
.\scripts\qa_route_contract.ps1 -OutputFormat Json

# T�m se�enekler
.\scripts\qa_route_contract.ps1 -BaseUrl http://localhost:5000 -OutputFormat Json -Verbose
```

### Ç?kt? Formatlar?

| Format | A�?klama |
|--------|----------|
| Text | Renkli konsol �?kt?s? (varsay?lan) |
| Json | JSON dosyas? olarak rapor |
| Csv | CSV format?nda rapor (gelecek) |

### Exit Codes

| Code | A�?klama |
|------|----------|
| 0 | T�m testler başar?l? |
| 1 | En az bir test başar?s?z |

---

## 6. Test Senaryolar?

### Test Suite: Health

| Test | A�?klama |
|------|----------|
| `GET /api/health` | Sunucu sağl?k kontrol� |

### Test Suite: Route

| Test | A�?klama | Beklenen Status |
|------|----------|----------------|
| Basic Success | Ge�erli Istanbul noktalar? ile rota | 200 |
| With Optimization | TSP optimizasyonu aktif | 200 |
| Missing Points | `points` alan? eksik | 400 |
| Insufficient Points | Sadece 1 nokta g�nderildi | 400 |
| Invalid Point Format | Nokta `[lat,lon]` format?nda değil | 400 |
| Outside Istanbul | Ankara koordinat? g�nderildi | 400 |

### Test Suite: Route Steps

| Test | A�?klama | Beklenen Status |
|------|----------|----------------|
| Basic Success | Ad?m-ad?m y�nlendirme isteği | 200 |

### Test Suite: Alternative Routes

| Test | A�?klama | Beklenen Status |
|------|----------|----------------|
| Basic Success | 3 alternatif rota isteği | 200 |

### Test Suite: Error Responses

| Test | Hata Tipi | Kontrol Edilen Alanlar | Not |
|------|----------|------------------------|-----|
| no_pedestrian_path | code, error, suggestion | 400 | Edge case koordinatlar gerekebilir |
| no_route_geometry | code, error, suggestion | 400 | OSM graph boşluklar? tetikleyebilir |
| outside_istanbul | code, geofence, field, suggestion | 400 | Ankara koordinat? ile test |

**Not:** `no_pedestrian_path` ve `no_route_geometry` hatalar?n? tetiklemek i�in ger�ek OSM graph'ta bağlant? olmayan nokta kombinasyonlar? gerekir. Pytest'te monkeypatch ile mock yap?l?r, smoke test'te ger�ek koordinatlar kullan?l?r.

#### Koordinat Kombinasyonlar?

| Senaryo | Noktalar | Beklenen Sonu� |
|---------|---------|----------------|
| Kad?k�y → Ayr?l?k Çeşmesi | (40.9911, 29.0289), (40.9928, 29.0060) | OSM graph gap olas?l?ğ? |

### Test Suite: Route Storage

| Test | A�?klama | Beklenen Status |
|------|----------|----------------|
| List Routes | Kay?tl? rotalar? listele | 200 |
| Save Route | Yeni rota kaydet | 200 |
| Route Stats | ?statistikleri getir | 200 |

---

## Mermaid Ak?ş Diyagram?

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant GraphMgr
    participant RouteEngine
    
    Client->>API: POST /api/get-route {points, optimize, route_type}
    API->>API: Validate points (min 2, [lat,lon] format)
    API->>API: Check Istanbul geofence
    API->>GraphMgr: get_graph_for_points(point_tuples)
    alt optimize=true AND len(points)>2
        API->>RouteEngine: solve_tsp(G, points)
    end
    API->>RouteEngine: build_alternative_routes(G, ordered_points, route_index)
    alt route_nodes empty
        API-->>Client: 400 no_pedestrian_path
    end
    API->>RouteEngine: nodes_to_coords(G, route_nodes)
    alt route_coords empty
        API-->>Client: 400 no_route_geometry
    end
    API->>RouteEngine: calculate_route_stats(G, route_nodes)
    API-->>Client: 200 {optimized_order, route_coords, total_distance_km, ...}
```

---

## Headers & Authentication

| Header | A�?klama |
|--------|----------|
| `Content-Type: application/json` | POST istekleri i�in |
| `X-Request-ID` | ?steğe bağl?, request takibi |
| `X-Correlation-ID` | ?steğe bağl?, correlation ID |

**CORS:** T�m endpoint'lerde etkin (`CORS(app)`)

---

## Ek: Pytest Testleri ile Karş?laşt?rma

Mevcut pytest testleri (`tests/test_api/test_routes.py`):

| Pytest Test | Smoke Script Karş?l?ğ? |
|-------------|------------------------|
| `test_get_route_rejects_outside_istanbul` | POST /api/get-route - Outside Istanbul |
| `test_get_route_returns_no_pedestrian_path_code` | Manuel mock gerekli |
| `test_get_route_returns_no_route_geometry_code` | Manuel mock gerekli |
| `test_get_alternative_routes_returns_no_alternative_code` | Manuel mock gerekli |

**Not:** `no_pedestrian_path` ve `no_route_geometry` hatalar?n? tetiklemek i�in graf mock'lanmas? gerekir. Bu pytest'te `monkeypatch` ile yap?l?r, smoke test'te ise ger�ek koordinatlar ile test edilebilir.