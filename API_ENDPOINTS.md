# 🚀 OpenRoutePlanner API Endpoint'leri

## 📋 Tüm Endpoint'ler ve Kullanılabilir Alanlar

---

## 🗺️ ROTA API'LERİ

### 1. POST `/api/get-route`
**Açıklama:** Koordinat listesi alır, optimize edilmiş rota döner.

**Request Body:**
```json
{
    "points": [[lat, lon], [lat, lon], ...],
    "place": "Kadikoy, Istanbul, Turkey",  // opsiyonel
    "optimize": true/false,                 // opsiyonel, varsayılan: false
    "route_type": "shortest"                // opsiyonel: "shortest", "fastest", "balanced"
}
```

**Response:**
```json
{
    "optimized_order": [0, 2, 1, ...],
    "route_coords": [[lat, lon], ...],
    "total_distance_km": 4.5,
    "estimated_walk_minutes": 55,
    "google_maps_link": "https://...",
    "route_type": "shortest"
}
```

---

### 2. POST `/api/get-alternative-routes`
**Açıklama:** Aynı noktalar için 3 farklı alternatif rota döner.

**Request Body:**
```json
{
    "points": [[lat, lon], [lat, lon], ...],
    "optimize": true/false
}
```

**Response:**
```json
{
    "alternatives": [
        {
            "type": "shortest",
            "name": "En Kısa Rota",
            "icon": "📏",
            "route_coords": [[lat, lon], ...],
            "distance_km": 4.5,
            "duration_minutes": 55,
            "description": "Minimum mesafe",
            "google_maps_link": "https://..."
        },
        {
            "type": "fastest",
            "name": "En Hızlı Rota",
            "icon": "⚡",
            ...
        },
        {
            "type": "balanced",
            "name": "Dengeli Rota",
            "icon": "⚖️",
            ...
        }
    ]
}
```

---

## 📍 POI (İlgi Noktası) API'LERİ

### 3. POST `/api/search-pois`
**Açıklama:** Belirtilen bölgede POI arar.

**Request Body:**
```json
{
    "place": "Kadikoy, Istanbul, Turkey",
    "category": "museum"
}
```

**Geçerli Kategoriler:**
- `museum` - Müze
- `cafe` - Kafe
- `park` - Park
- `restaurant` - Restoran
- `library` - Kütüphane
- `mosque` - Cami
- `hotel` - Otel
- `hospital` - Hastane
- `supermarket` - Market
- `cinema` - Sinema
- `bank` - Banka
- `fuel` - Benzinlik

**Response:**
```json
{
    "pois": [
        {
            "name": "...",
            "lat": 40.99,
            "lon": 29.03,
            "category": "museum"
        }
    ]
}
```

---

## 🌍 GEOCODING API'LERİ

### 4. POST `/api/geocode`
**Açıklama:** Yer ismini koordinata çevirir.

**Request Body:**
```json
{
    "place": "Kadıköy Parkı, İstanbul"
}
```

**Response:**
```json
{
    "status": "success",
    "lat": 40.990,
    "lon": 29.029,
    "display_name": "Kadıköy Parkı, İstanbul, Türkiye",
    "cached": false
}
```

---

### 5. POST `/api/reverse-geocode`
**Açıklama:** Koordinatı yer ismine çevirir.

**Request Body:**
```json
{
    "lat": 40.990,
    "lon": 29.029
}
```

**Response:**
```json
{
    "status": "success",
    "display_name": "Kadıköy, İstanbul, Türkiye",
    "address": {...},
    "cached": false
}
```

---

### 6. POST `/api/geocode/batch`
**Açıklama:** Toplu geocoding işlemi (max 10 yer).

**Request Body:**
```json
{
    "places": ["Kadıköy", "Beşiktaş", "Taksim"]
}
```

**Response:**
```json
{
    "results": [
        {"status": "success", "lat": 40.99, "lon": 29.03, ...},
        {"status": "success", "lat": 41.04, "lon": 29.00, ...}
    ]
}
```

---

## 💾 ROTA KAYDETME API'LERİ

### 7. POST `/api/routes/save`
**Açıklama:** Rotayı kaydeder.

**Request Body:**
```json
{
    "name": "Kadıköy Turu",
    "description": "Kadıköy'de gezilecek yerler",
    "points": [[lat, lon], ...],
    "route_coords": [[lat, lon], ...],
    "distance_km": 4.5,
    "duration_minutes": 55,
    "route_type": "shortest",
    "tags": ["tarihi", "kültürel"]
}
```

**Response:**
```json
{
    "status": "success",
    "route": {...},
    "message": "Rota kaydedildi"
}
```

---

### 8. GET `/api/routes`
**Açıklama:** Tüm kaydedilmiş rotaları getirir.

**Query Parameters:**
- `sort_by` - Sıralama: `created_at`, `name`, `distance_km`, `times_used`, `favorite`
- `limit` - Maksimum rota sayısı

**Response:**
```json
{
    "routes": [...],
    "count": 5
}
```

---

### 9. GET `/api/routes/<route_id>`
**Açıklama:** Belirli bir rotayı getirir.

**Response:**
```json
{
    "route": {...}
}
```

---

### 10. PUT `/api/routes/<route_id>`
**Açıklama:** Rotayı günceller.

**Request Body:**
```json
{
    "name": "Yeni İsim",
    "description": "Yeni açıklama",
    "tags": ["yeni", "etiketler"]
}
```

---

### 11. DELETE `/api/routes/<route_id>`
**Açıklama:** Rotayı siler.

---

### 12. POST `/api/routes/<route_id>/favorite`
**Açıklama:** Rotayı favorilere ekler/çıkarır.

---

