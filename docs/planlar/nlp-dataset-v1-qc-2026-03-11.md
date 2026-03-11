# NLP Dataset V1 QC Raporu (2026-03-11)

Bu dosya, kullanicinin paylastigi 200 satirlik JSONL veri seti icin
hizli kalite kontrol bulgularini ve duzeltme listesini icerir.

## 1) Kritik Hatalar (egitime direkt verilmemeli)

### A) Intent-slot uyumsuzlugu

1. `tr_000046`
- Sorun: `intent=single` ama metin iki nokta arasi gecis anlatiyor (`beykentten avcilara gitmek`).
- Beklenen: `intent=route`, `origin=beykent`, `destination=avcilar`.

2. `tr_000112`
- Sorun: `intent=route` ama `origin` bos.
- Beklenen: `single` olarak etiketlenmeli **veya** `origin` metinde acikca bulunuyorsa doldurulmali.

3. `tr_000113`
- Sorun: `intent=route` ama `origin` bos.
- Beklenen: `single` olarak etiketlenmeli **veya** `origin` metinde acikca bulunuyorsa doldurulmali.

### B) POI satirlarinda `poi_concept` bos (kurala aykiri)

Asagidaki kayitlarda `intent=poi` oldugu halde `poi_concept=null`:

- `tr_000012`
- `tr_000024`
- `tr_000040`
- `tr_000073`
- `tr_000120`
- `tr_000129`
- `tr_000140`
- `tr_000149`
- `tr_000159`
- `tr_000169`
- `tr_000179`
- `tr_000189`
- `tr_000199`

Beklenen: bu satirlarda `poi_concept` dolu olmali (ornek: `kafe`, `cami`, `eczane`, `park`, `restoran` gibi).

## 2) Veri Kalitesi Problemleri (duzeltilmesi tavsiye edilir)

### A) Duplicate (ayni metin tekrar ediyor)

1. `tr_000075` == `tr_000109`
- Metin: `fenerbahçede stadyum nerede`

2. `tr_000034` == `tr_000165`
- Metin: `sarıyerde eczane nerde`

### B) Slot normalizasyon tutarsizliklari

1. `tr_000017`
- Sorun: `destination="kadıkoye"` ekli/bozuk formatta.
- Beklenen: normalize lokasyon (tercihen `kadikoy` veya `kadıköy`), eksiz.

2. Veri genelinde Turkce/ASCII varyant karisikligi var
- Ornekler: `kadikoy/kadıköy`, `besiktas/beşiktaş`, `karakoy/karaköy`.
- Not: Typo zorlugu icin bir miktar varyasyon normaldir; ama slot alaninda tek bir normalize standart secilmeli.

### C) Asiri genel lokasyonlar (modeli bulaniklastirabilir)

- `tr_000096`, `tr_000097`, `tr_000098`, `tr_000099`, `tr_000100`
- Sorun: `anadolu`, `avrupa`, `bogaz` gibi cok genis/soyut lokasyonlar.
- Oneri: bu satirlarin bir kismini daha somut il/ilce/semt ile degistir.

## 3) Duzeltme Oncelik Sirasi

1. Intent-slot kritik hatalarini duzelt (`tr_000046`, `tr_000112`, `tr_000113`).
2. Tum `poi_concept=null` olan POI satirlarini doldur.
3. Duplicate satirlardan birini degistir.
4. Slot normalizasyonunu tek standarda cek.
5. Asiri genel lokasyonlarin bir kismini somutlastir.

## 4) Hedef Kalite Kriteri (V2)

- `intent-slot` uyumsuzluk: `0`
- `intent=poi` olup `poi_concept=null`: `0`
- Duplicate metin: `0`
- Slot normalizasyon standardi: `%100`

