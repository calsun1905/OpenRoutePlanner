# Backend Klasör Yapısı

Bu dokümantasyon, backend klasörünün yeniden düzenlenmiş yapısını açıklar.

## 📁 Klasör Yapısı

```
backend/
├── api/              # API endpoints ve Flask uygulaması
├── core/             # Temel rota motoru ve algoritmalar
├── nlp/              # Doğal dil işleme modülleri
├── services/         # Dış servisler ve API entegrasyonları
├── data/             # Veri yönetimi ve depolama
├── transit/          # Toplu taşıma ve GTFS modülleri
├── utils/            # Yardımcı fonksiyonlar
├── config/           # Konfigürasyon dosyaları
├── tests/            # Test dosyaları
├── benchmarks/       # Performans testleri
├── docs/             # Dokümantasyon
├── models/           # Veri modelleri
├── legacy/           # Eski/deprecated kodlar
└── cache/            # Cache dosyaları
```

## 📂 Klasör Açıklamaları

### `api/`
Flask uygulaması ve API endpoint'leri
- `app.py` - Ana Flask uygulaması

### `core/`
Temel rota planlama motoru ve algoritmalar
- `route_engine.py` - Rota motoru arayüzü
- `route_engine_impl.py` - Rota motoru implementasyonu
- `multimodal_engine.py` - Çoklu ulaşım modu motoru
- `graph_manager.py` - Graf yönetimi

### `nlp/`
Doğal dil işleme ve anlama modülleri
- `nlp_engine.py` - Ana NLP motoru
- `bert_engine.py` - BERT tabanlı NLP
- `bert_nlp_engine.py` - BERT NLP implementasyonu
- `nlp_concept_resolver.py` - Kavram çözümleyici
- `tag_grounder.py` - Etiket grounding
- `nlp_audit.py` - NLP denetim araçları

### `services/`
Dış servis entegrasyonları
- `gemini_service.py` - Google Gemini API
- `openrouter_service.py` - OpenRouter API
- `local_llm_service.py` - Yerel LLM servisi
- `weather_service.py` - Hava durumu servisi
- `rag_service.py` - RAG (Retrieval Augmented Generation)
- `ibb_transit.py` - İBB toplu taşıma API
- `llm_health.py` - LLM sağlık kontrolü

### `data/`
Veri yönetimi ve depolama
- `storage_db.py` - Ana veritabanı yönetimi
- `geocoder.py` - Coğrafi kodlama
- `districts_db.py` - İlçe veritabanı
- `chat_storage.py` - Sohbet geçmişi
- `route_storage.py` - Rota kayıtları
- `location_storage.py` - Konum kayıtları
- `local_places.py` - Yerel mekan verileri

### `transit/`
Toplu taşıma ile ilgili modüller
- `gtfs_shapes.py` - GTFS şekil verileri
- `check_gtfs.py` - GTFS doğrulama
- `time_planner.py` - Zaman planlama

### `utils/`
Yardımcı fonksiyonlar ve araçlar
- `cache_manager.py` - Cache yönetimi
- `spatial_index.py` - Mekansal indeksleme
- `text_utils.py` - Metin işleme yardımcıları
- `weather_utils.py` - Hava durumu yardımcıları
- `response_utils.py` - Yanıt formatlama
- `logging_config.py` - Loglama konfigürasyonu
- `route_config.py` - Rota konfigürasyonu

### `config/`
Konfigürasyon dosyaları ve sabitler
- `gemini_env.py` - Gemini ortam değişkenleri
- `osm_poi_dictionary.py` - OSM POI sözlüğü
- `turkey_places.py` - Türkiye mekan verileri

### `tests/`
Test dosyaları
- `test_*.py` - Birim ve entegrasyon testleri

### `benchmarks/`
Performans testleri ve benchmark'lar
- `benchmark_route_quality.py` - Rota kalitesi benchmark'ı
- `benchmark_results.json` - Benchmark sonuçları

### `docs/`
Teknik dokümantasyon
- Algoritma değerlendirmeleri
- Bilinen sorunlar
- Geliştirme yol haritası

## 🔄 Import Yolları

Yeni yapıda import'lar şu şekilde yapılmalıdır:

```python
# API
from backend.api.app import app

# Core
from backend.core.route_engine import RouteEngine
from backend.core.multimodal_engine import MultimodalEngine

# NLP
from backend.nlp.nlp_engine import NLPEngine
from backend.nlp.bert_engine import BertEngine

# Services
from backend.services.gemini_service import GeminiService
from backend.services.weather_service import WeatherService

# Data
from backend.data.storage_db import StorageDB
from backend.data.geocoder import Geocoder

# Transit
from backend.transit.gtfs_shapes import GTFSShapes

# Utils
from backend.utils.cache_manager import CacheManager
from backend.utils.text_utils import normalize_text

# Config
from backend.config.osm_poi_dictionary import POI_DICTIONARY
```

## 📝 Notlar

- Her klasörde `__init__.py` dosyası bulunur
- Eski dosyalar `legacy/` klasöründe saklanır
- Cache dosyaları `cache/` klasöründe tutulur
- Test dosyaları `tests/` klasöründe organize edilmiştir

## 🚀 Geliştirme

Yeni modül eklerken uygun klasöre yerleştirin:
- API endpoint'i → `api/`
- Algoritma/motor → `core/`
- NLP özelliği → `nlp/`
- Dış servis → `services/`
- Veri yönetimi → `data/`
- Yardımcı fonksiyon → `utils/`
