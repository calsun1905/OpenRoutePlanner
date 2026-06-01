"""
complete_location_poi_engine.py - TAM LOKASYON + POI MOTORU

Istanbul icin:
- 37 ilce (koordinatli)
- 15 POI tipi
- 123 ornek POI/mekan
- Dogal dil sorgusundan ilce + POI tipi eslestirme
"""

from typing import Dict, List, Set, Optional

# =============================================================================
# ?STANBUL ?LÇE VER?TABANI (37 il�e)
# =============================================================================

ISTANBUL_DISTRICTS = {
    "adalar": {"name": "Adalar", "il": "istanbul", "yakla": "anadolu", "lat": 40.87, "lon": 29.13},
    "arnavutk�y": {"name": "Arnavutk�y", "il": "istanbul", "yakla": "avrupa", "lat": 41.27, "lon": 28.73},
    "ataşehir": {"name": "Ataşehir", "il": "istanbul", "yakla": "anadolu", "lat": 40.99, "lon": 29.13},
    "avc?lar": {"name": "Avc?lar", "il": "istanbul", "yakla": "avrupa", "lat": 40.99, "lon": 28.72},
    "bağc?lar": {"name": "Bağc?lar", "il": "istanbul", "yakla": "avrupa", "lat": 41.04, "lon": 28.86},
    "bah�elievler": {"name": "Bah�elievler", "il": "istanbul", "yakla": "avrupa", "lat": 41.00, "lon": 28.86},
    "bak?rk�y": {"name": "Bak?rk�y", "il": "istanbul", "yakla": "avrupa", "lat": 40.98, "lon": 28.82},
    "başakşehir": {"name": "Başakşehir", "il": "istanbul", "yakla": "avrupa", "lat": 41.09, "lon": 28.79},
    "bayrampaşa": {"name": "Bayrampaşa", "il": "istanbul", "yakla": "avrupa", "lat": 41.05, "lon": 28.90},
    "beşiktaş": {"name": "Beşiktaş", "il": "istanbul", "yakla": "avrupa", "lat": 41.04, "lon": 29.01},
    "beylikd�z�": {"name": "Beylikd�z�", "il": "istanbul", "yakla": "avrupa", "lat": 41.01, "lon": 28.64},
    "beyoğlu": {"name": "Beyoğlu", "il": "istanbul", "yakla": "avrupa", "lat": 41.04, "lon": 28.98},
    "b�y�k�ekmece": {"name": "B�y�k�ekmece", "il": "istanbul", "yakla": "avrupa", "lat": 41.02, "lon": 28.58},
    "�atalca": {"name": "Çatalca", "il": "istanbul", "yakla": "avrupa", "lat": 41.15, "lon": 28.46},
    "�ekmek�y": {"name": "Çekmek�y", "il": "istanbul", "yakla": "anadolu", "lat": 41.03, "lon": 29.17},
    "esenler": {"name": "Esenler", "il": "istanbul", "yakla": "avrupa", "lat": 41.06, "lon": 28.88},
    "ey�psultan": {"name": "Ey�psultan", "il": "istanbul", "yakla": "avrupa", "lat": 41.05, "lon": 28.93},
    "fatih": {"name": "Fatih", "il": "istanbul", "yakla": "avrupa", "lat": 41.02, "lon": 28.95},
    "gaziosmanpaşa": {"name": "Gaziosmanpaşa", "il": "istanbul", "yakla": "avrupa", "lat": 41.07, "lon": 28.90},
    "g�ng�ren": {"name": "G�ng�ren", "il": "istanbul", "yakla": "avrupa", "lat": 41.01, "lon": 28.89},
    "kad?k�y": {"name": "Kad?k�y", "il": "istanbul", "yakla": "anadolu", "lat": 40.99, "lon": 29.03},
    "kağ?thane": {"name": "Kağ?thane", "il": "istanbul", "yakla": "avrupa", "lat": 41.07, "lon": 28.96},
    "kartal": {"name": "Kartal", "il": "istanbul", "yakla": "anadolu", "lat": 40.98, "lon": 29.19},
    "k���k�ekmece": {"name": "K���k�ekmece", "il": "istanbul", "yakla": "avrupa", "lat": 40.99, "lon": 28.79},
    "maltepe": {"name": "Maltepe", "il": "istanbul", "yakla": "anadolu", "lat": 40.94, "lon": 29.15},
    "pendik": {"name": "Pendik", "il": "istanbul", "yakla": "anadolu", "lat": 40.88, "lon": 29.23},
    "sancaktepe": {"name": "Sancaktepe", "il": "istanbul", "yakla": "anadolu", "lat": 40.99, "lon": 29.23},
    "sar?yer": {"name": "Sar?yer", "il": "istanbul", "yakla": "avrupa", "lat": 41.10, "lon": 29.04},
    "silivri": {"name": "Silivri", "il": "istanbul", "yakla": "avrupa", "lat": 41.07, "lon": 28.24},
    "sultanbeyli": {"name": "Sultanbeyli", "il": "istanbul", "yakla": "anadolu", "lat": 40.96, "lon": 29.28},
    "sultangazi": {"name": "Sultangazi", "il": "istanbul", "yakla": "avrupa", "lat": 41.08, "lon": 28.87},
    "şile": {"name": "Şile", "il": "istanbul", "yakla": "anadolu", "lat": 41.18, "lon": 29.61},
    "şişli": {"name": "Şişli", "il": "istanbul", "yakla": "avrupa", "lat": 41.05, "lon": 28.99},
    "tuzla": {"name": "Tuzla", "il": "istanbul", "yakla": "anadolu", "lat": 40.86, "lon": 29.30},
    "�mraniye": {"name": "Ümraniye", "il": "istanbul", "yakla": "anadolu", "lat": 41.01, "lon": 29.10},
    "�sk�dar": {"name": "Üsk�dar", "il": "istanbul", "yakla": "anadolu", "lat": 41.02, "lon": 29.02},
    "zeytinburnu": {"name": "Zeytinburnu", "il": "istanbul", "yakla": "avrupa", "lat": 41.01, "lon": 28.91},
}

