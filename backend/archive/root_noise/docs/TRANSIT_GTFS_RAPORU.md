# IBB Transit Sistemi - Calisma Raporu

**Tarih:** 26.05.2026  
**Konu:** GTFS Shapes Entegrasyonu ve Metro Rota Cizimi

---

## 1. Yapilan Isler

### 1.1 GTFS Shapes Indirme Sistemi
**Dosya:** `backend/gtfs_shapes.py`

- IBB CKAN API (`https://data.ibb.gov.tr/api/3/action/package_show?id=public-transport-gtfs-data`) uzerinden GTFS shapes verisi indirildi.
- **Dogrulanan ham veri:**
  - `backend/cache/gtfs_shapes.csv` -> 149,845 satir
  - unique `shape_id` -> **953**
- **Dogrulanan cache:**
  - `backend/cache/shapes_cache.json` -> **953 shape**

Kullanilan temel fonksiyonlar:
- `download_gtfs_csv()`
- `download_and_parse_shapes()`
- `match_shapes_to_metro_lines()`
- `get_metro_line_shape()`

### 1.2 Hat Koordinat Cache'i
**Dosya:** `backend/cache/gtfs_route_shapes.json`  
**Boyut:** 219,628 bytes (~220 KB)  
**Toplam hat:** 23  
**Toplam koordinat:** 5,788

| Hat | Koordinat |
|---|---:|
| M1A | 298 |
| M1B | 254 |
| M2 | 121 |
| M2A | 2 |
| M3 | 172 |
| M3A | 32 |
| M4 | 28 |
| M5 | 577 |
| M6 | 182 |
| M7 | 549 |
| M8 | 302 |
| M9 | 74 |
| Marmaray | 1870 |
| Marmaray1 | 244 |
| Marmaray2 | 277 |
| T1 | 434 |
| T3 | 99 |
| T4 | 221 |
| F1 | 2 |
| F2 | 4 |
| F3 | 40 |
| TF1 | 3 |
| TF2 | 3 |

### 1.3 Metro Cizim Algoritmasi
**Dosya:** `backend/multimodal_engine.py` (yaklasik 1850-1930)

- `_build_graph_metro_option()` icinde `get_metro_line_shape(line_name)` cagriliyor.
- Istasyonlar, shape koordinatlarina en yakin noktalara snap ediliyor.
- Bir shape noktasinin tekrar kullanimi `used_indices` ile sinirlanarak daha stabil bir cizim elde ediliyor.

### 1.4 Otobus OSRM Entegrasyonu
**Dosya:** `backend/multimodal_engine.py`

- `_get_bus_road_coords()` duraklar arasi yolu OSRM ile ciziyor.
- `_get_route_stop_coords()` sirali duraklardan road-snapped cizim uretiyor.

---

## 2. Duzeltilen Teknik Noktalar

| # | Konu | Durum |
|---|---|---|
| 1 | `sqlite3.Row` uzerinde `.get()` yerine `row['field']` kullanimi | Uygulandi |
| 2 | CKAN kaynak adlarinda `.txt` suffix normalizasyonu | Uygulandi |
| 3 | `shapes.csv` parse oncesi header dogrulamasi | Uygulandi |
| 4 | `gtfs_route_shapes.json` cache yolu `backend/cache/` | Uygulandi |

---

## 3. Bilinen Eksikler

### 3.1 Dusuk Koordinatli Hatlar
Asagidaki hatlarda GTFS koordinat sayisi cok dusuk:

| Hat | Koordinat |
|---|---:|
| F1 | 2 |
| F2 | 4 |
| TF1 | 3 |
| TF2 | 3 |
| M2A | 2 |

**GTFS verisi önceliklidir; yalnızca düşük kalite/sparse hatlarda (örn. F1, F2, TF1, TF2, M2A) koordinat sayisi esik altina düşerse manuel fallback uygulanir (mevcut esik: 8 nokta).**

### 3.2 Test Kapsami
- Frontend harita cizimi manuel/E2E dogrulama setiyle takip edilmeli.
- Transit panel akisi ve segment gorunurlugu senaryolari surekli regresyona alinmali.

### 3.3 Hat Kapsami
- T5 GTFS route cache'inde bulunmuyor; manuel fallback kullaniliyor.
- T2 icin GTFS/manuel netlestirme calismasi gerekli.

---

## 4. Eslestirme Davranisi (Kod Gercegi)

`match_shapes_to_metro_lines()` fonksiyonu routes/trips tablosu degil, **transit DB icindeki `metro_lines`** kayitlarini (`name`, `functional_code`) kullanarak shape adaylarini eslestirir.

---

## 5. Ilgili Dosyalar

| Dosya | Aciklama |
|---|---|
| `backend/gtfs_shapes.py` | GTFS indirme, parse, eslestirme, shape secimi |
| `backend/cache/gtfs_shapes.csv` | Ham shapes verisi |
| `backend/cache/shapes_cache.json` | Parse edilmis shape cache (953 shape) |
| `backend/cache/gtfs_route_shapes.json` | Hat bazli route shape cache |
| `backend/multimodal_engine.py` | Transit rota ve cizim koordinati uretimi |
| `frontend/js/transit.js` | Transit cizim UI akisi |

---

**Rapor Tarihi:** 26.05.2026  
**Toplam Hat:** 23  
**Toplam Koordinat:** 5,788
