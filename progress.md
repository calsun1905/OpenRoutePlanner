|---|---|---|
| `backend/app.py` | Etkili degisiklik | Runtime init lazy hale getirildi, graph preload startup flag ile kontrol edildi, BERT parse trace ve runtime metric loglari eklendi, timeline/weather entegrasyonu genisletildi. |
| `backend/bert_engine.py` | Etkili degisiklik | GPU zorunlu calisma politikasi netlestirildi (`ORP_BERT_FORCE_GPU`, `ORP_BERT_STRICT_GPU`), runtime GPU metrik ciktilari eklendi, similarity/index JSON tipleri native tipe cevrildi. |
| `backend/bert_nlp_engine.py` | Etkili degisiklik | Query noise ve suffix normalizasyonu guclendirildi, span bazli trace uretimi eklendi, query-type score dagilimi loglanabilir hale getirildi, multi/single secim mantigi iyilestirildi. |
| `backend/weather_service.py` | Etkili degisiklik | OpenMeteo cagrilarina retry + exponential backoff eklendi, route weather forecast modu gelistirildi, nokta bazli advice alanlari guclendirildi. |
| `backend/weather_utils.py` | Etkili degisiklik | `get_weather_advice()` eklendi (alert_level + maddeli tavsiye cikisi). |
| `frontend/js/app.js` | Etkili degisiklik | Haritaya nokta eklenince weather widget cagrisi, rota sonrasi weather banner, timeline icinde hava/advice gorunumu, NLP parse icin `debug: true` gonderimi. |
| `frontend/index.html` | Etkili degisiklik | Weather widget ve weather banner container'lari eklendi. |
| `frontend/css/style.css` | Etkili degisiklik | Weather widget/banner ve timeline weather/advice stilleri eklendi. |
| `frontend/bert-test-lab.html` | Etkili degisiklik | Mod bazli BERT dogrulama paneli, fallback guard, ayrintili debug log paneli, tum modlari dogrulama aksiyonu eklendi. |
| `requirements.txt` | Etkili degisiklik | `brotli` ve `zstandard` pinlendi; Flask-Compress codec uyumlulugu sabitlendi. |
| `tests/test_core/test_bert_nlp_preprocessing.py` | Yeni dosya | BERT preprocessing/suffix/noise filtre testleri eklendi. |
| `docs/planlar/poi-semantic-tag-grounding-plani.md` | Yeni dosya | Hardcoded sozluk olmadan semantik POI tag grounding tasarimi yazildi. |
| `backend/tag_grounder.py` | Yeni dosya (PoC) | Overpass tabanli dinamik tag profiling + embedding matching prototipi. |
| `PROJECT_INDEX.md` | Etkili degisiklik | Proje index'i canli mimari ve endpoint haritasi ile guncellendi. |
| `CLAUDE.md` | Etkili degisiklik | Mimari, weather servis ve calisma komutlari guncellendi. |
| `progress.md` | Etkili degisiklik | Onceki oturum notlari genisletildi (bu bolum dahil). |
| `backend/geocoder.py` | Teknik olarak modified | Icerik farki yok (anlamsal degisiklik tespit edilmedi). |
| `backend/storage_db.py` | Teknik olarak modified | Icerik farki yok (anlamsal degisiklik tespit edilmedi). |
| `docs/ogretici/openmeteo-sifirdan-rehber.md` | Teknik olarak modified | Icerik farki yok (anlamsal degisiklik tespit edilmedi). |
| `docs/planlar/weather-service-akis-diyagrami.md` | Teknik olarak modified | Icerik farki yok (anlamsal degisiklik tespit edilmedi). |
| `backend/data/` | Commite dahil edildi (istenmeyen) | `app_data.db-shm` ve `app_data.db-wal` son committe repoya girdi; cleanup commit ile kaldirilmasi gerekiyor. |
| `.coverage` | Commite dahil edildi (istenmeyen) | Yerel test artifact'i son committe repoya girdi; cleanup commit ile kaldirilmasi gerekiyor. |

### B) Hava Durumu Entegrasyonu - Mevcut Durum

