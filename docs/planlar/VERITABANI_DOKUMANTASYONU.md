# OpenRoutePlanner — Veritabanı Dokümantasyonu

> Bu dosya projedeki tüm veritabanı yapılarını, eklenenleri ve gelecek fikirleri içerir.
> Yeni fikir üretmek veya referans için kullanılabilir.

**Son güncelleme:** 08.03.2026

---

## 1. VERİTABANI ÖZETİ

| Veritabanı | Konum | Amaç |
|------------|-------|------|
| **app_data.db** | `backend/data/` | Rotalar, yerler + local_places (önceden tanımlı yerler) |
| **geocodes.db** | `backend/cache/` | Yer ismi ↔ koordinat cache (Nominatim) |
| **districts_turkey.db** | `backend/cache/` | Türkiye il/ilçe listesi |

---

## 2. app_data.db — Rota ve Lokasyon Depolama

**Dosya yolu:** `backend/data/app_data.db`  
**Modül:** `storage_db.py`, `route_storage.py`, `location_storage.py`  
**Oluşma:** İlk rota veya lokasyon işleminde otomatik oluşur.

### 2.1 routes tablosu

Kullanıcının kaydettiği rotalar.

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| `id` | TEXT PRIMARY KEY | Benzersiz rota ID (8 karakter UUID) |
| `name` | TEXT NOT NULL | Rota adı |
| `description` | TEXT DEFAULT '' | Açıklama |
| `points` | TEXT NOT NULL | Seçilen noktalar — JSON: `[[lat, lon], ...]` |
| `route_coords` | TEXT NOT NULL | Hesaplanan rota çizgisi — JSON: `[[lat, lon], ...]` |
| `distance_km` | REAL NOT NULL | Toplam mesafe (km) |
| `duration_minutes` | INTEGER NOT NULL | Tahmini süre (dakika) |
| `route_type` | TEXT DEFAULT 'route_1' | `route_1` (ana), `route_2`, `route_3` (alternatif) |
| `tags` | TEXT DEFAULT '[]' | Etiketler — JSON: `["romantik", "tarihi"]` |
| `favorite` | INTEGER DEFAULT 0 | Favori mi? (0/1) |
| `times_used` | INTEGER DEFAULT 0 | Kaç kez kullanıldı |
| `created_at` | TEXT NOT NULL | ISO format tarih |
| `updated_at` | TEXT NOT NULL | ISO format tarih |

### 2.2 locations tablosu

Kullanıcının kaydettiği yerler (Ev, Okul vb.).

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| `id` | TEXT PRIMARY KEY | Benzersiz yer ID |
| `name` | TEXT NOT NULL | Yer adı |
| `lat` | REAL NOT NULL | Enlem |
| `lon` | REAL NOT NULL | Boylam |
| `icon_type` | TEXT DEFAULT 'star' | home, work, school, gym, market, star vb. |
| `address` | TEXT DEFAULT '' | Açık adres |
| `favorite` | INTEGER DEFAULT 0 | Favori mi? (0/1) |
| `times_used` | INTEGER DEFAULT 0 | Kaç kez kullanıldı |
| `created_at` | TEXT NOT NULL | ISO format tarih |
| `updated_at` | TEXT NOT NULL | ISO format tarih |

### 2.3 local_places tablosu (YENİ — 08.03.2026)

Önceden tanımlı popüler yerler. Geocoder API'ye gitmeden önce bu tabloya bakar.

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| `id` | INTEGER PRIMARY KEY | Otomatik artan ID |
| `name` | TEXT NOT NULL | Yer adı (örn: "Taksim", "Kadıköy") |
| `display_name` | TEXT NOT NULL | Tam adres metni |
| `lat` | REAL NOT NULL | Enlem |
| `lon` | REAL NOT NULL | Boylam |
| `place_type` | TEXT DEFAULT 'semt' | semt, il_merkez, landmark |
| `search_terms` | TEXT DEFAULT '' | Alternatif arama terimleri (typo: "kadikoy") |

**Seed veri:** 45 yer (İstanbul semtleri, Ankara, İzmir, Antalya, Bursa, il merkezleri)

---

## 3. geocodes.db — Geocoding Cache

**Dosya yolu:** `backend/cache/geocodes.db`  
**Modül:** `geocoder.py`  
**Oluşma:** İlk yer arama yapıldığında.

### 3.1 geocodes tablosu

Yer ismi → koordinat (Nominatim API sonuçları).

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| `query_hash` | TEXT PRIMARY KEY | Sorgu metninin MD5 hash'i |
| `lat` | REAL | Enlem |
| `lon` | REAL | Boylam |
| `display_name` | TEXT | Tam adres metni |
| `address` | TEXT | Adres detayları |
| `timestamp` | REAL | Kaydedilme zamanı |

### 3.2 reverse_geocodes tablosu

Koordinat → yer ismi.

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| `lat_lon_key` | TEXT PRIMARY KEY | `{lat:.6f}_{lon:.6f}` formatı |
| `display_name` | TEXT | Bulunan yer adı |
| `address` | TEXT | Adres detayları |
| `timestamp` | REAL | Kaydedilme zamanı |

---

## 4. districts_turkey.db — İl/İlçe Veritabanı

**Dosya yolu:** `backend/cache/districts_turkey.db`  
**Modül:** `districts_db.py`  
**Kaynak:** `TURKEY_DISTRICTS` sözlüğü (81 il + ilçeler)

İl ve ilçe listesi, hızlı arama için SQLite'da tutulur.

---

## 5. DİĞER VERİ KAYNAKLARI (Veritabanı Değil)

### 5.1 turkey_places.py

