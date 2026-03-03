# 🗺️ OpenStreetMap - Tüm Kategori ve Tag'ler

## 📋 OSM Tag Sistemi Nasıl Çalışır?

OpenStreetMap'te her yer **key=value** formatında etiketlenir:

```
amenity=cafe          → Starbucks bir kafe
tourism=museum        → Ayasofya bir müze
shop=supermarket      → Migros bir market
leisure=park          → Gezi Parkı bir park
```

---

## 🏪 1. AMENITY (Tesisler)

### ☕ Yiyecek & İçecek
```
amenity=restaurant       → Restoran
amenity=cafe             → Kafe
amenity=fast_food        → Fast food
amenity=bar              → Bar
amenity=pub              → Pub
amenity=food_court       → Yemek alanı
amenity=ice_cream        → Dondurma
amenity=biergarten       → Bira bahçesi
```

### 🏥 Sağlık
```
amenity=hospital         → Hastane
amenity=clinic           → Klinik
amenity=doctors          → Doktor
amenity=dentist          → Diş hekimi
amenity=pharmacy         → Eczane
amenity=veterinary       → Veteriner
```

### 🎓 Eğitim
```
amenity=school           → Okul
amenity=university       → Üniversite
amenity=college          → Kolej
amenity=kindergarten     → Anaokulu
amenity=library          → Kütüphane
amenity=music_school     → Müzik okulu
amenity=language_school  → Dil okulu
```

### 🏦 Finans
```
amenity=bank             → Banka
amenity=atm              → ATM
amenity=bureau_de_change → Döviz bürosu
```

### 🚔 Kamu Hizmetleri
```
amenity=police           → Polis
amenity=fire_station     → İtfaiye
amenity=post_office      → Postane
amenity=townhall         → Belediye
amenity=courthouse       → Mahkeme
amenity=embassy          → Elçilik
amenity=community_centre → Toplum merkezi
```

### 🎭 Eğlence
```
amenity=cinema           → Sinema
amenity=theatre          → Tiyatro
amenity=nightclub        → Gece kulübü
amenity=casino           → Kumarhane
amenity=arts_centre      → Sanat merkezi
amenity=studio           → Stüdyo
```

### 🚗 Ulaşım
```
amenity=parking          → Otopark
amenity=parking_space    → Park yeri
amenity=bicycle_parking  → Bisiklet parkı
amenity=fuel             → Benzin istasyonu
amenity=charging_station → Şarj istasyonu
amenity=car_wash         → Oto yıkama
amenity=car_rental       → Araç kiralama
amenity=taxi             → Taksi durağı
amenity=bus_station      → Otobüs terminali
```

### 🏛️ Din
```
amenity=place_of_worship → İbadet yeri
  + religion=muslim      → Cami
  + religion=christian   → Kilise
  + religion=jewish      → Sinagog
  + religion=buddhist    → Budist tapınağı
  + religion=hindu       → Hindu tapınağı
```

### 🗑️ Diğer
```
amenity=toilets          → Tuvalet
amenity=drinking_water   → İçme suyu
amenity=bench            → Bank
amenity=waste_basket     → Çöp kutusu
amenity=recycling        → Geri dönüşüm
amenity=telephone        → Telefon
amenity=vending_machine  → Otomat
amenity=clock            → Saat
amenity=fountain         → Çeşme
amenity=shelter          → Barınak
amenity=marketplace      → Pazar yeri
amenity=public_bath      → Hamam
amenity=social_facility  → Sosyal tesis
amenity=prison           → Hapishane
amenity=grave_yard       → Mezarlık
```

---

## 🏪 2. SHOP (Mağazalar)