- Haritada bir noktaya tiklandiginda artik o koordinatin hava durumu alinabiliyor.
- UI tarafinda su an net ve aktif gorunen ana metrik sicaklik (ve temel emoji/aciklama) akisi.
- Backend tarafinda diger alanlar (yagis, ruzgar, olasilik, advice) mevcut; ancak kullaniciya sunum kapsaminda genisletme gerektiren kisimlar var.
- Sonraki adim: canli soru-cevap akisi veya detay panel ile diger hava metriklerinin kullaniciya kontrollu sunulmasi.

### C) Semantic POI (Mekan) Cozum Yonu

- Sorun: `cami`, `stadyum`, `okul`, `kantin` gibi kelimeler bazen yer ismi gibi algilanabiliyor.
- Bu oturumda cozum dosyasi eklendi:
  - `docs/planlar/poi-semantic-tag-grounding-plani.md`
- Hedef yon:
  - Lokasyon ve POI konseptini ayristir.
  - Concept -> OSM tag grounding adimini BERT semantic eslesme ile yap.
  - Overpass'i sadece final sonucu cekmekte kullan.

### D) Arayuz ve Turkce Mekan Listesi Notu (Plan)

- Arayuzde bir sonraki fazda POI kategori/etiketlerinin Turkceye cevrilmis ve net bir liste halinde sunulmasi planlandi.
- Beklenen kullanim:
  - Kullanici: "Kucukyali'da cami ariyorum"
  - Sistem: lokasyonu ayristir + POI tipini dogru tag'a bagla + ilgili camileri getir.
- Bu konu hem UX hem de semantic grounding implementasyonu ile birlikte ilerletilecek.

### E) Gerceklesen Commitler (2026-03-11)

Planlanan paketleme uygulanmistir. Bu oturumda atilan commitler:

1. `8124fdf` - `feat: BERT gozlemlenebilirlik ve parse akisi guclendirildi`
   - `backend/app.py`, `backend/bert_engine.py`, `backend/bert_nlp_engine.py`, `frontend/bert-test-lab.html`, `tests/test_core/test_bert_nlp_preprocessing.py`, `backend/tag_grounder.py`
2. `2659fea` - `feat: weather servis dayanikliligi ve arayuz entegrasyonu gelistirildi`
   - `backend/weather_service.py`, `backend/weather_utils.py`, `frontend/index.html`, `frontend/css/style.css`, `frontend/js/app.js`
3. `51ee5bf` - `chore: docs ve kalan workspace degisiklikleri tek committe toplandi`
   - `PROJECT_INDEX.md`, `progress.md`, `docs/planlar/poi-semantic-tag-grounding-plani.md`, `gunluk-rapor/11.03.2026/11.03.2026.txt`, `CLAUDE.md`, `requirements.txt`, `.coverage`, `backend/data/app_data.db-shm`, `backend/data/app_data.db-wal`

Not: Son committe gecici artifact dosyalari (.coverage, db-shm, db-wal) da girdigi icin bir sonraki adimda repo cleanup commit'i planlanmali.

## 2026-03-10 Guncel Not

**Hava Durumu Servisi Faz 1 TAMAMLANDI!** ✅

### 2026-03-10 Oturumu - Hava Durumu Faz 1 Tamamlandi

| # | Degisiklik | Dosya | Durum |
|---|-----------|-------|-------|
| 1 | **Hava durumu tasarim belgesi** | `docs/planlar/weather-service-design.md` | ✅ Yeni dosya |
| 2 | **weather_utils.py modulu** | `backend/weather_utils.py` | ✅ Yeni dosya |
| 3 | **weather_service.py modulu** | `backend/weather_service.py` | ✅ Yeni dosya |
| 4 | **API endpoint'leri eklendi** | `backend/app.py` | ✅ Guncellendi |
| 5 | **Test script'i yazildi** | `backend/test_weather_service.py` | ✅ Yeni dosya |
| 6 | **Tum testler gecti** | Test Suite | ✅ 11/11 PASS |

### Yeni Dosyalar
- `docs/planlar/weather-service-design.md` - Kapsamli tasarim belgesi
- `backend/weather_utils.py` - WMO kodlari, validasyon, cache utilities
- `backend/weather_service.py` - OpenMeteo API entegrasyonu
- `backend/test_weather_service.py` - Unit + integration test suite

