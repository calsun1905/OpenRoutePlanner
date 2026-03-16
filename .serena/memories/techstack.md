# OpenRoutePlanner - Tech Stack

## 🔧 Backend (Python)

### Ana Framework
- **Flask 3.1.0** - Web framework
- **Flask-CORS 5.0.1** - CORS desteği

### Harita ve Graf
- **OSMnx 2.0.1** - OpenStreetMap graf indirme ve analiz
- **NetworkX 3.4.2** - Graf algoritmaları (Dijkstra, TSP)

### Veri İşleme
- **pandas 2.2.3** - Veri manipülasyonu
- **scikit-learn 1.6.1** - Machine learning utilities
- **NumPy** (implicit) - Sayısal işlemler

### AI/NLP
- **transformers 4.48.0** - BERT model
- **torch 2.5.1** - PyTorch (⚠️ Python 3.13 ile uyumsuz)
- **sentence-transformers 3.3.1** - Cümle embedding'leri

### API İstemcileri
- **requests 2.32.3** - HTTP istemcisi

### Harici API'ler
- **Nominatim** - Geocoding (yer ismi → koordinat)
- **Overpass API** - POI arama
- **OpenStreetMap** - Harita verileri

## 🌐 Frontend

### Temel Teknolojiler
- **HTML5** - Yapı
- **CSS3** - Stil
- **Vanilla JavaScript** - Mantık (framework yok)

### Harita Kütüphanesi
- **Leaflet.js** - İnteraktif harita
- **CartoDB / OSM** - Tile layer (harita görselleri)

### Font
- **Inter (Google Fonts)** - UI fontu

## 💾 Veri Saklama

### Cache
- **OSM GraphML** - `backend/data/*.graphml` (OSM grafları)
- **JSON Cache** - `cache/*.json` (API yanıtları)
- **SQLite** - `backend/cache/districts_turkey.db` (ilçe veritabanı)

### Rota/Yer Storage
- **JSON** - Rota ve kayıtlı yerler (dosya tabanlı)

### Model
- **BERT Model** - `backend/models/bert-base-turkish-uncased/` (440 MB)

## 🗄️ Veritabanı (Türkiye Places)
- 81 il + ilçeler = 1775 yer ismi
- BERT embedding'leri ile hazır
- Typo tolerance için temel veri kaynağı

## 🔄 API Mimari

### Endpoint Kategorileri
1. **Rota ve Harita** - `/api/get-route`, `/api/get-alternative-routes`
2. **POI Arama** - `/api/search-pois`
3. **Geocoding** - `/api/geocode`, `/api/reverse-geocode`
4. **Rota Kaydetme** - `/api/routes/*`
5. **Zaman Planlama** - `/api/timeline/*`
6. **Kayıtlı Yerler** - `/api/locations/*`

### Rate Limiting
- **Nominatim:** 1 req/s
- **Overpass:** Ama kullanıma göre (geniş aralıklı sorgular)

## 🚀 Çalışma Ortamı

### Python
- **Sürüm:** Python 3.13 (⚠️ torch 2.5.1 ile uyumsuz)
- **Sanal Ortam:** `.venv/`

### Kurulum Komutları
```bash
# Sanal ortam oluştur
cd OpenRoutePlanner
python -m venv .venv
.venv\Scripts\activate  # Windows

# Bağımlılıkları yükle
cd backend
pip install -r requirements.txt

# Backend'i çalıştır
python app.py
# http://localhost:5000
```

### Geliştirme Ortamı
- **OS:** Windows 11
- **IDE:** VS Code
- **Shell:** bash (Git Bash)
- **Git:** Aktif
