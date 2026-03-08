# 📁 OpenRoutePlanner — Dosya Yapısı Rehberi

> Bu dosya, projedeki tüm dokümantasyon ve script dosyalarının konumlarını açıklar.  
> **Son güncelleme:** 08.03.2026

---

## 📂 Genel Yapı

```
OpenRoutePlanner/
├── progress.md              ← Ana ilerleme takibi (giriş noktası)
├── PROJECT_INDEX.md         ← Proje indeksi (bileşenler, API)
├── README.md                ← Proje tanıtımı
├── requirements.txt         ← Python bağımlılıkları
│
├── docs/                    ← Tüm dokümantasyon
│   ├── osm/                 ← OSM / Nominatim / Overpass rehberleri
│   ├── raporlar/            ← Fix, test ve analiz raporları
│   ├── planlar/             ← Planlar, öneriler, veritabanı dokümantasyonu
│   ├── ogretici/            ← Öğretici içerikler
│   ├── referans/            ← API referansı, komutlar
│   └── DOSYA_YAPISI.md      ← Bu dosya
│
├── scripts/                 ← Yardımcı scriptler
│   ├── fix/                 ← Encoding ve diğer fix scriptleri
│   ├── tools/               ← İndirme, test, UI araçları
│   └── debug/               ← Debug çıktıları (geçici)
│
├── backend/                 ← Flask API ve motorlar
├── frontend/                ← HTML/CSS/JS arayüz
├── progress/                ← Aylık ilerleme dosyaları
└── günlük-rapor/           ← Günlük notlar
```

---

## 📚 docs/ — Dokümantasyon

### docs/osm/ — OSM ve API Rehberleri

| Dosya | Açıklama |
|-------|----------|
| **OSM_API_REHBERI.md** | Nominatim, Overpass, Taginfo — ana rehber |
| **nominatim-osm-basit.md** | Nominatim ve OSM temel kullanım |
| **osm-kavramlari.md** | OSM kavramları (node, way, relation vb.) |
| **OSM_CATEGORIES_FULL.md** | Tam kategori listesi |
| **OSM_KAYNAKLARI.md** | OSM kaynakları ve referanslar |
| **OSM_TAG_DOGRULAMA.md** | OSM etiket doğrulama |

### docs/raporlar/ — Raporlar

| Dosya | Açıklama |
|-------|----------|
| **ALTERNATIF_ROTA_TEST_RAPORU_08_03_2026.md** | Alternatif rota test raporu |
| **GERCEK_COZUM.md** | Python cache sorunu — troubleshooting |
| **KOD_ANALIZ_RAPORU_08_03_2026.md** | Kod analiz raporu |

### docs/planlar/ — Planlar ve Öneriler

| Dosya | Açıklama |
|-------|----------|
| **PERFORMANS_OPTIMIZASYON_PLANI.md** | Performans optimizasyon planı |
| **VERITABANI_DOKUMANTASYONU.md** | Veritabanı yapısı ve kullanım |
| **oneriler-7-mart.md** | 07.03.2026 geliştirme önerileri ve yol haritası |

### docs/ogretici/ — Öğretici İçerikler

| Dosya | Açıklama |
|-------|----------|
| **incelemem.md** | app.py incelemesi ve açıklamalar |

### docs/referans/ — Referans

| Dosya | Açıklama |
|-------|----------|
| **API_ENDPOINTS.md** | API endpoint referansı |
| **komutlar.md** | GSD + SuperClaude komutları |

---

## 🔧 scripts/ — Scriptler

### scripts/fix/ — Fix Scriptleri

| Dosya | Açıklama |
|-------|----------|
| **fix_osmnx.bat** | OSMnx kurulum/güncelleme (Windows) |

### scripts/tools/ — Yardımcı Araçlar

| Dosya | Açıklama |
|-------|----------|
| **download_istanbul.py** | İstanbul harita verisi indirme |
| **download_maps.py** | Harita verisi indirme |
| **ornek_bert_kullanimi.py** | BERT kullanım örneği |
| **generate_icons.py** | İkon oluşturma |
| **update_ui.py** | UI güncelleme aracı |
| **test_100_routes.py** | 100 rota testi |
| **test_routes_fast.py** | Hızlı rota testi |

### scripts/debug/ — Debug Çıktıları

| Dosya | Açıklama |
|-------|----------|
| **debug_out.pkl** | Debug pickle çıktısı |
| **debug_queries.json** | Debug sorguları |
| **diff.patch** | Patch dosyası |

> ⚠️ `scripts/debug/` içindeki dosyalar geçicidir ve `.gitignore`'a eklenebilir.

---

## 📌 Hızlı Erişim

| Arıyorsanız | Konum |
|-------------|-------|
| OSM API nasıl kullanılır? | `docs/osm/OSM_API_REHBERI.md` |
| Alternatif rota test sonuçları | `docs/raporlar/ALTERNATIF_ROTA_TEST_RAPORU_08_03_2026.md` |
| Veritabanı yapısı | `docs/planlar/VERITABANI_DOKUMANTASYONU.md` |
| Performans planı | `docs/planlar/PERFORMANS_OPTIMIZASYON_PLANI.md` |
| Encoding fix scriptleri | `scripts/fix/` |
| Harita indirme | `scripts/tools/download_istanbul.py` |
