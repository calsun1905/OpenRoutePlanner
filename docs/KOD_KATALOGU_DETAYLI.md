# OpenTrip Tam Kod Katalogu (Temiz UTF-8)

Bu dokuman tum ana dosyalar icin satir araligi + fonksiyon + akis + cagrilar + algoritma bilgisini verir.

## Onsoz - Hizli Yol Haritasi

Bu bolum, raporu okurken \"nerede ne var\" sorusuna hizli cevap vermek icin eklendi.

### A) Bu Dokuman Icinde Nerede Ne Var?

- `Bolum 1`: Dosya boyutlari (hangi dosya kac satir).
- `Bolum 2`: `backend/app.py` tum endpointler (tek tek route/method/amac/cagrilar/hata kodlari).
- `Bolum 3`: `app.py` yardimci fonksiyonlar (endpoint disi orchestration/utility katmani).
- `Bolum 4`: `frontend/js/app.js` UI katalogu (bolum basliklari + tum fonksiyonlar).
- `Bolum 5`: `backend/bert_nlp_engine.py` katalogu (NLP/BERT akislari, parse cekirdegi).
- `Bolum 6`: `backend/multimodal_engine.py` katalogu (toplu tasima algoritmalari).
- `Bolum 7`: `backend/route_engine_impl.py` katalogu (yaya rota + alternatif rota algoritmalari).
- `Bolum 8`: Uctan uca akislari (UI -> API -> Engine) kisa baglanti listesi.
- `Bolum 9`: Notlar (sunum oncesi satir numarasi senkron kontrolu vb.).

### B) Kodda Ana Konular Nerede?

- `BERT/NLP`:
- Dosya: `backend/bert_nlp_engine.py`
- Kritik parse hatti: `1887-2276` (`parse`)
- Place extraction: `1644-1783`
- Intent scoring: `1528-1587`

- `Multimodal Toplu Tasima`:
- Dosya: `backend/multimodal_engine.py`
- Ana orkestrasyon: `find_transit_routes` `4274-4834`
- Karsilastirma cevabi: `compare_routes` `4835-4969`
- Metro graph shortest-path: `_shortest_metro_path` `2506-2689`

- `Yaya Rota ve Alternatifler`:
- Dosya: `backend/route_engine_impl.py`
- TSP siralama: `solve_tsp` `187-298`
- Alternatif rota motoru: `find_alternative_routes` `1039-1272`
- Batch alternatif birlestirme: `1322-1405`

- `API Omurgasi`:
- Dosya: `backend/app.py`
- Rota endpointleri: agirlikli olarak `1715-2310`
- CRUD bloklari: agirlikli olarak `2547-3139`
- Weather bloklari: agirlikli olarak `3522-3768`
- LLM/RAG bloklari: agirlikli olarak `3769-5174`
- Transit/Multimodal endpointleri: agirlikli olarak `5175-5478`

- `Frontend UI Omurgasi`:
- Dosya: `frontend/js/app.js`
- Rota cizim/hesap: `395-509`
- POI arama: `583-732`
- NLP paneli: `1200-1528`
- LLM paneli: `1409-2344`
- Saved routes/locations: `2539-3335`
- Weather UI: `3336-3810`

### C) Temel Moduller (Buyuk Resim)

Bu kisim, \"her minik fonksiyon\" yerine sunumda dogrudan anlatabilecegin ana modulleri verir.

1. **API Orkestrasyon Modulu**
- Dosya: `backend/app.py`
- Gorev: Tum HTTP endpointleri toplar, request validasyonu yapar, ilgili motoru cagirir ve response sozlesmesini doner.
- Kritik alt alanlar:
- Rota/POI/Geocode endpointleri
- NLP/BERT endpointleri
- LLM/RAG endpointleri
- Transit/Multimodal endpointleri
- Weather endpointleri

2. **Rota Motoru Modulu (Yaya + Alternatif)**
- Dosya: `backend/route_engine_impl.py`
- Gorev: En kisa rota, TSP siralama, alternatif rota uretimi ve rota istatistiklerini hesaplar.
- Kullanilan yaklasimlar:
- NetworkX shortest path (weighted)
- TSP tabanli sira optimizasyonu
- Penalty/disjoint/via-node ile alternatif geometri uretimi

3. **Toplu Tasima Motoru Modulu (Multimodal)**
- Dosya: `backend/multimodal_engine.py`
- Gorev: Otobus/metro/metrobus/vapur secimlerine gore toplu tasima adaylari uretir ve karsilastirir.
- Kullanilan yaklasimlar:
- Durak ve hat graph modeli
- State-space shortest path (transfer/ferry durumu dahil)
- Mode-kisit, absurd option filtreleme, cesitlendirme

4. **NLP Anlama Modulu (BERT)**
- Dosya: `backend/bert_nlp_engine.py`
- Gorev: Dogal dil sorgusunu `route/poi/multi/single/unknown` tiplerine ayirir, yer adlarini semantik olarak cikarir.
- Kullanilan yaklasimlar:
- Template embedding + hard-negative intent siniflandirma
- Span tabanli yer adayi cikarimi
- Semantic benzerlik ile place eslestirme
- Intent conflict matrix ile son karar dengeleme

5. **LLM + RAG Entegrasyon Modulu**
- Ana dosya: `backend/app.py` (LLM endpoint orkestrasyonu)
- RAG karar akisi: `app.py` icindeki RAG yardimcilari + `rag_service`
- Gorev: Query bazli RAG kullanimi, similarity dusukse fallback, local/openrouter/gemini model akisini yonetmek.
- Cikti disiplini:
- Kaynak/benzerlik bazli cevap politikalari
- Session tabanli chat gecmisi
- Stream veya sync response modu

6. **Frontend Uygulama Modulu**
- Dosya: `frontend/js/app.js`
- Gorev: Harita etkileşimi, rota/POI/NLP/LLM panelleri, kaydedilen rota-lokasyonlar, weather paneli gibi tum UX akislarini yonetir.
- Ana UI akislari:
- Nokta sec -> rota hesapla -> alternatif rota sec
- POI kategori sec -> bolge bazli arama -> marker render
- NLP sorgu analiz et -> haritaya uygula
- LLM paneliyle provider/model bazli sohbet

7. **Veri ve Cache Katmani**
- Dosyalar: `multimodal_engine.py` cache bloklari, `app.py` route response cache, proje icindeki db/cache servisleri
- Gorev: Tekrarlayan sorgulari hizlandirmak, API maliyetini azaltmak, systemin stabilitesini artirmak.

8. **Hava Durumu Servis Modulu**
- Ana endpoint orkestrasyonu: `backend/app.py` weather bloklari
- Gorev: Nokta bazli anlik hava, saatlik tahmin, rota bazli hava riski, weather cache ve saglik izleme.

### D) Sunum Icin En Temel Teknik Cekirdek (Modul Modul)

Bu kisim, juri sorularinda en cok gelen \"hangi algoritma nerede\" sorusuna direkt cevap verir.

1. **Yol Bulma Algoritmasi (Yaya Rota)**
- Dosya: `backend/route_engine_impl.py`
- `shortest_path` `76-97`: Temel en kisa yol hesabi (weighted shortest path / Dijkstra tabanli).
- `solve_tsp` `187-298`: Cok nokta varsa ziyaret sirasini optimize eder (TSP akisi).
- Nerede kullaniliyor: `backend/app.py` icindeki `/api/get-route` akisi.

2. **Alternatif Rota Algoritmasi**
- Dosya: `backend/route_engine_impl.py`
- `find_alternative_routes` `1039-1272`: Alternatif geometri uretir (disjoint + penalty + via-node yaklasimi).
- `build_all_alternative_routes_batch` `1322-1405`: Segment bazli adaylari birlestirip 3 tam rota cikarir.
- Nerede kullaniliyor: `backend/app.py` icindeki `/api/get-alternative-routes`.

3. **Toplu Tasima Yol Bulma Algoritmasi (Multimodal)**
- Dosya: `backend/multimodal_engine.py`
- `_shortest_metro_path` `2506-2689`: Durum uzayinda shortest path (station + line + transfer + ferry).
- `_build_graph_metro_option` `2690-3044`: Aday duraklari artan yaricaplarla toplayip en iyi varyanti secer.
- `find_transit_routes` `4274-4834`: Tum toplu tasima adaylarini uretir, filtreler ve mod kisitlarini uygular.
- `compare_routes` `4835-4969`: Nihai karsilastirma/onerilen sonuc cevabini olusturur.

4. **NLP/BERT Algoritmasi (Niyet + Yer Cikarimi)**
- Dosya: `backend/bert_nlp_engine.py`
- `classify_query_type_with_scores` `1528-1587`: Intent siniflandirma (template embedding + hard-negative).
- `extract_places` `1644-1783`: Yer adayi span cikarimi + semantik eslestirme.
- `parse` `1887-2276`: Tum NLP pipeline (query guard -> intent -> place -> conflict matrix -> final).
- Nerede kullaniliyor: `backend/app.py` icindeki `/api/nlp/parse`.

5. **Yapay Zeka Chat Yonetimi (Session + Provider + Stream)**
- Backend dosyasi: `backend/app.py`
- Session yonetimi endpointleri:
- `api_llm_chat_sessions` `3769-3787`
- `api_create_llm_chat_session` `3788-3800`
- `api_llm_chat_session_messages` `3801-3824`
- `api_archive_llm_chat_session` `3825-3835`
- Provider chat stream endpointleri:
- `api_openrouter_chat_stream` `3951-4171`
- `api_gemini_chat_stream` `4279-4493`
- Local/RAG chat endpointleri:
- `api_local_llm_chat_rag` `4578-4848`
- `api_local_llm_chat` `4852-4931`

6. **Yapay Zeka Chat UI Yonetimi**
- Frontend dosyasi: `frontend/js/app.js`
- `initMainLlmChat` `2252-2344`: Chat panel baslatma, event baglama, provider/model durum init.
- `mainLlmLoadSessions` `1841-1851`: Oturum listesini backendden ceker.
- `mainLlmCreateSession` `1852-1865`: Yeni oturum olusturur.
- `mainLlmSetActiveSession` `1885-1901`: Aktif oturumu degistirir.
- `mainLlmSendMessage` `2017-2251`: Mesaj gonderme (local RAG veya stream provider akisi).

### E) Moduller Ne Yapar? (Detayli Teknik Anlatim)

Bu bolum, "kucuk fonksiyon listesi" yerine juriye anlatimda kullanacagin cekirdek modul seviyesini verir.

1. **`backend/app.py` - API Orkestrasyon Modulu**
- Rol: Sistemin giris kapisi burasidir. Frontendden gelen tum HTTP istekleri burada dogrulanir, dogru motora yonlendirilir ve tek tip JSON cevap uretilir.
- Teknik akis:
- Adim 1: `request.get_json(...)` veya query parametreleri okunur.
- Adim 2: Girdi validasyonu yapilir (`points`, `lat/lon`, `query`, `allowed_modes` vb.).
- Adim 3: Gerekliyse geofence uygulanir (`_first_outside_point`, `_outside_istanbul_response`).
- Adim 4: Cache kontrolu yapilir (`_route_response_cache_get`) ve cache hit ise hesaplama atlanir.
- Adim 5: Ilgili motor cagrilir (route engine, multimodal engine, BERT parser, weather, LLM).
- Adim 6: Sonuc normalize edilip `jsonify(...)` ile doner.
- Kritik degiskenler:
- `route_cache_key`: ayni rota istegini deterministik anahtarla temsil eder.
- `cached_response`: hesaplama yerine daha onceki sonucu doner.
- `queue_wait_ms`, `permit_acquired`: NLP ve multimodal endpointlerde eszamanlilik kontrolu.
- `rag_used`, `rag_skip_reason`, `rag_result`: local chatte RAG karar kayitlari.
- Neden kritik: Alt sistemler farkli olsa da uygulamanin davranisini tutarli yapan katman budur.

