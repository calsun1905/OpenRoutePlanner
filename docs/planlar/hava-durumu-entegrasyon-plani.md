# Hava Durumu Entegrasyon Plani

Bu dokuman, daha once gecici oturum kaydinda kalan hava durumu entegrasyon planinin repo icine alinmis halidir.

## Amac

Rota planlama deneyimini hava durumuna gore zenginlestirmek.

Hedefler:

1. Kullaniciya guncel hava bilgisi gostermek
2. Saatlik forecast ile rota zamanlamasini daha anlamli hale getirmek
3. Yagmur, sicaklik ve ruzgar gibi durumlarda akilli uyari vermek
4. Hava durumuna gore mekan onerileri uretebilmek

---

## Kullanici Ihtiyaclari

### 1. Hava durumuna gore tavsiye

- Sicaklik 30C+ ise su ve golge uyari
- Yagmur varsa semsiye ve kapali mekan uyari
- Planlanan saat ile forecast bilgisini karsilastirma

### 2. Zaman ve mekan baglami

- Rota boyunca saatlik hava gorunsun
- Timeline modunda her durak icin ilgili saat hava bilgisi eklensin
- "18:00'de Besiktas'ta yagmur var" gibi net uyari verilebilsin

### 3. API tercihi

- OpenMeteo
- Ucretsiz
- API key gerektirmiyor
- Turkiye icin yeterli veri sagliyor

### 4. Akilli oneriler

- Yagmurluysa AVM, kafe, kapali mekan
- Cok sicaksa klimali veya golgeli alan
- Ruzgarliyse korunakli alan onerisi

---

## Fazlar

### Faz 1: Temel Hava Servisi

Yeni dosyalar:

- `backend/weather_service.py`
- `backend/weather_utils.py`

Planlanan endpoint'ler:

- `GET /api/weather`
- `GET /api/weather/forecast`
- `POST /api/weather/check-route`

### Faz 2: Timeline Entegrasyonu

Degisecek dosyalar:

- `backend/time_planner.py`
- `frontend/js/app.js`

Beklenen davranis:

- Timeline segmentlerine hava bilgisi eklenir
- O saatteki yagmur ve sicaklik riski gosterilir
- Kullanicinin rota saatine gore uyari olusturulur

### Faz 3: Akilli Oneri Sistemi

Yeni dosya:

- `backend/weather_recommendations.py`

Beklenen davranis:

- Yagmurluysa kapali mekan arama
- Sicaksa klimali veya golgeli alan arama
- Ruzgarliyse korunakli alan arama
- OSM POI aramasi ile baglanti

---

## Etkilenecek Dosyalar

Yeni dosyalar:

- `backend/weather_service.py`
- `backend/weather_utils.py`
- `backend/weather_recommendations.py`

Degisecek dosyalar:

- `backend/app.py`
- `backend/time_planner.py`
- `backend/route_engine.py` (opsiyonel)
- `frontend/js/app.js`
- `frontend/css/style.css`
- `frontend/index.html`

---

## Teknik Notlar

OpenMeteo kullanimi:

```text
https://api.open-meteo.com/v1/forecast
```

Gerekli alanlar:

- `current`
- `hourly`
- `forecast_hours`
- `timezone=auto`

Cache stratejisi:

- Hava verisi 15 dakika cache'lenebilir
- Route bazli yagmur kontrolu kisa sureli memory cache kullanabilir

---

## Uygulama Sirasi

1. Faz 1 backend servis ve endpoint'ler
2. Basit hava widget'i
3. Timeline hava entegrasyonu
4. Akilli mekan onerileri
5. Rota kararlarina hava etkisini baglama

---

## Kabul Kriterleri (Olculebilir)

1. Faz 1 endpoint kapsami:
   - `GET /api/weather`, `GET /api/weather/forecast`, `POST /api/weather/check-route` endpoint'leri calisir durumda olmali
2. Faz 1 dogrulama:
   - Her endpoint icin en az 1 basarili + 1 hatali senaryo testi olmali
3. Performans:
   - Cache hit durumunda weather endpoint p95 <= 250 ms
   - Cache miss durumunda weather endpoint p95 <= 1200 ms
4. Cache davranisi:
   - Ayni lokasyon/saat araliginda 15 dk icinde tekrarlayan isteklerde dis API cagrisi azaltilmali (cache hit metriği kayda alinmali)
5. Faz 2 timeline entegrasyonu:
   - Timeline'da her segment icin en az `sicaklik`, `yagis olasiligi`, `ruzgar` alanlari gorunmeli
6. Faz 3 oneriler:
   - Hava kosuluna bagli en az 3 farkli kural (yagmur/sicak/ruzgar) aktif ve testli olmali

---

## Baglantili Dokumanlar

- `docs/planlar/bert-gelistirme-akisi.md`
- `progress.md`
- `gunluk-rapor/09.03.2026/09.03.2026.txt`