### Yeni Endpoint'ler
- `GET /api/weather?lat={lat}&lon={lon}` - Guencel hava durumu
- `GET /api/weather/forecast?lat={lat}&lon={lon}&hours={hours}` - Saatlik forecast
- `POST /api/weather/check-route` - Rota boyunca hava kontrolu
- `GET /api/weather/status` - Servis durumu
- `GET /api/weather/health` - Saglik kontrolu
- `POST /api/weather/clear-cache` - Cache temizleme

### Test Sonuclari
```
[PASS] Coordinate Validation (8/8)
[PASS] Hours Validation (6/6)
[PASS] Weather Code Parsing (7/7)
[PASS] Weather Emoji (5/5)
[PASS] Cache Key Building (3/3)
[PASS] Temperature Formatting (3/3)
[PASS] Weather Alerts (4/4)
[PASS] Activity Suggestions (3/3)
[PASS] Service Import (1/1)
[PASS] Service Status (3/3)
[PASS] Cache Operations (4/4)
---
TOTAL: 11/11 tests passed
```

### Ozellikler
- OpenMeteo API entegrasyonu (API key gerektirmiyor)
- Memory cache (900 saniye TTL)
- WMO weather code parsing (0-99 arasi 46 kod)
- Hava durumu uyarilari (yagmur, sicaklik, ruzgar, sis)
- Aktivite onerileri (hava durumuna bagli)
- Heat index ve wind chill hesaplamalari

### Bir Sonraki Adimlar- **Hava Durumu & Senkronizasyon:** Backend veri şeması (`temperature`, `weather_emoji`, `weather_tr`, `advice`) frontend ile tam uyumlu hale getirildi. Zaman çizelgesi için genel rota özet banner'ı (`weather-alert-banner`) eklendi. Tavsiye (advice) sistemi zenginleştirildi. ✅detay metrik paneli acik.
- Rota kararlarina hava etkisini baglama - ilk seviyede uyarilar eklendi, karar skoru etkisi ileri fazda.

### Ogreti Dosyalari (2026-03-10)
- `docs/ogretici/openmeteo_ornek_kullanim.py` - OpenMeteo API ornek kullanim (baslangic seviyesi)
- `docs/ogretici/openmeteo-sifirdan-rehber.md` - Sifirdan baglanti rehberi
- **Ogreti sablonu:** progress.md icinde "Ogreti Yazim Sablonu" bolumu - yeni ogretiler bu formatta yazilacak

---

## 2026-03-09 Arsiv Not

- Hava durumu entegrasyon plani gecici oturum kaydindan geri alindi ve repo icine tasindi: `docs/planlar/hava-durumu-entegrasyon-plani.md`
- BERT gelistirme akisi ayri plan dokumani olarak eklendi: `docs/planlar/bert-gelistirme-akisi.md`
- BERT tarafinda yeni yon: `normalize -> mention detection -> candidate retrieval -> place linking -> slot filling -> intent merge`
- Regex ana cozum degil; sadece dar fallback olarak kalacak.

### Guncel Odak

1. Hava durumu Faz 2: Timeline entegrasyonu
2. BERT mention/linking/slot filling kalitesini artirmak
3. OSM-first ve local cache mantigini kontrollu sekilde genisletmek

> 📂 Detayli planlar: `docs/planlar/`
> 📝 Son oturum raporu: `günlük-rapor/09.03.2026/09.03.2026.txt`

---

## 📚 Öğretici Yazım Şablonu

**Kullanıcı için öğretici yazıldığında aşağıdaki şablon aynen uygulanmalıdır.**

### Şablon Kuralları

1. **Dosya başlığı:** Konu adı + "(Başlangıç Seviyesi)" veya uygun seviye
2. **Docstring:** Ne yaptığını, nasıl çalıştırılacağını, gereksinimleri açıkla
3. **Adım numaraları:** `# ADIM 1:`, `# ADIM 2:` vb. ile bölümler
4. **Ayırıcı çizgiler:** `# =============================================================================` ile her bölümü ayır
5. **Her satırın yanında Türkçe açıklama:** Ne yaptığını, neden yaptığını yaz
6. **Değişken seçimi:** Kullanıcı hangi verileri görecek, önce belirle
7. **Konum/parametre:** Koordinatlar ve parametreler açıklamalı olsun
8. **Bağlantı kısmı:** `requests.get()` ne yapıyor, timeout neden var
9. **Cevap kontrolü:** `status_code` ne anlama geliyor
10. **Veri çıkarma:** Hangi alan nereden alınıyor
11. **Hata yakalama:** `try/except` ile ConnectionError, Timeout, Exception açıklamalı