### 🛒 Gıda
```
shop=supermarket         → Süpermarket
shop=convenience         → Bakkal
shop=grocery             → Market
shop=bakery              → Fırın
shop=butcher             → Kasap
shop=greengrocer         → Manav
shop=seafood             → Balıkçı
shop=confectionery       → Şekerci
shop=chocolate           → Çikolata
shop=tea                 → Çaycı
shop=coffee              → Kahve
shop=deli                → Şarküteri
shop=dairy               → Süt ürünleri
shop=cheese              → Peynir
shop=wine                → Şarap
shop=alcohol             → İçki
shop=beverages           → İçecek
shop=water               → Su
shop=pastry              → Pastane
shop=farm                → Çiftlik ürünleri
```

### 👕 Giyim
```
shop=clothes             → Giyim
shop=shoes               → Ayakkabı
shop=fashion             → Moda
shop=boutique            → Butik
shop=jewelry             → Kuyumcu
shop=watches             → Saatçi
shop=bag                 → Çanta
shop=leather             → Deri
shop=fabric              → Kumaş
shop=tailor              → Terzi
shop=wedding             → Gelinlik
shop=baby_goods          → Bebek ürünleri
```

### 📱 Elektronik
```
shop=electronics         → Elektronik
shop=computer            → Bilgisayar
shop=mobile_phone        → Telefon
shop=hifi                → Ses sistemi
shop=photo               → Fotoğraf
shop=video_games         → Video oyun
shop=radiotechnics       → Radyo
```

### 🏠 Ev & Bahçe
```
shop=furniture           → Mobilya
shop=interior_decoration → İç dekorasyon
shop=houseware           → Ev eşyası
shop=hardware            → Hırdavat
shop=doityourself        → Yapı market
shop=paint               → Boya
shop=carpet              → Halı
shop=curtain             → Perde
shop=florist             → Çiçekçi
shop=garden_centre       → Bahçe merkezi
shop=glaziery            → Cam
```

### 📚 Kültür
```
shop=books               → Kitapçı
shop=newsagent           → Gazete bayii
shop=stationery          → Kırtasiye
shop=gift                → Hediyelik
shop=art                 → Sanat galerisi
shop=music               → Müzik
shop=musical_instrument  → Müzik aleti
shop=video               → Video
shop=anime               → Anime
shop=collector           → Koleksiyon
```

### 💄 Kişisel Bakım
```
shop=beauty              → Güzellik
shop=hairdresser         → Kuaför
shop=cosmetics           → Kozmetik
shop=perfumery           → Parfümeri
shop=chemist             → Eczane (kozmetik)
shop=massage             → Masaj
shop=tattoo              → Dövme
shop=optician            → Gözlükçü
shop=hearing_aids        → İşitme cihazı
shop=medical_supply      → Medikal malzeme
```

### 🚗 Otomotiv
```
shop=car                 → Araba bayii
shop=car_repair          → Oto tamir
shop=car_parts           → Yedek parça
shop=motorcycle          → Motosiklet
shop=bicycle             → Bisiklet
shop=tyres               → Lastik
```

### 🐕 Hayvan
```
shop=pet                 → Pet shop
shop=pet_grooming        → Hayvan bakımı
shop=agrarian            → Tarım
```

### 🎨 Hobi & Spor
```
shop=sports              → Spor malzemeleri
shop=outdoor             → Outdoor
shop=fishing             → Balıkçılık
shop=hunting             → Avcılık
shop=toys                → Oyuncak
shop=games               → Oyun
shop=model               → Maket
shop=hobby               → Hobi
```

### 🔧 Diğer
```
shop=department_store    → Büyük mağaza
shop=mall                → AVM
shop=variety_store       → Çeşitli ürünler
shop=general             → Genel
shop=kiosk               → Büfe
shop=trade               → Ticaret
shop=wholesale           → Toptan
shop=second_hand         → İkinci el
shop=charity             → Hayır kurumu
shop=pawnbroker          → Rehinci
shop=lottery             → Piyango
shop=funeral_directors   → Cenaze
shop=tobacco             → Tütün
shop=e-cigarette         → Elektronik sigara
shop=weapons             → Silah
shop=pyrotechnics        → Havai fişek
shop=erotic              → Erotik
shop=travel_agency       → Seyahat acentesi
shop=laundry             → Çamaşırhane
shop=dry_cleaning        → Kuru temizleme
shop=tailor              → Terzi
shop=locksmith           → Çilingir
shop=copyshop            → Fotokopi
shop=frame               → Çerçeve
shop=trophy              → Kupa
shop=ticket              → Bilet
shop=money_lender        → Tefeci
```