# =============================================================================
# POI T?PLER? VE ALIAS'LARI (OSM Format?)
# =============================================================================

POI_TYPES = {
    "kafe": {
        "aliases": ["kafe", "cafe", "café", "coffee", "kahve", "�ay", "�ayhane", "k?rato"],
        "osm_tags": ["amenity=cafe", "amenity=fast_food"],
        "description": "Kafeler ve kahve d�kkanlar?"
    },
    "restaurant": {
        "aliases": ["restaurant", "restoran", "lokanta", "yemek", "yemekhane", "食堂"],
        "osm_tags": ["amenity=restaurant"],
        "description": "Restoranlar ve yemek yerleri"
    },
    "bar": {
        "aliases": ["bar", "pub", "gece", "club", "kul�p", "bistro", "bira"],
        "osm_tags": ["amenity=bar", "amenity=nightclub"],
        "description": "Barlar ve gece kul�pleri"
    },
    "market": {
        "aliases": ["market", "bakkal", "market", "s�per", "s�permarket", "şark�teri"],
        "osm_tags": ["shop=supermarket", "shop=grocery"],
        "description": "Marketler ve bakkallar"
    },
    "eczane": {
        "aliases": ["eczane", "pharmacy", "ila�", "derman"],
        "osm_tags": ["amenity=pharmacy"],
        "description": "Eczaneler"
    },
    "hospital": {
        "aliases": ["hastane", "hospital", "sağl?k", "t?p", "doktor", "klinik"],
        "osm_tags": ["amenity=hospital", "amenity=clinic"],
        "description": "Hastaneler ve klinikler"
    },
    "school": {
        "aliases": ["okul", "school", "dersane", "eğitim", "�niversite"],
        "osm_tags": ["amenity=school", "amenity=university"],
        "description": "Okullar ve eğitim kurumlar?"
    },
    "park": {
        "aliases": ["park", "bah�e", "yeşil", "rekreasyon", "spor", "fitness"],
        "osm_tags": ["leisure=park", "leisure=fitness"],
        "description": "Parklar ve yeşil alanlar"
    },
    "bank": {
        "aliases": ["banka", "bank", "atm", "finans", "para"],
        "osm_tags": ["amenity=bank", "amenity=atm"],
        "description": "Bankalar ve ATM'ler"
    },
    "mosque": {
        "aliases": ["cami", "mosque", "namaz", "mescit"],
        "osm_tags": ["amenity=place_of_worship"],
        "description": "Camiler ve ibadet yerleri"
    },
    "hotel": {
        "aliases": ["otel", "hotel", "pansiyon", "konaklama", "hostel"],
        "osm_tags": ["tourism=hotel"],
        "description": "Oteller ve konaklama"
    },
    "atm": {
        "aliases": ["atm", "bankamatik", "nakit", "para �ekme"],
        "osm_tags": ["amenity=atm"],
        "description": "ATM'ler"
    },
    "parking": {
        "aliases": ["park", "otopark", "ara�", "garaj"],
        "osm_tags": ["amenity=parking"],
        "description": "Otoparklar"
    },
    "gas": {
        "aliases": ["benzin", "akaryak?t", "bp", "shell", "lpg", "doğalgaz"],
        "osm_tags": ["amenity=fuel"],
        "description": "Benzin istasyonlar?"
    },
    "police": {
        "aliases": ["polis", "karakol", "emniyet", "g�venlik"],
        "osm_tags": ["amenity=police"],
        "description": "Polis ve g�venlik"
    },
}

# =============================================================================
# POI VER?TABANI (ÖRNEK MEKAN VER?LER?)
# =============================================================================

