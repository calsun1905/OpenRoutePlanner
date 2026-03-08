# OpenRoutePlanner

Türkiye için optimize edilmiş, yapay zeka destekli rota planlama uygulaması.

## Özellikler

### 🗺️ Rota Optimizasyonu
- **TSP (Traveling Salesman)**: Birden fazla nokta için en kısa rota
- **Dijkstra**: En hızlı yaya rotası
- **Alternatif Rotalar v3.0**: Via-node ile 3 farklı rota seçeneği
- **Overlap Kontrolü**: Rotalar arası benzerlik yönetimi (%30 hedef)

### 🤖 Yapay Zeka
- **BERT NLP Engine**: Doğal dilde rota sorgusu (Türkçe)
- **17 POI Kategorisi**: Restoran, kafe, ATM, eczane, market vb.
- **Yer Tanıma**: 81 il + ilçe = 1775 Türk yerleşimi
- **Regex Fallback**: BERT yoksa alternatif motor

### ⏰ Zaman Planlama
- **Timeline Oluşturma**: Günlük rota planlaması
- **Çakışma Kontrolü**: Zaman çakışması tespiti
- **Optimizasyon**: Zaman verimliliği için

### 💾 Veri Saklama
- **SQLite Database**: Rota ve konum kayıt sistemi
- **Favori Rotalar**: Kayıtlı rotalar
- **Kayıtlı Konumlar**: Sık kullanılan yerler
- **Emoji İkonları**: Konumlar için görsel işaretleyiciler

## API Endpoints (25 adet)

### Rota (7 endpoint)
| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/api/get-route` | POST | Ana rota optimizasyonu (TSP/Dijkstra) |
| `/api/get-alternative-routes` | POST | 3 alternatif rota (fastest/balanced/scenic) |
| `/api/routes` | GET | Kayıtlı rotaları listele |
| `/api/routes` | POST | Rota kaydet |
| `/api/routes/<id>` | DELETE | Rota sil |
| `/api/routes/<id>` | PATCH | Rota güncelle |
| `/api/routes/statistics` | GET | Rota istatistikleri |

### Konum (7 endpoint)
| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/api/geocode/forward` | GET | İsim → Koordinat |
| `/api/geocode/reverse` | GET | Koordinat → İsim |
| `/api/geocode/suggest` | GET | Otomatik tamamlama önerileri |
| `/api/geocode/batch` | POST | Toplu geocoding |
| `/api/locations` | GET | Kayıtlı konumları listele |
| `/api/locations` | POST | Konum kaydet |
| `/api/locations/<id>` | DELETE | Konum sil |

### NLP (2 endpoint)
| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/api/nlp/parse` | POST | Doğal dil sorgusu parse et |
| `/api/nlp/status` | GET | NLP motoru durumu |

### Timeline (3 endpoint)
| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/api/timeline/create` | POST | Timeline oluştur |
| `/api/timeline/check-conflicts` | POST | Çakışma kontrolü |
| `/api/timeline/optimize` | POST | Zaman optimizasyonu |

