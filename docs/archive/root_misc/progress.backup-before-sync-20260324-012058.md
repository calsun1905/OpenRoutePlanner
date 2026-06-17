# Progress - OpenRoutePlanner (Detayli Turkce Rapor)

Tarih: 2026-03-24
Ana Dal: main
Rapor Tipi: Teknik + Operasyonel + Karar Geçmişi + Sonraki Yol Haritası
Hazırlayan: Codex oturumu

---

## 0) Bu rapor neden yeniden yazıldı?
Bu dosya tamamen Türkçe, detaylı ve geçmişle tutarlı olacak şekilde yeniden düzenlendi. Amaç sadece "ne değişti" demek değil; aynı zamanda:
- Hangi problemi neden yaşadık,
- Hangi adımın neyi çözdüğünü,
- Nerede teknik sınırlara takıldığımızı,
- Hangi kararları bilinçli aldığımızı,
- Sonraki çalışmada ne yapılması gerektiğini,

tek bir yerde anlaşılır hale getirmektir.

Bu rapor özellikle OpenRouter canlı sohbet entegrasyonu, model seçimi, fallback davranışı, hata sınıflandırması ve kullanıcı deneyimi (UI/UX) tarafındaki tüm güncel durumu kapsar.

---

## 1) Üst Seviye Hedefler (Dönemin ana amacı)
Bu dönem boyunca ana hedefler aşağıdaki gibi netleştirildi:

1. OpenRouter API ile canlı (stream) sohbeti sorunsuz çalıştırmak.
2. Model seçiminde kullanıcıya gerçek kontrol vermek.
3. Otomatik fallback ile manuel tek-model davranışını birbirinden ayırmak.
4. 429/402/400 gibi hataları saklamak yerine görünür ve yönetilebilir hale getirmek.
5. Tekrarlanan sorunları azaltmak için kategorik model ayrımı ve canlı durum paneli eklemek.
6. Tüm modellere uygulanacak tutarlı bir global system prompt tanımlamak.
7. Teknik çıktıları testle doğrulamak ve CI kapsamına dahil etmek.
8. Repo tarafında gereksiz lokal/artifact dosyalarını kontrol altında tutmak.

---

## 2) Son 5 commitin çok detaylı Türkçe açıklaması

Aşağıda son 5 commit, kronolojik ve teknik bağlamıyla birlikte açıklanmıştır.

### 2.1) `820817b`  
**Başlık:** OpenRouter chat: fallback, model categorization UI, global system prompt

Bu commit bu dönemin ana teknik omurgasını oluşturur. Etkisi çok geniştir ve backend + frontend + test + dokümantasyon katmanlarını birlikte kapsar.

#### A) Backend tarafı (Flask API / OpenRouter servis katmanı)
- `backend/openrouter_service.py` eklendi.
- Bu modül tek noktadan OpenRouter çağrıları için altyapı sağladı:
  - Normal chat completion çağrısı,
  - Stream (token bazlı) çağrı,
  - Fallback zinciri yönetimi,
  - ENV tabanlı model/fallback/timeout yönetimi,
  - Hata ayrıştırma ve tekrar denenebilir hata sınıflandırması.

##### Eklenecek önemli teknik davranışlar:
- `.env` otomatik yükleme desteği (uygulama ayağa kalktığında temel env okuma rahatlığı).
- Model adı normalize etme (kullanıcı URL/slug karışık yazsa bile toparlama).
- Fallback model listesini parse etme ve duplicate temizleme.
- 429/5xx/404 guardrail vb. durumlarda bir sonraki modele geçebilme.

#### B) API endpointleri (app.py)
Aşağıdaki endpointler aktif hale getirildi:
- `GET /api/llm/openrouter/status`
- `POST /api/llm/openrouter/chat`
- `POST /api/llm/openrouter/chat/stream`
- `GET /api/llm/openrouter/models`

Bu endpointlerle:
- Konfigürasyon görünür oldu,
- Tek istek ve stream kullanım senaryoları ayrıştı,
- Manuel/otomatik fallback kontrolü açıldı,
- Model listesi istemciye taşındı.

#### C) Global system prompt
- Tüm OpenRouter isteklerine otomatik uygulanacak global system prompt eklendi.
- Amaç: Türkçe ve temiz çıktı kalitesini artırmak, bozuk karakter olasılığını düşürmek, gereksiz uzun cevabı frenlemek.
- Kural: Eğer kullanıcı zaten `system` role göndermişse üzerine yazma; yoksa ekle.

#### D) Frontend canlı chat ekranı
- `frontend/openrouter-chat.html` oluşturuldu.
- Özellikler:
  - Otomatik fallback modu,
  - Manuel tek model modu,
  - Kategoriye göre model seçimi,
  - Canlı model durumu paneli,
  - Modelin deneme sırası / aktif model görünürlüğü,
  - Hata durumlarını meta satırlarında okunabilir gösterim.

#### E) Hata kategorileri ve kullanıcı deneyimi
- Hata tipleri kullanıcıya anlamlı şekilde sunuldu:
  - `429`: limit/rate
  - `402`: kredi/ücret
  - `400`: endpoint/model tipi uyumsuz
