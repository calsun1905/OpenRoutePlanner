# OpenStreetMap Ekosistemi - Nasıl Çalışır?

> Bu dosya projede kullanılan harita kavramlarını anlamak için hazırlandı.

---

## 🗺️ Genel Bakış

```
┌─────────────────────────────────────────────────────────────────┐
│                    OPENSTREETMAP (OSM)                         │
│              "Google Maps'ın ücretsiz versiyonu"               │
│                                                              │
│  - Tüm dünyanın harita verisi                                   │
│  - Herkes tarafından düzenlenebilir (Vikipedi gibi)            │
│  - Ücretsiz ve açık kaynak                                     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        │                                       │
        ↓                                       ↓
┌──────────────────┐                  ┌──────────────────┐
│   OSM Verisi     │                  │   OSM Verisi     │
│  (Yollar, Binalar,│                  │  (Yer İsimleri)  │
│   Parklar...)    │                  │                  │
└──────────────────┘                  └──────────────────┘
        ↓                                       ↓
   KULLANIM 1                            KULLANIM 2
        ↓                                       ↓
┌──────────────────┐                  ┌──────────────────┐
│     OSMnx        │                  │    Nominatim     │
│  (Python)        │                  │   (API)          │
│  Rota hesaplama  │                  │  Geocoding       │
└──────────────────┘                  └──────────────────┘
        ↓                                       ↓
   Backend                                Backend/Frontend
        ↓
┌──────────────────┐                  ┌──────────────────┐
│   Leaflet.js     │                  │  Koordinatlar    │
│  (JavaScript)    │                  │  [lat, lon]      │
│  Harita gösterme │                  │                  │
└──────────────────┘                  └──────────────────┘
        ↓
   Frontend
```

---

## 1. OpenStreetMap (OSM) - Veri Kaynağı

**OSM nedir?**
- Dünyanın en büyük ücretsiz harita veritabanı
- Google Maps gibi ama tamamen ücretsiz ve açık kaynak
- Milyonlarca gönüllü tarafından düzenleniyor

**OSM verisi ne içerir?**
```xml
<osm>
  <!-- Yollar -->
  <way id="123">
    <nd ref="456"/>  <!-- Node referansı -->
    <nd ref="789"/>
    <tag k="highway" v="primary"/>  <!-- Bu bir ana yol -->
    <tag k="name" v="Bağdat Caddesi"/>
  </way>

  <!-- Noktalar (POI) -->
  <node id="999" lat="40.990" lon="29.029">
    <tag k="name" v="Kadıköy Parkı"/>
    <tag k="leisure" v="park"/>
  </node>
</osm>
```

---

## 2. OSMnx - Python Kütüphanesi

**Ne işe yarar?**
- OSM verisini indirir
- Yol grafiği oluşturur (nodes + edges)
- Rota hesaplaması yapar

**Veri Akışı:**
```
OSMnx İndirir ──────→ OSM Verisi ──────→ Graph (Yol Grafiği)
                        ↓                        ↓
                    raw data           NetworkX Graph objesi
                                        (Düğümler + Kenarlar)
```

**Örnek:**
```python
import osmnx as ox

# 1. OSM'den Kadıköy'ün yürüyüş ağını indir
G = ox.graph_from_place("Kadıköy, İstanbul", network_type="walk")

# 2. Grafiği kaydet (cache)
ox.save_graphml(G, "kadikoy.graphml")

# 3. İki nokta arasında rota hesapla
origin = (40.990, 29.029)  # Kadıköy
destination = (40.985, 29.025)  # Kadıköy Parkı

route = ox.shortest_path(G, origin, destination)

# Çıktı: [(node1, node2), (node2, node3), ...]
```

**OSMnx Veri Yapısı:**
```python
# Graph = Nodes + Edges
G.nodes = {
    123456: {'lat': 40.990, 'lon': 29.029, 'y': 40.990, 'x': 29.029},
    123457: {'lat': 40.991, 'lon': 29.030, ...},
    ...
}

G.edges = {
    (123456, 123457): {
        'length': 15.5,  # metre
        'highway': 'primary',
        'name': 'Bağdat Caddesi'
    },
    ...
}
```

---

## 3. Nominatim - Geocoding API

**Ne işe yarar?**
- Yer ismini koordinata çevirir (Geocoding)
- Koordinatı yer ismine çevirir (Reverse Geocoding)
- OSM verisini arar

**Geocoding (İsim → Koordinat):**
```bash
# API isteği
https://nominatim.openstreetmap.org/search?q=Kadıköy+Parkı&format=json

# Yanıt
[
  {
    "place_id": 123456,
    "lat": "40.9850",
    "lon": "29.0250",
    "display_name": "Kadıköy Parkı, Caferağa, Kadıköy, İstanbul, Marmara Bölgesi, 34710, Türkiye",
    "type": "leisure"
  }
]
```

**Reverse Geocoding (Koordinat → İsim):**
```bash
# API isteği
https://nominatim.openstreetmap.org/reverse?lat=40.985&lon=29.025&format=json

# Yanıt
{
  "place_id": 123456,
  "display_name": "Kadıköy Parkı, Caferağa, Kadıköy, İstanbul..."
}
```