POI_DATABASE = {
    "kad?k�y": [
        {"name": "Starbucks Moda", "type": "kafe", "lat": 40.9912, "lon": 29.0265, "address": "Moda Cd. No:15", "rating": 4.2},
        {"name": "MMM Mant?", "type": "restaurant", "lat": 40.9905, "lon": 29.0258, "address": "Caferağa Mah.", "rating": 4.5},
        {"name": "Çeşm-i Cedit Cafe", "type": "kafe", "lat": 40.9920, "lon": 29.0275, "address": "Rasimpaşa Sk.", "rating": 4.0},
        {"name": "Beyaz F?r?n", "type": "restaurant", "lat": 40.9908, "lon": 29.0280, "address": "Kad?k�y Çarş?", "rating": 4.3},
        {"name": "Moda Sahil Cafe", "type": "kafe", "lat": 40.9930, "lon": 29.0250, "address": "Bahariye Cd.", "rating": 4.1},
        {"name": "Bostanc? Kuru Temizleme", "type": "market", "lat": 40.9880, "lon": 29.0300, "address": "Bostanc? Cd.", "rating": 3.8},
        {"name": "G�ztepe Eczane", "type": "eczane", "lat": 40.9875, "lon": 29.0350, "address": "G�ztepe Cd.", "rating": 4.5},
        {"name": "Fenerbah�e Park", "type": "park", "lat": 40.9945, "lon": 29.0230, "address": "Fenerbah�e", "rating": 4.4},
        {"name": "Kad?k�y Pazar? ATM", "type": "atm", "lat": 40.9900, "lon": 29.0290, "address": "Kad?k�y Pazar", "rating": 5.0},
        {"name": "Fenerbah�e Spor Kul�b�", "type": "park", "lat": 40.9950, "lon": 29.0220, "address": "Fenerbah�e Km.", "rating": 4.6},
        {"name": "Çiya Sofras?", "type": "restaurant", "lat": 40.9903, "lon": 29.0270, "address": "Caferağa", "rating": 4.7},
        {"name": "Kad?k�y'de Kahve", "type": "kafe", "lat": 40.9907, "lon": 29.0278, "address": "Osmanağa Sk.", "rating": 4.3},
        {"name": "Yeldeğirmeni Cafe", "type": "kafe", "lat": 40.9918, "lon": 29.0255, "address": "Yeldeğirmeni Sk.", "rating": 4.2},
        {"name": "Ac?badem Eczane", "type": "eczane", "lat": 40.9890, "lon": 29.0310, "address": "Ac?badem", "rating": 4.6},
        {"name": "Sahray?cedid Market", "type": "market", "lat": 40.9885, "lon": 29.0320, "address": "Sahray?cedid Cd.", "rating": 3.9},
    ],
    "beşiktaş": [
        {"name": "Kahve D�nyas?", "type": "kafe", "lat": 41.0442, "lon": 29.0101, "address": "Akaretler No:8", "rating": 4.1},
        {"name": "?stanbul Pub", "type": "bar", "lat": 41.0438, "lon": 29.0095, "address": "Barbaros Bulv.", "rating": 3.8},
        {"name": "Sultanahmet K�ftecisi", "type": "restaurant", "lat": 41.0450, "lon": 29.0110, "address": "Ertuğrul Sk.", "rating": 4.3},
        {"name": "Bebek Kahve", "type": "kafe", "lat": 41.0460, "lon": 29.0080, "address": "Bebek Cd.", "rating": 4.4},
        {"name": "Etiler Simit�i", "type": "restaurant", "lat": 41.0470, "lon": 29.0070, "address": "Etiler Cd.", "rating": 4.0},
        {"name": "Ortak�y B�fe", "type": "market", "lat": 41.0480, "lon": 29.0060, "address": "Ortak�y Cd.", "rating": 3.7},
        {"name": "Beşiktaş Eczane", "type": "eczane", "lat": 41.0445, "lon": 29.0098, "address": "Barbaros Bulv.", "rating": 4.5},
        {"name": "Bebek Park", "type": "park", "lat": 41.0465, "lon": 29.0075, "address": "Bebek", "rating": 4.3},
        {"name": "Levent ATM", "type": "atm", "lat": 41.0455, "lon": 29.0085, "address": "Levent Cd.", "rating": 5.0},
        {"name": "Ç?rağan Saray?", "type": "hotel", "lat": 41.0480, "lon": 29.0055, "address": "Ç?rağan Cd.", "rating": 4.9},
        {"name": "Barbaros Meyhanesi", "type": "restaurant", "lat": 41.0440, "lon": 29.0105, "address": "Barbaros Bulv.", "rating": 4.2},
        {"name": "Akaretler Kahve", "type": "kafe", "lat": 41.0443, "lon": 29.0100, "address": "Akaretler Cd.", "rating": 4.1},
        {"name": "Dikilitaş Eczane", "type": "eczane", "lat": 41.0435, "lon": 29.0115, "address": "Dikilitaş Sk.", "rating": 4.4},
        {"name": "Sinanpaşa Cafe", "type": "kafe", "lat": 41.0455, "lon": 29.0088, "address": "Sinanpaşa Cd.", "rating": 4.0},
    ],
    "�sk�dar": [
        {"name": "Çengelk�y Kahvesi", "type": "kafe", "lat": 41.0265, "lon": 29.0432, "address": "Çengelk�y Cd.", "rating": 4.4},
        {"name": "Pideci Hasan", "type": "restaurant", "lat": 41.0270, "lon": 29.0440, "address": "Çengelk�y Mah.", "rating": 4.2},
        {"name": "Beylerbeyi Saray? Cafe", "type": "kafe", "lat": 41.0280, "lon": 29.0425, "address": "Beylerbeyi", "rating": 4.3},
        {"name": "Altunizade Pide", "type": "restaurant", "lat": 41.0290, "lon": 29.0415, "address": "Altunizade Cd.", "rating": 4.1},
        {"name": "Üsk�dar Simit�i", "type": "market", "lat": 41.0268, "lon": 29.0430, "address": "Çengelk�y Cd.", "rating": 3.9},
        {"name": "Kuzguncuk Eczane", "type": "eczane", "lat": 41.0275, "lon": 29.0428, "address": "Kuzguncuk Sk.", "rating": 4.5},
        {"name": "Çengelk�y Sahil", "type": "park", "lat": 41.0260, "lon": 29.0435, "address": "Çengelk�y", "rating": 4.2},
        {"name": "Altunizade ATM", "type": "atm", "lat": 41.0288, "lon": 29.0410, "address": "Altunizade Cd.", "rating": 5.0},
        {"name": "?cadiye Cafe", "type": "kafe", "lat": 41.0272, "lon": 29.0435, "address": "?cadiye Sk.", "rating": 4.3},
        {"name": "Selimiye Eczane", "type": "eczane", "lat": 41.0285, "lon": 29.0420, "address": "Selimiye Sk.", "rating": 4.6},
    ],
    "şişli": [
        {"name": "Neşe D�r�m", "type": "restaurant", "lat": 41.0505, "lon": 28.9860, "address": "Halaskargazi Cd.", "rating": 4.0},
        {"name": "Glutensiz Cafe", "type": "kafe", "lat": 41.0510, "lon": 28.9855, "address": "?n�n� Cd.", "rating": 4.1},
        {"name": "Nişantaş? Kahve", "type": "kafe", "lat": 41.0515, "lon": 28.9850, "address": "Nişantaş? Cd.", "rating": 4.4},
        {"name": "Mecidiyek�y D�ner", "type": "restaurant", "lat": 41.0520, "lon": 28.9845, "address": "Mecidiyek�y Cd.", "rating": 4.2},
        {"name": "Abdi ?pek�i Cd. Cafe", "type": "kafe", "lat": 41.0508, "lon": 28.9858, "address": "Abdi ?pek�i Cd.", "rating": 4.3},
        {"name": "Şişli Eczane", "type": "eczane", "lat": 41.0512, "lon": 28.9853, "address": "Halaskargazi Cd.", "rating": 4.5},
        {"name": "Teşvikiye Park", "type": "park", "lat": 41.0518, "lon": 28.9848, "address": "Teşvikiye", "rating": 4.1},
        {"name": "?stanbul Lisesi", "type": "school", "lat": 41.0525, "lon": 28.9840, "address": "Cihangir", "rating": 4.6},
        {"name": "Şişli ATM", "type": "atm", "lat": 41.0505, "lon": 28.9862, "address": "Halaskargazi Cd.", "rating": 5.0},
        {"name": "Osmanbey Kafe", "type": "kafe", "lat": 41.0510, "lon": 28.9855, "address": "Osmanbey Sk.", "rating": 4.2},
        {"name": "Ma�ka Park", "type": "park", "lat": 41.0520, "lon": 28.9842, "address": "Ma�ka", "rating": 4.5},
        {"name": "Fulya Kahve", "type": "kafe", "lat": 41.0518, "lon": 28.9850, "address": "Fulya Cd.", "rating": 4.1},
    ],
    "fatih": [
        {"name": "S�leymaniye Kahvesi", "type": "kafe", "lat": 41.0167, "lon": 28.9612, "address": "S�leymaniye Mah.", "rating": 4.3},
        {"name": "Kuru Fasulye Ali", "type": "restaurant", "lat": 41.0155, "lon": 28.9620, "address": "Langa Cd.", "rating": 4.6},
        {"name": "Aksaray Pide", "type": "restaurant", "lat": 41.0150, "lon": 28.9630, "address": "Aksaray Cd.", "rating": 4.2},
        {"name": "Balat Kahve", "type": "kafe", "lat": 41.0145, "lon": 28.9640, "address": "Balat Cd.", "rating": 4.0},
        {"name": "Langa Kuru Fasulye", "type": "restaurant", "lat": 41.0160, "lon": 28.9618, "address": "Langa", "rating": 4.5},
        {"name": "Cerrahpaşa Eczane", "type": "eczane", "lat": 41.0162, "lon": 28.9615, "address": "Cerrahpaşa Cd.", "rating": 4.4},
        {"name": "Fatih Camii", "type": "mosque", "lat": 41.0152, "lon": 28.9635, "address": "Fatih", "rating": 4.8},
        {"name": "Karag�mr�k Pide", "type": "restaurant", "lat": 41.0148, "lon": 28.9645, "address": "Karag�mr�k", "rating": 4.1},
        {"name": "S�leymaniye Eczane", "type": "eczane", "lat": 41.0165, "lon": 28.9610, "address": "S�leymaniye", "rating": 4.3},
        {"name": "Vefa Boza", "type": "restaurant", "lat": 41.0158, "lon": 28.9622, "address": "Langa", "rating": 4.4},
    ],
    "sar?yer": [
        {"name": "Emirgan Korusu Cafe", "type": "kafe", "lat": 41.1080, "lon": 29.0560, "address": "Emirgan Korusu", "rating": 4.5},
        {"name": "?stinye Kahve", "type": "kafe", "lat": 41.1070, "lon": 29.0570, "address": "?stinye Cd.", "rating": 4.3},
        {"name": "Tarabya Meyhanesi", "type": "restaurant", "lat": 41.1090, "lon": 29.0550, "address": "Tarabya Cd.", "rating": 4.4},
        {"name": "B�y�kdere Cd. Cafe", "type": "kafe", "lat": 41.1060, "lon": 29.0580, "address": "B�y�kdere Cd.", "rating": 4.2},
        {"name": "Sar?yer Bal?k�?s?", "type": "restaurant", "lat": 41.1085, "lon": 29.0555, "address": "Sar?yer Cd.", "rating": 4.6},
        {"name": "Rumelifeneri Cafe", "type": "kafe", "lat": 41.1100, "lon": 29.0540, "address": "Rumelifeneri", "rating": 4.4},
        {"name": "Bah�ek�y Kahve", "type": "kafe", "lat": 41.1075, "lon": 29.0565, "address": "Bah�ek�y Sk.", "rating": 4.1},
        {"name": "?stinye Park ATM", "type": "atm", "lat": 41.1068, "lon": 29.0572, "address": "?stinye Park", "rating": 5.0},
        {"name": "Polonez Cafe", "type": "kafe", "lat": 41.1095, "lon": 29.0545, "address": "Polonez", "rating": 4.2},
    ],
    "beyoğlu": [
        {"name": "Kad?k�y Gastro Pub", "type": "bar", "lat": 41.0400, "lon": 28.9850, "address": "?stiklal Cd.", "rating": 4.1},
        {"name": "Çukurcuma Kahve", "type": "kafe", "lat": 41.0405, "lon": 28.9845, "address": "Çukurcuma", "rating": 4.3},
        {"name": "Asmal?mescit Cafe", "type": "kafe", "lat": 41.0402, "lon": 28.9848, "address": "Asmal?mescit Sk.", "rating": 4.4},
        {"name": "Galata Kulesi Cafe", "type": "kafe", "lat": 41.0410, "lon": 28.9840, "address": "Galata", "rating": 4.2},
        {"name": "Tarlabaş? Pide", "type": "restaurant", "lat": 41.0398, "lon": 28.9852, "address": "Tarlabaş? Cd.", "rating": 4.0},
        {"name": "Sishane Kahve", "type": "kafe", "lat": 41.0403, "lon": 28.9847, "address": "Sishane Sk.", "rating": 4.5},
        {"name": "Cihangir Cafe", "type": "kafe", "lat": 41.0408, "lon": 28.9842, "address": "Cihangir Sk.", "rating": 4.3},
        {"name": "?stiklal Cd. Bar", "type": "bar", "lat": 41.0401, "lon": 28.9849, "address": "?stiklal Cd.", "rating": 3.9},
        {"name": "Tomtom Kahve", "type": "kafe", "lat": 41.0406, "lon": 28.9844, "address": "Tomtom Sk.", "rating": 4.2},
        {"name": "Galata Cafe", "type": "kafe", "lat": 41.0412, "lon": 28.9838, "address": "Galata Kulesi Cd.", "rating": 4.1},
    ],
    "ataşehir": [
        {"name": "Kay?şdağ? Kahve", "type": "kafe", "lat": 40.9920, "lon": 29.1400, "address": "Kay?şdağ? Cd.", "rating": 4.1},
        {"name": "?�erenk�y Cafe", "type": "kafe", "lat": 40.9915, "lon": 29.1410, "address": "?�erenk�y Cd.", "rating": 4.2},
        {"name": "Kozyatağ? Coffee", "type": "kafe", "lat": 40.9910, "lon": 29.1420, "address": "Kozyatağ?", "rating": 4.4},
        {"name": "Ataşehir Pide", "type": "restaurant", "lat": 40.9925, "lon": 29.1395, "address": "Ataşehir", "rating": 4.0},
        {"name": "Bağdat Cd. Cafe", "type": "kafe", "lat": 40.9918, "lon": 29.1405, "address": "Bağdat Cd.", "rating": 4.3},
        {"name": "Şerifali Kahve", "type": "kafe", "lat": 40.9922, "lon": 29.1398, "address": "Şerifali Cd.", "rating": 4.1},
        {"name": "Yenidoğan Market", "type": "market", "lat": 40.9928, "lon": 29.1392, "address": "Yenidoğan", "rating": 3.8},
    ],
    "maltepe": [
        {"name": "Baş?b�y�k Kahve", "type": "kafe", "lat": 40.9500, "lon": 29.1500, "address": "Baş?b�y�k", "rating": 4.1},
        {"name": "Maltepe Sahil Cafe", "type": "kafe", "lat": 40.9495, "lon": 29.1510, "address": "Maltepe Sahil", "rating": 4.3},
        {"name": "Cevizli Pide", "type": "restaurant", "lat": 40.9505, "lon": 29.1495, "address": "Cevizli Cd.", "rating": 4.2},
        {"name": "Alt?n�ekmece Kahve", "type": "kafe", "lat": 40.9490, "lon": 29.1515, "address": "Alt?n�ekmece", "rating": 4.0},
        {"name": "Bağdat Cd. Maltepe", "type": "kafe", "lat": 40.9502, "lon": 29.1502, "address": "Bağdat Cd.", "rating": 4.2},
        {"name": "G�lsuyu Cafe", "type": "kafe", "lat": 40.9498, "lon": 29.1508, "address": "G�lsuyu", "rating": 4.1},
    ],
    "pendik": [
        {"name": "Şeyhli Kahve", "type": "kafe", "lat": 40.8800, "lon": 29.2300, "address": "Şeyhli Cd.", "rating": 4.0},
        {"name": "Pendik Sahil Cafe", "type": "kafe", "lat": 40.8795, "lon": 29.2310, "address": "Pendik Sahil", "rating": 4.2},
        {"name": "G��beyli Pide", "type": "restaurant", "lat": 40.8805, "lon": 29.2295, "address": "G��beyli", "rating": 4.1},
        {"name": "Velibaba Cafe", "type": "kafe", "lat": 40.8792, "lon": 29.2315, "address": "Velibaba", "rating": 4.3},
        {"name": "?�meler Kahve", "type": "kafe", "lat": 40.8798, "lon": 29.2305, "address": "?�meler", "rating": 4.4},
        {"name": "Kaynarca Market", "type": "market", "lat": 40.8810, "lon": 29.2290, "address": "Kaynarca", "rating": 3.9},
    ],
    "tuzla": [
        {"name": "Şifa Kahve", "type": "kafe", "lat": 40.8600, "lon": 29.3000, "address": "Şifa Cd.", "rating": 4.1},
        {"name": "Menderes Cafe", "type": "kafe", "lat": 40.8595, "lon": 29.3010, "address": "Menderes Cd.", "rating": 4.2},
        {"name": "?stiklal Tuzla Cafe", "type": "kafe", "lat": 40.8605, "lon": 29.2995, "address": "?stiklal Cd.", "rating": 4.0},
        {"name": "G�zelyal? Kahve", "type": "kafe", "lat": 40.8592, "lon": 29.3015, "address": "G�zelyal?", "rating": 4.3},
        {"name": "Tuzla Pide", "type": "restaurant", "lat": 40.8598, "lon": 29.3005, "address": "Tuzla Cd.", "rating": 4.2},
    ],
    "ey�psultan": [
        {"name": "Piyer Loti Kahve", "type": "kafe", "lat": 41.0500, "lon": 28.9300, "address": "Piyer Loti Cd.", "rating": 4.4},
        {"name": "Alibeyk�y Cafe", "type": "kafe", "lat": 41.0495, "lon": 28.9310, "address": "Alibeyk�y", "rating": 4.1},
        {"name": "Rami Pide", "type": "restaurant", "lat": 41.0505, "lon": 28.9295, "address": "Rami", "rating": 4.2},
        {"name": "Ey�psultan Kahve", "type": "kafe", "lat": 41.0492, "lon": 28.9315, "address": "Ey�p Sultan Cd.", "rating": 4.3},
        {"name": "Silahtarağa Cafe", "type": "kafe", "lat": 41.0498, "lon": 28.9305, "address": "Silahtarağa", "rating": 4.0},
        {"name": "G�zeltepe Kahve", "type": "kafe", "lat": 41.0488, "lon": 28.9320, "address": "G�zeltepe", "rating": 4.1},
    ],
    "bak?rk�y": [
        {"name": "Yeşilk�y Kahve", "type": "kafe", "lat": 40.9800, "lon": 28.8200, "address": "Yeşilk�y Cd.", "rating": 4.3},
        {"name": "Florya Cafe", "type": "kafe", "lat": 40.9795, "lon": 28.8210, "address": "Florya Cd.", "rating": 4.2},
        {"name": "Atak�y Pide", "type": "restaurant", "lat": 40.9805, "lon": 28.8195, "address": "Atak�y", "rating": 4.1},
        {"name": "Sefak�y Kahve", "type": "kafe", "lat": 40.9792, "lon": 28.8215, "address": "Sefak�y", "rating": 4.0},
        {"name": "Cennet Cafe", "type": "kafe", "lat": 40.9798, "lon": 28.8205, "address": "Cennet", "rating": 4.2},
        {"name": "Bak?rk�y Eczane", "type": "eczane", "lat": 40.9802, "lon": 28.8202, "address": "Bak?rk�y", "rating": 4.5},
        {"name": "Osmaniye Kahve", "type": "kafe", "lat": 40.9795, "lon": 28.8212, "address": "Osmaniye Sk.", "rating": 4.1},
    ],
    "beylikd�z�": [
        {"name": "Adnan Kahveci Cafe", "type": "kafe", "lat": 41.0100, "lon": 28.6400, "address": "Adnan Kahveci Cd.", "rating": 4.2},
        {"name": "Yakuplu Kahve", "type": "kafe", "lat": 41.0095, "lon": 28.6410, "address": "Yakuplu", "rating": 4.1},
        {"name": "Beylikd�z� Cafe", "type": "kafe", "lat": 41.0105, "lon": 28.6395, "address": "Beylikd�z� Cd.", "rating": 4.3},
        {"name": "Marina Cafe", "type": "kafe", "lat": 41.0092, "lon": 28.6415, "address": "Marina", "rating": 4.4},
        {"name": "Barbaros Pide", "type": "restaurant", "lat": 41.0098, "lon": 28.6405, "address": "Barbaros Cd.", "rating": 4.2},
        {"name": "G�rsel Kahve", "type": "kafe", "lat": 41.0102, "lon": 28.6402, "address": "G�rsel Cd.", "rating": 4.1},
    ],
}

