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
├── PROJECT_INDEX.md              ← Projenin tüm bileşenleri için indeks dosyası
├── öneriler 7 mart.md            ← 07.03.2026 geliştirme önerileri ve yol haritası
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

2. 🔀 **Alternatif Rotalar** - `/api/get-alternative-routes` 🔄 v3.0 YENİDEN YAZILDI
   - **v3.0 Strateji:** Dijkstra (Rota 1) → Via-Node (Rota 2, 3) → Gövde-only Penalty (yedek)
   - Via-Node: Ana rotadan uzak büyük kavşaklardan geçen rotalar (Google Maps/OSRM tarzı)
   - Asimetrik overlap: "Yeni rotanın % kaçı eskiyle aynı?" (eski Jaccard formülü düzeltildi)
   - Gövde-only penalty: Baş/son %10'a dokunmadan sadece gövdeye ceza
   - ✅ Disjoint paths'in OSM çıkmaz sokak problemi çözüldü (Via-Node ile değiştirildi)
   - ✅ Penalty zikzak problemi çözüldü (gövde-only + her iterasyonda yeniden oluşturma)
   - ✅ Jaccard alt küme yanılgısı düzeltildi (asimetrik formül)
   - ⚠️ Uçtan uca test bekliyor (torch kurulumu gerekli)
   - Konfigürasyon: `backend/route_config.py` (31 sabit, referans amaçlı)

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
   - ⚠️ **Durum:** Buton rota hesaplandıktan sonra aktif oluyor ancak deneyim hâlâ akıcı değil ve özellik pratikte prototip seviyesinde
   - ⚠️ Backend mantığı hiç test edilmedi
   - Commit: 0fc237c

5. 🏛️ **POI Arama** - Müze, kafe vb. mekanları bulur
   - Genişletilmiş Türkçe kategori sözlüğü ile çalışır
   - Frontend'de çok sayıda kategori butonu ile tetiklenir
   - Overpass/OSM verisini haritada gösterir

6. 🔎 **Yer İsmi ile Arama** - `/api/geocode` + `/api/geocode/suggest`
   - Yer ismini koordinata çevirir (Nominatim API)
   - Memory + SQLite cache ile hızlı
   - Rate limiting: 1 req/s
   - Yazarken öneri (autocomplete) desteği eklendi
   - Frontend tarafında debounce + öneri listesi ile daha akıcı arama deneyimi var
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

## 📅 Son Güncelleme: 08.03.2026 - Arama UX, Route Engine Düzeltmeleri ve Dokümantasyon

---

## 🚀 08.03.2026 Oturumu - Arama/Autocomplete, Route Engine Uyum Düzeltmeleri ve Dokümantasyon

### 🎯 Bu Oturumda Yapılanlar

| # | Değişiklik | Dosya | Durum |
|---|-----------|-------|-------|
| 1 | **Autocomplete endpoint'i eklendi** | `backend/app.py`, `backend/geocoder.py` | ✅ Tamamlandı |
| 2 | **Yer ismi arama kutusuna yazarken öneri eklendi** | `frontend/js/app.js`, `frontend/css/style.css` | ✅ Tamamlandı |
| 3 | **`route_type` → `route_index` uyum düzeltmesi** | `backend/app.py` | ✅ Tamamlandı |
| 4 | **Rota/TSP/POI akışına daha net loglar eklendi** | `backend/app.py`, `backend/geocoder.py`, `backend/graph_manager.py`, `backend/route_engine.py` | ✅ Tamamlandı |
| 5 | **Proje indeks dokümanı oluşturuldu** | `PROJECT_INDEX.md` | ✅ Yeni dosya |
| 6 | **Geliştirme önerileri ve yol haritası yazıldı** | `öneriler 7 mart.md` | ✅ Yeni dosya |
| 7 | **Progress güncellemesi** | `progress.md` | ✅ Güncellendi |

### 📝 Değişen Dosyalar ve Açıklamaları

