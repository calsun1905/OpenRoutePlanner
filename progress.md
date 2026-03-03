# Progress - OpenRoutePlanner

> 📂 Aylık ilerleme dosyaları için `progress/` klasörüne bakın
> 📝 Güncel ay: **[2026-02.md](progress/2026-02.md)**

---

## 📁 Dosya Yapısı

```
openroute/
├── .claude/
│   ├── hooks/
│   │   ├── SessionStart.claude   ← Oturum başı (otomatik + manuel)
│   │   └── SessionEnd.claude     ← Oturum sonu (SADECE manuel)
│   └── ...
│
├── progress.md                   ← Bu dosya (giriş noktası)
├── progress/
│   └── 2026-02.md                ← Şubat 2026 ilerlemesi
│
├── öneriler.md                   ← Öneriler ve notlar
├── komutlar.md                   ← GSD + SuperClaude komutları
│
├── günlük-rapor/                 ← Günlük notlar
│   ├── 27.02.2026/
│   ├── 28.02.2026/
│   └── 03.03.2026/
│
├── backend/
│   ├── app.py                    ← Flask API (tüm endpoint'ler)
│   ├── bert_engine.py            ← BERT embedding motoru (singleton)
│   ├── bert_nlp_engine.py        ← Ana NLP sistemi (niyet okuma + yer çıkarma)
│   ├── turkey_places.py          ← Türkiye veritabanı (81 il + ilçeler = 1775 yer)
│   ├── districts_db.py           ← İlçe veritabanı yönetimi (SQLite cache)
│   ├── osm_poi_dictionary.py     ← Türkçe→OSM etiket sözlüğü (167 kayıt)
│   ├── geocoder.py               ← Nominatim API + cache
│   ├── route_engine.py           ← Rota hesaplama + alternatif rotalar
│   ├── route_storage.py          ← Rota kaydetme/yükleme sistemi
│   ├── time_planner.py           ← Zaman bazlı planlama modülü
│   ├── nlp_engine.py             ← Eski regex tabanlı NLP (fallback)
│   ├── test_osm_poi.py           ← OSM Overpass API test aracı
│   ├── check_osm_counts.py       ← Kategori bazlı mekan sayısı sorgulama
│   ├── cache/
│   │   └── districts_turkey.db   ← Önbellek veritabanı
│   └── models/
│       └── bert-base-turkish-uncased/  ← BERT model dosyaları (.gitignore)
│
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
│
└── test_bert_extraction.py       ← BERT yer çıkarma testleri
```

---

## 🎯 Proje Hakkında

**Proje:** OpenRoutePlanner
**Teknoloji:** Python (Flask) + JavaScript (Frontend)
**Amaç:** Doğal dil ile rota planlama ve mekan arama

### Ana Özellikler:

1. 🗺️ **Rota Hesaplama** - `/api/get-route`
   - Noktalar arası en kısa rotayı bulur
   - TSP algoritması ile sıralama optimize eder
   - Gerçek sokak ağlarını kullanır
   - Mesafe/süre hesaplar
   - Google Maps linki üretir

