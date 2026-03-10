# Hava Durumu Servisi - Akış Diyagramları

Bu doküman, hava durumu servisinin tüm akışlarını tek bir referans dosyasında toplar.

---

## 1. Ana Akış Özeti (Üst Seviye)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        HAVA DURUMU SERVİSİ - ANA AKIŞ                            │
└─────────────────────────────────────────────────────────────────────────────────┘

    [Kullanıcı İsteği]
            │
            ▼
    ┌───────────────┐
    │ Flask Endpoint │
    └───────┬───────┘
            │
    ┌───────┴───────┬───────────────┬───────────────┬───────────────┬───────────────┐
    │               │               │               │               │               │
    ▼               ▼               ▼               ▼               ▼               ▼
┌───────┐     ┌─────────┐    ┌──────────┐    ┌─────────┐    ┌─────────┐    ┌──────────┐
│/weather│     │/forecast│    │check-route│   │ /status │    │ /health │    │clear-cache│
│ (GET) │     │  (GET)  │    │  (POST)   │    │  (GET)  │    │  (GET)  │    │  (POST)   │
└───┬───┘     └────┬────┘    └─────┬─────┘    └────┬────┘    └────┬────┘    └─────┬─────┘
    │              │               │               │               │               │
    ▼              ▼               ▼               ▼               ▼               ▼
 Güncel Hava   Saatlik       Rota Boyunca    Cache Stats    API Test      Cache Temizle
```

---

## 2. Güncel Hava Akışı (get_current_weather)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    get_current_weather(lat, lon, use_cache)                        │
└─────────────────────────────────────────────────────────────────────────────────┘

    [BAŞLANGIÇ]
         │
         ▼
    ┌─────────────────┐
    │ Koordinat       │
    │ Validasyonu     │─── Geçersiz ──► [InvalidCoordinatesError]
    │ validate_coords │
    └────────┬────────┘
         │ Geçerli
         ▼
    ┌─────────────────┐
    │ build_cache_key │
    │ "current:lat:lon"│
    └────────┬────────┘
         │
         ▼
    ┌─────────────────┐      Evet      ┌──────────────────┐
    │ _get_from_cache │────────────────►│ cache_hit: True  │
    └────────┬────────┘                 │ Response Dön     │
         │ Hayır                        └────────┬─────────┘
         ▼                                              │
    ┌─────────────────┐                                 │
    │_build_url_current│                                │
    │ OpenMeteo URL   │                                 │
    └────────┬────────┘                                 │
         │                                              │
         ▼                                              │
    ┌─────────────────┐                                 │
    │_fetch_from_     │  429 ──► RateLimitError         │
    │ openmeteo       │  Timeout ──► NetworkError       │
    └────────┬────────┘  ≠200 ──► ParseError            │
         │ 200 OK                                       │
         ▼                                              │
    ┌─────────────────┐                                 │
    │_parse_current_  │                                 │
    │ weather         │                                 │
    │ • temperature   │                                 │
    │ • weather_code  │                                 │
    │ • parse_weather_code                              │
    │ • get_weather_emoji                               │
    └────────┬────────┘                                 │
         │                                              │
         ▼                                              │
    ┌─────────────────┐                                 │
    │ _save_to_cache  │                                 │
    │ TTL: 15 dk      │                                 │
    └────────┬────────┘                                 │
         │                                              │
         ▼                                              │
    ┌──────────────────┐                                │
    │ cache_hit: False │                                │
    │ Response Dön     │────────────────────────────────┘
    └────────┬─────────┘
             │
             ▼
        [BİTİŞ]
```

---

## 3. Saatlik Forecast Akışı (get_hourly_forecast)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                 get_hourly_forecast(lat, lon, hours=24, use_cache)                 │
└─────────────────────────────────────────────────────────────────────────────────┘

    [BAŞLANGIÇ]
         │
         ▼
    ┌─────────────────┐
    │ validate_coords │─── Geçersiz ──► InvalidCoordinatesError
    └────────┬────────┘
         │
         ▼
    ┌─────────────────┐
    │ validate_hours  │─── Geçersiz (1-168 dışı) ──► ValueError
    │ (1-168 arası)   │
    └────────┬────────┘
         │
         ▼
    ┌─────────────────┐
    │ build_cache_key │
    │ "hourly:lat:lon:24"
    └────────┬────────┘
         │
         ▼
    ┌─────────────────┐      Evet      ┌──────────────────┐
    │ _get_from_cache │────────────────►│ Cached Forecast  │
    └────────┬────────┘                 └────────┬─────────┘
         │ Hayır                                │
         ▼                                      │
    ┌─────────────────┐                         │
    │_build_url_hourly│                         │
    │ forecast_hours=24                         │
    └────────┬────────┘                         │
         │                                     │
         ▼                                     │
    ┌─────────────────┐                         │
    │_fetch_from_     │                         │
    │ openmeteo       │                         │
    └────────┬────────┘                         │
         │                                     │
         ▼                                     │
    ┌─────────────────┐                         │
    │_parse_hourly_   │                         │
    │ forecast        │                         │
    │ time[], temp[], │                         │
    │ precipitation[] │                         │
    └────────┬────────┘                         │
         │                                     │
         ▼                                     │
    ┌─────────────────┐                         │
    │ _save_to_cache  │                         │
    └────────┬────────┘                         │
             │                                 │
             └─────────────────────────────────┘
                          │
                          ▼
                     [BİTİŞ]
