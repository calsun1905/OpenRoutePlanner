# 📑 OpenRoutePlanner — Proje İndeksi

> Bu dosya projenin tüm bileşenlerini, dosya yapısını ve API endpoint'lerini tek bir yerden görmenizi sağlar.  
> **Son güncelleme:** 07.03.2026

---

## 📂 Proje Kök Yapısı

```
routeplanner/
├── OpenRoutePlanner/          ← Ana proje klasörü
│   ├── backend/               ← Python Flask API
│   ├── frontend/              ← HTML/CSS/JS arayüz
│   ├── progress.md            ← İlerleme takibi (ana kaynak)
│   ├── OSM_API_REHBERI.md     ← Nominatim, Overpass, Taginfo rehberi
│   ├── PROJECT_INDEX.md       ← Bu dosya (proje indeksi)
│   └── günlük-rapor/          ← Günlük notlar
│
├── cache/                     ← API cache dosyaları (JSON)
├── .claude/                   ← Cursor/Claude ayarları
└── .vscode/                   ← VS Code ayarları
```

---

## 🗂️ Backend Dosyaları (Python)

| Dosya | Satır | Açıklama |
|-------|-------|----------|
| **app.py** | ~994 | Flask API sunucusu — tüm endpoint'ler burada tanımlı |
| **graph_manager.py** | ~193 | OSMnx ile OSM harita verisi indirme, cache, POI arama |
| **route_engine.py** | ~1150 | Rota hesaplama çekirdeği v3.0 — Dijkstra, TSP, alternatif rotalar |
| **route_config.py** | 133 | Rota motoru konfigürasyon sabitleri (31 anahtar) |
| **route_storage.py** | — | Rota kaydetme, yükleme, silme, favorileme |
| **location_storage.py** | — | Kayıtlı yerler (CRUD), favorileme |

### Backend Bağımlılıkları (app.py import'ları)

- `graph_manager`: `get_graph`, `get_graph_for_points`, `search_pois`
- `geocoder`: `geocode`, `reverse_geocode`, `geocode_batch` *(dosya mevcut değilse oluşturulmalı)*
- `geocoder`: `geocode`, `reverse_geocode`, `geocode_batch`
- `route_engine`: `solve_tsp`, `build_full_route`, `build_alternative_routes`, `build_all_alternative_routes_batch`, `nodes_to_coords`, `calculate_route_stats`, `generate_google_maps_link`
- `route_storage`: `save_route`, `get_route`, `get_all_routes`, `update_route`, `delete_route`, `toggle_favorite`, `search_routes`, `get_statistics`
- `time_planner`: `create_timeline`, `format_duration`, `check_time_conflicts`, `optimize_schedule` *(dosya mevcut değilse oluşturulmalı)*
- `location_storage`: `save_location`, `get_all_locations`, `update_location`, `delete_location`, `toggle_location_favorite`

---

## 🌐 API Endpoint'leri (app.py)

### Rota ve Harita

| Endpoint | Metod | Açıklama |
|----------|-------|----------|
| `/api/get-route` | POST | Koordinat listesi → optimize rota (TSP), mesafe, süre, Google Maps linki |
| `/api/get-alternative-routes` | POST | Alternatif rotalar (v3.0: Dijkstra + Via-Node + Gövde-only Penalty) |
| `/api/search-pois` | POST | POI arama (kategori + bölge) — Overpass API |
| `/api/geocode` | POST | Yer ismi → koordinat (Nominatim) |
| `/api/reverse-geocode` | POST | Koordinat → yer ismi |
| `/api/geocode/batch` | POST | Toplu geocoding |
| `/api/health` | GET | Sağlık kontrolü |

### Rota Kaydetme/Yükleme

| Endpoint | Metod | Açıklama |
|----------|-------|----------|
| `/api/routes/save` | POST | Rota kaydet |
| `/api/routes` | GET | Tüm rotaları listele |
| `/api/routes/<id>` | GET | Tek rota getir |
| `/api/routes/<id>` | PUT | Rota güncelle |
| `/api/routes/<id>` | DELETE | Rota sil |
| `/api/routes/<id>/favorite` | POST | Favori aç/kapa |
| `/api/routes/search` | GET | Rota ara |
| `/api/routes/statistics` | GET | İstatistikler |

### Zaman Planlama

| Endpoint | Metod | Açıklama |
|----------|-------|----------|
| `/api/timeline/create` | POST | Zaman çizelgesi oluştur |
| `/api/timeline/check-conflicts` | POST | Çakışma kontrolü |
| `/api/timeline/optimize` | POST | Zamanlama optimizasyonu |

### Kayıtlı Yerler

| Endpoint | Metod | Açıklama |
|----------|-------|----------|
| `/api/locations` | GET | Tüm kayıtlı yerler |
| `/api/locations` | POST | Yer ekle |
| `/api/locations/<id>` | PUT | Yer güncelle |
| `/api/locations/<id>` | DELETE | Yer sil |
| `/api/locations/<id>/favorite` | POST | Favori aç/kapa |

### Statik

| Endpoint | Metod | Açıklama |
|----------|-------|----------|
| `/` | GET | Ana sayfa (frontend) |

---

## 🖥️ Frontend Dosyaları

| Dosya | Açıklama |
|-------|----------|
| **index.html** | Ana sayfa — OpenTrip arayüzü |
| **css/style.css** | Stil dosyası |
| **js/app.js** | Ana JavaScript — harita, rota, POI, kayıtlı yerler |

### Frontend Ana Bileşenler (index.html)

- **Sidebar:** Seçilen noktalar, yer arama, bölge seçimi, POI butonları
- **Harita:** Leaflet tabanlı interaktif harita
- **Rota butonları:** Hesapla, Alternatif Rotalar, Zaman Planla, Kaydet
- **Kayıtlı yerler:** İkon seçimi, favorileme

---

## 📚 Dokümantasyon Dosyaları

| Dosya | İçerik |
|-------|--------|
| **progress.md** | İlerleme takibi, özellik listesi, bilinen sorunlar, TODO |
| **OSM_API_REHBERI.md** | Nominatim, Overpass, Taginfo — OSM tag sistemi, projede kullanım |
| **PROJECT_INDEX.md** | Bu dosya — proje indeksi |

---

## 🔧 route_engine.py v3.0 Özeti

| Özellik | Açıklama |
|---------|----------|
| **Dijkstra** | Ana rota (en kısa yol) |
| **Via-Node** | Ana rotadan uzak kavşaklardan geçen alternatif rotalar |
| **Gövde-only Penalty** | Baş/son %10'a dokunmadan sadece gövdeye ceza |
| **Asimetrik Overlap** | "Yeni rotanın % kaçı eskiyle aynı?" (Jaccard yerine) |

---

## 📦 Harici Bağımlılıklar (Tahmini)

- **Python:** Flask, flask-cors, osmnx, networkx
- **Frontend:** Leaflet, Google Fonts (Inter)
- **API'ler:** Nominatim (geocoding), Overpass (POI)

---

## 🚀 Hızlı Başlangıç

1. Backend: `cd OpenRoutePlanner/backend && python app.py`
2. Tarayıcı: `http://localhost:5000`
3. Haritaya tıklayarak nokta ekleyin → "Rota Hesapla" → Alternatif rotaları inceleyin

---

## 📌 Önemli Notlar

- **Cache:** `backend/data/*.graphml` — OSM grafları
- **Rota/Location storage:** JSON veya SQLite (dosya yapısına göre)
- **BERT NLP:** progress.md'de bahsediliyor; `app.py`'de endpoint yok (TODO)
