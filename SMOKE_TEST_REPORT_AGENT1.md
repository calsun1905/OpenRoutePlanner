# OpenRoutePlanner Smoke Test Report - Agent 1 (Pozitif Akış)

**Tarih:** 26 Mayıs 2026  
**Agent:** Agent 1 (Pozitif Akış Testleri)  
**Durum:** ✅ PASS

---

## 1. Environment

| Bileşen | Değer |
|---------|-------|
| Working Directory | `C:\Users\batuf\Documents\GitHub\openroute\OpenRoutePlanner` |
| Backend Port | 5001 |
| Backend Host | 127.0.0.1 |
| Python | 3.13.6 |
| Flask Backend | flask_api.py |

---

## 2. Startup Sonucu

| Adım | Durum | Detay |
|------|-------|-------|
| Process ID | ✅ | 22292 |
| Health Check | ✅ | 1 attempt'te OK |
| Backend Ready | ✅ | 30 saniye içinde hazır |

---

## 3. HTTP Testleri (T1-T6)

### T1 - GET /api/health

| Alan | Beklenen | Gerçek | Durum |
|------|----------|--------|-------|
| status_code | 200 | 200 | ✅ |
| status | "ok" | "ok" | ✅ |
| version | var | "1.0" | ✅ |

**Response:** `{"status":"ok","message":"Location & POI API calisiyor","version":"1.0"}`

---

### T2 - GET /api/stats

| Alan | Beklenen | Gerçek | Durum |
|------|----------|--------|-------|
| status_code | 200 | 200 | ✅ |
| success | true | true | ✅ |
| stats.districts | 37 | 37 | ✅ |
| stats.poi_types | 15 | 15 | ✅ |
| stats.total_pois | 123 | 123 | ✅ |

**Response:** `{"success":true,"stats":{"districts":37,"poi_types":15,"total_pois":123,"districts_with_pois":14}}`

---

### T3 - GET /api/locations

| Alan | Beklenen | Gerçek | Durum |
|------|----------|--------|-------|
| status_code | 200 | 200 | ✅ |
| success | true | true | ✅ |
| count | 37 | 37 | ✅ |

**Dosya:** `smoke_artifacts/agent1/T3_locations.json`

---

### T4 - GET /api/poi/types

| Alan | Beklenen | Gerçek | Durum |
|------|----------|--------|-------|
| status_code | 200 | 200 | ✅ |
| success | true | true | ✅ |
| count | 15 | 15 | ✅ |

**Dosya:** `smoke_artifacts/agent1/T4_poi_types.json`

---

### T5 - POST /api/nlp/parse

**Request Body:** `{"query":"Kadikoyde kafe"}`

| Alan | Beklenen | Gerçek | Durum |
|------|----------|--------|-------|
| status_code | 200 | 200 | ✅ |
| success | true | true | ✅ |
| poi_type | "kafe" | "kafe" | ✅ |
| result_count | >= 0 | 5 | ✅ |

**Response:** 
```json
{
  "success": true,
  "query": "Kadikoyde kafe",
  "location": {"name": "Kadıköy", "lat": 40.99, "lon": 29.03},
  "poi_type": "kafe",
  "result_count": 5,
  "pois": [
    {"name": "Starbucks Moda", "rating": 4.2},
    {"name": "Çeşm-i Cedit Cafe", "rating": 4.0},
    {"name": "Moda Sahil Cafe", "rating": 4.1},
    {"name": "Kadıköy'de Kahve", "rating": 4.3},
    {"name": "Yeldeğirmeni Cafe", "rating": 4.2}
  ]
}
```

---

### T6 - POST /api/poi/search

**Request Body:** `{"location":"besiktas","poi_type":"kafe"}`

| Alan | Beklenen | Gerçek | Durum |
|------|----------|--------|-------|
| status_code | 200 | 200 | ✅ |
| success | true | true | ✅ |
| result_count | integer | 4 | ✅ |

**Response:**
```json
{
  "success": true,
  "pois": [
    {"name": "Kahve Dünyası", "rating": 4.1},
    {"name": "Bebek Kahve", "rating": 4.4},
    {"name": "Akaretler Kahve", "rating": 4.1},
    {"name": "Sinanpaşa Cafe", "rating": 4.0}
  ],
  "result_count": 4
}
```

---

## 4. Pytest Özeti

**Komut:** `python -m pytest -q test_api.py backend\test_gtfs_shapes_fallback.py`

**Sonuç:**
```
============================= test session starts =============================
platform win32 -- Python 3.13.6, pytest-8.0.0, pluggy-1.6.0
rootdir: C:\Users\batuf\Documents\GitHub\openroute\OpenRoutePlanner
configfile: pytest.ini
[CompleteEngine] 37 ilçe, 15 POI tipi, 123 mekan
collected 20 items

test_api.py ...............
backend\test_gtfs_shapes_fallback.py .....

============================= 20 passed in 0.62s ==============================
```

**Dosya:** `smoke_artifacts/agent1/pytest.txt`

---

## 5. Temizlik

| Adım | Durum |
|------|-------|
| Process ID 22292 kapatıldı | ✅ |
| Process durumu kontrol edildi | ✅ |

---

## 6. Test Artifact'ları

| Dosya | Açıklama |
|-------|----------|
| `smoke_artifacts/agent1/T1_health.json` | Health check response |
| `smoke_artifacts/agent1/T2_stats.json` | Stats response |
| `smoke_artifacts/agent1/T3_locations.json` | Locations response |
| `smoke_artifacts/agent1/T4_poi_types.json` | POI types response |
| `smoke_artifacts/agent1/T5_parse.json` | NLP parse response |
| `smoke_artifacts/agent1/T6_search.json` | POI search response |
| `smoke_artifacts/agent1/pytest.txt` | Pytest output |

---

## 7. Genel Değerlendirme

| Kategori | Sonuç |
|-----------|-------|
| Backend Startup | ✅ PASS |
| Health Endpoint | ✅ PASS |
| Stats Endpoint | ✅ PASS |
| Locations Endpoint | ✅ PASS |
| POI Types Endpoint | ✅ PASS |
| NLP Parse Endpoint | ✅ PASS |
| POI Search Endpoint | ✅ PASS |
| Pytest | ✅ PASS (20/20) |

---

## 8. Sonuç

# ✅ OVERALL: PASS

Tüm testler başarıyla geçti. API düzgün çalışıyor ve tüm beklenen verileri döndürüyor.

---

**Rapor Tarihi:** 26 Mayıs 2026  
**Agent:** 1 (Pozitif Akış)