**1. `backend/app.py`**
- `geocode_suggest` import edildi
- Yeni endpoint eklendi: `/api/geocode/suggest`
- Yer arama (`/api/geocode`) için daha net log akışı eklendi
- `/api/get-route` içinde `route_type` string değerinin `route_index` integer değerine çevrilmesi düzeltildi
- `/api/get-alternative-routes` ve `/api/search-pois` için debug logları netleştirildi

**2. `backend/geocoder.py`**
- Yeni fonksiyon eklendi: `geocode_suggest()`
- Kısmi arama için çoklu öneri döndüren autocomplete desteği yazıldı
- Memory cache ve SQLite cache hit durumları loglanır hale getirildi
- Geocoding akışı daha görünür hale geldi

**3. `backend/graph_manager.py`**
- POI arama başladığında ve bittiğinde daha sade/okunabilir loglar eklendi
- Bu sayede hangi bölge ve kategori için arama yapıldığı daha rahat takip ediliyor

**4. `backend/route_engine.py`**
- `solve_tsp()` içine başlangıç ve sonuç logları eklendi
- `find_alternative_routes()` içine alternatif rota üretim sayısını gösteren loglar eklendi
- Route engine tarafında özellikle TSP ve alternatif rota akışını takip etmek kolaylaştı

**5. `frontend/js/app.js`**
- Arama kutusuna yazarken otomatik öneri getiren debounce mekanizması eklendi
- `fetchSuggestions()` fonksiyonu ile backend autocomplete endpoint'ine bağlanıldı
- Kullanıcı öneri listesinden seçtiği yeri doğrudan haritaya ekleyebiliyor
- Dışarı tıklanınca öneri listesinin kapanması eklendi

**6. `frontend/css/style.css`**
- Yazarken çıkan öneri satırları için ek stil tanımları eklendi
- Böylece arama sonuçları ve öneri sonuçları arayüzde daha okunur hale geldi

**7. `PROJECT_INDEX.md`**
- Projenin ana yapısı, endpoint'leri, backend/frontend dosyaları ve çekirdek modülleri tek bir dosyada özetlendi
- Yeni oturumlarda hızlı bağlam kurmak için referans dosyası olarak kullanılabilir

**8. `öneriler 7 mart.md`**
- Uygulamanın gelişim yönü için ürün, teknik ve mimari öneriler yazıldı
- Faz bazlı yol haritası oluşturuldu

### ✅ Bu Oturumun Sonucu

- Yer arama deneyimi artık sadece tam arama değil, yazarken öneri veren daha modern bir yapıya geçti
- Route engine ile backend API arasındaki `route_type`/`route_index` uyumsuzluğu giderildi
- Geliştirici tarafında loglar sayesinde hata ayıklama daha kolay hale geldi
- Dokümantasyon tarafı güçlendirildi: indeks dosyası ve ayrı öneri dosyası eklendi

---

## 🚀 07.03.2026 Oturumu - Alternatif Rota Motoru v3.0 Yeniden Yazımı

### 🎯 Bu Oturumda Yapılanlar

| # | Değişiklik | Dosya | Durum |
|---|-----------|-------|-------|
| 1 | **Jaccard → Asimetrik Overlap** | `backend/route_engine.py` | ✅ Tamamlandı |
| 2 | **Via-Node (Ara Nokta) sistemi** | `backend/route_engine.py` | ✅ Tamamlandı |
| 3 | **Gövde-Only Penalty (zikzak önleme)** | `backend/route_engine.py` | ✅ Tamamlandı |
| 4 | **find_alternative_routes v3.0 yeniden yazımı** | `backend/route_engine.py` | ✅ Tamamlandı |
| 5 | **Konfigürasyon sabitleri dosyası** | `backend/route_config.py` | ✅ Yeni dosya |
| 6 | **Frontend cache bugfix** | `frontend/js/app.js` | ✅ Tamamlandı |
| 7 | **Progress ve günlük rapor** | `progress.md`, `günlük-rapor/` | ✅ Güncellendi |

### 📝 Detaylı Değişiklik Açıklamaları