2. **`backend/route_engine_impl.py` - Yaya Rota ve Alternatif Rota Modulu**
- Rol: Yol bulma ve alternatif yol uretiminin ana matematiksel cekirdegidir.
- Teknik akis (tek rota):
- Adim 1: Noktalar nearest-node ile graph dugumlerine map edilir.
- Adim 2: `shortest_path(...)` ile segmentlerin en kisa yolu bulunur.
- Adim 3: Segmentler birlestirilir, `nodes_to_coords(...)` ile cizim koordinatina donusturulur.
- Adim 4: `calculate_route_stats(...)` ile km ve sure hesaplanir.
- Teknik akis (cok nokta):
- Adim 1: `solve_tsp(...)` distance matrix kurar.
- Adim 2: Ulasilamayan ciftler `unreachable_pairs` olarak yakalanir.
- Adim 3: Gecerliyse optimize ziyaret sirasi uretilir.
- Teknik akis (alternatif rota):
- `find_alternative_routes(...)` disjoint + penalty + via-node kombinasyonuyla farkli geometri adaylari uretir.
- `build_all_alternative_routes_batch(...)` segment adaylarini birlestirip route_1/2/3 uretir.
- Kritik degiskenler:
- `dist_matrix`: TSP ciftler arasi maliyet matrisi.
- `directed_reachable`: baglanabilirlik kontrolu.
- `alternatives`: alternatif aday listesi.
- `full_nodes`: birlestirilmis final rota dugum dizisi.
- Algoritmalar: weighted shortest path, TSP optimizasyonu, penalty/disjoint/via-node heuristikleri.

3. **`backend/multimodal_engine.py` - Toplu Tasima Karar ve Karsilastirma Modulu**
- Rol: Metro/otobus/metrobus/vapur secimlerini dikkate alip uygulanabilir transit rotalari uretir.
- Teknik akis:
- Adim 1: `allowed_modes` normalize edilir (`_normalize_allowed_modes`).
- Adim 2: Direkt yurume referansi hesaplanir (`direct_walk_m`, `direct_walk_min`).
- Adim 3: Durak/hat adaylari artan yaricapla toplanir.
- Adim 4: Baglanti adaylari uzerinden transit segmentleri olusturulur.
- Adim 5: Mantiksiz secenekler filtrelenir (`_is_absurd_transit_option`, jump kontrolleri).
- Adim 6: Cesitlendirme yapilir (`_diversify_transit_options`).
- Adim 7: `compare_routes(...)` final cevap + telemetry uretir.
- Metro graph cekirdegi:
- `_shortest_metro_path(...)` state-space shortest path kullanir.
- State: `(station_id, current_line, transfer_count, used_ferry)`.
- Bu state sayesinde "az aktarma" ve "ferry kullanimi" maliyete yansitilir.
- Kritik degiskenler:
- `allowed_user_modes`: kullanici seciminin normalize seti.
- `line_map`, `station_map`, `graph`: transit graph veri yapisi.
- `transit_options`, `merged`: ham ve final secenek listeleri.
- `transfer_count`, `total_time_min`: oneri kararinin ana metrigi.

4. **`backend/bert_nlp_engine.py` - NLP Anlama Modulu (Detayli)**
- Rol: Serbest metin sorgusunu sistemin anlayacagi yapisal parse sonucuna cevirir.
- Bu modulle ilgili en kritik nokta: "metin -> niyet + yer + rol" donusumunu tek boru hattinda yapmasidir.
- Pipeline adimlari:
- Adim 1: **Normalize**
- `normalize_query_text(...)` ile apostrof/bosluk varyasyonlari normalize edilir.
- `normalize_token_with_role(...)` token son eklerinden rol ipucu cikarir (`from`, `to`, `loc`).
- Adim 2: **Intent siniflandirma**
- `classify_query_type_with_scores(...)` query embedding uretir.
- Template embeddingleriyle cosine score hesaplar.
- Hard-negative seti ile chitchat metnin route/poiye kaymasini azaltir.
- Cikti: `query_type`, `confidence`, `type_scores`.
- Adim 3: **Yer cikarimi (semantic)**
- `extract_candidate_spans(...)` tek token + n-gram span adaylari cikarir.
- `extract_places(...)` her span icin embedding benzerligiyle place eslestirir.
- Role hint, token sayisi ve similarity esikleriyle false-positive temizler.
- Cikti: `detected_places` + `ordered_places`.
- Adim 4: **Yon ve niyet dengeleme**
- `detect_route_direction(...)` origin/destination secimini rol ve konuma gore yapar.
- `apply_intent_conflict_matrix(...)` celisen sinyalleri dengeler.
- `should_rescue_poi_intent(...)` POI niyetini geri kazanma mantigi uygular.
- Adim 5: **Final parse objesi**
- `parse(...)` finalde `type`, `origin/destination/location`, `confidence`, `trace` dondurur.
- Kritik degiskenler:
- `query_embedding`: tum semantic kararlarin vektor temeli.
- `type_scores`, `score_margin`: intent guven dagilimi.
- `detected_places`, `role_hints`: yer ve yon sinyalleri.
- `poi_resolution`, `intent_matrix_meta`: POI ve conflict karar metasi.
- Nerede kullanilir: `app.py` -> `/api/nlp/parse` endpointi.
- Neden kritik: Yanlis parse, rota/POI akisinin tamamen yanlis endpointlere gitmesine neden olur.

#### NLP Yaklasimlari - Ne Demek, Kodda Nasil Yapiliyor?

1. **Template Embedding (Intent Sablon Vektorlugu)**
- Ne demek:
- Her intent tipi (`route`, `poi`, `multi`, `single`) icin ornek cumleler bir \"sablon seti\" olarak tutulur.
- Kullanici sorgusu da ayni vektor uzayina cevrilir ve bu sablonlara ne kadar benzedigi olculur.
- Kodda nerede:
- `QUERY_TEMPLATES`: intent sablon listeleri.
- `BertNLPEngine._get_template_embeddings(...)`: sablonlari encode edip cacheler.
- `BertNLPEngine.classify_query_type_with_scores(...)`: skorlamayi yapar.
- Nasil yapiliyor:
- `query_embedding = self.bert.encode(query)` ile kullanici sorgusunun vektoru alinir.
- Her intentin sablon embeddingleri ile `cosine_similarity(...)` hesaplanir.
- Intent bazli `avg_score` uretilir.
- Ayni anda intent centroid vektoru ile `centroid_score` hesaplanir.
- Final skor: `final_score = 0.65 * avg_score + 0.35 * centroid_score`.
- Kritik degiskenler:
- `query_embedding`, `template_embeddings`, `avg_score`, `centroid_score`, `final_score`, `score_map`, `best_type`, `best_score`.

2. **Hard-Negative Intent Koruma**
- Ne demek:
- Selamlasma/chitchat gibi sorgularin route/poi intentine yanlis dusmesini engelleyen negatif ornek seti.
- Kodda nerede:
- `HARD_NEGATIVE_TEMPLATES`
- `BertNLPEngine._get_hard_negative_embeddings(...)`
- `should_force_unknown_with_hard_negative(...)`
- Nasil yapiliyor:
- Query embedding ile hard-negative embeddingler arasi maksimum benzerlik `hard_negative_score` olarak olculur.
- Eger bu skor yuksekse ve intent skor marji dusukse sonuc `unknown`a zorlanir.
- Bazen direkt `unknown` yerine `best_score` uzerinde ceza uygulanir (`-0.05` gibi).
- Kritik degiskenler:
- `hard_negative_embs`, `hard_negative_score`, `second_best`, `best_score`, `best_type`.

3. **Span Tabanli Yer Cikarimi**
- Ne demek:
- Sadece tum cumleyi tek parca okumak yerine, token ve n-gram parcalari cikarilip her parcadan yer adayi bulunur.
- Kodda nerede:
- `normalize_token_with_role(...)`
- `extract_candidate_spans(...)`
- `extract_places(...)`
- Nasil yapiliyor:
- Tokenlar normalize edilir; eklerden rol ipucu cikarilir (`from`, `to`, `loc`).
- 1-gram, 2-gram, 3-gram adaylar uretilir.
- Her aday span icin embedding alinip place veritabaniyla eslestirilir.
- Sadece esik ustu ve \"lokasyon benzeri\" adaylar tutulur.
- Kritik degiskenler:
- `candidate_spans`, `span_embeddings`, `role_hint`, `token_count`, `threshold`, `match`, `best_matches`.

4. **Semantic Place Matching (Anlamsal Esleme)**
- Ne demek:
- \"Kadikoy\", \"Kadikoy'den\", \"kadikoyde\" gibi varyasyonlarin anlamsal benzerlikle ayni yere maplenmesi.
- Kodda nerede:
- `PlaceDatabase.find_best_match(...)`
- `build_place_lookup_keys(...)` / `normalize_place_key(...)`
- Nasil yapiliyor:
- Once lookup/alias ile kolay eslesme denenir.
- Sonra embedding benzerligi ile en iyi aday secilir.
- Kaynak bilgisi de tutulur (`lookup-exact`, semantic vb.).
- Kritik degiskenler:
- `normalized`, `lookup keys`, `similarity`, `source`, `place`, `index`.

5. **Intent Conflict Matrix (Son Karar Dengeleme)**
- Ne demek:
- Ilk intent sonucu her zaman final degildir; route/poi/multi sinyalleri celisirse ikinci bir karar matrisi uygulanir.
- Kodda nerede:
- `apply_intent_conflict_matrix(...)`
- `should_rescue_poi_intent(...)`
- Nasil yapiliyor:
- `has_poi_cue`, `has_multi_cue`, `direction_hints`, `route_intent_cue`, `score_margin` gibi sinyaller toplanir.
- Kurallara gore intent yeniden ayarlanir (ornegin route -> poi donusumu gibi).
- Final intent ve gerekce `intent_matrix_meta` icinde saklanir.
- Kritik degiskenler:
- `query_type`, `type_confidence`, `score_margin`, `has_poi_cue`, `direction_hints`, `intent_matrix_meta`.

6. **POI Intent Kurtarma ve Yorumlama**
- Ne demek:
- Sorguda POI niyeti varsa ama ilk siniflandirma zayifsa, POI niyetini geri kazanma adimi.
- Kodda nerede:
- `extract_poi_concept_with_meta(...)`
- `should_rescue_poi_intent(...)`
- Nasil yapiliyor:
- POI kavram tokenlari cikartilir (`eczane`, `kafe`, `muze` vb.).
- Lokasyon ve soru kalibi birlikte degerlendirilir.
- Uygunsa final intent `poi`ya cekilir.
- Kritik degiskenler:
- `poi_resolution`, `poi_concept`, `poi_question_cue`, `role_hints`, `unique_place_names`.

7. **Trace ve Gozlemlenebilirlik**
- Ne demek:
- Parse kararlarinin neden o sekilde ciktigini debug etmek icin ara metrikleri kaydetme.
- Kodda nerede:
- `parse(..., include_trace=True)` ve `trace_data` bloklari.
- Nasil yapiliyor:
- Aday spanlar, kabul/red nedenleri, skor dagilimlari, intent sinyal matrisi trace objesine yazilir.
- API katmaninda bu trace redaksiyon ve audit bilgisiyle loglanabilir.
- Kritik degiskenler:
- `trace_data`, `candidate_spans`, `accepted_span_count`, `type_scores`, `intent_signals`, `audit_id`.

