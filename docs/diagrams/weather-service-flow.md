# Hava Durumu Servisi - Akış Diyagramı

## Genel Akış Diyagramı

```mermaid
flowchart TD
    START([Kullanıcı İsteği]) --> ENDPOINT{Flask Endpoint}

    ENDPOINT --> |GET /api/weather| CURRENT[Endpoint: Güncel Hava]
    ENDPOINT --> |GET /api/weather/forecast| HOURLY[Endpoint: Saatlik Forecast]
    ENDPOINT --> |POST /api/weather/check-route| ROUTE[Endpoint: Rota Kontrolü]
    ENDPOINT --> |GET /api/weather/status| STATUS[Endpoint: Servis Durumu]
    ENDPOINT --> |GET /api/weather/health| HEALTH[Endpoint: Sağlık Kontrolü]
    ENDPOINT --> |POST /api/weather/clear-cache| CLEAR[Endpoint: Cache Temizle]

    subgraph "Validation Katmanı"
        VALIDATE_IN[Koordinat Validasyonu]
        VALIDATE_COORD[validate_coordinates]
        VALIDATE_HOURS[validate_hours]
        VALIDATE_TEMP[validate_temperature]
    end

    subgraph "Cache Katmanı"
        CACHE_KEY[build_cache_key]
        CACHE_CHECK[_get_from_cache]
        CACHE_HIT{Cache Hit?}
        CACHE_MISS[Cache Miss - API'ye Git]
        CACHE_SAVE[_save_to_cache]
        CACHE_TTL[TTL: 900 sn = 15 dk]
        CACHE_STATS[get_cache_stats]
    end

    subgraph "OpenMeteo API"
        API_URL[_build_url_current / _build_url_hourly]
        API_FETCH[_fetch_from_openmeteo]
        API_RESPONSE[JSON Response]
    end

    subgraph "Data Parsing"
        PARSE_CURRENT[_parse_current_weather]
        PARSE_HOURLY[_parse_hourly_forecast]
        PARSE_CODE[parse_weather_code]
        PARSE_EMOJI[get_weather_emoji]
    end

    subgraph "Analysis Functions"
        ANALYZE_ALERT[get_weather_alert]
        ANALYZE_SUGGEST[get_activity_suggestion]
        ANALYZE_UV[calculate_uv_index_risk]
        ANALYZE_HEAT[calculate_heat_index]
        ANALYZE_CHILL[calculate_wind_chill]
    end

    %% Ana Akış: Güncel Hava Durumu
    CURRENT --> VALIDATE_IN
    VALIDATE_IN --> VALIDATE_COORD
    VALIDATE_COORD --> |Geçersiz| ERROR[InvalidCoordinatesError]

    VALIDATE_COORD --> CACHE_KEY
    CACHE_KEY --> CACHE_CHECK
    CACHE_CHECK --> CACHE_HIT
    CACHE_HIT --> |Return Cached Data| RESPONSE_CURRENT[Response: Hava Durumu]

    CACHE_CHECK --> CACHE_MISS
    CACHE_MISS --> API_URL
    API_URL --> API_FETCH
    API_FETCH --> |Rate Limit Error| RATE_ERROR[RateLimitError]
    API_FETCH --> |Network Error| NET_ERROR[NetworkError]
    API_FETCH --> API_RESPONSE

    API_RESPONSE --> PARSE_CURRENT
    PARSE_CURRENT --> PARSE_CODE
    PARSE_CODE --> PARSE_EMOJI
    PARSE_EMOJI --> CACHE_SAVE
    CACHE_SAVE --> RESPONSE_CURRENT

    %% Ana Akış: Saatlik Forecast
    HOURLY --> VALIDATE_IN
    VALIDATE_IN --> VALIDATE_HOURS
    VALIDATE_HOURS --> |Geçersiz| ERROR

    VALIDATE_HOURS --> CACHE_KEY
    CACHE_KEY --> CACHE_CHECK
    CACHE_CHECK --> CACHE_HIT
    CACHE_HIT --> |Return Cached Data| RESPONSE_HOURLY[Response: Forecast]

    CACHE_CHECK --> CACHE_MISS
    CACHE_MISS --> API_URL
    API_URL --> API_FETCH
    API_RESPONSE --> PARSE_HOURLY
    PARSE_HOURLY --> CACHE_SAVE
    CACHE_SAVE --> RESPONSE_HOURLY

    %% Ana Akış: Rota Kontrolü
    ROUTE --> VALIDATE_IN
    VALIDATE_IN --> VALIDATE_COORD

    VALIDATE_COORD --> |Her Nokta İçin| LOOP_START[Loop: Noktalar]
    LOOP_START --> CURRENT
    CURRENT --> ANALYZE_ALERT
    ANALYZE_ALERT --> |Uyari Var| WARNINGS[Warnings Listesi]
    ANALYZE_ALERT --> COLLECT[Collect Results]

    LOOP_START --> |Sonraki Nokta| LOOP_START
    COLLECT --> EVALUATE[_evaluate_overall_conditions]
    EVALUATE --> RESPONSE_ROUTE[Response: Rota Hava Durumu]

    %% Status ve Health Check
    STATUS --> CACHE_STATS
    CACHE_STATS --> RESPONSE_STATUS[Response: Servis Durumu]

    HEALTH --> |Test API Call| CURRENT
    HEALTH --> |Success=True| HEALTH_OK[Healthy: True]
    HEALTH --> |Success=False| HEALTH_BAD[Healthy: False]

    %% Cache Temizleme
    CLEAR --> CLEAR_ALL[clear_cache]
    CLEAR_ALL --> RESPONSE_CLEAR[Response: Cache Temizlendi]

    %% Response Outputs
    RESPONSE_CURRENT --> JSON_OUT[JSON Response]
    RESPONSE_HOURLY --> JSON_OUT
    RESPONSE_ROUTE --> JSON_OUT
    RESPONSE_STATUS --> JSON_OUT
    HEALTH_OK --> JSON_BOOL[Boolean]
    HEALTH_BAD --> JSON_BOOL
    RESPONSE_CLEAR --> JSON_OUT
    ERROR --> ERROR_RESP[Error Response]

    JSON_OUT --> END([Response Dön])
```