# =============================================================================
# YARDIMCI FONKS?YONLAR
# =============================================================================

def normalize(text: str) -> str:
    """Metni normalize eder."""
    text = text.lower()
    replacements = {"?": "i", "ş": "s", "ğ": "g", "�": "u", "�": "o", "�": "c"}
    for turkish, ascii_char in replacements.items():
        text = text.replace(turkish, ascii_char)
    return text

def normalize_poi_type(poi_type: str) -> Optional[str]:
    """POI tipini normalize eder."""
    poi_norm = normalize(poi_type)
    
    for poi_key, poi_data in POI_TYPES.items():
        if poi_norm in poi_data["aliases"] or poi_key in poi_norm:
            return poi_key
    
    return None

def find_location(query: str, districts: Dict) -> Optional[Dict]:
    """Sorguya uygun lokasyonu bulur."""
    normalized = normalize(query)
    
    # Suffix kald?r
    suffixes = ["da", "de", "ta", "te"]
    base = normalized
    for suffix in suffixes:
        if normalized.endswith(suffix):
            base = normalized[:-len(suffix)]
            break
    
    if base in districts:
        return districts[base]
    
    for key in districts:
        if normalize(key) in normalized or normalized in normalize(key):
            return districts[key]
    
    return None


# =============================================================================
# TAM LOKASYON + POI MOTORU
# =============================================================================

