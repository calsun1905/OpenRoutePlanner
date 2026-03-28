# 2026-03-28 - Guncel Durum ve Yeni Ucuncu Asama Notlari

Bu bolum bugun yapilanlari ve ekipten gelen yeni 3 ana istegi sirali sekilde resmi kayda alir.

## A) Bugun yapilanlar (toplu tasima + metro)
- Toplu tasima ciziminde sapma kontrolu iyilestirildi:
  - Otobus ciziminde OSRM sonucu asiri saparsa durak polyline fallback mekanizmasi eklendi.
  - Waypoint ornekleme ile gereksiz zigzag/detour etkisi azaltildi.
- Toplu tasima katman temizligi ve harita adim gostergeleri sadeletirildi:
  - Destination marker her segmentte degil, rota sonunda bir kez gosteriliyor.
- Metro seceneklerini bulma guclendirildi:
  - Arama yaricapi genisletildi.
  - Sure/mesafe filtreleri daha gercekci esiklere cekildi.
  - Aktarma tespiti sadece istasyon adi ile degil fiziksel yakinlik ile de desteklendi.
  - Ayni metro kombinasyonlari tekilleştirildi (tekrarli kartlar azaltildi).

## B) Ekipten gelen yeni 3 oncelik (sirali islenecek)
1. LLM chatbotu ana uygulamaya entegre etme (birinci oncelik).
2. BERT/NLP motorunu akis bazli guclendirme (ikinci oncelik).
3. Veritabani stratejisini netlestirme ve yazili hale getirme (ucuncu oncelik).

## C) 1. Oncelik - LLM Chatbot entegrasyonu (yeni net hedef)
Durum:
- Dun eklenen free LLM anahtarlari var; bir kismi stabil, bir kismi bozuk veya rate-limitli.
- LLM test sayfasi ile "calisiyor / calismiyor" kontrolu zaten yapilabiliyor.

Hedef:
- Test ekranindaki yetenegi urunun ana chatbot akisina tasimak.
- Kullaniciya model sagligi ve hata sinifi gorunur hale getirmek.

Uygulama adimlari:
1. Ana arayuze chatbot panelini kalici olarak bagla.
2. Model secimini "stabil / rate-limit / kredi / uyumsuz endpoint" kategorilerine ayir.
3. Otomatik fallback + manuel model secimi modlarini ayni panelde koru.
4. Istek bazli log ile model saglik puani uretilsin (basari orani, ortalama gecikme, son hata kodu).
5. "Bozuk key/model" otomatik devreden cikarilsin, bir sure sonra tekrar denensin (cooldown).

Bugun bu baslikta tamamlanan teknik adimlar:
- `backend/llm_health.py` eklendi:
  - model bazli basari/basarisizlik takibi
  - ardiskik hata sayisi
  - cooldown suresi ve gecici bloklama
- API genisletmeleri:
  - `GET /api/llm/model-health?provider=openrouter|gemini`
  - provider status endpointlerinde `blocked_models` ve `health_count` alanlari
- Chat stream akisi guncellendi (OpenRouter + Gemini):
  - fallback denemelerinde cooldown aktif modeller otomatik atlanir
  - her deneme sonucu health tablosuna yazilir (success/failure, error_type, latency)
- Frontend chatbot paneli guncellendi:
  - model listesinde cooldown'daki modeller ayri grupta gosterilir
  - manuel modda cooldown'daki model secimi engellenir
  - durum satirinda cooldown model sayisi gosterilir

## D) 2. Oncelik - BERT/NLP motorunu guclendirme (arkadas notlarinin resmi kaydi)
Temel problem:
- BERT tek basina yeterli degil; preprocess + regex guard + kok/ek normalize + semantic eslestirme birlikte calismali.

Hedef akis (ornek: "Kadikoyde cami ariyorum"):
1. Cumle alinir ve normalize edilir (unicode/encoding/punktuasyon/harf duzeltme).
2. Tokenizasyon + kok/ek ayristirma yapilir.
3. Lokasyon adayi ve mekan adayi birlikte cikartilir.
4. Mekan adayi OSM/Overpass tag adaylarina maplenir (synonym + turkce varyant destekli).
5. Lokasyon adayi geocoder veya lokal place verisiyle dogrulanir.
6. BERT embedding skoruyla adaylar siralanir; regex/kural sinyali ile birlestirilir.
7. En iyi sorgu plani secilir ve confidence ile birlikte calistirilir.
8. Ciktiya "neden bu etiket secildi" iz kaydi eklenir.

Teknik not:
- Embedding tek karar verici olmayacak.
- Regex tek basina motor olmayacak.
- Hibrit skor (kural + embedding + sozluk eslesmesi) esas alinacak.

Bugun bu baslikta tamamlanan teknik adimlar:
- POI concept resolver debug katmani eklendi:
  - `resolve_poi_from_tokens_with_debug(...)` ile ngram denemeleri, adaylar ve secilen sonuc adim adim kaydediliyor.
- BERT parse sonucuna query-plan gorunurlugu eklendi:
  - `poi_token_candidates`
  - `poi_resolution_plan`
  - `poi_osm_queries`
  - `poi_resolution_status`
- POI etiket ipucunda fallback guclendirildi:
  - Sozlukten dogrudan `poi_tags_hint` yoksa `poi_osm_queries` ilk adayindan etiket ipucu uretiliyor.
- Debug trace iyilestirildi:
  - Parse trace logunda POI plan denemelerinin ilk adimlari gorunur hale getirildi.

## E) 3. Oncelik - Veritabani basligi (yeni oturumda detaylandirilacak)
- Bu basliga ekipten gelecek yeni veritabani dusunceleri eklenerek net karar dokumani cikarilacak.
- Ozellikle su kararlar netlestirilecek:
  - SQLite ile devam + optimizasyon mu?
  - Yoksa PostgreSQL gecis planlamasi mi?
  - Cache/arsiv tablolarinin saklama politikasi ve ekip ici senkron kurallari.

Bugun bu baslikta tamamlanan teknik adimlar:
- NLP parse audit katmani eklendi:
  - Yeni modul: `backend/nlp_audit.py`
  - Tablo: `nlp_parse_audit`
  - Kaydedilen alanlar: query_redacted, query_type, confidence, parse_time_ms,
    origin/destination/location, detected_places, poi_concept, poi_tags_hint,
    poi_resolution_source/confidence/status, poi_osm_queries, error_text, trace metadata.
- Runtime baslatmada audit semasi otomatik garanti edildi (`initialize_runtime` icinde).
- `/api/nlp/parse` endpointi basarili parse sonuclarini audit tablosuna yazar hale getirildi;
  donuste `audit_id` alani eklendi.
- Parse endpointinde hata olursa da audit kaydi (minimal payload + error_text) yaziliyor.
- Son kayitlari UI/test tarafinda hizli gorebilmek icin endpoint eklendi:
  - `GET /api/nlp/audit/recent?limit=50`

---

# 2026-03-24 - Ucuncu Asama Plani (LLM + BERT + Veritabani)

Bu bolum, bugun tamamlanan teknik degisiklikleri ve bir sonraki sprintte uygulanacak net yol haritasini resmi kayit olarak tutar.

## 0) Ek tamamlananlar — POI cache, arsiv ve stabilizasyon
- POI yumusak TTL yaklasik **14 gun** olacak sekilde ayarlandi (`POI_CACHE_SOFT_TTL_DAYS = 14`); hard/empty TTL ve mevcut stale-while-revalidate akisi korunuyor.
- Ana POI cache (`pois` tablosu) **yenilenmeden once** eski JSON + zaman damgasi, ayni `pois.db` icindeki **`pois_archive`** tablosuna kopyalaniyor; yer+kategori basina son **N** surum tutuluyor (`POI_ARCHIVE_MAX_PER_KEY`, varsayilan 5). Silmeden once tekrar kullanim / ileride geri yukleme API icin zemin.
- Genis idari alanlarda (il/ilce) **parcali grid tarama + birlestirme** eklendi; cok buyuk bbox icin tek sorgu yerine hucre bazli sorgu ve dedup (`POI_BOUNDARY_CHUNK_*` anahtarlari `route_config.py`).
- Frontend `app.js` icinde kalan bozuk `??` / ikon metinleri **Unicode escape** ile duzeltildi; `index.html` icinde `app.js` cache kirma surumu guncellendi.
- `docs/CACHE_REPOLITIKASI.md` eklendi; `docs/VERITABANI_BILGILENDIRME.md` POI arsivi ve TTL ozetiyle guncellendi.
- `.gitignore` altinda `backend/cache/*` + `.gitkeep` ve istege bagli repoya alinacak dosyalar icin **yorumlu ornek** `!` satirlari netlestirildi.

## 1) Bugun yapilanlar (tamamlanan)
- Harita yuklenmeme problemi frontend tarafinda giderildi.
- Turkce metinlerdeki gorunum/encoding bozulmalarina yonelik duzeltmeler yapildi.
- POI arama tarafinda il/ilce secimi ile kapsam davranisi iyilestirildi.
- POI cache yonetimine soft TTL, hard TTL ve empty TTL stratejileri eklendi.
- API testleri guncel endpoint davranisiyla hizalandi.

## 2) Dun yapilan LLM calismalari (durum)
- OpenRouter tabanli canli test sayfasi eklendi.
- Free modeller tek tek test edildi.
- Sonuclar model bazinda asagidaki siniflara ayrildi:
  - Sorunsuz cevap donen modeller
  - 429 rate limit veren modeller
  - 402 kredi isteyen modeller
  - 400 endpoint uyumsuz modeller (ornek: embedding modeli chat endpointinde)
- Bu sayfa sayesinde modelin calisip calismadigi, neden hata verdigi ve hangi kodla hata verdigi canli gorulebiliyor.

## 3) Birinci oncelik: LLM chatbotu ana uygulamaya entegre etme
Hedef:
- Test ekranindaki LLM altyapisini ana uygulama akisina tasimak.
- Kullanici tarafinda model secimi, model durumu ve hata sinifini net gostermek.

Planlanan moduller:
1. Ana arayuze chatbot paneli/sekmesi eklenmesi.
2. Model secim ekraninin kategorik hale getirilmesi:
   - calisanlar
   - limitli/tikananlar
   - kredi isteyenler
   - uyumsuz endpoint gerektirenler (embedding/video vb)
3. Fallback kullanan panel ile manuel model secim panelinin ayrilmasi.
4. Sistem prompt yonetiminin merkezilestirilmesi.
5. Hata mesajlarinin teknik ama okunur formatta siniflandirilmasi.

## 4) Ikinci oncelik: BERT/NLP motorunu guclendirme
Problem:
- BERT tek basina yeterli degil; preprocess, regex guard, kok/ek normalizasyonu ve semantic eslestirme birlikte calismali.

Hedeflenen parse akisi (ornek: "Kadikoyde cami ariyorum"):
1. Cumle girisi alinir.
2. On isleme yapilir (normalizasyon, unicode temizlik, noktalama sadeleme).
3. Aday varliklar cikartilir (lokasyon adayi + mekan adayi).
4. Kok-ek ayristirma ve kelime kanoniklestirme yapilir.
5. Mekan adayi Overpass/OSM tag setine maplenir.
6. Lokasyon adayi geocoder veya yerel place verisi ile dogrulanir.
7. Arama plani secilir (il/ilce secimine gore boundary bazli arama).
8. Sonuc skoru + confidence + iz kaydi uretilir.

Not:
- Regex tek basina ana motor degil; BERT ve semantic katman icin emniyet agi olmalidir.
- Embedding skoru tek karar noktasi olmamali; kural tabanli sinyallerle birlikte kullanilmalidir.

## 5) Ucuncu oncelik: Veritabani stratejisi
Mevcut:
- Uygulama SQLite3 ile calisiyor.
- Veriler lokal `.db` dosyalarinda tutuluyor.

Gelecek:
- Ihtiyac buyurse PostgreSQL gibi dis SQL veritabanina gecis planlanabilir.
- Mevcut tablo yapisi duzenli oldugu icin SQL tabanli migration teknik olarak uygundur.

Ek dokumantasyon:
- `docs/VERITABANI_BILGILENDIRME.md` dosyasi bu kapsamda olusturuldu/guncellendi.
- Bu dosya "hangi veri nerede tutuluyor" sorusunun teknik referans dokumani olarak kullanilacaktir.

## 6) Coklu bilgisayar / ekip calisma notu
- Merkezi bir dis veritabani olmadigi icin belirli cache dosyalarinin da repoda tasinabilir olmasi gerekiyor.
- Bu nedenle kritik cache artefaktlari (ozellikle `backend/cache/*.json` ve `backend/cache/geocodes.db`) surum kontrolune alinmistir.
- Amac: farkli bilgisayarda acildiginda ilk sorgularda ayni veri tabanina yakin davranis elde etmek.

## 7) Bu oturum commit ozeti (kisa)
- Yapilan: Progress kayitlarinin detaylandirilmasi, LLM/BERT/DB yol haritasinin netlestirilmesi, veritabani bilgilendirme dokumaninin duzenlenmesi.
- Siradaki adim: Chatbot entegrasyonu + BERT parse pipeline kalitesi + veri katmani kararlarinin teknik parcali implementasyonu.

## 8) Bugun devam edilen teknik degisiklikler (detayli)
- Ana ekrana sag dock chat paneli eklendi: ac/kapa davranisi, mobilde drawer benzeri akis, masaustunde harita alaninin chat paneline gore yeniden boyutlanmasi.
- Ana ekrandaki LLM kutusu iki moda ayrildi ve birlikte korundu:
  - otomatik fallback modu
  - manuel tek model modu
- Manuel model seciminde kategori bazli filtreleme netlestirildi:
  - sorunsuz calisanlar
  - tikananlar
  - limit hatasi (429)
  - para/kredi gerektiren (402)
  - embedding/vl (chat uyumsuz)
- LLM sohbet oturumlari kalici hale getirildi:
  - backend'de `chat_sessions` ve `chat_messages` semasi,
  - frontend'de oturum secimi/yeni oturum/arsivleme,
  - mesajlarin tekrar yuklenmesi ve local cache ile hizli geri acilis.
- Stream endpointleri oturum bazli calisacak sekilde genisletildi (`session_id`):
  - OpenRouter stream sonunda user+assistant mesaji DB'ye yaziliyor.
  - Gemini stream sonunda user+assistant mesaji DB'ye yaziliyor.
  - LLM context penceresi son 40 mesaj olacak sekilde kullaniliyor.
- JSON mirror senkronu eklendi:
  - `backend/data/chat_history.sync.json` uretimi,
  - acilista JSON -> DB rebuild/sync akisi,
  - coklu cihazda Git merge kolayligi.
- Turkce karakter/encoding tarafinda runtime onarim katmani eklendi:
  - `backend/text_utils.py` ile `repair_text`,
  - API giris/cikislarinda ve stream token birlestirmede metin temizligi,
  - frontend tarafinda da benzer metin onarimlari.
- POI/cache tarafindaki onceki iyilestirmeler korunarak bugunle uyumlu hale getirildi (dokumantasyonla birlikte).

## 9) Gemini notu (Google AI Studio + yedek anahtar stratejisi)
- Gemini entegrasyonu icin Google AI Studio uzerinden alinan API anahtari akisi kullanildi.
- Projede Gemini anahtar okumasi iki isimden yapiliyor:
  - `GEMINI_API_KEY`
  - `GOOGLE_API_KEY`
- Varsayilan model + fallback model listesi ENV ile yonetilecek sekilde ayarlandi.
- Operasyon notu:
  - Gemini tarafinda farkli key'ler kullanilacagi icin yedek anahtar stratejisi zorunlu.
  - Limit veya kota durumunda anahtar rotasyonu yapilacak sekilde ortam degiskenlerinin guncel tutulmasi gerekiyor.
  - Ileride Gemini modellerini daha efektif kullanmak icin model/fallback sirasi ve key rotasyonu birlikte optimize edilecek.

## 10) Degisen 19 dosya icin 5 commit hazirlik plani (sablon uyumlu taslak)
Not: Asagidaki plan "hazirlik" amaclidir; commit atilmadan once son diff kontrolu yapilacaktir.

1) fix: ana ekran chat panel yerlesimi + ui davranis duzeltmeleri
- Dosyalar:
  - `frontend/index.html`
  - `frontend/css/style.css`
  - `frontend/js/app.js`
  - `frontend/openrouter-chat.html`
- Kazanim:
  - sag dock panel akisinin stabil hale gelmesi
  - model secim ekraninin daha okunur ve kategorik kullanimi
  - panel ac/kapa ve mobil davranislarinin toparlanmasi

2) feat: kalici sohbet oturumu (session + message) ve stream kaliciligi
- Dosyalar:
  - `backend/chat_storage.py`
  - `backend/storage_db.py`
  - `backend/app.py`
  - `backend/data/chat_history.sync.json`
- Kazanim:
  - cok oturumlu sohbet
  - session bazli gecmis yukleme/arsivleme
  - stream sonunda mesajlarin DB + JSON mirror'a yazilmasi

3) feat: Gemini servis entegrasyonu (chat + stream + fallback)
- Dosyalar:
  - `backend/gemini_env.py`
  - `backend/gemini_service.py`
  - `backend/app.py`
  - `.env.example`
- Kazanim:
  - OpenRouter yanina Gemini provider secenegi
  - Gemini model/fallback sirasi ile daha dayanikli akis
  - ENV tarafinda net Gemini konfigurasyonu

4) fix/chore: turkce karakter onarimi + cache/git politikasi netlestirme
- Dosyalar:
  - `backend/text_utils.py`
  - `backend/app.py`
  - `backend/route_config.py`
  - `backend/graph_manager.py`
  - `.gitignore`
  - `docs/CACHE_REPOLITIKASI.md`
  - `docs/VERITABANI_BILGILENDIRME.md`
- Kazanim:
  - mojibake/encoding bozulmalarina karsi koruma
  - cache artefaktlarinin repoda nasil yonetileceginin netlestirilmesi
  - POI cache/arsiv davranisinin dokumante edilmesi

5) test/docs: API testleri + progress kaydinin guncel teknik ozetle tamamlanmasi
- Dosyalar:
  - `tests/test_api/test_llm_chat_sessions_api.py`
  - `progress.md`
- Kazanim:
  - chat session endpointleri ve stream kaliciligi icin test guvencesi
  - bugun yapilanlarin proje kaydina net ve izlenebilir sekilde eklenmesi

---

# Progress - Tum Proje Derin Analiz Raporu

Uretim Tarihi: 2026-03-24 01:14
Kapsam: Git tarafinda takip edilen tum proje dosyalari (git ls-files)
Yontem: Dosya bazli + satir araligi bazli analiz + Python dosyalarinda fonksiyon/sinif/route cikarma

## 1) Ust Duzey Ozet
- Takipli dosya sayisi: 163
- Uzanti dagilimi:
  - .py: 60
  - .md: 42
  - .txt: 18
  - .json: 16
  - .html: 6
  - [uzantisiz]: 5
  - .jsonl: 3
  - .claude: 2
  - .ini: 2
  - .bat: 1
  - .css: 1
  - .example: 1
  - .ico: 1
  - .js: 1
  - .png: 1
  - .svg: 1
  - .tgz: 1
  - .yml: 1

## 2) Satir-Satir Yakinlikta Dosya Analizi
Not: Her dosya icin satir araligi bazli aciklama verildi. Python dosyalarinda fonksiyon/sinif/route listesi ayrica cikartildi.

### 1. `.agent/workflows/baslat.md`
- Satir sayisi: 31
- Boyut: 1094 bayt
- Ilk anlamli satir: ---
- Son anlamli satir: // Bu adımları otomatik çalıştırmak istersen bana söyleyebilirsin.
- Satir araligi incelemesi:
  - L1-L31: basliklar -> ### 1. Oturum Başlangıç Hook'unu Çalıştır; # Agent, aşağıdaki dosyayı oku ve sadece Hızlı Başlangıç (Lite Mod) adımlarını VEYA tüm adımları uygula.; # view_file('.claude/hooks/SessionStart.claude'); ### 2. Sanal Ortamı (Venv) Aktif Et