5. **`app.py` + `rag_service` + Local LLM - Chat ve RAG Yonetim Modulu**
- Rol: Chat oturumu, model secimi, RAG kullanimi ve fallback kararlarini yonetir.
- Teknik akis:
- Adim 1: Session kontrolu (`session_id` gecerli mi, arsivli mi).
- Adim 2: Kullanici metni cikarma (`query` veya `messages` son user mesaji).
- Adim 3: RAG tetikleme karari (`_should_use_rag_for_query_with_reason`).
- Adim 4: RAG sonucu kalite kontrolu (`_should_fallback_from_rag`).
- Adim 5: RAG uygunsa extractive/structured cevap, degilse normal LLM chat.
- Adim 6: Cevap/session kaydi ve payload donusu.
- Kritik degiskenler:
- `use_rag_for_query`, `rag_reason`: RAG karar sebebi.
- `rag_min_similarity`, `top_similarity`: kalite ve esik kontrolu.
- `messages`, `use_session_context`: context bleed kontrolu.
- `assistant_text`, `tried_models`, `usage`: son cevap ve izleme verileri.

6. **`frontend/js/app.js` - UI Durum ve Etkilesim Modulu**
- Rol: Harita, rota, POI, NLP, chat, weather panellerinin tum state gecislerini yonetir.
- Teknik akis:
- Harita state: `selectedPoints` ile nokta secimi, rota cizimi, alternatif secimi.
- POI state: kategori + bolge secimiyle backend arama, marker/popup render.
- NLP state: parse sonucu kartta gosterim, haritaya uygulama/focus aksiyonlari.
- Chat state: `mainLlmMessages`, `mainLlmSessions`, `mainLlmActiveSessionId` ile session yonetimi.
- Kritik degiskenler:
- `currentRouteData`: aktif rota metrikleri ve geometri.
- `poiMarkers`: haritadaki POI katmanlari.
- `mainLlmStreaming`: chatte stream kilidi ve UI disable kontrolu.
- Neden kritik: Kullanici algiladigi "sistem calisiyor mu" hissi bu modulde olusur.

7. **Cache ve Performans Modulu (Dagitik Katman)**
- Rol: Tekrarlayan hesaplamalari tekrar calistirmadan cevaplayarak gecikmeyi dusurur.
- Nerede:
- `app.py`: rota response cache.
- `multimodal_engine.py`: lookup/segment/compare cache + OSRM sqlite cache.
- Kritik degiskenler:
- cache anahtarlari, TTL politikasi, inflight lock mekanizmasi.
- Neden kritik: Demo ve yuk altinda timeout yerine stabil cevap uretilmesini saglar.

8. **Weather Modulu**
- Rol: Rotanin sadece mesafe degil kosul uygunlugu tarafini da degerlendirir.
- Teknik akis:
- Anlik hava (`/api/weather`) ve saatlik tahmin (`/api/weather/forecast`) alinir.
- Rota noktalarina gore risk analizi (`/api/weather/check-route`) yapilir.
- UI tarafinda banner/simulator ile karar destek bilgisi sunulur.
- Kritik degiskenler:
- `route_weather`, `warnings`, `overall_conditions`.

### F) Modul Bazli Veri Kaynagi, Depolama ve Degisken Akisi (Tam Teknik)

Bu bolum "hangi modul ne yapar?" sorusunu bir adim ileri goturur:
- Veri nereden gelir?
- Nerede tutulur?
- Hangi degiskenlere atanir?
- Hangi endpointten hangi motora gider?

#### F.1 `backend/app.py` - Giris Katmani ve Yonlendirme
- Dosya rolu:
- Tum HTTP istekleri burada karsilanir, girdi dogrulama yapilir, ilgili motora aktarilir.
- Kritik import baglantilari:
- Rota: `route_engine` (`shortest_path`, `build_all_alternative_routes_batch`, `calculate_route_stats`)
- POI/OSM: `graph_manager` (`search_pois`)
- NLP: `bert_nlp_engine` (`get_bert_nlp_engine`)
- LLM/RAG: `local_llm_service`, `openrouter_service`, `gemini_service`, `rag_service`
- Transit: `ibb_transit`, `multimodal_engine`
- Storage: `route_storage`, `location_storage`, `chat_storage`, `storage_db`
- Input -> degisken atama ornekleri:
- `api_multimodal_compare` (`5362-5478`):
- `data = request.get_json(...)`
- `origin = data["origin"]`, `destination = data["destination"]`
- `allowed_modes = data.get("allowed_modes")`
- normalize edilen liste `allowed_modes = normalized_modes`
- motor cagrisi: `result = multimodal_compare(..., allowed_modes=allowed_modes)`
- `api_local_llm_chat_rag` (`4578-4848`):
- `query`, `messages`, `session_id`, `rag_top_k`, `rag_collection`, `rag_min_similarity`
- karar degiskenleri: `use_rag_for_query`, `rag_reason`, `rag_used`, `rag_skip_reason`
- RAG sonucu: `rag_result`, `rag_context`
- Donus payload'i: `payload["rag"]` icinde `used`, `top_similarity`, `sources`, `chunks`

#### F.2 `backend/storage_db.py` - Ana Uygulama Veritabani
- Fiziksel DB dosyasi:
- `DB_PATH = backend/data/app_data.db`
- Sema olusturma:
- `init_schema` (`187-299`) asagidaki tablolari olusturur:
- `routes`: kaydedilen rota meta + geometri JSON
- `locations`: kaydedilen kullanici konumlari
- `local_places`: geocoder/NLP fallback yer havuzu
- `chat_sessions`, `chat_messages`: LLM sohbet gecmisi
- Baglanti modeli:
- `get_connection` (`123-161`) thread-local pooled sqlite baglantisi dondurur.
- WAL + cache + mmap pragmalari performans icin aktif edilir.
- Uygulama akisi:
- Endpoint cagrilari `route_storage/location_storage/chat_storage` uzerinden bu DB'ye yazar/okur.

#### F.3 `backend/route_storage.py` - Rota CRUD Depolama
- Veri kaynagi:
- Frontendde kaydet tusu -> `/api/routes/save` -> `save_route(...)`.
- Nereye yazar:
- `routes` tablosu (`app_data.db`).
- Temel atamalar:
- `route_id = str(uuid.uuid4())[:8]`
- `compact_route_coords = simplify_coords(route_coords)` (RDP sadeleştirme)
- `points`, `route_coords`, `tags` alanlari JSON olarak yazilir.
- Akis:
- Save: `save_route` (`158+`)
- Liste: `get_all_routes` (`261+`)
- Tek rota + usage artisi: `get_route` (`234+`)
- Update/Delete/Favorite: `update_route`, `delete_route`, `toggle_favorite`

#### F.4 `backend/location_storage.py` - Lokasyon CRUD Depolama
- Veri kaynagi:
- Harita uzerinden kaydedilen "Ev/Is/Okul" vb. konumlar.
- Nereye yazar:
- `locations` tablosu (`app_data.db`).
- Temel atamalar:
- `location_id`, `name`, `lat`, `lon`, `icon_type`, `address`
- favori toggleda `favorite` 0/1 olarak guncellenir.
- Akis:
- Save: `save_location` (`85+`)
- Liste: `get_all_locations` (`161+`)
- Update/Delete/Favorite: `update_location`, `delete_location`, `toggle_location_favorite`

#### F.5 `backend/chat_storage.py` - Chat Session Kaliciligi
- Nereye yazar:
- `chat_sessions` + `chat_messages` tablolari (`app_data.db`).
- Ek mirror:
- `backend/data/chat_history.sync.json` (json mirror/sync icin).
- Temel atamalar:
- Session olusumu: `create_session` -> `session_id`, `title`, `created_at`
- Mesaj kaydi: `save_turn` -> user+assistant iki satir olarak eklenir.
- Akis:
- LLM endpointleri cevap urettikten sonra `save_chat_turn(...)` cagirir.
- UI session listesi `/api/llm/chat/sessions` ile bu tablodan gelir.

#### F.6 `backend/local_places.py` - Yerel Yer Havuzu (Geocoder/NLP Destek)
- Nereye yazar:
- `local_places` tablosu (`app_data.db`).
- Veri kaynagi:
- `SEED_PLACES`: static populer yer tohumlari.
- OSM dinamik cache: `save_dynamic_place(...)` ile `place_type='osm_dynamic'`.
- Akis:
- `lookup(place_name)` once lokal tabloyu dener.
- Bulunamazsa geocoder/OSM katmani devreye girer; uygun sonuc tekrar `local_places`e yazilabilir.
- NLP tarafinda `get_all_local_place_names` ve `get_dynamic_place_names` kullanilir.

#### F.7 `backend/graph_manager.py` - OSM Graph + POI Arama ve POI Cache
- Veri kaynagi:
- OSMnx/Overpass sorgulari (`features_from_place`, `features_from_point`).
- Nereye yazar:
- `POI_DB_PATH = backend/data/pois.db`
- tablolar: `pois`, `pois_archive`.
- POI akis:
- `/api/search-pois` endpointi `search_pois(...)` cagirir.
- kategori -> tag donusumu `osm_poi_dictionary.POI_MAPPING` ile yapilir.
- `search_mode`:
- `place_boundary_only`: idari sinirdan tek sorgu, gerekirse chunk fallback.
- `auto`: point yaricap fallback adimlari.
- Cache politikasi:
- soft TTL, hard TTL, empty TTL
- stale cache cevap verip arkaplanda refresh acabilir (`_start_background_poi_refresh`).

#### F.8 `backend/ibb_transit.py` - IBB Transit Veri Toplama ve Sorgu
- Veri kaynagi (dis API):
- IETT SOAP: `IBB_API_URL`
- Metro API: `METRO_API_BASE`
- GTFS CKAN: `GTFS_CKAN_URL`
- Nereye yazar:
- `TRANSIT_DB = backend/cache/transit.db`
- Tablolar (`_get_db_connection`, `185+`):
- `stops`, `routes`, `route_stops`, `meta`
- `metro_lines`, `metro_stations`, `metro_line_stations`
- Transit yukleme akis:
- `initialize_transit_data` (`1078+`) sirasiyla cagirir:
- `download_all_stops`
- `download_all_routes`
- `download_route_stops`
- `download_metro_data`
- `sync_marmaray_from_gtfs`
- Transit sorgu akis:
- yakin durak: `get_stops_in_area`
- durakta gecen hatlar: `get_routes_for_stop`
- iki durak arasi baglanti: `find_connecting_routes`
- metro istasyon/hat sorgulari: `get_metro_stations_in_area`, `get_metro_lines_for_station`, `get_metro_line_stations`

#### F.9 `backend/multimodal_engine.py` - Toplu Tasima Karsilastirma Motoru
- Cekilen veri:
- `ibb_transit` fonksiyonlari uzerinden `transit.db` okunur.
- `_build_metro_graph_data` (`2283+`) dogrudan `metro_lines/metro_stations/metro_line_stations` SQL okur.
- Ana endpoint:
- `/api/multimodal/compare` -> `compare_routes` (`4835+`) -> `find_transit_routes` (`4274+`)
- Mode secimi:
- `_normalize_allowed_modes` (`3420+`) kullanici secimini normalize eder.
- `option_user_modes` ile option icindeki gercek modlar hesaplanir.
- Degisken akis cekirdegi:
- giris: `origin_lat/lon`, `dest_lat/lon`, `allowed_modes`
- referans yuruyus: `direct_walk_m`, `direct_walk_min`, `direct_walk_coords`
- adaylar: `transit_options`
- filtrelenmis liste: `filtered`
- secilen sonuc: `recommended`, `recommendation_reason`
- Cache katmani:
- memory TTL cache + OSRM sqlite shard cache (`_osrm_sqlite_*` fonksiyonlari)

#### F.10 `frontend/js/transit.js` - Toplu Tasima UI ve Mode Secimi
- UI kaynaklari:
- checkboxlar: `input[data-transit-mode]`
- secim okuyucu: `getSelectedTransitModes()` (`215+`)
- varsayilan: `["bus","metro","metrobus","ferry"]`
- Backend cagrisi:
- `compareMultimodalRoutes()` (`664+`)
- payload: `{ origin, destination, allowed_modes: allowedModes }`
- endpoint: `POST /api/multimodal/compare`
- Sonuc cizimi:
- `displayMultimodalResults(...)` kartlari basar
- `showTransitRoute(...)` segmentleri haritada cizer
- `splitSegmentCoords(...)` ile "uzun teleport cizgi" artefaktlarini boler.

