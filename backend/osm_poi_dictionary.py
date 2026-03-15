"""
osm_poi_dictionary.py - OpenStreetMap (OSM) NLP Kategori Eşleştirme Sözlüğü

Buradaki sözlük, BERT NLP motorunun algıladığı "POI" (Mekan/İlgi Noktası) niyetlerini,
OpenStreetMap (Overpass/Nominatim API) sorgularında kullanılacak gerçek veritabanı 
etiketlerine (key=value) dönüştürmek için kullanılır.

Binlerce farklı mekanı kapsayacak şekilde genişletilmiştir.
"""

# Kullanıcının yazabileceği Türkçe kelimeler -> OSM Etiketleri
# Format: "turkce_kelime": {"key": "value"}
POI_MAPPING = {
    # ==========================================
    # YEME & İÇME (FOOD & DRINK - AMENITY)
    # ==========================================
    "kafe": {"amenity": "cafe"},
    "cafe": {"amenity": "cafe"},
    "kahve": {"amenity": "cafe"},
    "kahveci": {"amenity": "cafe"},
    "restoran": {"amenity": "restaurant"},
    "lokanta": {"amenity": "restaurant"},
    "yemek": {"amenity": "restaurant"},
    "fast food": {"amenity": "fast_food"},
    "hamburger": {"amenity": "fast_food"},
    "döner": {"amenity": "fast_food"},
    "pizzacı": {"amenity": "fast_food"},
    "bar": {"amenity": "bar"},
    "pub": {"amenity": "pub"},
    "meyhane": {"amenity": "bar"},
    "bira": {"amenity": "pub"},
    "dondurmacı": {"amenity": "ice_cream"},
    "tatlıcı": {"amenity": "ice_cream"},
    "çikolatacı": {"amenity": "ice_cream"},
    "çay bahçesi": {"amenity": "cafe"}, # OSM'de genellikle cafe veya fast_food olarak geçer
    "kebapçı": {"amenity": "restaurant", "cuisine": "kebab"},
    "balıkçı": {"amenity": "restaurant", "cuisine": "seafood"},
    "pilavcı": {"amenity": "restaurant", "cuisine": "turkish"},
    "pilav salonu": {"amenity": "restaurant", "cuisine": "turkish"},
    "pilavci": {"amenity": "restaurant", "cuisine": "turkish"},

    # ==========================================
    # ALIŞVERİŞ & MARKET (SHOPPING - SHOP)
    # ==========================================
    "market": {"shop": "supermarket"},
    "süpermarket": {"shop": "supermarket"},
    "bakkal": {"shop": "convenience"},
    "büfe": {"shop": "convenience"},
    "tekel": {"shop": "alcohol"},
    "tekel bayi": {"shop": "alcohol"},
    "içki": {"shop": "alcohol"},
    "şarap evi": {"shop": "alcohol"},
    "fırın": {"shop": "bakery"},
    "pastane": {"shop": "pastry"},
    "kasap": {"shop": "butcher"},
    "manav": {"shop": "greengrocer"},
    "giyim": {"shop": "clothes"},
    "kıyafet": {"shop": "clothes"},
    "butik": {"shop": "boutique"},
    "ayakkabıcı": {"shop": "shoes"},
    "kozmetik": {"shop": "cosmetics"},
    "parfüm": {"shop": "cosmetics"},
    "kuyumcu": {"shop": "jewelry"},
    "saatçi": {"shop": "watches"},
    "çiçekçi": {"shop": "florist"},
    "kitapçı": {"shop": "books"},
    "kırtasiye": {"shop": "stationery"},
    "oyuncakçı": {"shop": "toys"},
    "elektronik": {"shop": "electronics"},
    "telefoncu": {"shop": "mobile_phone"},
    "bilgisayarcı": {"shop": "computer"},
    "beyaz eşya": {"shop": "appliances"},
    "mobilya": {"shop": "furniture"},
    "avm": {"shop": "mall"},
    "alışveriş merkezi": {"shop": "mall"},
    "eczane": {"amenity": "pharmacy"},
    "pet shop": {"shop": "pet"},
    "evcil hayvan": {"shop": "pet"},
    "bisikletçi": {"shop": "bicycle"},
    "nalbur": {"shop": "hardware"},
    "hırdavat": {"shop": "hardware"},
    "yapı market": {"shop": "doityourself"},
    "kuru temizleme": {"shop": "dry_cleaning"},
    "terzi": {"shop": "tailor"},
    "kuaför": {"shop": "hairdresser"},
    "berber": {"shop": "hairdresser"},
    "güzellik salonu": {"shop": "beauty"},

    # ==========================================
    # SAĞLIK (HEALTHCARE - AMENITY)
    # ==========================================
    "hastane": {"amenity": "hospital"},
    "devlet hastanesi": {"amenity": "hospital"},
    "özel hastane": {"amenity": "hospital"},
    "klinik": {"amenity": "clinic"},
    "sağlık ocağı": {"amenity": "clinic"},
    "doktor": {"amenity": "doctors"},
    "dişçi": {"amenity": "dentist"},
    "diş hekimi": {"amenity": "dentist"},
    "veteriner": {"amenity": "veterinary"},
    "kan merkezi": {"amenity": "blood_donation"},

    # ==========================================
    # HİZMETLER & BANKA (SERVICES - AMENITY)
    # ==========================================
    "banka": {"amenity": "bank"},
    "atm": {"amenity": "atm"},
    "döviz": {"amenity": "bureau_de_change"},
    "postane": {"amenity": "post_office"},
    "ptt": {"amenity": "post_office"},
    "kargo": {"amenity": "post_office"},
    "benzinlik": {"amenity": "fuel"},
    "akaryakıt": {"amenity": "fuel"},
    "benzin istasyonu": {"amenity": "fuel"},
    "şarj": {"amenity": "charging_station"},
    "elektrikli araç şarj": {"amenity": "charging_station"},
    "polis": {"amenity": "police"},
    "karakol": {"amenity": "police"},
    "itfaiye": {"amenity": "fire_station"},
    "belediye": {"amenity": "townhall"},
    "adliye": {"amenity": "courthouse"},
    "tuvalet": {"amenity": "toilets"},
    "wc": {"amenity": "toilets"},
    "duş": {"amenity": "showers"},
    "çeşme": {"amenity": "drinking_water"},
    "çöp kutusu": {"amenity": "waste_basket"},

    # ==========================================
    # TURİZM & GEZİ & EĞLENCE (TOURISM / LEISURE)
    # ==========================================
    "müze": {"tourism": "museum"},
    "sanat galerisi": {"tourism": "gallery"},
    "galeri": {"tourism": "gallery"},
    "otel": {"tourism": "hotel"},
    "rezidans": {"tourism": "hotel"},
    "pansiyon": {"tourism": "guest_house"},
    "hostel": {"tourism": "hostel"},
    "kamp": {"tourism": "camp_site"},
    "karavan": {"tourism": "caravan_site"},
    "hayvanat bahçesi": {"tourism": "zoo"},
    "tema park": {"tourism": "theme_park"},
    "lunapark": {"tourism": "theme_park"},
    "akvaryum": {"tourism": "aquarium"},
    "manzara": {"tourism": "viewpoint"},
    "seyir terası": {"tourism": "viewpoint"},
    "park": {"leisure": "park"},
    "bahçe": {"leisure": "park"},
    "oyun parkı": {"leisure": "playground"},
    "doğa": {"leisure": "nature_reserve"},
    "stadyum": {"leisure": "stadium"},
    "spor salonu": {"leisure": "sports_centre"},
    "yüzme havuzu": {"leisure": "swimming_pool"},
    "plaj": {"natural": "beach"},
    "orman": {"landuse": "forest"},
    "piknik": {"tourism": "picnic_site"},
    "sinema": {"amenity": "cinema"},
    "tiyatro": {"amenity": "theatre"},
    "gece kulübü": {"amenity": "nightclub"},
    "casino": {"amenity": "casino"},

    # ==========================================
    # TARİH & DİN (HISTORIC / AMENITY)
    # ==========================================
    "tarihi yer": {"historic": "archaeological_site"},
    "ören yeri": {"historic": "archaeological_site"},
    "antik kent": {"historic": "archaeological_site"},
    "kale": {"historic": "castle"},
    "anıt": {"historic": "monument"},
    "heykel": {"historic": "monument"},
    "cami": {"amenity": "place_of_worship", "religion": "muslim"},
    "mescit": {"amenity": "place_of_worship", "religion": "muslim"},
    "kilise": {"amenity": "place_of_worship", "religion": "christian"},
    "sinagog": {"amenity": "place_of_worship", "religion": "jewish"},
    "mezarlık": {"cemetery": "grave"},

    # ==========================================
    # EĞİTİM (EDUCATION - AMENITY)
    # ==========================================
    "okul": {"amenity": "school"},
    "ilkokul": {"amenity": "school"},
    "lise": {"amenity": "school"},
    "üniversite": {"amenity": "university"},
    "kampüs": {"amenity": "university"},
    "kolej": {"amenity": "college"},
    "anaokulu": {"amenity": "kindergarten"},
    "kreş": {"amenity": "kindergarten"},
    "kütüphane": {"amenity": "library"},
    "sürücü kursu": {"amenity": "driving_school"},

    # ==========================================
    # ULAŞIM (TRANSPORT)
    # ==========================================
    "durak": {"highway": "bus_stop"},
    "otobüs durağı": {"highway": "bus_stop"},
    "metro": {"station": "subway"},
    "metro istasyonu": {"station": "subway"},
    "tren istasyonu": {"railway": "station"},
    "marmaray": {"railway": "station"},
    "tramvay": {"railway": "tram_stop"},
    "havalimanı": {"aeroway": "aerodrome"},
    "havaalanı": {"aeroway": "aerodrome"},
    "otogar": {"amenity": "bus_station"},
    "taksi durağı": {"amenity": "taxi"},
    "taksi": {"amenity": "taxi"},
    "vapur": {"amenity": "ferry_terminal"},
    "iskele": {"amenity": "ferry_terminal"},
    "liman": {"harbour": "yes"},
    "otopark": {"amenity": "parking"},
    "katlı otopark": {"amenity": "parking", "parking": "multi-storey"},

    # ==========================================
    # DİĞER (OTHERS)
    # ==========================================
    "otel": {"tourism": "hotel"},
    "şelale": {"waterway": "waterfall"},
    "göl": {"natural": "water", "water": "lake"},
    "nehir": {"waterway": "river"},
    "dağ": {"natural": "peak"},
    "mağara": {"natural": "cave_entrance"}
}

def get_osm_tags_for_keyword(keyword: str) -> dict:
    """
    Kullanıcının yazdığı kelimenin OSM Karşılığını (tag'leri) bulur.
    
    Örnek Kullanım:
        get_osm_tags_for_keyword("fırın") -> {"shop": "bakery"}
        get_osm_tags_for_keyword("bilinmeyen") -> None
    """
    keyword_lower = keyword.lower().strip()
    return POI_MAPPING.get(keyword_lower, None)

def get_all_supported_keywords() -> list:
    """Sözlükteki tüm kelimeleri liste olarak döner."""
    return list(POI_MAPPING.keys())

if __name__ == "__main__":
    print(f"Sözlükte {len(POI_MAPPING)} adet kelime eşleştirmesi var.")
    print("\nÖrnekler:")
    print(f"tekel -> {get_osm_tags_for_keyword('tekel')}")
    print(f"müze -> {get_osm_tags_for_keyword('müze')}")
    print(f"metro -> {get_osm_tags_for_keyword('metro')}")
