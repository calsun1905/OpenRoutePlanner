"""
🌍 OSM (OpenStreetMap) POI (Mekan) Test ve Listeleme Aracı

--- NASIL ÇALIŞIR? ---
1. VERİ KAYNAĞI NEDİR?: 
   Buradaki veriler dünyanın en büyük ve ücretsiz haritacılık projesi olan OpenStreetMap (OSM) veritabanından çekilmektedir. 

2. NEDEN İNTERNETTEN ÇEKİLİYOR YAZIYOR?:
   Milyonlarca mekan OSM'nin sunucularındadır. Bilgisayarımızda (lokalde) milyonlarca kafeyi/tekel'i barındırmak imkansız olduğu için,
   bu kod cihazınızın internet bağlantısını kullanarak Almanya'daki "Overpass API" adlı arama motoruna bağlanır.

3. OVERPASS API NEDİR?:
   Overpass API, devasa OSM haritasında saniyeler içinde arama yapmamızı sağlayan sisteme verilen addır. 
   Sisteme "Bana Kadıköy sınırları içindeki Alkol (Shop=Alcohol) satılan yerleri ver" komutunu göndeririz. 
   O da tüm veritabanını tarar ve saniyeler içinde sonucu bize JSON (liste) formatında canlı olarak iletir.

ÖZETLE: Kod çalışırken canlı olarak Almanya'daki sunuculara (OSM veritabanına) soru sorar, güncel harita mekanlarını alıp ekrana basar.
"""
import requests
import time

def list_osm_pois(city_name: str, osm_key: str, osm_value: str, limit: int = 50):
    """
    Belirli bir şehir veya ilçede, belirli bir kategoriye giren mekanları listeler.
    
    Args:
        city_name (str): Aranacak yer (Şehir, İlçe veya Belde). Örn: "Kadıköy", "Ankara"
        osm_key (str): OSM sözlüğündeki anahtar kelime (amenity, shop, tourism vb.)
        osm_value (str): OSM sözlüğündeki değer (cafe, alcohol, museum vb.)
        limit (int): Ekrana basılacak maksimum sonuç sayısı
    """
    print("=" * 60)
    print(f"🌍 OSM MEKAN ARAMA MOTORU")
    print("=" * 60)
    print(f"📍 Konum: {city_name}")
    print(f"🏷️  Kategori: {osm_key}={osm_value}")
    print("İnternetten veri çekiliyor, lütfen bekleyin...\n")

    # Overpass API URL'si
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    # Overpass QL (Sorgu Dili)
    # 1. Alanı (Şehri) bul ve ismine searchArea de
    # 2. Bu alan içerisindeki node (nokta), way (yol/bina) ve relation'ları (bölgeleri) bul
    # 3. İsimlerini json formatında bize ver
    overpass_query = f"""
    [out:json][timeout:25];
    area["name"="{city_name}"]->.searchArea;
    (
      node["{osm_key}"="{osm_value}"](area.searchArea);
      way["{osm_key}"="{osm_value}"](area.searchArea);
      relation["{osm_key}"="{osm_value}"](area.searchArea);
    );
    out tags {limit};
    """
    
    try:
        baslangic = time.time()
        
        # API'ye POST isteği at
        response = requests.post(overpass_url, data={'data': overpass_query})
        response.raise_for_status() # HTTP hatası varsa exception fırlatır
        
        data = response.json()
        elements = data.get('elements', [])
        
        if not elements:
            print(f"❌ '{city_name}' sınırları içerisinde '{osm_key}={osm_value}' kategorisinde mekan bulunamadı.")
            return

        print(f"✅ {len(elements)} adet mekan bulundu! (Süre: {time.time() - baslangic:.2f} saniye)\n")
        
        # Sadece ismi olanları ekrana yazdır (İsimsiz olanları filtreleyelim)
        isim_olanlar = []
        for element in elements:
            tags = element.get('tags', {})
            name = tags.get('name')
            if name:
                isim_olanlar.append(name)
        
        # Ekrana bas
        for i, name in enumerate(isim_olanlar, 1):
            print(f"{i}. {name}")
            
        if len(isim_olanlar) < len(elements):
             print(f"\n*(Ayrıca isimsiz, sadece haritada işaretlenmiş {len(elements) - len(isim_olanlar)} adet konum bulundu.)*")
             
    except Exception as e:
        print(f"❌ API Bağlantı Hatası: {e}")

if __name__ == "__main__":
    # =====================================================================
    # BURADAKİ AYARLARI DEĞİŞTİREREK TEST EDEBİLİRSİNİZ
    # Sözlük için: backend/osm_poi_dictionary.py dosyasına bakabilirsiniz.
    # =====================================================================
    
    # ARANACAK YER (İlçe, Şehir):
    ARANACAK_YER = "Kadıköy"  
    
    # ARANACAK KATEGORİ:
    # Örnek Kategoriler:
    # 1. Tekeller için -> KATEGORI_ANAHTAR = "shop", KATEGORI_DEGER = "alcohol"
    # 2. Kafeler için -> KATEGORI_ANAHTAR = "amenity", KATEGORI_DEGER = "cafe"
    # 3. Müzeler için -> KATEGORI_ANAHTAR = "tourism", KATEGORI_DEGER = "museum"
    # 4. AVM'ler için -> KATEGORI_ANAHTAR = "shop", KATEGORI_DEGER = "mall"
    
    KATEGORI_ANAHTAR = "shop"
    KATEGORI_DEGER = "alcohol"
    
    # ARAMAYI BAŞLAT
    list_osm_pois(ARANACAK_YER, KATEGORI_ANAHTAR, KATEGORI_DEGER, limit=30)
