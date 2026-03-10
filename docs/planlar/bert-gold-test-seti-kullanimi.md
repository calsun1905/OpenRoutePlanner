# BERT Gold Test Seti Kullanimi

Bu dokuman, Turkce BERT NLP ciktilarini olcmek icin eklenen gold test setini nasil kullanacagini anlatir.

## Dosyalar

- Dataset: `tests/data/bert_gold_tr_v1.jsonl`
- Evaluator: `scripts/tools/evaluate_bert_gold.py`

## Amac

- Refactor oncesi/sonrasi kaliteyi sayisal karsilastirmak
- `type`, `origin`, `destination`, `location`, `locations` alanlarinda regresyonu erken yakalamak
- Parse gecikmesini (p50/p95) takip etmek

## Calistirma

Tum dataset:

```bash
python scripts/tools/evaluate_bert_gold.py
```

Not: Varsayilan mod deterministik benchmark icin `OSM=off`, `OSM-first=off`, `static-seed=on` kullanir.
Dynamic cache seed de varsayilan olarak kapalidir (`dynamic-cache=off`).

Ilk 10 kayit:

```bash
python scripts/tools/evaluate_bert_gold.py --limit 10
```

Markdown rapor yaz:

```bash
python scripts/tools/evaluate_bert_gold.py --write-report
```

OSM acik test modu:

```bash
python scripts/tools/evaluate_bert_gold.py --with-osm
```

OSM-first test modu:

```bash
python scripts/tools/evaluate_bert_gold.py --osm-first
```

DB'deki dinamik cache'i dahil etmek istersen:

```bash
python scripts/tools/evaluate_bert_gold.py --with-dynamic-cache
```

## Dataset Kayit Formati

Her satir bir JSON nesnesidir:

```json
{
  "id": "tr_route_001",
  "query": "Kadıköy'den Beşiktaş'a rota çiz",
  "expected": {
    "type": "route",
    "origin": "kadıköy",
    "destination": "beşiktaş"
  },
  "tags": ["route", "apostrophe"]
}
```

## Notlar

- Bu dataset koda kural yazdirmak icin degil, sadece olcum icindir.
- Karsilastirma "fuzzy" yapildigi icin `Kadıköy` ile `Kadıköy, Istanbul` eslesebilir.
- Ilk asamada sadece Turkce odakli tutulmustur.
