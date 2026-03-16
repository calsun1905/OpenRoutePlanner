# OpenRoutePlanner - Loglama Sistemi Özeti

## 📅 Oluşturulma Tarihi
2026-03-07

## ✅ Tamamlanan İşler

### 1. Merkezi Loglama Konfigürasyonu (`backend/logging_config.py`)
- **StructuredFormatter**: Timestamp + Seviye + Modül + Fonksiyon + Satır + Mesaj
- **JSONFormatter**: Log aggregation sistemleri için
- **Çoklu handler**: Console (renkli), File (tüm loglar), Error file (sadece hatalar)
- **Özel method'lar**: `info_data()`, `debug_data()`, `warning_data()`, `error_data()`

### 2. Backend Loglaması

#### `backend/route_engine.py`
- ✅ Dijkstra algoritması loglaması
- ✅ TSP optimizasyonu loglaması
- ✅ Alternatif rota hesaplama v3.0 loglaması
  - ADIM 1: En kısa rota
  - ADIM 2: Via-Node rotaları
  - Structured data ile performans takibi

#### `backend/app.py`
- ✅ Import: `import logging` + `from logging_config import get_logger, setup_logging`
- ✅ Startup loglaması
- ✅ Middleware: Her istek için loglama
- ✅ `/api/get-alternative-routes` endpoint loglaması
  - İstek validation
  - Nokta sayısı kontrolü
  - Optimizasyon parametresi

### 3. Frontend Loglaması (`frontend/js/app.js`)
- ✅ LOG objesi: timestamp, seviye, renkli çıktı
- ✅ Seviyeler: DEBUG, INFO, WARN, ERROR
- ✅ Özel method'lar: `LOG.api()`, `LOG.route()`
- ✅ `displayAlternativeRoutes()`: Cache dolumu loglaması
- ✅ `selectAlternativeRoute()`: Rota seçimi loglaması

### 4. Test Scripti (`backend/test_logging.py`)
- ✅ 5 test senaryosu
- ✅ Temel loglama seviyeleri
- ✅ Structured logging (extra data)
- ✅ Route engine simülasyonu
- ✅ Error logging (exception)
- ✅ Performance logging

## 📊 Loglama Seviyeleri

| Seviye | Kullanım Alanı | Console | File |
|--------|----------------|---------|------|
| **DEBUG** | Detaylı algoritma adımları | ❌ | ✅ |
| **INFO** | Önemli olaylar (rota hesaplandı, endpoint çağrıldı) | ✅ | ✅ |
| **WARNING** | Potansiyel sorunlar | ✅ | ✅ |
| **ERROR** | Hatalar | ✅ | ✅ |

## 📁 Log Dosyaları

```
OpenRoutePlanner/
├── backend/
│   ├── logging_config.py      # Merkezi konfigürasyon
│   ├── test_logging.py         # Test scripti
│   └── ...
├── logs/
│   ├── app.log                 # Tüm loglar (DEBUG+)
│   └── errors.log              # Sadece hatalar
└── frontend/
    └── js/
        └── app.js              # Console loglama (LOG objesi)
```

## 🎯 Test Edilecek Kısımlar

### Backend
1. **Alternatif rota hesaplama** - Via-Node algoritması
2. **API endpoint'ler** - İstek/yanıt loglaması
3. **Hata yönetimi** - Exception yakalama

### Frontend
1. **Alternatif rota seçimi** - Console logları
2. **API çağrıları** - Network logları
3. **Cache yönetimi** - alternativeRoutesCache

## 🚀 Kullanım Örnekleri

### Backend (Python)
```python
from logging_config import get_logger

logger = get_logger(__name__)

# Basit log
logger.info("Rota hesaplandı")

# Structured log
logger.info_data("Alternatif rota bulundu",
                via_node=12345,
                distance_km=4.2)
```

### Frontend (JavaScript)
```javascript
// Basit log
LOG.info("Rota hesaplandı");

// Structured log
LOG.route("Alternatif rota seçildi", { type: "route_2", coords_count: 150 });
```

## ⚠️ Bilinen Sorunlar

1. **Karakter kodlama**: Windows terminal'de Türkçe karakterler gösteremiyor (cp1254 sorunu)
2. **Çözüm**: Log dosyalarına UTF-8 ile yazılıyor, dosya okuyarak kontrol edin

## 📝 Notlar

- Loglama sistemi test edildi ve çalışıyor
- Backend'de `logging` import edildi
- Frontend'de console'a renkli loglar yazılıyor
- Test scripti: `cd backend && python test_logging.py`