### Örnek Format (Referans)

```
# =============================================================================
# ADIM 1: Hangi verileri istediğimizi belirliyoruz (3 değişken)
# =============================================================================
# OpenMeteo'dan 3 farklı veri isteyeceğiz:
# 1. Sıcaklık (temperature_2m) - Kaç derece?
# 2. Nem (relative_humidity_2m) - Hava ne kadar nemli? (%)
# 3. Hava durumu kodu (weather_code) - Açık mı, yağmurlu mu?

istek_edilen_veriler = "temperature_2m,relative_humidity_2m,weather_code"

# =============================================================================
# ADIM 2: Hangi konum için veri istiyoruz? (Koordinatlar)
# =============================================================================
# Enlem ve boylam = Dünya üzerinde bir noktanın adresi (sayılarla)

enlem = 41.0      # latitude  - Kuzey/güney konumu
boylam = 29.0     # longitude - Doğu/batı konumu

# =============================================================================
# ADIM 4: Bağlantı kuruyoruz ve istek atıyoruz
# =============================================================================
# requests.get() = İnternet üzerinden sunucuya "Bu verileri ver" diye sorar
# timeout=10 = 10 saniye içinde cevap gelmezse vazgeç

cevap = requests.get(api_adresi, params=parametreler, timeout=10)
```

### Referans Dosyalar

- **Örnek:** `docs/ogretici/openmeteo_ornek_kullanim.py`
- **Rehber:** `docs/ogretici/openmeteo-sifirdan-rehber.md`

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
├── PROJECT_INDEX.md              ← Projenin tüm bileşenleri için indeks dosyası
├── docs/                         ← Dokümantasyon (OSM, raporlar, planlar, referans)
│   ├── osm/                      ← OSM API rehberleri
│   ├── raporlar/                 ← Fix ve test raporları
│   ├── planlar/                  ← Planlar, öneriler (oneriler-7-mart.md vb.)
│   ├── ogretici/                 ← Öğretici içerikler
│   ├── referans/                 ← API, komutlar (komutlar.md)
│   └── DOSYA_YAPISI.md           ← Dosya yapısı rehberi
├── scripts/                      ← Yardımcı scriptler
│   ├── fix/                      ← Encoding ve diğer fix scriptleri
│   ├── tools/                    ← İndirme, test, UI araçları
│   └── debug/                    ← Debug çıktıları
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

2. 🔀 **Alternatif Rotalar** - `/api/get-alternative-routes` 🔄 v3.0 UÇTAN UCA TEST EDİLDİ ✅
   - **v3.0 Strateji:** Dijkstra (Rota 1) → Via-Node (Rota 2, 3) → Gövde-only Penalty (yedek)
   - Via-Node: Ana rotadan uzak büyük kavşaklardan geçen rotalar (Google Maps/OSRM tarzı)
   - Asimetrik overlap: "Yeni rotanın % kaçı eskiyle aynı?" (eski Jaccard formülü düzeltildi)
   - Gövde-only penalty: Baş/son %10'a dokunmadan sadece gövdeye ceza
   - ✅ Disjoint paths'in OSM çıkmaz sokak problemi çözüldü (Via-Node ile değiştirildi)
   - ✅ Penalty zikzak problemi çözüldü (gövde-only + her iterasyonda yeniden oluşturma)
   - ✅ Jaccard alt küme yanılgısı düzeltildi (asimetrik formül)
   - ✅ **Uçtan uca test TAMAMLANDI** (08.03.2026) - 17 edge case testi, %82 başarı
   - ⚠️ Bilinen sorunlar: Çok kısa mesafelerde (< 100m) yüksek overlap, timeout sınırı
   - Test raporu: `docs/raporlar/ALTERNATIF_ROTA_TEST_RAPORU_08_03_2026.md`
   - Konfigürasyon: `backend/route_config.py` (31 sabit, referans amaçlı)