## Cache Mekanizması Detaylı Diyagramı

```mermaid
sequenceDiagram
    participant Client as Kullanıcı/Frontend
    participant Endpoint as Flask API
    participant Validator as Validation
    participant Cache as Memory Cache
    participant API as OpenMeteo API
    participant Parser as Data Parser

    Client->>Endpoint: GET /api/weather?lat=41.0082&lon=28.9784

    Endpoint->>Validator: validate_coordinates(lat, lon)
    Validator-->>Endpoint: True (Geçerli)

    Endpoint->>Cache: build_cache_key("current", lat, lon)
    Cache-->>Endpoint: "current:41.0082:28.9784"

    Endpoint->>Cache: _get_from_cache(key)
    alt Cache Hit
        Cache-->>Endpoint: Cached Data (cache_hit: True)
        Endpoint-->>Client: 200 OK (Cached Data)
    else Cache Miss
        Cache-->>Endpoint: None

        Endpoint->>API: _build_url_current(lat, lon)
        Endpoint->>API: _fetch_from_openmeteo(url)
        API-->>Endpoint: JSON Response
        Endpoint->>Parser: _parse_current_weather(response)

        Parser->>Parser: parse_weather_code(code)
        Parser-->>Endpoint: Parsed Weather Data

        Endpoint->>Cache: _save_to_cache(key, data)
        Cache-->>Endpoint: Saved (timestamp: now)

        Endpoint-->>Client: 200 OK (Fresh Data)
    end

    Note over Cache, API: Cache TTL: 15 dakika
    Note over Parser: WMO Code → Emoji, TR açıklama
```

