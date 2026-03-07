# OpenRoutePlanner - 7 Mart Önerileri

Bu dosya, uygulamayı bir sonraki seviyeye taşımak için önerilen geliştirmeleri içerir.
Öneriler; ürün değeri, teknik ihtiyaç ve mevcut kod yapısına uygunluk açısından hazırlanmıştır.

## Genel Değerlendirme

Mevcut yapıda uygulama zaten güçlü bir temel sunuyor:

- Flask tabanlı bir backend var.
- Alternatif rota motoru çalışıyor.
- Geocoding, POI arama, kayıtlı rota ve kayıtlı konum desteği mevcut.
- Timeline altyapısı var.
- BERT/NLP tarafı büyük ölçüde hazırlanmış durumda.

En büyük fırsat, bu hazır parçaları daha bütünleşik ve kullanıcı açısından daha akıllı hale getirmek.

---

## En Yüksek Öncelikli Geliştirmeler

### 1. Doğal Dil ile Rota ve Arama

Uygulamayı farklılaştıracak en güçlü özellik bu olur.

Örnek kullanım:

- "Kadıköy'den Beşiktaş'a rota oluştur"
- "Kadıköy'de kafeleri göster"
- "Moda, Kadıköy ve Üsküdar'ı gez"

Mevcut durum:

- BERT altyapısı hazır.
- Yer veritabanı hazır.
- POI eşleme sözlüğü hazır.
- Ancak backend tarafında NLP endpoint'i henüz yok.
- Frontend tarafında buna uygun bir doğal dil giriş alanı henüz bağlı değil.

Öneri:

- Backend'e `/api/nlp/parse` endpoint'i eklenmeli.
- Frontend'e doğal dil arama kutusu eklenmeli.
- NLP sonucu rota, POI arama veya çoklu durak planına otomatik dönüştürülmeli.

Beklenen fayda:

- Uygulama daha "akıllı" hissedilir.
- Kullanıcı deneyimi ciddi biçimde yükselir.
- Projenin sunum değeri çok artar.

---

### 2. Zaman Planlama Sisteminin Gerçek Kullanıma Uygun Hale Getirilmesi

Mevcut timeline mantığı iyi bir başlangıç ama halen prototip seviyesinde.

Eksik görünen alanlar:

- Noktalar arası süre kaba biçimde hesaplanıyor.
- Her durak için ayrı kalış süresi yönetimi sınırlı.
- Acik/kapalı saat kontrolü pratikte kullanılmıyor.
- Kullanıcıya "bu plan fazla uzun" veya "bu noktayı çıkar" gibi akıllı öneriler yeterince güçlü değil.

Öneri:

- Her nokta için özel ziyaret süresi tanımlama.
- Açılış saatine göre uyarı sistemi.
- Kullanıcının hedef bitiş saatine göre plan önerisi.
- "Bu plan 8 saate sığmıyor" gibi net uyarılar.
- Rota ile timeline ilişkisinin daha doğru kurulması.

Beklenen fayda:

- Uygulama sadece rota çizen değil, günü planlayan bir araca dönüşür.
- Sunumlarda çok güçlü görünür.

---

### 3. JSON Tabanlı Kayıt Yapısından SQLite'a Geçiş

Şu anda kayıtlı rotalar ve kayıtlı yerler JSON dosyalarında tutuluyor.
Bu yapı küçük ölçekte yeterli ama büyüdükçe sorun çıkarır.

Riskler:

- Performans düşer.
- Veri bütünlüğü zayıflar.
- Arama ve filtreleme sınırlı kalır.
- Aynı anda erişim ve güncelleme yönetimi zorlaşır.

Öneri:

- `route_storage.py` ve `location_storage.py` SQLite tabanlı hale getirilmeli.
- Rotalar, yerler, etiketler ve favoriler daha düzenli tablolarla tutulmalı.
- Arama ve sıralama sorguları veri tabanı üstünden yapılmalı.

Beklenen fayda:

- Daha hızlı ve daha güvenilir veri yapısı.
- Gelecekte kullanıcı hesabı veya gelişmiş filtreleme eklemek kolaylaşır.

