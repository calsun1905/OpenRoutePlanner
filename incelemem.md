
Tabii ki, parça parça ve daha sade bir şekilde anlatayım. Arka planı (backend) anlamak, uygulamanın beyninin nasıl çalıştığını anlamak demek. O yüzden uygulamamızın omurgası olan 

app.py
 dosyasını bölerek inceleyelim.

Python (Flask) kullanılarak yazılan bu arka plan, temel olarak iki büyük işi yapıyor:

Verilen noktalar arasında en kısa/en mantıklı rotayı bulmak.
Harita üzerinde müze, kafe gibi önemli mekanları (POI) aramak.
Bugün ilk olarak en önemli kısım olan Rota Hesaplama sisteminin üzerinden geçelim:

1. Rota Hesaplama Sistemi (/api/get-route)
Kullanıcı haritada bazı noktalara (örneğin A, B ve C noktaları) tıkladığında, ön yüz bu noktaların koordinatlarını arka plana gönderiyor. Burada devreye /api/get-route isimli bir fonksiyon giriyor. Bu fonksiyon adım adım şunları yapıyor:

Noktaları Alıp Haritayı Tanıma: Önce kullanıcının gönderdiği noktaların koordinatlarını (enlem ve boylam) alıyor. Sonra bu noktaların bulunduğu şehrin veya bölgenin sokak ağını (bir nevi dijital haritasını) hafızaya yüklüyor.
En Mantıklı Sırayı Bulma (Optimize Etme): Diyelim ki kullanıcı 5 farklı yer seçti ama bunları karışık sırayla seçti. Sistemdeki TSP (Gezgin Satıcı Problemi) algoritması devreye girip, "Acaba bu 5 noktayı hangi sırayla gezersek en az yürümüş oluruz?" sorusunu çözüyor. Yani noktaları ziyaret etmek için en mantıklı sırayı buluyor.
Sokaklardan Geçen Tam Rotayı Çizme: Sıralama bulunduktan sonra, kuş uçuşu gitmek yerine gerçek sokakları kullanarak noktaları birbirine bağlıyor. Hedefe ulaşmak için hangi sokaklardan dönülmesi gerektiğini hesaplıyor.
İstatistikleri Çıkarma: Çizilen bu rotanın toplam kaç kilometre sürdüğünü ve ortalama hızla yürüdüğümüzde kaç dakika süreceğini hesaplıyor.
Google Maps Linki Üretme: Kullanıcının bu rotayı telefonunda açabilmesi için tıklanabilir bir Google Haritalar linki oluşturuyor.
Tüm bu hesaplamalar bittikten sonra, arka plan bulduğu bu sonuçları (çizilecek rotanın tüm koordinatları, süre, mesafe vs.) tekrar ön yüze gönderiyor ve böylece ekranda o mavi rotayı görebiliyoruz.

Bu birinci kısımdı. Rota hesaplama mantığı genel olarak böyle işliyor. Bu kısım anlaşıldıysa veya sormak istediğiniz bir detay yoksa, uygulamanın arka plandaki diğer yeteneği olan Kategoriye Göre Mekan (POI) Arama kısmına geçebilirim. Ne dersiniz?

sana uygulamayla bazı tek tek soruları sorsam bana yardımcı olabilir misin?   öncelikle ben en batan beri kodda yetkin olmak istiyorum o yüzden mnce global dğeikenler görüyorum cache için ,  bu tam olarak ne oluyor sadece sorduğum sorulara cevap verebilirsen çok sevinirim
Tabii ki, adım adım gidelim. Bu şekilde ilerlemek kodu tam olarak sindirmen için harika bir yöntem.

Kodun 27. ve 28. satırlarındaki şu değişkenlerden bahsediyorsun:

python
27: _graph_cache = {}
28: _poi_cache = {}
Bu "Cache" (Önbellek) Ne İşe Yarıyor?
En kısa cevap: Uygulamanın hızını artırmak ve aynı işi tekrar tekrar yapıp bilgisayarı (veya interneti) yormamak için kullanılan bir **"kısa süreli hafıza"**dır.

Daha detaylı açıklarsak:

Ağır İşlemleri Bir Kez Yapmak: Sokak ağlarını (grafik yapılarını) internetten indirmek veya yerel veritabanından işleyip hafızaya yüklemek zaman alan "maliyetli" ve yavaş işlemlerdir.
Hafızaya Not Almak:
Bir kullanıcı "Kadıköy" için bir rota istediğinde, sistem Kadıköy'ün harita verisini (

graph
) bir kez oluşturur ve bunu _graph_cache sözlüğüne (dictionary) kaydeder.
5 dakika sonra aynı kullanıcı veya başka biri tekrar Kadıköy üzerinde bir işlem yaptığında, sistem "Kadıköy haritası bende zaten var" der ve işlemi internete/diske gitmeden milisaniyeler içinde hafızadan getirir.
POI (Mekan) Araması: _poi_cache de benzer şekilde çalışır. "Kadıköy'deki müzeler" bir kez arandığında sonuçlar buraya kaydedilir. Aynı arama tekrar yapıldığında sonuç şak diye ekrana gelir.
Özetle: Bu boş süslü parantezler {} aslında boş kutulardır. Uygulama çalıştıkça içine öğrendiği bilgileri koyar ki bir dahaki sefere daha hızlı cevap verebilsin.

Bu kısım net mi? Eğer öyleyse bir sonraki soruna geçebiliriz.