## get_current_weather Fonksiyonu Detaylı Akışı

```mermaid
flowchart TD
    START([get_current_weather çağrısı]) --> INPUT{lat, lon, use_cache=True}

    INPUT --> VALIDATE{Koordinat Validasyonu}
    VALIDATE --> |lat: -90 to 90| CHECK_LAT{Geçerli aralıkta mi?}
    VALIDATE --> |lon: -180 to 180| CHECK_LON{Geçerli aralıkta mi?}

    CHECK_LAT --> |Hayır| INVALID[InvalidCoordinatesError]
    CHECK_LON --> |Hayır| INVALID

    CHECK_LAT --> |Evet| BUILD_KEY
    CHECK_LON --> |Evet| BUILD_KEY{build_cache_key}

    BUILD_KEY --> CACHE_LOOKUP{_get_from_cache}
    CACHE_LOOKUP --> CACHE_DECISION{Cache'te var mi?}

    CACHE_DECISION -->|Evet| CACHE_HIT[✅ Cache HIT]
    CACHE_DECISION -->|Hayır| CACHE_MISS[❌ Cache MISS]

    CACHE_HIT --> RETURN_CACHE{cache_hit: True}
    RETURN_CACHE --> OUTPUT

    CACHE_MISS --> BUILD_URL{_build_url_current}
    BUILD_URL --> FETCH{_fetch_from_openmeteo}

    FETCH --> |Network Error| NET_ERR[NetworkError]
    FETCH --> |Rate Limit| RATE_ERR[RateLimitError]
    FETCH --> |Status ≠ 200| API_ERR[ParseError]
    FETCH --> |Success| RESPONSE[JSON Response]

    RESPONSE --> PARSE{_parse_current_weather}
    PARSE --> EXTRACT{temperature, humidity, weather_code, vb.}
    EXTRACT --> CONVERT{WMO code → TR açıklama, emoji}
    CONVERT --> SAVE_CACHE{_save_to_cache}

    SAVE_CACHE --> RETURN_FRESH{cache_hit: False}
    RETURN_FRESH --> OUTPUT

    OUTPUT --> SUCCESS[{"success": true, "data": {...}}]

    NET_ERR --> ERROR_RESPONSE
    RATE_ERR --> ERROR_RESPONSE
    API_ERR --> ERROR_RESPONSE
    INVALID --> ERROR_RESPONSE

    ERROR_RESPONSE --> END([Error Response])
    SUCCESS --> END
```

## check_route_weather Fonksiyonu Akışı

```mermaid
flowchart TD
    START([check_route_weather çağrısı]) --> INPUT{points: [{lat, lon, name}, ...]}

    INPUT --> CHECK_EMPTY{Nokta var mı?}
    CHECK_EMPTY --> |Hayır| VALUE_ERR[ValueError: En az 1 nokta]

    CHECK_EMPTY --> |Evet| INIT_LOOP{Her nokta için}
    INIT_LOOP --> GET_POINT{Noktayı al}

    GET_POINT --> EXTRACT_COORD{lat, lon çıkar}
    EXTRACT_COORD --> CHECK_COORD{Koordinat var mı?}

    CHECK_COORD --> |Hayır| ADD_ERROR{Hata ekle}
    CHECK_COORD --> |Evet| GET_WEATHER{get_current_weather}

    GET_WEATHER --> PARSE_DATA{current data}
    PARSE_DATA --> CHECK_ALERT{get_weather_alert}

    CHECK_ALERT --> |Uyari var| ADD_WARN{warnings listesine ekle}
    CHECK_ALERT --> |Uyari yok| ADD_RESULT{route_weather listesine ekle}

    ADD_WARN --> ADD_RESULT
    ADD_ERROR --> NEXT_POINT{Sonraki nokta}
    ADD_RESULT --> NEXT_POINT

    NEXT_POINT --> MORE_POINTS{Daha fazla nokta var mı?}
    MORE_POINTS --> |Evet| GET_POINT

    MORE_POINTS --> |Hayır| EVALUATE{_evaluate_overall_conditions}

    EVALUATE --> ANALYZE_CODES{Tum weather kodlarını topla}
    ANALYZE_CODES --> FIND_MAX{En yüksek kodu bul}

    FIND_MAX --> CATEGORIZE{Kategori belirle}
    CATEGORIZE --> |max ≤ 3| CLEAR[clear]
    CATEGORIZE --> |max ≤ 48| FOGGY[foggy]
    CATEGORIZE --> |max ≤ 82| RAINY[rainy]
    CATEGORIZE --> |max ≤ 86| SNOWY[snowy]
    CATEGORIZE --> |max > 86| STORMY[stormy]

    CLEAR --> OUTPUT
    FOGGY --> OUTPUT
    RAINY --> OUTPUT
    SNOWY --> OUTPUT
    STORMY --> OUTPUT

    OUTPUT --> SUCCESS[{"success": true, "data": {...}}]
    VALUE_ERR --> ERROR

    SUCCESS --> END
    ERROR --> END
```

