# BERT + Türkçe Morfoloji + Sözlük + Overpass Entegrasyonu
## POI/Lokasyon Çözümleme Spec Kit (v1.1)

**Durum:** Tasarım Onayı Bekliyor (v1.1 kritik boşluklar işlendi)  
**Proje:** OpenRoutePlanner  
**Tarih:** 2026-03-15  
**Sahiplik:** NLP/Backend  
**İlgili Modüller:** `backend/bert_nlp_engine.py`, `backend/nlp_engine.py`, `backend/graph_manager.py`, `backend/osm_poi_dictionary.py` (yeni/genişletilmiş), `backend/app.py`

---

## 1) Problem Tanımı

Uygulama kullanıcıdan Türkçe doğal cümle alıyor:
- “Malatya’da pilavcı arıyorum”
- “Küçükyalıda güzel pilavcılar önerir misin?”
- “Yakınımda çiğ köfteci var mı?”

Ama mevcut akışta şu riskler var:
1. Ekli kelimelerden kök doğru çıkarılamıyor.
2. Yanlış kök kesimi (over-stemming) ile yanlış POI konseptine gidilebiliyor.
3. Yazım hatası/latinize yazım (`pilavci`) gibi varyasyonlar kaçabiliyor.
4. Lokasyon ve POI bazen karışabiliyor.
5. Overpass’a yanlış/çok dar/çok geniş tag atılabiliyor.

**Hedef:** Türkçe cümleden doğru lokasyon + doğru POI konsepti çıkarıp, güvenli ve açıklanabilir şekilde Overpass sorgu planı üretmek.

---

## 2) Hedefler ve Hedef Dışı

### 2.1 Hedefler
- Türkçe ekli yüzey formları güvenli normalize etmek.
- POI için kanonik konsept çözümlemek.
- Lokasyon ve POI’yi ayrı pipeline’da ele almak.
- BERT’i fallback/doğrulayıcı olarak kullanmak (ana karar verici değil).
- Overpass için skorlu sorgu planı üretmek (A/B/C fallback).
- Karar sürecini trace edilebilir hale getirmek.
- Düşük güvende `unknown/ambiguous` dönebilmek.

### 2.2 Hedef Dışı
- Tam morfolojik çözümleyici yazmak (Zemberek benzeri tam parser hedef değil).
- Tüm Türkçe POI evrenini ilk iterasyonda kapsamak.
- Her sorguda kusursuz semantik sonuç garantisi.

---

## 3) Temel İlkeler

1. **Yanlış pozitiften kaçın:** Emin değilsek `unknown` daha iyidir.
2. **Deterministik önce, semantik sonra:** Önce kural+sözlük, sonra BERT fallback.
3. **Canonical merkezli tasarım:** Overpass’a surface form değil canonical concept gider.
4. **Açıklanabilir karar:** Her aşama trace üretir.
5. **Sınırlı fallback:** Overpass fallback en fazla 2-3 adım.

---

## 4) Kavramlar

- **Surface:** Kullanıcının yazdığı ham ifade (`pilavcılardan`).
- **Normalized Surface:** Ön normalize sonrası ifade (`pilavcılardan`, `pilavcılar`, vb. adaylar).
- **Canonical Concept:** İç sistemde tekil POI anahtar adı (`pilavcı`).
- **Synonym:** Canonical’a bağlanan alternatif yüzey (`pilav salonu`, `pilavci`).
- **OSM Tag Plan:** Overpass için etiket kombinasyon listesi.
- **Confidence:** Çözüm güven skoru.
- **Trace:** Karar adımlarının kayıt çıktısı.

---

## 5) Üst Düzey Mimari

### 5.1 Akış
1. `normalize_text`
2. `extract_candidates` (lokasyon/poi/intent ayrı)
3. `normalize_location`
4. `normalize_poi_concept`
5. `map_concept_to_osm_queries`
6. `execute_overpass_plan` (A→B→C)
7. `result + trace`

### 5.2 Ayrı Pipeline Prensibi
- **Lokasyon pipeline:** il/ilçe/mahalle + geocoding çözümü
- **POI pipeline:** mekan türü/konsept + OSM tag map

---

## 6) Veri Modeli Tasarımı