```

---

## 4. Rota Hava Kontrolü Akışı (check_route_weather)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│              check_route_weather(points: [{lat, lon, name}, ...])                  │
└─────────────────────────────────────────────────────────────────────────────────┘

    [BAŞLANGIÇ]
         │
         ▼
    ┌─────────────────┐
    │ points boş mu?  │─── Evet ──► ValueError
    └────────┬────────┘
         │ Hayır
         ▼
    ┌─────────────────────────────────────────────────────────┐
    │              DÖNGÜ: Her nokta için                       │
    └─────────────────────────────────────────────────────────┘
         │
         ▼
    ┌─────────────────┐
    │ lat, lon çıkar  │
    │ (lat/lon veya   │
    │  latitude/longitude)
    └────────┬────────┘
         │
    ┌────┴────┐
    │ Koordinat│
    │ var mı?  │
    └────┬────┘
    │    │
    Hayır│    Evet
    │    │
    ▼    ▼
┌───────┐  ┌─────────────────┐
│ Hata  │  │get_current_weather│
│ ekle  │  │ (lat, lon)       │
└───┬───┘  └────────┬────────┘
    │               │
    │               ▼
    │          ┌─────────────────┐
    │          │ get_weather_alert│
    │          │ Uyarı var mı?    │
    │          └────────┬────────┘
    │               │   │
    │          Var  │   │ Yok
    │               ▼   ▼
    │          ┌─────────────┐
    │          │ warnings[]  │
    │          │ route_weather[]│
    │          └──────┬──────┘
    │                 │
    └─────────────────┤
                      │
                      ▼
    ┌─────────────────────────────────┐
    │ Sonraki nokta var mı?            │
    │ Evet → Döngüye devam             │
    │ Hayır → Devam                    │
    └─────────────────┬───────────────┘
                      │
                      ▼
    ┌─────────────────────────────────┐
    │ _evaluate_overall_conditions     │
    │ • Tüm weather_code'ları topla    │
    │ • max_code bul                   │
    │ • Kategori: clear/foggy/rainy/   │
    │   snowy/stormy                   │
    └─────────────────┬───────────────┘
                      │
                      ▼
    ┌─────────────────────────────────┐
    │ Response:                        │
    │ • route_weather[]                │
    │ • warnings[]                     │
    │ • overall_conditions             │
    └─────────────────┬───────────────┘
                      │
                      ▼
                 [BİTİŞ]
```

---

## 5. Cache Mekanizması Akışı

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         CACHE YAŞAM DÖNGÜSÜ                                       │
└─────────────────────────────────────────────────────────────────────────────────┘

    [İstek Geldi]
         │
         ▼
    ┌─────────────────┐
    │ build_cache_key │
    │ prefix:lat:lon  │
    └────────┬────────┘
         │
         ▼
    ┌─────────────────┐
    │ _get_from_cache │
    │ key var mı?     │
    └────────┬────────┘
         │
    ┌────┴────┐
    │         │
    Var      Yok
    │         │
    ▼         ▼
┌────────┐  ┌────────────┐
│ TTL    │  │ Cache MISS │
│ kontrol│  │ → API'ye git│
└───┬────┘  └─────┬──────┘
    │             │
┌───┴───┐         │
│       │         │
<15dk  ≥15dk      │
│       │         │
▼       ▼         │
HIT   EXPIRE      │
│     Sil         │
│       │         │
▼       └─────────┤
│                 │
▼                 ▼
┌─────────────────────┐
│ Veri Dön            │
│ cache_hit: true/false│
└──────────┬──────────┘
           │
           ▼
    [Response]

    TTL = 900 saniye (15 dakika)
    Temizleme: clear_cache() veya TTL sonrası lazy delete
