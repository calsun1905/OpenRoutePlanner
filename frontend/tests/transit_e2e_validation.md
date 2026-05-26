# Transit E2E Validation Set

Bu dosya, `frontend/js/transit.js` akisi icin manuel/yarim-otomatik E2E dogrulama protokoludur.

## Genel On Kosullar
- Backend calisiyor ve transit verisi ulasilabilir.
- Frontend haritasi aciliyor.
- Tarayici console acik (JS hata takibi icin).
- Test kaydi icin ekran goruntusu alinabiliyor.

## Kanit Toplama Kurali
Her senaryo icin:
- En az 1 ekran goruntusu
- Varsa console hatasi metni
- Sonuc: PASS/FAIL

---

## Senaryo 1 - Transit paneli ac/kapat

### On kosul
- Uygulama acik.

### Adimlar
1. Sag panelde transit/sohbet bolgesini daralt.
2. Tekrar ac.
3. Bu islemi art arda 3 kez yap.

### Beklenen sonuc
- Panel her seferinde acilip kapanir.
- UI donmaz, butonlar yanit verir.

### Basarisizlik belirtileri
- Buton tiklanir ama panel durumu degismez.
- Console'da JS exception.

### Kanit
- `S1-open.png`, `S1-closed.png`

---

## Senaryo 2 - Transit secenegi secildiginde rota cizimi olusur

### On kosul
- Multimodal secenek listesi gorunur.

### Adimlar
1. Bir transit secenegine tikla.
2. Haritada cizgi/layer olustugunu gozlemle.

### Beklenen sonuc
- En az bir segment cizilir.
- Harita bounds secilen rotaya oturur.

### Basarisizlik belirtileri
- Secenek secilir ama hic cizim olmaz.
- Harita hic hareket etmez.

### Kanit
- `S2-route-drawn.png`

---

## Senaryo 3 - Transit-only modda yurume segment gorunurlugu

### On kosul
- Secilen opsiyon `type=transit`.

### Adimlar
1. Transit-only rota cizimini ac.
2. Segmentleri incele.

### Beklenen sonuc
- Ara yuruyus segmentleri gizlenir.
- Sadece baslangic/bitis erisim yuruyusleri kalir.

### Basarisizlik belirtileri
- Tum yuruyus segmentleri gorunur (gorsel kalabalik).
- Endpoint walk segmentleri de kaybolur.

### Kanit
- `S3-transit-only-walk-filter.png`

---

## Senaryo 4 - Bus/Rail/Ferry cizim stili dogrulama

### On kosul
- En az bir bus/rail/ferry segmenti olan rota.

### Adimlar
1. Bus segmentli rota sec.
2. Rail segmentli rota sec.
3. Ferry segmentli rota sec.

### Beklenen sonuc
- Bus ve rail kalin/renkli line olarak cizilir.
- Ferry segment dash (kesikli) stil ile gelir.

### Basarisizlik belirtileri
- Tum modlar ayni stilde cizilir.
- Ferry kesikli cizilmez.

### Kanit
- `S4-bus.png`, `S4-rail.png`, `S4-ferry.png`

---

## Senaryo 5 - Route label gorunumu

### On kosul
- Transit segmentte `route_code` mevcut.

### Adimlar
1. Rota cizildikten sonra orta nokta etiketlerini kontrol et.
2. Metrobus kodu varsa etiket formatini kontrol et.

### Beklenen sonuc
- Segment ortasinda route label gorunur.
- Metrobus icin ozel etiket sinifi/formati uygulanir.

### Basarisizlik belirtileri
- Etiket hic cikmaz.
- Yanlis route kodu gorunur.

### Kanit
- `S5-route-label.png`

---

## Senaryo 6 - Bos/eksik segmentte graceful davranis

### On kosul
- Segment `coords` eksik veya 2'den az.

### Adimlar
1. Bilerek eksik koordinatli bir secenek sec (veya mock data ile).
2. Cizim akisini izle.

### Beklenen sonuc
- Uygulama cokermez.
- Eksik segment atlanir, diger segmentler cizilmeye devam eder.

### Basarisizlik belirtileri
- Runtime exception ile akisin durmasi.
- Tum rota ciziminin iptal olmasi.

### Kanit
- `S6-graceful-skip.png`, console log

---

## Senaryo 7 - Rota degistirince onceki layer temizligi

### On kosul
- En az iki farkli transit secenegi.

### Adimlar
1. Secenek A'yi ac.
2. Secenek B'ye gec.

### Beklenen sonuc
- A'ya ait layer/marker temizlenir.
- Sadece B'ye ait layer gorunur.

### Basarisizlik belirtileri
- Eski rota hayalet cizgi olarak kalir.
- Marker birikmesi olur.

### Kanit
- `S7-before-after.png`

---

## Senaryo 8 - Segment bazli marker kurallari

### On kosul
- Transit-only disi gorunumde segment markerlari acik.

### Adimlar
1. Walk segmentte baslangic markerini kontrol et.
2. Rail/Bus/Ferry segmentlerinde binis/inis markerlarini kontrol et.

### Beklenen sonuc
- Walk -> `W` markeri.
- Transit segment -> `B` ve `I` markerleri.

### Basarisizlik belirtileri
- Marker tipleri yanlis.
- Markerlar rastgele veya eksik.

### Kanit
- `S8-markers.png`

---

## Senaryo 9 - Zoom/fitBounds davranisi

### On kosul
- Rota en az 2 nokta iceriyor.

### Adimlar
1. Rota sec ve harita konumunu gozlemle.
2. Farkli rota sec ve yeniden gozlemle.

### Beklenen sonuc
- Harita rota kapsamina fit edilir.
- Asiri zoom-in/out yapmaz (kullanilabilir seviyede kalir).

### Basarisizlik belirtileri
- Harita ayni yerde kalir.
- Rota ekran disinda kalir.

### Kanit
- `S9-fitbounds.png`

---

## Senaryo 10 - Hata dayanikliligi (console)

### On kosul
- Tarayici console acik.

### Adimlar
1. Senaryo 1-9 boyunca console'u izle.
2. Kritik error stack var mi kontrol et.

### Beklenen sonuc
- Engelleyici uncaught exception yok.

### Basarisizlik belirtileri
- `TypeError`, `Cannot read properties of undefined`, `Unhandled promise rejection` gibi kritik hatalar.

### Kanit
- `S10-console.png` veya export edilmis log

---

## PASS/FAIL Rapor Sablonu

```
Test Date:
Tester:
Build/Commit:
Environment:

S1: PASS/FAIL - Notes:
S2: PASS/FAIL - Notes:
S3: PASS/FAIL - Notes:
S4: PASS/FAIL - Notes:
S5: PASS/FAIL - Notes:
S6: PASS/FAIL - Notes:
S7: PASS/FAIL - Notes:
S8: PASS/FAIL - Notes:
S9: PASS/FAIL - Notes:
S10: PASS/FAIL - Notes:

Blocking Issues:
- 

Non-blocking Issues:
- 

Overall Result: PASS / FAIL
```