### 2. `.agent/workflows/kapat.md`
- Satir sayisi: 23
- Boyut: 1008 bayt
- Ilk anlamli satir: ---
- Son anlamli satir: ```
- Satir araligi incelemesi:
  - L1-L23: basliklar -> ### 1. Oturum Bitiş Hook'unu Çalıştır; # Agent, aşağıdaki dosyayı oku ve sadece Hızlı Kapanış (Lite Mod) adımlarını VEYA tüm adımları uygula.; # view_file('.claude/hooks/SessionEnd.claude'); ### 2. Geliştirme Sunucusunu Durdur

### 3. `.claude/hooks/SessionEnd.claude`
- Satir sayisi: 174
- Boyut: 6946 bayt
- Ilk anlamli satir: # 🌙 Oturum Sonu
- Son anlamli satir: - AI Ajana Not: Token limitlerini şişirmemek adına, `git diff HEAD` (saf diff çıktısı) kullanmak yerine sadece listel...
- Satir araligi incelemesi:
  - L1-L60: genel icerik
  - L61-L120: genel icerik
  - L121-L174: genel icerik

### 4. `.claude/hooks/SessionStart.claude`
- Satir sayisi: 271
- Boyut: 9435 bayt
- Ilk anlamli satir: # 🌅 Oturum Başlangıcı
- Son anlamli satir: - **Rapor isimlendirme:** Her gün için tek dosya kullan (`[TARİH].txt`). Her oturumda dosyaya yepyeni bir kayıt gibi ...
- Satir araligi incelemesi:
  - L1-L60: genel icerik
  - L61-L120: genel icerik
  - L121-L180: genel icerik
  - L181-L240: genel icerik
  - L241-L271: genel icerik

### 5. `.claude/settings.json`
- Satir sayisi: 9
- Boyut: 143 bayt
- Ilk anlamli satir: {
- Son anlamli satir: }
- Satir araligi incelemesi:
  - L1-L9: veri satirlari/json icerigi

### 6. `.claude/settings.local.example.json`
- Satir sayisi: 18
- Boyut: 372 bayt
- Ilk anlamli satir: {
- Son anlamli satir: }
- Satir araligi incelemesi:
  - L1-L18: veri satirlari/json icerigi

### 7. `.claude/settings.local.json`
- Satir sayisi: 49
- Boyut: 1985 bayt
- Ilk anlamli satir: {
- Son anlamli satir: }
- Satir araligi incelemesi:
  - L1-L49: veri satirlari/json icerigi

### 8. `.env.example`
- Satir sayisi: 63
- Boyut: 2421 bayt
- Ilk anlamli satir: ﻿# OpenRoutePlanner environment variables example
- Son anlamli satir: OPENROUTER_APP_TITLE=OpenRoutePlanner
- Satir araligi incelemesi:
  - L1-L60: genel icerik
  - L61-L63: Bos/yalnizca bosluk

### 9. `.gitattributes`
- Satir sayisi: 2
- Boyut: 66 bayt
- Ilk anlamli satir: # Auto detect text files and perform LF normalization
- Son anlamli satir: * text=auto
- Satir araligi incelemesi:
  - L1-L2: genel icerik

### 10. `.github/workflows/ci.yml`
- Satir sayisi: 48
- Boyut: 1483 bayt
- Ilk anlamli satir: name: CI
- Son anlamli satir: backend/test_weather_service.py
- Satir araligi incelemesi:
  - L1-L48: genel icerik

### 11. `.gitignore`
- Satir sayisi: 38
- Boyut: 732 bayt
- Ilk anlamli satir: venv/
- Son anlamli satir: claude-mem-*.tgz
- Satir araligi incelemesi:
  - L1-L38: genel icerik

### 12. `.mcp.json`
- Satir sayisi: 15
- Boyut: 351 bayt
- Ilk anlamli satir: {
- Son anlamli satir: }
- Satir araligi incelemesi:
  - L1-L15: veri satirlari/json icerigi

### 13. `.vscode/settings.json`
- Satir sayisi: 3
- Boyut: 46 bayt
- Ilk anlamli satir: {
- Son anlamli satir: }
- Satir araligi incelemesi:
  - L1-L3: veri satirlari/json icerigi

### 14. `CLAUDE.md`
- Satir sayisi: 247
- Boyut: 9288 bayt
- Ilk anlamli satir: # CLAUDE.md
- Son anlamli satir: - **Onay İste:** Kod değişikliği öncesi kısa özet sun ve onay al
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # CLAUDE.md; ## Project Overview; ## Common Commands; # Development setup
  - L61-L120: basliklar -> ## NLP Architecture (Dual Engine); ## Graph Management; ## Database Schema; ## API Response Format
  - L121-L180: basliklar -> ## Environment Variables; ## Weather Service (v1.0); ## Testing Conventions
  - L181-L240: basliklar -> ## File Organization Notes; ## Important Gotchas; # 🇹🇷 KULLANICI ÖZEL KURALLARI; ## İletişim Tarzı
  - L241-L247: basliklar -> ## Chat Arayüzü Davranışı

### 15. `PROJECT_INDEX.md`
- Satir sayisi: 270
- Boyut: 10628 bayt
- Ilk anlamli satir: # OpenRoutePlanner - Live Project Index
- Son anlamli satir: - **Storage behavior**: `backend/route_storage.py`, `backend/location_storage.py`, `backend/storage_db.py`.
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # OpenRoutePlanner - Live Project Index; ## 1) Top-Level Structure; ## 2) Runtime Architecture (High Level); ## 3) Backend Module Index
  - L61-L120: basliklar -> ## 4) Actual API Endpoint Index (`backend/app.py`); ### Route + POI; ### Health + Geocode; ### Frontend Serving
  - L121-L180: basliklar -> ## 5) BERT-Focused Deep Index; ### Main BERT files; ### BERT runtime behavior (current); ### BERT parse pipeline (current)
  - L181-L240: basliklar -> ### Weather service behavior; ### Route weather output model; ### Important note; ## 7) Frontend Index
  - L241-L270: basliklar -> ## 10) Change Entry Points (for next tasks)

### 16. `README.md`
- Satir sayisi: 266
- Boyut: 9071 bayt
- Ilk anlamli satir: # OpenRoutePlanner
- Son anlamli satir: - `http://localhost:5000/openrouter-chat.html`
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # OpenRoutePlanner; ## Özellikler; ### 🗺️ Rota Optimizasyonu; ### 🤖 Yapay Zeka
  - L61-L120: basliklar -> ### Diğer (6 endpoint); ## Kurulum; # 1. Repoyu klonla; # 2. Sanal ortam oluştur
  - L121-L180: basliklar -> ## Test; # Tüm testleri çalıştır; # Coverage raporu oluştur; # Sadece API testleri
  - L181-L240: basliklar -> ## Geliştirme Durumu; ### v3.0 Özellikleri (Tamamlandı); ### Güvenlik Düzeltmeleri (v3.1 - Tamamlandı); ### Test Altyapısı (v3.2 - Tamamlandı)
  - L241-L266: metin/rapor icerigi

### 17. `backend/app.py`
- Satir sayisi: 2488
- Boyut: 85905 bayt
- Python ozeti: import=38, sinif=0, fonksiyon=72, flask_route=46
- Fonksiyonlar:
  - L18: _env_flag
  - L26: _env_float
  - L37: _openrouter_system_prompt
  - L56: _inject_system_message
  - L68: _configure_live_console_output
  - L94: _environbuilder_init
  - L207: _preload_bert_async
  - L218: _target
  - L256: _poi_version_token
  - L260: _should_log_bert_metrics
  - L272: _log_bert_runtime_metrics
  - L295: _log_bert_parse_trace
  - L358: initialize_runtime
  - L373: initialize_graph_preload
  - L386: _get_cached_graph
  - L402: _redact_pii_text
  - L411: _request_trace_prefix
  - L418: _ensure_runtime_initialized
  - L438: _attach_trace_headers
  - L448: _disable_bert_runtime
  - L456: _build_regex_fallback_result
  - L467: api_get_route
  - L568: api_get_route_steps
  - L606: build_turn_by_turn_steps
  - L664: api_get_alternative_routes
  - L758: _coords_equal
  - L780: api_search_pois
  - L869: health_check
  - L875: api_geocode_suggest
  - L892: api_geocode_forward_get
  - L908: api_geocode_reverse_get
  - L922: api_geocode
  - L965: api_reverse_geocode
  - L1004: api_geocode_batch
  - L1045: serve_frontend
  - L1054: serve_static_files
  - L1080: api_save_route
  - L1139: api_get_routes
  - L1196: api_get_route_by_id
  - L1219: api_update_route
  - L1259: api_delete_route
  - L1286: api_toggle_favorite
  - L1315: api_search_routes
  - L1347: api_route_statistics
  - L1374: api_create_timeline
  - L1442: api_check_conflicts
  - L1489: api_optimize_timeline
  - L1535: api_get_locations
  - L1571: api_save_location
  - L1604: api_delete_location
  - L1623: api_update_location
  - L1648: api_toggle_location_favorite
  - L1673: api_nlp_parse
  - L1778: api_nlp_status
  - L1799: api_nlp_similarity
  - L1865: api_nlp_best_match
  - L1946: api_get_weather
  - L2002: api_get_weather_forecast
  - L2059: api_check_route_weather
  - L2122: api_weather_status
  - L2153: api_weather_health
  - L2171: api_weather_clear_cache
  - L2193: api_openrouter_status
  - L2216: api_openrouter_chat
  - L2292: api_openrouter_chat_stream
  - L2330: _generator
  - L2365: api_openrouter_models
  - L2393: api_nlp_warmup
  - L2411: api_nlp_seed_places
  - L2438: _run_cmd
  - L2459: api_nlp_optimize_model
  - L2471: _run_cmd
- Flask route satirlari:
  - L466: @app.route("/api/get-route", methods=["POST"])
  - L567: @app.route("/api/get-route-steps", methods=["POST"])
  - L663: @app.route("/api/get-alternative-routes", methods=["POST"])
  - L779: @app.route("/api/search-pois", methods=["POST"])
  - L868: @app.route("/api/health", methods=["GET"])
  - L874: @app.route("/api/geocode/suggest", methods=["GET"])
  - L891: @app.route("/api/geocode/forward", methods=["GET"])
  - L907: @app.route("/api/geocode/reverse", methods=["GET"])
  - L921: @app.route("/api/geocode", methods=["POST"])
  - L964: @app.route("/api/reverse-geocode", methods=["POST"])
  - L1003: @app.route("/api/geocode/batch", methods=["POST"])
  - L1044: @app.route("/")
  - L1053: @app.route("/<path:filepath>")
  - L1079: @app.route("/api/routes/save", methods=["POST"])
  - L1138: @app.route("/api/routes", methods=["GET"])
  - L1195: @app.route("/api/routes/<route_id>", methods=["GET"])
  - L1218: @app.route("/api/routes/<route_id>", methods=["PUT"])
  - L1258: @app.route("/api/routes/<route_id>", methods=["DELETE"])
  - L1285: @app.route("/api/routes/<route_id>/favorite", methods=["POST"])
  - L1314: @app.route("/api/routes/search", methods=["GET"])
  - L1346: @app.route("/api/routes/statistics", methods=["GET"])
  - L1373: @app.route("/api/timeline/create", methods=["POST"])
  - L1441: @app.route("/api/timeline/check-conflicts", methods=["POST"])
  - L1488: @app.route("/api/timeline/optimize", methods=["POST"])
  - L1534: @app.route("/api/locations", methods=["GET"])
  - L1570: @app.route("/api/locations", methods=["POST"])
  - L1603: @app.route("/api/locations/<location_id>", methods=["DELETE"])
  - L1622: @app.route("/api/locations/<location_id>", methods=["PUT"])
  - L1647: @app.route("/api/locations/<location_id>/favorite", methods=["POST"])
  - L1672: @app.route("/api/nlp/parse", methods=["POST"])
  - L1777: @app.route("/api/nlp/status", methods=["GET"])
  - L1798: @app.route("/api/nlp/similarity", methods=["POST"])
  - L1864: @app.route("/api/nlp/best-match", methods=["POST"])
  - L1945: @app.route("/api/weather", methods=["GET"])
  - L2001: @app.route("/api/weather/forecast", methods=["GET"])
  - L2058: @app.route("/api/weather/check-route", methods=["POST"])
  - L2121: @app.route("/api/weather/status", methods=["GET"])
  - L2152: @app.route("/api/weather/health", methods=["GET"])
  - L2170: @app.route("/api/weather/clear-cache", methods=["POST"])
  - L2192: @app.route("/api/llm/openrouter/status", methods=["GET"])
  - L2215: @app.route("/api/llm/openrouter/chat", methods=["POST"])
  - L2291: @app.route("/api/llm/openrouter/chat/stream", methods=["POST"])
  - L2364: @app.route("/api/llm/openrouter/models", methods=["GET"])
  - L2392: @app.route("/api/nlp/warmup", methods=["GET", "POST"])
  - L2410: @app.route("/api/nlp/seed-places", methods=["POST"])
  - L2458: @app.route('/api/nlp/optimize-model', methods=['POST'])
- Ilk anlamli satir: """
- Son anlamli satir: return jsonify({'error': str(e)}), 500
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=_env_flag, _env_float, _openrouter_system_prompt, _inject_system_message
  - L61-L120: fonksiyonlar=_configure_live_console_output, _environbuilder_init
  - L121-L180: yardimci/degisken/akis kodu
  - L181-L240: fonksiyonlar=_preload_bert_async, _target
  - L241-L300: fonksiyonlar=_poi_version_token, _should_log_bert_metrics, _log_bert_runtime_metrics, _log_bert_parse_trace
  - L301-L360: fonksiyonlar=initialize_runtime
  - L361-L420: fonksiyonlar=initialize_graph_preload, _get_cached_graph, _redact_pii_text, _request_trace_prefix, _ensure_runtime_initialized
  - L421-L480: fonksiyonlar=_attach_trace_headers, _disable_bert_runtime, _build_regex_fallback_result, api_get_route | route_adedi=1
  - L481-L540: yardimci/degisken/akis kodu
  - L541-L600: fonksiyonlar=api_get_route_steps | route_adedi=1
  - L601-L660: fonksiyonlar=build_turn_by_turn_steps
  - L661-L720: fonksiyonlar=api_get_alternative_routes | route_adedi=1
  - L721-L780: fonksiyonlar=_coords_equal, api_search_pois | route_adedi=1
  - L781-L840: yardimci/degisken/akis kodu
  - L841-L900: fonksiyonlar=health_check, api_geocode_suggest, api_geocode_forward_get | route_adedi=3
  - L901-L960: fonksiyonlar=api_geocode_reverse_get, api_geocode | route_adedi=2
  - L961-L1020: fonksiyonlar=api_reverse_geocode, api_geocode_batch | route_adedi=2
  - L1021-L1080: fonksiyonlar=serve_frontend, serve_static_files, api_save_route | route_adedi=3
  - L1081-L1140: fonksiyonlar=api_get_routes | route_adedi=1
  - L1141-L1200: fonksiyonlar=api_get_route_by_id | route_adedi=1
  - L1201-L1260: fonksiyonlar=api_update_route, api_delete_route | route_adedi=2
  - L1261-L1320: fonksiyonlar=api_toggle_favorite, api_search_routes | route_adedi=2
  - L1321-L1380: fonksiyonlar=api_route_statistics, api_create_timeline | route_adedi=2
  - L1381-L1440: yardimci/degisken/akis kodu
  - L1441-L1500: fonksiyonlar=api_check_conflicts, api_optimize_timeline | route_adedi=2
  - L1501-L1560: fonksiyonlar=api_get_locations | route_adedi=1
  - L1561-L1620: fonksiyonlar=api_save_location, api_delete_location | route_adedi=2
  - L1621-L1680: fonksiyonlar=api_update_location, api_toggle_location_favorite, api_nlp_parse | route_adedi=3
  - L1681-L1740: yardimci/degisken/akis kodu
  - L1741-L1800: fonksiyonlar=api_nlp_status, api_nlp_similarity | route_adedi=2
  - L1801-L1860: yardimci/degisken/akis kodu
  - L1861-L1920: fonksiyonlar=api_nlp_best_match | route_adedi=1
  - L1921-L1980: fonksiyonlar=api_get_weather | route_adedi=1
  - L1981-L2040: fonksiyonlar=api_get_weather_forecast | route_adedi=1
  - L2041-L2100: fonksiyonlar=api_check_route_weather | route_adedi=1
  - L2101-L2160: fonksiyonlar=api_weather_status, api_weather_health | route_adedi=2
  - L2161-L2220: fonksiyonlar=api_weather_clear_cache, api_openrouter_status, api_openrouter_chat | route_adedi=3
  - L2221-L2280: yardimci/degisken/akis kodu
  - L2281-L2340: fonksiyonlar=api_openrouter_chat_stream, _generator | route_adedi=1
  - L2341-L2400: fonksiyonlar=api_openrouter_models, api_nlp_warmup | route_adedi=2
  - L2401-L2460: fonksiyonlar=api_nlp_seed_places, _run_cmd, api_nlp_optimize_model | route_adedi=2
  - L2461-L2488: fonksiyonlar=_run_cmd

### 18. `backend/bert_engine.py`
- Satir sayisi: 409
- Boyut: 13334 bayt
- Python ozeti: import=12, sinif=1, fonksiyon=10, flask_route=0
- Siniflar:
  - L44: BERTEngine
- Fonksiyonlar:
  - L33: _env_flag
  - L53: __init__
  - L105: encode
  - L139: encode_batch
  - L176: get_runtime_metrics
  - L226: similarity
  - L250: find_best_match
  - L313: get_bert_engine
  - L332: is_bert_available
  - L351: test_bert_engine
- Ilk anlamli satir: """
- Son anlamli satir: test_bert_engine()
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=_env_flag, __init__ | siniflar=BERTEngine
  - L61-L120: fonksiyonlar=encode
  - L121-L180: fonksiyonlar=encode_batch, get_runtime_metrics
  - L181-L240: fonksiyonlar=similarity
  - L241-L300: fonksiyonlar=find_best_match
  - L301-L360: fonksiyonlar=get_bert_engine, is_bert_available, test_bert_engine
  - L361-L409: yardimci/degisken/akis kodu

### 19. `backend/bert_nlp_engine.py`
- Satir sayisi: 2019
- Boyut: 77978 bayt
- Python ozeti: import=31, sinif=2, fonksiyon=56, flask_route=0
- Siniflar:
  - L693: PlaceDatabase
  - L1192: BertNLPEngine
- Fonksiyonlar:
  - L50: get_all_locations
  - L61: save_dynamic_place
  - L62: get_dynamic_place_names
  - L63: get_all_local_place_names
  - L140: load_intent_template_bundle
  - L187: cosine_similarity
  - L195: should_force_unknown_with_hard_negative
  - L211: apply_intent_conflict_matrix
  - L295: _env_flag
  - L303: _env_float
  - L326: normalize_place_key
  - L335: is_likely_action_token
  - L348: _singularize_tr_token
  - L357: _normalize_poi_mapping
  - L378: is_poi_concept_term
  - L395: _collect_poi_tokens
  - L411: in_occupied_range
  - L440: extract_poi_concept_with_meta
  - L475: extract_poi_concept
  - L480: _extract_explicit_multi_places
  - L515: _extract_plain_multi_places
  - L538: build_place_lookup_keys
  - L566: normalize_query_text
  - L571: normalize_token_with_role
  - L617: extract_candidate_spans
  - L646: add_span
  - L707: __init__
  - L743: _seed_dynamic_cache
  - L754: _seed_user_locations
  - L769: _seed_local_places
  - L783: _seed_turkish_places
  - L796: _seed_fallback_places
  - L822: add_place
  - L846: get_embedding_matrix
  - L865: resolve_lookup
  - L875: find_best_match
  - L911: score_embeddings
  - L963: search_osm_api
  - L1013: add_places_from_osm
  - L1025: cache_osm_results
  - L1112: _build_osm_prefetch_queries
  - L1127: prefetch_osm_candidates
  - L1151: find_all_matches
  - L1199: __init__
  - L1244: _get_template_embeddings
  - L1265: _get_hard_negative_embeddings
  - L1272: classify_query_type_with_scores
  - L1330: classify_query_type
  - L1337: _is_location_like_match
  - L1386: extract_places
  - L1512: detect_route_direction
  - L1531: select_best
  - L1584: _choose_best_poi_location
  - L1615: parse
  - L1951: get_bert_nlp_engine
  - L1969: test_bert_nlp
- Ilk anlamli satir: """
- Son anlamli satir: test_bert_nlp()
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=get_all_locations
  - L61-L120: fonksiyonlar=save_dynamic_place, get_dynamic_place_names, get_all_local_place_names
  - L121-L180: fonksiyonlar=load_intent_template_bundle
  - L181-L240: fonksiyonlar=cosine_similarity, should_force_unknown_with_hard_negative, apply_intent_conflict_matrix
  - L241-L300: fonksiyonlar=_env_flag
  - L301-L360: fonksiyonlar=_env_float, normalize_place_key, is_likely_action_token, _singularize_tr_token, _normalize_poi_mapping
  - L361-L420: fonksiyonlar=is_poi_concept_term, _collect_poi_tokens, in_occupied_range
  - L421-L480: fonksiyonlar=extract_poi_concept_with_meta, extract_poi_concept, _extract_explicit_multi_places
  - L481-L540: fonksiyonlar=_extract_plain_multi_places, build_place_lookup_keys
  - L541-L600: fonksiyonlar=normalize_query_text, normalize_token_with_role
  - L601-L660: fonksiyonlar=extract_candidate_spans, add_span
  - L661-L720: fonksiyonlar=__init__ | siniflar=PlaceDatabase
  - L721-L780: fonksiyonlar=_seed_dynamic_cache, _seed_user_locations, _seed_local_places
  - L781-L840: fonksiyonlar=_seed_turkish_places, _seed_fallback_places, add_place
  - L841-L900: fonksiyonlar=get_embedding_matrix, resolve_lookup, find_best_match
  - L901-L960: fonksiyonlar=score_embeddings
  - L961-L1020: fonksiyonlar=search_osm_api, add_places_from_osm
  - L1021-L1080: fonksiyonlar=cache_osm_results
  - L1081-L1140: fonksiyonlar=_build_osm_prefetch_queries, prefetch_osm_candidates
  - L1141-L1200: fonksiyonlar=find_all_matches, __init__ | siniflar=BertNLPEngine
  - L1201-L1260: fonksiyonlar=_get_template_embeddings
  - L1261-L1320: fonksiyonlar=_get_hard_negative_embeddings, classify_query_type_with_scores
  - L1321-L1380: fonksiyonlar=classify_query_type, _is_location_like_match
  - L1381-L1440: fonksiyonlar=extract_places
  - L1441-L1500: yardimci/degisken/akis kodu
  - L1501-L1560: fonksiyonlar=detect_route_direction, select_best
  - L1561-L1620: fonksiyonlar=_choose_best_poi_location, parse
  - L1621-L1680: yardimci/degisken/akis kodu
  - L1681-L1740: yardimci/degisken/akis kodu
  - L1741-L1800: yardimci/degisken/akis kodu
  - L1801-L1860: yardimci/degisken/akis kodu
  - L1861-L1920: yardimci/degisken/akis kodu
  - L1921-L1980: fonksiyonlar=get_bert_nlp_engine, test_bert_nlp
  - L1981-L2019: yardimci/degisken/akis kodu

### 20. `backend/cache/.gitkeep`
- Satir sayisi: 1
- Boyut: 2 bayt
- Satir araligi incelemesi:
  - L1-L1: Bos/yalnizca bosluk

### 21. `backend/cache_manager.py`
- Satir sayisi: 281
- Boyut: 9409 bayt
- Python ozeti: import=7, sinif=3, fonksiyon=25, flask_route=0
- Siniflar:
  - L18: LRUCache
  - L125: GraphCache
  - L204: POICache
- Fonksiyonlar:
  - L33: __init__
  - L44: get
  - L67: put
  - L89: remove
  - L99: clear
  - L107: size
  - L111: stats
  - L135: __init__
  - L149: get
  - L164: put
  - L173: preload
  - L177: remove
  - L186: clear
  - L190: clear_all
  - L195: stats
  - L214: __init__
  - L219: _make_key
  - L226: get
  - L231: put
  - L236: remove
  - L241: clear
  - L245: stats
  - L256: get_graph_cache
  - L266: get_poi_cache
  - L276: get_all_cache_stats
- Ilk anlamli satir: """
- Son anlamli satir: }
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=__init__, get | siniflar=LRUCache
  - L61-L120: fonksiyonlar=put, remove, clear, size, stats
  - L121-L180: fonksiyonlar=__init__, get, put, preload, remove | siniflar=GraphCache
  - L181-L240: fonksiyonlar=clear, clear_all, stats, __init__, _make_key, get, put, remove | siniflar=POICache
  - L241-L281: fonksiyonlar=clear, stats, get_graph_cache, get_poi_cache, get_all_cache_stats

