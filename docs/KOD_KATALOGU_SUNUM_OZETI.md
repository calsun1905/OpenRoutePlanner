# OpenRoutePlanner Sunum Kod Katalogu

Bu dokuman, proje sunumu veya juri anlatimi icin hazirlanmis kisa kod katalogudur.

- Okuyucu: projeyi anlatacak ekip uyesi
- Amac: "hangi ana modül nerede, ne yapıyor, en kritik kısmı ne?" sorusuna hizli cevap vermek
- Not: Bu dokumanda bilerek dosya yolu ve satir araligi verilmistir; cunku hedefi uzun omurlu genel dokumantasyon degil, hizli teknik sunum destegidir.

## Hizli Harita

| Baslik | Dosya | Satir araligi | Ne yapar? | Sunumda en kritik nokta |
|---|---|---:|---|---|
| API omurgasi | `backend/app.py` | `1715-5367` agirlikli | Tum endpointleri toplar, validasyon yapar, dogru motoru cagirir | Uygulamanin orkestrasyon merkezi burasidir |
| BERT/NLP servisi | `backend/bert_nlp_engine.py` | `1611-2308` | Dogal dil sorgusunu niyet ve lokasyona ayirir | Sadece regex degil, embedding ve semantic matching kullanir |
| Rota motoru | `backend/route_engine_impl.py` | `76-1405` | Yaya rota, TSP, alternatif rota hesaplar | En kisa yol + alternatif rota heuristikleri ayni motorda toplanir |
| Toplu tasima motoru | `backend/multimodal_engine.py` | `2506-4969` agirlikli | Metro, otobus, metrobus, vapur secenekleri uretir | Graph tabanli multimodal route comparison yapar |
| OpenRouter provider | `backend/services/openrouter_service.py` | `305-541` | OpenRouter uzerinden cloud LLM cagrilari yapar | Fallback ve stream akisi desteklenir |
| Gemini provider | `backend/services/gemini_service.py` | `206-380` | Gemini uzerinden chat ve stream cagrilari yapar | Provider bazli fallback mantigi vardir |
| Local LLM provider | `backend/services/local_llm_service.py` | `179-276` | Yerel model ile chat ve stream cagrisi yapar | Internet olmadan veya dusuk maliyetli calisma icin kullanilir |
| RAG servisi | `backend/services/rag_service.py` | `77-147` | Bilgi tabanindan baglam getirir | Chat cevabini proje verisiyle destekler |
| Frontend rota ve AI paneli | `frontend/js/app.js` | `429-2487` agirlikli | Rota, alternatif rota, NLP ve LLM panel akisini yonetir | Tum backend yetenekleri UI'da burada gorunur |

## 1. API Omurgasi

### Dosya
- `backend/app.py`

### Temel bolumler
- `1715-1834`: `/api/get-route`
- `2014-2167`: `/api/get-alternative-routes`
- `2169-2312`: `/api/search-pois`
- `3145-3446`: NLP endpointleri
- `3527-3752`: hava durumu endpointleri
- `3774-4940`: LLM, provider ve RAG endpointleri
- `5180-5367`: transit ve multimodal endpointleri

### Gorevi
- Tum HTTP isteklerini alir
- Giris verisini dogrular
- Gerekirse geofence, cache ve queue kontrolu uygular
- Ilgili servis veya algoritma modülüne delege eder
- Tek tip JSON cevap dondurur

### En onemli kisim
- Projenin tum alt sistemleri farkli dosyalarda olsa da, kullanici davranisi burada birlestirilir.
- Sunumda "sistemin beyni degil ama trafik polisi" gibi anlatilabilir.

## 2. BERT / NLP Servisi

### Dosya
- `backend/bert_nlp_engine.py`

### Ana bolumler
- `912+`: `extract_candidate_spans`
- `1611-2308`: `class BertNLPEngine`
- `1702-1822`: `classify_query_type_with_scores`
- `1823-2109`: `extract_places`
- `2110-2308`: `parse`

### Gorevi
- Kullanici sorgusunun ne istedigini anlar
- Sorguyu `route`, `poi`, `multi`, `single`, `unknown` gibi tiplere ayirir
- Lokasyonlari ve POI niyetlerini ayiklar
- Gerekirse intent conflict matrix ile son karari dengeler