#### F.11 `backend/bert_nlp_engine.py` - NLP/BERT Parse Pipeline (Degisken Seviyesi)
- Giris:
- `parse(query, include_trace=False)` (`1887+`)
- Guard:
- `normalized_query_for_guard = normalize_query_text(query)`
- selam/chitchat regexi yakalanirsa erken `type=unknown` doner.
- Intent asamasi:
- `query_type, type_confidence, type_scores = classify_query_type_with_scores(query)`
- bu asamada:
- `query_embedding`
- `template_embeddings` (`QUERY_TEMPLATES`)
- `hard_negative_embs` (`HARD_NEGATIVE_TEMPLATES`)
- Yer cikarma:
- `detected_places = extract_places(query, trace=trace_data)`
- ara degiskenler:
- `candidate_spans`, `span_embeddings`, `threshold`, `match`
- Parse birlestirme:
- `ordered_places`, `place_names`, `unique_place_names`, `role_hints`, `direction_hints`
- `poi_resolution = extract_poi_concept_with_meta(...)`
- `query_type` conflict matrix ile revize edilir:
- `apply_intent_conflict_matrix(...)`
- `should_rescue_poi_intent(...)`
- Final cikti:
- `result["type"]`, `result["confidence"]`
- route ise `origin/destination`
- poi ise `location`, `poi_concept`, `poi_tags_hint`, `poi_osm_queries`
- `include_trace=True` ise `trace_data` tum ara kararlarla doner.

#### F.12 `backend/rag_service.py` + `app.py` - RAG Veri Akisi
- Fiziksel index:
- default `chroma_db` klasoru (`_db_path`).
- koleksiyon:
- env yoksa `istanbul_rag_core` (`_collection_name`).
- Embed model:
- env yoksa `BAAI/bge-m3` (`_embed_model_name`).
- Query akis:
- `rag_query(question, top_k, collection)`:
- embedding -> Chroma query -> `chunks`, `sources`, `top_similarity`
- API katmaninda (app.py):
- `_should_use_rag_for_query_with_reason` RAG tetikleme kararini verir.
- `_should_fallback_from_rag` similarity dusukse RAG'i pasiflestirir.
- RAG kullanilirsa:
- once `_try_direct_rag_structured_answer`, olmazsa `_build_extractive_rag_answer`.
- RAG kullanilmazsa:
- normal local LLM completion akisi calisir.

#### F.13 `backend/weather_service.py` - Hava Servisi ve Cache
- Veri kaynagi:
- Open-Meteo HTTP API (`_fetch_from_openmeteo`).
- Cache:
- servis icinde memory cache (`_get_from_cache`, `_save_to_cache`)
- Endpoint baglantisi (`app.py`):
- `/api/weather` -> `get_current_weather`
- `/api/weather/forecast` -> `get_hourly_forecast`
- `/api/weather/check-route` -> `check_route_weather`
- Degisken akis:
- giris lat/lon + route noktalarindan `route_weather`, `warnings`, `overall_conditions` uretilir.

#### F.14 `frontend/js/app.js` - Ana Ekran Is Akislari
- Ana state degiskenleri:
- `selectedPoints` (`18`)
- `poiMarkers` (`22`)
- `currentRouteData` (`24`)
- `mainLlmMessages`, `mainLlmSessions`, `mainLlmActiveSessionId` (`1411-1413`)
- Cekirdek akislar:
- Rota hesap: `calculateRoute` (`395+`)
- POI arama: `searchPois` (`583+`)
- NLP analiz: `analyzeNaturalLanguageQuery` (`1286+`)
- LLM chat: `mainLlmSendMessage` (`2017+`)
- Alternatif rota: `showAlternativeRoutes` (`2345+`)
- Save route/location, weather, timeline, route steps gibi tum panel yonetimi bu dosyadadir.

#### F.15 Sunumda Cok Sorulan "Veri Nerede?" Cevaplari (Kisa)
- Uygulama CRUD verisi: `backend/data/app_data.db`
- Transit hat/durak DB: `backend/cache/transit.db`
- POI cache DB: `backend/data/pois.db`
- Geocode cache: `backend/cache/geocodes.db`
- Chat JSON mirror: `backend/data/chat_history.sync.json`
- RAG vector DB: varsayilan `chroma_db/`


## 1) Dosya Boyutlari

- `backend/app.py`: 5608 satir
- `frontend/js/app.js`: 4265 satir
- `backend/bert_nlp_engine.py`: 2345 satir
- `backend/multimodal_engine.py`: 4969 satir
- `backend/route_engine_impl.py`: 1405 satir

## 2) backend/app.py - Tum Endpointler (Detayli)

### 2.1 `api_get_route` `1715-1832`
- Route/Method: `/api/get-route` [POST]
- Amac: Rota hesaplama endpointi veya rota kayit/okuma islemi.
- Ana akis cagrilari: `get_json`, `jsonify`, `get`, `_first_outside_point`, `_outside_istanbul_response`, `_route_response_cache_key`, `_route_response_cache_get`, `_build_primary_route_with_retries`, `_unreachable_waypoints_response`, `nodes_to_coords`, `calculate_route_stats`, `generate_google_maps_link`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500

### 2.2 `api_get_route_steps` `1836-2009`
- Route/Method: `/api/get-route-steps` [POST]
- Amac: Hesaplanan rota icin adim adim yon tarifi uretir.
- Ana akis cagrilari: `get_json`, `jsonify`, `get`, `_to_lat_lon_pair`, `_first_outside_point`, `_outside_istanbul_response`, `_route_response_cache_key`, `_route_response_cache_get`, `_build_primary_route_with_retries`, `_unreachable_waypoints_response`, `append`, `get_node_coords`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500

### 2.3 `api_get_alternative_routes` `2014-2165`
- Route/Method: `/api/get-alternative-routes` [POST]
- Amac: Ayni noktalar icin alternatif rota adaylari uretir.
- Ana akis cagrilari: `get_json`, `jsonify`, `get`, `_to_lat_lon_pair`, `_first_outside_point`, `_outside_istanbul_response`, `_route_response_cache_key`, `_route_response_cache_get`, `_build_alternative_batch_with_retries`, `_unreachable_waypoints_response`, `nodes_to_coords`, `append`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500

### 2.4 `api_search_pois` `2169-2310`
- Route/Method: `/api/search-pois` [POST]
- Amac: POI arama islemi yapar (kategori + bolge).
- Ana akis cagrilari: `get_json`, `jsonify`, `get`, `_is_place_text_in_istanbul`, `_outside_istanbul_response`, `lower`, `strip`, `split`, `_request_trace_prefix`, `resolve_poi_concept`, `_redact_pii_text`, `isascii`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500

### 2.5 `health_check` `2314-2316`
- Route/Method: `/api/health` [GET]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `jsonify`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: Endpoint icinde explicit kod yok veya ust katmanda yonetiliyor.

### 2.6 `api_cache_stats` `2320-2334`
- Route/Method: `/api/cache/stats` [GET]
- Amac: Cache istatistik veya yonetim islemi yapar.
- Ana akis cagrilari: `get_all_cache_stats`, `multimodal_compare_cache_stats`, `multimodal_transit_lookup_cache_stats`, `multimodal_segment_cache_stats`, `multimodal_osrm_cache_stats`, `_queue_stats_payload`, `evaluate_cache_policy`, `isoformat`, `now`, `jsonify`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 500

### 2.7 `api_geocode_suggest` `2338-2351`
- Route/Method: `/api/geocode/suggest` [GET]
- Amac: Adres ve koordinat donusum islemlerini yonetir.
- Ana akis cagrilari: `strip`, `get`, `geocode_suggest`, `jsonify`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: Endpoint icinde explicit kod yok veya ust katmanda yonetiliyor.

### 2.8 `api_geocode_forward_get` `2355-2367`
- Route/Method: `/api/geocode/forward` [GET]
- Amac: Adres ve koordinat donusum islemlerini yonetir.
- Ana akis cagrilari: `get`, `jsonify`, `geocode`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500

### 2.9 `api_geocode_reverse_get` `2371-2381`
- Route/Method: `/api/geocode/reverse` [GET]
- Amac: Adres ve koordinat donusum islemlerini yonetir.
- Ana akis cagrilari: `get`, `jsonify`, `reverse_geocode`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500

### 2.10 `api_geocode` `2385-2424`
- Route/Method: `/api/geocode` [POST]
- Amac: Adres ve koordinat donusum islemlerini yonetir.
- Ana akis cagrilari: `get_json`, `jsonify`, `geocode`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 404, 500

### 2.11 `api_reverse_geocode` `2428-2463`
- Route/Method: `/api/reverse-geocode` [POST]
- Amac: Adres ve koordinat donusum islemlerini yonetir.
- Ana akis cagrilari: `get_json`, `jsonify`, `reverse_geocode`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 404, 500

### 2.12 `api_geocode_batch` `2467-2504`
- Route/Method: `/api/geocode/batch` [POST]
- Amac: Adres ve koordinat donusum islemlerini yonetir.
- Ana akis cagrilari: `get_json`, `jsonify`, `geocode_batch`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500

### 2.13 `serve_frontend` `2508-2515`
- Route/Method: `/` [GET]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `send_from_directory`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: Endpoint icinde explicit kod yok veya ust katmanda yonetiliyor.

### 2.14 `serve_static_files` `2519-2539`
- Route/Method: `/<path:filepath>` [GET]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `send_from_directory`, `endswith`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: Endpoint icinde explicit kod yok veya ust katmanda yonetiliyor.

### 2.15 `api_save_route` `2547-2602`
- Route/Method: `/api/routes/save` [POST]
- Amac: Rotayi kalici depoya kaydeder.
- Ana akis cagrilari: `get_json`, `jsonify`, `save_route`, `get`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500

### 2.16 `api_get_routes` `2606-2659`
- Route/Method: `/api/routes` [GET]
- Amac: Rota hesaplama endpointi veya rota kayit/okuma islemi.
- Ana akis cagrilari: `get`, `get_routes_count`, `get_all_routes`, `jsonify`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 500

### 2.17 `api_get_route_by_id` `2663-2682`
- Route/Method: `/api/routes/<route_id>` [GET]
- Amac: Rota hesaplama endpointi veya rota kayit/okuma islemi.
- Ana akis cagrilari: `get_route`, `jsonify`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 404, 500

### 2.18 `api_update_route` `2686-2722`
- Route/Method: `/api/routes/<route_id>` [PUT]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `get_json`, `jsonify`, `update_route`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 404, 500

### 2.19 `api_delete_route` `2726-2749`
- Route/Method: `/api/routes/<route_id>` [DELETE]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `delete_route`, `jsonify`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 404, 500

### 2.20 `api_toggle_favorite` `2753-2778`
- Route/Method: `/api/routes/<route_id>/favorite` [POST]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `toggle_favorite`, `jsonify`, `get`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 404, 500

### 2.21 `api_search_routes` `2782-2810`
- Route/Method: `/api/routes/search` [GET]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `get`, `jsonify`, `search_routes`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500

### 2.22 `api_route_statistics` `2814-2833`
- Route/Method: `/api/routes/statistics` [GET]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `get_statistics`, `jsonify`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 500

### 2.23 `api_create_timeline` `2841-2905`
- Route/Method: `/api/timeline/create` [POST]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `get_json`, `jsonify`, `get`, `items`, `create_timeline`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500

### 2.24 `api_check_conflicts` `2909-2952`
- Route/Method: `/api/timeline/check-conflicts` [POST]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `get_json`, `jsonify`, `get`, `items`, `check_time_conflicts`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500