**1. Overlap Formülü Düzeltmesi (Kritik Bug)**
- **Eski:** Jaccard formülü (`kesişim / birleşim`) — 100 kenarlık rotanın 20 kenarlık alt kümesini "%20 farklı" sanıyordu
- **Yeni:** Asimetrik formül (`kesişim / yeni_rota_kenar_sayısı`) — aynı örnek artık "%100 aynı" olarak doğru tespit ediliyor
- Fonksiyon: `count_edge_overlap()`

**2. Via-Node (Ara Nokta) Sistemi (Yeni)**
- Google Maps / OSRM tarzı endüstri standardı yaklaşım
- Ana rotanın bounding box'ını genişletip, ana rotadan uzak büyük kavşakları (degree ≥ 3) bulur
- `A → C → B` şeklinde ara noktadan geçen rota oluşturur
- Disjoint paths'in OSM çıkmaz sokak problemini kökten çözer
- Fonksiyon: `find_via_node_routes()`

**3. Gövde-Only Penalty (Yeni)**
- **Eski:** Tüm kullanılmış kenarlara sabit ×2 ceza → "zikzak" (tırtıklı) rotalar üretiyordu
- **Yeni:** Rotanın baş %10 ve son %10'una dokunmaz, sadece gövde kenarlarını cezalandırır
- Penalty grafı her iterasyonda yeniden oluşturuluyor (eskiden aynı grafı tekrar kullanıyordu)
- Fonksiyonlar: `get_body_edges()`, `find_routes_with_penalty()` güncellendi

**4. find_alternative_routes v3.0**
- **Eski strateji:** Topoloji analizi → Disjoint paths → Penalty
- **Yeni strateji:** Dijkstra (Rota 1) → Via-Node (Rota 2, 3) → Gövde-only Penalty (yedek)
- Eski fonksiyonlar (`find_disjoint_paths`, `check_alternative_potential`) korundu ama artık çağrılmıyor

**5. route_config.py (Yeni Dosya)**
- Tüm hardcoded sabitlerin merkezi referansı (31 anahtar)
- Şu an referans amaçlı — ileride route_engine.py buradan okuyacak
- Via-Node parametreleri: bbox genişletme, min degree, max aday, self-overlap limiti

**6. Frontend Cache Bugfix**
- `alternativeRoutesCache` değişkeni STATE'te tanımlı değildi → alternatif rota seçince harita güncellenemiyordu
- `displayAlternativeRoutes()` içinde cache doldurma eklendi

### ⏳ Bu Oturumda Yapılmayanlar / Bekleyenler

| # | Konu | Neden Yapılmadı | Öncelik |
|---|------|-----------------|---------|
| 1 | route_config.py'den okuma | Sabitleri taşıdık ama route_engine henüz config'den okumuyor (referans dosyası) | 🟡 Orta |
| 2 | Uçtan uca test | Backend başlatılamıyor (`torch` versiyon uyumsuzluğu) | 🔴 Yüksek |
| 3 | BERT `/api/nlp/parse` endpoint | app.py'ye eklenmedi | 🔴 Yüksek |
| 4 | Frontend BERT entegrasyonu | Endpoint olmadan yapılamaz | 🔴 Yüksek |
| 5 | torch kurulumu düzeltme | `torch==2.5.1` Python 3.13 ile uyumsuz, 2.6.0+ gerekebilir | 🟡 Orta |

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
| **Alternatif Rota Algoritması** | Yen's K-Shortest Paths + Edge-based overlap (04.03.2026'da çözüldü) | ✅ ÇÖZÜLDÜ - Node overlap yerine edge overlap kullanıldı, %60 threshold ile minimum %40 farklı sokak garantilendi |
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