### 6.1 Canonical POI Sözlüğü (önerilen yapı)

`POI_CANONICAL[concept] = {`
- `synonyms: [str]`
- `negative_terms: [str]`  (yanlış bağlanmayı azaltır)
- `osm_plans: [ {tags: dict, score: float, plan_id: str} ]`
- `category: str` (food, health, transport...)
`}`

Örnek konseptler:
- `pilavcı`
- `çiğ köfteci`
- `dönerci`
- `eczane`
- `benzinlik`

### 6.2 Trace Şeması

`trace = {`
- `raw_text`
- `normalized_text`
- `tokens`
- `location_candidates`
- `poi_candidates`
- `poi_resolution`: {selected, source, score, rejected[]}
- `intent_resolution`
- `osm_plan_selected`
- `fallback_steps`
- `final_confidence`
- `status: success|unknown|ambiguous`
`}`

### 6.3 Sözlük Sürümleme ve Migrasyon

Sözlük şeması versiyonlu tutulur:
- `schema_version`
- `dict_version`
- `generated_at`

Kurallar:
1. `schema_version` değişirse migration script zorunlu.
2. Runtime, desteklemediği schema görürse fail-fast + açık hata döner.
3. Backward compatibility için en az 1 eski sürüm okuyucu tutulur.
4. CI’da dictionary schema validation testi zorunludur.

Öneri:
- `backend/osm_poi_dictionary.py` yanında `dictionary_migrations/` klasörü.
- `dict_version` cache key’lere pinlenir.

---

## 7) Ön Normalizasyon Kuralları

1. Küçük harfe çevir.
2. Fazla boşluk/noktalama temizliği.
3. Apostrof varyasyonlarını normalize et (`Malatya'da`, `Malatyada`).
4. Türkçe karakter fold desteği (opsiyonel): `pilavci -> pilavcı`.
5. Orijinal surface’i trace’de sakla (geri dönüş ve debug için).

---

## 8) Aday Çıkarma Stratejisi

### 8.1 Token + N-gram
- 3-gram → 2-gram → 1-gram sırayla dene.
- Yüksek güvenli n-gram bulunursa alt parçaları ele.
- Ama büyük n-gram düşük güvenliyse alt parçaları denemeyi sürdür.

### 8.2 Aday Tipleri
- `location_candidate`
- `poi_candidate`
- `intent_candidate`
- `stopword/filler`

---

## 9) POI Çözümleme (3 Katman)

## Katman-1: Morfolojik Aday Üretimi
- Ek temizleme ile top-k kök aday üret.
- Tek kök dayatma yok.
- Örn: `pilavcılardan -> [pilavcı, pilavcılar, pilav]` (sıralı)

## Katman-2: Sözlük Doğrulama + Rollback
- Aday canonical/synonym havuzunda mı?
- Varsa kabul et.
- Yoksa rollback ile diğer adayı dene.
- Over-stemming korumaları uygula (`dondurma` gibi).

## Katman-3: BERT Fallback
- Yalnızca önceki katmanlar başarısızsa.
- Sadece canonical whitelist içinde nearest concept ara.
- `min_score`, `min_margin`, `min_len` eşikleri zorunlu.
- Eşik altıysa `unknown`.

---

## 10) Lokasyon Çözümleme

- Lokasyon sözlüğü (il/ilçe/mahalle) + mevcut geocoding destekleri.
- Ek temizleme ama POI’den farklı kurallarla.
- Gerekirse `ambiguous location` dönebilmeli.
- Lokasyon confidence ayrı tutulmalı.

---

## 11) Intent Çözümleme

Asgari intent set:
- `search` (ara/bul)
- `recommendation` (öner)
- `nearest` (yakınımda/en yakın)
- `route` (rota çiz/götür)

Intent, Overpass plan sırasını ve sonuç sıralamayı etkiler.

### 11.1 Mevcut Sistem Tipleri ile Mapping (Regresyon Önleyici)

Mevcut backend/frontend akışında kullanılan tiplerle yeni intent taksonomisinin eşleşmesi zorunludur:

| Yeni Intent | Mevcut Tip(ler) | Dönüşüm Kuralı |
|---|---|---|
| `search` | `poi` | Varsayılan POI arama niyeti |
| `recommendation` | `poi` | `poi` + sıralama bias (puan/popülerlik) |
| `nearest` | `poi` | `poi` + proximity bias (mesafe öncelikli) |
| `route` | `route`, `single`, `multi` | `single/multi` route alt-tipi olarak korunur |

**Kural:** API dış sözleşmesinde mevcut `poi/single/multi/route` alanları korunacak; yeni intent alanı iç karar motorunda kullanılacaktır.

---

## 12) Overpass Tag Planı (A/B/C)

### Plan-A (dar, yüksek güven)
- Canonical’a en yakın özel tag seti

### Plan-B (orta genişlik)
- Kategori tabanlı alternatif tag

### Plan-C (geniş fallback)
- Daha genel tag/cuisine kombinasyonu

**Kural:**
- A’dan başla
- Sonuç yetersizse B
- Hâlâ yetersizse C
- En fazla 3 plan

### 12.1 Coğrafi Sınırlandırma Zorunlu Kuralları

Overpass sorguları gürültüyü azaltmak için geo-bound olmadan çalıştırılmayacaktır.

1. **Lokasyon çözümlenmişse:** önce `area`/`bbox` üzerinden sınırlandır.
2. **Lokasyon çözümlenmemişse ama kullanıcı konumu varsa:** yarıçap (`around`) ile sınırlandır.
3. **Hiçbiri yoksa:** global sorgu atma, `unknown_location` dön.
4. **Plan-A/B/C’nin hepsinde aynı geo-bound kullanılsın** (yalnızca tag genişlesin).
5. **Sonuç üst limiti** (`limit`) zorunlu olsun (örn. 50/100).

Önerilen öncelik:
- `polygon/area` > `bbox` > `around`

---

## 13) Unknown / Ambiguous Politikası

Sistem şu durumlarda zorlamaz:
- POI confidence eşik altı
- Lokasyon confidence eşik altı
- Location/POI eşit güçlü çakışma

Dönen durumlar:
- `unknown_poi`
- `unknown_location`
- `ambiguous_poi_location`

### 13.1 Lokasyon-POI Çakışma Karar Matrisi (Tie-break)

| Durum | Kural | Çıktı |
|---|---|---|
| `loc_conf >= 0.85` ve `poi_conf < 0.60` | Lokasyon baskın | `location` seç |
| `poi_conf >= 0.85` ve `loc_conf < 0.60` | POI baskın | `poi` seç |
| Her ikisi `>= 0.75` ve fark `>= 0.15` | Yüksek fark | yüksek olanı seç |
| Her ikisi `>= 0.75` ve fark `< 0.15` | Belirsiz | `ambiguous_poi_location` |
| İkisi de eşik altı | Düşük güven | `unknown_*` |

Ek bağlam kuralları:
- `yakınımda`, `en yakın` varsa POI tarafına +0.05 bias
- il/ilçe/mahalle eşleşmesi varsa lokasyon tarafına +0.05 bias
- BERT kaynağı, morph+dict sonucunu yalnızca margin kuralı geçerse override eder

---

## 14) Eşik Politikası (İlk Değerler)

- `morph+dict`: 0.95 (yüksek)
- `rule+dict`: 0.88 (orta-yüksek)
- `bert+dict`: min 0.80
- `bert_margin`: min 0.08
- `min_token_len_for_bert`: 4

Not: Bunlar başlangıç değerleri; canlı metrikle kalibre edilir.

### 14.1 Kalibrasyon Protokolü

- **Dataset split:** `train/dev/test = 70/15/15` (sorgu bazlı, sızıntısız)
- **Raporlama metriği:**
  - POI concept accuracy
  - wrong-tag rate
  - no-result rate
  - ambiguous/unknown rate
- **Kalibrasyon sıklığı:**
  - Haftalık küçük ayar (dev set)
  - Aylık tam yeniden kalibrasyon (dev+shadow test)
- **Eşik güncelleme kuralı:**
  - Yeni eşik, test setinde wrong-tag rate’i artırmıyorsa alınır
  - no-result rate artışı > %2 ise değişiklik reddedilir