## Data Yapıları ve Format Dönüşümleri

```mermaid
graph LR
    subgraph OpenMeteo API Response
        API1[["current": {...}]]
        API2[["hourly": {...}]]
    end

    subgraph Parsing
        P1[_parse_current_weather]
        P2[_parse_hourly_forecast]
    end

    subgraph WMO Code Processing
        WMO1[WMO Code: 0-99]
        WMO2[parse_weather_code]
    end

    subgraph Enhanced Data
        E1[description: "Clear sky"]
        E2[tr: "Acik gokyuzu"]
        E3[icon: "sun"]
        E4[category: "clear"]
        E5[emoji: "☀️"]
    end

    subgraph Final Response
        R1[{"success": true}]
        R2[{"data": {"location": {...}}}]
        R3[{"current": {...}}]
        R4[{"hourly": {...}}]
    end

    API1 --> P1
    API2 --> P2
    WMO1 --> WMO2
    WMO2 --> E1
    WMO2 --> E2
    WMO2 --> E3
    WMO2 --> E4
    WMO2 --> E5
    E1 --> R3
    E2 --> R3
    E5 --> R3
    P1 --> R1
    P2 --> R1
    R1 --> R2
```

## Hata Yakalama Akışı

```mermaid
flowchart TD
    START([İstek]) --> TRY_BLOCK{Try Block Başlat}

    TRY_BLOCK --> VALIDATION{Koordinat Validasyonu}
    VALIDATION --> |Geçersiz| INVALID[InvalidCoordinatesError]

    VALIDATION --> CACHE_CHECK{Cache Kontrolü}
    CACHE_CHECK --> API_CALL{OpenMeteo API Çağrısı}

    API_CALL --> |Network Timeout| NET_ERR[NetworkError: Request timeout]
    API_CALL --> |Connection Error| NET_ERR[NetworkError: Connection error]
    API_CALL --> |Status 429| RATE_ERR[RateLimitError: Rate limit exceeded]
    API_CALL --> |Status 5xx| NET_ERR[NetworkError: Server error]
    API_CALL --> |Status 4xx| PARSE_ERR[ParseError: API error]
    API_CALL --> |JSON Decode Error| PARSE_ERR[ParseError: Failed to parse JSON]

    API_CALL --> SUCCESS{Success: 200 OK}

    SUCCESS --> PARSE{Response Parse}
    PARSE --> |Missing field| PARSE_ERR

    PARSE --> SAVE_CACHE{Cache'e Kaydet}
    SAVE_CACHE --> RETURN[Success Response]

    INVALID --> LOG_ERROR[Log Error]
    NET_ERR --> LOG_ERROR
    RATE_ERR --> LOG_ERROR
    PARSE_ERR --> LOG_ERROR

    LOG_ERROR --> RAISE[Exception Fırlat]
    RAISE --> ERROR_RESPONSE[Error Response to Client]

    RETURN --> END([Response Dön])
    ERROR_RESPONSE --> END
```