### 13. GET `/api/routes/search`
**Açıklama:** Rota arama.

**Query Parameters:**
- `q` - Arama sorgusu

---

### 14. GET `/api/routes/statistics`
**Açıklama:** Rota istatistikleri.

**Response:**
```json
{
    "total_routes": 10,
    "total_distance_km": 45.2,
    "total_duration_minutes": 550,
    "favorite_count": 3,
    "most_used_route": {...}
}
```

---

## ⏰ ZAMAN PLANLAMA API'LERİ

### 15. POST `/api/timeline/create`
**Açıklama:** Rota için zaman çizelgesi oluşturur.

**Request Body:**
```json
{
    "points": [
        {"name": "Kadıköy", "lat": 40.99, "lon": 29.03},
        {"name": "Moda", "lat": 40.98, "lon": 29.04}
    ],
    "segment_distances": [1.2, 0.8],
    "start_time": "09:00",
    "visit_duration": 30,
    "transport_mode": "walking",
    "custom_durations": {0: 45, 1: 60}
}
```

**Transport Modes:**
- `walking` - Yürüyüş (5 km/h)
- `cycling` - Bisiklet (15 km/h)
- `driving` - Araba (30 km/h)

**Response:**
```json
{
    "start_time": "09:00",
    "end_time": "14:30",
    "total_duration_minutes": 330,
    "schedule": [
        {
            "point_index": 0,
            "name": "Kadıköy",
            "arrival_time": "09:00",
            "departure_time": "09:45",
            "visit_duration_minutes": 45,
            "travel_to_next_minutes": 15
        }
    ]
}
```

---

### 16. POST `/api/timeline/check-conflicts`
**Açıklama:** Zaman çizelgesinde çakışmaları kontrol eder.

**Request Body:**
```json
{
    "schedule": [...],
    "opening_hours": {
        0: {"open": "09:00", "close": "18:00"},
        1: {"open": "10:00", "close": "20:00"}
    }
}
```

---

### 17. POST `/api/timeline/optimize`
**Açıklama:** Zaman çizelgesini optimize eder.

**Request Body:**
```json
{
    "schedule": [...],
    "max_duration_minutes": 360,
    "preferred_end_time": "18:00"
}
```

---

## 📌 LOKASYON API'LERİ

### 18. GET `/api/locations`
**Açıklama:** Kaydedilmiş tüm lokasyonları getirir.

**Query Parameters:**
- `sort_by` - Sıralama
- `limit` - Maksimum sayı

---

### 19. POST `/api/locations`
**Açıklama:** Yeni lokasyon kaydeder.

**Request Body:**
```json
{
    "name": "Favori Yerim",
    "lat": 40.99,
    "lon": 29.03,
    "icon_type": "star",
    "address": "Kadıköy, İstanbul"
}
```

**Icon Types:**
- `star` - ⭐
- `home` - 🏠
- `work` - 💼
- `food` - 🍽️
- `coffee` - ☕
- `shopping` - 🛍️

---

### 20. PUT `/api/locations/<location_id>`
**Açıklama:** Lokasyonu günceller.

---

### 21. DELETE `/api/locations/<location_id>`
**Açıklama:** Lokasyonu siler.

---

## 🏥 SAĞLIK KONTROLÜ

### 22. GET `/api/health`
**Açıklama:** Sunucu sağlık kontrolü.

**Response:**
```json
{
    "status": "ok",
    "message": "OpenTrip API çalışıyor!"
}
```

---

## 📊 ÖZET

**Toplam Endpoint Sayısı:** 22

**Kategoriler:**
- 🗺️ Rota API'leri: 2
- 📍 POI API'leri: 1
- 🌍 Geocoding API'leri: 3
- 💾 Rota Kaydetme: 8
- ⏰ Zaman Planlama: 3
- 📌 Lokasyon: 4
- 🏥 Sağlık: 1

---

## 🎯 Kullanım Örnekleri

### Örnek 1: Rota Oluştur
```bash
curl -X POST http://localhost:5000/api/get-route \
  -H "Content-Type: application/json" \
  -d '{
    "points": [[40.99, 29.03], [41.01, 29.05]],
    "optimize": true,
    "route_type": "shortest"
  }'
```

### Örnek 2: POI Ara
```bash
curl -X POST http://localhost:5000/api/search-pois \
  -H "Content-Type: application/json" \
  -d '{
    "place": "Kadikoy, Istanbul",
    "category": "cafe"
  }'
```

### Örnek 3: Zaman Çizelgesi
```bash
curl -X POST http://localhost:5000/api/timeline/create \
  -H "Content-Type: application/json" \
  -d '{
    "points": [
      {"name": "Kadıköy", "lat": 40.99, "lon": 29.03}
    ],
    "start_time": "09:00",
    "visit_duration": 30
  }'
```

---

## 🔧 Yeni Endpoint Eklemek İçin

1. `app.py` dosyasını aç
2. Yeni endpoint fonksiyonu ekle:
```python
@app.route("/api/yeni-endpoint", methods=["POST"])
def api_yeni_endpoint():
    """
    Açıklama buraya
    
    Request Body:
        {...}
    
    Response:
        {...}
    """
    try:
        data = request.get_json()
        # İşlemler...
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

3. Bu dosyayı güncelle
4. Frontend'de kullan

---

## 📝 Notlar

- Tüm POST endpoint'leri JSON formatında veri bekler
- Hata durumunda HTTP status code ve error mesajı döner
- Cache mekanizması bazı endpoint'lerde aktif
- Rate limiting yok (şimdilik)
- CORS tüm origin'lere açık (development için)

---

**Son Güncelleme:** 2026-03-03
**Versiyon:** 1.0