### 22. `backend/data/intent_templates_tr.json`
- Satir sayisi: 38
- Boyut: 961 bayt
- Ilk anlamli satir: {
- Son anlamli satir: }
- Satir araligi incelemesi:
  - L1-L38: veri satirlari/json icerigi

### 23. `backend/data/place_names.json`
- Satir sayisi: 1787
- Boyut: 33608 bayt
- Ilk anlamli satir: [
- Son anlamli satir: ]
- Satir araligi incelemesi:
  - L1-L60: veri satirlari/json icerigi
  - L61-L120: veri satirlari/json icerigi
  - L121-L180: veri satirlari/json icerigi
  - L181-L240: veri satirlari/json icerigi
  - L241-L300: veri satirlari/json icerigi
  - L301-L360: veri satirlari/json icerigi
  - L361-L420: veri satirlari/json icerigi
  - L421-L480: veri satirlari/json icerigi
  - L481-L540: veri satirlari/json icerigi
  - L541-L600: veri satirlari/json icerigi
  - L601-L660: veri satirlari/json icerigi
  - L661-L720: veri satirlari/json icerigi
  - L721-L780: veri satirlari/json icerigi
  - L781-L840: veri satirlari/json icerigi
  - L841-L900: veri satirlari/json icerigi
  - L901-L960: veri satirlari/json icerigi
  - L961-L1020: veri satirlari/json icerigi
  - L1021-L1080: veri satirlari/json icerigi
  - L1081-L1140: veri satirlari/json icerigi
  - L1141-L1200: veri satirlari/json icerigi
  - L1201-L1260: veri satirlari/json icerigi
  - L1261-L1320: veri satirlari/json icerigi
  - L1321-L1380: veri satirlari/json icerigi
  - L1381-L1440: veri satirlari/json icerigi
  - L1441-L1500: veri satirlari/json icerigi
  - L1501-L1560: veri satirlari/json icerigi
  - L1561-L1620: veri satirlari/json icerigi
  - L1621-L1680: veri satirlari/json icerigi
  - L1681-L1740: veri satirlari/json icerigi
  - L1741-L1787: veri satirlari/json icerigi

### 24. `backend/districts_db.py`
- Satir sayisi: 231
- Boyut: 16723 bayt
- Python ozeti: import=2, sinif=0, fonksiyon=5, flask_route=0
- Fonksiyonlar:
  - L99: create_database
  - L138: search_districts
  - L170: get_all_provinces
  - L182: get_districts_by_province
  - L198: print_stats
- Ilk anlamli satir: """
- Son anlamli satir: print(f"  - {r['full_name']}")
- Satir araligi incelemesi:
  - L1-L60: yardimci/degisken/akis kodu
  - L61-L120: fonksiyonlar=create_database
  - L121-L180: fonksiyonlar=search_districts, get_all_provinces
  - L181-L231: fonksiyonlar=get_districts_by_province, print_stats

### 25. `backend/geocoder.py`
- Satir sayisi: 631
- Boyut: 18736 bayt
- Python ozeti: import=7, sinif=3, fonksiyon=11, flask_route=0
- Siniflar:
  - L43: LocationNotFoundError
  - L48: NetworkError
  - L53: InvalidQueryError
- Fonksiyonlar:
  - L62: _init_cache_db
  - L109: purge_old_geocodes
  - L141: _query_hash
  - L146: _lat_lon_key
  - L151: _get_from_cache
  - L200: _save_to_cache
  - L255: _rate_limit
  - L276: geocode
  - L428: geocode_suggest
  - L485: reverse_geocode
  - L611: geocode_batch
- Ilk anlamli satir: """
- Son anlamli satir: return results
- Satir araligi incelemesi:
  - L1-L60: siniflar=LocationNotFoundError, NetworkError, InvalidQueryError
  - L61-L120: fonksiyonlar=_init_cache_db, purge_old_geocodes
  - L121-L180: fonksiyonlar=_query_hash, _lat_lon_key, _get_from_cache
  - L181-L240: fonksiyonlar=_save_to_cache
  - L241-L300: fonksiyonlar=_rate_limit, geocode
  - L301-L360: yardimci/degisken/akis kodu
  - L361-L420: yardimci/degisken/akis kodu
  - L421-L480: fonksiyonlar=geocode_suggest
  - L481-L540: fonksiyonlar=reverse_geocode
  - L541-L600: yardimci/degisken/akis kodu
  - L601-L631: fonksiyonlar=geocode_batch

### 26. `backend/graph_manager.py`
- Satir sayisi: 494
- Boyut: 17226 bayt
- Python ozeti: import=18, sinif=0, fonksiyon=16, flask_route=0
- Fonksiyonlar:
  - L33: _init_poi_db
  - L51: _build_tags_cache_suffix
  - L64: _cache_path
  - L70: get_graph
  - L90: get_graph_for_points
  - L145: find_nearest_node
  - L179: _rows_to_poi_list
  - L217: _resolve_search_center
  - L239: _fetch_pois_with_fallback
  - L283: search_pois_by_tags
  - L343: search_pois
  - L366: search_poi_by_name_fuzzy
  - L446: preload_popular_regions
  - L454: _preload_region
  - L483: is_preloaded
  - L490: get_preloaded_graph
- Ilk anlamli satir: """
- Son anlamli satir: return _preloaded_graphs.get(place_name)
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=_init_poi_db, _build_tags_cache_suffix
  - L61-L120: fonksiyonlar=_cache_path, get_graph, get_graph_for_points
  - L121-L180: fonksiyonlar=find_nearest_node, _rows_to_poi_list
  - L181-L240: fonksiyonlar=_resolve_search_center, _fetch_pois_with_fallback
  - L241-L300: fonksiyonlar=search_pois_by_tags
  - L301-L360: fonksiyonlar=search_pois
  - L361-L420: fonksiyonlar=search_poi_by_name_fuzzy
  - L421-L480: fonksiyonlar=preload_popular_regions, _preload_region
  - L481-L494: fonksiyonlar=is_preloaded, get_preloaded_graph

### 27. `backend/local_places.py`
- Satir sayisi: 231
- Boyut: 9309 bayt
- Python ozeti: import=2, sinif=0, fonksiyon=5, flask_route=0
- Fonksiyonlar:
  - L67: _seed_if_empty
  - L90: lookup
  - L138: save_dynamic_place
  - L181: get_dynamic_place_names
  - L205: get_all_local_place_names
- Ilk anlamli satir: """
- Son anlamli satir: return [row["name"] for row in rows if row["name"]]
- Satir araligi incelemesi:
  - L1-L60: yardimci/degisken/akis kodu
  - L61-L120: fonksiyonlar=_seed_if_empty, lookup
  - L121-L180: fonksiyonlar=save_dynamic_place
  - L181-L231: fonksiyonlar=get_dynamic_place_names, get_all_local_place_names

### 28. `backend/location_storage.py`
- Satir sayisi: 272
- Boyut: 8051 bayt
- Python ozeti: import=6, sinif=0, fonksiyon=11, flask_route=0
- Fonksiyonlar:
  - L22: _row_to_location
  - L38: _migrate_from_json_if_needed
  - L85: save_location
  - L127: toggle_location_favorite
  - L151: _get_location_by_id
  - L161: get_all_locations
  - L188: get_locations_count
  - L199: increment_usage
  - L215: update_location
  - L242: delete_location
  - L258: search_locations_by_name
- Ilk anlamli satir: """
- Son anlamli satir: return [_row_to_location(row) for row in rows]
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=_row_to_location, _migrate_from_json_if_needed
  - L61-L120: fonksiyonlar=save_location
  - L121-L180: fonksiyonlar=toggle_location_favorite, _get_location_by_id, get_all_locations
  - L181-L240: fonksiyonlar=get_locations_count, increment_usage, update_location
  - L241-L272: fonksiyonlar=delete_location, search_locations_by_name

### 29. `backend/logging_config.py`
- Satir sayisi: 524
- Boyut: 16905 bayt
- Python ozeti: import=17, sinif=4, fonksiyon=23, flask_route=0
- Siniflar:
  - L35: RequestContext
  - L77: JSONFormatter
  - L152: ColoredFormatter
  - L287: FlaskLoggingMiddleware
- Fonksiyonlar:
  - L39: set_request_id
  - L44: set_user_id
  - L49: set_client_ip
  - L54: get_context
  - L66: clear
  - L97: __init__
  - L101: format
  - L168: format
  - L193: _setup_logging
  - L239: get_logger
  - L297: __init__
  - L301: __call__
  - L331: custom_start_response
  - L360: init_flask_logging
  - L384: log_execution
  - L393: calculate_route
  - L404: decorator
  - L406: wrapper
  - L444: log_slow_calls
  - L454: fetch_from_api
  - L461: decorator
  - L463: wrapper
  - L485: log_request_data
- Ilk anlamli satir: """
- Son anlamli satir: default_logger = get_logger('openrouteplanner')
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=set_request_id, set_user_id, set_client_ip, get_context | siniflar=RequestContext
  - L61-L120: fonksiyonlar=clear, __init__, format | siniflar=JSONFormatter
  - L121-L180: fonksiyonlar=format | siniflar=ColoredFormatter
  - L181-L240: fonksiyonlar=_setup_logging, get_logger
  - L241-L300: fonksiyonlar=__init__ | siniflar=FlaskLoggingMiddleware
  - L301-L360: fonksiyonlar=__call__, custom_start_response, init_flask_logging
  - L361-L420: fonksiyonlar=log_execution, calculate_route, decorator, wrapper
  - L421-L480: fonksiyonlar=log_slow_calls, fetch_from_api, decorator, wrapper
  - L481-L524: fonksiyonlar=log_request_data

### 30. `backend/models.py`
- Satir sayisi: 482
- Boyut: 14799 bayt
- Python ozeti: import=4, sinif=45, fonksiyon=1, flask_route=0
- Siniflar:
  - L18: RouteType
  - L25: IconType
  - L37: WeatherCategory
  - L52: Coordinate
  - L67: PointWithName
  - L82: PaginationParams
  - L93: RouteCalculateRequest
  - L125: RouteSegment
  - L132: RouteData
  - L144: RouteResponse
  - L156: SaveRouteRequest
  - L168: UpdateRouteRequest
  - L176: RouteListItem
  - L195: SaveLocationRequest
  - L204: UpdateLocationRequest
  - L213: LocationItem
  - L231: GeocodeRequest
  - L236: ReverseGeocodeRequest
  - L242: GeocodeSuggestion
  - L250: GeocodeResponse
  - L260: GeocodeSuggestResponse
  - L270: WeatherRequest
  - L276: WeatherForecastRequest
  - L281: WeatherAlert
  - L288: CurrentWeather
  - L302: HourlyWeatherItem
  - L313: WeatherResponse
  - L320: RouteWeatherCheckRequest
  - L325: RouteWeatherItem
  - L338: POISearchRequest
  - L344: POIItem
  - L359: NLPQueryRequest
  - L364: ExtractedEntity
  - L371: NLPQueryResponse
  - L383: TimelineEvent
  - L394: TimelineRequest
  - L401: TimelineResponse
  - L412: PaginationMeta
  - L422: PaginatedResponse
  - L433: HealthCheckStatus
  - L440: ServiceStatus
  - L447: HealthCheckResponse
  - L459: ErrorResponse
  - L471: ValidationErrorDetail
  - L478: ValidationErrorResponse
- Fonksiyonlar:
  - L101: validate_unique_points
- Ilk anlamli satir: """
- Son anlamli satir: errors: List[ValidationErrorDetail]
- Satir araligi incelemesi:
  - L1-L60: siniflar=RouteType, IconType, WeatherCategory, Coordinate
  - L61-L120: fonksiyonlar=validate_unique_points | siniflar=PointWithName, PaginationParams, RouteCalculateRequest
  - L121-L180: siniflar=RouteSegment, RouteData, RouteResponse, SaveRouteRequest, UpdateRouteRequest, RouteListItem
  - L181-L240: siniflar=SaveLocationRequest, UpdateLocationRequest, LocationItem, GeocodeRequest, ReverseGeocodeRequest
  - L241-L300: siniflar=GeocodeSuggestion, GeocodeResponse, GeocodeSuggestResponse, WeatherRequest, WeatherForecastRequest, WeatherAlert, CurrentWeather
  - L301-L360: siniflar=HourlyWeatherItem, WeatherResponse, RouteWeatherCheckRequest, RouteWeatherItem, POISearchRequest, POIItem, NLPQueryRequest
  - L361-L420: siniflar=ExtractedEntity, NLPQueryResponse, TimelineEvent, TimelineRequest, TimelineResponse, PaginationMeta
  - L421-L480: siniflar=PaginatedResponse, HealthCheckStatus, ServiceStatus, HealthCheckResponse, ErrorResponse, ValidationErrorDetail, ValidationErrorResponse
  - L481-L482: yardimci/degisken/akis kodu

### 31. `backend/models/.gitkeep`
- Satir sayisi: 2
- Boyut: 113 bayt
- Ilk anlamli satir: # Bu klasör yapay zeka modellerini barındırır.
- Son anlamli satir: # Model dosyaları .gitignore kuralları ile takip edilmez.
- Satir araligi incelemesi:
  - L1-L2: genel icerik

### 32. `backend/models/bert-base-turkish-uncased/.gitkeep`
- Satir sayisi: 1
- Boyut: 199 bayt
- Ilk anlamli satir: Bu dosya, backend/models/bert-base-turkish-uncased klasörünün Git üzerinde takip edilmesini sağlar, ancak indirilmiş ...
- Son anlamli satir: Bu dosya, backend/models/bert-base-turkish-uncased klasörünün Git üzerinde takip edilmesini sağlar, ancak indirilmiş ...
- Satir araligi incelemesi:
  - L1-L1: genel icerik

### 33. `backend/nlp_concept_resolver.py`
- Satir sayisi: 326
- Boyut: 9433 bayt
- Python ozeti: import=6, sinif=1, fonksiyon=15, flask_route=0
- Siniflar:
  - L21: PoiResolution
- Fonksiyonlar:
  - L57: normalize_text
  - L65: tr_fold
  - L69: singularize_token
  - L77: strip_case_suffix
  - L97: morph_candidates
  - L105: push
  - L127: _build_index
  - L157: _dict_lookup
  - L164: resolve_poi_concept
  - L234: build_poi_ngrams
  - L246: resolve_poi_from_tokens
  - L265: extract_candidates
  - L283: normalize_poi_concept
  - L289: map_concept_to_osm_queries
  - L307: resolve_query
- Ilk anlamli satir: """
- Son anlamli satir: }
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=normalize_text | siniflar=PoiResolution
  - L61-L120: fonksiyonlar=tr_fold, singularize_token, strip_case_suffix, morph_candidates, push
  - L121-L180: fonksiyonlar=_build_index, _dict_lookup, resolve_poi_concept
  - L181-L240: fonksiyonlar=build_poi_ngrams
  - L241-L300: fonksiyonlar=resolve_poi_from_tokens, extract_candidates, normalize_poi_concept, map_concept_to_osm_queries
  - L301-L326: fonksiyonlar=resolve_query

### 34. `backend/nlp_engine.py`
- Satir sayisi: 487
- Boyut: 16451 bayt
- Python ozeti: import=10, sinif=0, fonksiyon=6, flask_route=0
- Fonksiyonlar:
  - L25: get_all_locations
  - L144: _clean_text
  - L162: _extract_place_names
  - L199: _is_turkish_location
  - L232: parse_query
  - L446: test_parser
- Ilk anlamli satir: """
- Son anlamli satir: test_parser()
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=get_all_locations
  - L61-L120: yardimci/degisken/akis kodu
  - L121-L180: fonksiyonlar=_clean_text, _extract_place_names
  - L181-L240: fonksiyonlar=_is_turkish_location, parse_query
  - L241-L300: yardimci/degisken/akis kodu
  - L301-L360: yardimci/degisken/akis kodu
  - L361-L420: yardimci/degisken/akis kodu
  - L421-L480: fonksiyonlar=test_parser
  - L481-L487: yardimci/degisken/akis kodu

### 35. `backend/openrouter_service.py`
- Satir sayisi: 582
- Boyut: 17523 bayt
- Python ozeti: import=6, sinif=0, fonksiyon=22, flask_route=0
- Fonksiyonlar:
  - L17: _load_dotenv_if_present
  - L61: _normalize_model_ref
  - L81: _parse_model_list
  - L89: _append
  - L113: _env_float
  - L123: _base_url
  - L128: _api_key
  - L132: _default_model
  - L139: _fallback_models
  - L144: _candidate_models
  - L153: _timeout_sec
  - L157: is_openrouter_configured
  - L161: openrouter_status
  - L171: _is_non_text_model
  - L203: openrouter_list_text_models
  - L252: _extract_text
  - L277: _is_fallback_retryable_error
  - L305: openrouter_chat_completion
  - L384: openrouter_chat_completion_with_fallback
  - L418: _extract_delta_text
  - L442: openrouter_chat_completion_stream
  - L541: openrouter_chat_completion_stream_with_fallback
- Ilk anlamli satir: """
- Son anlamli satir: raise RuntimeError("Tum modeller basarisiz: " + " | ".join(errors))
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=_load_dotenv_if_present
  - L61-L120: fonksiyonlar=_normalize_model_ref, _parse_model_list, _append, _env_float
  - L121-L180: fonksiyonlar=_base_url, _api_key, _default_model, _fallback_models, _candidate_models, _timeout_sec, is_openrouter_configured, openrouter_status
  - L181-L240: fonksiyonlar=openrouter_list_text_models
  - L241-L300: fonksiyonlar=_extract_text, _is_fallback_retryable_error
  - L301-L360: fonksiyonlar=openrouter_chat_completion
  - L361-L420: fonksiyonlar=openrouter_chat_completion_with_fallback, _extract_delta_text
  - L421-L480: fonksiyonlar=openrouter_chat_completion_stream
  - L481-L540: yardimci/degisken/akis kodu
  - L541-L582: fonksiyonlar=openrouter_chat_completion_stream_with_fallback

### 36. `backend/osm_poi_dictionary.py`
- Satir sayisi: 242
- Boyut: 10110 bayt
- Python ozeti: import=0, sinif=0, fonksiyon=2, flask_route=0
- Fonksiyonlar:
  - L222: get_osm_tags_for_keyword
  - L233: get_all_supported_keywords
- Ilk anlamli satir: """
- Son anlamli satir: print(f"metro -> {get_osm_tags_for_keyword('metro')}")
- Satir araligi incelemesi:
  - L1-L60: yardimci/degisken/akis kodu
  - L61-L120: yardimci/degisken/akis kodu
  - L121-L180: yardimci/degisken/akis kodu
  - L181-L240: fonksiyonlar=get_osm_tags_for_keyword, get_all_supported_keywords
  - L241-L242: yardimci/degisken/akis kodu

### 37. `backend/response_utils.py`
- Satir sayisi: 632
- Boyut: 18636 bayt
- Python ozeti: import=8, sinif=1, fonksiyon=21, flask_route=3
- Siniflar:
  - L121: ErrorResponse
- Fonksiyonlar:
  - L11: get_routes
  - L16: get_route
  - L32: success_response
  - L73: created_response
  - L104: no_content_response
  - L151: error_response
  - L192: validation_error
  - L221: not_found_response
  - L247: internal_error_response
  - L270: service_unavailable_response
  - L294: paginated_response
  - L351: conditional_response
  - L380: health_check_response
  - L415: options_response
  - L444: batch_response
  - L487: get_pagination_params
  - L530: extract_request_data
  - L588: handle_exceptions
  - L602: calculate_route
  - L609: decorator
  - L611: wrapper
- Flask route satirlari:
  - L10: @app.route('/api/routes')
  - L15: @app.route('/api/routes/<id>')
  - L600: @app.route('/api/route/calculate')
- Ilk anlamli satir: """
- Son anlamli satir: return decorator
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=get_routes, get_route, success_response | route_adedi=2
  - L61-L120: fonksiyonlar=created_response, no_content_response
  - L121-L180: fonksiyonlar=error_response | siniflar=ErrorResponse
  - L181-L240: fonksiyonlar=validation_error, not_found_response
  - L241-L300: fonksiyonlar=internal_error_response, service_unavailable_response, paginated_response
  - L301-L360: fonksiyonlar=conditional_response
  - L361-L420: fonksiyonlar=health_check_response, options_response
  - L421-L480: fonksiyonlar=batch_response
  - L481-L540: fonksiyonlar=get_pagination_params, extract_request_data
  - L541-L600: fonksiyonlar=handle_exceptions | route_adedi=1
  - L601-L632: fonksiyonlar=calculate_route, decorator, wrapper