## Component Mimari Diyagramı

```mermaid
graph TD
    subgraph "Flask API Layer"
        APP[app.py]
        E1["GET /api/weather"]
        E2["GET /api/weather/forecast"]
        E3["POST /api/weather/check-route"]
        E4["GET /api/weather/status"]
        E5["GET /api/weather/health"]
        E6["POST /api/weather/clear-cache"]
    end

    subgraph "Service Layer"
        SVC[weather_service.py]
        S1[get_current_weather]
        S2[get_hourly_forecast]
        S3[check_route_weather]
        S4[get_service_status]
        S5[health_check]
        S6[clear_cache]
        S7[get_multiple_locations_weather]
    end

    subgraph "Utility Layer"
        UTIL[weather_utils.py]
        U1[validate_coordinates]
        U2[validate_hours]
        U3[parse_weather_code]
        U4[get_weather_emoji]
        U5[build_cache_key]
        U6[get_weather_alert]
        U7[get_activity_suggestion]
        U8[calculate_heat_index]
        U9[calculate_wind_chill]
        U10[calculate_uv_index_risk]
    end

    subgraph "Cache Layer"
        CACHE[_weather_cache: dict]
        C1[_get_from_cache]
        C2[_save_to_cache]
        C3[_is_cache_valid]
        C4[get_cache_stats]
    end

    subgraph "External API"
        OPENMeteo[OpenMeteo API]
        URL["https://api.open-meteo.com/v1/forecast"]
    end

    APP --> E1
    APP --> E2
    APP --> E3
    APP --> E4
    APP --> E5
    APP --> E6

    E1 --> S1
    E2 --> S2
    E3 --> S3
    E4 --> S4
    E5 --> S5
    E6 --> S6

    S1 --> C1
    S1 --> C2
    S1 --> U1
    S1 --> U3

    S2 --> C1
    S2 --> C2
    S2 --> U2

    S3 --> S1
    S3 --> U6

    S1 --> URL
    S2 --> URL
    URL --> OPENMeteo
    OPENMeteo --> S1
    OPENMeteo --> S2

    S1 --> UTIL
    S2 --> UTIL
    S3 --> UTIL
    S4 --> C4

    C1 --> CACHE
    C2 --> CACHE
    C3 --> CACHE
    C4 --> CACHE
```

## Cache Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Idle: Cache Başlangıç

    Idle --> KeyBuild: Anahtar Oluşturuluyor
    KeyBuild --> Lookup: Cache Kontrolü

    Lookup --> Hit: ✅ Cache Hit (15 dk içinde)
    Lookup --> Miss: ❌ Cache Miss (15 dk dışı/süresi farklı)

    Hit --> ReturnData: Veri Dönüyor
    ReturnData --> Idle

    Miss --> FetchAPI: OpenMeteo API'den Çekiliyor
    FetchAPI --> ParseResponse: Response Parse Ediliyor
    ParseResponse --> Save: Cache'e Kaydediliyor

    Save --> ReturnData: Veri Dönüyor
    ReturnData --> Idle

    state Save {
        [*] --> Saving
        Saving --> Saved: ✓ Kayıt Başarılı
    }

    Saved --> Idle

    Idle --> Expire: 15 Dakika Sonra Expire Olur
    Expire --> Cleanup: Expired Cache Siliniyor
    Cleanup --> Idle

    Idle --> Clear: Manuel Temizleme
    Clear --> Purged: Tüm Cache Silindi
    Purged --> Idle

    note right of Hit
        TTL = 900 saniye
    end note

    note right of Miss
        API çağrısı yapılır
    end note

    note right of Save
        timestamp = time.now()
    end note
