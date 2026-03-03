# 🗺️ OpenStreetMap - Tüm Kategorileri Nereden Öğrenebilirim?

## 🎯 Resmi Kaynaklar

### 1️⃣ **OSM Wiki - Map Features** (EN KAPSAMLI)
🔗 **Link:** https://wiki.openstreetmap.org/wiki/Map_features

**Ne Var?**
- ✅ TÜM kategoriler (amenity, shop, tourism...)
- ✅ Her kategorinin ALT kategorileri
- ✅ Açıklamalar ve örnekler
- ✅ Kullanım istatistikleri
- ✅ Fotoğraflar

**Nasıl Kullanılır?**
1. Sayfayı aç
2. Sol menüden kategori seç (örn: "Amenity")
3. Tüm alt kategorileri gör
4. Her birine tıkla, detayları oku

---

### 2️⃣ **Taginfo** (İSTATİSTİKLER)
🔗 **Link:** https://taginfo.openstreetmap.org/

**Ne Var?**
- ✅ Dünyada kaç tane kullanılmış
- ✅ En popüler tag'ler
- ✅ Kombinasyonlar (örn: amenity=cafe + cuisine=coffee)
- ✅ Grafikler ve haritalar

**Nasıl Kullanılır?**
1. Arama kutusuna "amenity" yaz
2. Tüm amenity değerlerini gör
3. Her birine tıkla, kaç tane olduğunu gör

**Örnek:**
```
amenity=cafe          → 1,234,567 adet (dünyada)
amenity=restaurant    → 2,345,678 adet
shop=supermarket      → 567,890 adet
```

---

### 3️⃣ **Overpass Turbo** (CANLI TEST)
🔗 **Link:** https://overpass-turbo.eu/

**Ne Var?**
- ✅ Canlı sorgu testi
- ✅ Haritada görselleştirme
- ✅ Sonuçları indir (JSON, GeoJSON)
- ✅ Örnek sorgular

**Nasıl Kullanılır?**
1. Sol tarafa sorgu yaz
2. "Çalıştır" butonuna bas
3. Haritada sonuçları gör

**Örnek Sorgu - Tüm Kafeleri Bul:**
```overpass
[out:json];
node["amenity"="cafe"](around:1000,40.99,29.03);
out;
```

**Örnek Sorgu - Tüm Shop Kategorilerini Bul:**
```overpass
[out:json];
node["shop"](around:5000,40.99,29.03);
out;
```

---

### 4️⃣ **OSM Wiki - Key Pages** (DETAYLI AÇIKLAMALAR)
🔗 **Link:** https://wiki.openstreetmap.org/wiki/Key:amenity

**Her Kategori İçin Ayrı Sayfa:**
- https://wiki.openstreetmap.org/wiki/Key:amenity
- https://wiki.openstreetmap.org/wiki/Key:shop
- https://wiki.openstreetmap.org/wiki/Key:tourism
- https://wiki.openstreetmap.org/wiki/Key:leisure
- https://wiki.openstreetmap.org/wiki/Key:office
- https://wiki.openstreetmap.org/wiki/Key:historic

**Ne Var?**
- ✅ Tüm değerler (values)
- ✅ Ne zaman kullanılır
- ✅ Örnekler
- ✅ Fotoğraflar
- ✅ İlgili tag'ler

---

### 5️⃣ **OSM Tag Finder** (ARAMA MOTORU)
🔗 **Link:** https://tagfinder.herokuapp.com/

**Ne Var?**
- ✅ Anahtar kelime ile arama
- ✅ İlgili tag'leri öner
- ✅ Kullanım örnekleri

**Örnek:**
- "coffee" ara → `amenity=cafe`, `shop=coffee`, `cuisine=coffee_shop`
- "food" ara → `amenity=restaurant`, `shop=bakery`, `amenity=fast_food`

---

## 🔍 PYTHON İLE NASIL ÖĞRENİRİZ?

### Yöntem 1: Overpass API ile Tüm Tag'leri Çek