---

## 🏨 3. TOURISM (Turizm)

```
tourism=hotel            → Otel
tourism=motel            → Motel
tourism=hostel           → Hostel
tourism=guest_house      → Pansiyon
tourism=apartment        → Apart
tourism=chalet           → Dağ evi
tourism=camp_site        → Kamp alanı
tourism=caravan_site     → Karavan
tourism=alpine_hut       → Dağ kulübesi

tourism=museum           → Müze
tourism=gallery          → Galeri
tourism=attraction       → Turistik yer
tourism=viewpoint        → Manzara noktası
tourism=zoo              → Hayvanat bahçesi
tourism=aquarium         → Akvaryum
tourism=theme_park       → Tema parkı

tourism=information      → Turist danışma
tourism=artwork          → Sanat eseri
tourism=picnic_site      → Piknik alanı
```

---

## 🎾 4. LEISURE (Eğlence & Spor)

```
leisure=park             → Park
leisure=playground       → Oyun parkı
leisure=garden           → Bahçe
leisure=nature_reserve   → Doğa koruma alanı
leisure=beach_resort     → Plaj

leisure=sports_centre    → Spor merkezi
leisure=stadium          → Stadyum
leisure=swimming_pool    → Yüzme havuzu
leisure=fitness_centre   → Fitness
leisure=golf_course      → Golf sahası
leisure=pitch            → Saha (futbol, basketbol)
leisure=track            → Koşu pisti
leisure=ice_rink         → Buz pisti
leisure=bowling_alley    → Bowling
leisure=horse_riding     → Binicilik
leisure=miniature_golf   → Mini golf
leisure=water_park       → Su parkı

leisure=marina           → Marina
leisure=fishing          → Balıkçılık
leisure=slipway          → Tekne rampası

leisure=dance            → Dans salonu
leisure=amusement_arcade → Oyun salonu
leisure=adult_gaming_centre → Kumar salonu
leisure=escape_game      → Kaçış oyunu
leisure=hackerspace      → Hackerspace
leisure=bandstand        → Konser alanı
```

---

## 🚉 5. RAILWAY (Demiryolu)

```
railway=station          → Tren istasyonu
railway=halt             → Durak
railway=subway_entrance  → Metro girişi
railway=tram_stop        → Tramvay durağı
railway=platform         → Peron
```

---

## 🚌 6. HIGHWAY (Yol & Ulaşım)

```
highway=bus_stop         → Otobüs durağı
highway=bus_station      → Otobüs terminali
highway=rest_area        → Dinlenme tesisi
highway=services         → Servis alanı
```

---

## 🏢 7. OFFICE (Ofisler)

```
office=company           → Şirket
office=government        → Devlet dairesi
office=lawyer            → Avukat
office=estate_agent      → Emlakçı
office=insurance         → Sigorta
office=telecommunication → Telekom
office=newspaper         → Gazete
office=architect         → Mimar
office=association       → Dernek
office=ngo               → STK
office=accountant        → Muhasebeci
office=tax_advisor       → Vergi danışmanı
office=notary            → Noter
```

---

## 🏛️ 8. HISTORIC (Tarihi Yerler)

```
historic=monument        → Anıt
historic=memorial        → Anma yeri
historic=castle          → Kale
historic=ruins           → Harabe
historic=archaeological_site → Arkeolojik alan
historic=fort            → Kale
historic=manor           → Konak
historic=palace          → Saray
historic=tomb            → Türbe
historic=wayside_cross   → Haç
historic=wayside_shrine  → Türbe
historic=battlefield     → Savaş alanı
historic=city_gate       → Şehir kapısı
```