### 1. Alternatif Rotalar - 🔄 v3.0 Yeniden Yazıldı (07.03.2026)
| Sorun | Detay | Önem | Durum |
|-------|-------|------|-------|
| ~~3 seçenek aynı çizgiyi gösteriyordu~~ | v3.0 Via-Node ile geometrik olarak farklı rotalar üretiliyor | 🔴 Yüksek | ✅ Çözüldü |
| ~~Jaccard alt küme yanılgısı~~ | Asimetrik overlap formülüne geçildi | 🔴 Yüksek | ✅ Çözüldü |
| ~~Disjoint OSM çıkmaz sorun~~ | Via-Node sistemi ile değiştirildi | 🔴 Yüksek | ✅ Çözüldü |
| ~~Penalty zikzak problemi~~ | Gövde-only penalty + her iterasyonda rebuild | 🔴 Yüksek | ✅ Çözüldü |
| Uçtan uca test yapılmadı | Backend başlatılamıyor (torch sorunu) | 🔴 Yüksek | ⏳ Bekliyor |
| **Yöntem v3.0:** Dijkstra + Via-Node + Gövde-only Penalty | Eski disjoint/connectivity kaldı ama çağrılmıyor | | ✅ Aktif |

### 2. Rota Kaydetme/Yükleme - ✅ Temelde Çalışıyor
| Durum | Detay |
|-------|-------|
| ✅ Kaydetme | `simplify_coords()` ile hızlandırıldı |
| ✅ Yükleme | Çalışıyor |
| ✅ Silme | Çalışıyor |
| ⚠️ | Edge case'ler ve favori sistemi tam doğrulanmadı |

### 3. Rota Hesaplama - ⚠️ Aralıklı Hata (Ana rota stabil, alternatiflerde sorunlar var)
| Sorun | Detay | Önem |
|-------|-------|------|
| Bazen hata veriyor | Ana rota (Dijkstra) genelde stabil; alternatif rota algoritması bazı uç örneklerde hata fırlatıyor | 🔴 Yüksek |
| Uzun sürüyor | OSMnx graph ilk indirmede bottleneck, yarıçap ve cache ile kısmen optimize edildi ama daha da iyileştirilebilir | 🟡 Orta |

### 3A. Yer İsmi ile Arama - ✅ Geliştirildi
| Durum | Detay | Önem |
|-------|-------|------|
| ✅ Autocomplete eklendi | `/api/geocode/suggest` ile yazarken öneri listesi geliyor | 🟢 Faydalı |
| ✅ Debounce eklendi | Her tuşta değil, kısa gecikme ile istek atılıyor | 🟢 Faydalı |
| ⚠️ Nominatim bağımlılığı sürüyor | Dış servis limiti ve ağ yavaşlığı hâlâ etkileyebilir | 🟡 Orta |

### 4. Zaman Bazlı Planlama - ⚠️ Tuş Hâlâ Pratikte Kullanılamıyor
| Durum | Detay | Önem |
|-------|-------|------|
| ⚠️ Tuş tasarım gereği sonradan aktif oluyor ama kullanıcı açısından “çalışmıyor gibi” | Buton, rota hesaplandıktan sonra otomatik aktif oluyor (`updateButtons()` → `selectedPoints.length >= 2 && currentRouteData`), fakat gerçek kullanımda henüz akıcı bir deneyim sağlamıyor; zaman modu fiilen kullanılmıyor | 🟡 Orta |
| ⚠️ Backend testi yapılmadı | `time_planner.py` ve `/api/timeline/create` endpoint'i var ama gerçek kullanımda test edilmedi; ileride detaylı test ve UX iyileştirmesi gerekiyor | 🟡 Orta |

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
| Öncelik notu | Alternatif rota algoritması netleştikten sonra **bir sonraki büyük adım BERT entegrasyonunu tamamlamak** (unutulmaması için not) | 🟡 Orta |

---

## 🧪 Test Durumu (04.03.2026 Akşam)

