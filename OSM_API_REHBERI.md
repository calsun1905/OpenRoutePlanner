# 🗺️ OSM API Rehberi — Nominatim, Overpass ve Taginfo

> Bu dosya Nominatim API, Overpass API ve Taginfo sisteminin nasıl çalıştığını, hangi endpoint'lerin nerede kullanıldığını ve OSM tag sistemini basit seviyede anlatır.

---

## 📋 İçindekiler

1. [OSM Ekosistemi Özeti](#1-osm-ekosistemi-özeti)
2. [OSM Tag Sistemi (key=value)](#2-osm-tag-sistemi-keyvalue)
3. [Nominatim API](#3-nominatim-api)
4. [Overpass API](#4-overpass-api)
5. [Taginfo — Hangi Tag'ler Var?](#5-taginfo--hangi-tagler-var)
6. [Projede Nerede Kullanılıyor?](#6-projede-nerede-kullanılıyor)
7. [Karşılaştırma Tablosu](#7-karşılaştırma-tablosu)

---

## 1. OSM Ekosistemi Özeti

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OPENSTREETMAP (OSM) VERİTABANI                    │
│         Dünyanın tüm harita verisi (yollar, binalar, mekanlar)       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│  NOMINATIM    │         │  OVERPASS     │         │  TAGINFO      │
│  "İsim ver,   │         │  "Koordinat + │         │  "Hangi tag'ler│
│   koordinat   │         │   tag ver,     │         │   var? Kaç tane│
│   bulayım"    │         │   mekan listesi│         │   kullanılmış?"│
│               │         │   vereyim"     │         │               │
└───────────────┘         └───────────────┘         └───────────────┘
   Geocoding                 POI Arama                 Tag Keşfi
```

**Kısa özet:**
- **OSM** = Veri deposu (milyonlarca yer, yol, mekan)
- **Nominatim** = İsim → koordinat (ve tersi) araması
- **Overpass** = Koordinat + tag ile mekan listesi sorgulama
- **Taginfo** = Hangi tag'lerin var olduğunu, kaç kez kullanıldığını gösterir

---

## 2. OSM Tag Sistemi (key=value)

OSM'de her mekan **tag** (etiket) ile tanımlanır. Tag = `key=value` çifti.

### Örnekler

| Mekan Türü | OSM Tag | Açıklama |
|------------|---------|----------|
| Kafe | `amenity=cafe` | amenity anahtarı, cafe değeri |
| Müze | `tourism=museum` | tourism anahtarı, museum değeri |
| Park | `leisure=park` | leisure anahtarı, park değeri |
| Market | `shop=supermarket` | shop anahtarı, supermarket değeri |
| Cami | `amenity=place_of_worship` + `religion=muslim` | İki tag birlikte |

### Ana Tag Anahtarları (Key)

| Key | Ne İçin Kullanılır? | Örnek Değerler |
|-----|---------------------|----------------|
| `amenity` | Hizmetler (kafe, hastane, banka) | cafe, restaurant, hospital, pharmacy |
| `shop` | Alışveriş yerleri | supermarket, bakery, clothes |
| `tourism` | Turistik yerler | museum, hotel, viewpoint |
| `leisure` | Boş zaman mekanları | park, stadium, playground |
| `historic` | Tarihi yerler | monument, castle, ruins |

**Neden önemli?** Overpass API'ye sorgu yazarken bu tag'leri kullanırsın. "Kadıköy'deki kafeler" = `amenity=cafe` + Kadıköy koordinatları.

---

## 3. Nominatim API

### Ne İşe Yarar?

**Geocoding:** Yer ismi → koordinat  
**Reverse Geocoding:** Koordinat → yer ismi

### Base URL
```
https://nominatim.openstreetmap.org
```

### Endpoint'ler

| Endpoint | Method | Ne Yapar? |
|----------|--------|-----------|
| `/search` | GET | İsim ver → koordinat bul (Geocoding) |
| `/reverse` | GET | Koordinat ver → isim bul (Reverse Geocoding) |

### Örnek 1: Geocoding (İsim → Koordinat)

**İstek:**
```
GET https://nominatim.openstreetmap.org/search?q=Kadıköy+Parkı&format=json&limit=1
```

**Parametreler:**
- `q` = Arama metni (yer ismi)
- `format` = json (veya xml)
- `limit` = Kaç sonuç dönsün (1-10 arası)

**Yanıt:**
```json
[
  {
    "place_id": 123456,
    "lat": "40.9850",
    "lon": "29.0250",
    "display_name": "Kadıköy Parkı, Caferağa, Kadıköy, İstanbul, Türkiye",
    "type": "leisure"
  }
]
```

### Örnek 2: Reverse Geocoding (Koordinat → İsim)

**İstek:**
```
GET https://nominatim.openstreetmap.org/reverse?lat=40.985&lon=29.025&format=json
```

**Yanıt:**
```json
{
  "place_id": 123456,
  "display_name": "Kadıköy Parkı, Caferağa, Kadıköy, İstanbul...",
  "address": {
    "road": "...",
    "suburb": "Caferağa",
    "city": "İstanbul",
    "country": "Türkiye"
  }
}
```

### ⚠️ Önemli Kurallar

1. **User-Agent header ZORUNLU** — Yoksa IP ban riski
2. **Rate limit: 1 istek/saniye** — Daha hızlı istek atarsan ban olursun
3. **Ücretsiz** — Ticari kullanım için Usage Policy kontrol et

### Python Örneği

```python
import requests

def geocode(place_name):
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "OpenRoutePlanner/1.0"}
    params = {"q": place_name, "format": "json", "limit": 1}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    if data:
        return {"lat": float(data[0]["lat"]), "lon": float(data[0]["lon"])}
    return None
```

---

## 4. Overpass API

### Ne İşe Yarar?

Koordinat + tag vererek **belirli bir alandaki mekanları** (POI) listeler. Örn: "Kadıköy'deki tüm kafeler", "Beşiktaş'taki müzeler".

### Base URL
```
https://overpass-api.de/api/interpreter
```
(Alternatif: `https://overpass.kumi.systems/api/interpreter`)

### Nasıl Çalışır?

1. **Overpass QL** adında bir sorgu dili kullanırsın
2. Sorguyu POST ile gönderirsin
3. JSON veya başka formatta sonuç alırsın

### Overpass QL Temel Sözdizimi

```
[out:json];                    // Çıktı formatı
node["amenity"="cafe"](around:1000, 40.99, 29.03);  // 1km yarıçap, kafeler
out body;                       // Sonuçları döndür
```

### Örnek Sorgu: Kadıköy'deki Kafeler

```
[out:json][timeout:60];
(
  node["amenity"="cafe"](around:3000, 40.9903, 29.0291);
  way["amenity"="cafe"](around:3000, 40.9903, 29.0291);
);
out body;
```

- `around:3000` = 3000 metre (3 km) yarıçap
- `40.9903, 29.0291` = Kadıköy merkez koordinatları
- `node` ve `way` = OSM'de hem nokta hem alan olarak kafeler olabilir

### Python Örneği

```python
import requests

def get_cafes_near(lat, lon, radius_m=2000):
    query = f"""
    [out:json][timeout:60];
    (
      node["amenity"="cafe"](around:{radius_m},{lat},{lon});
      way["amenity"="cafe"](around:{radius_m},{lat},{lon});
    );
    out body;
    """
    url = "https://overpass-api.de/api/interpreter"
    response = requests.post(url, data={"data": query})
    return response.json()
```

### Örnek Yanıt Yapısı

```json
{
  "elements": [
    {
      "type": "node",
      "id": 123456,
      "lat": 40.99,
      "lon": 29.03,
      "tags": {
        "name": "Kahve Dünyası",
        "amenity": "cafe"
      }
    }
  ]
}
```

### ⚠️ Önemli Kurallar

1. **Rate limit** — Saniyede 1-2 istek yeterli
2. **Timeout** — Uzun sorgularda `[timeout:60]` ekle
3. **Büyük alan** — Çok geniş alan sorgulama, sunucu yüklenir

---

## 5. Taginfo — Hangi Tag'ler Var?

### Ne İşe Yarar?

**Taginfo** = OSM tag'lerinin istatistikleri ve keşfedilmesi için araç.  
"Kafe için hangi tag kullanılır?", "Dünyada kaç tane müze var?" gibi sorulara cevap verir.

### URL
```
https://taginfo.openstreetmap.org/
```

### Taginfo API Kullanımı

**Belirli bir key'in tüm değerlerini gör:**
```
GET https://taginfo.openstreetmap.org/api/4/key/values?key=amenity&page=1&rp=50&sortname=count&sortorder=desc
```

**Örnek yanıt:** `amenity` key'i için en çok kullanılan değerler (cafe, restaurant, hospital, pharmacy...)

### Nasıl Kullanılır?

1. **Tag keşfi:** "Kafe" için hangi tag? → `amenity=cafe`
2. **İstatistik:** `amenity=cafe` dünyada kaç tane? → 1.2 milyon
3. **Alternatif tag'ler:** "Restoran" için `amenity=restaurant` veya `amenity=fast_food` olabilir

### Overpass Turbo ile Test

Overpass sorgularını **tarayıcıda test** etmek için:
- **Overpass Turbo:** https://overpass-turbo.eu/
- Sol panele sorgu yaz, "Run" butonuna bas
- Haritada sonuçları gör

---

## 6. Projede Nerede Kullanılıyor?

### Nominatim

| Dosya | Kullanım |
|-------|----------|
| `backend/geocoder.py` | `geocode()`, `reverse_geocode()`, `geocode_batch()` — Tüm geocoding işlemleri |
| `backend/app.py` | `/api/geocode`, `/api/reverse-geocode`, `/api/geocode/batch` endpoint'leri |

**Akış:** Frontend "Kadıköy Parkı" yazar → `geocoder.geocode()` → Nominatim API'ye istek → Koordinat döner.

### Overpass

| Dosya | Kullanım |
|-------|----------|
| `backend/graph_manager.py` | `search_pois()` — **OSMnx** kullanıyor (`ox.features_from_place`), **doğrudan Overpass değil** |
| `backend/test_osm_poi.py` | Overpass API ile test sorguları |

**Not:** Projede POI araması şu an **OSMnx** ile yapılıyor. OSMnx kendi içinde OSM verisini indirir. Overpass API kullanmak istersen `test_osm_poi.py` veya benzeri bir modül üzerinden eklenebilir.

### Tag Sistemi

| Dosya | Kullanım |
|-------|----------|
| `backend/graph_manager.py` | `tag_map` sözlüğü — category → OSM tag (örn: museum → tourism=museum) |
| `backend/osm_poi_dictionary.py` | Türkçe kelime → OSM tag (örn: "kafe" → amenity=cafe) |

### Taginfo

Projede **doğrudan Taginfo API kullanılmıyor**. Ancak `osm_poi_dictionary.py` ve `graph_manager.py` içindeki tag'ler **Taginfo veya OSM Wiki** üzerinden araştırılarak oluşturulmuş.

---

## 7. Karşılaştırma Tablosu

| Özellik | Nominatim | Overpass | Taginfo |
|---------|-----------|----------|---------|
| **İşlev** | İsim ↔ Koordinat | Tag + alan → mekan listesi | Tag istatistikleri |
| **Girdi** | Yer ismi veya koordinat | Koordinat + tag sorgusu | Key (örn: amenity) |
| **Çıktı** | Koordinat veya adres | Mekan listesi (JSON) | Tag değerleri + sayıları |
| **Projede kullanım** | geocoder.py, /api/geocode | OSMnx (dolaylı), test_osm_poi | Dolaylı (tag referansı) |
| **Rate limit** | 1 req/s | Makul kullan | Makul kullan |

---

## Özet Akış Örneği

```
Kullanıcı: "Kadıköy'deki kafeleri göster"

1. Kadıköy koordinatları lazım
   → Nominatim: "Kadıköy" → [40.99, 29.03]

2. Bu koordinat civarındaki kafeler lazım
   → Overpass: node["amenity"="cafe"](around:3000, 40.99, 29.03)
   → Veya OSMnx: ox.features_from_place("Kadıköy", tags={"amenity": "cafe"})

3. "Kafe" için doğru tag'ı nereden buldum?
   → Taginfo veya OSM Wiki: amenity=cafe
```

---

**Son Güncelleme:** 04.03.2026
