# Veritabani Bilgilendirme

Bu proje su an dis bir veritabani sunucusuna bagimli degildir. Kalici veri katmani agirlikli olarak SQLite3 dosyalari uzerinden lokal makinede calisir.

## Mevcut depolama yaklasimi
- Ana uygulama verileri: `backend/data/app_data.db`
- POI cache verileri: `backend/data/pois.db`
- Geocode cache verileri: `backend/cache/geocodes.db`
- Il/ilce veri kaynagi: `backend/cache/districts_turkey.db`
- Graph cache verileri: `backend/data/*.graphml`

## Neden SQLite3 kullaniyoruz?
- Kurulum maliyeti dusuk
- Lokal gelistirme hizli
- Dis servis bagimliligi olmadan calisabilir
- Tek makine/sinif projesi olceginde yeterli

## Gelecek veritabani secenegi
Ileride daha fazla kullanici, daha fazla eszamanli istek ve merkezi yonetim ihtiyaci olursa PostgreSQL gibi bir SQL veritabanina gecis planlanabilir.

Mevcut sema duzeni tablo-temelli oldugu icin SQL migration yolu aciktir.

## Not
Bu dokuman, proje icinde "veri nerede tutuluyor" sorusuna hizli cevap vermek icin tutulur. Kod tarafindaki gercek kaynak her zaman ilgili moduldeki DB tanimlari ve schema olusturma kodlaridir.