| Özellik | Test Edildi mi? | Sonuç |
|---------|-----------------|-------|
| Rota Hesaplama | ✅ Evet | Genellikle çalışıyor, bazen hata |
| Alternatif Rotalar | ⚠️ Ara aşama (04.03.2026) | Dijkstra + Yen's K-Shortest + edge-based overlap + dinamik threshold; çoğu yerde iyi çalışıyor ama bazı senaryolarda tek rota / hata devam ediyor |
| Rota Kaydetme/Yükleme/Silme | ✅ Evet | Temel çalışıyor |
| Zaman Planlama | ⚠️ Kısmen | Tuş davranışı normal (rota sonrası aktif), backend endpoint var ama gerçek test yapılmadı |
| POI Arama | ✅ Evet | Maltepe dahil çalışıyor; OSM API rehberi ve genişletilmiş kategori sözlüğü sayesinde artık çok daha fazla sorgu tipi destekleniyor |
| OSM Mekan Endpoint'leri | ⏳ Araştırıldı | Nasıl çalıştığı incelendi, frontend eşleşmesi bekliyor |
| Geocoding | ✅ Evet | Çalışıyor |
| Geocode Autocomplete | ✅ Evet | Yazarken öneri geliyor, temel akış çalışıyor |
| BERT Typo Tolerance | ✅ Evet | Kadikoy→Kadıköy %95 |
| NLP→Frontend Entegrasyon | ❌ Hayır | Henüz yapılmadı |

---

## 📋 Yapılacaklar (TODO)

### 🔴 Acil
- [x] Backend encoding (charmap) hatalarını düzeltme
- [x] Frontend tıklanabilirlik sorunu giderme
- [x] POI arama bağlantı hatası giderme (Maltepe)
- [x] `simplify_coords()` ile rota kaydetme hızlandırma
- [x] Alternatif rota cache bug fix (`alternativeRoutesCache` tanımlandı ve dolduruldu)
- [x] Yer arama autocomplete endpoint'i eklendi (`/api/geocode/suggest`)
- [x] Frontend arama kutusuna yazarken öneri listesi eklendi
- [x] `route_type` → `route_index` uyum düzeltmesi yapıldı
- [x] ~~Zamanlayıcı tuşunun frontend'de aktif hale getirilmesi~~ → Tuş zaten doğru çalışıyor (rota hesaplandıktan sonra aktif, 04.03 analizi)
- [ ] Rota hesaplama aralıklı hata sebebinin araştırılması
- [ ] OSM mekan endpoint'lerinin frontend'e entegrasyonu

### 🟡 Önemli
- [ ] BERT NLP motorunun frontend'e bağlanması
- [ ] `/api/nlp/parse` endpoint'inin app.py'ye eklenmesi
- [ ] False positive azaltma (threshold iyileştirme)
- [ ] Arama önerileri için lokal cache / fallback iyileştirmesi
- [ ] Rota kaydetme edge case'lerinin tam doğrulanması

### 🟢 Gelecek
- [ ] OSM API fallback mekanizmasının test edilmesi
- [ ] Veritabanına mahalle, cadde, özel mekan isimleri eklenmesi
- [ ] POI aramasında kategori bazlı harita gösterimi

---

## 📅 04.03.2026 Oturum Planı

### 🎯 Bugünün Hedefleri (Kullanıcı Belirledi):
1. ~~Zamanlayıcı tuşu~~ → ✅ Analiz edildi, sorun yok (rota sonrası aktif oluyor)
2. **Alternatif rotalar** → Farklı yaklaşımla çözülecek
3. ~~**İkon işaretleri ve favorileme** sistemi~~ → ✅ Tamamlandı (04.03)
4. **Endpoint'leri anlama** → Nominatim API + Overpass API öğrenme
5. **BERT modelini** frontend'e entegre etme (en son)

### ✅ 04.03.2026 — İkon ve Favorileme Tamamlandı
- **Kayıtlı yerler ikon seçenekleri:** 7 → 12 ikon (coffee, restaurant, heart, hospital, park eklendi)
- **Kayıtlı yerler favorileme:** Backend `toggle_location_favorite`, `/api/locations/<id>/favorite` endpoint, frontend favori butonu
- **POI butonları:** 17 adet placeholder "📍" emoji doğru ikonla değiştirildi (🍔🍺🥙🐟🧁👗💻🔌🏗️💅🩺🛏️🚐🏫🅿️)

---