class CompleteLocationPOIEngine:
    """
    Istanbul icin lokasyon + POI cozumleme motoru.

    Kapsam:
    - Ilce tanima (37 ilce)
    - POI tipi tanima (15 tip)
    - Ilce bazli POI listesi dondurme

    Not:
    - Mahalle/sokak cozumleme bu sinifta yoktur.
    - Mahalle/sokak analizi icin `detailed_location_engine.py` kullanilmalidir.
    """
    
    def __init__(self):
        self.districts = ISTANBUL_DISTRICTS
        self.poi_types = POI_TYPES
        self.poi_db = POI_DATABASE
        self.all_locations: Set[str] = set()
        
        # ?l�eleri indexle
        for key in self.districts:
            self.all_locations.add(key)
            self.all_locations.add(normalize(key))
        
        print(f"[CompleteEngine] {len(self.districts)} il�e, {len(self.poi_types)} POI tipi, {sum(len(v) for v in self.poi_db.values())} mekan")
    
    def parse_query(self, query: str) -> Dict:
        """
        Sorguyu ��z�mler.
        
        Args:
            query: "Kad?k�yde kafe" veya "Beşiktaşta bar Moda'da"
        
        Returns:
            {
                "success": True,
                "query": "...",
                "location": {...},  # Ana lokasyon
                "poi_type": "kafe",  # POI tipi
                "poi_aliases": [...],  # OSM tagler
                "pois": [...],  # Sonu�lar
                "result_count": 5
            }
        """
        query = query.strip()
        if not query:
            return {"success": False, "error": "Boş sorgu", "pois": []}
        
        # Sorguyu kelimelere ay?r
        words = query.split()
        
        location = None
        poi_type = None
        additional_locations = []  # ?kinci lokasyon i�in
        
        # Her kelimeyi kontrol et
        for i, word in enumerate(words):
            # Lokasyon kontrol�
            loc = find_location(word, self.districts)
            if loc:
                if location is None:
                    location = loc
                else:
                    additional_locations.append(loc)
                continue
            
            # POI tipi kontrol�
            normalized_type = normalize_poi_type(word)
            if normalized_type:
                poi_type = normalized_type
                continue
        
        # Sonu�lar? ara
        pois = []
        
        if location and poi_type:
            # ?l�ede POI ara
            loc_key = location.get("name", "").lower()
            loc_norm = normalize(loc_key)
            
            # ?l�e anahtar?n? bul
            district_key = None
            for d in self.districts:
                if normalize(d) == loc_norm or normalize(self.districts[d]["name"]) == loc_norm:
                    district_key = d
                    break
            
            if district_key and district_key in self.poi_db:
                for poi in self.poi_db[district_key]:
                    if poi["type"] == poi_type or poi_type in POI_TYPES.get(poi["type"], {}).get("aliases", []):
                        pois.append(poi)
        
        elif location:
            # Sadece lokasyon verildi, t�m POI'leri getir
            loc_key = location.get("name", "").lower()
            loc_norm = normalize(loc_key)
            
            district_key = None
            for d in self.districts:
                if normalize(d) == loc_norm or normalize(self.districts[d]["name"]) == loc_norm:
                    district_key = d
                    break
            
            if district_key and district_key in self.poi_db:
                pois = self.poi_db[district_key][:20]  # Max 20 sonu�
        
        elif poi_type:
            # Sadece POI tipi verildi, t�m il�elerde ara
            for district, pois_list in self.poi_db.items():
                for poi in pois_list:
                    if poi["type"] == poi_type:
                        pois.append(poi)
        
        # POI tipi bilgilerini ekle
        poi_info = self.poi_types.get(poi_type, {}) if poi_type else {}
        
        return {
            "success": len(pois) > 0 or location is not None,
            "query": query,
            "location": location,
            "poi_type": poi_type,
            "poi_type_name": poi_info.get("description", ""),
            "osm_tags": poi_info.get("osm_tags", []),
            "pois": pois[:10],  # Max 10 sonu�
            "result_count": len(pois),
            "additional_locations": additional_locations,
        }
    
    def get_stats(self) -> Dict:
        """?statistikler."""
        return {
            "districts": len(self.districts),
            "poi_types": len(self.poi_types),
            "total_pois": sum(len(v) for v in self.poi_db.values()),
            "districts_with_pois": len(self.poi_db),
        }