3. 💾 **Rota Kaydetme/Yükleme** ✅ SQLite (08.03.2026)
   - **Depolama:** `backend/data/app_data.db` (SQLite) — routes + locations tabloları
   - Rota kaydetme, yükleme, silme
   - Favori sistemi (yıldızlama)
   - Rota arama ve filtreleme
   - JSON → SQLite otomatik migrasyon (mevcut veriler taşınır)
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
   - ⚠️ Guncel eksikler:
     - `normalize -> mention detection -> candidate retrieval -> place linking -> slot filling` ayristirma refactor'u tamamlanmadi
     - Origin/destination role atama kalitesi ve false positive azaltma iyilestirmesi gerekli
     - OSM dynamic retrieval + local cache dengesinin davranis testleri eksik
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

## 📅 Arsiv Kaydi: 08.03.2026 - Alternatif Rota Motoru v3.0 Edge Case Testleri (Uçtan Uca)

---

## 🚀 08.03.2026 Oturumu - Alternatif Rota Motoru v3.0 Edge Case Testleri

### 🎯 Bu Oturumda Yapılanlar

| # | Değişiklik | Dosya | Durum |
|---|-----------|-------|-------|
| 1 | **Alternatif rota motoru v3.0 uçtan uca test** | Backend API | ✅ Tamamlandı |
| 2 | **17 edge case test senaryosu** | Test Suite | ✅ Tamamlandı |
| 3 | **Overlap analizi** | Python Test Script | ✅ Tamamlandı |
| 4 | **Test raporu oluşturuldu** | `ALTERNATIF_ROTA_TEST_RAPORU_08_03_2026.md` | ✅ Yeni dosya |
| 5 | **Günlük rapor güncellendi** | `günlük-rapor/08.03.2026/` | ✅ Güncellendi |
| 6 | **Progress.md güncellendi** | `progress.md` | ✅ Güncellendi |

### 🧪 Test Sonuçları Özeti

**Toplam Test:** 17
**Başarılı:** 14 (%82)
**Sorunlu:** 3 (%18)

#### ✅ Başarılı Test Kategorileri:
- Temel mesafe testleri (7/7) - 500m'den 25km'ye
- Ek edge case testleri (4/4) - Dar sokaklar, boğaz kenarı
- Çıkma sokak bölgeleri (1/1) - Balat-Fener

#### ⚠️ Sorunlu Testler:
1. **Çok kısa mesafe (< 100m):** %100 overlap - OSM graph sınırları
2. **Timeout:** Boğazköy → Yeniköy (~20km) - 60 saniye yetmedi

### 📊 Performans Analizi

| Mesafe Aralığı | Ortalama Overlap | Değerlendirme |
|----------------|------------------|---------------|
| 50-100m | %90-100 | ⚠️ SORUNLU |
| 100-500m | %30-70 | ✅ KABUL EDİLEBİLİR |
| 500m-1km | %15-30 | ✅ İYİ |
| 1km-5km | %5-25 | ✅ ÇOK İYİ |
| 5km+ | %5-15 | ✅ ÇOK İYİ |

### ✅ Önemli Bulgular

1. **Via-Node Sistemi Başarılı:**
   - Boğaz geçişi senaryoları çalışıyor
   - Orta/uzun mesafelerde overlap %5-30 aralığında

2. **Asimetrik Overlap Formülü Doğru:**
   - Jaccard alt küme yanılgısı düzeltilmiş

3. **Gövde-Only Penalty Etkili:**
   - Zikzak problemi azalmış
   - Rotalar daha doğal

### 🔍 Tespit Edilen Sorunlar ve Öneriler

1. **Timeout Ayarı:**
   - 60 → 120 saniyeye çıkarılmalı
   - Async işlem düşünülebilir

2. **Kısa Mesafe Bildirimi:**
   - 100m'den kısa rotalarda kullanıcı bilgilendirilmeli

3. **Graph Preloading:**
   - Yüksek hit bölgeleri için önbellekleme

---

## 📅 Arsiv Kaydi: 08.03.2026 - Arama UX, Route Engine Düzeltmeleri ve Dokümantasyon

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
| 6 | **Geliştirme önerileri ve yol haritası yazıldı** | `docs/planlar/oneriler-7-mart.md` | ✅ Yeni dosya |
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