```python
import requests

def get_all_tags_in_area(lat, lon, radius=5000):
    """
    Belirli bir alandaki TÜM tag'leri çeker
    """
    query = f"""
    [out:json][timeout:60];
    (
        node(around:{radius},{lat},{lon});
        way(around:{radius},{lat},{lon});
    );
    out tags;
    """
    
    url = "https://overpass-api.de/api/interpreter"
    response = requests.post(url, data={"data": query})
    data = response.json()
    
    # Tüm tag'leri topla
    all_tags = {}
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        for key, value in tags.items():
            if key not in all_tags:
                all_tags[key] = set()
            all_tags[key].add(value)
    
    return all_tags

# Kullanım
tags = get_all_tags_in_area(40.99, 29.03, 5000)

# Sonuçları yazdır
for key, values in sorted(tags.items()):
    print(f"\n{key}:")
    for value in sorted(values):
        print(f"  - {value}")
```

**Çıktı:**
```
amenity:
  - atm
  - bank
  - cafe
  - hospital
  - pharmacy
  - restaurant
  
shop:
  - bakery
  - butcher
  - clothes
  - convenience
  - supermarket
  
tourism:
  - hotel
  - museum
  - viewpoint
```

---

### Yöntem 2: Taginfo API Kullan

```python
import requests

def get_popular_tags(key="amenity", limit=100):
    """
    Taginfo API'den popüler tag'leri çeker
    """
    url = f"https://taginfo.openstreetmap.org/api/4/key/values"
    params = {
        "key": key,
        "page": 1,
        "rp": limit,
        "sortname": "count",
        "sortorder": "desc"
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    results = []
    for item in data.get("data", []):
        results.append({
            "value": item["value"],
            "count": item["count"],
            "description": item.get("description", "")
        })
    
    return results

# Kullanım
amenities = get_popular_tags("amenity", 50)

print("En Popüler Amenity Tag'leri:")
for i, tag in enumerate(amenities[:20], 1):
    print(f"{i}. {tag['value']:20} → {tag['count']:,} adet")
```

**Çıktı:**
```
En Popüler Amenity Tag'leri:
1. parking              → 5,234,567 adet
2. place_of_worship     → 3,456,789 adet
3. school               → 2,345,678 adet
4. restaurant           → 2,123,456 adet
5. fuel                 → 1,234,567 adet
6. cafe                 → 1,123,456 adet
7. bank                 → 987,654 adet
8. fast_food            → 876,543 adet
9. pharmacy             → 765,432 adet
10. hospital            → 654,321 adet
```

---

### Yöntem 3: OSM Wiki'den Scrape Et

```python
import requests
from bs4 import BeautifulSoup

def scrape_osm_wiki_categories(key="amenity"):
    """
    OSM Wiki'den tüm kategorileri çeker
    """
    url = f"https://wiki.openstreetmap.org/wiki/Key:{key}"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Tablo bul
    tables = soup.find_all('table', class_='wikitable')
    
    categories = []
    for table in tables:
        rows = table.find_all('tr')[1:]  # İlk satır başlık
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                value = cols[0].get_text(strip=True)
                description = cols[1].get_text(strip=True)
                categories.append({
                    "key": key,
                    "value": value,
                    "description": description
                })
    
    return categories

# Kullanım
amenities = scrape_osm_wiki_categories("amenity")

print(f"Toplam {len(amenities)} amenity kategorisi bulundu:")
for cat in amenities[:10]:
    print(f"  {cat['value']:20} → {cat['description'][:50]}")
```

---

## 📊 HIZLI REFERANS - EN POPÜLER TAG'LER

### Amenity (Top 30)
```
1. parking               → Otopark
2. place_of_worship      → İbadet yeri
3. school                → Okul
4. restaurant            → Restoran
5. fuel                  → Benzin istasyonu
6. cafe                  → Kafe
7. bank                  → Banka
8. fast_food             → Fast food
9. pharmacy              → Eczane
10. hospital             → Hastane
11. post_office          → Postane
12. toilets              → Tuvalet
13. bench                → Bank
14. waste_basket         → Çöp kutusu
15. drinking_water       → İçme suyu
16. atm                  → ATM
17. police               → Polis
18. fire_station         → İtfaiye
19. library              → Kütüphane
20. cinema               → Sinema
21. theatre              → Tiyatro
22. community_centre     → Toplum merkezi
23. townhall             → Belediye
24. kindergarten         → Anaokulu
25. university           → Üniversite
26. college              → Kolej
27. doctors              → Doktor
28. dentist              → Diş hekimi
29. veterinary           → Veteriner
30. clinic               → Klinik
```

