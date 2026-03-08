# OpenRoutePlanner — Performans Optimizasyon Planı

> **Bu dosya projenin tüm performans ve veritabanı optimizasyon planını içerir.**
> Kaybolmaması için detaylı tutulmuştur. Uygulama aşamaları bu dosyaya göre yapılacaktır.

**Oluşturulma:** 08.03.2026  
**Durum:** Uygulanacak — Kesinlikle eklenecek

---

## İÇİNDEKİLER

1. [Genel Bakış](#1-genel-bakış)
2. [Yapılanlar (Tamamlanan)](#2-yapılanlar-tamamlanan)
3. [SQLite Optimizasyonları](#3-sqlite-optimizasyonları)
4. [Memory-Mapped I/O (mmap) Açıklaması](#4-memory-mapped-io-mmap-açıklaması)
5. [Önceden İndirme (Preload) Açıklaması](#5-önceden-indirme-preload-açıklaması)
6. [Geocode TTL ve Cache Temizliği](#6-geocode-ttl-ve-cache-temizliği)
7. [Uygulama Fazları](#7-uygulama-fazları)
8. [Kod Referansları](#8-kod-referansları)

---

## 1. GENEL BAKIŞ

### 1.1 Planın Amacı

Uygulamayı **Prototip** aşamasından **Production (Canlı)** aşamasına taşımak için:

- Veritabanı okuma/yazma hızını artırmak
- Rota hesaplama süresini kısaltmak (önceden indirme ile)
- Geocoding ve cache yönetimini iyileştirmek

### 1.2 Üç Ana Katman

| Katman | Açıklama |
|--------|----------|
| **SQLite Optimizasyonu** | PRAGMA ayarları, indeksler, mmap, ANALYZE |
| **1 GB Cache Doğru Kullanımı** | geocodes.db'ye aynı ayarlar, TTL/purge |
| **Bölge Önceden İndirme** | İstanbul vb. için graph'ları önceden indir, rota hesaplamada kullan |

---

## 2. YAPILANLAR (TAMAMLANAN)

### 2.1 JSON → SQLite Geçişi ✅

- `saved_routes.json` → `app_data.db` routes tablosu
- `saved_locations.json` → `app_data.db` locations tablosu
- Otomatik migrasyon (mevcut JSON varsa taşınır)

### 2.2 storage_db.py PRAGMA Ayarları ✅

```python
PRAGMA journal_mode = WAL;      # Yazarken okumayı kilitlemez
PRAGMA synchronous = NORMAL;   # Disk yazma optimizasyonu
PRAGMA cache_size = -1048576;  # 1 GB RAM cache (1024×1024 KB)
PRAGMA temp_store = MEMORY;    # Geçici işlemler RAM'de
```

### 2.3 İndeksler ✅

- `idx_routes_favorite`, `idx_routes_created_at`, `idx_routes_favorite_created`, `idx_routes_name`
- `idx_locations_favorite`, `idx_locations_created_at`, `idx_locations_favorite_created`, `idx_locations_name`
- `idx_local_places_name`

### 2.4 mmap + ANALYZE ✅

- `PRAGMA mmap_size = 1073741824` (storage_db.py, geocoder.py)
- `ANALYZE` — init_schema sonunda çalışır

### 2.5 geocodes.db PRAGMA + TTL ✅

- geocoder.py: WAL, cache_size, mmap, temp_store
- `purge_old_geocodes(days=90)` — uygulama başlangıcında çağrılır

### 2.6 local_places Tablosu ✅

- 45 önceden tanımlı yer (Taksim, Kadıköy, Ankara, İzmir vb.)
- Geocoder API'ye gitmeden önce bu tabloya bakar
- `local_places.py` — SEED_PLACES listesi, lookup() fonksiyonu

---

## 3. SQLITE OPTİMİZASYONLARI

### 3.1 Eklenecek PRAGMA'lar

| PRAGMA | Değer | Açıklama |
|--------|-------|----------|
| `mmap_size` | `1073741824` | 1 GB memory-mapped I/O (byte cinsinden) |
| `journal_mode` | `WAL` | Zaten var |
| `synchronous` | `NORMAL` | Zaten var |
| `cache_size` | `-1048576` | 1 GB — Zaten var |
| `temp_store` | `MEMORY` | Zaten var |

### 3.2 Eklenecek İndeksler

```sql
-- Bileşik indeks: Favori rotaları tarihe göre
CREATE INDEX IF NOT EXISTS idx_routes_favorite_created ON routes(favorite, created_at DESC);

-- İsim araması için
CREATE INDEX IF NOT EXISTS idx_routes_name ON routes(name);

-- Lokasyonlar için bileşik
CREATE INDEX IF NOT EXISTS idx_locations_favorite_created ON locations(favorite, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_locations_name ON locations(name);
```

### 3.3 Periyodik ANALYZE ve OPTIMIZE

```sql
-- Sorgu planlayıcı için istatistik güncelleme
ANALYZE;

-- WAL checkpoint (opsiyonel, periyodik)
PRAGMA wal_checkpoint(TRUNCATE);
```

**Ne zaman çalıştırılır:** Uygulama başlangıcında veya belirli sayıda işlem sonrası.

---

## 4. MEMORY-MAPPED I/O (mmap) AÇIKLAMASI

### 4.1 Normal SQLite Okuma

```
1. SQLite "Kadıköy rotasını getir" der
2. Diskteki app_data.db dosyasından ilgili sayfayı OKUR
3. Bu sayfayı RAM'e KOPYALAR
4. RAM'deki kopyadan veriyi alır
5. İş bitince kopyayı atar
```

Her okumada: **Disk → RAM kopyalama** yapılır.

### 4.2 Memory-Mapped (mmap) ile

```
1. app_data.db dosyasını RAM'e "yansıt" (map et)
2. Dosya sanki RAM'deymiş gibi davranır
3. SQLite okuma yaparken doğrudan bu "yansıma"dan okur
4. İşletim sistemi gerektiğinde sayfaları diskten yükler
```

**Kopyalama yok** — doğrudan eşleşmiş bellekten okuma.

### 4.3 Benzetme

| Yöntem | Benzetme |
|--------|----------|
| **Normal** | Kitabı fotokopiyle çoğaltıp masana koyuyorsun |
| **mmap** | Kitabı masana açık bırakıyorsun, sayfaya baktığında doğrudan kitaptan okuyorsun |

### 4.4 Kod

```python
conn.execute("PRAGMA mmap_size = 1073741824;")  # 1 GB (byte)
```

- `1073741824` = 1024 × 1024 × 1024 = 1 GB
- SQLite veritabanı dosyasının en fazla 1 GB'ını memory-mapped kullanabilir

---

## 5. ÖNCEDEN İNDİRME (PRELOAD) AÇIKLAMASI

### 5.1 Şu An Ne Oluyor?

```
Kullanıcı Kadıköy + Taksim seçer → "Rota hesapla" tıklar
    ↓
Sistem: "Bu 2 nokta için sokak haritası lazım"
    ↓
İnternetten OSM'den İNDİR (5–30 saniye) ← YAVAŞ
    ↓
.graphml dosyasına kaydet
    ↓
Rota hesapla
```

### 5.2 Preload ile Ne Olacak?

```
UYGULAMA AÇILMADAN ÖNCE veya ilk açılışta:
    "Kadıköy sokak haritasını indir" → kaydet
    "Beşiktaş sokak haritasını indir" → kaydet
    "Şişli sokak haritasını indir" → kaydet
    (Bir kere yapılır, 2–3 dakika)

Kullanıcı "Rota hesapla" tıkladığında:
    "Noktalar Kadıköy/Beşiktaş bölgesinde"
    "Harita ZATEN VAR!"
    → Diskten oku (1–2 saniye) ← HIZLI
    → Rota hesapla
```

### 5.3 Benzetme

| Durum | Benzetme |
|-------|----------|
| **Preload yok** | Her yemek yaparken markete gidiyorsun |
| **Preload var** | Dolabı önceden dolduruyorsun; yemek yaparken dolaptan alıyorsun |

### 5.4 Regions Manifest (Bölge Kaydı)

Önceden indirilen bölgeleri tutacak tablo veya dosya:

| Alan | Açıklama |
|------|----------|
| `region_id` | Benzersiz ID |
| `place_name` | "Kadikoy, Istanbul, Turkey" |
| `center_lat`, `center_lon` | Merkez koordinat |
| `radius` | Yarıçap (metre) veya bbox |
| `graphml_path` | Dosya yolu |
| `updated_at` | Son güncelleme |

### 5.5 get_graph_for_points Mantığı (Yeni)

```
1. Kullanıcı noktaları verdi (points)
2. Bu noktalar hangi preload region içinde?
3. Varsa → O region'ın graphml'ini diskten oku
4. Yoksa → Mevcut mantık (graph_from_point ile indir)
```

### 5.6 Zorluklar

| Konu | Açıklama |
|------|----------|
| **İstanbul büyüklüğü** | Tüm İstanbul tek seferde çok büyük; ilçe bazlı yapılmalı |
| **Bölge eşleştirme** | Noktalar hangi region'a düşüyor? Bbox veya merkez+yarıçap kontrolü |
| **Çapraz rotalar** | Kadıköy–Taksim gibi iki ilçe arası → İki region'ı birleştirmek veya daha büyük region |

### 5.7 Önerilen Preload Listesi

- Kadıköy, Istanbul, Turkey
- Beşiktaş, Istanbul, Turkey
- Şişli, Istanbul, Turkey
- Fatih, Istanbul, Turkey
- Beyoğlu, Istanbul, Turkey
- Ankara, Turkey (veya Çankaya)
- İzmir, Turkey (veya Konak)

---

## 6. GEOCODE TTL VE CACHE TEMİZLİĞİ

### 6.1 Sorun

`geocodes.db` süresiz büyüyor. Her arama cache'e yazılıyor, hiç silinmiyor.

### 6.2 Çözüm: TTL (Time To Live)

- `geocodes` ve `reverse_geocodes` tablolarında `timestamp` var
- 30–90 günden eski kayıtları sil
- Periyodik cleanup (uygulama başlangıcında veya haftalık)

### 6.3 Örnek Cleanup Sorgusu

```sql
-- 90 günden eski geocodes
DELETE FROM geocodes WHERE timestamp < (strftime('%s', 'now') - 90*24*60*60);

-- 90 günden eski reverse_geocodes
DELETE FROM reverse_geocodes WHERE timestamp < (strftime('%s', 'now') - 90*24*60*60);
```

### 6.4 geocodes.db PRAGMA'ları

`geocoder.py` içindeki `_init_cache_db()` veya bağlantı açıldığında:

```python
conn.execute("PRAGMA journal_mode = WAL;")
conn.execute("PRAGMA synchronous = NORMAL;")
conn.execute("PRAGMA cache_size = -1048576;")  # 1 GB
conn.execute("PRAGMA mmap_size = 1073741824;")
conn.execute("PRAGMA temp_store = MEMORY;")
```

---

## 7. UYGULAMA FAZLARI

### FAZ 1: Geocodes.db + TTL ✅ TAMAMLANDI

| Adım | Dosya | Durum |
|------|-------|-------|
| 1 | `geocoder.py` | PRAGMA eklendi (WAL, cache_size, mmap, temp_store) |
| 2 | `geocoder.py` | `purge_old_geocodes(days=90)` eklendi |
| 3 | `app.py` | Uygulama başlangıcında purge çağrılıyor |

### FAZ 2: mmap + Ek İndeksler + ANALYZE ✅ TAMAMLANDI

| Adım | Dosya | Durum |
|------|-------|-------|
| 1 | `storage_db.py` | `PRAGMA mmap_size = 1073741824` eklendi |
| 2 | `storage_db.py` | Bileşik indeksler eklendi |
| 3 | `storage_db.py` | `init_schema()` sonunda `ANALYZE` çalışıyor |

### FAZ 3: Preload Region Yönetimi (Zor, En Büyük Etki)

| Adım | Dosya | Yapılacak |
|------|-------|-----------|
| 1 | Yeni: `preload_regions.py` | Region listesi, preload script |
| 2 | `graph_manager.py` | `get_graph_for_points` önce preload region'lara bak |
| 3 | `storage_db.py` veya ayrı | `regions` tablosu (region_id, place_name, center_lat, center_lon, radius, graphml_path, updated_at) |
| 4 | Script veya komut | `python -m backend.preload_regions` — İlçe graflarını indir |

---

## 8. KOD REFERANSLARI

### 8.1 Mevcut Dosya Konumları

```
OpenRoutePlanner/backend/
├── storage_db.py      ← app_data.db, PRAGMA, şema
├── route_storage.py   ← routes CRUD
├── location_storage.py← locations CRUD
├── local_places.py    ← SEED_PLACES, lookup()
├── geocoder.py        ← Nominatim, geocodes.db
├── graph_manager.py   ← get_graph, get_graph_for_points, OSMnx
├── data/
│   ├── app_data.db
│   └── *.graphml
└── cache/
    └── geocodes.db
```

### 8.2 PRAGMA Değer Referansı

| PRAGMA | Değer | Açıklama |
|--------|-------|----------|
| cache_size (1 GB) | `-1048576` | Negatif = KB, 1048576 KB = 1 GB |
| mmap_size (1 GB) | `1073741824` | Byte, 1024³ |
| TTL 90 gün (saniye) | `90*24*60*60` | 7776000 |

### 8.3 Öncelik Sırası (Uygulama Sırası)

1. **Faz 1** — geocodes.db PRAGMA + TTL
2. **Faz 2** — mmap + indeksler + ANALYZE
3. **Faz 3** — Preload region

---

## 9. NOTLAR VE UYARILAR

- Bu plan **kesinlikle uygulanacak** — proje hedefleri arasında
- Faz 1 ve 2 düşük risk, hızlı kazanım
- Faz 3 daha karmaşık, test gerekli
- Preload için ilk bölge: Kadıköy (küçük, test için ideal)
- Tüm değişiklikler bu dosyaya referans verilerek yapılacak

---

**Dosya sonu — Güncellemeler buraya eklenebilir**