- Model seçimi tarafında kategori yaklaşımı benimsendi:
  - Sorunsuz çalışanlar,
  - Tıkananlar,
  - Limit hatası alanlar,
  - Kredi isteyenler,
  - Embedding/VL (chat uyumsuz),
  - Diğer.

#### F) Test ve kalite
- `tests/test_api/test_openrouter_api.py` eklendi.
- Status/chat/stream endpointlerinin temel doğrulamaları yapıldı.
- Testler dönemde düzenli olarak 5/5 geçti.

#### G) Operasyonel dokümantasyon
- `openrouter-model-envanteri.txt` ile kullanıcı tarafından paylaşılan model URL/slug verileri kategorize edilerek korundu.
- Bu dosya ileride model stratejisi için veri kaynağı olarak kullanılabilir.

---

### 2.2) `f110106`  
**Başlık:** Initial commit

Bu commit tarihsel olarak başlangıç noktasıdır. Detay tarafında en önemli not:
- İlk kurulum döneminin doğal sonucu olarak ham/deneysel/lokal nitelikli dosyalar da bulunuyordu.
- Yani modern üretim standardı açısından "temiz" başlangıç değil, daha çok "çalışan başlangıç" karakterindeydi.

Bu bilgi önemli çünkü sonraki temizleme commitleri (özellikle .gitignore ve cache/artifact yönetimi) bu başlangıç borcunu kapatmak için atıldı.

---

### 2.3) `5523adb`  
**Başlık:** ci: broaden regression test coverage for core, api, nav, and weather

Bu commitin ana değeri:
- CI pipeline'da test kapsamının genişletilmesi.
- OpenRouter testlerinin de otomasyonda yer alması.

Neden kritik?
- Yerelde çalışan bir değişiklik, CI'da görünmeden üretime kayabilir.
- API davranışında geriye dönük kırılmaları erken yakalamak için test kapsamı şart.

Bu commitle birlikte OpenRouter entegrasyonu sadece "çalışıyor" değil, "testlenen" bir parçaya dönüştü.

---

### 2.4) `875270d`  
**Başlık:** chore(repo): remove tracked cache artifacts and standardize local config files

Ana hedef:
- Repoya yanlışlıkla giren cache/artifact dosyalarını temizlemek.
- Lokal geliştirici ayarlarını standardize etmek.

Bu commit neden değerli?
- Repo kirlenmesi ekip hızını düşürür.
- Gereksiz dosya takibi merge çakışmalarını artırır.
- Geliştirici makinesine özel dosyalar (local config/cache/db) takımda sorun çıkarır.

Özetle bu commit operasyonel hijyen commitidir.

---

### 2.5) `8f34aec`  
**Başlık:** chore(gitignore): ignore local tool artifacts

Bu commit küçük görünür ama etkisi büyüktür:
- Lokal araç çıktıları ignore altına alındı.
- "Neden bu dosya değişti?" karmaşasını azalttı.

Bu sayede:
- Commitler daha anlamlı,
- Diffler daha temiz,
- Kod inceleme daha hızlı hale geldi.

---

## 3) OpenRouter entegrasyonu - Teknik mimari özeti

### 3.1) Veri akışı
1. Kullanıcı frontend'de mesaj gönderir.
2. Frontend `/api/llm/openrouter/chat/stream` endpointine gider.
3. Backend mesajları kontrol eder, gerekiyorsa global system prompt ekler.
4. Manuel mod ise tek model, otomatik mod ise fallback zinciri işletilir.
5. Stream tokenları NDJSON olarak döner.
6. Frontend tokenları canlı birleştirir ve model durum panelini günceller.

### 3.2) Manuel vs Otomatik mod farkı
- Otomatik mod:
  - `use_fallback=true`
  - Başarısız modelde sıradaki modele geçebilir.
- Manuel mod:
  - `use_fallback=false`
  - Sadece seçilen modeli dener.

Bu ayrım, kullanıcıya test ve üretim davranışını ayrı ayrı kullanma imkânı verir.