# =============================================================================
# TEST
# =============================================================================

def test_complete_engine():
    """Test."""
    engine = CompleteLocationPOIEngine()
    
    print("=" * 60)
    print("TAM LOKASYON + POI MOTORU TEST")
    print("=" * 60)
    
    # Test sorgular?
    test_queries = [
        "Kad?k�yde kafe",
        "Beşiktaşta bar",
        "Üsk�dar cafe",
        "Şişli restaurant",
        "Fatih pide",
        "sar?yer kahve",
        "kad?k�y eczane",
        "maltepe park",
        "beyoğlu pub",
        "ataşehir market",
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"SORGU: {query}")
        print("="*50)
        
        result = engine.parse_query(query)
        
        if result["success"]:
            loc = result.get("location", {})
            loc_name = loc.get("name", "T�m ?stanbul") if loc else "T�m ?stanbul"
            poi_type = result.get("poi_type", "genel")
            poi_name = result.get("poi_type_name", "")
            count = result["result_count"]
            
            print(f"📍 Lokasyon: {loc_name}")
            print(f"🏷️ POI Tip: {poi_type} ({poi_name})")
            print(f"📊 Sonu�: {count} mekan")
            
            if result["pois"]:
                print("\n🏪 Mekanlar:")
                for i, poi in enumerate(result["pois"][:5], 1):
                    print(f"  {i}. {poi['name']}")
                    print(f"     📌 {poi['address']} | ⭐ {poi['rating']}")
        else:
            print(f"❌ Sonu� bulunamad?: {result.get('error')}")
    
    print("\n" + "=" * 60)
    stats = engine.get_stats()
    print("?STAT?ST?KLER:")
    print(f"  - ?l�e: {stats['districts']}")
    print(f"  - POI Tip: {stats['poi_types']}")
    print(f"  - Toplam Mekan: {stats['total_pois']}")
    print(f"  - Veri olan il�e: {stats['districts_with_pois']}")
    print("=" * 60)


if __name__ == "__main__":
    test_complete_engine()