- **Yayınlama:**
  - Eşikler `config` üzerinden versiyonlu tutulur (`threshold_profile=vYYYYMMDD`)

---

## 15) Performans ve Cache Planı

Önerilen cache katmanları:
1. `surface -> normalized concept`
2. `concept -> osm tag plan`
3. `location text -> geocode result`
4. `query signature -> overpass result`

### 15.1 TTL / Invalidation / Version Pinning

| Cache Katmanı | TTL | Invalidation Tetikleyici | Version Key |
|---|---:|---|---|
| surface->concept | 24 saat | sözlük/synonym güncellemesi | `dict_version` |
| concept->tag plan | 24 saat | tag plan şema değişimi | `tag_schema_version` |
| location->geocode | 6 saat | geocoder provider değişimi | `geo_provider_version` |
| query->overpass | 5-15dk | overpass plan değişimi / bölgesel invalidation | `plan_version` |

Zorunlu kurallar:
- Cache key içine `dict_version + threshold_profile + plan_version` eklenir.
- Sözlük güncellendiğinde en az ilk iki katman toplu invalidate edilir.
- Eski versiyon key’leri grace-period sonrası temizlenir.

Kısa devre:
- morph+dict başarılıysa BERT’i atla
- ilk overpass planı yeterliyse fallback atlama

---

## 16) Gözlemlenebilirlik (Observability)

Kalıcı log alanları:
- `request_id` / `correlation_id`
- source (`morph|rule|bert`)
- selected concept
- confidence
- rejected candidates + neden
- selected overpass plan
- fallback count
- no-result reason

PII ve saklama politikası:
- Ham kullanıcı metni varsayılan olarak maskeli/log dışı (debug flag açık değilse).
- Lokasyon koordinatları logda kaba hassasiyetle (örn. 3-4 ondalık) saklanır.
- Trace log retention: 14 gün (debug), özet metrik retention: 90 gün.
- Debug trace API cevabına yalnızca yetkili/debug modunda eklenir.

Debug response (opsiyonel):
- `trace` sadece debug modda dönsün.

---

## 17) Kalite Metrikleri

İzlenecek metrikler:
1. Concept resolution accuracy
2. Wrong-tag rate
3. No-result rate
4. Fallback usage rate
5. BERT intervention rate
6. Unknown rate
7. Ambiguous rate
8. Ortalama sorgu gecikmesi

---

## 18) Test Stratejisi

### 18.1 Unit Test
- Ek temizleme
- Protected words
- Synonym resolution
- BERT gating
- Tag plan üretimi

### 18.2 Golden Set
- Türkçe gerçek sorgulardan etiketli dataset
- Her PR’da offline skor karşılaştırma

### 18.3 Entegrasyon Testi
- Query → parse → overpass plan → sonuç sayısı
- fallback zinciri doğrulama

### 18.4 Regresyon Test
- Önceki doğru çalışan sorgular bozulmamalı

---

## 19) Güvenlik ve Dayanıklılık

- Overpass sorgularında kontrolsüz genişleme engeli
- Query timeout/retry sınırı
- Kullanıcı metninde aşırı uzun girdi koruması
- SSRF benzeri risklere karşı sabit endpoint politikası

---

## 20) Uygulama Fazları

## Faz-1 (MVP)
- `normalize_poi_concept(surface)`
- canonical + synonym sözlüğü
- unknown/ambiguous dönüşü
- basic trace
- map_concept_to_osm_queries (A/B)

**Çıkış kriteri:**
- Yanlış pozitifler düşmeli
- Sık sorgularda doğru concept artmalı

## Faz-2 (Güçlendirme)
- n-gram lock mekanizması
- BERT margin/len gating
- Overpass feedback loop
- 4 katman cache
- kapsamlı metrik dashboard

**Çıkış kriteri:**
- no-result rate düşmeli
- latency kabul sınırında kalmalı

---

## 21) Dosya Bazlı Teknik Plan

### Mevcut dosyalarda değişecek yerler
- `backend/bert_nlp_engine.py`
  - `extract_poi_concept` entegrasyonu
  - BERT fallback gating

- `backend/nlp_engine.py`
  - regex fallback tarafında aynı canonical sistemle uyum

