# OpenRoutePlanner - Son Commit Analizi (11.03.2026)

## 📝 Son 10 Commit Özeti (Güncel)

### 🔥 1. 51ee5bf - chore: docs ve kalan workspace değişiklikleri (EN SON)
**Tarih:** ~11.03.2026
**İçerik:** Docs, index ve kalan workspace değişiklikleri tek committe toplandı.

---

### 2. 2659fea - feat: weather servis dayanıklılığı ve arayüz entegrasyonu
**İçerik:** 
- `weather_service.py` → retry + exponential backoff
- `weather_utils.py` → `get_weather_advice()` (alert_level + maddeli tavsiye)
- `frontend/index.html` → weather widget + banner container'ları
- `frontend/css/style.css` → weather widget/banner/timeline stilleri
- `frontend/js/app.js` → weather widget bağlantısı, rota sonrası banner, timeline kartlarında advice

---

### 3. 8124fdf - feat: BERT gözlemlenebilirlik ve parse akışı güçlendirildi
**İçerik:**
- `bert_engine.py` → GPU politikası netleştirildi (`ORP_BERT_FORCE_GPU`, `ORP_BERT_STRICT_GPU`)
- `bert_nlp_engine.py` → trace tabanlı parse altyapısı, query-type score dağılımı, span kabul/ret detayları
- `app.py` → BERT parse trace + runtime metric loglama

---

### 4. ac06503 - chore: geliştirme yardımcı dosyaları ve operasyon scriptleri
**İçerik:** Yardımcı araçlar, scriptler, operasyon dosyaları eklendi.

---

### 5. 30539ec - feat: frontend autocomplete akışı ve NLP API testleri
**İçerik:** Frontend'de autocomplete + NLP API test akışı güncellendi.

---

### 6. 30f5d9e - perf: route engine ve geocoder tarafında davranış iyileştirmeleri
**İçerik:** Route engine geometri iyileştirmeleri, geocoder TTL purge + timestamp indexleri.

---

### 7. 26493b5 - feat: BERT test lab, akış şeması ve diyagram görseli
**İçerik:** `frontend/bert-test-lab.html` → mod bazlı doğrulama paneli, detaylı debug log paneli.

---

### 8. 8aeb011 - feat: BERT NLP motoru, gold evaluator ve benchmark raporları
**İçerik:** BERT gold evaluation scripti, benchmark raporları (`docs/raporlar/`).

---

### 9. 05170fb - feat: hava durumu servisi ve OpenMeteo dokümantasyon paketi
**İçerik:** `weather_service.py`, `weather_utils.py` ilk versiyonları. OpenMeteo dökümantasyonu.

---

### 10. 72ce533 - feat: API runtime, cache altyapısı ve depolama katmanı
**İçerik:** `storage_db.py`, SQLite altyapısı, `route_storage.py` + `location_storage.py` JSON→SQLite geçişi.

---

## 📊 11.03.2026 İtibariyle Toplam Commit Sayısı
Proje başından bu yana ~50 commit.

## 🎯 Güncel Durum (11.03.2026)

### ✅ Tamamlanan (Son Oturumlardan)
- Alternatif rota motoru v3.0 (Via-Node + Gövde-only Penalty) → uçtan uca test edildi
- BERT test lab (bert-test-lab.html) → debug ve validation paneli
- Weather service MVP (weather_service.py + weather_utils.py)
- Weather UI entegrasyonu (widget, banner, timeline)
- BERT trace/metrics gözlemlenebilirlik
- SQLite storage altyapısı (route_storage + location_storage)
- NLP endpoint (`/api/nlp/parse`) eklenmiş gibi görünüyor
- Frontend NLP/AI paneli

### ⏳ Bekleyen
- Semantic POI grounding (lokasyon + concept ayrımı, `tag_grounder.py` PoC mevcut)
- Weather → Timeline entegrasyonu (hava bazlı akıllı öneriler)
- BERT mention/linking/slot filling ayrıştırması (retrieval/linking odaklı)
- Encoding normalizasyonu (bazı dosyalarda mojibake hala var)
- Kısa mesafede yüksek overlap sorunu için UI bildirimi
- Timeout iyileştirmesi (60 → 120 saniye)

### 📌 Önemli Notlar
- **Commit Planı (11.03.2026 raporu):**
  - Commit-1: weather service + weather UI
  - Commit-2: BERT trace/metrics + NLP kalite + test
  - Commit-3: docs/index/progress + semantic POI plan
  - Commit-4: dependency/ortam sabitleme (requirements)
- **Son büyük değişiklik:** Weather UI + BERT trace
- **Test durumu:** Alternatif rota v3.0 test edildi (%82 başarılı)
- **Yeni dosyalar:** `weather_service.py`, `weather_utils.py`, `storage_db.py`, `tag_grounder.py`, `bert-test-lab.html`, `spatial_index.py`, `cache_manager.py`, `logging_config.py`, `nlp_engine.py`, `response_utils.py`
