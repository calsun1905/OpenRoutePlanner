# POI Semantic Tag Grounding Plani

## 1) Problem Tanimi
Su an sistem bazi sorgularda (ornegin `cami`, `stadyum`, `kantin`) bu kelimeleri yer adi gibi yorumlayabiliyor.
Bu da yanlis `detected_places` ve yanlis POI ciktisina neden oluyor.

Hedef:
- `lokasyon` ve `POI tipi`ni ayri ele almak
- `POI tipi`ni OSM tag semasi uzerinden BERT ile eslestirmek
- kelime->tag hardcoded sozluk kullanmadan dogru Overpass filtresi uretmek

## 2) Cozum Ozet
Onersilen yontem: **Schema-based Semantic Grounding**

- Startup'ta tek sefer:
  - OSM tag semasi (key=value) + Turkce aciklama metinleri yuklenir
  - her sema kaydi icin embedding hesaplanir ve RAM'de cache edilir
- Request'te:
  - BERT parse ile lokasyon cikartilir
  - sorgunun POI konsepti (concept phrase) cikartilir
  - concept embedding'i sema embedding'leri ile karsilastirilir
  - en iyi tag(ler) secilir
  - Overpass sorgusu sadece final adimda secilen tag ile calisir

Bu akista Overpass, grounding asamasinda degil; sadece sonuc getirme asamasinda kullanilir.

## 3) Neden Bu Yontem
- Dusuk latency: Overpass cagrisi tek adimda.
- Deterministik ve aciklanabilir: hangi tag neden secildi loglanabilir.
- Bakimi kolay: buyuk kelime sozlugu yerine sema metin bakimi.
- Genisleyebilir: yeni kategori eklemek sadece sema kaydi eklemekle olur.

## 4) Mimari Bilesenler

### 4.1 `backend/poi_schema_catalog.py`
Icerik:
- `SchemaEntry` veri modeli (id, key, value, tr_desc, en_desc, examples, quality_weight)
- baslangicta ~150-200 sema kaydi

Not:
- Bu bir kelime->tag map degil.
- Her tag kaydi icin aciklayici metin ve ornek ifade bulunur.

### 4.2 `backend/poi_schema_embedder.py`
Icerik:
- startup'ta tum schema metinlerini BERT ile embed eder
- memory cache + opsiyonel disk cache (npz/json)
- singleton erisim

### 4.3 `backend/poi_grounder.py`
Icerik:
- `ground_concept_to_tags(concept_text, top_k=3)`
- semantic similarity hesaplama
- skor siralama
- confidence ve debug trace uretimi

### 4.4 Entegrasyon Noktalari
- `backend/bert_nlp_engine.py`
  - parse sonucu `type=poi` oldugunda `location` ve `poi_concept` ayri alanlar
- `backend/app.py`
  - `/api/nlp/parse` response'una `poi_grounding` (opsiyonel debug)
- `backend/app.py` veya ilgili servis
  - final Overpass cagrisi top tag ile

## 5) Veri Akisi (Request)
1. Kullanici sorgusu: `maltepe'de cami ariyorum`
2. NLP parse:
   - `type=poi`
   - `location=Maltepe`
   - `poi_concept='cami ariyorum'` (veya normalize edilmis concept)
3. Grounding:
   - concept embedding -> schema embedding search
   - top_k tag secimi
4. Final query:
   - `location=Maltepe`
   - `tag=amenity=place_of_worship` (ornek)
   - Overpass sorgusu
5. Sonuc:
   - POI listesi + grounding debug (opsiyonel)

## 6) Skorlama Onerisi
Temel:
- `semantic_score = cosine(concept_emb, schema_emb)`

Final:
- `final_score = semantic_score * quality_weight`

Opsiyonel gelistirme:
- `top1-top2 margin` ile guven kontrolu
- dusuk margin durumunda `clarification_required=true`

## 7) Hardcoded Olmadan Dogruluk Stratejisi
Hardcoded kelime->tag sozlugu yok.
Ama schema aciklama metinleri kaliteli olmali:
- kisa aciklama
- yaygin kullanim sekli
- 2-3 ornek ifade

Bu sayede model, kelime ezberlemek yerine anlam eslestirmesi yapar.

## 8) Loglama ve Gozlemlenebilirlik
Her POI parse icin su loglar onerilir:
- `concept_text`
- top_k tag adaylari (score ile)
- secilen tag
- secilme nedeni (score/margin)
- Overpass sonuc sayisi

Ornek log:
`[POI GROUND] concept='cami' top=[amenity=place_of_worship:0.93, tourism=attraction:0.41] selected=amenity=place_of_worship`

## 9) Test Plani

### 9.1 Unit Test
- concept -> tag secimi
- threshold/margin davranisi
- bos/hatali concept

### 9.2 Integration Test
- `maltepe'de cami ariyorum` -> place_of_worship
- `kadikoyde stadyum` -> stadium/sport ilgili tag
- `besiktasta okul` -> school/education ilgili tag

### 9.3 Regression
- mevcut route/multi/single akislari etkilenmemeli
- weather ve diger endpointler etkilenmemeli

## 10) Rollout Plani
1. Faz 1: Catalog + Embedder + Grounder (arka planda hazir)
2. Faz 2: `/api/nlp/parse` debug response'a grounding ekle
3. Faz 3: POI query pipeline'da aktif et (feature flag ile)
4. Faz 4: eski heuristicleri kademeli azalt

Feature flag onerisi:
- `ORP_POI_GROUNDER_ENABLED=1`
- `ORP_POI_GROUNDER_TOP_K=3`
- `ORP_POI_GROUNDER_MIN_MARGIN=0.08`

## 11) Beklenen Sonuc
- `cami` gibi kavramlar yer adi gibi yanlis yakalanmaz
- POI sorgularinda dogru tag secim orani artar
- sistem daha aciklanabilir ve bakimi kolay hale gelir