### 2.25 `api_optimize_timeline` `2956-2994`
- Route/Method: `/api/timeline/optimize` [POST]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `get_json`, `jsonify`, `get`, `optimize_schedule`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500

### 2.26 `api_get_locations` `3002-3034`
- Route/Method: `/api/locations` [GET]
- Amac: Kullanici konum kaydi/favori/guncelleme islemini yonetir.
- Ana akis cagrilari: `get`, `get_locations_count`, `get_all_locations`, `jsonify`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 500

### 2.27 `api_save_location` `3038-3067`
- Route/Method: `/api/locations` [POST]
- Amac: Kullanici konum kaydi/favori/guncelleme islemini yonetir.
- Ana akis cagrilari: `get_json`, `jsonify`, `save_location`, `get`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500

### 2.28 `api_delete_location` `3071-3086`
- Route/Method: `/api/locations/<location_id>` [DELETE]
- Amac: Kullanici konum kaydi/favori/guncelleme islemini yonetir.
- Ana akis cagrilari: `delete_location`, `jsonify`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 404, 500

### 2.29 `api_update_location` `3090-3111`
- Route/Method: `/api/locations/<location_id>` [PUT]
- Amac: Kullanici konum kaydi/favori/guncelleme islemini yonetir.
- Ana akis cagrilari: `get_json`, `jsonify`, `update_location`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 404, 500

### 2.30 `api_toggle_location_favorite` `3115-3132`
- Route/Method: `/api/locations/<location_id>/favorite` [POST]
- Amac: Kullanici konum kaydi/favori/guncelleme islemini yonetir.
- Ana akis cagrilari: `toggle_location_favorite`, `jsonify`, `get`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 404, 500

### 2.31 `api_nlp_parse` `3140-3305`
- Route/Method: `/api/nlp/parse` [POST]
- Amac: NLP/BERT analiz, durum veya yardimci operasyonu yonetir.
- Ana akis cagrilari: `_request_trace_prefix`, `get_json`, `jsonify`, `strip`, `get`, `_redact_pii_text`, `perf_counter`, `acquire`, `_increment_queue_timeout_counter`, `get_bert_nlp_engine`, `_log_bert_runtime_metrics`, `parse`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 429, 500, 503

### 2.32 `api_nlp_status` `3309-3356`
- Route/Method: `/api/nlp/status` [GET]
- Amac: NLP/BERT analiz, durum veya yardimci operasyonu yonetir.
- Ana akis cagrilari: `get_runtime_metrics`, `_queue_stats_payload`, `jsonify`, `get`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: Endpoint icinde explicit kod yok veya ust katmanda yonetiliyor.

### 2.33 `api_nlp_audit_recent` `3360-3371`
- Route/Method: `/api/nlp/audit/recent` [GET]
- Amac: NLP/BERT analiz, durum veya yardimci operasyonu yonetir.
- Ana akis cagrilari: `get`, `jsonify`, `list_recent_nlp_parse_audits`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500

### 2.34 `api_nlp_similarity` `3375-3437`
- Route/Method: `/api/nlp/similarity` [POST]
- Amac: NLP/BERT analiz, durum veya yardimci operasyonu yonetir.
- Ana akis cagrilari: `jsonify`, `get_json`, `strip`, `get_bert_engine`, `_log_bert_runtime_metrics`, `similarity`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500, 503

### 2.35 `api_nlp_best_match` `3441-3514`
- Route/Method: `/api/nlp/best-match` [POST]
- Amac: NLP/BERT analiz, durum veya yardimci operasyonu yonetir.
- Ana akis cagrilari: `jsonify`, `get_json`, `get`, `strip`, `get_bert_engine`, `_log_bert_runtime_metrics`, `find_best_match`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500, 503

### 2.36 `api_get_weather` `3522-3574`
- Route/Method: `/api/weather` [GET]
- Amac: Hava durumu verisi, durum veya cache islemlerini yonetir.
- Ana akis cagrilari: `jsonify`, `get`, `get_current_weather`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500, 503

### 2.37 `api_get_weather_forecast` `3578-3631`
- Route/Method: `/api/weather/forecast` [GET]
- Amac: Hava durumu verisi, durum veya cache islemlerini yonetir.
- Ana akis cagrilari: `jsonify`, `get`, `get_hourly_forecast`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500, 503

### 2.38 `api_check_route_weather` `3635-3694`
- Route/Method: `/api/weather/check-route` [POST]
- Amac: Hava durumu verisi, durum veya cache islemlerini yonetir.
- Ana akis cagrilari: `jsonify`, `get_json`, `get`, `check_route_weather`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500, 503

### 2.39 `api_weather_status` `3698-3725`
- Route/Method: `/api/weather/status` [GET]
- Amac: Hava durumu verisi, durum veya cache islemlerini yonetir.
- Ana akis cagrilari: `jsonify`, `get_service_status`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 500, 503

### 2.40 `api_weather_health` `3729-3743`
- Route/Method: `/api/weather/health` [GET]
- Amac: Hava durumu verisi, durum veya cache islemlerini yonetir.
- Ana akis cagrilari: `jsonify`, `weather_health_check`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 500, 503

### 2.41 `api_weather_clear_cache` `3747-3765`
- Route/Method: `/api/weather/clear-cache` [POST]
- Amac: Hava durumu verisi, durum veya cache islemlerini yonetir.
- Ana akis cagrilari: `jsonify`, `clear_weather_cache`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 500, 503

### 2.42 `api_llm_chat_sessions` `3769-3784`
- Route/Method: `/api/llm/chat/sessions` [GET]
- Amac: LLM provider/session/chat islemlerini yonetir.
- Ana akis cagrilari: `_as_bool`, `get`, `list_chat_sessions`, `jsonify`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: Endpoint icinde explicit kod yok veya ust katmanda yonetiliyor.

### 2.43 `api_create_llm_chat_session` `3788-3797`
- Route/Method: `/api/llm/chat/sessions` [POST]
- Amac: LLM provider/session/chat islemlerini yonetir.
- Ana akis cagrilari: `get_json`, `repair_text`, `get`, `create_chat_session`, `jsonify`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: Endpoint icinde explicit kod yok veya ust katmanda yonetiliyor.

### 2.44 `api_llm_chat_session_messages` `3801-3821`
- Route/Method: `/api/llm/chat/sessions/<session_id>/messages` [GET]
- Amac: LLM provider/session/chat islemlerini yonetir.
- Ana akis cagrilari: `get_chat_session`, `jsonify`, `get`, `strip`, `list_chat_messages`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 404

### 2.45 `api_archive_llm_chat_session` `3825-3832`
- Route/Method: `/api/llm/chat/sessions/<session_id>/archive` [POST]
- Amac: LLM provider/session/chat islemlerini yonetir.
- Ana akis cagrilari: `archive_chat_session`, `jsonify`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 404

### 2.46 `api_llm_model_health` `3836-3847`
- Route/Method: `/api/llm/model-health` [GET]
- Amac: LLM provider/session/chat islemlerini yonetir.
- Ana akis cagrilari: `lower`, `strip`, `get`, `jsonify`, `list_provider_health`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400

### 2.47 `api_openrouter_status` `3851-3874`
- Route/Method: `/api/llm/openrouter/status` [GET]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `jsonify`, `openrouter_status`, `list_provider_health`, `get`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 503

### 2.48 `api_openrouter_chat` `3878-3947`
- Route/Method: `/api/llm/openrouter/chat` [POST]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `jsonify`, `is_openrouter_configured`, `get_json`, `get`, `repair_text`, `_normalize_messages`, `_inject_system_message`, `_as_bool`, `openrouter_chat_completion_with_fallback`, `openrouter_chat_completion`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500, 502, 503

### 2.49 `api_openrouter_chat_stream` `3951-4168`
- Route/Method: `/api/llm/openrouter/chat/stream` [POST]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `jsonify`, `is_openrouter_configured`, `get_json`, `strip`, `get`, `get_chat_session`, `repair_text`, `_normalize_messages`, `_extract_latest_user_text`, `_inject_system_message`, `_chat_context_from_session`, `_as_bool`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 404, 503

### 2.50 `api_openrouter_models` `4172-4185`
- Route/Method: `/api/llm/openrouter/models` [GET]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `jsonify`, `openrouter_list_text_models`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 500, 502, 503

### 2.51 `api_gemini_status` `4189-4210`
- Route/Method: `/api/llm/gemini/status` [GET]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `jsonify`, `gemini_status`, `list_provider_health`, `get`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 503

### 2.52 `api_gemini_chat` `4214-4275`
- Route/Method: `/api/llm/gemini/chat` [POST]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `jsonify`, `is_gemini_configured`, `get_json`, `get`, `repair_text`, `_normalize_messages`, `_inject_system_message`, `_as_bool`, `gemini_chat_completion_with_fallback`, `gemini_chat_completion`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500, 502, 503

### 2.53 `api_gemini_chat_stream` `4279-4490`
- Route/Method: `/api/llm/gemini/chat/stream` [POST]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `jsonify`, `is_gemini_configured`, `get_json`, `strip`, `get`, `get_chat_session`, `repair_text`, `_normalize_messages`, `_extract_latest_user_text`, `_inject_system_message`, `_chat_context_from_session`, `_as_bool`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 404, 503

### 2.54 `api_gemini_models` `4494-4510`
- Route/Method: `/api/llm/gemini/models` [GET]
- Amac: Uygulama akisinin yardimci veya orchestration fonksiyonudur.
- Ana akis cagrilari: `jsonify`, `gemini_status`, `get`, `strip`, `add`, `append`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 500, 503

### 2.55 `api_local_llm_status` `4514-4535`
- Route/Method: `/api/llm/local/status` [GET]
- Amac: LLM provider/session/chat islemlerini yonetir.
- Ana akis cagrilari: `jsonify`, `local_llm_status`, `list_provider_health`, `get`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 503

### 2.56 `api_local_llm_models` `4539-4548`
- Route/Method: `/api/llm/local/models` [GET]
- Amac: LLM provider/session/chat islemlerini yonetir.
- Ana akis cagrilari: `jsonify`, `local_llm_list_models`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 500, 502, 503

### 2.57 `api_rag_status` `4552-4574`
- Route/Method: `/api/llm/rag/status` [GET]
- Amac: RAG baglam ve local LLM cevaplama akisini yonetir.
- Ana akis cagrilari: `jsonify`, `rag_status`, `get`, `rag_list_collections`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 500, 503

### 2.58 `api_local_llm_chat_rag` `4578-4848`
- Route/Method: `/api/llm/local/chat/rag` [POST]
- Amac: RAG baglam ve local LLM cevaplama akisini yonetir.
- Ana akis cagrilari: `jsonify`, `is_local_llm_configured`, `get_json`, `strip`, `get`, `get_chat_session`, `repair_text`, `_normalize_messages`, `_extract_latest_user_text`, `_resolve_rag_min_similarity`, `_as_bool`, `_should_use_rag_for_query_with_reason`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 404, 500, 502, 503

### 2.59 `api_local_llm_chat` `4852-4931`
- Route/Method: `/api/llm/local/chat` [POST]
- Amac: LLM provider/session/chat islemlerini yonetir.
- Ana akis cagrilari: `jsonify`, `is_local_llm_configured`, `get_json`, `strip`, `get`, `get_chat_session`, `repair_text`, `_normalize_messages`, `_extract_latest_user_text`, `_chat_context_from_session`, `_inject_local_system_message`, `_local_llm_generation_options`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 404, 500, 502, 503

### 2.60 `api_local_llm_chat_stream` `4935-5152`
- Route/Method: `/api/llm/local/chat/stream` [POST]
- Amac: LLM provider/session/chat islemlerini yonetir.
- Ana akis cagrilari: `jsonify`, `is_local_llm_configured`, `get_json`, `strip`, `get`, `get_chat_session`, `repair_text`, `_normalize_messages`, `_extract_latest_user_text`, `_inject_local_system_message`, `_chat_context_from_session`, `_local_llm_generation_options`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 404, 503

