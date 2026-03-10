# BERT Calisma Akis Semasi (Detayli)

Bu dokuman, mevcut BERT NLP akisini kutu kutu aciklar.
Amac: "hangi adim ne yapiyor?" sorusuna net cevap vermek.

## 1) Calisma Akisi (Runtime Parse)

```mermaid
flowchart TD
    A0["A0 Baslangic: parse(query)"] --> A1{"A1 Sorgu gecerli mi?"}
    A1 -- "Hayir" --> A2["A2 unknown + error don"]
    A1 -- "Evet" --> B0["B0 Intent siniflandir (ilk tahmin)"]

    B0 --> C0["C0 Span cikart: token + ngram + start/end + role_hint"]
    C0 --> C1["C1 Her span icin aday esleme dongusu"]
    C1 --> C2["C2 Lexical lookup: normalize/alias/fold varyantlari"]
    C2 --> C3{"C3 Exact eslesme var mi?"}
    C3 -- "Evet" --> C4["C4 Aday = similarity 1.0"]
    C3 -- "Hayir" --> C5["C5 BERT encode(span) + cosine similarity"]
    C5 --> C6{"C6 Esik ustu mu?"}
    C6 -- "Hayir" --> C7["C7 Span elenir"]
    C6 -- "Evet" --> C8["C8 Aday kabul edilir"]
    C4 --> D0["D0 Dedup + best-per-place secimi"]
    C8 --> D0
    C7 --> D0

    D0 --> D1["D1 Global filtre + siralama => ordered_places"]
    D1 --> E0["E0 Intent refine (role_hint + cue words)"]
    E0 --> E1{"E1 Nihai type"}

    E1 -- "route" --> F0["F0 Route slot filling"]
    F0 --> F1["F1 from/to adaylarindan origin/destination sec"]
    F1 --> F2["F2 Gerekirse metin sirasi fallback"]

    E1 -- "poi" --> G0["G0 POI slot filling"]
    G0 --> G1["G1 _choose_best_poi_location()"]

    E1 -- "multi" --> H0["H0 locations listesi olustur"]
    E1 -- "single" --> I0["I0 destination sec"]
    E1 -- "unknown" --> J0["J0 error/fallback"]

    F2 --> K0["K0 Final JSON sonucu don"]
    G1 --> K0
    H0 --> K0
    I0 --> K0
    J0 --> K0
```

## 2) Kutu Aciklamalari (Parse)

| Kutu | Ne yapiyor | Girdi | Cikti |
|---|---|---|---|
| A0 | Ana parse fonksiyonu baslar | query (str) | islem akisi |
| A1 | Bos/gecersiz sorgu kontrolu | query | true/false |
| A2 | Hata cevabi | gecersiz query | type=unknown, error |
| B0 | Ilk intent tahmini | query | route/poi/multi/single/unknown + confidence |
| C0 | Mention/span adayi cikarir | normalize query | span listesi (surface, normalized, start, end, role_hint) |
| C1 | Her span icin aday arama dongusu | span listesi | adaylar |
| C2 | Dogrudan isim eslesmesi arar | normalized span | canonical place adayi |
| C3 | Exact eslesme karari | lookup sonucu | var/yok |
| C4 | Exact bulunursa en yuksek guvenle adaya cevirir | place | similarity=1.0 aday |
| C5 | Exact yoksa semantic eslesme yapar | span embedding + place embeddings | similarity skorlari |
| C6 | Skor esik kontrolu | similarity | kabul/red |
| C7 | Dusuk skor span'i atar | span | elenmis |
| C8 | Yuksek skor span'i adaya ekler | span + match | kabul edilmis aday |
| D0 | Ayni place icin en iyi adayi tutar | adaylar | dedup adaylar |
| D1 | Filtre + siralama yapar | dedup adaylar | ordered_places |
| E0 | Intent'i kurallarla rafine eder | ilk intent + role_hint + cue words | nihai intent |
| E1 | Nihai tip secimi | refine sonucu | route/poi/multi/single/unknown |
| F0 | Route slot asamasi | ordered_places | route alanlari |
| F1 | from/to sinyallerinden yon atar | role_hint + similarity | origin/destination |
| F2 | Yon cikmazsa metin sirasi fallback | ordered_places | origin/destination tamam |
| G0 | POI slot asamasi | ordered_places | location |
| G1 | POI lokasyonu secme fonksiyonu | ordered_places | en iyi location |
| H0 | Coklu gezi listesi doldurma | ordered_places | locations[] |
| I0 | Tek hedef secimi | ordered_places | destination |
| J0 | Hata/fallback | yetersiz sinyal | unknown/error |
| K0 | Ciktiyi JSON olarak doner | tum alanlar | final result |

## 3) _choose_best_poi_location() Ic Mantigi

1. Exact eslesen aday varsa (similarity 1.0), onu sec.
2. Exact yoksa role_hint=loc adaylarini degerlendir.
3. Hala yoksa en yuksek similarity adayi sec.

Bu siralama, "Taksim civarinda muze var mi?" gibi sorgularda
genel semantik benzer ama alakasiz yerlerin one gecmesini azaltir.

## 4) Intent Refine Kurallari (Ozet)

1. `from/to` sinyali gucluyse `route`.
2. POI cue kelimeleri varsa ve yon sinyali yoksa `poi`.
3. 3+ yer + multi cue varsa `multi`.
4. Tek hedef sinyali varsa `single`.
5. Hicbiri degilse `unknown`/fallback.

## 5) Degerlendirme (Gold Benchmark) Akisi

```mermaid
flowchart TD
    T0["T0 JSONL dataset oku"] --> T1["T1 evaluate_bert_gold.py parse dongusu"]
    T1 --> T2["T2 Expected vs Predicted karsilastir"]
    T2 --> T3["T3 Metrikler: case accuracy + field accuracy"]
    T3 --> T4["T4 Latency p50/p95 hesapla"]
    T4 --> T5["T5 Konsol ozeti + opsiyonel markdown rapor"]
```

## 6) Neden Bu Mimari?

- Sadece regex'e bagli degil, retrieval + semantic + slot karar katmani var.
- Exact lexical adim sayesinde yer adlarinda yanlis semantic eslesme azalir.
- Intent refine katmani, tek model skorunun yanlis tip secmesini dengeler.
- Benchmark scripti ile degisiklikten sonra kalite/regresyon olculur.