### 38. `backend/route_config.py`
- Satir sayisi: 156
- Boyut: 6608 bayt
- Python ozeti: import=1, sinif=0, fonksiyon=0, flask_route=0
- Ilk anlamli satir: """
- Son anlamli satir: }
- Satir araligi incelemesi:
  - L1-L60: yardimci/degisken/akis kodu
  - L61-L120: yardimci/degisken/akis kodu
  - L121-L156: yardimci/degisken/akis kodu

### 39. `backend/route_engine.py`
- Satir sayisi: 51
- Boyut: 1730 bayt
- Python ozeti: import=2, sinif=0, fonksiyon=3, flask_route=0
- Fonksiyonlar:
  - L13: get_overlap_threshold
  - L29: count_edge_overlap
  - L38: normalize_edge
- Ilk anlamli satir: # Compatibility wrapper for route_engine
- Son anlamli satir: return intersection / max(len(set1), len(set2))
- Satir araligi incelemesi:
  - L1-L51: fonksiyonlar=get_overlap_threshold, count_edge_overlap, normalize_edge

### 40. `backend/route_engine_impl.py`
- Satir sayisi: 1243
- Boyut: 49567 bayt
- Python ozeti: import=9, sinif=1, fonksiyon=28, flask_route=0
- Siniflar:
  - L355: RouteTelemetry
- Fonksiyonlar:
  - L25: shortest_path
  - L45: _node_coord
  - L51: _extract_edge_coords
  - L80: sqdist
  - L91: nodes_to_coords
  - L114: solve_tsp
  - L184: build_full_route
  - L213: calculate_route_stats
  - L251: generate_google_maps_link
  - L269: path_to_edges
  - L284: count_edge_overlap
  - L300: normalize_edge
  - L317: dynamic_overlap_threshold
  - L336: get_max_candidates
  - L360: __init__
  - L370: finish
  - L394: check_alternative_potential
  - L437: find_disjoint_paths
  - L493: dynamic_overlap_threshold_connectivity
  - L547: apply_penalty_to_graph
  - L597: find_routes_with_penalty
  - L662: get_fallback_routes
  - L728: get_body_edges
  - L741: find_via_node_routes
  - L829: min_distance_to_route
  - L901: find_alternative_routes
  - L1137: build_alternative_routes
  - L1174: build_all_alternative_routes_batch
- Ilk anlamli satir: """
- Son anlamli satir: return results
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=shortest_path, _node_coord, _extract_edge_coords
  - L61-L120: fonksiyonlar=sqdist, nodes_to_coords, solve_tsp
  - L121-L180: yardimci/degisken/akis kodu
  - L181-L240: fonksiyonlar=build_full_route, calculate_route_stats
  - L241-L300: fonksiyonlar=generate_google_maps_link, path_to_edges, count_edge_overlap, normalize_edge
  - L301-L360: fonksiyonlar=dynamic_overlap_threshold, get_max_candidates, __init__ | siniflar=RouteTelemetry
  - L361-L420: fonksiyonlar=finish, check_alternative_potential
  - L421-L480: fonksiyonlar=find_disjoint_paths
  - L481-L540: fonksiyonlar=dynamic_overlap_threshold_connectivity
  - L541-L600: fonksiyonlar=apply_penalty_to_graph, find_routes_with_penalty
  - L601-L660: yardimci/degisken/akis kodu
  - L661-L720: fonksiyonlar=get_fallback_routes
  - L721-L780: fonksiyonlar=get_body_edges, find_via_node_routes
  - L781-L840: fonksiyonlar=min_distance_to_route
  - L841-L900: yardimci/degisken/akis kodu
  - L901-L960: fonksiyonlar=find_alternative_routes
  - L961-L1020: yardimci/degisken/akis kodu
  - L1021-L1080: yardimci/degisken/akis kodu
  - L1081-L1140: fonksiyonlar=build_alternative_routes
  - L1141-L1200: fonksiyonlar=build_all_alternative_routes_batch
  - L1201-L1243: yardimci/degisken/akis kodu

### 41. `backend/route_storage.py`
- Satir sayisi: 399
- Boyut: 12121 bayt
- Python ozeti: import=6, sinif=0, fonksiyon=13, flask_route=0
- Fonksiyonlar:
  - L21: _row_to_route
  - L55: _migrate_from_json_if_needed
  - L106: simplify_coords
  - L116: save_route
  - L178: _get_route_by_id
  - L192: get_route
  - L219: get_all_routes
  - L252: get_routes_count
  - L263: update_route
  - L303: delete_route
  - L319: toggle_favorite
  - L344: search_routes
  - L365: get_statistics
- Ilk anlamli satir: """
- Son anlamli satir: }
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=_row_to_route, _migrate_from_json_if_needed
  - L61-L120: fonksiyonlar=simplify_coords, save_route
  - L121-L180: fonksiyonlar=_get_route_by_id
  - L181-L240: fonksiyonlar=get_route, get_all_routes
  - L241-L300: fonksiyonlar=get_routes_count, update_route
  - L301-L360: fonksiyonlar=delete_route, toggle_favorite, search_routes
  - L361-L399: fonksiyonlar=get_statistics

### 42. `backend/spatial_index.py`
- Satir sayisi: 499
- Boyut: 15418 bayt
- Python ozeti: import=4, sinif=4, fonksiyon=28, flask_route=0
- Siniflar:
  - L15: BoundingBox
  - L63: POIItem
  - L111: SpatialIndex
  - L303: POISpatialCache
- Fonksiyonlar:
  - L30: contains
  - L34: intersects
  - L43: expand
  - L58: to_tuple
  - L76: __init__
  - L93: bounds
  - L97: distance_to
  - L124: __init__
  - L134: _get_cell_key
  - L138: _get_cells_for_bbox
  - L149: insert
  - L163: search_bbox
  - L194: search_radius
  - L229: search_nearest
  - L262: get
  - L266: remove
  - L285: clear
  - L290: stats
  - L326: __init__
  - L331: insert
  - L364: search_bbox
  - L388: search_radius
  - L419: search_nearest
  - L446: get
  - L459: remove
  - L472: clear
  - L477: stats
  - L492: get_poi_spatial_cache
- Ilk anlamli satir: """
- Son anlamli satir: return _poi_spatial_cache
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=contains, intersects, expand, to_tuple | siniflar=BoundingBox
  - L61-L120: fonksiyonlar=__init__, bounds, distance_to | siniflar=POIItem, SpatialIndex
  - L121-L180: fonksiyonlar=__init__, _get_cell_key, _get_cells_for_bbox, insert, search_bbox
  - L181-L240: fonksiyonlar=search_radius, search_nearest
  - L241-L300: fonksiyonlar=get, remove, clear, stats
  - L301-L360: fonksiyonlar=__init__, insert | siniflar=POISpatialCache
  - L361-L420: fonksiyonlar=search_bbox, search_radius, search_nearest
  - L421-L480: fonksiyonlar=get, remove, clear, stats
  - L481-L499: fonksiyonlar=get_poi_spatial_cache

### 43. `backend/storage_db.py`
- Satir sayisi: 293
- Boyut: 9785 bayt
- Python ozeti: import=5, sinif=1, fonksiyon=19, flask_route=0
- Siniflar:
  - L31: _PooledConnection
- Fonksiyonlar:
  - L38: __init__
  - L43: __getattr__
  - L49: cursor
  - L55: execute
  - L61: executemany
  - L67: commit
  - L73: rollback
  - L79: close
  - L94: row_factory
  - L98: row_factory
  - L101: __enter__
  - L104: __exit__
  - L108: _create_connection
  - L123: get_connection
  - L164: close_connection
  - L177: close_all_connections
  - L187: init_schema
  - L262: ensure_db
  - L281: run_sqlite_maintenance
- Ilk anlamli satir: """
- Son anlamli satir: conn.close()
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=__init__, __getattr__, cursor, execute | siniflar=_PooledConnection
  - L61-L120: fonksiyonlar=executemany, commit, rollback, close, row_factory, row_factory, __enter__, __exit__
  - L121-L180: fonksiyonlar=get_connection, close_connection, close_all_connections
  - L181-L240: fonksiyonlar=init_schema
  - L241-L293: fonksiyonlar=ensure_db, run_sqlite_maintenance

### 44. `backend/tag_grounder.py`
- Satir sayisi: 311
- Boyut: 11912 bayt
- Python ozeti: import=7, sinif=2, fonksiyon=9, flask_route=0
- Siniflar:
  - L51: TagProfile
  - L84: TagGrounder
- Fonksiyonlar:
  - L60: __init__
  - L94: __init__
  - L108: ground
  - L178: _get_area_profiles
  - L207: _fetch_overpass
  - L227: _build_profiles
  - L265: _compute_embeddings
  - L282: _cosine_sim
  - L300: get_tag_grounder
- Ilk anlamli satir: """
- Son anlamli satir: return _grounder_instance
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=__init__ | siniflar=TagProfile
  - L61-L120: fonksiyonlar=__init__, ground | siniflar=TagGrounder
  - L121-L180: fonksiyonlar=_get_area_profiles
  - L181-L240: fonksiyonlar=_fetch_overpass, _build_profiles
  - L241-L300: fonksiyonlar=_compute_embeddings, _cosine_sim, get_tag_grounder
  - L301-L311: yardimci/degisken/akis kodu

### 45. `backend/test_route_steps.py`
- Satir sayisi: 100
- Boyut: 4034 bayt
- Python ozeti: import=3, sinif=0, fonksiyon=4, flask_route=0
- Fonksiyonlar:
  - L6: make_test_graph
  - L19: test_get_route_steps_basic
  - L54: test_missing_street_name
  - L77: test_roundabout_detection
- Ilk anlamli satir: import json
- Son anlamli satir: assert any((s.get('turn_type') == 'roundabout') or ('kavşa' in s.get('instruction', '').lower()) for s in steps), "Ro...
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=make_test_graph, test_get_route_steps_basic, test_missing_street_name
  - L61-L100: fonksiyonlar=test_roundabout_detection

### 46. `backend/test_weather_service.py`
- Satir sayisi: 621
- Boyut: 17789 bayt
- Python ozeti: import=9, sinif=0, fonksiyon=16, flask_route=0
- Fonksiyonlar:
  - L33: print_test_header
  - L40: print_result
  - L51: test_validate_coordinates
  - L96: test_validate_hours
  - L133: test_parse_weather_code
  - L185: test_get_weather_emoji
  - L209: test_build_cache_key
  - L242: test_format_temperature
  - L272: test_weather_alerts
  - L313: test_activity_suggestions
  - L350: test_weather_service_import
  - L368: test_service_status
  - L403: test_cache_operations
  - L454: test_openmeteo_api_call
  - L498: test_current_weather_live
  - L545: run_all_tests
- Ilk anlamli satir: """
- Son anlamli satir: sys.exit(0 if success else 1)
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=print_test_header, print_result, test_validate_coordinates
  - L61-L120: fonksiyonlar=test_validate_hours
  - L121-L180: fonksiyonlar=test_parse_weather_code
  - L181-L240: fonksiyonlar=test_get_weather_emoji, test_build_cache_key
  - L241-L300: fonksiyonlar=test_format_temperature, test_weather_alerts
  - L301-L360: fonksiyonlar=test_activity_suggestions, test_weather_service_import
  - L361-L420: fonksiyonlar=test_service_status, test_cache_operations
  - L421-L480: fonksiyonlar=test_openmeteo_api_call
  - L481-L540: fonksiyonlar=test_current_weather_live
  - L541-L600: fonksiyonlar=run_all_tests
  - L601-L621: yardimci/degisken/akis kodu

### 47. `backend/time_planner.py`
- Satir sayisi: 473
- Boyut: 17023 bayt
- Python ozeti: import=6, sinif=0, fonksiyon=7, flask_route=0
- Fonksiyonlar:
  - L19: calculate_travel_time
  - L44: create_timeline
  - L221: find_smart_departure_time
  - L275: generate_route_weather_summary
  - L347: format_duration
  - L365: check_time_conflicts
  - L412: optimize_schedule
- Ilk anlamli satir: """
- Son anlamli satir: }
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=calculate_travel_time, create_timeline
  - L61-L120: yardimci/degisken/akis kodu
  - L121-L180: yardimci/degisken/akis kodu
  - L181-L240: fonksiyonlar=find_smart_departure_time
  - L241-L300: fonksiyonlar=generate_route_weather_summary
  - L301-L360: fonksiyonlar=format_duration
  - L361-L420: fonksiyonlar=check_time_conflicts, optimize_schedule
  - L421-L473: yardimci/degisken/akis kodu

### 48. `backend/turkey_places.py`
- Satir sayisi: 115
- Boyut: 14533 bayt
- Python ozeti: import=0, sinif=0, fonksiyon=1, flask_route=0
- Fonksiyonlar:
  - L88: get_all_turkey_places
- Ilk anlamli satir: """
- Son anlamli satir: print(f"  - {place}")
- Satir araligi incelemesi:
  - L1-L60: yardimci/degisken/akis kodu
  - L61-L115: fonksiyonlar=get_all_turkey_places

### 49. `backend/weather_service.py`
- Satir sayisi: 1538
- Boyut: 53974 bayt
- Python ozeti: import=6, sinif=5, fonksiyon=23, flask_route=0
- Siniflar:
  - L82: WeatherServiceError
  - L87: InvalidCoordinatesError
  - L92: NetworkError
  - L97: RateLimitError
  - L102: ParseError
- Fonksiyonlar:
  - L111: _get_from_cache
  - L160: _save_to_cache
  - L199: _is_cache_valid
  - L232: clear_cache
  - L265: get_cache_stats
  - L312: _fetch_from_openmeteo
  - L422: _sleep_with_backoff
  - L438: _build_url_current
  - L476: _build_url_hourly
  - L521: _parse_current_weather
  - L601: _parse_hourly_forecast
  - L658: get_current_weather
  - L773: get_hourly_forecast
  - L903: get_weather_at_time
  - L978: _parse_context_time
  - L997: _precip_level
  - L1007: _build_critical_advice
  - L1031: get_two_hour_risk_window
  - L1130: check_route_weather
  - L1308: _evaluate_overall_conditions
  - L1384: get_multiple_locations_weather
  - L1444: get_service_status
  - L1502: health_check
- Ilk anlamli satir: """
- Son anlamli satir: return False
- Satir araligi incelemesi:
  - L1-L60: yardimci/degisken/akis kodu
  - L61-L120: fonksiyonlar=_get_from_cache | siniflar=WeatherServiceError, InvalidCoordinatesError, NetworkError, RateLimitError, ParseError
  - L121-L180: fonksiyonlar=_save_to_cache
  - L181-L240: fonksiyonlar=_is_cache_valid, clear_cache
  - L241-L300: fonksiyonlar=get_cache_stats
  - L301-L360: fonksiyonlar=_fetch_from_openmeteo
  - L361-L420: yardimci/degisken/akis kodu
  - L421-L480: fonksiyonlar=_sleep_with_backoff, _build_url_current, _build_url_hourly
  - L481-L540: fonksiyonlar=_parse_current_weather
  - L541-L600: yardimci/degisken/akis kodu
  - L601-L660: fonksiyonlar=_parse_hourly_forecast, get_current_weather
  - L661-L720: yardimci/degisken/akis kodu
  - L721-L780: fonksiyonlar=get_hourly_forecast
  - L781-L840: yardimci/degisken/akis kodu
  - L841-L900: yardimci/degisken/akis kodu
  - L901-L960: fonksiyonlar=get_weather_at_time
  - L961-L1020: fonksiyonlar=_parse_context_time, _precip_level, _build_critical_advice
  - L1021-L1080: fonksiyonlar=get_two_hour_risk_window
  - L1081-L1140: fonksiyonlar=check_route_weather
  - L1141-L1200: yardimci/degisken/akis kodu
  - L1201-L1260: yardimci/degisken/akis kodu
  - L1261-L1320: fonksiyonlar=_evaluate_overall_conditions
  - L1321-L1380: yardimci/degisken/akis kodu
  - L1381-L1440: fonksiyonlar=get_multiple_locations_weather
  - L1441-L1500: fonksiyonlar=get_service_status
  - L1501-L1538: fonksiyonlar=health_check

### 50. `backend/weather_utils.py`
- Satir sayisi: 1255
- Boyut: 43304 bayt
- Python ozeti: import=3, sinif=0, fonksiyon=22, flask_route=0
- Fonksiyonlar:
  - L196: validate_coordinates
  - L229: validate_hours
  - L266: validate_temperature
  - L309: build_cache_key
  - L360: parse_cache_key
  - L407: parse_weather_code
  - L458: get_weather_emoji
  - L530: format_temperature
  - L572: celsius_to_fahrenheit
  - L599: fahrenheit_to_celsius
  - L625: calculate_heat_index
  - L687: calculate_wind_chill
  - L741: get_weather_alert
  - L779: get_activity_suggestion
  - L842: calculate_uv_index_risk
  - L913: summarize_weather_data
  - L958: compare_weather
  - L1015: get_weather_color_code
  - L1064: _extract_hhmm
  - L1085: _build_context_prefix
  - L1099: get_weather_advice
  - L1205: get_weather_background_class