---

### 4. Frontend Kodunun Modüler Hale Getirilmesi

Şu an frontend tek büyük JavaScript dosyasında ilerliyor.
Bu kısa vadede hızlı geliştirme sağlar ama uzun vadede yönetimi zorlaştırır.

Öneri:

- `app.js` modüllere ayrılmalı.
- Olası modüller:
  - `map.js`
  - `routes.js`
  - `alternatives.js`
  - `pois.js`
  - `saved-routes.js`
  - `saved-locations.js`
  - `timeline.js`
  - `api.js`

Beklenen fayda:

- Bug bulmak kolaylaşır.
- Yeni özellik eklemek daha güvenli olur.
- Kod tabanı daha profesyonel görünür.

---

## Ürünü Güçlendirecek Özellikler

### 5. GPX ve GeoJSON Dışa Aktarma

Kullanıcı oluşturduğu rotayı dışarı aktarabilmeli.

Öneri:

- GPX export
- GeoJSON export
- İsteğe bağlı KML export

Beklenen fayda:

- Rota başka uygulamalarda da kullanılabilir.
- Uygulama gerçek dünyada daha işe yarar hale gelir.

---

### 6. Paylaşılabilir Rota Linki

Kullanıcı oluşturduğu rotayı bağlantı ile paylaşabilmeli.

Öneri:

- URL parametresi ile nokta paylaşımı
- Kısa rota ID sistemi
- Kaydedilmiş rotalar için paylaş butonu

Beklenen fayda:

- Sosyal ve pratik kullanım artar.
- Proje demosunda çok etkileyici olur.

---

### 7. Ulaşım Modu Desteği

Şu anda mantık ağırlıklı olarak yürüyüş odaklı.

Öneri:

- Walking
- Cycling
- Driving

Her mod için:

- farklı hız hesabı
- farklı süre hesabı
- gerekiyorsa farklı OSM network profili

Beklenen fayda:

- Daha geniş kullanım senaryosu.
- Zaman planlama daha gerçekçi hale gelir.

---

### 8. Akıllı POI Filtreleri

POI sistemi şu anda güçlü bir kategori tabanına sahip.
Ama filtreleme daha da gelişebilir.

Öneri:

- Sadece açık olanları göster
- Rotaya yakın olanları göster
- Belirli yarıçap içinde ara
- Kategori + mesafe + saat filtreleme
- Favori POI listesi

Beklenen fayda:

- Kullanıcı aradığı yeri daha hızlı bulur.
- Harita daha işlevsel hale gelir.

---

### 9. Rota Tercihleri

Sadece en kısa rota değil, tercih odaklı rota da önemli.

Öneri:

- En sakin rota
- Ana caddelerden kaçınan rota
- Park içinden geçen rota
- Daha az yokuşlu rota
- Daha güvenli rota

Beklenen fayda:

- Uygulama daha akıllı görünür.
- Gerçek kullanıcı ihtiyacına daha çok yaklaşır.

---

### 10. Rota Üzerine Not ve Durak Bilgisi

Kullanıcı her noktaya bilgi ekleyebilmeli.

Öneri:

- Durak notu
- Tahmini kalış süresi
- Özel etiket
- Öncelik seviyesi

Beklenen fayda:

- Rotalar daha kişisel ve düzenli hale gelir.

---

### 11. Rota Üzerinde Yakındaki Yer Önerileri

Bu özellik kullanıcı deneyimini ciddi biçimde güçlendirir.

Örnek:

- "Bu rotaya yakın kahvecileri ekle"
- "Yol üstünde müze var mı?"
- "500 metre sapma ile eczane bul"

Öneri:

- Mevcut rota çizgisine göre yakın POI analizi
- Kullanıcının rotayı bozmadan yeni durak ekleyebilmesi

Beklenen fayda:

- Uygulama rota planlayıcıdan gezi asistanına dönüşür.

---

### 12. Geri Alma / İleri Alma Sistemi

Kullanıcı yanlışlıkla nokta silerse veya sıralamayı bozarsa geri alabilmeli.

