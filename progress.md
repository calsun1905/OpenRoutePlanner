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
└── günlük-rapor/                 ← Günlük notlar
    ├── 27.02.2026/
    │   ├── 27.02.2026.txt        ← Günlük notlar
    │   ├── 27.02.2026-sabah.txt  ← Oturum başı raporu
    │   └── 27.02.2026-akşam.txt  ← Oturum sonu raporu
    └── ...
```

---

## 🔄 Günlük Akış

| Olay | Hook | İşlev |
|------|------|-------|
| Proje açılınca | ✅ SessionStart | Önceki oturumu özetle, görevleri devral |
| `/gsd:resume-work` | ✅ SessionStart | Manuel oturum başı |
| `/gsd:pause-work` | ✅ SessionEnd | Manuel oturum sonu raporu |
| Her önemli adım | - | `progress/2026-02.md` güncelle |
| Kullanıcı isterse | - | Commit at |

---

## 🎯 Proje Hakkında

**Proje:** OpenRoutePlanner
**Teknoloji:** Python (Flask)
**Amaç:** Kodu tam olarak anlamak ve geliştirmek

### Ana Özellikler:
1. 🗺️ **Rota Hesaplama** - `/api/get-route`
   - Noktalar arası en kısa rotayı bulur
   - TSP algoritması ile sıralama optimize eder
   - Gerçek sokak ağlarını kullanır
   - Mesafe/süre hesaplar
   - Google Maps linki üretir

2. 🏛️ **POI Arama** - Müze, kafe vb. mekanları bulur

3. 🔎 **Yer İsmi ile Arama** - `/api/geocode` ✅ YENİ EKLENDİ
   - Yer ismini koordinata çevirir (Nominatim API)
   - Memory + SQLite cache ile hızlı
   - Rate limiting: 1 req/s
   - Frontend arama kutusu eklendi
   - Commit: 215bd40

4. 🧠 **Doğal Dil Sorgu Sistemi (Prototype → Geliştiriliyor)**
   - **Mevcut Durum:** Regex tabanlı prototype tamamlandı (`nlp_engine.py`)
   - **Sorun:** Regex sınırlı, typo tolerant değil, bağlamayı anlamıyor
   - **Plan:** Hibrit sisteme geçiş (Regex + spaCy NER)
   - **Gelecek:** Transformer/LLM entegrasyonu değerlendiriliyor
   - **Durum:** Aktif geliştirme aşamasında

### Öğrenilenler:
- ✅ Global değişkenler: `_graph_cache`, `_poi_cache` (cache mekanizması)

---

## 📝 Notlar

- **Cache:** Uygulamanın hızını artırmak için kullanılan kısa süreli hafıza
- **TSP:** Gezgin Satıcı Problemi - noktaları en mantıklı sırada ziyaret etme algoritması

## 📅 Son Güncelleme: 28.02.2026 - ~01:00

**Bu oturumda yapılanlar:**
1. ✅ **Arama Özelliği Eklendi** (geocoder.py + Frontend)
   - Nominatim API entegrasyonu
   - Yer ismi → Koordinat dönüşümü
   - Cache mekanizması
   - Frontend arama kutusu
   - Commit: 215bd40

2. ✅ **Doğal Dil Sorgu Prototype** (nlp_engine.py)
   - Regex tabanlı ayrıştırıcı
   - 6 sorgu tipi destekleniyor
   - **Sınırlama:** Typo tolerant değil, bağlamayı anlayamıyor

3. 🔄 **Mimari Kararı: Hibrit Sisteme Geçiş**
   - Regex: Basit sorgular (1ms)
   - spaCy NER: Karmaşık sorgular (50ms)
   - Gelecek: Transformer/LLM değerlendirmesi

**Sonraki adım:** spaCy entegrasyonu

---
---