# BERT Calibration / Regression Özeti (Faz-2)

Tarih: 2026-03-15

## Çalıştırılan benchmark
- Dataset: `tests/data/bert_gold_tr_v1.jsonl`
- Toplam örnek: 24
- Komut: `python scripts/tools/evaluate_bert_gold.py`

## Sonuçlar

### 1) Deterministik mod (OSM kapalı)
- Mode: `OSM=off, OSM-first=off, dynamic-cache=off, static-seed=on`
- Case accuracy: **100.00% (24/24)**
- Latency p50: **41.7 ms**
- Latency p95: **78.8 ms**
- Field accuracy:
  - type: 100.00%
  - origin: 100.00%
  - destination: 100.00%
  - location: 100.00%
  - locations: 100.00%

### 2) OSM-first mod (OSM açık)
- Mode: `OSM=on, OSM-first=on, dynamic-cache=off, static-seed=on`
- Case accuracy: **95.83% (23/24)**
- Latency p50: **6229.6 ms**
- Latency p95: **9954.7 ms**
- Kalan tek hata: `tr_unknown_002 (Merhaba nasılsın)`

## Yapılan düzeltmeler (özet)
- Intent conflict matrix güçlendirildi.
- Chitchat guard eklendi (`merhaba/selam/nasılsın` -> unknown).
- POI vs route çakışmasında `poi question cue` ile doğru yöne zorlama.
- Multi için:
  - explicit list extraction (`,`, `ve`) eklendi,
  - plain multi list extraction (virgülsüz `gezi planı` gibi) eklendi,
  - weak multi false-positive’leri düşürüldü.
- Unknown branch’te kontrolsüz `len(place_names)>=3 => multi` davranışı sınırlandı.

## Not
- OSM-first modda doğruluk yüksek olsa da gecikme belirgin şekilde artıyor.
- Üretim için hızlı/kararlı yol: OSM kapalı deterministik parse + gerektiğinde bounded OSM lookup.