- Ilk anlamli satir: """
- Son anlamli satir: return class_map.get(category, "weather-unknown")
- Satir araligi incelemesi:
  - L1-L60: yardimci/degisken/akis kodu
  - L61-L120: yardimci/degisken/akis kodu
  - L121-L180: yardimci/degisken/akis kodu
  - L181-L240: fonksiyonlar=validate_coordinates, validate_hours
  - L241-L300: fonksiyonlar=validate_temperature
  - L301-L360: fonksiyonlar=build_cache_key, parse_cache_key
  - L361-L420: fonksiyonlar=parse_weather_code
  - L421-L480: fonksiyonlar=get_weather_emoji
  - L481-L540: fonksiyonlar=format_temperature
  - L541-L600: fonksiyonlar=celsius_to_fahrenheit, fahrenheit_to_celsius
  - L601-L660: fonksiyonlar=calculate_heat_index
  - L661-L720: fonksiyonlar=calculate_wind_chill
  - L721-L780: fonksiyonlar=get_weather_alert, get_activity_suggestion
  - L781-L840: yardimci/degisken/akis kodu
  - L841-L900: fonksiyonlar=calculate_uv_index_risk
  - L901-L960: fonksiyonlar=summarize_weather_data, compare_weather
  - L961-L1020: fonksiyonlar=get_weather_color_code
  - L1021-L1080: fonksiyonlar=_extract_hhmm
  - L1081-L1140: fonksiyonlar=_build_context_prefix, get_weather_advice
  - L1141-L1200: yardimci/degisken/akis kodu
  - L1201-L1255: fonksiyonlar=get_weather_background_class | siniflar=adi, adi, tanimlanmistir, adini, adi

### 51. `cache/1d3db6ec60a0c9e5cc888ec7221ca829081df6eb.json`
- Satir sayisi: 1
- Boyut: 281604 bayt
- Ilk anlamli satir: {"version": 0.6, "generator": "Overpass API 0.7.62.10 2d4cfc48", "osm3s": {"timestamp_osm_base": "2026-03-03T13:15:03...
- Son anlamli satir: {"version": 0.6, "generator": "Overpass API 0.7.62.10 2d4cfc48", "osm3s": {"timestamp_osm_base": "2026-03-03T13:15:03...
- Satir araligi incelemesi:
  - L1-L1: veri satirlari/json icerigi

### 52. `cache/4dec26ed13c78ed3d949c85f256e7e8410bf5fde.json`
- Satir sayisi: 1
- Boyut: 27053 bayt
- Ilk anlamli satir: [{"place_id": 54429767, "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://osm.org/copyright", "osm...
- Son anlamli satir: [{"place_id": 54429767, "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://osm.org/copyright", "osm...
- Satir araligi incelemesi:
  - L1-L1: veri satirlari/json icerigi

### 53. `cache/60bb5807f595175e8027275cb66add0930daf349.json`
- Satir sayisi: 1
- Boyut: 741 bayt
- Ilk anlamli satir: {"version": 0.6, "generator": "Overpass API 0.7.62.10 2d4cfc48", "osm3s": {"timestamp_osm_base": "2026-03-03T09:20:25...
- Son anlamli satir: {"version": 0.6, "generator": "Overpass API 0.7.62.10 2d4cfc48", "osm3s": {"timestamp_osm_base": "2026-03-03T09:20:25...
- Satir araligi incelemesi:
  - L1-L1: veri satirlari/json icerigi

### 54. `cache/6a37e242888889dbb766a75692432c19b1cc1537.json`
- Satir sayisi: 1
- Boyut: 362070 bayt
- Ilk anlamli satir: {"version": 0.6, "generator": "Overpass API 0.7.62.10 2d4cfc48", "osm3s": {"timestamp_osm_base": "2026-03-03T13:17:05...
- Son anlamli satir: {"version": 0.6, "generator": "Overpass API 0.7.62.10 2d4cfc48", "osm3s": {"timestamp_osm_base": "2026-03-03T13:17:05...
- Satir araligi incelemesi:
  - L1-L1: veri satirlari/json icerigi

### 55. `cache/6b641f4d7b8528bfabda3e761c669498332b8bba.json`
- Satir sayisi: 1
- Boyut: 2513248 bayt
- Ilk anlamli satir: {"version": 0.6, "generator": "Overpass API 0.7.62.10 2d4cfc48", "osm3s": {"timestamp_osm_base": "2026-03-03T09:24:30...
- Son anlamli satir: {"version": 0.6, "generator": "Overpass API 0.7.62.10 2d4cfc48", "osm3s": {"timestamp_osm_base": "2026-03-03T09:24:30...
- Satir araligi incelemesi:
  - L1-L1: veri satirlari/json icerigi

### 56. `cache/6dc80c7496171e9c1e4ae6edcd2c878ea75f3816.json`
- Satir sayisi: 1
- Boyut: 39296 bayt
- Ilk anlamli satir: {"version": 0.6, "generator": "Overpass API 0.7.62.10 2d4cfc48", "osm3s": {"timestamp_osm_base": "2026-03-03T09:20:25...
- Son anlamli satir: {"version": 0.6, "generator": "Overpass API 0.7.62.10 2d4cfc48", "osm3s": {"timestamp_osm_base": "2026-03-03T09:20:25...
- Satir araligi incelemesi:
  - L1-L1: veri satirlari/json icerigi

### 57. `cache/cd2f48a680ba372cca90e45762f6f10124990102.json`
- Satir sayisi: 1
- Boyut: 54614 bayt
- Ilk anlamli satir: {"version": 0.6, "generator": "Overpass API 0.7.62.10 2d4cfc48", "osm3s": {"timestamp_osm_base": "2026-03-03T09:21:26...
- Son anlamli satir: {"version": 0.6, "generator": "Overpass API 0.7.62.10 2d4cfc48", "osm3s": {"timestamp_osm_base": "2026-03-03T09:21:26...
- Satir araligi incelemesi:
  - L1-L1: veri satirlari/json icerigi

### 58. `cache/fa0bac04c5ffebfa451bd7441eea95a5b44bb7d2.json`
- Satir sayisi: 1
- Boyut: 575057 bayt
- Ilk anlamli satir: {"version": 0.6, "generator": "Overpass API 0.7.62.10 2d4cfc48", "osm3s": {"timestamp_osm_base": "2026-03-03T09:27:28...
- Son anlamli satir: {"version": 0.6, "generator": "Overpass API 0.7.62.10 2d4cfc48", "osm3s": {"timestamp_osm_base": "2026-03-03T09:27:28...
- Satir araligi incelemesi:
  - L1-L1: veri satirlari/json icerigi

### 59. `claude-mem-10.5.2.tgz`
- Tip: Binary/asset dosya
- Boyut: 25312740 bayt
- Satir analizi: Uygulanmadi (binary)

### 60. `docs/DOSYA_YAPISI.md`
- Satir sayisi: 127
- Boyut: 4715 bayt
- Ilk anlamli satir: # 📁 OpenRoutePlanner — Dosya Yapısı Rehberi
- Son anlamli satir: | Harita indirme | `scripts/tools/download_istanbul.py` |
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # 📁 OpenRoutePlanner — Dosya Yapısı Rehberi; ## 📂 Genel Yapı; ## 📚 docs/ — Dokümantasyon; ### docs/osm/ — OSM ve API Rehberleri
  - L61-L120: basliklar -> ### docs/ogretici/ — Öğretici İçerikler; ### docs/referans/ — Referans; ## 🔧 scripts/ — Scriptler; ### scripts/fix/ — Fix Scriptleri
  - L121-L127: metin/rapor icerigi

### 61. `docs/README.md`
- Satir sayisi: 17
- Boyut: 690 bayt
- Ilk anlamli satir: # 📚 OpenRoutePlanner Dokümantasyonu
- Son anlamli satir: - **BERT temel kavramlar ve akis:** [ogretici/bert-temel-kavramlar-ve-calisma-prensibi.md](ogretici/bert-temel-kavram...
- Satir araligi incelemesi:
  - L1-L17: basliklar -> # 📚 OpenRoutePlanner Dokümantasyonu; ## Onerilen Baslangic Dokumani

### 62. `docs/diagrams/bert-engine-query-lab-20260310.png`
- Tip: Binary/asset dosya
- Boyut: 1161909 bayt
- Satir analizi: Uygulanmadi (binary)

### 63. `docs/diagrams/weather-service-flow.md`
- Satir sayisi: 610
- Boyut: 17616 bayt
- Ilk anlamli satir: # Hava Durumu Servisi - Akış Diyagramı
- Son anlamli satir: 9. **WMO Code Processing**: Kod dönüşüm pipeline'ı
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # Hava Durumu Servisi - Akış Diyagramı; ## Genel Akış Diyagramı
  - L61-L120: metin/rapor icerigi
  - L121-L180: basliklar -> ## Cache Mekanizması Detaylı Diyagramı; ## get_current_weather Fonksiyonu Detaylı Akışı
  - L181-L240: basliklar -> ## check_route_weather Fonksiyonu Akışı
  - L241-L300: basliklar -> ## Data Yapıları ve Format Dönüşümleri
  - L301-L360: basliklar -> ## Hata Yakalama Akışı
  - L361-L420: basliklar -> ## Component Mimari Diyagramı
  - L421-L480: basliklar -> ## Cache Lifecycle
  - L481-L540: basliklar -> ## Saatlik Forecast Akışı
  - L541-L600: basliklar -> ## WMO Code Processing Pipeline
  - L601-L610: metin/rapor icerigi

### 64. `docs/ogretici/bert-temel-kavramlar-ve-calisma-prensibi.md`
- Satir sayisi: 170
- Boyut: 5610 bayt
- Ilk anlamli satir: # BERT NLP Temel Kavramlar ve Calisma Prensibi
- Son anlamli satir: ```
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # BERT NLP Temel Kavramlar ve Calisma Prensibi; ## 1) Temel Terimler; ## 2) Sistem Neden Bu Sekilde Kuruldu?
  - L61-L120: basliklar -> ## 3) End-to-End Ornek (Route); ## 4) End-to-End Ornek (POI); ## 5) Intent Refine Nedir?; ## 6) Lexical Exact Lookup Neden Kritik?
  - L121-L170: basliklar -> ## 7) Gold Test Seti Nasil Kullaniliyor?; ## 8) Kisa Ozet; ## 9) GPU Calisma Notu (Onemli)

### 65. `docs/ogretici/openmeteo-sifirdan-rehber.md`
- Satir sayisi: 268
- Boyut: 7197 bayt
- Ilk anlamli satir: # OpenMeteo API - Sıfırdan Başlangıç Rehberi
- Son anlamli satir: Çalıştırma: `python test_ilk_baglanti.py`
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # OpenMeteo API - Sıfırdan Başlangıç Rehberi; ## Bölüm 1: OpenMeteo Nedir?; ## Bölüm 2: Ne Lazım?; ## Bölüm 3: İlk Bağlantı - Tarayıcıdan Deneme
  - L61-L120: basliklar -> ## Bölüm 4: Python'dan İlk İstek; ### Adım 1: Boş bir Python dosyası oluşturun; ### Adım 2: Bu kodu yazın; # 1. API adresi (OpenMeteo'nun sunucu adresi)
  - L121-L180: basliklar -> ## Bölüm 6: Hata Durumları; ### İnternet yoksa; # Hata: requests.exceptions.ConnectionError; ### Sunucu yanıt vermezse (10 saniye bekledikten sonra)
  - L181-L240: basliklar -> ## Bölüm 8: Projedeki Kullanım (weather_service.py); ## Bölüm 9: Özet - İlk Kullanım Checklist; ## Bölüm 10: Hızlı Test Scripti; # test_ilk_baglanti.py
  - L241-L268: metin/rapor icerigi

### 66. `docs/ogretici/openmeteo_ornek_kullanim.py`
- Satir sayisi: 132
- Boyut: 6058 bayt
- Python ozeti: import=1, sinif=0, fonksiyon=0, flask_route=0
- Ilk anlamli satir: """
- Son anlamli satir: print("HATA:", str(hata))
- Satir araligi incelemesi:
  - L1-L60: yardimci/degisken/akis kodu
  - L61-L120: yardimci/degisken/akis kodu
  - L121-L132: yardimci/degisken/akis kodu

### 67. `docs/osm/API_ENDPOINTS.md`
- Satir sayisi: 528
- Boyut: 9884 bayt
- Ilk anlamli satir: # 🚀 OpenRoutePlanner API Endpoint'leri
- Son anlamli satir: **Versiyon:** 1.0
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # 🚀 OpenRoutePlanner API Endpoint'leri; ## 📋 Tüm Endpoint'ler ve Kullanılabilir Alanlar; ## 🗺️ ROTA API'LERİ; ### 1. POST `/api/get-route`
  - L61-L120: basliklar -> ## 📍 POI (İlgi Noktası) API'LERİ; ### 3. POST `/api/search-pois`
  - L121-L180: basliklar -> ## 🌍 GEOCODING API'LERİ; ### 4. POST `/api/geocode`; ### 5. POST `/api/reverse-geocode`; ### 6. POST `/api/geocode/batch`
  - L181-L240: basliklar -> ## 💾 ROTA KAYDETME API'LERİ; ### 7. POST `/api/routes/save`; ### 8. GET `/api/routes`; ### 9. GET `/api/routes/<route_id>`
  - L241-L300: basliklar -> ### 10. PUT `/api/routes/<route_id>`; ### 11. DELETE `/api/routes/<route_id>`; ### 12. POST `/api/routes/<route_id>/favorite`; ### 13. GET `/api/routes/search`
  - L301-L360: basliklar -> ### 15. POST `/api/timeline/create`; ### 16. POST `/api/timeline/check-conflicts`
  - L361-L420: basliklar -> ### 17. POST `/api/timeline/optimize`; ## 📌 LOKASYON API'LERİ; ### 18. GET `/api/locations`; ### 19. POST `/api/locations`
  - L421-L480: basliklar -> ### 22. GET `/api/health`; ## 📊 ÖZET; ## 🎯 Kullanım Örnekleri; ### Örnek 1: Rota Oluştur
  - L481-L528: basliklar -> ## 🔧 Yeni Endpoint Eklemek İçin; # İşlemler...; ## 📝 Notlar

### 68. `docs/osm/OSM_API_REHBERI.md`
- Satir sayisi: 351
- Boyut: 11707 bayt
- Ilk anlamli satir: # 🗺️ OSM API Rehberi — Nominatim, Overpass ve Taginfo
- Son anlamli satir: **Son Güncelleme:** 04.03.2026
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # 🗺️ OSM API Rehberi — Nominatim, Overpass ve Taginfo; ## 📋 İçindekiler; ## 1. OSM Ekosistemi Özeti; ## 2. OSM Tag Sistemi (key=value)
  - L61-L120: basliklar -> ### Ana Tag Anahtarları (Key); ## 3. Nominatim API; ### Ne İşe Yarar?; ### Base URL
  - L121-L180: basliklar -> ### ⚠️ Önemli Kurallar; ### Python Örneği; ## 4. Overpass API; ### Ne İşe Yarar?
  - L181-L240: basliklar -> ### Overpass QL Temel Sözdizimi; ### Örnek Sorgu: Kadıköy'deki Kafeler; ### Python Örneği; ### Örnek Yanıt Yapısı
  - L241-L300: basliklar -> ### ⚠️ Önemli Kurallar; ## 5. Taginfo — Hangi Tag'ler Var?; ### Ne İşe Yarar?; ### URL
  - L301-L351: basliklar -> ### Tag Sistemi; ### Taginfo; ## 7. Karşılaştırma Tablosu; ## Özet Akış Örneği

### 69. `docs/osm/OSM_CATEGORIES_FULL.md`
- Satir sayisi: 543
- Boyut: 15437 bayt
- Ilk anlamli satir: # 🗺️ OpenStreetMap - Tüm Kategori ve Tag'ler
- Son anlamli satir: **Toplam:** 500+ farklı kategori! 🎯
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # 🗺️ OpenStreetMap - Tüm Kategori ve Tag'ler; ## 📋 OSM Tag Sistemi Nasıl Çalışır?; ## 🏪 1. AMENITY (Tesisler); ### ☕ Yiyecek & İçecek
  - L61-L120: basliklar -> ### 🎭 Eğlence; ### 🚗 Ulaşım; ### 🏛️ Din; ### 🗑️ Diğer
  - L121-L180: basliklar -> ## 🏪 2. SHOP (Mağazalar); ### 🛒 Gıda; ### 👕 Giyim; ### 📱 Elektronik
  - L181-L240: basliklar -> ### 📚 Kültür; ### 💄 Kişisel Bakım; ### 🚗 Otomotiv; ### 🐕 Hayvan
  - L241-L300: basliklar -> ### 🔧 Diğer; ## 🏨 3. TOURISM (Turizm)
  - L301-L360: basliklar -> ## 🎾 4. LEISURE (Eğlence & Spor); ## 🚉 5. RAILWAY (Demiryolu); ## 🚌 6. HIGHWAY (Yol & Ulaşım)
  - L361-L420: basliklar -> ## 🏢 7. OFFICE (Ofisler); ## 🏛️ 8. HISTORIC (Tarihi Yerler); ## 🏗️ 9. BUILDING (Binalar)
  - L421-L480: basliklar -> ## 🌳 10. NATURAL (Doğal Özellikler); ## 🎯 NASIL KULLANILIR?; ### Örnek 1: Tüm Restoranlar
  - L481-L540: basliklar -> ### Örnek 2: Tüm Mağazalar; ### Örnek 3: Sadece Süpermarketler; ### Örnek 4: Camiler; ### Örnek 5: Tüm Turizm Yerleri
  - L541-L543: metin/rapor icerigi

### 70. `docs/osm/OSM_KAYNAKLARI.md`
- Satir sayisi: 429
- Boyut: 11787 bayt
- Ilk anlamli satir: # 🗺️ OpenStreetMap - Tüm Kategorileri Nereden Öğrenebilirim?
- Son anlamli satir: Hangisini yapalım? 🤔
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # 🗺️ OpenStreetMap - Tüm Kategorileri Nereden Öğrenebilirim?; ## 🎯 Resmi Kaynaklar; ### 1️⃣ **OSM Wiki - Map Features** (EN KAPSAMLI); ### 2️⃣ **Taginfo** (İSTATİSTİKLER)
  - L61-L120: basliklar -> ### 4️⃣ **OSM Wiki - Key Pages** (DETAYLI AÇIKLAMALAR); ### 5️⃣ **OSM Tag Finder** (ARAMA MOTORU); ## 🔍 PYTHON İLE NASIL ÖĞRENİRİZ?; ### Yöntem 1: Overpass API ile Tüm Tag'leri Çek
  - L121-L180: basliklar -> # Tüm tag'leri topla; # Kullanım; # Sonuçları yazdır; ### Yöntem 2: Taginfo API Kullan
  - L181-L240: basliklar -> # Kullanım; ### Yöntem 3: OSM Wiki'den Scrape Et
  - L241-L300: basliklar -> # Tablo bul; # Kullanım; ## 📊 HIZLI REFERANS - EN POPÜLER TAG'LER; ### Amenity (Top 30)
  - L301-L360: basliklar -> ### Shop (Top 30); ### Tourism (Top 20)
  - L361-L420: basliklar -> ### Leisure (Top 20); ## 🎯 SONUÇ
  - L421-L429: basliklar -> ## 🚀 PROJEYE NASIL EKLERİZ?

### 71. `docs/osm/OSM_TAG_DOGRULAMA.md`
- Satir sayisi: 213
- Boyut: 5667 bayt
- Ilk anlamli satir: # 🔍 OSM Tag Doğrulama - Gerçekten Var mı?
- Son anlamli satir: Hepsi **gerçek** ve **OSM'de kayıtlı**! ✅
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # 🔍 OSM Tag Doğrulama - Gerçekten Var mı?; ## ❓ Soru: "stadium" tag'i gerçekten var mı?; ## 📊 Gerçek OSM İstatistikleri (Taginfo'dan); ### 1️⃣ leisure=stadium
  - L61-L120: basliklar -> ### Yöntem 1: Taginfo (En Kolay); ### Yöntem 2: Overpass Turbo (Canlı Test); ### Yöntem 3: OSM Wiki; ## ✅ Doğrulanmış Kategoriler
  - L121-L180: basliklar -> ## 🔍 Yeni Bir Tag Eklemeden Önce Kontrol Et; ### Adım 1: Taginfo'da Ara; ### Adım 2: OSM Wiki'de Kontrol Et; ### Adım 3: Overpass Turbo'da Test Et
  - L181-L213: basliklar -> ## 🚀 Bonus: İstanbul'daki Stadyumlar