### En onemli kisim
- `parse` fonksiyonu (`2110+`) tum NLP akisini birlestiren merkezdir.
- En kritik teknik fark, yalnizca anahtar kelime aramasi degil:
  - template embedding
  - semantic similarity
  - span tabanli place extraction
  - conflict resolution

### Sunumda nasil anlatilir?
- "Kullanici 'Kadikoyden Besiktasa nasil giderim' dediginde sistem once niyeti anliyor, sonra yerleri cikariyor, sonra bu sonucu rota motoruna veriyor."

## 3. AI Servisleri ve Provider Katmani

Bu katman, uygulamanin farkli LLM saglayicilarina baglanmasini saglar.

### 3.1 OpenRouter

#### Dosya
- `backend/services/openrouter_service.py`

#### Ana bolumler
- `305-383`: `openrouter_chat_completion`
- `384-441`: `openrouter_chat_completion_with_fallback`
- `442-540`: `openrouter_chat_completion_stream`
- `541+`: `openrouter_chat_completion_stream_with_fallback`

#### Gorevi
- OpenRouter uzerinden model cagrisi yapmak
- Model fallback yonetmek
- Stream cevaplari desteklemek

#### En onemli kisim
- Tek provider cagrisi degil, fallback destekli provider cagrisi yapmasi

### 3.2 Gemini

#### Dosya
- `backend/services/gemini_service.py`

#### Ana bolumler
- `206-264`: `gemini_chat_completion`
- `265-295`: `gemini_chat_completion_with_fallback`
- `296-379`: `gemini_chat_completion_stream`
- `380+`: `gemini_chat_completion_stream_with_fallback`

#### Gorevi
- Gemini API icin chat ve stream katmani saglamak

#### En onemli kisim
- OpenRouter ile ayni mimariyi takip ederek provider degisimini kolaylastirmasi

### 3.3 Local LLM

#### Dosya
- `backend/services/local_llm_service.py`

#### Ana bolumler
- `179-241`: `local_llm_chat_completion`
- `242-275`: `local_llm_chat_completion_with_fallback`
- `276+`: `local_llm_chat_completion_stream`

#### Gorevi
- Yerel model cagrilarini yonetmek
- Harici provider yerine lokal inference secenegi sunmak

#### En onemli kisim
- Maliyet ve bagimsizlik icin local calisma yolunu acmasi

### 3.4 RAG

#### Dosya
- `backend/services/rag_service.py`

#### Ana bolumler
- `77-81`: `is_rag_available`
- `82-133`: `rag_status`
- `134-147`: `rag_query`

#### Gorevi
- Soruya uygun bilgi parcaciklarini veri tabanindan getirmek
- LLM cevabini proje/kurum bilgisiyla desteklemek

#### En onemli kisim
- Model tek basina cevap vermiyor; once baglam getirip sonra cevap kalitesini arttiriyor

## 4. Provider Endpointleri App Katmaninda Nerede?

### Dosya
- `backend/app.py`

### OpenRouter endpointleri
- `3856`: `/api/llm/openrouter/status`
- `3883`: `/api/llm/openrouter/chat`
- `3956`: `/api/llm/openrouter/chat/stream`
- `4177`: `/api/llm/openrouter/models`

### Gemini endpointleri
- `4194`: `/api/llm/gemini/status`
- `4219`: `/api/llm/gemini/chat`
- `4284`: `/api/llm/gemini/chat/stream`
- `4499`: `/api/llm/gemini/models`

### Local LLM ve RAG endpointleri
- `4519`: `/api/llm/local/status`
- `4544`: `/api/llm/local/models`
- `4557`: `/api/llm/rag/status`
- `4583`: `/api/llm/local/chat/rag`
- `4857`: `/api/llm/local/chat`
- `4940`: `/api/llm/local/chat/stream`

### En onemli kisim
- Provider secimi UI'da yapilsa da, asil yonlendirme ve koruma mantigi backend `app.py` uzerinden geciyor.

## 5. Yol Bulma ve Rota Hesaplama

### Dosya
- `backend/route_engine_impl.py`