### 3.3) Hata kodlarının anlamı
- 429: O anda provider yoğun, geçici.
- 402: Kredi/ücret gerekiyor.
- 400: Yanlış endpoint türü (ör: embedding modelini chat'e atmak).
- 404 (guardrail/data policy): Hesap/policy kısıtı kaynaklı olabilir.

### 3.4) Neden bazı modeller cevap dönmüyor?
- Free model kotası dolu olabilir (429).
- Hesapta kredi yoksa paid model cevap vermez (402).
- Model chat endpoint uyumlu değilse teknik olarak imkânsızdır (400).

Bu nedenle sorun her zaman "kod" değildir; çoğu zaman provider/policy/kredi kombinasyonudur.

---

## 4) Arayüz tarafında yapılan ana UX kararları

### 4.1) Sadece model listesi yetmiyor
Kullanıcının gerçek ihtiyacı "model adını görmek" değil, "hangi modelin neden çalışmadığını anlamak" olduğu için:
- Kategorik seçim alanı,
- Canlı model sağlık paneli,
- Hata sınıfına göre ayrım eklendi.

### 4.2) Neden kategori yaklaşımı?
Çünkü kullanıcı tarafında deneme sürecini hızlandırır:
- Çalışan modelleri hızlıca seçer,
- Limitte takılanları bekletir,
- Kredi isteyenleri eleyebilir,
- Embedding/VL modellerini chat'ten uzak tutar.

### 4.3) Tıkananlar kategorisi
Liquid modelleri özel istekle "tıkananlar" altında gruplanmıştır.
Ayrıca boş token/boş cevap akışlarında model otomatik bu kategoriye düşürülebilecek şekilde yapı kurulmuştur.

---

## 5) Konfigürasyon (ENV) stratejisi

### 5.1) Kritik ENV alanları
- `OPENROUTER_API_KEY`
- `OPENROUTER_BASE_URL`
- `OPENROUTER_MODEL`
- `OPENROUTER_FALLBACK_MODELS`
- `ORP_OPENROUTER_TIMEOUT_SEC`
- `OPENROUTER_HTTP_REFERER`
- `OPENROUTER_APP_TITLE`
- `OPENROUTER_SYSTEM_PROMPT` (override için)

### 5.2) Uygulama kuralı
- URL değil model slug kullan.
- Fallback listesinde chat dışı modeli mümkün olduğunca tutma.
- 402 verenleri manuel testte ayrı kategoriye it.

---

## 6) Test ve doğrulama özeti

Bu dönemde OpenRouter testleri düzenli çalıştırıldı ve geçti.
Öne çıkan doğrulamalar:
- status endpoint davranışı,
- chat endpoint input validasyonu,
- stream endpoint davranışı,
- fallback fonksiyonlarının entegrasyonu.

Özet: OpenRouter katmanı testlenebilir ve tekrar üretilebilir duruma getirildi.

---

## 7) Karşılaşılan gerçek saha sorunları ve alınan aksiyonlar

### Sorun 1: Free modellerde yüksek 429
Aksiyon:
- fallback zinciri eklendi,
- kategori ayrımı eklendi,
- kullanıcıya görünür teşhis paneli verildi.

### Sorun 2: Embedding modelinin chat'e gönderilmesi
Aksiyon:
- model envanteri ayrıştırıldı,
- endpoint uyumsuzları ayrı sınıfa alındı.

### Sorun 3: 402 kredi hataları
Aksiyon:
- paid/kredi isteyenler kategorik işaretlendi,
- manuel seçimde daha net ayrım sağlandı.

### Sorun 4: Karakter bozulması / kalite dalgalanması
Aksiyon:
- global system prompt eklendi,
- Türkçe + temiz UTF-8 + kısa/net üretim kuralı tanımlandı.

---

## 8) Güncel çalışma önerisi (pratik işletim)

### Önerilen günlük kullanım
1. Önce `Sorunsuz Calisanlar` kategorisinden model seç.
2. Yoğunluk olursa otomatik moda geçip fallback kullan.
3. 429 çoksa kısa bekleme (30-90 sn) sonrası tekrar dene.
4. 402 görünen modelleri free akışta kullanma.

### Geliştirici için kısa checklist
- Backend restart sonrası status endpoint kontrol et.
- Model seçim listesi güncel mi bak.
- Stream akışında token geliyor mu kontrol et.
- Hata panelinde sınıflandırma doğru mu doğrula.

---

## 9) Açık riskler / teknik borç

1. 429 için tam otomatik backoff+circuit breaker henüz yok.
2. Bozuk karakter için istemci tarafı normalize filtresi henüz eklenmedi.
3. Model durumlarının kalıcı veri tabanına yazımı yok (şu an oturumluk).
4. Bazı provider davranışları gün içinde değişebildiği için statik kategori zamanla sapabilir.

---

## 10) Sonraki sprint için net görev listesi

1. 429 algılanınca otomatik `retry + exponential backoff` ekle.
2. Belirli süre model cooldown mantığı ekle.
3. UTF-8/mixed encoding temizleme filtresi ekle.
4. Model hata istatistiklerini json/log dosyasına kalıcı yaz.
5. UI'da "son 24 saat başarı oranı" göstergesi ekle.
6. Kategoriye ek olarak "önerilen sıra" puanı ekle.
7. README Türkçe bölümünü bu yeni akışla güncelle.

---

## 11) İletişim ve çalışma kuralı notu

Bu projede kullanıcı talebi açık şekilde şudur:
- Tüm açıklamalar Türkçe olsun.
- Teknik detaylar açık yazılsın, yüzeysel geçilmesin.
- Onay olmadan commit atılmasın.

Bu rapor bu prensiplere uygun şekilde hazırlanmıştır.

---

## 12) Kısa sonuç cümlesi

OpenRouter entegrasyonu artık sadece "mesaj atan" bir yapı değildir; model davranışını gözlemleyebilen, hata tiplerini ayırabilen, manuel/otomatik mod arasında kontrollü geçiş yapabilen ve global sistem prompt ile çıktı kalitesini belirli bir standarda taşıyan operasyonel bir katmana dönüşmüştür.
