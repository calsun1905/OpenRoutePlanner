# OpenTrip — Akıllı Rota Optimizasyonu

Kullanıcının harita üzerinde seçtiği noktaları **Gezgin Satıcı Problemi (TSP)** ve **Dijkstra** algoritmaları ile optimize ederek en kısa rotayı oluşturan bir web uygulaması.

## Teknolojiler

| Katman | Teknoloji |
|--------|-----------|
| **Backend** | Python, Flask, OSMnx, NetworkX |
| **Frontend** | HTML, CSS, JavaScript, Leaflet.js |
| **Harita Verisi** | OpenStreetMap (Açık Kaynak) |
| **Algoritmalar** | Dijkstra, TSP (Nearest Neighbor / Approximation) |

## Kurulum

### 1. Sanal Ortam Oluştur
```bash
cd "Graduation Project"
python -m venv venv
venv\Scripts\activate      # Windows
```

### 2. Bağımlılıkları Yükle
```bash
cd backend
pip install -r requirements.txt
```

### 3. Backend'i Çalıştır
```bash
python app.py
```
Sunucu `http://localhost:5000` adresinde çalışacak.

### 4. Frontend'i Aç
`frontend/index.html` dosyasını tarayıcıda aç.

## Kullanım

1. Haritaya tıklayarak nokta ekle (en az 2 nokta)
2. "Rotayı Hesapla" butonuna bas
3. Optimize edilmiş rota haritada çizilir
4. Rota detayları (mesafe, süre) sol panelde gösterilir
5. "Google Maps'te Aç" ile rotayı Google Maps'te görüntüle

## API Endpoint'leri

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/api/get-route` | POST | Rota optimizasyonu |
| `/api/search-pois` | POST | Mekan arama (POI) |
| `/api/health` | GET | Sağlık kontrolü |

## Mimari

```
Kullanıcı (Tarayıcı / Leaflet.js)
      │
      ├── Tıkla → Koordinat Seç
      └── "Rota Oluştur" → HTTP POST
              │
      Flask API (Python)
              │
              ├── OSMnx → Harita Verisi (Cache)
              └── NetworkX → TSP + Dijkstra
              │
      JSON Response → Haritada Polyline
```
