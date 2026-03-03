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

2. 🔀 **Alternatif Rotalar** - `/api/get-alternative-routes` ✅ YENİ
   - En Kısa Rota (shortest) - Minimum mesafe
   - En Hızlı Rota (fastest) - Büyük yolları tercih eder
   - Dengeli Rota (balanced) - Mesafe ve hız arası denge
   - ⚠️ Bilinen sorunlar:
     - Alternatif seçildiğinde önceki rota haritada kalıyor
     - Seçim sonrası alternatiflerin güncellenmesi gerekiyor
   - Commit: 27af924

3. 💾 **Rota Kaydetme/Yükleme** ✅ YENİ
   - Rota kaydetme, yükleme, silme
   - Favori sistemi (yıldızlama)
   - Rota arama ve filtreleme
   - ⚠️ Bilinen sorunlar:
     - Kaydetme işlemi çok uzun sürüyor (yavaşlık)
     - "Önce rotayı hesaplayın" uyarısı hatalı çalışıyor (rota zaten hesaplanmış)
   - Commit: bb19215

4. ⏰ **Zaman Bazlı Planlama** ✅ YENİ (Prototip)
   - Başlangıç saati seçimi
   - Varış/ayrılış saatleri hesaplama
   - Ziyaret ve yürüyüş süreleri
   - Timeline görünümü
   - ⚠️ Prototip aşamasında, tam test edilmedi
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

## 📅 Son Güncelleme: 03.03.2026 - ~12:45

---

## 🐛 Bilinen Sorunlar ve Kötü Çalışan Yerler

### 1. Alternatif Rotalar (Commit: 27af924)
| Sorun | Detay | Önem |
|-------|-------|------|
| Önceki rota kalıyor | Bir alternatif rota seçildiğinde önceki rota haritadan silinmiyor, yeni rota üzerine ekleniyor | 🔴 Yüksek |
| Alternatifler güncellenmiyor | Yeni bir rota seçtiğinde alternatif rotaların yeniden hesaplanması gerekiyor ama eskiler gösteriliyor | 🔴 Yüksek |
| Kayıtlı rota gösterimi | Daha önce kaydettiğin rotayı yüklediğinde alternatifler eski rotayı gösteriyor | 🟡 Orta |

### 2. Rota Kaydetme/Yükleme (Commit: bb19215)
| Sorun | Detay | Önem |
|-------|-------|------|
| Çok yavaş | İki noktaya rota ekleyip kaydedebiliyorsun ama kaydetme işlemi çok uzun sürüyor | 🔴 Yüksek |
| Hatalı uyarı | Rota zaten hesaplanmış olmasına rağmen "Önce rotayı hesaplayın" diyor | 🔴 Yüksek |
| Hesaplama kontrolü | Rota hesaplanıp hesaplanmadığını doğru kontrol edemiyor | 🟡 Orta |

### 3. Zaman Bazlı Planlama (Commit: 0fc237c)
| Sorun | Detay | Önem |
|-------|-------|------|
| Test edilmedi | Prototip olarak eklendi, hiç test edilmedi | 🔴 Yüksek |
| Doğruluk bilinmiyor | Zaman hesaplamalarının doğruluğu bilinmiyor | 🟡 Orta |

### 4. BERT NLP Motoru (Commit: 951d0db)
| Sorun | Detay | Önem |
|-------|-------|------|
| API endpoint yok | /api/nlp/parse endpoint'i app.py'ye eklenmedi, motor çalışıyor ama dışarıdan erişilemiyor | 🔴 Yüksek |
| Frontend bağlantısı yok | BERT motorunu kullanan hiçbir frontend arayüzü yok | 🔴 Yüksek |
| False positive | Bazı kelimeleri yanlışlıkla yer ismi olarak algılıyor, eşik (threshold) iyileştirmesi gerekli | 🟡 Orta |
| OSM fallback test edilmedi | Bilinmeyen yerlerde OSM API'ye düşme mantığı yazıldı ama gerçek ortamda test edilmedi | 🟡 Orta |

---

## 🧪 Test Durumu

| Özellik | Test Edildi mi? | Sonuç |
|---------|-----------------|-------|
| Rota Hesaplama (temel) | ✅ Evet | Çalışıyor |
| Alternatif Rotalar | ⚠️ Kısmen | Backend çalışıyor, frontend sorunlu |
| Rota Kaydetme | ⚠️ Kısmen | Kaydediyor ama yavaş + hatalı uyarılar |
| Zaman Planlama | ❌ Hayır | Hiç test edilmedi |
| BERT Typo Tolerance | ✅ Evet | Çalışıyor (Kadikoy→Kadıköy %95) |
| BERT Sorgu Sınıflandırma | ✅ Evet | route/poi/multi/single çalışıyor |
| BERT Yer Çıkarma | ⚠️ Kısmen | Temel çalışıyor, false positive var |
| OSM POI Sözlüğü | ✅ Evet | 167 kelime eşleştirmesi çalışıyor |
| OSM Overpass API | ✅ Evet | Kadıköy tekelleri test edildi, çalışıyor |
| NLP→Frontend Entegrasyon | ❌ Hayır | Henüz yapılmadı |

---

## 📋 Yapılacaklar (TODO)

### 🔴 Acil (Mevcut özelliklerin düzeltilmesi)
- [ ] Alternatif rota seçildiğinde önceki rotanın haritadan silinmesi
- [ ] Rota seçimi sonrası alternatiflerin güncellenmesi
- [ ] Rota kaydetme hız sorununun çözülmesi
- [ ] "Önce rotayı hesaplayın" hatalı uyarısının düzeltilmesi
- [ ] Zaman Bazlı Planlama modülünün test edilmesi

### 🟡 Önemli (Yeni entegrasyonlar)
- [ ] /api/nlp/parse endpoint'inin app.py'ye eklenmesi
- [ ] BERT NLP motorunun frontend'e bağlanması
- [ ] POI arama için OSM sözlüğünün BERT ile entegrasyonu
- [ ] False positive azaltma (threshold iyileştirme)
- [ ] OSM API fallback mekanizmasının gerçek ortamda test edilmesi

### 🟢 Gelecek (Geliştirme)
- [ ] Veritabanına mahalle, cadde, özel mekan isimleri eklenmesi
- [ ] Harita üzerinde gerçek rota çizimi ve koordinat işlemleri
- [ ] Enlem/boylam (lat/lon) çekme sisteminin tamamlanması
- [ ] POI aramasında kategori bazlı harita gösterimi

---