```

---

## 6. WMO Kod İşleme Akışı

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    WMO WEATHER CODE → KULLANICI ÇIKTISI                            │
└─────────────────────────────────────────────────────────────────────────────────┘

    [WMO Code: 0-99]
         │
         ▼
    ┌─────────────────┐
    │ parse_weather_code│
    │ WMO_WEATHER_CODES│
    │ sözlüğünde ara   │
    └────────┬────────┘
         │
    ┌────┴────┐
    │         │
  Var      Yok
    │         │
    ▼         ▼
┌────────┐  ┌────────────┐
│ Bilgi  │  │ Varsayılan │
│ çıkar  │  │ Unknown    │
└───┬────┘  │ Bilinmiyor │
    │       └─────┬──────┘
    │             │
    └──────┬──────┘
           │
           ▼
    ┌──────────────────────────────────────────┐
    │ Çıktılar:                                 │
    │ • description (EN)                        │
    │ • tr (TR)                                 │
    │ • icon                                    │
    │ • category                                │
    └──────────────────┬───────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
    ┌─────────┐  ┌──────────┐  ┌─────────────┐
    │get_     │  │get_      │  │get_weather_│
    │weather_ │  │weather_  │  │background_ │
    │emoji    │  │color_code│  │class       │
    └────┬────┘  └────┬─────┘  └──────┬──────┘
         │            │               │
         ▼            ▼               ▼
      "☀️"       "#FFD700"      "weather-clear"
```

---

## 7. Hata Yakalama Akışı

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         HATA YAKALAMA HİYERARŞİSİ                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

    [API Çağrısı]
         │
         ▼
    ┌─────────────────┐
    │ try:            │
    │ API işlemi      │
    └────────┬────────┘
             │
    ┌────────┴────────────────────────────────────────┐
    │                                                   │
    ▼                                                   ▼
[Başarı]                                          [Hata]
    │                                                   │
    │         ┌─────────────────────────────────────────┤
    │         │                                          │
    │         ▼                                          ▼
    │    ┌─────────────┐                          ┌─────────────┐
    │    │ Timeout     │ ──► NetworkError         │ except:     │
    │    │ Connection  │ ──► NetworkError         │ logger.error│
    │    │ 429         │ ──► RateLimitError       │ raise       │
    │    │ 5xx         │ ──► NetworkError         └──────┬──────┘
    │    │ 4xx         │ ──► ParseError                 │
    │    │ JSON parse  │ ──► ParseError                 ▼
    │    │ Koordinat   │ ──► InvalidCoordinatesError   │
    │    │ Geçersiz    │ ──► ValueError                 │
    │    └─────────────┘                                │
    │                                                   ▼
    │                                            [Error Response]
    │                                            Client'a 500/503
    │
    ▼
[Success Response]
```

---

## 8. Katman Mimarisi (Dikey Akış)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         KATMANLI MİMARİ                                           │
└─────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────┐
    │  FLASK API (app.py)                                      │
    │  /api/weather | /api/weather/forecast | check-route     │
    └───────────────────────────┬─────────────────────────────┘
                                │
                                ▼
    ┌─────────────────────────────────────────────────────────┐
    │  SERVICE (weather_service.py)                            │
    │  get_current_weather | get_hourly_forecast |             │
    │  check_route_weather | get_service_status | health_check │
    └───────────────────────────┬─────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │ CACHE         │ │ UTILS         │ │ EXTERNAL API  │
    │ _weather_cache│ │ weather_utils │ │ OpenMeteo     │
    │ _get_from_    │ │ validate_*    │ │ api.open-     │
    │ _save_to_     │ │ parse_weather_│ │ meteo.com     │
    │ get_cache_    │ │ get_weather_  │ │               │
    │ stats         │ │ emoji         │ │               │
    └───────────────┘ └───────────────┘ └───────────────┘
```

---

## 9. Veri Dönüşüm Akışı

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    API RESPONSE → UYGULAMA FORMATI                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

    OpenMeteo API                    weather_service.py                 Frontend
    ─────────────                    ─────────────────                 ────────

    current: {                 _parse_current_weather()           {
      time: "2026-03-10T12:00"   → timestamp (ISO)                    success: true,
      temperature_2m: 12.9     → temperature                         data: {
      weather_code: 0          → weather_code                           location: {...},
      ...                     → parse_weather_code() →                  current: {
    }                           weather_tr: "Acik gokyuzu"               temperature: 12.9,
                                → get_weather_emoji() → "☀️"            weather_tr: "...",
                                                                        weather_emoji: "☀️",
                                                                        ...
                                                                      },
                                                                      cache_hit: false
                                                                    }
                                                                  }
```

---

## Özet Tablo

| Diyagram | Açıklama |
|----------|----------|
| 1. Ana Akış | Tüm endpoint'lerin üst seviye görünümü |
| 2. get_current_weather | Güncel hava akışı (cache + API + parse) |
| 3. get_hourly_forecast | Saatlik tahmin akışı |
| 4. check_route_weather | Rota boyunca hava kontrolü döngüsü |
| 5. Cache Mekanizması | TTL, hit/miss, temizleme |
| 6. WMO Kod İşleme | Kod → açıklama, emoji, renk |
| 7. Hata Yakalama | Exception türleri ve akışı |
| 8. Katman Mimarisi | Flask → Service → Cache/Utils/API |
| 9. Veri Dönüşümü | API formatı → uygulama formatı |
