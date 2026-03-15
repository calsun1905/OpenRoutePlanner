# BERT + OSM Operasyon Profilleri (Güncel)

Tarih: 2026-03-15

## Özet
OSM-first akışına timeout-budget/degrade eklendi.
Böylece Nominatim yavaşladığında parse süresi kontrol altında kalıyor.

## Yeni ENV ayarları
- `ORP_BERT_OSM_TIMEOUT_SEC` (varsayılan: `3.0`)
  - Tek bir OSM HTTP isteğinin timeout süresi.
- `ORP_BERT_OSM_PREFETCH_BUDGET_SEC` (varsayılan: `2.5`)
  - Parse başına toplam OSM prefetch zaman bütçesi.
- `ORP_BERT_OSM_PREFETCH_MAX_QUERIES` (varsayılan: `3`)
  - Parse başına en fazla OSM prefetch sorgu sayısı.

## Önerilen profiller

### 1) Hız öncelikli (önerilen üretim)
- `ORP_BERT_USE_OSM=0`
- `ORP_BERT_PREFER_OSM_FIRST=0`

Beklenen (gold dataset):
- Accuracy: ~100%
- p50: ~40 ms
- p95: ~75 ms

### 2) Dengeli OSM-first
- `ORP_BERT_USE_OSM=1`
- `ORP_BERT_PREFER_OSM_FIRST=1`
- `ORP_BERT_OSM_TIMEOUT_SEC=2.5`
- `ORP_BERT_OSM_PREFETCH_BUDGET_SEC=2.0`
- `ORP_BERT_OSM_PREFETCH_MAX_QUERIES=2`

Beklenen:
- Accuracy: yüksek (datasette 100% görüldü)
- p50/p95: saniye seviyesinde ama önceki sürüme göre belirgin düşük

### 3) Kalite öncelikli OSM-first
- `ORP_BERT_USE_OSM=1`
- `ORP_BERT_PREFER_OSM_FIRST=1`
- `ORP_BERT_OSM_TIMEOUT_SEC=3.0`
- `ORP_BERT_OSM_PREFETCH_BUDGET_SEC=2.5`
- `ORP_BERT_OSM_PREFETCH_MAX_QUERIES=3`

Beklenen:
- Accuracy: çok yüksek
- Latency: dengeli profile göre daha yüksek

## Son ölçüm (güncel)
- Deterministik (`OSM=off`): 24/24, p50 38.9ms, p95 74.3ms
- OSM-first (budget aktif): 24/24, p50 3440.9ms, p95 4878.7ms

## Not
Eski raporlardaki 7-10s p95 değerleri timeout-budget öncesi çıktılardır.
Yeni profil ayarları ile bu gecikme azaltıldı.