```

## Saatlik Forecast Akışı

```mermaid
flowchart TD
    START([get_hourly_forecast]) --> INPUT{lat, lon, hours=24, use_cache=True}

    INPUT --> VALIDATE1{validate_coordinates}
    VALIDATE1 --> |Geçersiz| INVALID_COORD

    VALIDATE1 --> VALIDATE2{validate_hours: 1-168}
    VALIDATE2 --> |Geçersiz| INVALID_HOURS

    VALIDATE2 --> BUILD_KEY{build_cache_key: "hourly", hours}
    BUILD_KEY --> CACHE_LOOKUP

    CACHE_LOOKUP --> HIT{✅ Cache Hit}
    CACHE_LOOKUP --> MISS{❌ Cache Miss}

    HIT --> RETURN_CACHED{cache_hit: True}
    RETURN_CACHED --> OUTPUT

    MISS --> BUILD_URL{_build_url_hourly}
    BUILD_URL --> API_CALL{_fetch_from_openmeteo}
    API_CALL --> API_RESP{JSON Response}

    API_RESP --> PARSE{_parse_hourly_forecast}
    PARSE --> EXTRACT{time[], temperature[], precipitation[], ...}
    EXTRACT --> SAVE_CACHE

    SAVE_CACHE --> RETURN_FRESH{cache_hit: False}
    RETURN_FRESH --> OUTPUT

    OUTPUT --> SUCCESS[{"success": true, "data": {"hourly": {...}}}]
    INVALID_COORD --> ERROR[InvalidCoordinatesError]
    INVALID_HOURS --> ERROR[ValueError]

    ERROR --> END
    SUCCESS --> END
```

## WMO Code Processing Pipeline

```mermaid
flowchart LR
    CODE[WMO Weather Code<br/>0-99 Tam Sayı] --> PARSE[parse_weather_code]

    subgraph "WMO_WEATHER_CODES Lookup"
        DICT[WMO_WEATHER_CODES<br/>46 Kod Map]
    end

    PARSE --> DICT
    DICT --> |Kod var mi?| CHECK{Kontrol}

    CHECK -->|Evet| EXTRACT{Bilgileri Çıkar}
    CHECK -->|Hayır| DEFAULT{Unknown Varsayılan}

    EXTRACT --> SPLIT{4 Bilgi Çıkar}
    SPLIT --> D1[description: "Clear sky"]
    SPLIT --> D2[tr: "Acik gokyuzu"]
    SPLIT --> D3[icon: "sun"]
    SPLIT --> D4[category: "clear"]

    D1 --> EMOJI[get_weather_emoji]
    D4 --> COLOR[get_weather_color_code]
    D4 --> CSS[get_weather_background_class]

    EMOJI --> E_OUT["☀️"]
    COLOR --> C_OUT["#FFD700"]
    CSS --> CSS_OUT["weather-clear"]

    DEFAULT --> D_OUT1[description: "Unknown"]
    DEFAULT --> T_OUT[tr: "Bilinmiyor"]
    DEFAULT --> I_OUT[icon: "question"]
    DEFAULT --> CAT_OUT[category: "unknown"]

    D_OUT1 --> EMOJI
    T_OUT --> EMOJI
    I_OUT --> EMOJI
    CAT_OUT --> COLOR
    CAT_OUT --> CSS
```

Bu diyagramlar hava durumu servisinin tüm akışını görsel olarak temsil etmektedir. Her biri farklı bir açıdan servisi gösterir:
1. **Genel Akış**: Tüm endpoint'ler ve veri akışı
2. **Cache Mekanizması**: Memory cache çalışma prensibi
3. **get_current_weather**: En çok kullanılan fonksiyon
4. **check_route_weather**: Rta bazlı hava kontrolü
5. **Hata Yakalama**: Exception handling
6. **Component Mimari**: Katmanlı yapı
7. **Cache Lifecycle**: Cache yaşam döngüsü
8. **Saatlik Forecast**: Forecast akışı
9. **WMO Code Processing**: Kod dönüşüm pipeline'ı