**8. `docs/planlar/oneriler-7-mart.md`**
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
| 3 | BERT `/api/nlp/parse` endpoint | 07.03 oturumunda eklenmemisti (09.03 itibariyla eklendi) | 🔴 Yüksek |
| 4 | Frontend BERT entegrasyonu | 07.03 oturumunda bagli degildi (09.03 itibariyla temel entegrasyon var) | 🔴 Yüksek |
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

### 6. BERT NLP Motoru - ⚠️ Temel Entegrasyon Var, Kalite Refactor Bekliyor
| Sorun | Detay | Önem |
|-------|-------|------|
| Pipeline ayrıştırma eksik | `normalize -> mention detection -> candidate retrieval -> place linking -> slot filling` tam ayri katmanlara gecmedi | 🔴 Yüksek |
| Slot atama hatalari | Origin/destination rol atamasi bazi sorgularda yanlis eslesebiliyor | 🔴 Yüksek |
| False positive | Bazi kelimeleri yanlis yer ismi olarak algiliyor | 🟡 Orta |
| Oncelik notu | Sonraki buyuk adim BERT kalite/refactor fazini tamamlamak | 🟡 Orta |

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
| NLP→Frontend Entegrasyon | ✅ Evet | AI panel + parse akisi bagli; kalite ve pipeline refactor calismasi bekliyor |

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
- [x] **Alternatif Rota Motoru v3.0 uçtan uca test** (08.03.2026) ✅ 17 edge case testi tamamlandı
- [ ] Rota hesaplama aralıklı hata sebebinin araştırılması
- [ ] OSM mekan endpoint'lerinin frontend'e entegrasyonu

### 🟡 Önemli
- [x] BERT NLP motorunun frontend'e bağlanması (AI panel + parse akışı eklendi)
- [x] `/api/nlp/parse` ve `/api/nlp/status` endpoint'lerinin app.py'ye eklenmesi
- [ ] BERT pipeline'in `normalize -> mention detection -> candidate retrieval -> place linking -> slot filling` akışına tam ayrıştırılması
- [x] Hava durumu entegrasyonu Faz 1: `weather_service.py`, `weather_utils.py`, temel endpoint'ler
- [ ] False positive azaltma (threshold iyileştirme)
- [ ] Arama önerileri için lokal cache / fallback iyileştirmesi
- [ ] Rota kaydetme edge case'lerinin tam doğrulanması
- [ ] Repo cleanup: `.coverage` ve `backend/data/*.db-shm`, `backend/data/*.db-wal` dosyalarini takipten cikar ve `.gitignore`a ekle

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
---

## 2026-03-08 - Son Commit Sonrasi Konsolidasyon (Canli Envanter)

### Durum Ozeti
- Bu kayit hazirlanirken `git status` ciktisinda **24 degisen kayit** var.
- Dagilim: **15 modified + 9 untracked**.
- Not: Onceki hedeften (23) farkli olarak su an bir ekstra untracked kayit var.

### Degisen Dosyalar (Anlik)
- M `.gitignore`
- M `PROJECT_INDEX.md`
- M `backend/app.py`
- M `backend/bert_nlp_engine.py`
- M `backend/cache/geocodes.db`
- M `backend/geocoder.py`
- M `backend/graph_manager.py`
- M `backend/location_storage.py`
- M `backend/nlp_engine.py`
- M `backend/route_engine.py`
- M `backend/route_storage.py`
- M `docs/DOSYA_YAPISI.md`
- M `frontend/css/style.css`
- M `frontend/index.html`
- M `progress.md`
- ?? `backend/local_places.py`
- ?? `backend/storage_db.py`
- ?? `frontend/test_encoding.html`
- ?? `frontend/test_timeline.html`
- ?? `günlük-rapor/08.03.2026/08.03.2026.txt`
- ?? `scripts/fix/fix_backend.py`
- ?? `scripts/fix/fix_emoji.py`
- ?? `scripts/tools/deep_scan.py`
- ?? `scripts/tools/scan_encoding.py`

### Bu Paket Icinde Dogrulanan Ana Isler
1. Veri katmani JSON -> SQLite gecisi:
   - `route_storage.py` ve `location_storage.py` SQLite tabanli hale getirildi.
   - JSON veriler icin migrate mekanizmasi eklendi.
