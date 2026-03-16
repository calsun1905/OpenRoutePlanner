# OpenRoutePlanner - Proje Bilgisi

## 🎯 Proje Amacı
**OpenRoutePlanner** - Doğal dil ile rota planlama ve mekan arama uygulaması. Kullanıcıların harita üzerinde seçtiği noktaları TSP (Gezgin Satıcı Problemi) ve Dijkstra algoritmaları ile optimize ederek en kısa rotayı oluşturan bir web uygulaması.

## 📂 Proje Yapısı

### Ana Klasörler
```
OpenRoutePlanner/
├── backend/          # Python Flask API
│   ├── app.py              # Ana Flask sunucusu
│   ├── route_engine.py     # Rota hesaplama motoru v3.0
│   ├── route_config.py     # Rota motoru konfigürasyonu
│   ├── graph_manager.py    # OSMnx harita verisi yönetimi
│   ├── geocoder.py         # Nominatim geocoding + TTL cache
│   ├── route_storage.py    # Rota kaydetme/yükleme (SQLite)
│   ├── location_storage.py # Kayıtlı yerler yönetimi (SQLite)
│   ├── storage_db.py       # SQLite altyapısı (schema, index)
│   ├── bert_engine.py      # BERT embedding motoru (GPU kontrol)
│   ├── bert_nlp_engine.py  # BERT NLP (trace tabanlı parse)
│   ├── nlp_engine.py       # NLP motoru (regex + fallback)
│   ├── turkey_places.py    # Türkiye veritabanı (1775 yer)
│   ├── osm_poi_dictionary.py # OSM POI sözlüğü (167 kelime)
│   ├── time_planner.py     # Zaman planlama modülü
│   ├── weather_service.py  # OpenMeteo hava durumu servisi
│   ├── weather_utils.py    # Hava durumu tavsiye yardımcıları
│   ├── cache_manager.py    # Cache yönetimi
│   ├── spatial_index.py    # Uzamsal indeks
│   ├── logging_config.py   # Loglama konfigürasyonu
│   ├── response_utils.py   # API yanıt yardımcıları
│   ├── tag_grounder.py     # Semantic POI grounding PoC
│   ├── districts_db.py     # İlçe veritabanı
│   ├── local_places.py     # Yerel yerler
│   ├── models.py           # Veri modelleri
│   └── models/             # BERT model dosyaları
├── frontend/
│   ├── index.html          # Ana sayfa (weather widget dahil)
│   ├── bert-test-lab.html  # BERT debug & validation paneli
│   ├── css/style.css       # Stil dosyası
│   └── js/app.js          # Ana JavaScript
├── tests/                  # Test altyapısı
│   ├── test_api/           # API testleri
│   └── test_core/          # Core testler
├── docs/                   # Dokümantasyon
│   ├── planlar/            # Geliştirme planları
│   ├── osm/                # OSM rehberleri
│   ├── raporlar/           # BERT eval raporları
│   └── diagrams/           # Mimari diyagramlar
├── scripts/                # Yardımcı scriptler
├── progress.md             # İlerleme takibi (ana kaynak)
└── günlük-rapor/          # Günlük notlar
```

## 🔑 Ana Özellikler

### 1. Rota Hesaplama (`/api/get-route`)
- TSP algoritması ile nokta sıralama optimizasyonu
- Dijkstra ile en kısa yol hesaplama
- Mesafe/süre hesaplama
- Google Maps linki üretimi

### 2. Alternatif Rotalar (`/api/get-alternative-routes`) - v3.0
- **Dijkstra** → Ana rota
- **Via-Node** → Ana rotadan uzak kavşaklardan geçen rotalar
- **Gövde-only Penalty** → Zikzak önleme
- **Asimetrik Overlap** → Jaccard yerine daha doğru formül

### 3. Rota Kaydetme/Yükleme
- Rota kaydetme, yükleme, silme
- Favori sistemi (yıldızlama)
- Rota arama ve filtreleme

### 4. POI Arama (`/api/search-pois`)
- Overpass API ile canlı mekan verileri
- Kategori bazlı arama (167 Türkçe kelime → OSM etiketi)

### 5. Geocoding (`/api/geocode`)
- Nominatim API ile yer ismi → koordinat
- Memory + SQLite cache ile hızlı erişim
- Rate limiting: 1 req/s

### 6. BERT NLP Motoru
- **Model:** `dbmdz/bert-base-turkish-uncased` (440 MB, lokal)
- **Embedding:** 768 boyutlu vektörler
- **Typo Tolerance:** "Kadikoy" → "Kadıköy" (%95)
- **Sorgu Sınıflandırma:** route, poi, multi, single
- **Türkiye Veritabanı:** 81 il + ilçeler = 1775 yer

### 7. Zaman Bazlı Planlama
- Başlangıç saati seçimi
- Varış/ayrılış saatleri hesaplama
- Timeline görünümü
- ⚠️ Backend test edilmedi

## 📋 Bilinen Sorunlar

### 🔴 Yüksek Öncelik
1. **Encoding** → Bazı dosyalarda mojibake devam ediyor
2. **Semantic POI Grounding** → `tag_grounder.py` PoC var, tam entegrasyon bekliyor
3. **BERT mention/linking** → Retrieval/linking tabanlı yaklaşım planlandı, henüz uygulanmadı

### 🟡 Orta Öncelik
1. **Kısa Mesafe Overlap** → 50-100m arası rotalar %100 overlap üretiyor (UI bildirimi gerekli)
2. **Timeout** → Uzun graph indirme ~60s timeout, 120s'ye çıkarmak gerekiyor
3. **Weather → Timeline** → Hava bazlı akıllı öneri entegrasyonu bekliyor
4. **Zaman Planlama** → Frontend butonu disabled durumda

### ✅ Çözülen (Son Oturumlar)
- Alternatif rotalar v3.0 uçtan uca test edildi
- `storage_db.py` SQLite migrasyonu tamamlandı
- NLP endpoint (`/api/nlp/parse`) eklendi
- Weather service MVP tamamlandı
- BERT trace + metrics gözlemlenebilirlik eklendi

## 📝 Önemli Notlar
- **Cache:** `backend/data/*.graphml` — OSM grafları
- **Rate Limiting:** Nominatim 1 req/s, Overpass ama kullanıma göre
- **BERT:** Lokal model, internet olmadan çalışır
- **OSM:** OpenStreetMap verileri (Almanya sunucuları)