### 72. `docs/osm/komutlar.md`
- Satir sayisi: 141
- Boyut: 3465 bayt
- Ilk anlamli satir: # Komutlar Rehberi - GSD + SuperClaude + Claude Code
- Son anlamli satir: ```
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # Komutlar Rehberi - GSD + SuperClaude + Claude Code; ## 🚀 GSD (Get Shit Done) Komutları; ### Proje Yönetimi; ### Planlama ve Çalışma
  - L61-L120: basliklar -> ### Diğer; ## 📝 Claude Code Yerel Komutları; ## 💡 Kullanım Örnekleri; ### Öğrenme Süreci İçin:
  - L121-L141: basliklar -> ## ⚡ Hızlı Başlangıç

### 73. `docs/osm/nominatim-osm-basit.md`
- Satir sayisi: 179
- Boyut: 5849 bayt
- Ilk anlamli satir: # Nominatim ve OSM - Basit Anlatım
- Son anlamli satir: - **Nominatim = Arama motoru (bu veride arama yapar)**
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # Nominatim ve OSM - Basit Anlatım; ## 🎯 En Basit Haliyle; ## 📚 Google Benzetmesi; ## 🔍 Örnek Senaryo
  - L61-L120: basliklar -> ## 💻 Kod ile Görelim; # Nominatim API'sini kullanıyoruz (bu bir web servisi); # OSM veritabanını aramak için; # Arama yapıyoruz
  - L121-L179: basliklar -> ## 🆚 Karşılaştırma; ## 🎯 Tekrar Özet; ## 💡 Neden İkisine de İhtiyacımız Var?; ## 🔗 Gerçek Hayat Örneği

### 74. `docs/osm/osm-kavramlari.md`
- Satir sayisi: 343
- Boyut: 13284 bayt
- Ilk anlamli satir: # OpenStreetMap Ekosistemi - Nasıl Çalışır?
- Son anlamli satir: - ❌ Nominatim (yeni ekleyeceğiz - doğal dil sorgu için)
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # OpenStreetMap Ekosistemi - Nasıl Çalışır?; ## 🗺️ Genel Bakış; ## 1. OpenStreetMap (OSM) - Veri Kaynağı
  - L61-L120: basliklar -> ## 2. OSMnx - Python Kütüphanesi; # 1. OSM'den Kadıköy'ün yürüyüş ağını indir; # 2. Grafiği kaydet (cache); # 3. İki nokta arasında rota hesapla
  - L121-L180: basliklar -> ## 3. Nominatim - Geocoding API; # API isteği; # Yanıt; # API isteği
  - L181-L240: basliklar -> # Kullanım; # {'lat': 40.9850, 'lon': 29.0250, 'name': 'Kadıköy Parkı, Caferağa...'}; ## 4. Leaflet.js - JavaScript Kütüphanesi; ## 🔗 Hepsi Bir Arada - Proje Akışı
  - L241-L300: basliklar -> ## 📊 Karşılaştırma Tablosu; ## 🎓 Özet
  - L301-L343: basliklar -> ## 🔗 Faydalı Linkler; ## ❓ Sorular

### 75. `docs/planlar/PERFORMANS_OPTIMIZASYON_PLANI.md`
- Satir sayisi: 359
- Boyut: 11128 bayt
- Ilk anlamli satir: # OpenRoutePlanner — Performans Optimizasyon Planı
- Son anlamli satir: **Dosya sonu — Güncellemeler buraya eklenebilir**
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # OpenRoutePlanner — Performans Optimizasyon Planı; ## İÇİNDEKİLER; ## 1. GENEL BAKIŞ; ### 1.1 Planın Amacı
  - L61-L120: basliklar -> ### 2.3 İndeksler ✅; ### 2.4 mmap + ANALYZE ✅; ### 2.5 geocodes.db PRAGMA + TTL ✅; ### 2.6 local_places Tablosu ✅
  - L121-L180: basliklar -> ## 4. MEMORY-MAPPED I/O (mmap) AÇIKLAMASI; ### 4.1 Normal SQLite Okuma; ### 4.2 Memory-Mapped (mmap) ile; ### 4.3 Benzetme
  - L181-L240: basliklar -> ### 5.2 Preload ile Ne Olacak?; ### 5.3 Benzetme; ### 5.4 Regions Manifest (Bölge Kaydı); ### 5.5 get_graph_for_points Mantığı (Yeni)
  - L241-L300: basliklar -> ## 6. GEOCODE TTL VE CACHE TEMİZLİĞİ; ### 6.1 Sorun; ### 6.2 Çözüm: TTL (Time To Live); ### 6.3 Örnek Cleanup Sorgusu
  - L301-L359: basliklar -> ### FAZ 3: Preload Region Yönetimi (Zor, En Büyük Etki); ## 8. KOD REFERANSLARI; ### 8.1 Mevcut Dosya Konumları; ### 8.2 PRAGMA Değer Referansı

### 76. `docs/planlar/VERITABANI_DOKUMANTASYONU.md`
- Satir sayisi: 266
- Boyut: 9153 bayt
- Ilk anlamli satir: # OpenRoutePlanner — Veritabanı Dokümantasyonu
- Son anlamli satir: - Alternatif rotalar veritabanına otomatik yazılmaz; kullanıcı kaydettiğinde `route_type` ile tek rota kaydedilir
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # OpenRoutePlanner — Veritabanı Dokümantasyonu; ## 1. VERİTABANI ÖZETİ; ## 2. app_data.db — Rota ve Lokasyon Depolama; ### 2.1 routes tablosu
  - L61-L120: basliklar -> ### 2.3 local_places tablosu (YENİ — 08.03.2026); ## 3. geocodes.db — Geocoding Cache; ### 3.1 geocodes tablosu; ### 3.2 reverse_geocodes tablosu
  - L121-L180: basliklar -> ## 5. DİĞER VERİ KAYNAKLARI (Veritabanı Değil); ### 5.1 turkey_places.py; ### 5.2 OSM GraphML dosyaları; ### 5.3 Memory cache (RAM)
  - L181-L240: basliklar -> ## 8. GELECEK FİKİRLER — Optimizasyon ve Geliştirme; ### 8.1 SQLite Performans; ### 8.2 Yerel Yer Veritabanı; ### 8.3 Geocoding İyileştirmeleri
  - L241-L266: basliklar -> ## 9. DOSYA KONUMLARI ÖZETİ; ## 10. NOTLAR

### 77. `docs/planlar/bert-calisma-akis-semasi.md`
- Satir sayisi: 114
- Boyut: 4971 bayt
- Ilk anlamli satir: # BERT Calisma Akis Semasi (Detayli)
- Son anlamli satir: - Benchmark scripti ile degisiklikten sonra kalite/regresyon olculur.
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # BERT Calisma Akis Semasi (Detayli); ## 1) Calisma Akisi (Runtime Parse); ## 2) Kutu Aciklamalari (Parse)
  - L61-L114: basliklar -> ## 3) _choose_best_poi_location() Ic Mantigi; ## 4) Intent Refine Kurallari (Ozet); ## 5) Degerlendirme (Gold Benchmark) Akisi; ## 6) Neden Bu Mimari?

### 78. `docs/planlar/bert-gelistirme-akisi.md`
- Satir sayisi: 367
- Boyut: 7085 bayt
- Ilk anlamli satir: # BERT Gelistirme Akisi
- Son anlamli satir: - origin / destination hatalarini azaltir
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # BERT Gelistirme Akisi; ## Hedef; ## Mevcut Sistem; ### Mevcut sistemin sorunu
  - L61-L120: basliklar -> ## Ana Fikir; ## Ornek 1: Route Sorgusu; ### 1. Normalize; ### 2. Mention Detection
  - L121-L180: basliklar -> ### 4. Place Linking; ### 5. Slot Filling; ### 6. Final Result; ## Ornek 2: POI Sorgusu
  - L181-L240: basliklar -> ## Yeni Moduller; ## Kisa Gorev Tanimlari; ### 1. Query Normalizer; ### 2. Mention Detector
  - L241-L300: basliklar -> ### 3. Place Retriever; ### 4. Place Linker; ### 5. Slot Filler
  - L301-L360: basliklar -> ## Uygulama Sirasi; ### Asama 1; ### Asama 2; ### Asama 3
  - L361-L367: metin/rapor icerigi

### 79. `docs/planlar/bert-gold-test-seti-kullanimi.md`
- Satir sayisi: 78
- Boyut: 1778 bayt
- Ilk anlamli satir: # BERT Gold Test Seti Kullanimi
- Son anlamli satir: - Ilk asamada sadece Turkce odakli tutulmustur.
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # BERT Gold Test Seti Kullanimi; ## Dosyalar; ## Amac; ## Calistirma
  - L61-L78: basliklar -> ## Notlar

### 80. `docs/planlar/bert-poi-lokasyon-spec-kit-v1.md`
- Satir sayisi: 577
- Boyut: 17055 bayt
- Ilk anlamli satir: # BERT + Türkçe Morfoloji + Sözlük + Overpass Entegrasyonu
- Son anlamli satir: **Öneri:** Faz-1’i hızlıca tamamlayıp golden set ile ölç, sonra Faz-2 güçlendirmesine geç.
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # BERT + Türkçe Morfoloji + Sözlük + Overpass Entegrasyonu; ## POI/Lokasyon Çözümleme Spec Kit (v1.1); ## 1) Problem Tanımı; ## 2) Hedefler ve Hedef Dışı
  - L61-L120: basliklar -> ## 5) Üst Düzey Mimari; ### 5.1 Akış; ### 5.2 Ayrı Pipeline Prensibi; ## 6) Veri Modeli Tasarımı
  - L121-L180: basliklar -> ### 6.3 Sözlük Sürümleme ve Migrasyon; ## 7) Ön Normalizasyon Kuralları; ## 8) Aday Çıkarma Stratejisi; ### 8.1 Token + N-gram
  - L181-L240: basliklar -> ## 10) Lokasyon Çözümleme; ## 11) Intent Çözümleme; ### 11.1 Mevcut Sistem Tipleri ile Mapping (Regresyon Önleyici); ## 12) Overpass Tag Planı (A/B/C)
  - L241-L300: basliklar -> ## 13) Unknown / Ambiguous Politikası; ### 13.1 Lokasyon-POI Çakışma Karar Matrisi (Tie-break); ## 14) Eşik Politikası (İlk Değerler); ### 14.1 Kalibrasyon Protokolü
  - L301-L360: basliklar -> ## 15) Performans ve Cache Planı; ### 15.1 TTL / Invalidation / Version Pinning; ## 16) Gözlemlenebilirlik (Observability)
  - L361-L420: basliklar -> ## 17) Kalite Metrikleri; ## 18) Test Stratejisi; ### 18.1 Unit Test; ### 18.2 Golden Set
  - L421-L480: basliklar -> ## 21) Dosya Bazlı Teknik Plan; ### Mevcut dosyalarda değişecek yerler; ### Yeni/yeniden düzenlenecek yardımcı dosyalar; ## 22) Önerilen Fonksiyon İmzaları
  - L481-L540: basliklar -> ## 23) Kabul Kriterleri (Definition of Done); ## 24) Risk Register; ## 25) Operasyon ve Süreç; ## 26) Açık Kararlar (Karar Gerektiren Noktalar)
  - L541-L577: basliklar -> ## 28) Örnek Senaryolar; ## 29) Sonuç

### 81. `docs/planlar/ci-test-runbook.md`
- Satir sayisi: 24
- Boyut: 785 bayt
- Ilk anlamli satir: # CI ve Test Runbook
- Son anlamli satir: - Artifact dosyaları (`.coverage`, `*.db-wal`, `*.db-shm`, `_test_result.json`) commitlenmemeli
- Satir araligi incelemesi:
  - L1-L24: basliklar -> # CI ve Test Runbook; ## Amaç; ## Yerel Çalıştırma; ## CI Akışı

### 82. `docs/planlar/gelisirme-firsatlari-analizi.md`
- Satir sayisi: 460
- Boyut: 12084 bayt
- Ilk anlamli satir: # OpenRoutePlanner - Geliştirme Fırsatları Analizi
- Son anlamli satir: *Bu belge Canlı - güncellemeler devam edecek*
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # OpenRoutePlanner - Geliştirme Fırsatları Analizi; ## 📊 Özet; ### İstatistikler; ## 🔴 Kritik Öncelik (Acil)
  - L61-L120: basliklar -> # ÖNCESİ; # SONRASI; ### 3. Hata Yönetimi Standardizasyonu; # backend/exceptions.py (Yeni Dosya)
  - L121-L180: basliklar -> ## 🟡 Yüksek Öncelik; ### 4. BERT NLP Pipeline Refactoring; # bert_nlp_engine.py refactor; # 1. Normalize
  - L181-L240: basliklar -> # backend/logging_config.py (Yeni Dosya); # Format; # Handler'lar; # Configure
  - L241-L300: basliklar -> # Kullanım; ## 🟢 Orta Öncelik; ### 7. Frontend Modularization; ### 8. Configuration Management
  - L301-L360: basliklar -> # backend/config.py (Yeni Dosya); # Kullanım; ### 9. API Documentation (OpenAPI/Swagger)
  - L361-L420: basliklar -> # swagger.yaml (Yeni Dosya); ## 📋 Önceliklendirilmiş Action Plan; ### Faz 1: Foundation (1-2 hafta); ### Faz 2: Quality (2-3 hafta)
  - L421-L460: basliklar -> ## 📈 Success Metrics; ## 🚀 Quick Wins (1 gün içinde); ## 💡 Teknik Borç (Technical Debt) Listesi

### 83. `docs/planlar/hava-durumu-entegrasyon-plani.md`
- Satir sayisi: 163
- Boyut: 3790 bayt
- Ilk anlamli satir: # Hava Durumu Entegrasyon Plani
- Son anlamli satir: - `gunluk-rapor/09.03.2026/09.03.2026.txt`
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # Hava Durumu Entegrasyon Plani; ## Amac; ## Kullanici Ihtiyaclari; ### 1. Hava durumuna gore tavsiye
  - L61-L120: basliklar -> ### Faz 2: Timeline Entegrasyonu; ### Faz 3: Akilli Oneri Sistemi; ## Etkilenecek Dosyalar; ## Teknik Notlar
  - L121-L163: basliklar -> ## Uygulama Sirasi; ## Kabul Kriterleri (Olculebilir); ## Baglantili Dokumanlar

### 84. `docs/planlar/nlp-dataset-v1-corrections-final.jsonl`
- Satir sayisi: 19
- Boyut: 4538 bayt
- Ilk anlamli satir: {"id":"tr_000017","text":"pendik'ten kadıköy'e yol tarifi","intent":"route","slots":{"origin":"pendik","destination":...
- Son anlamli satir: {"id":"tr_000165","text":"sarıyerde nöbetçi eczane nerde","intent":"poi","slots":{"origin":null,"destination":null,"l...
- Satir araligi incelemesi:
  - L1-L19: veri satirlari/json icerigi

### 85. `docs/planlar/nlp-dataset-v1-fix-ids.txt`
- Satir sayisi: 33
- Boyut: 400 bayt
- Ilk anlamli satir: CRITICAL_INTENT_SLOT
- Son anlamli satir: tr_000100
- Satir araligi incelemesi:
  - L1-L33: metin/rapor icerigi

### 86. `docs/planlar/nlp-dataset-v1-qc-2026-03-11.md`
- Satir sayisi: 82
- Boyut: 2696 bayt
- Ilk anlamli satir: # NLP Dataset V1 QC Raporu (2026-03-11)
- Son anlamli satir: - Slot normalizasyon standardi: `%100`
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # NLP Dataset V1 QC Raporu (2026-03-11); ## 1) Kritik Hatalar (egitime direkt verilmemeli); ### A) Intent-slot uyumsuzlugu; ### B) POI satirlarinda `poi_concept` bos (kurala aykiri)
  - L61-L82: basliklar -> ### C) Asiri genel lokasyonlar (modeli bulaniklastirabilir); ## 3) Duzeltme Oncelik Sirasi; ## 4) Hedef Kalite Kriteri (V2)

### 87. `docs/planlar/oneriler-7-mart.md`
- Satir sayisi: 428
- Boyut: 9981 bayt
- Ilk anlamli satir: # OpenRoutePlanner - 7 Mart Önerileri
- Son anlamli satir: Eğer bu üç alan doğru bağlanırsa, uygulama sıradan bir rota çiziciden çıkıp akıllı gezi planlama asistanına dönüşebilir.
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # OpenRoutePlanner - 7 Mart Önerileri; ## Genel Değerlendirme; ## En Yüksek Öncelikli Geliştirmeler; ### 1. Doğal Dil ile Rota ve Arama
  - L61-L120: basliklar -> ### 3. JSON Tabanlı Kayıt Yapısından SQLite'a Geçiş; ### 4. Frontend Kodunun Modüler Hale Getirilmesi
  - L121-L180: basliklar -> ## Ürünü Güçlendirecek Özellikler; ### 5. GPX ve GeoJSON Dışa Aktarma; ### 6. Paylaşılabilir Rota Linki; ### 7. Ulaşım Modu Desteği
  - L181-L240: basliklar -> ### 8. Akıllı POI Filtreleri; ### 9. Rota Tercihleri; ### 10. Rota Üzerine Not ve Durak Bilgisi
  - L241-L300: basliklar -> ### 11. Rota Üzerinde Yakındaki Yer Önerileri; ### 12. Geri Alma / İleri Alma Sistemi; ## Teknik Olarak Güçlendirilmesi Gereken Alanlar; ### 13. Test Altyapısının Güçlendirilmesi
  - L301-L360: basliklar -> ### 14. Python ve Torch Uyumluluğunun Netleştirilmesi; ### 15. Loglama ve Performans Ölçümü; ### 16. Dokümantasyon Güncellemesi; ### 17. Mobil Uyum ve Arayüz İyileştirmesi
  - L361-L420: basliklar -> ### 18. Güvenlik ve Rate Limit Katmanı; ## Önerilen Yol Haritası; ### Faz 1; ### Faz 2
  - L421-L428: metin/rapor icerigi

### 88. `docs/planlar/performance-optimizations-implementation.md`
- Satir sayisi: 206
- Boyut: 5272 bayt
- Ilk anlamli satir: # Performance Optimizations - Implementation Summary
- Son anlamli satir: - **Backward compatible** - mevcut kodla uyumlu
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # Performance Optimizations - Implementation Summary; ## ✅ Tamamlanan Optimizasyonlar; ### 1. LRU Cache for Graphs; # Graph al (memory → preloaded → disk sırası)
  - L61-L120: basliklar -> # POI al; # POI ekle; # İstatistikler; # {"size": 15, "maxsize": 50, "hits": 200, "misses": 30, "hit_rate": "87.0%", "ttl": 1800}
  - L121-L180: basliklar -> ## 📈 Performans Kazançları; ## 🔧 Konfigürasyon; # Cache Yönetimi; ## 📊 İzleme (Monitoring)
  - L181-L206: basliklar -> ## 🚀 Sonraki Adımlar; ## 📝 Notlar

### 89. `docs/planlar/poi-semantic-tag-grounding-plani.md`
- Satir sayisi: 143
- Boyut: 4634 bayt
- Ilk anlamli satir: # POI Semantic Tag Grounding Plani
- Son anlamli satir: - sistem daha aciklanabilir ve bakimi kolay hale gelir
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # POI Semantic Tag Grounding Plani; ## 1) Problem Tanimi; ## 2) Cozum Ozet; ## 3) Neden Bu Yontem
  - L61-L120: basliklar -> ## 5) Veri Akisi (Request); ## 6) Skorlama Onerisi; ## 7) Hardcoded Olmadan Dogruluk Stratejisi; ## 8) Loglama ve Gozlemlenebilirlik
  - L121-L143: basliklar -> ### 9.3 Regression; ## 10) Rollout Plani; ## 11) Beklenen Sonuc

### 90. `docs/planlar/weather-service-akis-diyagrami.md`
- Satir sayisi: 475
- Boyut: 27812 bayt
- Ilk anlamli satir: # Hava Durumu Servisi - Akış Diyagramları
- Son anlamli satir: | 9. Veri Dönüşümü | API formatı → uygulama formatı |
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # Hava Durumu Servisi - Akış Diyagramları; ## 1. Ana Akış Özeti (Üst Seviye); ## 2. Güncel Hava Akışı (get_current_weather)
  - L61-L120: basliklar -> ## 3. Saatlik Forecast Akışı (get_hourly_forecast)
  - L121-L180: basliklar -> ## 4. Rota Hava Kontrolü Akışı (check_route_weather)
  - L181-L240: metin/rapor icerigi
  - L241-L300: basliklar -> ## 5. Cache Mekanizması Akışı
  - L301-L360: basliklar -> ## 6. WMO Kod İşleme Akışı; ## 7. Hata Yakalama Akışı
  - L361-L420: basliklar -> ## 8. Katman Mimarisi (Dikey Akış)
  - L421-L475: basliklar -> ## 9. Veri Dönüşüm Akışı; ## Özet Tablo

### 91. `docs/planlar/weather-service-design.md`
- Satir sayisi: 540
- Boyut: 13203 bayt
- Ilk anlamli satir: # Hava Durumu Servisi - Tasarım Belgesi
- Son anlamli satir: - Proje Planı: `docs/planlar/hava-durumu-entegrasyon-plani.md`
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # Hava Durumu Servisi - Tasarım Belgesi; ## Sürüm; ## 1. Genel Bakış; ### 1.1 Amaç
  - L61-L120: basliklar -> ## 3. API Tasarımı; ### 3.1 Endpoint 1: Güncel Hava Durumu; ### 3.2 Endpoint 2: Saatlik Forecast
  - L121-L180: basliklar -> ### 3.3 Endpoint 3: Rota Kontrolü
  - L181-L240: basliklar -> ## 4. OpenMeteo API Entegrasyonu; ### 4.1 Base URL; ### 4.2 Current Weather İstek Parametreleri; ### 4.3 Hourly Forecast İstek Parametreleri
  - L241-L300: basliklar -> ## 6. Cache Stratejisi; ### 6.1 Cache Türleri; ### 6.2 Cache Key Formatı; ### 6.3 Cache Invalidation
  - L301-L360: basliklar -> # Imports; # Local imports; # Constants; # Global cache
  - L361-L420: basliklar -> ### 8.2 weather_utils.py; # Constants; # ...; # Functions
  - L421-L480: basliklar -> ## 10. Test Senaryoları; ### 10.1 Unit Tests; # test_weather_service.py; # First call - cache miss
  - L481-L540: basliklar -> ## 11. Performans Hedefleri; ## 12. Güvenlik; ### 12.1 Rate Limiting; ### 12.2 Input Validation

### 92. `docs/raporlar/BERT_GOLD_EVAL_TR_20260310_123841.md`
- Satir sayisi: 58
- Boyut: 3231 bayt
- Ilk anlamli satir: # BERT Gold Evaluation (TR)
- Son anlamli satir: - fields: `{'type': False}`
- Satir araligi incelemesi:
  - L1-L58: basliklar -> # BERT Gold Evaluation (TR); ## Field Accuracy; ## Failures (first 20)

### 93. `docs/raporlar/BERT_GOLD_EVAL_TR_20260310_124044.md`
- Satir sayisi: 74
- Boyut: 4367 bayt
- Ilk anlamli satir: # BERT Gold Evaluation (TR)
- Son anlamli satir: - fields: `{'type': False}`
- Satir araligi incelemesi:
  - L1-L60: basliklar -> # BERT Gold Evaluation (TR); ## Field Accuracy; ## Failures (first 20)
  - L61-L74: metin/rapor icerigi

### 94. `docs/raporlar/BERT_GOLD_EVAL_TR_20260310_125637.md`
- Satir sayisi: 46
- Boyut: 2528 bayt
- Ilk anlamli satir: # BERT Gold Evaluation (TR)
- Son anlamli satir: - fields: `{'type': False, 'locations': False}`
- Satir araligi incelemesi:
  - L1-L46: basliklar -> # BERT Gold Evaluation (TR); ## Field Accuracy; ## Failures (first 20)

### 95. `docs/raporlar/BERT_GOLD_EVAL_TR_20260310_130916.md`
- Satir sayisi: 19
- Boyut: 433 bayt
- Ilk anlamli satir: # BERT Gold Evaluation (TR)
- Son anlamli satir: - None
- Satir araligi incelemesi:
  - L1-L19: basliklar -> # BERT Gold Evaluation (TR); ## Field Accuracy; ## Failures (first 20)

### 96. `docs/raporlar/BERT_GOLD_EVAL_TR_20260315_181123.md`
- Satir sayisi: 38
- Boyut: 1846 bayt
- Ilk anlamli satir: # BERT Gold Evaluation (TR)
- Son anlamli satir: - fields: `{'type': False}`
- Satir araligi incelemesi:
  - L1-L38: basliklar -> # BERT Gold Evaluation (TR); ## Field Accuracy; ## Failures (first 20)

### 97. `docs/raporlar/BERT_GOLD_EVAL_TR_20260315_181341.md`
- Satir sayisi: 42
- Boyut: 2068 bayt
- Ilk anlamli satir: # BERT Gold Evaluation (TR)
- Son anlamli satir: - fields: `{'type': False}`
- Satir araligi incelemesi:
  - L1-L42: basliklar -> # BERT Gold Evaluation (TR); ## Field Accuracy; ## Failures (first 20)

### 98. `docs/raporlar/bert_calibration_phase2_latest.md`
- Satir sayisi: 43
- Boyut: 1549 bayt
- Ilk anlamli satir: # BERT Calibration / Regression Özeti (Faz-2)
- Son anlamli satir: - Üretim için hızlı/kararlı yol: OSM kapalı deterministik parse + gerektiğinde bounded OSM lookup.
- Satir araligi incelemesi:
  - L1-L43: basliklar -> # BERT Calibration / Regression Özeti (Faz-2); ## Çalıştırılan benchmark; ## Sonuçlar; ### 1) Deterministik mod (OSM kapalı)

### 99. `docs/raporlar/bert_osm_operasyon_profilleri.md`
- Satir sayisi: 56
- Boyut: 1707 bayt
- Ilk anlamli satir: # BERT + OSM Operasyon Profilleri (Güncel)
- Son anlamli satir: Yeni profil ayarları ile bu gecikme azaltıldı.
- Satir araligi incelemesi:
  - L1-L56: basliklar -> # BERT + OSM Operasyon Profilleri (Güncel); ## Özet; ## Yeni ENV ayarları; ## Önerilen profiller

### 100. `empty_pytest.ini`
- Satir sayisi: 1
- Boyut: 2 bayt
- Satir araligi incelemesi:
  - L1-L1: Bos/yalnizca bosluk

### 101. `frontend/bert-test-lab.html`
- Satir sayisi: 1411
- Boyut: 52648 bayt
- Ilk anlamli satir: ﻿<!DOCTYPE html>
- Son anlamli satir: </html>
- Satir araligi incelemesi:
  - L1-L60: UI/JS parcalari -> .container { | .header { | .header h1 {
  - L61-L120: UI/JS parcalari -> .status-badge { | .status-badge.connected { | .status-badge.disconnected {
  - L121-L180: UI/JS parcalari -> .card-icon { | .card-title { | .input-group {
  - L181-L240: UI/JS parcalari -> .btn-primary { | .btn-primary:hover { | .btn-secondary {
  - L241-L300: UI/JS parcalari -> .score-display { | .score-circle { | .score-circle::before {
  - L301-L360: UI/JS parcalari -> .parsed-item { | .parsed-label { | .parsed-value {
  - L361-L420: UI/JS parcalari -> .model-info { | .info-item { | .info-label {
  - L421-L480: UI/JS parcalari -> .chat-input-area { | .chat-input-area input { | .mode-grid {
  - L481-L540: UI/JS parcalari -> .log-panel { | .log-line { | .log-info { color: #cbd5e1; }
  - L541-L600: UI/stil/markup icerigi
  - L601-L660: UI/stil/markup icerigi
  - L661-L720: UI/stil/markup icerigi
  - L721-L780: UI/JS parcalari -> function showToast(message, type = "success") { | setTimeout(() => toast.remove(), 3000); | function nowStamp() {
  - L781-L840: UI/JS parcalari -> function getModeLabel(status) { | function setModeStatus(mode, status, detail = "") { | function setGuardBanner(ok, message) { | .replace(/&/g, "&amp;")
  - L841-L900: UI/JS parcalari -> function evaluateStatusPayload(data) { | function renderStatusInfo(evalInfo, payload) {
  - L901-L960: UI/JS parcalari -> function setSimText(text1, text2) { | function setSimTest(text1, text2) { | ...evalInfo,
  - L961-L1020: UI/stil/markup icerigi
  - L1021-L1080: UI/JS parcalari -> function setQuery(query) { | const placesHtml = data.detected_places.map((item) => {
  - L1081-L1140: UI/JS parcalari -> rows.sort((a, b) => { | function renderBreakdownHtml(breakdown, winner) {
  - L1141-L1200: UI/JS parcalari -> const rowsHtml = breakdown.rows.map((row) => { | const candidates = candidatesText.split("\n").map((x) => x.trim()).filter(Boolean);
  - L1201-L1260: UI/stil/markup icerigi
  - L1261-L1320: UI/stil/markup icerigi
  - L1321-L1380: UI/JS parcalari -> data.detected_places.forEach((item) => {
  - L1381-L1411: UI/stil/markup icerigi

### 102. `frontend/css/style.css`
- Satir sayisi: 2062
- Boyut: 43285 bayt
- Ilk anlamli satir: /* ============================================
- Son anlamli satir: .wbi-text  { line-height: 1.4; }
- Satir araligi incelemesi:
  - L1-L60: UI/stil/markup icerigi
  - L61-L120: UI/JS parcalari -> #map { | .sidebar { | .sidebar-header {
  - L121-L180: UI/JS parcalari -> .logo h1 { | .tagline { | .section {
  - L181-L240: UI/JS parcalari -> .empty-state { | .point-item { | .point-item:hover {
  - L241-L300: UI/JS parcalari -> .point-item .btn-remove:hover { | .point-actions { | .point-item {
  - L301-L360: UI/JS parcalari -> .point-item .point-label { | .btn { | .btn:disabled {
  - L361-L420: UI/JS parcalari -> .btn-danger { | .btn-danger:hover:not(:disabled) { | .btn-ghost {
  - L421-L480: UI/JS parcalari -> .search-input:hover { | .search-input:focus { | .search-input::placeholder {
  - L481-L540: UI/JS parcalari -> .search-suggestion-item { | .search-suggestion-item:last-child { | .search-result-name {
  - L541-L600: UI/JS parcalari -> .select-input:focus { | .poi-grid { | .poi-grid::-webkit-scrollbar {
  - L601-L660: UI/JS parcalari -> .stat-card:first-child { | .stat-card:nth-child(2) { | .stat-card:nth-child(3) {
  - L661-L720: UI/JS parcalari -> .spinner { | .loading-spinner p { | .toast-container {
  - L721-L780: UI/JS parcalari -> .sidebar-footer p { | .sidebar-footer .version { | .custom-marker {
  - L781-L840: UI/JS parcalari -> .poi-popup .leaflet-popup-close-button:hover { | .poi-card { | .poi-card-header {
  - L841-L900: UI/JS parcalari -> .poi-detail-icon { | .poi-detail a { | .poi-detail a:hover {
  - L901-L960: UI/JS parcalari -> .sidebar { | #map { | .alternatives-list {
  - L961-L1020: UI/JS parcalari -> .alternative-card:hover { | .alternative-card.active { | .alternative-header {
  - L1021-L1080: UI/JS parcalari -> .alternative-stat .stat-icon { | .alternative-stat .stat-text { | .btn-select-route {
  - L1081-L1140: UI/JS parcalari -> .saved-route-header { | .saved-route-name { | .btn-favorite {
  - L1141-L1200: UI/JS parcalari -> .saved-route-actions { | .btn-load-route { | .btn-load-route:hover {
  - L1201-L1260: UI/JS parcalari -> .btn-success:hover:not(:disabled) { | .modal { | .modal-content {
  - L1261-L1320: UI/JS parcalari -> .modal-close:hover { | .modal-body { | .form-group {
  - L1321-L1380: UI/JS parcalari -> .timeline-settings { | .form-group-inline { | .form-group-inline label {
  - L1381-L1440: UI/JS parcalari -> .timeline-stat { | .timeline-stat-label { | .timeline-stat-value {
  - L1441-L1500: UI/JS parcalari -> .timeline-content { | .timeline-point-name { | .timeline-times {
  - L1501-L1560: UI/JS parcalari -> .saved-locations-list { | .saved-location-card { | .saved-location-card:hover {
  - L1561-L1620: UI/JS parcalari -> .ic-btn { | .ic-btn:hover { | .ic-btn-favorite {
  - L1621-L1680: UI/JS parcalari -> .icon-btn.active { | .location-marker { | .location-marker:hover {
  - L1681-L1740: UI/JS parcalari -> .nlp-input::placeholder { | .btn-nlp { | .btn-nlp:hover {
  - L1741-L1800: UI/JS parcalari -> .nlp-results { | .nlp-result-item { | .nlp-result-item:last-child {
  - L1801-L1860: UI/JS parcalari -> .nlp-result-places { | .nlp-place-tag { | .nlp-actions {
  - L1861-L1920: UI/JS parcalari -> .nlp-empty { | .weather-widget { | .weather-widget.auto-hide {
  - L1921-L1980: UI/JS parcalari -> .weather-widget .weather-desc { | .timeline-weather { | .tl-weather-emoji { font-size: 1rem; }
  - L1981-L2040: UI/JS parcalari -> .weather-banner.visible { | .weather-banner-info    { border-color: rgba(0,206,201,0.4); } | .weather-banner-warning { border-color: rgba(249,202,36,0.5); }
  - L2041-L2062: UI/JS parcalari -> .wbc-icon { font-size: 0.95rem; flex-shrink: 0; margin-top: 1px; } | .wbc-text { | .weather-banner-items {

### 103. `frontend/data/turkiye-data.json`
- Satir sayisi: 97
- Boyut: 13198 bayt
- Ilk anlamli satir: {
- Son anlamli satir: }
- Satir araligi incelemesi:
  - L1-L60: veri satirlari/json icerigi
  - L61-L97: veri satirlari/json icerigi

### 104. `frontend/favicon.ico`
- Tip: Binary/asset dosya
- Boyut: 283 bayt
- Satir analizi: Uygulanmadi (binary)

### 105. `frontend/favicon.svg`
- Tip: Binary/asset dosya
- Boyut: 283 bayt
- Satir analizi: Uygulanmadi (binary)

### 106. `frontend/index.html`
- Satir sayisi: 399
- Boyut: 20324 bayt
- Ilk anlamli satir: <!DOCTYPE html>
- Son anlamli satir: </html>
- Satir araligi incelemesi:
  - L1-L60: UI/stil/markup icerigi
  - L61-L120: UI/stil/markup icerigi
  - L121-L180: UI/stil/markup icerigi
  - L181-L240: UI/stil/markup icerigi
  - L241-L300: UI/stil/markup icerigi
  - L301-L360: UI/stil/markup icerigi
  - L361-L399: UI/stil/markup icerigi

### 107. `frontend/js/app.js`
- Satir sayisi: 2620
- Boyut: 89276 bayt
- Ilk anlamli satir: /**
- Son anlamli satir: }
- Satir araligi incelemesi:
  - L1-L60: UI/stil/markup icerigi
  - L61-L120: UI/JS parcalari -> function createNumberedIcon(number) { | function createPoiIcon(emoji) { | function isValidField(v) {
  - L121-L180: UI/JS parcalari -> function addPoint(lat, lng) { | function removePoint(index) { | markers.forEach((m, i) => {
  - L181-L240: UI/JS parcalari -> function clearAllPoints() { | markers.forEach((m) => map.removeLayer(m)); | function handleDragStart(e, index) {
  - L241-L300: UI/JS parcalari -> function updatePointsList() { | selectedPoints.forEach((p, i) => {
  - L301-L360: UI/JS parcalari -> function updateButtons() { | function drawRoute(data) {
  - L361-L420: UI/JS parcalari -> function clearRoute() { | routeGlowPolylines.forEach(layer => map.removeLayer(layer)); | function showRouteInfo(data) {
  - L421-L480: UI/JS parcalari -> function displayPois(pois, category) { | pois.forEach((poi) => {
  - L481-L540: UI/JS parcalari -> function buildPoiPopup(poi, emoji, label) {
  - L541-L600: UI/JS parcalari -> function clearPois() { | poiMarkers.forEach((m) => map.removeLayer(m)); | document.querySelectorAll(".btn-poi").forEach((btn) => btn.classList.remove("active"));
  - L601-L660: UI/JS parcalari -> locationIconBtns.forEach(btn => { | locationIconBtns.forEach(b => b.classList.remove("active")); | document.querySelectorAll(".btn-poi").forEach((btn) => {
  - L661-L720: UI/JS parcalari -> () => fetchSuggestions(query, suggestAbortController.signal), | elSearchResults.innerHTML = data.suggestions.map((s) => ` | elSearchResults.querySelectorAll(".search-suggestion-item").forEach((el) => {
  - L721-L780: UI/JS parcalari -> el.addEventListener("click", () => {
  - L781-L840: UI/JS parcalari -> function displaySearchResult(data) { | resultItem.addEventListener("click", () => { | saveButton.addEventListener("click", (event) => {
  - L841-L900: UI/JS parcalari -> function setNlpLoading(isLoading) { | function buildNlpSummary(result) { | function renderNlpResults(result) {
  - L901-L960: UI/JS parcalari -> elNlpResults.querySelectorAll("[data-action='apply-nlp']").forEach((button) => { | elNlpResults.querySelectorAll("[data-action='focus-nlp']").forEach((button) => {
  - L961-L1020: UI/stil/markup icerigi
  - L1021-L1080: UI/JS parcalari -> function displayAlternativeRoutes(alternatives) { | alternatives.forEach(alt => {
  - L1081-L1140: UI/JS parcalari -> alternatives.forEach((alt, index) => { | function selectAlternativeRoute(routeType, routeCoords) {
  - L1141-L1200: UI/JS parcalari -> document.querySelectorAll(".alternative-card").forEach(card => {
  - L1201-L1260: UI/JS parcalari -> function openSaveRouteModal() { | function closeSaveRouteModal() { | const tags = tagsInput ? tagsInput.split(",").map(t => t.trim()).filter(t => t) : [];
  - L1261-L1320: UI/JS parcalari -> function displaySavedRoutes(routes) { | routes.forEach(route => {
  - L1321-L1380: UI/JS parcalari -> ${route.tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join("")} | route.points.forEach(([lat, lon]) => {
  - L1381-L1440: UI/stil/markup icerigi
  - L1441-L1500: UI/JS parcalari -> function showTimelinePlanner() { | const points = selectedPoints.map((point, index) => ({
  - L1501-L1560: UI/JS parcalari -> function calculateSegmentDistances() { | function displayTimeline(timeline) {
  - L1561-L1620: UI/JS parcalari -> timeline.schedule.forEach((item, index) => { | ${item.weather.advice.items.map(a =>
  - L1621-L1680: UI/JS parcalari -> locationIconBtns.forEach(b => b.classList.remove("active")); | function closeSaveLocationModal() {
  - L1681-L1740: UI/stil/markup icerigi
  - L1741-L1800: UI/JS parcalari -> function displaySavedLocationsSidebar(locations) { | locations.forEach(loc => {
  - L1801-L1860: UI/JS parcalari -> function drawSavedLocationsOnMap(locations) { | locations.forEach(loc => {
  - L1861-L1920: UI/JS parcalari -> function clearSavedLocationMarkers() { | customLocationMarkers.forEach(m => map.removeLayer(m)); | function toggleSavedLocationsVisibility() {
  - L1921-L1980: UI/stil/markup icerigi
  - L1981-L2040: UI/JS parcalari -> _weatherHideTimer = setTimeout(() => { | function initWeatherWidget() { | function formatLocalDateISO(date) {
  - L2041-L2100: UI/JS parcalari -> const updatePreference = () => { | const pointsPayload = points.map((p, i) => ({
  - L2101-L2160: UI/JS parcalari -> function showWeatherBanner(routeWeather, criticalAdvice = null) { | routeWeather.forEach(rw => { | advice.items.forEach(item => {
  - L2161-L2220: UI/JS parcalari -> function hideWeatherBanner() { | function initializeRegionDropdown() { | Object.keys(turkiyeData).forEach(region => {
  - L2221-L2280: UI/JS parcalari -> Object.keys(provinces).forEach(province => { | districts.forEach(district => {
  - L2281-L2340: UI/JS parcalari -> function displayRouteSteps(steps) { | elTurnByTurnList.innerHTML = steps.map((s,i)=>`<div class="turn-step"><strong>${i+1}.</strong> ${escapeHtml(s.instruc... | function startVoicePlayback() {
  - L2341-L2400: UI/JS parcalari -> function stopVoicePlayback() { | function normalizePoiConfidenceScore(poi) { | function ensureRouteDecisionPanel() {
  - L2401-L2460: UI/JS parcalari -> function summarizeWeatherForDecision(routeWeather, criticalAdvice) { | routeWeather.forEach((rw) => {
  - L2461-L2520: UI/JS parcalari -> function buildShortDistanceOverlapWarning(alternatives) { | const closeAlternatives = alternatives.slice(1).filter((alt) => { | function ensurePoiFilterPanel() {
  - L2521-L2580: UI/JS parcalari -> function applyPoiFilters() { | poiMarkers.forEach((marker) => { | poiMarkers.forEach((marker, idx) => {
  - L2581-L2620: UI/JS parcalari -> Array.from(categories).forEach((cat) => {

### 108. `frontend/openrouter-chat.html`
- Satir sayisi: 744
- Boyut: 25154 bayt
- Ilk anlamli satir: <!doctype html>
- Son anlamli satir: </html>
- Satir araligi incelemesi:
  - L1-L60: UI/JS parcalari -> .shell { | .header { | .title {
  - L61-L120: UI/JS parcalari -> .status { | .dot { | .dot.ok {
  - L121-L180: UI/JS parcalari -> .user { | .assistant { | .meta {
  - L181-L240: UI/JS parcalari -> .health-row { | .pill { | .pill-ok { background: rgba(34,197,94,0.18); color: #86efac; }
  - L241-L300: UI/JS parcalari -> .user { margin-left: 6%; } | .assistant { margin-right: 6%; } | .composer { grid-template-columns: 1fr; }
  - L301-L360: UI/stil/markup icerigi
  - L361-L420: UI/JS parcalari -> function setStatus(ok, text) { | function setActiveModel(model, triedModels) { | function addOptionIfMissing(model) {
  - L421-L480: UI/JS parcalari -> function classifyModelForSelection(model) { | function refreshModelOptions() { | const addModel = (model) => {
  - L481-L540: UI/JS parcalari -> function classifyError(errorText) { | function renderHealth() { | const print = (setObj) => {
  - L541-L600: UI/JS parcalari -> function appendMeta(target, text) { | function toggleUi(isBusy) {
  - L601-L660: UI/stil/markup icerigi
  - L661-L720: UI/stil/markup icerigi
  - L721-L744: UI/JS parcalari -> clearBtn.addEventListener("click", () => { | inputEl.addEventListener("keydown", (e) => {

### 109. `frontend/test-dropdown.html`
- Satir sayisi: 127
- Boyut: 5268 bayt
- Ilk anlamli satir: <!DOCTYPE html>
- Son anlamli satir: </html>
- Satir araligi incelemesi:
  - L1-L60: UI/JS parcalari -> function initializeRegionDropdown() { | Object.keys(turkiyeData).forEach(region => { | .info { background: #f0f0f0; padding: 10px; margin: 10px 0; }
  - L61-L120: UI/JS parcalari -> Object.keys(provinces).forEach(province => { | districts.forEach(district => {
  - L121-L127: UI/stil/markup icerigi

### 110. `frontend/test_encoding.html`
- Satir sayisi: 72
- Boyut: 2151 bayt
- Ilk anlamli satir: <!DOCTYPE html>
- Son anlamli satir: </html>
- Satir araligi incelemesi:
  - L1-L60: UI/JS parcalari -> .test-box { | .success { color: #00b894; } | .fail { color: #ff6b6b; }
  - L61-L72: UI/stil/markup icerigi

### 111. `frontend/test_timeline.html`
- Satir sayisi: 55
- Boyut: 1961 bayt
- Ilk anlamli satir: <!DOCTYPE html>
- Son anlamli satir: </html>
- Satir araligi incelemesi:
  - L1-L55: UI/stil/markup icerigi

### 112. `gÃ¼nlÃ¼k-rapor/03.03.2026/03.03.2026-gÃ¼n-sonu.txt`
- Durum: Dosya git'te takipli ama yerelde bulunamadi.

### 113. `gÃ¼nlÃ¼k-rapor/03.03.2026/03.03.2026.txt`
- Durum: Dosya git'te takipli ama yerelde bulunamadi.

### 114. `gÃ¼nlÃ¼k-rapor/04.03.2026/04.03.2026.txt`
- Durum: Dosya git'te takipli ama yerelde bulunamadi.

### 115. `gÃ¼nlÃ¼k-rapor/07.03.2026/07.03.2026.txt`
- Durum: Dosya git'te takipli ama yerelde bulunamadi.

### 116. `gÃ¼nlÃ¼k-rapor/08.03.2026/08.03.2026.txt`
- Durum: Dosya git'te takipli ama yerelde bulunamadi.

### 117. `gÃ¼nlÃ¼k-rapor/09.03.2026/09.03.2026.txt`
- Durum: Dosya git'te takipli ama yerelde bulunamadi.

### 118. `gÃ¼nlÃ¼k-rapor/11.03.2026/11.03.2026.txt`
- Durum: Dosya git'te takipli ama yerelde bulunamadi.

### 119. `gÃ¼nlÃ¼k-rapor/15.03.2026/15.03.2026.txt`
- Durum: Dosya git'te takipli ama yerelde bulunamadi.

### 120. `gÃ¼nlÃ¼k-rapor/27.02.2026/27.02.2026-akÅŸam.txt`
- Durum: Dosya git'te takipli ama yerelde bulunamadi.

### 121. `gÃ¼nlÃ¼k-rapor/27.02.2026/27.02.2026.txt`
- Durum: Dosya git'te takipli ama yerelde bulunamadi.

### 122. `gÃ¼nlÃ¼k-rapor/28.02.2026/28.02.2026-akÅŸam-2.txt`
- Durum: Dosya git'te takipli ama yerelde bulunamadi.

### 123. `gÃ¼nlÃ¼k-rapor/28.02.2026/28.02.2026-akÅŸam-3.txt`
- Durum: Dosya git'te takipli ama yerelde bulunamadi.

### 124. `gÃ¼nlÃ¼k-rapor/28.02.2026/28.02.2026-akÅŸam.txt`
- Durum: Dosya git'te takipli ama yerelde bulunamadi.

### 125. `gÃ¼nlÃ¼k-rapor/28.02.2026/28.02.2026-gece.txt`
- Durum: Dosya git'te takipli ama yerelde bulunamadi.

### 126. `gÃ¼nlÃ¼k-rapor/28.02.2026/28.02.2026-sabah.txt`
- Durum: Dosya git'te takipli ama yerelde bulunamadi.

### 127. `openrouter-model-envanteri.txt`
- Satir sayisi: 85
- Boyut: 3781 bayt
- Ilk anlamli satir: ﻿OpenRouter Model Envanteri (Kullanici Tarafindan Gonderilenler)
- Son anlamli satir: - https://openrouter.ai/meta-llama/llama-3.2-3b-instruct:free
- Satir araligi incelemesi:
  - L1-L60: metin/rapor icerigi
  - L61-L85: metin/rapor icerigi

### 128. `progress.md`
- Satir sayisi: 333
- Boyut: 12419 bayt
- Ilk anlamli satir: ﻿# Progress - OpenRoutePlanner (Detayli Turkce Rapor)
- Son anlamli satir: OpenRouter entegrasyonu artık sadece "mesaj atan" bir yapı değildir; model davranışını gözlemleyebilen, hata tiplerin...
- Satir araligi incelemesi:
  - L1-L60: basliklar -> ## 0) Bu rapor neden yeniden yazıldı?; ## 1) Üst Seviye Hedefler (Dönemin ana amacı); ## 2) Son 5 commitin çok detaylı Türkçe açıklaması; ### 2.1) `820817b`
  - L61-L120: basliklar -> #### B) API endpointleri (app.py); #### C) Global system prompt; #### D) Frontend canlı chat ekranı; #### E) Hata kategorileri ve kullanıcı deneyimi
  - L121-L180: basliklar -> ### 2.3) `5523adb`; ### 2.4) `875270d`; ### 2.5) `8f34aec`; ## 3) OpenRouter entegrasyonu - Teknik mimari özeti
  - L181-L240: basliklar -> ### 3.3) Hata kodlarının anlamı; ### 3.4) Neden bazı modeller cevap dönmüyor?; ## 4) Arayüz tarafında yapılan ana UX kararları; ### 4.1) Sadece model listesi yetmiyor
  - L241-L300: basliklar -> ## 6) Test ve doğrulama özeti; ## 7) Karşılaşılan gerçek saha sorunları ve alınan aksiyonlar; ### Sorun 1: Free modellerde yüksek 429; ### Sorun 2: Embedding modelinin chat'e gönderilmesi
  - L301-L333: basliklar -> ## 10) Sonraki sprint için net görev listesi; ## 11) İletişim ve çalışma kuralı notu; ## 12) Kısa sonuç cümlesi

### 129. `pytest.ini`
- Satir sayisi: 11
- Boyut: 214 bayt
- Ilk anlamli satir: [pytest]
- Son anlamli satir: --tb=short
- Satir araligi incelemesi:
  - L1-L11: genel icerik

### 130. `requirements.txt`
- Satir sayisi: 23
- Boyut: 708 bayt
- Ilk anlamli satir: flask==3.1.0
- Son anlamli satir: pydantic-settings==2.6.1
- Satir araligi incelemesi:
  - L1-L23: basliklar -> # Flask-Compress codec backend'lerini sabit tutuyoruz.; # brotlicffi yerine brotli kullanimi hedeflenir (urllib3 uyumlulugu).; # PyTorch CUDA 13.0 için manuel kurulum gereklidir:; # pip uninstall torch -y

### 131. `scripts/fix/fix_backend.py`
- Satir sayisi: 93
- Boyut: 2300 bayt
- Python ozeti: import=2, sinif=0, fonksiyon=0, flask_route=0
- Ilk anlamli satir: #!/usr/bin/env python3
- Son anlamli satir: print("2. Tarayıcıda Hard Refresh: Ctrl+Shift+R")
- Satir araligi incelemesi:
  - L1-L60: yardimci/degisken/akis kodu
  - L61-L93: yardimci/degisken/akis kodu

### 132. `scripts/fix/fix_emoji.py`
- Satir sayisi: 60
- Boyut: 1422 bayt
- Python ozeti: import=1, sinif=0, fonksiyon=0, flask_route=0
- Ilk anlamli satir: #!/usr/bin/env python3
- Son anlamli satir: print("=" * 80)
- Satir araligi incelemesi:
  - L1-L60: yardimci/degisken/akis kodu

### 133. `scripts/fix/fix_encoding.py`
- Satir sayisi: 247
- Boyut: 8287 bayt
- Python ozeti: import=4, sinif=0, fonksiyon=6, flask_route=0
- Fonksiyonlar:
  - L32: has_replacement_char
  - L39: fix_mojibake
  - L47: fix_file
  - L102: check_file
  - L153: scan_files
  - L174: main
- Ilk anlamli satir: #!/usr/bin/env python3
- Son anlamli satir: sys.exit(main())
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=has_replacement_char, fix_mojibake, fix_file
  - L61-L120: fonksiyonlar=check_file
  - L121-L180: fonksiyonlar=scan_files, main
  - L181-L240: yardimci/degisken/akis kodu
  - L241-L247: yardimci/degisken/akis kodu

### 134. `scripts/fix/fix_encoding_aggressive.py`
- Satir sayisi: 85
- Boyut: 2702 bayt
- Python ozeti: import=2, sinif=0, fonksiyon=2, flask_route=0
- Fonksiyonlar:
  - L8: try_decode
  - L24: fix_all_backend_files
- Ilk anlamli satir: #!/usr/bin/env python3
- Son anlamli satir: fix_all_backend_files()
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=try_decode, fix_all_backend_files
  - L61-L85: yardimci/degisken/akis kodu

### 135. `scripts/fix/fix_osmnx.bat`
- Satir sayisi: 27
- Boyut: 642 bayt
- Ilk anlamli satir: @echo off
- Son anlamli satir: pause
- Satir araligi incelemesi:
  - L1-L27: genel icerik

### 136. `scripts/monitor_gpu.py`
- Satir sayisi: 91
- Boyut: 2954 bayt
- Python ozeti: import=7, sinif=0, fonksiyon=2, flask_route=0
- Fonksiyonlar:
  - L8: get_gpu_memory
  - L21: test_bert_on_gpu
- Ilk anlamli satir: """
- Son anlamli satir: test_bert_on_gpu()
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=get_gpu_memory, test_bert_on_gpu
  - L61-L91: yardimci/degisken/akis kodu

### 137. `scripts/tools/deep_scan.py`
- Satir sayisi: 89
- Boyut: 2851 bayt
- Python ozeti: import=2, sinif=0, fonksiyon=0, flask_route=0
- Ilk anlamli satir: #!/usr/bin/env python3
- Son anlamli satir: print("✅ TÜM DOSYALAR TEMİZ!")
- Satir araligi incelemesi:
  - L1-L60: yardimci/degisken/akis kodu
  - L61-L89: yardimci/degisken/akis kodu

### 138. `scripts/tools/download_istanbul.py`
- Satir sayisi: 29
- Boyut: 1095 bayt
- Python ozeti: import=3, sinif=0, fonksiyon=1, flask_route=0
- Fonksiyonlar:
  - L11: download_istanbul
- Ilk anlamli satir: import os
- Son anlamli satir: print("\nTest bitti.")
- Satir araligi incelemesi:
  - L1-L29: fonksiyonlar=download_istanbul

### 139. `scripts/tools/download_maps.py`
- Satir sayisi: 35
- Boyut: 1421 bayt
- Python ozeti: import=3, sinif=0, fonksiyon=1, flask_route=0
- Fonksiyonlar:
  - L11: download_maps
- Ilk anlamli satir: import os
- Son anlamli satir: print("\nTest tamamlandı. 'backend/data/' klasörünü kontrol ederek indirilen .graphml boyutlarına bakabiliriz.")
- Satir araligi incelemesi:
  - L1-L35: fonksiyonlar=download_maps

### 140. `scripts/tools/evaluate_bert_gold.py`
- Satir sayisi: 350
- Boyut: 13099 bayt
- Python ozeti: import=11, sinif=0, fonksiyon=8, flask_route=0
- Fonksiyonlar:
  - L42: normalize_text
  - L52: fuzzy_match
  - L66: match_list
  - L84: percentile
  - L99: load_dataset
  - L116: evaluate_case
  - L138: append_confusion_cell
  - L147: main
- Ilk anlamli satir: """
- Son anlamli satir: raise SystemExit(main())
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=normalize_text, fuzzy_match
  - L61-L120: fonksiyonlar=match_list, percentile, load_dataset, evaluate_case
  - L121-L180: fonksiyonlar=append_confusion_cell, main
  - L181-L240: yardimci/degisken/akis kodu
  - L241-L300: yardimci/degisken/akis kodu
  - L301-L350: yardimci/degisken/akis kodu

### 141. `scripts/tools/generate_icons.py`
- Satir sayisi: 56
- Boyut: 3288 bayt
- Python ozeti: import=4, sinif=0, fonksiyon=0, flask_route=0
- Ilk anlamli satir: import sys
- Son anlamli satir: print(f"Generated {len(html_buttons)} buttons in tmp_buttons.html")
- Satir araligi incelemesi:
  - L1-L56: yardimci/degisken/akis kodu

### 142. `scripts/tools/optimize_model.py`
- Satir sayisi: 76
- Boyut: 2678 bayt
- Python ozeti: import=5, sinif=0, fonksiyon=0, flask_route=0
- Ilk anlamli satir: #!/usr/bin/env python3
- Son anlamli satir: print('[optimize_model] Done')
- Satir araligi incelemesi:
  - L1-L60: yardimci/degisken/akis kodu
  - L61-L76: yardimci/degisken/akis kodu

### 143. `scripts/tools/ornek_bert_kullanimi.py`
- Satir sayisi: 67
- Boyut: 2730 bayt
- Python ozeti: import=2, sinif=0, fonksiyon=0, flask_route=0
- Ilk anlamli satir: from transformers import pipeline
- Son anlamli satir: print("="*60)
- Satir araligi incelemesi:
  - L1-L60: yardimci/degisken/akis kodu
  - L61-L67: yardimci/degisken/akis kodu

### 144. `scripts/tools/scan_encoding.py`
- Satir sayisi: 70
- Boyut: 1818 bayt
- Python ozeti: import=2, sinif=0, fonksiyon=0, flask_route=0
- Ilk anlamli satir: #!/usr/bin/env python3
- Son anlamli satir: print("   python scripts/fix/fix_backend.py")
- Satir araligi incelemesi:
  - L1-L60: yardimci/degisken/akis kodu
  - L61-L70: yardimci/degisken/akis kodu

### 145. `scripts/tools/seed_places.py`
- Satir sayisi: 91
- Boyut: 3651 bayt
- Python ozeti: import=9, sinif=0, fonksiyon=0, flask_route=0
- Ilk anlamli satir: #!/usr/bin/env python3
- Son anlamli satir: sys.exit(2)
- Satir araligi incelemesi:
  - L1-L60: yardimci/degisken/akis kodu
  - L61-L91: yardimci/degisken/akis kodu

### 146. `scripts/tools/test_100_routes.py`
- Satir sayisi: 422
- Boyut: 14877 bayt
- Python ozeti: import=6, sinif=0, fonksiyon=9, flask_route=0
- Fonksiyonlar:
  - L85: generate_test_routes
  - L105: geocode_place
  - L119: calculate_route
  - L135: get_alternative_routes
  - L151: calculate_overlap_ratio
  - L167: score_alternative_routes
  - L208: run_single_test
  - L295: analyze_results
  - L346: main
- Ilk anlamli satir: """
- Son anlamli satir: main()
- Satir araligi incelemesi:
  - L1-L60: yardimci/degisken/akis kodu
  - L61-L120: fonksiyonlar=generate_test_routes, geocode_place, calculate_route
  - L121-L180: fonksiyonlar=get_alternative_routes, calculate_overlap_ratio, score_alternative_routes
  - L181-L240: fonksiyonlar=run_single_test
  - L241-L300: fonksiyonlar=analyze_results
  - L301-L360: fonksiyonlar=main
  - L361-L420: yardimci/degisken/akis kodu
  - L421-L422: yardimci/degisken/akis kodu

### 147. `scripts/tools/test_routes_fast.py`
- Satir sayisi: 182
- Boyut: 5943 bayt
- Python ozeti: import=4, sinif=0, fonksiyon=3, flask_route=0
- Fonksiyonlar:
  - L48: geocode
  - L59: run_route
  - L133: main
- Ilk anlamli satir: """
- Son anlamli satir: main()
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=geocode, run_route
  - L61-L120: yardimci/degisken/akis kodu
  - L121-L180: fonksiyonlar=main
  - L181-L182: yardimci/degisken/akis kodu

### 148. `scripts/tools/update_ui.py`
- Satir sayisi: 42
- Boyut: 1664 bayt
- Python ozeti: import=3, sinif=0, fonksiyon=0, flask_route=0
- Ilk anlamli satir: import re
- Son anlamli satir: print("index.html and style.css updated successfully.")
- Satir araligi incelemesi:
  - L1-L42: yardimci/degisken/akis kodu

### 149. `tests/__init__.py`
- Satir sayisi: 3
- Boyut: 39 bayt
- Python ozeti: import=0, sinif=0, fonksiyon=0, flask_route=0
- Ilk anlamli satir: """
- Son anlamli satir: """
- Satir araligi incelemesi:
  - L1-L3: yardimci/degisken/akis kodu

### 150. `tests/data/bert_gold_tr_v1.jsonl`
- Satir sayisi: 24
- Boyut: 3575 bayt
- Ilk anlamli satir: {"id":"tr_route_001","query":"Kadıköy'den Beşiktaş'a rota çiz","expected":{"type":"route","origin":"kadıköy","destina...
- Son anlamli satir: {"id":"tr_unknown_002","query":"Merhaba nasılsın","expected":{"type":"unknown"},"tags":["unknown","chitchat"]}
- Satir araligi incelemesi:
  - L1-L24: veri satirlari/json icerigi

### 151. `tests/data/intent_hard_negative_tr_v1.jsonl`
- Satir sayisi: 5
- Boyut: 362 bayt
- Ilk anlamli satir: {"id":"hn_001","query":"Merhaba nasilsin","expected":{"type":"unknown"}}
- Son anlamli satir: {"id":"hn_005","query":"Bugun hava nasil","expected":{"type":"unknown"}}
- Satir araligi incelemesi:
  - L1-L5: veri satirlari/json icerigi

### 152. `tests/test_api/__init__.py`
- Satir sayisi: 3
- Boyut: 30 bayt
- Python ozeti: import=0, sinif=0, fonksiyon=0, flask_route=0
- Ilk anlamli satir: """
- Son anlamli satir: """
- Satir araligi incelemesi:
  - L1-L3: yardimci/degisken/akis kodu

### 153. `tests/test_api/test_openrouter_api.py`
- Satir sayisi: 89
- Boyut: 3330 bayt
- Python ozeti: import=3, sinif=0, fonksiyon=8, flask_route=0
- Fonksiyonlar:
  - L10: _client_with_env
  - L16: test_openrouter_status_not_configured
  - L28: test_openrouter_chat_requires_query_or_messages
  - L37: test_openrouter_chat_success_with_query
  - L41: _fake_chat_completion
  - L61: test_openrouter_chat_stream_requires_query_or_messages
  - L70: test_openrouter_chat_stream_success
  - L74: _fake_stream
- Ilk anlamli satir: import importlib
- Son anlamli satir: assert '"type": "done"' in text
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=_client_with_env, test_openrouter_status_not_configured, test_openrouter_chat_requires_query_or_messages, test_openrouter_chat_success_with_query, _fake_chat_completion
  - L61-L89: fonksiyonlar=test_openrouter_chat_stream_requires_query_or_messages, test_openrouter_chat_stream_success, _fake_stream

### 154. `tests/test_api/test_poi_api.py`
- Satir sayisi: 68
- Boyut: 2066 bayt
- Python ozeti: import=4, sinif=0, fonksiyon=5, flask_route=0
- Fonksiyonlar:
  - L15: client
  - L22: test_search_pois_resolves_category_with_morph_dict
  - L25: fake_search_pois
  - L49: test_search_pois_keeps_unknown_category
  - L52: fake_search_pois
- Ilk anlamli satir: """
- Son anlamli satir: assert captured["category"] == "xzy-bilinmeyen"
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=client, test_search_pois_resolves_category_with_morph_dict, fake_search_pois, test_search_pois_keeps_unknown_category, fake_search_pois
  - L61-L68: yardimci/degisken/akis kodu

### 155. `tests/test_api/test_routes.py`
- Satir sayisi: 182
- Boyut: 5707 bayt
- Python ozeti: import=4, sinif=1, fonksiyon=13, flask_route=0
- Siniflar:
  - L28: _StubNlpEngine
- Fonksiyonlar:
  - L18: client
  - L29: parse
  - L70: test_health_endpoint
  - L80: test_trace_headers_preserve_incoming_request_id
  - L94: test_nlp_status
  - L104: test_nlp_parse_with_query
  - L119: test_nlp_parse_empty_query
  - L127: test_nlp_parse_non_string_query
  - L137: test_geocode_forward
  - L147: test_geocode_reverse
  - L156: test_locations_list
  - L164: test_routes_list
  - L172: test_routes_statistics
- Ilk anlamli satir: """
- Son anlamli satir: pytest.main([__file__, '-v'])
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=client, parse | siniflar=_StubNlpEngine
  - L61-L120: fonksiyonlar=test_health_endpoint, test_trace_headers_preserve_incoming_request_id, test_nlp_status, test_nlp_parse_with_query, test_nlp_parse_empty_query
  - L121-L180: fonksiyonlar=test_nlp_parse_non_string_query, test_geocode_forward, test_geocode_reverse, test_locations_list, test_routes_list, test_routes_statistics
  - L181-L182: yardimci/degisken/akis kodu

### 156. `tests/test_core/__init__.py`
- Satir sayisi: 3
- Boyut: 29 bayt
- Python ozeti: import=0, sinif=0, fonksiyon=0, flask_route=0
- Ilk anlamli satir: """
- Son anlamli satir: """
- Satir araligi incelemesi:
  - L1-L3: yardimci/degisken/akis kodu

### 157. `tests/test_core/test_bert_nlp_preprocessing.py`
- Satir sayisi: 122
- Boyut: 3602 bayt
- Python ozeti: import=3, sinif=0, fonksiyon=11, flask_route=0
- Fonksiyonlar:
  - L26: test_plain_loc_suffix_does_not_trim_short_place_name
  - L32: test_plain_loc_suffix_trims_long_token
  - L38: test_noise_word_gidelim_filtered_from_spans
  - L44: test_noise_word_dolas_filtered_from_multi_query
  - L51: test_action_token_ariyorum_detected
  - L56: test_poi_concept_term_detects_cami
  - L60: test_extract_poi_concept_ignores_detected_location_span
  - L68: test_intent_conflict_matrix_promotes_poi_over_single_without_direction
  - L83: test_intent_conflict_matrix_promotes_route_when_direction_present
  - L99: test_prefetch_osm_candidates_respects_zero_budget
  - L114: fake_cache
- Ilk anlamli satir: """
- Son anlamli satir: assert calls["count"] == 0
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=test_plain_loc_suffix_does_not_trim_short_place_name, test_plain_loc_suffix_trims_long_token, test_noise_word_gidelim_filtered_from_spans, test_noise_word_dolas_filtered_from_multi_query, test_action_token_ariyorum_detected, test_poi_concept_term_detects_cami, test_extract_poi_concept_ignores_detected_location_span
  - L61-L120: fonksiyonlar=test_intent_conflict_matrix_promotes_poi_over_single_without_direction, test_intent_conflict_matrix_promotes_route_when_direction_present, test_prefetch_osm_candidates_respects_zero_budget, fake_cache
  - L121-L122: yardimci/degisken/akis kodu

### 158. `tests/test_core/test_graph_manager_poi_fallback.py`
- Satir sayisi: 62
- Boyut: 2369 bayt
- Python ozeti: import=3, sinif=1, fonksiyon=6, flask_route=0
- Siniflar:
  - L14: DummyGDF
- Fonksiyonlar:
  - L15: __init__
  - L18: __len__
  - L22: test_fetch_pois_requires_geobound_center
  - L36: test_fetch_pois_fallback_order_a_then_b
  - L41: fake_point
  - L56: test_search_pois_by_tags_returns_empty_when_all_fallbacks_fail
- Ilk anlamli satir: """
- Son anlamli satir: assert result == []
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=__init__, __len__, test_fetch_pois_requires_geobound_center, test_fetch_pois_fallback_order_a_then_b, fake_point, test_search_pois_by_tags_returns_empty_when_all_fallbacks_fail | siniflar=DummyGDF
  - L61-L62: yardimci/degisken/akis kodu

### 159. `tests/test_core/test_intent_template_bundle.py`
- Satir sayisi: 57
- Boyut: 1692 bayt
- Python ozeti: import=7, sinif=0, fonksiyon=3, flask_route=0
- Fonksiyonlar:
  - L23: test_load_intent_template_bundle_from_file
  - L44: test_should_force_unknown_with_hard_negative_true
  - L52: test_should_force_unknown_with_hard_negative_false
- Ilk anlamli satir: """
- Son anlamli satir: ) is False
- Satir araligi incelemesi:
  - L1-L57: fonksiyonlar=test_load_intent_template_bundle_from_file, test_should_force_unknown_with_hard_negative_true, test_should_force_unknown_with_hard_negative_false

### 160. `tests/test_core/test_nlp_engine_poi_patterns.py`
- Satir sayisi: 24
- Boyut: 701 bayt
- Python ozeti: import=3, sinif=0, fonksiyon=2, flask_route=0
- Fonksiyonlar:
  - L14: test_parse_query_poi_with_location_and_search_phrase
  - L21: test_parse_query_poi_with_recommendation_phrase
- Ilk anlamli satir: """
- Son anlamli satir: assert result.get("poi_concept") == "pilavcı"
- Satir araligi incelemesi:
  - L1-L24: fonksiyonlar=test_parse_query_poi_with_location_and_search_phrase, test_parse_query_poi_with_recommendation_phrase

### 161. `tests/test_core/test_poi_cache_version_token.py`
- Satir sayisi: 25
- Boyut: 720 bayt
- Python ozeti: import=3, sinif=0, fonksiyon=1, flask_route=0
- Fonksiyonlar:
  - L14: test_poi_cache_isolated_by_version_token
- Ilk anlamli satir: """
- Son anlamli satir: assert hit == [{"id": 1}]
- Satir araligi incelemesi:
  - L1-L25: fonksiyonlar=test_poi_cache_isolated_by_version_token

### 162. `tests/test_core/test_poi_concept_resolver.py`
- Satir sayisi: 75
- Boyut: 2289 bayt
- Python ozeti: import=4, sinif=0, fonksiyon=9, flask_route=0
- Fonksiyonlar:
  - L22: test_resolve_plural_case_suffix_to_pilavci
  - L29: test_resolve_latinized_variant_to_pilavci
  - L35: test_unknown_surface_stays_unknown
  - L41: test_extract_poi_concept_with_meta_ignores_location_span
  - L50: test_resolve_from_tokens_prefers_multiword_when_exists
  - L56: test_extract_candidates_contains_morph_forms
  - L61: test_normalize_poi_concept_returns_canonical
  - L65: test_resolve_query_returns_osm_queries
  - L73: test_map_concept_to_osm_queries_fallback_name
- Ilk anlamli satir: """
- Son anlamli satir: assert queries == [{"name": "xzy bilinmeyen"}]
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=test_resolve_plural_case_suffix_to_pilavci, test_resolve_latinized_variant_to_pilavci, test_unknown_surface_stays_unknown, test_extract_poi_concept_with_meta_ignores_location_span, test_resolve_from_tokens_prefers_multiword_when_exists, test_extract_candidates_contains_morph_forms
  - L61-L75: fonksiyonlar=test_normalize_poi_concept_returns_canonical, test_resolve_query_returns_osm_queries, test_map_concept_to_osm_queries_fallback_name

### 163. `tests/test_core/test_route_engine.py`
- Satir sayisi: 133
- Boyut: 4653 bayt
- Python ozeti: import=18, sinif=4, fonksiyon=15, flask_route=0
- Siniflar:
  - L16: TestOverlapThresholds
  - L44: TestMaxCandidates
  - L72: TestConfigIntegration
  - L104: TestEdgeOverlap
- Fonksiyonlar:
  - L19: test_overlap_very_short_distance
  - L25: test_overlap_short_distance
  - L31: test_overlap_medium_distance
  - L37: test_overlap_long_distance
  - L47: test_max_candidates_very_short
  - L53: test_max_candidates_short
  - L59: test_max_candidates_medium
  - L65: test_max_candidates_long
  - L75: test_walk_speed_from_config
  - L81: test_overlap_thresholds_in_config
  - L89: test_max_candidates_in_config
  - L97: test_penalty_factor_in_config
  - L107: test_no_overlap
  - L115: test_full_overlap
  - L123: test_partial_overlap
- Ilk anlamli satir: """
- Son anlamli satir: pytest.main([__file__, '-v'])
- Satir araligi incelemesi:
  - L1-L60: fonksiyonlar=test_overlap_very_short_distance, test_overlap_short_distance, test_overlap_medium_distance, test_overlap_long_distance, test_max_candidates_very_short, test_max_candidates_short, test_max_candidates_medium | siniflar=TestOverlapThresholds, TestMaxCandidates
  - L61-L120: fonksiyonlar=test_max_candidates_long, test_walk_speed_from_config, test_overlap_thresholds_in_config, test_max_candidates_in_config, test_penalty_factor_in_config, test_no_overlap, test_full_overlap | siniflar=TestConfigIntegration, TestEdgeOverlap
  - L121-L133: fonksiyonlar=test_partial_overlap

## 3) Genel Tespitler
- Proje backend agirlikli (Flask + NLP + rota + hava durumu + OpenRouter).
- Frontend tarafinda tek sayfa + yardimci test/lab sayfalari var.
- Dokumantasyon kapsamli ancak bazi dosyalarda encoding/miras icerik birikimi var.
- Test klasoru hem API hem core katmaninda anlamli kapsama sahip.

## 4) Sonraki Aksiyon Onerisi
1. progress.md icindeki bu raporu bolumlere ayirip (backend/frontend/docs/test) daha hizli gezilebilir hale getirme.
2. encoding standardizasyonu (UTF-8) icin tek seferlik duzenleme.
3. CI test rapor ozetini progress.md'ye otomatik ekleyen script.
4. model hata istatistiklerini kalici loglama.