2. Yeni DB altyapisi:
   - `storage_db.py` eklendi (schema, index, PRAGMA, checkpoint yardimcisi).
   - `ensure_db` surec basina bir kez calisacak sekilde optimize edildi.
3. Geocoder performans ve temizlik:
   - `geocoder.py` icinde PRAGMA ayarlari guclendirildi.
   - `purge_old_geocodes(days=90)` eklendi.
   - TTL delete icin timestamp indexleri eklendi.
4. Runtime init akisi:
   - `app.py` icinde startup init (ensure_db + checkpoint + geocode purge) eklendi.
5. Rota cizim kalitesi:
   - `route_engine.py` edge geometry bazli koordinat cikarma kullanacak sekilde guncellendi.
6. NLP ve UI genislemeleri:
   - `app.py` tarafinda NLP endpointleri ve status endpointi eklendi.
   - `frontend/index.html` + `frontend/css/style.css` icinde AI Asistan alani ve stilleri eklendi.
7. Dokumantasyon/yapi guncellemeleri:
   - `PROJECT_INDEX.md`, `docs/DOSYA_YAPISI.md`, `.gitignore` guncellendi.

### Bilinen Sorunlar / Riskler (Acil Takip)
1. **Encoding/Mojibake riski devam ediyor:**
   - `backend/app.py`, `backend/geocoder.py`, `progress.md`, gunluk rapor ve bazi scriptlerde bozuk karakter izi var.
2. **NLP regex regresyon riski (`backend/nlp_engine.py`):**
   - Bazi patternlerde soru isareti opsiyonel yerine zorunlu hale gelmis olabilir.
3. **Test dosyalari guvenilir degil:**
   - `frontend/test_encoding.html` ve `scripts/fix/*` dosyalari da bozuk karakter iceriyor.
4. **Calisma ortami farki:**
   - Bu ortamda `flask` modulu olmadigi icin import tabanli canli endpoint smoke testi yapilamadi.

### Henuz Yapilmayanlar
- Faz 3 (preload region) tasarimi/uygulamasi.
- Tum kod tabaninda tek seferlik, kontrollu encoding normalize turu.
- NLP regex davranisinin testlerle geri dogrulanmasi.
- Frontend test dosyalarinin ya duzeltilmesi ya da repo disina alinmasi.

### Commit Plani Icin Not
- Bu envanter, commitleri alanlara bolmek icin hazirlandi.
- Ayrim onerisi: `db+storage`, `routing`, `nlp+ui`, `docs+scripts`, `encoding cleanup`.

## 2026-03-11 - BERT Gelisim Yolu (Iki Yaklasim Karari)

Bu oturumda BERT tarafi icin iki teknik yol netlestirildi ve hibrit gecis stratejisi kabul edildi.

### Yaklasim-1 (Kisa Vade): Sablon Veri Setini Buyutme
- Intent sablonlari koddan ayri bir veri dosyasina tasinacak (JSONL/YAML).
- 4 intent (poi/route/single/multi) icin genis ornek havuzu tutulacak.
- Karar tek sablona gore degil, kategori bazli ortalama/centroid + margin ile verilecek.
- Hard negative ornekler eklenecek.

### Yaklasim-2 (Orta-Uzun Vade): Egitimli Model
- BERT embedding uzerine intent classifier egitilecek.
- Sonraki fazda BIO tabanli slot extraction (LOC/POI_TYPE) eklenecek.
- Sablon mekanizmasi fallback/debug amacli minimum seviyede tutulacak.

### Kabul Edilen Yol: Hibrit Gecis
1. Simdi Yaklasim-1 (hizli ve guvenli iyilesme)
2. Paralelde etiketli veri biriktirme
3. Esik asildiginda Yaklasim-2'ye kademeli gecis

### Sonraki Oturum Icin Net Aksiyonlar
- [ ] `backend/bert_nlp_engine.py` icindeki intent sablonlarini dosya tabanli hale getir
- [ ] `docs/planlar/` altina intent dataset formati ve etiketleme kurali ekle
- [ ] Kategori-centroid + margin skorlamasini implement et
- [ ] Hard negative mini seti olustur ve testlere ekle
- [ ] Intent accuracy / confusion matrix raporlamasini ekle