### 2.61 `api_transit_stops` `5175-5206`
- Route/Method: `/api/transit/stops` [GET]
- Amac: Transit durak/hat verisi endpointidir.
- Ana akis cagrilari: `jsonify`, `get`, `get_stops_in_area`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500, 503

### 2.62 `api_transit_search` `5210-5238`
- Route/Method: `/api/transit/search` [GET]
- Amac: Transit durak/hat verisi endpointidir.
- Ana akis cagrilari: `jsonify`, `get`, `search_transit_stops`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500, 503

### 2.63 `api_transit_route` `5242-5267`
- Route/Method: `/api/transit/route` [GET]
- Amac: Transit durak/hat verisi endpointidir.
- Ana akis cagrilari: `jsonify`, `get`, `get_transit_route_info`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 404, 500, 503

### 2.64 `api_transit_stop_routes` `5271-5297`
- Route/Method: `/api/transit/stop-routes` [GET]
- Amac: Transit durak/hat verisi endpointidir.
- Ana akis cagrilari: `jsonify`, `get`, `get_routes_for_stop`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 500, 503

### 2.65 `api_transit_stats` `5301-5312`
- Route/Method: `/api/transit/stats` [GET]
- Amac: Transit durak/hat verisi endpointidir.
- Ana akis cagrilari: `jsonify`, `get_transit_statistics`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 500, 503

### 2.66 `api_transit_init` `5316-5336`
- Route/Method: `/api/transit/init` [POST]
- Amac: Transit durak/hat verisi endpointidir.
- Ana akis cagrilari: `jsonify`, `lower`, `get`, `initialize_transit_data`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 500, 503

### 2.67 `api_multimodal_compare` `5362-5478`
- Route/Method: `/api/multimodal/compare` [POST]
- Amac: Toplu tasima modlarina gore karsilastirma/oneri uretir.
- Ana akis cagrilari: `jsonify`, `perf_counter`, `get_json`, `get`, `lower`, `strip`, `add`, `append`, `_to_lat_lon_pair`, `_is_in_istanbul_bbox`, `_outside_istanbul_response`, `acquire`
- Kod icinde acik gorulen HTTP hata kodlari: 400, 429, 500, 503

### 2.68 `api_nlp_warmup` `5514-5528`
- Route/Method: `/api/nlp/warmup` [GET, POST]
- Amac: NLP/BERT analiz, durum veya yardimci operasyonu yonetir.
- Ana akis cagrilari: `get_json`, `get`, `lower`, `_preload_bert_async`, `jsonify`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 500

### 2.69 `api_nlp_seed_places` `5532-5576`
- Route/Method: `/api/nlp/seed-places` [POST]
- Amac: NLP/BERT analiz, durum veya yardimci operasyonu yonetir.
- Ana akis cagrilari: `get_json`, `get`, `join`, `getcwd`, `append`, `run`, `Thread`, `start`, `jsonify`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 500

### 2.70 `api_nlp_optimize_model` `5580-5608`
- Route/Method: `/api/nlp/optimize-model` [POST]
- Amac: NLP/BERT analiz, durum veya yardimci operasyonu yonetir.
- Ana akis cagrilari: `get_json`, `get`, `join`, `getcwd`, `run`, `Thread`, `start`, `jsonify`, `route`
- Kod icinde acik gorulen HTTP hata kodlari: 500

## 3) app.py - Yardimci Fonksiyonlar (Tam Liste)

| Fonksiyon | Satir | Ne Yapar |
|---|---:|---|
| `_env_flag` | `41-46` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_env_float` | `49-57` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_env_int` | `60-67` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_to_lat_lon_pair` | `78-91` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_is_in_istanbul_bbox` | `94-98` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_outside_istanbul_response` | `101-111` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_first_outside_point` | `114-122` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_route_radius_multipliers` | `125-155` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_get_graph_for_points_with_multiplier` | `158-163` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_collect_snap_metrics` | `166-182` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_route_index_from_type` | `185-186` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_round_point_pairs` | `189-196` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_route_response_cache_key` | `199-213` | Cache istatistik veya yonetim islemi yapar. |
| `_route_response_cache_get` | `216-220` | Cache istatistik veya yonetim islemi yapar. |
| `_route_response_cache_put` | `223-226` | Cache istatistik veya yonetim islemi yapar. |
| `_unreachable_waypoints_response` | `229-238` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_build_primary_route_with_retries` | `241-302` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_build_alternative_batch_with_retries` | `305-365` | Ayni noktalar icin alternatif rota adaylari uretir. |
| `_is_place_text_in_istanbul` | `368-398` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_extract_nlp_places_for_scope_check` | `401-436` | NLP/BERT analiz, durum veya yardimci operasyonu yonetir. |
| `_is_route_intent_query_text` | `439-452` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_has_poi_concept_cue` | `455-463` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_has_single_location_style_cue` | `466-471` | Kullanici konum kaydi/favori/guncelleme islemini yonetir. |
| `_postprocess_nlp_result_for_poi` | `474-505` | NLP/BERT analiz, durum veya yardimci operasyonu yonetir. |
| `_openrouter_system_prompt` | `508-524` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_inject_system_message` | `527-536` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_local_llm_system_prompt` | `539-551` | LLM provider/session/chat islemlerini yonetir. |
| `_inject_local_system_message` | `554-563` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_as_bool` | `566-573` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_normalize_messages` | `576-588` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_extract_latest_user_text` | `591-600` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_classify_llm_error` | `603-613` | LLM provider/session/chat islemlerini yonetir. |
| `_local_llm_max_tokens` | `616-635` | LLM provider/session/chat islemlerini yonetir. |
| `_local_llm_float_param` | `638-645` | LLM provider/session/chat islemlerini yonetir. |
| `_local_llm_int_param` | `648-655` | LLM provider/session/chat islemlerini yonetir. |
| `_normalize_common_turkish_glitches` | `661-683` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_normalize_for_match` | `686-703` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_contains_route_relation` | `706-711` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_is_dynamic_route_request` | `714-722` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_is_poi_request` | `725-731` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_should_use_rag_for_query_with_reason` | `734-773` | RAG baglam ve local LLM cevaplama akisini yonetir. |
| `_should_use_rag_for_query` | `776-777` | RAG baglam ve local LLM cevaplama akisini yonetir. |
| `_resolve_rag_min_similarity` | `780-790` | RAG baglam ve local LLM cevaplama akisini yonetir. |
| `_should_fallback_from_rag` | `793-803` | RAG baglam ve local LLM cevaplama akisini yonetir. |
| `_extract_stop_names_from_text` | `806-839` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_extract_query_line_code` | `842-845` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_extract_station_candidate_for_line_query` | `848-860` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_try_direct_rag_structured_answer` | `863-946` | RAG baglam ve local LLM cevaplama akisini yonetir. |
| `_split_text_sentences` | `957-969` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_query_tokens_for_extractive` | `972-984` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_build_extractive_rag_answer` | `987-1046` | RAG baglam ve local LLM cevaplama akisini yonetir. |
| `_is_rag_context_relevant` | `1049-1067` | RAG baglam ve local LLM cevaplama akisini yonetir. |
| `_local_llm_generation_options` | `1070-1083` | LLM provider/session/chat islemlerini yonetir. |
| `_is_repetition_loop` | `1086-1109` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_unique_models` | `1112-1121` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_llm_candidate_models` | `1124-1135` | LLM provider/session/chat islemlerini yonetir. |
| `_chat_context_from_session` | `1138-1149` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_configure_live_console_output` | `1152-1168` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_preload_bert_async` | `1358-1378` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_poi_version_token` | `1444-1445` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_increment_queue_timeout_counter` | `1448-1454` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_semaphore_snapshot` | `1457-1462` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_queue_stats_payload` | `1465-1481` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_should_log_bert_metrics` | `1484-1493` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_log_bert_runtime_metrics` | `1496-1516` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_log_bert_parse_trace` | `1519-1584` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `initialize_runtime` | `1587-1603` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `initialize_graph_preload` | `1606-1615` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_get_cached_graph` | `1619-1632` | Cache istatistik veya yonetim islemi yapar. |
| `_redact_pii_text` | `1635-1641` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_request_trace_prefix` | `1644-1647` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_ensure_runtime_initialized` | `1651-1667` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_attach_trace_headers` | `1671-1693` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_disable_bert_runtime` | `1696-1701` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_build_regex_fallback_result` | `1704-1710` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |

## 4) frontend/js/app.js - UI Katalogu

### 4.1 Bolum Basliklari

- `7`: ========== CONFIG ==========
- `17`: ========== STATE ==========
- `29`: ========== MAP INIT ==========
- `72`: ========== DOM ELEMENTS ==========
- `153`: ========== CUSTOM MARKER ICON ==========
- `178`: ========== MAP CLICK HANDLER ==========
- `278`: ========== UI UPDATES ==========
- `279`: ========== DRAG & DROP VARIABLES ==========
- `282`: ========== DRAG & DROP HANDLERS ==========
- `394`: ========== ROUTE CALCULATION ==========
- `505`: ========== POI SEARCH ==========
- `742`: ========== LOADING ==========
- `752`: ========== TOAST NOTIFICATIONS ==========
- `768`: ========== LAYOUT CONTROLS ==========
- `906`: ========== EVENT LISTENERS ==========
- `991`: ========== PLACE SEARCH (GEOCODING) ==========
- `1198`: ========== AI ASSISTANT (NLP) ==========
- `1409`: ========== MAIN LLM CHAT (OPENROUTER/GEMINI) ==========
- `2340`: ========== ALTERNATIVE ROUTES ==========
- `2534`: ========== SAVE ROUTE ==========
- `2797`: ========== TIME PLANNING ==========
- `2964`: ========== SAVED LOCATIONS (KAYITLI YERLER) ==========
- `3239`: ========== EVENT DELEGATION - XSS Güvenlik Düzeltmeleri ==========
- `3331`: ========== WEATHER WIDGET ==========
- `3370`: ========== WEATHER BANNER ==========
- `3615`: ========== WEATHER & TIMELINE SIMULATOR ==========
- `3807`: ========== TÜRKğYE VERğSğ YÖNETğMğ ==========
- `3909`: ========== TURN-BY-TURN & TTS ==========
- `3997`: ========== UX ENHANCEMENTS (2026-03-18) ==========

### 4.2 Tum Fonksiyonlar