### Ana bolumler
- `76-159`: `shortest_path`
- `162-184`: `nodes_to_coords`
- `187-329`: `solve_tsp`
- `332-1036`: `calculate_route_stats`
- `1039-1321`: `find_alternative_routes`
- `1322+`: `build_all_alternative_routes_batch`

### Gorevi
- Tek nokta veya cok nokta icin rota uretmek
- En kisa yolu hesaplamak
- Cok nokta varsa uygun ziyaret sirasini bulmak
- Alternatif rota secenekleri cikarmak

### En onemli kisim
- `solve_tsp` cok durakli gezilerde siralamayi optimize eder
- `find_alternative_routes` ise sadece tek rota degil, kullaniciya secim sunar

### Sunumda nasil anlatilir?
- "Birinci katman en kisa yolu buluyor, ikinci katman alternatif olasiliklar uretiyor."

## 6. Toplu Tasima ve Multimodal Yol Bulma

### Dosya
- `backend/multimodal_engine.py`

### Ana bolumler
- `2506-2689`: `_shortest_metro_path`
- `2690-3044`: `_build_graph_metro_option`
- `3045-3183`: `_build_ferry_only_options`
- `3420-3435`: `_normalize_allowed_modes`
- `3489-3531`: `_is_absurd_transit_option`
- `4274-4834`: `find_transit_routes`
- `4835+`: `compare_routes`

### Gorevi
- Metro, otobus, metrobus ve vapur gibi modlari birlikte degerlendirmek
- En makul toplu tasima adaylarini uretmek
- Sacma veya gercek disi secenekleri filtrelemek
- Son kullaniciya karsilastirilmis rota listesi sunmak

### En onemli kisim
- `find_transit_routes` ana orkestrasyon fonksiyonudur
- `compare_routes` ise sunulacak nihai cevabi toparlar
- Bu modülde sadece shortest path degil, uygulanabilirlik ve mantiklilik filtreleri de vardir

### Sunumda nasil anlatilir?
- "Bu katman yalnizca mesafe degil, transfer, mod uygunlugu ve kullanilabilirlik degerlendiriyor."

## 7. Frontend'de Bu Yeteneklerin Karsiligi

### Dosya
- `frontend/js/app.js`

### Rota tarafi
- `429`: `calculateRoute`
- `485`: `drawRoute`
- `2387`: `showAlternativeRoutes`
- `2428`: `displayAlternativeRoutes`

### NLP tarafi
- `1328`: `analyzeNaturalLanguageQuery`
- `1364`: `applyNlpResult`

### AI / chat tarafi
- `1616`: `mainLlmGetProvider`
- `1713`: `mainLlmFetchProviderModels`
- `2059`: `mainLlmSendMessage`
- `2294`: `initMainLlmChat`

### En onemli kisim
- Backend'deki teknik yeteneklerin kullaniciya gorunen buton, panel ve akislari burada toplanir

## 8. Sunumda Mutlaka Gecmesi Gereken 5 Teknik Nokta

1. `backend/app.py` sistemin orkestrasyon katmanidir; tum motorlar buradan cagrilir.
2. `backend/bert_nlp_engine.py` sadece regex degil, embedding tabanli niyet ve yer anlama yapar.
3. `backend/route_engine_impl.py` en kisa yol, TSP ve alternatif rota uretimini birlikte yonetir.
4. `backend/multimodal_engine.py` toplu tasimada graph tabanli karsilastirma ve filtreleme yapar.
5. `backend/services/*` katmani sayesinde ayni chat akisi OpenRouter, Gemini, local LLM ve RAG ile calisabilir.

## 9. Sunum Icin Kisa Anlatim Sirasi

Sunumda teknik akis su sirayla anlatilabilir:

1. Kullanici istegi frontend `app.js` tarafindan alinir.
2. Istek `backend/app.py` endpointine gider.
3. Eger dogal dil varsa `bert_nlp_engine.py` devreye girer.
4. Eger rota isteniyorsa `route_engine_impl.py` veya `multimodal_engine.py` devreye girer.
5. Eger AI sohbet isteniyorsa provider servisleri ve gerekirse `rag_service.py` devreye girer.
6. Sonuc tekrar `app.py` uzerinden JSON olarak frontend'e doner.