### Diğer (6 endpoint)
| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/api/health` | GET | Sağlık kontrolü |
| `/api/search-pois` | POST | POI arama (Overpass API) |
| `/api/locations/<id>/favorite` | PATCH | Konum favori toggle |
| `/api/routes/<id>/favorite` | PATCH | Rota favori toggle |
| `/` | GET | Frontend sunumu |
| `/*` | GET | Statik dosyalar |

## Kurulum

```bash
# 1. Repoyu klonla
git clone <repo-url>
cd OpenRoutePlanner

# 2. Sanal ortam oluştur
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. Backend'i başlat
cd backend
python app.py

# 5. Tarayıcıda aç
# http://localhost:5000
```

## Teknoloji Stack

| Katman | Teknoloji |
|--------|-----------|
| **Backend** | Flask, OSMnx, NetworkX |
| **Frontend** | Vanilla JavaScript, Leaflet |
| **AI/NLP** | Transformers (BERT), PyTorch |
| **Database** | SQLite |
| **Maps** | OpenStreetMap, Overpass API |
| **Testing** | Pytest, pytest-cov |

## Proje Yapısı

```
OpenRoutePlanner/
├── backend/
│   ├── app.py                  # Flask ana uygulama (1155 satır)
│   ├── route_engine.py         # Rota motoru (TSP, Dijkstra, Alternatif)
│   ├── graph_manager.py        # OSMnx grafiği yönetimi
│   ├── geocoder.py             # Nominatim geocoding
│   ├── route_storage.py        # Rota CRUD (SQLite)
│   ├── location_storage.py     # Konum CRUD (SQLite)
│   ├── time_planner.py         # Timeline ve çakışma kontrolü
│   ├── nlp_engine.py           # Regex fallback NLP motoru
│   ├── bert_nlp_engine.py      # BERT NLP motoru
│   ├── route_config.py         # Konfigürasyon sabitleri
│   └── storage_db.py           # SQLite veritabanı yardımcıları
├── frontend/
│   ├── index.html              # Ana HTML
│   ├── css/style.css           # Stil dosyası
│   └── js/app.js               # Frontend uygulama mantığı
├── tests/                      # Otomatik testler
│   ├── test_api/               # API endpoint testleri
│   └── test_core/              # Core modül testleri
├── requirements.txt            # Python bağımlılıkları
├── pytest.ini                  # Pytest yapılandırması
└── progress.md                 # Geliştirme durumu
```

## Test

```bash
# Tüm testleri çalıştır
pytest

# Coverage raporu oluştur
pytest --cov=backend --cov-report=html

# Sadece API testleri
pytest tests/test_api/

# Sadece core testleri
pytest tests/test_core/
```

## Yapılandırma

`backend/route_config.py` dosyasından rota motoru parametrelerini ayarlayabilirsiniz:

```python
ROUTE_CONFIG = {
    "WALK_SPEED_KMH": 5.0,              # Yürüme hızı
    "OVERLAP_THRESHOLD_SHORT": 0.90,    # < 1km overlap limiti
    "OVERLAP_THRESHOLD_MEDIUM": 0.80,   # 1-3km overlap limiti
    "OVERLAP_THRESHOLD_LONG": 0.75,     # 3-7km overlap limiti
    "OVERLAP_THRESHOLD_VERY_LONG": 0.70, # > 7km overlap limiti
    "MAX_CANDIDATES_VERY_SHORT": 50,     # < 1km max aday
    "MAX_CANDIDATES_SHORT": 75,          # 1-3km max aday
    "MAX_CANDIDATES_LONG": 100,          # 3-7km max aday
    "MAX_CANDIDATES_VERY_LONG": 150,     # > 7km max aday
    "PENALTY_FACTOR": 2.0,               # Alternatif rota ceza faktörü
    "GRAPH_RADIUS_MAX_M": 3500,          # Maksimum graf yarıçapı
}
```

## Geliştirme Durumu

Detaylı geliştirme durumu için [progress.md](progress.md) dosyasına bakınız.

### v3.0 Özellikleri (Tamamlandı)
- ✅ Via-node alternatif rota üretimi
- ✅ Asimetrik overlap hesaplama
- ✅ Gövde-only penalty uygulaması
- ✅ Telemetry logging ile performans takibi
- ✅ 82% başarı oranı edge case testlerinde

### Güvenlik Düzeltmeleri (v3.1 - Tamamlandı)
- ✅ XSS güvenlik açıkları düzeltildi (12 inline onclick → event delegation)
- ✅ Encoding/mojibake temizliği yapıldı
- ✅ Config entegrasyonu tamamlandı

### Test Altyapısı (v3.2 - Tamamlandı)
- ✅ Pytest framework kuruldu
- ✅ API smoke tests eklendi
- ✅ Core unit tests eklendi

## Lisans

Bu proje açık kaynak kodludur.

## Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Branch'e push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

## Destek

Sorun bildirmek için [GitHub Issues](../../issues) sayfasını kullanın.