2. 🔀 **Alternatif Rotalar** - `/api/get-alternative-routes` ❌ SORUNLU
   - En Kısa Rota (shortest) - Minimum mesafe
   - En Hızlı Rota (fastest) - Büyük yolları tercih eder
   - Dengeli Rota (balanced) - Mesafe ve hız arası denge
   - ❌ **Durum:** Birden fazla düzeltme denendi (Yen's K-Shortest Paths dahil), hala 3 seçenek aynı rotayı gösteriyor
   - ⚠️ Köklü algoritma değişikliği veya farklı yaklaşım gerekebilir
   - Commit: 27af924

3. 💾 **Rota Kaydetme/Yükleme** ✅ YENİ
   - Rota kaydetme, yükleme, silme
   - Favori sistemi (yıldızlama)
   - Rota arama ve filtreleme
   - ⚠️ Bilinen sorunlar:
     - Kaydetme işlemi çok uzun sürüyor (yavaşlık)
     - "Önce rotayı hesaplayın" uyarısı hatalı çalışıyor (rota zaten hesaplanmış)
   - Commit: bb19215

4. ⏰ **Zaman Bazlı Planlama** ❌ SORUNLU (Prototip)
   - Başlangıç saati seçimi
   - Varış/ayrılış saatleri hesaplama
   - Ziyaret ve yürüyüş süreleri
   - Timeline görünümü
   - ❌ **Durum:** Frontend'de "Zaman Planla" tuşu aktif gözükmüyor (disabled)
   - ⚠️ Backend mantığı hiç test edilmedi
   - Commit: 0fc237c

5. 🏛️ **POI Arama** - Müze, kafe vb. mekanları bulur

6. 🔎 **Yer İsmi ile Arama** - `/api/geocode`
   - Yer ismini koordinata çevirir (Nominatim API)
   - Memory + SQLite cache ile hızlı
   - Rate limiting: 1 req/s
   - Commit: 215bd40

7. 🧠 **BERT NLP Motoru** ✅ YENİ
   - **Model:** `dbmdz/bert-base-turkish-uncased` (440 MB, lokal)
   - **Embedding:** 768 boyutlu vektörler, GPU/CPU desteği
   - **Typo Tolerance:** "Kadikoy" → "Kadıköy" (%95), "Beşiktasi" → "Beşiktaş" (%93)
   - **Türkiye Veritabanı:** 81 il + ilçeler = 1775 yer ismi (turkey_places.py)
     - Bu liste BERT embedding'leri için temel veri kaynağıdır
     - Hızlı arama (0.05 sn) ve typo düzeltme için ZORUNLUDUR
     - OSM API tek başına typo düzeltme YAPAMAZ
     - İnternet olmadan da çalışma sağlar
   - **Sorgu Sınıflandırma:**
     - `route` → "Kadıköy'den Beşiktaş'a rota"
     - `poi` → "Kadıköy'de neler var?"
     - `multi` → "Kadıköy, Taksim ve Beşiktaş'ı gez"
     - `single` → "Taksim'e git"
   - **OSM API Entegrasyonu** (hazır, test bekliyor):
     - Bilinmeyen yerler için otomatik Nominatim sorgusu
     - Rate limiting (1 sn) ve cache sistemi
   - ⚠️ Eksikler:
     - /api/nlp/parse endpoint'i app.py'ye eklenmeli
     - Frontend entegrasyonu yapılmadı
     - False positive azaltma iyileştirme gerekli
   - Commitler: 951d0db, 5dcbc85

8. 🌍 **OSM POI Sözlüğü** ✅ YENİ
   - 167 Türkçe kelime → OSM etiket eşleştirmesi
   - Kategoriler: yeme-içme, alışveriş, sağlık, turizm, ulaşım, eğitim, tarih, doğa
   - BERT "poi" niyeti algıladığında bu sözlük devreye girer
   - Overpass API ile canlı veri çekme (binlerce mekan)
   - Commit: 5dcbc85

### Öğrenilenler:
- ✅ Global değişkenler: `_graph_cache`, `_poi_cache` (cache mekanizması)
- ✅ OSM Overpass API: Canlı mekan verileri çekme (Almanya sunucuları)
- ✅ BERT Singleton Pattern: Model bir kez yüklenir, her yerde kullanılır
- ✅ Lokal veritabanı + API hibrit yaklaşımı (hız + doğruluk dengesi)

---

## 📝 Notlar

- **Cache:** Uygulamanın hızını artırmak için kullanılan kısa süreli hafıza
- **TSP:** Gezgin Satıcı Problemi - noktaları en mantıklı sırada ziyaret etme algoritması
- **Overpass API:** OSM veritabanında arama motoru (internetten canlı veri çeker)
- **Embedding:** Kelimelerin 768 boyutlu matematiksel temsilci vektörleri

## 📅 Son Güncelleme: 03.03.2026 - Gün Sonu (~23:59)

---

## 🚀 03.03.2026 Akşam Oturumu - Değiştirilen Dosyalar (31 adet)

### 🎯 Kritik Kod Değişiklikleri

| Dosya | Yapılan Değişiklik |
|-------|--------------------|
| `frontend/js/app.js` | `routeGlowPolylines` tracking ile alternatif rota düzeltmesi, map debug logging, tile layer CartoDB → OSM Standard |
| `frontend/css/style.css` | Map arka plan rengi `#e5e5e5` (gri) yapıldı |
| `frontend/index.html` | Cache buster eklendi (`?v=1.0.3`) |
| `frontend/test.html` | Yeni oluşturuldu (harita test sayfası) |
| `backend/route_storage.py` | `simplify_coords()` fonksiyonu eklendi — koordinatları sıkıştırarak kaydetmeyi hızlandırır |
| `backend/app.py` | Encoding fix (Türkçe print'ler kaldırıldı), file-based logging eklendi |
| `backend/geocoder.py` | `qhash` NameError fix, encoding print'ler kapatıldı |
| `backend/route_engine.py` | SyntaxError (yanlış yerleştirilmiş `except` bloğu) kaldırıldı |

### 📋 Oluşturulan Dokümantasyon Dosyaları

| Dosya | İçerik |
|-------|--------|
| `ALTERNATIF_ROTA_DUZELTME.md` | Alternatif rota UI fix açıklaması |
| `FIX_OSMNX_ERROR.md` | OSMnx graph indirme hatası çözümü |
| `GERCEK_COZUM.md` | Gerçek çözüm notları |
| `TIMELINE_FIX_REPORT.md` | Zaman planlama fix raporu |
| `TROUBLESHOOTING.md` | Genel hata giderme rehberi |
| `UI_IMPROVEMENT_POI_LOCATION.md` | POI konum UI iyileştirmesi |
| `ZAMAN_PLANLA_BUTON_FIX.md` | Zaman planla butonu fix |

### 🧪 Test ve Yardımcı Dosyalar
`test_bert_extraction.py`, `test_endpoints.py`, `test_timeline.py`, `quick_test.py`, `backend/test_maltepe_poi.py`, `backend/test_osm_poi.py`

---

## 🚀 03.03.2026 Gün Sonu Oturumu - Çalışmalar (23 değişen dosya)

### 🎯 Yapılan Çalışmalar

| Alan | Yapılan | Sonuç |
|------|---------|-------|
| **Alternatif Rota Algoritması** | Yen's K-Shortest Paths dahil birkaç farklı yaklaşımla düzeltme denendi | ❌ BAŞARISIZ - Birkaç denemeden sonra hala 3 seçenek aynı rotayı gösteriyor. Algoritma fiziksel olarak farklı güzergah üretemiyor. |
| **Zamanlayıcı (Time Planner)** | Frontend'de "Zaman Planla" tuşu incelendi | ❌ Tuş aktif olarak gözükmüyor, tıklanamıyor (disabled durumda) |
| **OSM Mekan Endpoint'leri** | OSM üzerinde mekan (POI) endpoint'lerinin nasıl çalıştığı araştırıldı, frontend tarafında gerçek eşleşme olup olmayacağı incelendi | ⏳ Araştırma aşamasında - nasıl eklenir, frontend'de eşleşir mi soruları üzerinde çalışıldı |
| **Rota Kaydetme** | Rota kaydetme/yükleme işlemleri üzerinde çalışıldı | ⚠️ Temel çalışıyor, iyileştirmeler devam ediyor |

### 📊 Durum Özeti
- **Çözülen sorun:** Yok (bugün ağırlıklı olarak araştırma ve deneme günüydü)
- **Denenen ama çözülemeyen:** Alternatif rota algoritması (birden fazla deneme)
- **Araştırılan:** OSM mekan endpoint'leri + frontend entegrasyonu
- **Tespit edilen yeni sorun:** Zamanlayıcı tuşu frontend'de disabled

---

## 🐛 Bilinen Sorunlar ve Kötü Çalışan Yerler

### 1. Alternatif Rotalar - ❌ ÇÖZÜLEMEDI (Birden Fazla Deneme Yapıldı)
| Sorun | Detay | Önem | Durum |
|-------|-------|------|-------|
| 3 seçenek aynı çizgiyi gösteriyor | Shortest/Fastest/Balanced olarak 3 seçenek sunuluyor ama haritada hepsi aynı polyline'ı çiziyor | 🔴 Yüksek | ❌ Çözülemedi |
| Gerçek alternatif üretilmiyor | Yen's K-Shortest Paths dahil birkaç farklı yaklaşım denendi, hala aynı yolu döndürüyor | 🔴 Yüksek | ❌ Çözülemedi |
| Birden fazla deneme yapıldı | 03.03.2026'da birkaç kez düzeltme denendi ama başarısız oldu, algoritma köklü bir yeniden yazım gerektirebilir | 🔴 Yüksek | ❌ Bekliyor |
| **Kural:** Düz çizgi hariç her yerde fiziksel olarak farklı güzergah bulunabilir. "Aynı yol" cevabı kabul edilemez. | | | |

### 2. Rota Kaydetme/Yükleme - ✅ Temelde Çalışıyor
| Durum | Detay |
|-------|-------|
| ✅ Kaydetme | `simplify_coords()` ile hızlandırıldı |
| ✅ Yükleme | Çalışıyor |
| ✅ Silme | Çalışıyor |
| ⚠️ | Edge case'ler ve favori sistemi tam doğrulanmadı |

### 3. Rota Hesaplama - ⚠️ Aralıklı Hata
| Sorun | Detay | Önem |
|-------|-------|------|
| Bazen hata veriyor | Çoğu zaman çalışıyor ama ara sıra hata fırlatıyor, kök neden araştırılmadı | 🔴 Yüksek |
| Uzun sürüyor | OSMnx graph ilk indirmede bottleneck | 🟡 Orta |

### 4. Zaman Bazlı Planlama - ❌ Frontend Tuşu Çalışmıyor
| Sorun | Detay | Önem |
|-------|-------|------|
| Tuş aktif gözükmüyor | "Zaman Planla" butonu frontend'de disabled/inaktif durumda, tıklanamıyor | 🔴 Yüksek |
| Sıfır test | Backend mantığı hiç test edilmedi | 🔴 Yüksek |

### 5. OSM Mekan Endpoint'leri - ⏳ Araştırma Aşamasında
| Sorun | Detay | Önem |
|-------|-------|------|
| Frontend eşleşmesi belirsiz | OSM endpoint'leri backend'de var ama frontend'te gerçekten doğru eşleşip eşleşmediği test edilmedi | 🟡 Orta |
| Entegrasyon planı gerekli | Mekan verilerinin frontend'e nasıl aktarılacağı ve gösterileceği planlanmalı | 🟡 Orta |

### 6. BERT NLP Motoru - ⏳ Yapılacak
| Sorun | Detay | Önem |
|-------|-------|------|
| API endpoint yok | `/api/nlp/parse` app.py'ye eklenmedi | 🔴 Yüksek |
| Frontend bağlantısı yok | Hiçbir arayüz BERT'e bağlı değil | 🔴 Yüksek |
| False positive | Bazı kelimeleri yanlış yer ismi olarak algılıyor | 🟡 Orta |

---

## 🧪 Test Durumu (03.03.2026 Gün Sonu)

| Özellik | Test Edildi mi? | Sonuç |
|---------|-----------------|-------|
| Rota Hesaplama | ✅ Evet | Genellikle çalışıyor, bazen hata |
| Alternatif Rotalar | ❌ Birkaç deneme | Birden fazla düzeltme denendi, hala aynı rotayı gösteriyor |
| Rota Kaydetme/Yükleme/Silme | ✅ Evet | Temel çalışıyor |
| Zaman Planlama | ❌ Hayır | Frontend tuşu disabled, backend test edilmedi |
| POI Arama | ✅ Evet | Maltepe dahil çalışıyor |
| OSM Mekan Endpoint'leri | ⏳ Araştırıldı | Nasıl çalıştığı incelendi, frontend eşleşmesi bekliyor |
| Geocoding | ✅ Evet | Çalışıyor |
| BERT Typo Tolerance | ✅ Evet | Kadikoy→Kadıköy %95 |
| NLP→Frontend Entegrasyon | ❌ Hayır | Henüz yapılmadı |

---

## 📋 Yapılacaklar (TODO)

### 🔴 Acil
- [x] Backend encoding (charmap) hatalarını düzeltme
- [x] Frontend tıklanabilirlik sorunu giderme
- [x] POI arama bağlantı hatası giderme (Maltepe)
- [x] `simplify_coords()` ile rota kaydetme hızlandırma
- [ ] **Alternatif rotaların gerçek geometrik farklılık üretmesi** ← EN ÖNEMLİ (birden fazla deneme yapıldı, çözülemedi)
- [ ] **Zamanlayıcı tuşunun frontend'de aktif hale getirilmesi** ← YENİ
- [ ] Rota hesaplama aralıklı hata sebebinin araştırılması
- [ ] OSM mekan endpoint'lerinin frontend'e entegrasyonu

### 🟡 Önemli
- [ ] BERT NLP motorunun frontend'e bağlanması
- [ ] `/api/nlp/parse` endpoint'inin app.py'ye eklenmesi
- [ ] False positive azaltma (threshold iyileştirme)
- [ ] Rota kaydetme edge case'lerinin tam doğrulanması

### 🟢 Gelecek
- [ ] OSM API fallback mekanizmasının test edilmesi
- [ ] Veritabanına mahalle, cadde, özel mekan isimleri eklenmesi
- [ ] POI aramasında kategori bazlı harita gösterimi

---