- **Format:** Python sözlüğü (TURKEY_PLACES)
- **İçerik:** 81 il + 970+ ilçe
- **Kullanım:** BERT NLP, typo tolerance
- **Not:** Koordinat içermez, sadece isim listesi

### 5.2 OSM GraphML dosyaları

- **Konum:** `backend/data/*.graphml`
- **İçerik:** OSM sokak ağları (OSMnx formatı)
- **Örnek:** `kadikoy_istanbul_turkey.graphml`, `point_40.99_29.02_500.graphml`

### 5.3 Memory cache (RAM)

- `_graph_cache`: Yer adı → OSM grafiği
- `_poi_cache`: `{place}::{category}` → POI listesi
- `_geocode_cache`, `_reverse_geocode_cache`: Geocoder memory cache

---

## 6. YAPILAN DEĞİŞİKLİKLER (08.03.2026)

### 6.1 JSON → SQLite Geçişi

| Önceki | Sonraki |
|--------|---------|
| `saved_routes.json` | `app_data.db` → `routes` tablosu |
| `saved_locations.json` | `app_data.db` → `locations` tablosu |

### 6.2 Eklenen Dosyalar

- **storage_db.py** — SQLite bağlantısı, şema tanımı
- **app_data.db** — Uygulama çalışınca otomatik oluşur

### 6.3 Güncellenen Dosyalar

- **route_storage.py** — SQLite kullanımı, JSON migrasyonu
- **location_storage.py** — SQLite kullanımı, JSON migrasyonu
- **.gitignore** — app_data.db, saved_locations.json eklendi

### 6.4 Otomatik Migrasyon

Mevcut `saved_routes.json` veya `saved_locations.json` varsa ve tablolar boşsa, veriler otomatik olarak SQLite'a taşınır.

---

## 7. VERİ AKIŞI ÖZETİ

```
Kullanıcı "Kaydet" tıklar
    → route_storage.save_route() veya location_storage.save_location()
    → storage_db.get_connection()
    → app_data.db'ye INSERT

Kullanıcı yer arar ("Kadıköy")
    → geocoder.geocode()
    → 1) Memory cache
    → 2) geocodes.db (SQLite)
    → 3) Nominatim API
    → Sonuç cache'e yazılır
```

---

## 8. GELECEK FİKİRLER — Optimizasyon ve Geliştirme

### 8.1 SQLite Performans

| Fikir | Açıklama |
|-------|----------|
| **İndeksler** | `routes(created_at)`, `routes(favorite)`, `routes(name)`, `locations(name)` |
| **WAL modu** | `PRAGMA journal_mode=WAL` — daha iyi eşzamanlı okuma/yazma |
| **PRAGMA ayarları** | `synchronous`, `cache_size` optimizasyonu |

### 8.2 Yerel Yer Veritabanı

| Fikir | Açıklama |
|-------|----------|
| **local_places tablosu** | Popüler semtler, landmark'lar (Taksim, Kadıköy, Galata Kulesi) |
| **Koordinatlı veri** | turkey_places sadece isim tutuyor; koordinat eklenebilir |
| **Geocoder fallback** | Nominatim yokken veya yavaşken local_places'e bak |

### 8.3 Geocoding İyileştirmeleri

| Fikir | Açıklama |
|-------|----------|
| **geocode_suggest cache** | Autocomplete şu an cache'siz; her tuşta API çağrısı |
| **Suggest SQLite tablosu** | Sık aranan yerler için ayrı cache tablosu |
| **Offline mod** | İnternet yokken local_places + kayıtlı yerlerle çalışma |

### 8.4 Yeni Tablo Fikirleri

| Tablo | Amaç |
|-------|------|
| **local_places** | Önceden tanımlı yerler (name, lat, lon, place_type, search_terms) |
| **geocode_suggest_cache** | Autocomplete sonuçları cache'i |
| **route_cache** | Sık kullanılan A→B rotaları (karmaşık, düşük öncelik) |

### 8.5 Veri Zenginleştirme

| Fikir | Açıklama |
|-------|----------|
| **Mahalle/cadde ekleme** | turkey_places veya local_places'e mahalle, cadde isimleri |
| **İl merkez koordinatları** | Her il için merkez (lat, lon) — fallback için |
| **Popüler POI'ler** | Sık aranan kategorilerin önceden hesaplanmış sonuçları |

### 8.6 Alternatif Rotalar

| Mevcut durum | Fikir |
|--------------|-------|
| Alternatif rotalar kaydedilmiyor | Kullanıcı hangisini seçerse o kaydediliyor |
| 3 rota anlık hesaplanıyor | İsteğe bağlı: 3'ünü birden kaydetme seçeneği |

---

## 9. DOSYA KONUMLARI ÖZETİ

```
OpenRoutePlanner/
└── backend/
    ├── data/
    │   ├── app_data.db          ← Rotalar + lokasyonlar
    │   └── *.graphml            ← OSM grafları
    ├── cache/
    │   ├── geocodes.db          ← Geocoding cache
    │   ├── districts_turkey.db  ← İl/ilçe
    │   └── (geocodes.db burada)
    ├── storage_db.py
    ├── route_storage.py
    ├── location_storage.py
    ├── geocoder.py
    └── districts_db.py
```

---

## 10. NOTLAR

- **app_data.db**, **geocodes.db**, **districts_turkey.db** — `.gitignore`'da, projeye commit edilmez
- Veritabanları uygulama ilk çalıştığında oluşturulur
- Alternatif rotalar veritabanına otomatik yazılmaz; kullanıcı kaydettiğinde `route_type` ile tek rota kaydedilir