### Shop (Top 30)
```
1. convenience           → Bakkal
2. supermarket           → Süpermarket
3. clothes               → Giyim
4. hairdresser           → Kuaför
5. bakery                → Fırın
6. car_repair            → Oto tamir
7. butcher               → Kasap
8. beauty                → Güzellik salonu
9. furniture             → Mobilya
10. kiosk                → Büfe
11. electronics          → Elektronik
12. mobile_phone         → Telefon
13. shoes                → Ayakkabı
14. florist              → Çiçekçi
15. hardware             → Hırdavat
16. books                → Kitapçı
17. jewelry              → Kuyumcu
18. optician             → Gözlükçü
19. bicycle              → Bisiklet
20. car                  → Araba bayii
21. doityourself         → Yapı market
22. greengrocer          → Manav
23. alcohol              → İçki
24. gift                 → Hediyelik
25. stationery           → Kırtasiye
26. newsagent            → Gazete bayii
27. sports               → Spor malzemeleri
28. toys                 → Oyuncak
29. pet                  → Pet shop
30. chemist              → Eczane (kozmetik)
```

### Tourism (Top 20)
```
1. hotel                 → Otel
2. attraction            → Turistik yer
3. information           → Turist danışma
4. museum                → Müze
5. viewpoint             → Manzara noktası
6. guest_house           → Pansiyon
7. artwork               → Sanat eseri
8. picnic_site           → Piknik alanı
9. camp_site             → Kamp alanı
10. hostel               → Hostel
11. motel                → Motel
12. gallery              → Galeri
13. zoo                  → Hayvanat bahçesi
14. theme_park           → Tema parkı
15. aquarium             → Akvaryum
16. apartment            → Apart
17. chalet               → Dağ evi
18. caravan_site         → Karavan
19. alpine_hut           → Dağ kulübesi
20. wilderness_hut       → Vahşi doğa kulübesi
```

### Leisure (Top 20)
```
1. park                  → Park
2. playground            → Oyun parkı
3. pitch                 → Saha
4. sports_centre         → Spor merkezi
5. swimming_pool         → Yüzme havuzu
6. garden                → Bahçe
7. stadium               → Stadyum
8. track                 → Koşu pisti
9. fitness_centre        → Fitness
10. golf_course          → Golf sahası
11. nature_reserve       → Doğa koruma
12. marina               → Marina
13. ice_rink             → Buz pisti
14. beach_resort         → Plaj
15. water_park           → Su parkı
16. bowling_alley        → Bowling
17. miniature_golf       → Mini golf
18. horse_riding         → Binicilik
19. fishing              → Balıkçılık
20. dance                → Dans salonu
```

---

## 🎯 SONUÇ

**Tüm Tag'leri Öğrenmek İçin:**

1. **OSM Wiki** → https://wiki.openstreetmap.org/wiki/Map_features
2. **Taginfo** → https://taginfo.openstreetmap.org/
3. **Overpass Turbo** → https://overpass-turbo.eu/

**Toplam Tag Sayısı:**
- **Ana Kategoriler:** ~50
- **Alt Kategoriler:** ~2000+
- **Kombinasyonlar:** Sınırsız!

**En Çok Kullanılan 5 Kategori:**
1. `amenity` → 100+ değer
2. `shop` → 150+ değer
3. `tourism` → 20+ değer
4. `leisure` → 30+ değer
5. `office` → 15+ değer

---

## 🚀 PROJEYE NASIL EKLERİZ?

Şimdi istersen:
1. ✅ Popüler tag'leri projeye ekleyelim
2. ✅ Dinamik kategori sistemi yapalım (kullanıcı ekleyebilsin)
3. ✅ Taginfo API entegrasyonu yapalım
4. ✅ Otomatik kategori önerisi yapalım

Hangisini yapalım? 🤔