| Fonksiyon | Satir | Ne Yapar |
|---|---:|---|
| `isInIstanbulBounds` | `46-54` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `focusMapInIstanbul` | `55-153` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `createNumberedIcon` | `154-163` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `createPoiIcon` | `164-173` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `isValidField` | `174-183` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `addPoint` | `184-235` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `removePoint` | `236-263` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `clearAllPoints` | `264-282` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `handleDragStart` | `283-289` | RAG baglam ve local LLM cevaplama akisini yonetir. |
| `handleDragEnd` | `290-298` | RAG baglam ve local LLM cevaplama akisini yonetir. |
| `handleDragOver` | `299-307` | RAG baglam ve local LLM cevaplama akisini yonetir. |
| `handleDragLeave` | `308-314` | RAG baglam ve local LLM cevaplama akisini yonetir. |
| `handleDrop` | `315-343` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `updatePointsList` | `344-383` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `updateButtons` | `384-394` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `calculateRoute` | `395-445` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `drawRoute` | `446-472` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `clearRoute` | `473-492` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `showRouteInfo` | `493-509` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `parsePoiButtonLabel` | `510-520` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `getPoiVisualFromCategory` | `521-541` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `formatPoiAge` | `542-552` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `renderPoiMeta` | `553-582` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `searchPois` | `583-659` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `displayPois` | `660-683` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `buildPoiPopup` | `684-732` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `clearPois` | `733-742` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `showLoading` | `743-747` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `hideLoading` | `748-752` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `showToast` | `753-782` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `isMobileViewport` | `783-786` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `loadLayoutPrefs` | `787-805` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `saveLayoutPrefs` | `806-813` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `updateLayoutButtonLabels` | `814-819` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `applyLayoutPrefs` | `820-841` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `initLayoutResizers` | `842-842` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `bindHorizontalResizer` | `843-1055` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `fetchSuggestions` | `1056-1098` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `searchPlace` | `1099-1141` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `displaySearchResult` | `1142-1176` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `selectSearchResult` | `1177-1190` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `escapeHtml` | `1191-1199` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `geocodePlaceName` | `1200-1214` | Adres ve koordinat donusum islemlerini yonetir. |
| `setNlpLoading` | `1215-1219` | NLP/BERT analiz, durum veya yardimci operasyonu yonetir. |
| `buildNlpSummary` | `1220-1237` | NLP/BERT analiz, durum veya yardimci operasyonu yonetir. |
| `renderNlpResults` | `1238-1285` | NLP/BERT analiz, durum veya yardimci operasyonu yonetir. |
| `analyzeNaturalLanguageQuery` | `1286-1321` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `applyNlpResult` | `1322-1358` | NLP/BERT analiz, durum veya yardimci operasyonu yonetir. |
| `focusNlpLocation` | `1359-1528` | NLP/BERT analiz, durum veya yardimci operasyonu yonetir. |
| `mainLlmRepairText` | `1529-1550` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmRepairTokenText` | `1551-1573` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmGetProvider` | `1574-1578` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmGetMode` | `1579-1582` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmLocalCacheKey` | `1583-1586` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmSaveLocalCache` | `1587-1596` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmLoadLocalCache` | `1597-1617` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmSetStatus` | `1618-1625` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmSetActiveModel` | `1626-1631` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmClassifyModel` | `1632-1643` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmSelectedManualModel` | `1644-1647` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmLoadModelHealth` | `1648-1670` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmFetchProviderModels` | `1671-1697` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmClassifyError` | `1698-1706` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmAppendMeta` | `1707-1714` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmAddMessage` | `1715-1724` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmRenderMessages` | `1725-1737` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmUpdateModeUi` | `1738-1756` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmRefreshModelOptions` | `1757-1816` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmSortSessions` | `1817-1824` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmPopulateSessionSelect` | `1825-1840` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmLoadSessions` | `1841-1851` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmCreateSession` | `1852-1865` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmLoadSessionMessages` | `1866-1884` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmSetActiveSession` | `1885-1901` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmEnsureActiveSession` | `1902-1916` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmCreateAndSwitchSession` | `1917-1922` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmArchiveCurrentSession` | `1923-1942` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmToggleBusy` | `1943-1950` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmPanelSetOpen` | `1951-1963` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmCheckStatus` | `1964-2016` | LLM provider/session/chat islemlerini yonetir. |
| `mainLlmSendMessage` | `2017-2251` | LLM provider/session/chat islemlerini yonetir. |
| `initMainLlmChat` | `2252-2344` | LLM provider/session/chat islemlerini yonetir. |
| `showAlternativeRoutes` | `2345-2385` | Ayni noktalar icin alternatif rota adaylari uretir. |
| `displayAlternativeRoutes` | `2386-2444` | Ayni noktalar icin alternatif rota adaylari uretir. |
| `selectAlternativeRoute` | `2445-2538` | Ayni noktalar icin alternatif rota adaylari uretir. |
| `openSaveRouteModal` | `2539-2551` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `closeSaveRouteModal` | `2552-2562` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `confirmSaveRoute` | `2563-2619` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `loadSavedRoutes` | `2620-2641` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `displaySavedRoutes` | `2642-2694` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `loadRoute` | `2695-2744` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `toggleRouteFavorite` | `2745-2770` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `deleteRoute` | `2771-2801` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `showTimelinePlanner` | `2802-2814` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `generateTimeline` | `2815-2874` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `calculateSegmentDistances` | `2875-2889` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `displayTimeline` | `2890-3008` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `closeSaveLocationModal` | `3009-3016` | Kullanici konum kaydi/favori/guncelleme islemini yonetir. |
| `confirmSaveLocation` | `3017-3071` | Kullanici konum kaydi/favori/guncelleme islemini yonetir. |
| `loadSavedLocations` | `3072-3093` | Kullanici konum kaydi/favori/guncelleme islemini yonetir. |
| `displaySavedLocationsSidebar` | `3094-3140` | Kullanici konum kaydi/favori/guncelleme islemini yonetir. |
| `toggleLocationFavorite` | `3141-3161` | Kullanici konum kaydi/favori/guncelleme islemini yonetir. |
| `deleteSavedLocation` | `3162-3189` | Kullanici konum kaydi/favori/guncelleme islemini yonetir. |
| `drawSavedLocationsOnMap` | `3190-3211` | Kullanici konum kaydi/favori/guncelleme islemini yonetir. |
| `clearSavedLocationMarkers` | `3212-3216` | Kullanici konum kaydi/favori/guncelleme islemini yonetir. |
| `toggleSavedLocationsVisibility` | `3217-3335` | Kullanici konum kaydi/favori/guncelleme islemini yonetir. |
| `fetchWeatherWidget` | `3336-3362` | Hava durumu verisi, durum veya cache islemlerini yonetir. |
| `initWeatherWidget` | `3363-3374` | Hava durumu verisi, durum veya cache islemlerini yonetir. |
| `formatLocalDateISO` | `3375-3398` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `checkRouteWeatherAndShowBanner` | `3399-3449` | Hava durumu verisi, durum veya cache islemlerini yonetir. |
| `showWeatherBanner` | `3450-3520` | Hava durumu verisi, durum veya cache islemlerini yonetir. |
| `showWeatherWarningModal` | `3521-3609` | Hava durumu verisi, durum veya cache islemlerini yonetir. |
| `hideWeatherBanner` | `3610-3622` | Hava durumu verisi, durum veya cache islemlerini yonetir. |
| `initWeatherSimulator` | `3623-3695` | Hava durumu verisi, durum veya cache islemlerini yonetir. |
| `loadForecastStrip` | `3696-3755` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `getWeatherEmoji` | `3756-3789` | Hava durumu verisi, durum veya cache islemlerini yonetir. |
| `getWeatherDescTr` | `3790-3810` | Hava durumu verisi, durum veya cache islemlerini yonetir. |
| `loadTurkiyeData` | `3811-3822` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `initializeRegionDropdown` | `3823-3918` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `clearRouteSteps` | `3919-3928` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `fetchRouteSteps` | `3929-3954` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `displayRouteSteps` | `3955-3960` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `startVoicePlayback` | `3961-3971` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `playNextTTS` | `3972-3981` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `stopVoicePlayback` | `3982-4004` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `normalizePoiConfidenceScore` | `4005-4013` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `ensureRouteDecisionPanel` | `4014-4030` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `renderRouteDecisionPanel` | `4031-4067` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `summarizeWeatherForDecision` | `4068-4105` | Hava durumu verisi, durum veya cache islemlerini yonetir. |
| `buildShortDistanceOverlapWarning` | `4106-4150` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `ensurePoiFilterPanel` | `4151-4186` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `applyPoiFilters` | `4187-4265` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |

## 5) backend/bert_nlp_engine.py - Tam Fonksiyon Katalogu