**Python Kullanımı:**
```python
import requests

def geocode(place_name):
    """Yer ismini koordinata çevirir"""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": place_name,
        "format": "json",
        "limit": 1
    }
    response = requests.get(url, params=params)
    data = response.json()

    if data:
        return {
            "lat": float(data[0]["lat"]),
            "lon": float(data[0]["lon"]),
            "name": data[0]["display_name"]
        }
    return None

# Kullanım
result = geocode("Kadıköy Parkı, İstanbul")
print(result)
# {'lat': 40.9850, 'lon': 29.0250, 'name': 'Kadıköy Parkı, Caferağa...'}
```

---

## 4. Leaflet.js - JavaScript Kütüphanesi

**Ne işe yarar?**
- Web tarayıcısında harita gösterir
- Kullanıcı etkileşimi sağlar (tıklama, zoom)
- Rota çizer, marker koyar

**Temel Kullanım:**
```html
<!-- HTML -->
<div id="map" style="height: 500px;"></div>

<!-- JavaScript -->
<script>
// 1. Haritayı başlat
var map = L.map('map').setView([40.990, 29.029], 13);

// 2. Tile layer ekle (harita görselleri)
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

// 3. Marker ekle
L.marker([40.985, 29.025]).addTo(map)
    .bindPopup('Kadıköy Parkı');

// 4. Rota çiz
var routeCoords = [
    [40.990, 29.029],
    [40.988, 29.027],
    [40.985, 29.025]
];
L.polyline(routeCoords, {color: 'blue'}).addTo(map);
</script>
```

---

## 🔗 Hepsi Bir Arada - Proje Akışı

```
┌─────────────────────────────────────────────────────────────────┐
│                        KULLANICI                                │
│  "Kadıköy'den Kadıköy Parkı'na rota yap"                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Leaflet.js)                       │
│  - Chat input'tan sorguyu al                                    │
│  - Backend'a gönder                                             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                    API Request (/api/natural-query)
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (Flask)                            │
│                                                                  │
│  1️⃣ NLP Engine: Sorguyu analiz et                              │
│     "Kadıköy" + "Kadıköy Parkı" tespit et                       │
│                      ↓                                          │
│  2️⃣ Nominatim API: Yer isimlerini koordinata çevir             │
│     "Kadıköy"        → [40.990, 29.029]                         │
│     "Kadıköy Parkı"  → [40.985, 29.025]                         │
│                      ↓                                          │
│  3️⃣ OSMnx: Rota hesapla                                        │
│     Graph yükle → En kısa yolu bul                              │
│                      ↓                                          │
│  4️⃣ Response: Rota koordinatlarını Frontend'e gönder           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                    API Response (JSON)
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Leaflet.js)                       │
│  - Rota çiz (polyline)                                           │
│  - Markerları göster                                             │
│  - Mesafe/süre göster                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Karşılaştırma Tablosu

| Özellik | OSMnx | Nominatim | Leaflet.js |
|---------|-------|-----------|------------|
| **Dil** | Python | HTTP API | JavaScript |
| **Nerede çalışır?** | Backend | Backend/Frontend | Frontend |
| **Ne yapar?** | Rota hesaplar | İsim → Koordinat | Harita gösterir |
| **Veri kaynağı** | OSM | OSM | OSM (tile server) |
| **API ücreti** | Ücretsiz | Ücretsiz | Ücretsiz |
| **Kullanım limiti** | Yok | 1 req/sec (ücretsiz) | Yok |
| **Projenizde** | ✅ Var | ❌ Yeni ekleyeceğiz | ✅ Var |

---

## 🎓 Özet

```
OpenStreetMap (OSM) = Büyük veritabanı
         ↓
    ┌────┴────┐
    ↓         ↓
  OSMnx    Nominatim
  (Rota)   (Arama)
    ↓         ↓
  Leaflet.js
  (Görüntüleme)
```

1. **OSM**: Ham harita verisi (yollar, binalar, parklar...)
2. **OSMnx**: Python ile rota hesaplama kütüphanesi
3. **Nominatim**: Yer ismi arama motoru (Google Maps arama çubuğu gibi)
4. **Leaflet.js**: Tarayıcıda harita gösterme kütüphanesi

**Hepsi OSM verisini kullanıyor!** Üçü de aynı ekosistemin parçaları.

---

## 🔗 Faydalı Linkler

- **OpenStreetMap**: https://www.openstreetmap.org/
- **Nominatim Demo**: https://nominatim.openstreetmap.org/ui/search.html
- **OSMnx Dokümantasyon**: https://osmnx.readthedocs.io/
- **Leaflet.js**: https://leafletjs.com/

---

## ❓ Sorular

1. **OSMnx ve Nominatim aynı veriyi mi kullanır?**
   - Evet, ikisi de OpenStreetMap veritabanını kullanır. Bu yüzden koordinatlar tutarlıdır.

2. **Neden ikisi de var?**
   - OSMnx: Rota hesaplama için (yol grafiği lazım)
   - Nominatim: Yer ismi arama için (isim → koordinat dönüşümü)

3. **Leaflet.js neden OSM kullanıyor?**
   - Leaflet sadece bir "görüntüleme" kütüphanesi. Harita verisi (tile images) OpenStreetMap sunucularından gelir.

4. **API ücreti nedir?**
   - Hepsi ücretsiz! Nominatim için sadece kullanım limiti var (ücretsiz kullanımda 1 isteka/saniye).

5. **Projemizde neler var?**
   - ✅ OSMnx (rota hesaplama için)
   - ✅ Leaflet.js (harita gösterme için)
   - ❌ Nominatim (yeni ekleyeceğiz - doğal dil sorgu için)
