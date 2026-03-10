# BERT NLP Temel Kavramlar ve Calisma Prensibi

Bu dosya, BERT tarafinda kullandigimiz terimleri en temel seviyeden aciklar ve sistemi adim adim anlatir.
Amac: teknik terimleri bilmeden de akisin mantigini takip edebilmek.

## 1) Temel Terimler

`BERT`
Metinleri sayisal vektorlere ceviren bir dil modeli. Bizdeki gorevi, bir metnin baska bir metne ne kadar benzedigini olcmek.

`Embedding`
Bir kelimeyi veya cumleyi sayisal bir diziye ceviren temsil. Bu temsil sayesinde benzerlik hesabi yapilir.

`Cosine Similarity`
Iki embedding vektorunun benzerligini 0-1 araliginda olcen skor.
1.0'a yaklastikca benzerlik artar.

`Intent`
Kullanicinin niyeti. Ornek: `route`, `poi`, `single`, `multi`, `unknown`.

`Token`
Cumlenin parcalanmis kucuk birimi (genelde kelime).

`Span`
Cumlede yer adayi olabilecek parca. Span sadece metni degil konumu da tutar.
Ornek alanlar: `surface`, `normalized`, `start`, `end`, `role_hint`.

`Role Hint`
Eklerden cikan rol ipucu.
`from`: baslangic, `to`: varis, `loc`: konum.

`N-gram`
1, 2 veya 3 kelimelik bloklar.
Tek kelimeye bakmak yerine kelime gruplarina da bakabilmek icin kullanilir.

`PlaceDatabase`
Sistemin yer isimleri hafizasi.
Ic kaynaklari: `local_places`, kullanici kayitli yerleri, Turkey yer listesi, opsiyonel OSM dynamic cache.

`Lexical Exact Lookup`
Yer adini once dogrudan metinsel olarak bulma adimi.
Ornek: `kadikoy` normalize edilip `Kadikoy`/`Kadiköy` kaydina birebir baglanir.
Bu adim dogrudan eslesme verdiginde `similarity=1.0` kabul edilir.

`Threshold`
Benzerlik esigi. Esik alti eslesmeler atilir.

`Slot Filling`
Bulunan yerleri dogru alana koyma.
Ornek: `origin`, `destination`, `location`, `locations`.

`Dedup`
Ayni yere ait birden fazla adayi tek en iyi adaya indirgeme.

## 2) Sistem Neden Bu Sekilde Kuruldu?

Sadece regex kullansaydik yeni yer adlari, yazim farklari ve dogal dil varyasyonlari kolayca bozulurdu.
Sadece BERT kullansaydik da bazen alakasiz ama semantik olarak benzer yerlere kayma olabilirdi.
Bu nedenle sistem hibrit kuruldu:

1. Once metni normalize et.
2. Span adaylarini cikar.
3. Once lexical exact lookup dene.
4. Exact yoksa BERT similarity ile adayi sec.
5. Intent ve role ipuclari ile slotlari doldur.

## 3) End-to-End Ornek (Route)

Ornek cumle:
`Kadıköy'den Beşiktaş'a rota çiz`

1. `parse(query)` calisir.
2. Gecerlilik kontrolu yapilir.
Geçersiz sayilanlar: bos sorgu, `None`, string olmayan tip.
3. Ilk intent tahmini yapilir.
4. Span cikartma adiminda adaylar bulunur:
`Kadıköy'den`, `Beşiktaş'a`.
5. Normalize edilir:
`Kadıköy'den -> kadıköy + role_hint=from`
`Beşiktaş'a -> beşiktaş + role_hint=to`
6. Lexical exact lookup denenir.
`kadıköy` ve `beşiktaş` PlaceDatabase icinde varsa dogrudan baglanir.
7. Exact bulunmazsa BERT similarity devreye girer.
8. Dusuk guvenli adaylar esik altinda kalir ve atilir.
9. Kalan adaylar dedup edilir ve siralanir.
10. Intent refine adiminda role_hint sinyali ile `route` kesinlesir.
11. Slot filling:
`origin=Kadıköy`, `destination=Beşiktaş`.
12. Final JSON doner.

## 4) End-to-End Ornek (POI)

Ornek cumle:
`Kadıköy'de kahve içilecek yerler`

1. Span adaylari cikarilir.
2. `Kadıköy'de` normalize edilir ve `role_hint=loc` olur.
3. POI cue kelimeleri (`kahve`, `yerler`, `nerede` benzeri) intent refine asamasinda `poi` kararini guclendirir.
4. `_choose_best_poi_location()` fonksiyonu calisir.
Oncelik sirasi:
exact eslesme > `role_hint=loc` > en yuksek similarity.
5. `location=Kadıköy` atanir ve POI turu sonuc doner.

## 5) Intent Refine Nedir?

Ilk intent modeli bazen yanlis tip secebilir.
Refine katmani bu yanlis secimi metin ipuclariyla duzeltir.

Ornek kurallar:
1. `from/to` sinyali gucluyse `route`.
2. POI cue var ve yon sinyali yoksa `poi`.
3. Coklu yer + multi cue varsa `multi`.
4. Tek hedef sinyali varsa `single`.

Bu katman, modelin tek basina verdigi ilk karari daha dogru hale getirir.

## 6) Lexical Exact Lookup Neden Kritik?

Yer adlarinda en buyuk hata kaynagi, benzer ama farkli isimlere kaymaktir.
Lexical exact lookup, bu riski azaltir.

Ornek:
`Maltepe` varsa direkt `Maltepe` secilir.
BERT sadece backup olarak kullanilir.

Bu sayede:
1. Gereksiz semantik sapmalar azalir.
2. Slot dogrulugu artar.
3. Cikti daha stabil olur.

## 7) Gold Test Seti Nasil Kullaniliyor?

Dosya:
`tests/data/bert_gold_tr_v1.jsonl`

Script:
`scripts/tools/evaluate_bert_gold.py`

Calisma mantigi:
1. Her test sorgusu `parse()` fonksiyonuna verilir.
2. Cikan alanlar beklenen alanlarla karsilastirilir.
3. Metrikler uretilir:
`case accuracy`, `field accuracy`, `latency p50/p95`.
4. Istendiginde markdown rapor yazilir.

Bu test seti modeli ezberletmek icin degil, degisikliklerden sonra kaliteyi olcmek icin kullanilir.

## 8) Kisa Ozet

Sistem su sirayla calisir:

`query -> normalize -> span -> lexical exact lookup -> BERT fallback -> intent refine -> slot filling -> final JSON`

Bu kurgu sayesinde hem serbest dogal dil daha iyi yakalanir, hem de yer adlarinda yanlis eslesme riski dusurulur.

## 9) GPU Calisma Notu (Onemli)

Bu projede BERT motoru varsayilan olarak GPU zorunlu moda alinmistir.

- Varsayilan: `ORP_BERT_FORCE_GPU=1`
- CUDA kullanilabilir degilse BERT motoru acik hata vererek durur.
- Gecici CPU fallback istenirse:
  - `ORP_BERT_FORCE_GPU=0`

GPU torch kurulumu (venv aktifken):

```bash
pip uninstall -y torch torchvision torchaudio
pip install --index-url https://download.pytorch.org/whl/cu124 torch torchvision torchaudio
```