| Fonksiyon | Satir | Ne Yapar |
|---|---:|---|
| `_osm_retry_request` | `32-57` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `get_all_locations` | `83-83` | Kullanici konum kaydi/favori/guncelleme islemini yonetir. |
| `save_dynamic_place` | `94-94` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `get_dynamic_place_names` | `95-95` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `get_all_local_place_names` | `96-96` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `tr_lower` | `142-144` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `load_intent_template_bundle` | `199-234` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `cosine_similarity` | `246-251` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `should_force_unknown_with_hard_negative` | `254-267` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `apply_intent_conflict_matrix` | `270-322` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_env_flag` | `354-359` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_env_float` | `362-370` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_env_int` | `373-381` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `normalize_place_key` | `396-402` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `is_likely_action_token` | `405-415` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_singularize_tr_token` | `418-424` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_normalize_poi_mapping` | `427-435` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `is_poi_concept_term` | `448-462` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_collect_poi_tokens` | `465-515` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `in_occupied_range` | `481-485` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `extract_poi_concept_with_meta` | `518-591` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `extract_poi_concept` | `594-596` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_extract_explicit_multi_places` | `599-631` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_extract_plain_multi_places` | `634-654` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `build_place_lookup_keys` | `657-682` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `normalize_query_text` | `685-687` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `normalize_token_with_role` | `690-738` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `extract_candidate_spans` | `741-810` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `add_span` | `770-782` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `__init__` | `831-876` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_seed_dynamic_cache` | `878-887` | Cache istatistik veya yonetim islemi yapar. |
| `_seed_user_locations` | `889-902` | Kullanici konum kaydi/favori/guncelleme islemini yonetir. |
| `_seed_local_places` | `904-916` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_seed_turkish_places` | `918-929` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_seed_fallback_places` | `931-955` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `add_place` | `957-1003` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `get_embedding_matrix` | `1005-1028` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `resolve_lookup` | `1030-1038` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `find_best_match` | `1040-1126` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `score_embeddings` | `1076-1096` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `search_osm_api` | `1128-1176` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `add_places_from_osm` | `1178-1188` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `cache_osm_results` | `1190-1297` | Cache istatistik veya yonetim islemi yapar. |
| `_build_osm_prefetch_queries` | `1299-1312` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `prefetch_osm_candidates` | `1314-1341` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `find_all_matches` | `1343-1377` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `should_rescue_poi_intent` | `1384-1410` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `should_prefetch_osm_for_query` | `1413-1430` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `__init__` | `1444-1498` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_get_template_embeddings` | `1500-1519` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_get_hard_negative_embeddings` | `1521-1526` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `classify_query_type_with_scores` | `1528-1586` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `classify_query_type` | `1588-1593` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_is_location_like_match` | `1595-1642` | Kullanici konum kaydi/favori/guncelleme islemini yonetir. |
| `extract_places` | `1644-1782` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `detect_route_direction` | `1784-1854` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `select_best` | `1803-1813` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_choose_best_poi_location` | `1856-1885` | Kullanici konum kaydi/favori/guncelleme islemini yonetir. |
| `parse` | `1887-2267` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `get_bert_nlp_engine` | `2277-2288` | NLP/BERT analiz, durum veya yardimci operasyonu yonetir. |
| `test_bert_nlp` | `2295-2341` | NLP/BERT analiz, durum veya yardimci operasyonu yonetir. |

### 5.1 BERT Parse Cekirdegi
- `parse` `1887-2276`: query guard -> intent score -> place extraction -> conflict matrix -> final JSON.
- `extract_places` `1644-1783`: span uretimi, semantic match, threshold, false-positive filtreleme.
- `classify_query_type_with_scores` `1528-1587`: template + centroid + hard-negative score birlesimi.

## 6) backend/multimodal_engine.py - Tam Fonksiyon Katalogu

| Fonksiyon | Satir | Ne Yapar |
|---|---:|---|
| `_resolve_cache_path` | `98-106` | Cache istatistik veya yonetim islemi yapar. |
| `_current_telemetry` | `147-151` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_telemetry_count` | `154-162` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_telemetry_set_count` | `165-173` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_telemetry_add_ms` | `176-185` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_osrm_cache_key_hash` | `188-190` | Cache istatistik veya yonetim islemi yapar. |
| `_osrm_sqlite_shard_width` | `193-194` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_osrm_sqlite_shard_db_path` | `197-199` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_osrm_sqlite_db_paths` | `202-205` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_osrm_sqlite_target_db_path` | `208-212` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_osrm_sqlite_legacy_fallback_db_path` | `215-221` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_osrm_sqlite_candidate_db_paths` | `224-230` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_osrm_sqlite_connect` | `233-240` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_ensure_osrm_sqlite_schema` | `243-264` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_ensure_osrm_sqlite_cache` | `267-289` | Cache istatistik veya yonetim islemi yapar. |
| `_osrm_sqlite_max_rows_per_db` | `292-298` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_prune_osrm_sqlite_cache` | `301-321` | Cache istatistik veya yonetim islemi yapar. |
| `_osrm_sqlite_cache_get` | `324-381` | Cache istatistik veya yonetim islemi yapar. |
| `_osrm_sqlite_cache_put` | `384-424` | Cache istatistik veya yonetim islemi yapar. |
| `_osrm_sqlite_cache_size` | `427-445` | Cache istatistik veya yonetim islemi yapar. |
| `_begin_osrm_inflight` | `448-460` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_wait_osrm_inflight` | `463-479` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_finish_osrm_inflight` | `482-494` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_effective_walk_to_stop_limit_m` | `497-518` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_cache_get` | `521-525` | Cache istatistik veya yonetim islemi yapar. |
| `_cache_put` | `528-538` | Cache istatistik veya yonetim islemi yapar. |
| `_ttl_cache_get` | `541-551` | Cache istatistik veya yonetim islemi yapar. |
| `_ttl_cache_put` | `554-563` | Cache istatistik veya yonetim islemi yapar. |
| `_compare_cache_get` | `566-575` | Cache istatistik veya yonetim islemi yapar. |
| `_compare_cache_put` | `578-581` | Cache istatistik veya yonetim islemi yapar. |
| `_lookup_cache_get` | `584-593` | Cache istatistik veya yonetim islemi yapar. |
| `_lookup_cache_put` | `596-597` | Cache istatistik veya yonetim islemi yapar. |
| `_segment_cache_get` | `600-611` | Cache istatistik veya yonetim islemi yapar. |
| `_segment_cache_put` | `614-617` | Cache istatistik veya yonetim islemi yapar. |
| `get_compare_cache_stats` | `620-631` | Cache istatistik veya yonetim islemi yapar. |
| `get_transit_lookup_cache_stats` | `634-645` | Transit durak/hat verisi endpointidir. |
| `get_segment_cache_stats` | `648-659` | Cache istatistik veya yonetim islemi yapar. |
| `get_osrm_cache_stats` | `662-714` | Cache istatistik veya yonetim islemi yapar. |
| `_cached_get_stops_in_area` | `717-724` | Cache istatistik veya yonetim islemi yapar. |
| `_cached_find_connecting_routes` | `727-734` | Cache istatistik veya yonetim islemi yapar. |
| `_cached_get_route_info` | `737-745` | Rota hesaplama endpointi veya rota kayit/okuma islemi. |
| `_cached_get_metro_stations_in_area` | `748-755` | Cache istatistik veya yonetim islemi yapar. |
| `_cached_get_metro_lines_for_station` | `758-765` | Cache istatistik veya yonetim islemi yapar. |
| `_cached_get_metro_line_stations` | `768-775` | Cache istatistik veya yonetim islemi yapar. |
| `_osrm_route_coords` | `782-867` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_get_bus_road_coords` | `870-937` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_sample_waypoints` | `894-906` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_osrm_multi_waypoint` | `940-1015` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_get_walk_road_coords` | `1018-1021` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_walking_time_minutes` | `1028-1030` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_bus_travel_time_minutes` | `1033-1037` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_metro_travel_time_minutes` | `1040-1044` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_ferry_travel_time_minutes` | `1047-1052` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_ferry_display_name` | `1097-1103` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_resolve_ferry_terminal_key` | `1106-1108` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_transfer_max_distance_for_name` | `1137-1142` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_bosphorus_side` | `1145-1154` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_is_forbidden_bosphorus_walk` | `1157-1180` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_is_likely_halic_straight_cross` | `1183-1198` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_is_major_water_crossing_straight` | `1201-1213` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_is_likely_halic_crossing` | `1216-1239` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_is_likely_alibey_crossing` | `1242-1289` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_alibey_side` | `1262-1267` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_coords_pass_near_checkpoints` | `1292-1307` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_is_allowed_water_crossing_walk` | `1310-1331` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_path_distance_m` | `1334-1344` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_max_jump_in_coords_m` | `1347-1359` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_has_implausible_segment_jump` | `1362-1386` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_sum_walk_distance_m` | `1389-1395` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_sum_walk_duration_min` | `1398-1404` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_looks_like_straight_fallback` | `1407-1420` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_direct_walk_metrics` | `1423-1459` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_is_feasible_transfer_walk` | `1462-1500` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_build_walk_leg` | `1503-1598` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_get_routes_at_stop` | `1601-1616` | Rota hesaplama endpointi veya rota kayit/okuma islemi. |
| `_normalize_transit_stop_name` | `1619-1633` | Transit durak/hat verisi endpointidir. |
| `_expand_route_stop_code_aliases` | `1636-1696` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_get_route_stop_coords` | `1699-1801` | Rota hesaplama endpointi veya rota kayit/okuma islemi. |
| `_get_nearby_routes` | `1804-1818` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_normalize_station_name` | `1821-1835` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_get_line_path_between_stations` | `1838-1871` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_find_metro_transfer_pairs` | `1874-1925` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_build_metro_options` | `1928-2230` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_normalized_station_name` | `2233-2247` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_normalized_station_name` | `2250-2280` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_build_metro_graph_data` | `2283-2503` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_is_valid_transfer_pair` | `2350-2373` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_shortest_metro_path` | `2506-2687` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_build_graph_metro_option` | `2690-3042` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_build_ferry_only_options` | `3045-3181` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_ferry_terminal_name` | `3060-3065` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_near_ferry_terminals` | `3067-3078` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_transit_signature` | `3184-3189` | Transit durak/hat verisi endpointidir. |
| `_diversify_transit_options` | `3192-3400` | Transit durak/hat verisi endpointidir. |
| `_option_walk_m` | `3199-3202` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_option_walk_min` | `3204-3205` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_effective_time` | `3207-3214` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_count_mode` | `3231-3235` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_option_bus_routes` | `3237-3255` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_can_pick_under_route_cap` | `3257-3261` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_route_usage_score` | `3263-3267` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_register_route_usage` | `3269-3271` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_metrobus_simplicity_score` | `3273-3279` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_pick` | `3281-3306` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_is_reasonable_transit_time` | `3403-3409` | Transit durak/hat verisi endpointidir. |
| `_is_reasonable_transit_distance` | `3412-3417` | Transit durak/hat verisi endpointidir. |
| `_normalize_allowed_modes` | `3420-3433` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_is_metrobus_code` | `3436-3438` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_is_rail_route_code` | `3441-3452` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_option_user_modes` | `3455-3486` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_is_absurd_transit_option` | `3489-3529` | Transit durak/hat verisi endpointidir. |
| `_find_one_transfer_candidates` | `3532-3581` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_get_route_stop_candidates_after` | `3584-3640` | Rota hesaplama endpointi veya rota kayit/okuma islemi. |
| `_get_route_stop_candidates_before` | `3643-3698` | Rota hesaplama endpointi veya rota kayit/okuma islemi. |
| `_build_bus_metro_mixed_options` | `3701-3929` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_build_metro_bus_mixed_options` | `3932-4267` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_dest_has_metrobus` | `3965-3970` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `find_transit_routes` | `4274-4832` | Transit durak/hat verisi endpointidir. |
| `compare_routes` | `4835-4944` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |

### 6.1 Multimodal Algoritmalar
- `_shortest_metro_path` `2506-2689`: state-space Dijkstra (station,line,transfer,used_ferry).
- `_build_graph_metro_option` `2690-3044`: artan yaricapla aday durak + varyant skorlama.
- `_build_ferry_only_options` `3045-3183`: sadece vapur seciminde deterministic rota uretimi.
- `_diversify_transit_options` `3192-3402`: hizli/az aktarma/az yurume odakli secenek cesitleme.
- `find_transit_routes` `4274-4834`: transit aday uretimi + filtreleme + mode kisit uygulama.
- `compare_routes` `4835-4969`: API cevabi, onerilen sonuc ve telemetry birlestirme.

## 7) backend/route_engine_impl.py - Tam Fonksiyon Katalogu

| Fonksiyon | Satir | Ne Yapar |
|---|---:|---|
| `_safe_print` | `27-32` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_routing_weight_key` | `38-39` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_route_speed_kmh` | `42-47` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_route_debug_enabled` | `50-52` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_route_debug_log` | `55-57` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `__init__` | `63-65` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `to_payload` | `67-73` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `shortest_path` | `76-95` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_node_coord` | `98-101` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_best_edge_data` | `104-114` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_is_valid_path` | `117-121` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `_extract_edge_coords` | `124-159` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `sqdist` | `151-152` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `nodes_to_coords` | `162-185` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `solve_tsp` | `187-296` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `build_full_route` | `299-329` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `calculate_route_stats` | `332-366` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `generate_google_maps_link` | `369-384` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `path_to_edges` | `387-397` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `count_edge_overlap` | `400-434` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `normalize_edge` | `414-418` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `dynamic_overlap_threshold` | `437-453` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `get_max_candidates` | `456-468` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `__init__` | `480-488` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `finish` | `490-511` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `check_alternative_potential` | `514-554` | Ayni noktalar icin alternatif rota adaylari uretir. |
| `find_disjoint_paths` | `557-610` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `dynamic_overlap_threshold_connectivity` | `613-664` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `apply_penalty_to_graph` | `667-712` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `find_routes_with_penalty` | `715-777` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `get_fallback_routes` | `780-846` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `get_body_edges` | `853-863` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `calculate_via_route_sample_count` | `866-882` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `find_via_node_routes` | `885-1036` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `min_distance_to_route` | `964-974` | Uygulama akisinin yardimci veya orchestration fonksiyonudur. |
| `find_alternative_routes` | `1039-1270` | Ayni noktalar icin alternatif rota adaylari uretir. |
| `build_alternative_routes` | `1273-1319` | Ayni noktalar icin alternatif rota adaylari uretir. |
| `build_all_alternative_routes_batch` | `1322-1405` | Ayni noktalar icin alternatif rota adaylari uretir. |

### 7.1 Rota Algoritmalari
- `shortest_path` `76-97`: weighted shortest path (NetworkX).
- `solve_tsp` `187-298`: coklu nokta siralama optimizasyonu ve unreachable kontrolu.
- `find_alternative_routes` `1039-1272`: disjoint + penalty + via-node + fallback kombinasyonu.
- `build_all_alternative_routes_batch` `1322-1405`: segment alternatiflerinden 3 tam rota olusturma.

## 8) Capraz Akislar (UI -> API -> Engine)

- Rota hesapla: `app.js/calculateRoute` -> `/api/get-route` -> `route_engine_impl` hesaplama akisi.
- Alternatif rota: `app.js/showAlternativeRoutes` -> `/api/get-alternative-routes` -> batch alternatif motoru.
- POI arama: `app.js/searchPois` -> `/api/search-pois` -> POI kaynaklari + cache katmani.
- NLP parse: `app.js/analyzeNaturalLanguageQuery` -> `/api/nlp/parse` -> `BertNLPEngine.parse`.
- Local LLM/RAG: `app.js/mainLlmSendMessage` -> `/api/llm/local/chat/rag` -> RAG karar + local model.
- Transit karsilastirma: UI mod secimi -> `/api/multimodal/compare` -> `multimodal_engine.compare_routes`.

## 9) Not
- Bu surum encoding sorunu olmamasi icin ASCII/temiz UTF-8 metinle yazilmistir.
- Satir numaralari dosya degistikce kayabilir; sunum oncesi hizli kontrol onerilir.