- `backend/graph_manager.py`
  - Overpass plan fallback yürütme (A/B/C)

- `backend/app.py`
  - debug trace alanının güvenli şekilde opsiyonel sunulması

### Yeni/yeniden düzenlenecek yardımcı dosyalar
- `backend/osm_poi_dictionary.py`
  - canonical/synonym/osm_plans yapısı

- `backend/nlp_concept_resolver.py` (öneri)
  - `normalize_poi_concept`
  - `resolve_query`

- `backend/nlp_trace.py` (öneri)
  - trace şeması + yardımcılar

---

## 22) Önerilen Fonksiyon İmzaları

- `normalize_text(text: str) -> str`
- `extract_candidates(text: str) -> dict`
- `normalize_location(candidates: list) -> dict`
- `normalize_poi_concept(surface_or_ngram: str) -> dict`
- `map_concept_to_osm_queries(concept: str, intent: str) -> list`
- `resolve_query(text: str, debug: bool=False) -> dict`

Beklenen `resolve_query` çıktısı:
- `location`
- `poi_concept`
- `intent`
- `confidence`
- `overpass_plan`
- `status`
- `trace` (debug modda)

---

## 23) Kabul Kriterleri (Definition of Done)

1. En az 100+ Türkçe test sorgusunda baseline’a göre daha iyi concept doğruluğu.
2. Yanlış tag oranında gözle görülür düşüş.
3. Unknown/ambiguous çıktıları kontrollü ve anlamlı.
4. Overpass fallback maksimum 3 adımda sınırlı.
5. Debug trace ile her karar adımı izlenebilir.
6. Ortalama gecikme kabul sınırında (hedef: mevcuta yakın, kötüleşme sınırlı).

---

## 24) Risk Register

1. Sözlük bakım yükü artışı
2. BERT yanlış pozitif
3. N-gram yanlış kilitleme
4. Overpass sonuç boşluğu
5. Latency artışı

Azaltma stratejileri:
- weekly synonym review
- threshold kalibrasyonu
- fallback sınırı
- cache
- unknown politikası

---

## 25) Operasyon ve Süreç

- Haftalık synonym öneri raporu
- Aylık threshold kalibrasyonu
- Golden set sürümleme
- Trace örneklerinden hata analizi

---

## 26) Açık Kararlar (Karar Gerektiren Noktalar)

1. BERT fallback global eşik mi, intent bazlı eşik mi?
2. Unknown dönerken kullanıcı mesajı ne kadar açıklayıcı olacak?
3. Overpass fallback planı 2 mi 3 adım mı?
4. Debug trace’i API response’a mı sadece log’a mı koyacağız?

---

## 27) İlk Sprint Görev Kırılımı (Öneri)

### Sprint-1
- [ ] canonical sözlük şeması
- [ ] normalize_text + aday çıkarma
- [ ] morph+dict + rollback
- [ ] unknown/ambiguous dönüşü
- [ ] temel unit testler

### Sprint-2
- [ ] BERT fallback gating
- [ ] overpass A/B/C plan yürütme
- [ ] trace modeli
- [ ] golden set eval script güncellemesi
- [ ] performans ölçümleri

---

## 28) Örnek Senaryolar

1) `Malatya'da pilavcı arıyorum`
- location: `Malatya`
- poi: `pilavcı`
- intent: `search`
- plan: A→(gerekirse)B

2) `küçükyalıda pilavcılardan arıyorum`
- location: `Küçükyalı`
- poi: `pilavcı`
- source: `morph+dict`

3) `pilavci oner`
- poi: `pilavcı`
- source: `bert+dict` (eşik geçerse)

4) `dondurma nerede`
- poi: `dondurmacı` (sözlükte varsa)
- `dondur` gibi hatalı kök engellenmiş olmalı

---

## 29) Sonuç

Bu spec kit, Türkçe doğal dil POI/lokasyon çözümleme hattını:
- daha doğru,
- daha kontrollü,
- daha açıklanabilir,
- Overpass entegrasyonuna daha uygun
hale getirmek için uygulanabilir bir yol haritası sunar.

**Öneri:** Faz-1’i hızlıca tamamlayıp golden set ile ölç, sonra Faz-2 güçlendirmesine geç.