---

## 🏗️ 9. BUILDING (Binalar)

```
building=apartments      → Apartman
building=house           → Ev
building=residential     → Konut
building=commercial      → Ticari
building=retail          → Perakende
building=industrial      → Endüstriyel
building=warehouse       → Depo
building=office          → Ofis
building=hotel           → Otel
building=hospital        → Hastane
building=school          → Okul
building=university      → Üniversite
building=public          → Kamu binası
building=church          → Kilise
building=mosque          → Cami
building=temple          → Tapınak
building=synagogue       → Sinagog
building=stadium         → Stadyum
building=train_station   → Tren istasyonu
building=transportation  → Ulaşım
building=parking         → Otopark
building=bridge          → Köprü
building=tower           → Kule
building=bunker          → Sığınak
building=castle          → Kale
building=ruins           → Harabe
```

---

## 🌳 10. NATURAL (Doğal Özellikler)

```
natural=peak             → Zirve
natural=volcano          → Volkan
natural=valley           → Vadi
natural=cliff            → Uçurum
natural=cave_entrance    → Mağara girişi
natural=beach            → Plaj
natural=coastline        → Kıyı şeridi
natural=bay              → Koy
natural=spring           → Kaynak
natural=hot_spring       → Kaplıca
natural=geyser           → Gayzer
natural=waterfall        → Şelale
natural=water            → Su
natural=wood             → Orman
natural=tree             → Ağaç
natural=tree_row         → Ağaç sırası
natural=scrub            → Çalılık
natural=heath            → Fundalık
natural=grassland        → Çayır
natural=wetland          → Sulak alan
natural=glacier          → Buzul
natural=rock             → Kaya
natural=stone            → Taş
natural=sand             → Kum
natural=bare_rock        → Çıplak kaya
```

---

## 🎯 NASIL KULLANILIR?

### Örnek 1: Tüm Restoranlar
```python
query = """
[out:json];
node["amenity"="restaurant"](around:1000,40.99,29.03);
out;
"""
```

### Örnek 2: Tüm Mağazalar
```python
query = """
[out:json];
node["shop"](around:1000,40.99,29.03);
out;
"""
```

### Örnek 3: Sadece Süpermarketler
```python
query = """
[out:json];
node["shop"="supermarket"](around:1000,40.99,29.03);
out;
```

### Örnek 4: Camiler
```python
query = """
[out:json];
node["amenity"="place_of_worship"]["religion"="muslim"](around:1000,40.99,29.03);
out;
"""
```

### Örnek 5: Tüm Turizm Yerleri
```python
query = """
[out:json];
node["tourism"](around:1000,40.99,29.03);
out;
"""
```

---

## 🔍 DAHA FAZLA BİLGİ

**OSM Wiki:** https://wiki.openstreetmap.org/wiki/Map_features
**Taginfo:** https://taginfo.openstreetmap.org/
**Overpass Turbo:** https://overpass-turbo.eu/

---

## 📊 ÖZETİ

**Ana Kategoriler:**
1. **amenity** - Tesisler (kafe, hastane, okul...)
2. **shop** - Mağazalar (market, giyim, elektronik...)
3. **tourism** - Turizm (otel, müze, galeri...)
4. **leisure** - Eğlence (park, spor, havuz...)
5. **railway** - Demiryolu (tren, metro...)
6. **highway** - Yol (otobüs durağı...)
7. **office** - Ofisler (şirket, avukat...)
8. **historic** - Tarihi (anıt, kale, saray...)
9. **building** - Binalar (ev, apartman...)
10. **natural** - Doğal (dağ, plaj, orman...)

**Toplam:** 500+ farklı kategori! 🎯