Öneri:

- Undo
- Redo
- Son işlemleri hafızada tutan state geçmişi

Beklenen fayda:

- Kullanıcı deneyimi daha güvenli olur.

---

## Teknik Olarak Güçlendirilmesi Gereken Alanlar

### 13. Test Altyapısının Güçlendirilmesi

Özellikle rota motoru için testler kritik.

Öneri:

- Alternatif rota regresyon testleri
- Endpoint testleri
- Timeline testleri
- Geocoder cache testleri
- Saved route ve saved location testleri

Beklenen fayda:

- Yeni özellik eklerken eski işlevler bozulmaz.

---

### 14. Python ve Torch Uyumluluğunun Netleştirilmesi

Mevcut bağımlılıklarda BERT tarafında sürüm uyumsuzluğu riski var.

Öneri:

- Kullanılan Python sürümüne göre torch sürümü netleştirilmeli.
- Gerekirse ayrı kurulum profilleri hazırlanmalı.
- BERT'siz fallback çalışma modu korunmalı.

Beklenen fayda:

- Kurulum ve demo süreci daha sorunsuz olur.

---

### 15. Loglama ve Performans Ölçümü

Özellikle rota üretiminde ve OSM sorgularında ölçüm gerekli.

Öneri:

- Alternatif rota üretim süresi ölçümü
- Cache hit oranı ölçümü
- Geocoding süreleri
- Overpass ve Nominatim hata kayıtları

Beklenen fayda:

- Nerede yavaşladığı net görünür.
- Performans iyileştirmesi daha kolay yapılır.

---

### 16. Dokümantasyon Güncellemesi

README güncel kodun gerisinde kalmış görünüyor.

Öneri:

- README güncellenmeli.
- Gerçek endpoint listesi tek yerde tutulmalı.
- Kurulum ve çalıştırma adımları sadeleştirilmeli.
- BERT özellikleri ve opsiyonel kurulum ayrı anlatılmalı.

Beklenen fayda:

- Proje daha düzenli görünür.
- Yeni geliştirici veya jüri için anlaşılır olur.

---

### 17. Mobil Uyum ve Arayüz İyileştirmesi

Mevcut sidebar yapısı masaüstü için iyi ama mobilde zorlayıcı olabilir.

Öneri:

- Mobil için açılır panel sistemi
- Daha sade POI görünümü
- Harita alanını mobilde daha fazla büyüten tasarım
- Küçük ekranlarda daha net buton akışı

Beklenen fayda:

- Uygulama daha profesyonel görünür.

---

### 18. Güvenlik ve Rate Limit Katmanı

Geocoder ve OSM tabanlı sorgular dış servislere bağlı olduğu için sınırlama önemli.

Öneri:

- Basit rate limiting
- Request validation
- Kötü istekleri erken reddetme
- Girdi temizleme ve hata mesajlarını standardize etme

Beklenen fayda:

- Uygulama daha dayanıklı hale gelir.

---

## Önerilen Yol Haritası

Bu proje için en mantıklı geliştirme sırası şöyle görünüyor:

### Faz 1

- NLP endpoint ekleme
- Frontend doğal dil arama kutusu
- Timeline sistemini iyileştirme

### Faz 2

- SQLite'a geçiş
- Frontend modülerleştirme
- Test kapsamını artırma

### Faz 3

- GPX ve GeoJSON export
- Paylaşılabilir rota linkleri
- Rota tercih sistemi
- Yakındaki POI önerileri

### Faz 4

- Mobil uyum iyileştirmeleri
- Gelişmiş filtreleme
- Performans ve güvenlik sertleştirmeleri

---

## Kısa Sonuç

Bu projede en güçlü potansiyel alanlar şunlar:

- BERT tabanlı doğal dil etkileşimi
- rota + zaman planlama birleşimi
- POI ile zenginleştirilmiş akıllı gezi deneyimi

Eğer bu üç alan doğru bağlanırsa, uygulama sıradan bir rota çiziciden çıkıp akıllı gezi planlama asistanına dönüşebilir.
