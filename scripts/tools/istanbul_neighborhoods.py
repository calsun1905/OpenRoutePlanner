"""
istanbul_neighborhoods.py - ?stanbul Mahalleleri Veritaban?

OSM/Nominatim API'den �ekilen ?stanbul mahalle ve b�lge verileri.
"""
from typing import Dict, List, Optional

ISTANBUL_NEIGHBORHOODS = {
    # ============================================================
    # BEŞ?KTAŞ ?LÇES?
    # ============================================================
    "beşiktaş": {
        "il": "istanbul",
        "il�e": "beşiktaş",
        "mahalleler": [
            "Abbasağa", "Akağlar", "Arnavutk�y", "Bebek", "Cihann�ma", 
            "Ertuğrul", "Fbbek", "Kuru�eşme", "KÜLTÜR", "Levent", 
            "Merkez", "Mimaroba", "Nişantepe", "Ortak�y", "Serencebey", 
            "Sinanpaşa", "T�rkb�k�", "Ulubatl?", "Yeni", "Y?ld?z"
        ],
        "b�lgeler": ["Levent", "Etiler", "Ortak�y", "Arnavutk�y", "Bebek", "Yeni Levent"]
    },
    
    # ============================================================
    # KADIKÖY ?LÇES?
    # ============================================================
    "kad?k�y": {
        "il": "istanbul",
        "il�e": "kad?k�y",
        "mahalleler": [
            "Ac?badem", "Bostanc?", "Caddebostan", "Caferağa", "Denizalg?n?",
            " Erenk�y", "Feneryolu", "F?st?kağac?", "G�ztepe", "Hasanpaşa",
            "Haydarpaşa", "Kozyatağ?", "K���kyal?", "Moda", "Rasimpaşa",
            "Sahray?cedid", "Selami�eşme", "Z�mr�tevler"
        ],
        "b�lgeler": ["Moda", "Bostanc?", "G�ztepe", "Kozyatağ?", "K���kyal?", "Haydarpaşa", "Ac?badem"]
    },
    
    # ============================================================
    # ÜSKÜDAR ?LÇES?
    # ============================================================
    "�sk�dar": {
        "il": "istanbul",
        "il�e": "�sk�dar",
        "mahalleler": [
            "Ac?badem", "Altunizade", "Aziz Mahmut H�dayi", "Beylerbeyi", "Burhaniye",
            "Cengelk�y", "Çengelk�y", "Emirgan", "G�zeltepe", "ICBalkon",
            "Kandilli", "K?s?kl?", "Kuleli", " Kuzguncuk", "Mimar Sinan",
            "Moda", "Nakkaş", "Petek", "Selimiye", "Tantavi", "Tokatk�y",
            "Yavuzt�rk", "Zeynep Kamil"
        ],
        "b�lgeler": ["Altunizade", "Çengelk�y", "Beylerbeyi", "Kuzguncuk", "Emirgan", "Tarabya"]
    },
    
    # ============================================================
    # Ş?ŞL? ?LÇES?
    # ============================================================
    "şişli": {
        "il": "istanbul",
        "il�e": "şişli",
        "mahalleler": [
            "Bozlu", "Cihangir", "Dar�şşafaka", "Ferik�y", "F?nd?kl?",
            "Halide Edip Ad?var", "Harbiye", "?n�n�", "?tibariye", "Kaptanpaşa",
            "Kuştepe", "Mahalle", "Mehmet Akif Ersoy", "Merkez", "Nisantas?",
            "Osmanbey", "Pangalt?", "Sanayi", "Seyrige", "Şişli", "Tepebaş?"
        ],
        "b�lgeler": ["Nişantaş?", "Mecidiyek�y", "Osmanbey", "Ferik�y", "Cihangir"]
    },
    
    # ============================================================
    # FAT?H ?LÇES?
    # ============================================================
    "fatih": {
        "il": "istanbul",
        "il�e": "fatih",
        "mahalleler": [
            "Aksaray", "Balat", "Beyaz?t", "Cerrahpaşa", "Çapa",
            "Emniyet", "Fener", "Haseki", "Karag�mr�k", "Kocamustafapaşa",
            "Langa", "Milletedar", "Musevi", "Rumelihisar?", "Samatya",
            "Sara�hane", "S�leymaniye", "S�tl�ce", "Tayakad?n", "Topkapi", "Vefa",
            "Yedikule", "Zeyrek"
        ],
        "b�lgeler": ["S�leymaniye", "Balat", "Fener", "Samatya", "Karag�mr�k", "Langa"]
    },
    
    # ============================================================
    # BEYOGLU ?LÇES?
    # ============================================================
    "beyoğlu": {
        "il": "istanbul",
        "il�e": "beyoğlu",
        "mahalleler": [
            "Arap�iftliği", "Asmal?mescit", "Bedrettin", "Bostan", "Cihangir",
            "Çatma", "Demirci", "D�şeme", "Ertuğrul", "Firuzağa", "Hac?mimi",
            "Hal?c?oğlu", "Hamidiye", "H�srev", "?stiklal", "Kalyoncu", "Kamer",
            "K?l?�alipaşa", "Kocatepe", "Kurd", "Mimar", "Mimar Sinan", "Museh?",
            "Piyalepaşa", "Sahne", "Sal?", "Saray", "S?raserviler", "Şahkulu",
            "Şaksahane", "Tarlabaş?", "Tersane", "Tomtom", "Yenişehir"
        ],
        "b�lgeler": ["?stiklal Caddesi", "Tarlabaş?", "Cihangir", "Asmal?mescit", "Galata"]
    },
    
    # ============================================================
    # BAKIRKÖY ?LÇES?
    # ============================================================
    "bak?rk�y": {
        "il": "istanbul",
        "il�e": "bak?rk�y",
        "mahalleler": [
            "Atak�y", "Bak?rk�y", "Bas?nk�y", "Bat?", "Boyal?ca",
            "Cevizlik", "Degirmen", "Kartaltepe", "Kaynarca", "K?razl?",
            "Kumkap?", "Mek", "Osmaniye", "Pazaryeri", "Sak?zağac?",
            "Sanayi", "Seyrantepe", "Sofor", "Yeni", "Yeşilk�y", "Zeytinlik"
        ],
        "b�lgeler": ["Atak�y", "Yeşilk�y", "Florya", "Zeytinlik", "Kartaltepe"]
    },
    
    # ============================================================
    # ZEYT?NBURNU ?LÇES?
    # ============================================================
    "zeytinburnu": {
        "il": "istanbul",
        "il�e": "zeytinburnu",
        "mahalleler": [
            "Beyaz?t", "Ç?rp?c?", "Deniz", "G�kalp", "?lky?ld?z",
            "Kazl?�eşme", "Merkez", "N.topkap?", "Seyitnizam", "Şehit", "Yenidoğan",
            "Yeşil", "Zeytin", "Zeytinburnu"
        ],
        "b�lgeler": ["Kazl?�eşme", "Zeytinburnu", "Ç?rp?c?"]
    },
    
    # ============================================================
    # EYÜPSULTAN ?LÇES?
    # ============================================================
    "ey�psultan": {
        "il": "istanbul",
        "il�e": "ey�psultan",
        "mahalleler": [
            "Akşemsettin", "Alibeyk�y�", "Çiftlik", "Defterdar", "D�ğmeciler",
            "Emir", "Ey�psultan", "G�kt�rk", "G�zel", "?hsaniye", "?slambey",
            "Karadeniz", "Kemer", "Mimar", "Nişanca", "Otağ", "Piri",
            "Rami", "Sakarya", "S�tl�ce", "Top�ular", "Yeşil", "Yusufpaşa"
        ],
        "b�lgeler": ["Alibeyk�y�", "G�kt�rk", "Rami", "Karadeniz", "S�tl�ce"]
    },
    
    # ============================================================
    # SARIYER ?LÇES?
    # ============================================================
    "sar?yer": {
        "il": "istanbul",
        "il�e": "sar?yer",
        "mahalleler": [
            "Ayazağa", "B�y�kdere", "Cumhuriyet", "Dar�şşafaka", "Demirciler",
            "Emirgân", "Erikap?", "Fera", "F?nd?kzade", "G�m�şdere", "Huzur",
            "?stinye", "K?s?r", "Kuru�eşme", "Murat", "PTT", "Reşit", "Rumeli",
            "Rumeli Kavağ?", "Rumelifeneri", "Sariyer", "Sehrin", "Seyrantepe",
            "Tarabya", "Tokat", "Yeni", "Yukar?", "Zekeriyak�y"
        ],
        "b�lgeler": ["?stinye", "Tarabya", "Emirgan", "Sar?yer Merkez", "Zekeriyak�y", "B�y�kdere"]
    },
    
    # ============================================================
    # KAĞITHANE ?LÇES?
    # ============================================================
    "kağ?thane": {
        "il": "istanbul",
        "il�e": "kağ?thane",
        "mahalleler": [
            "Armaganevler", "Çeliktepe", "Deresi", "Emniyet", "G�ltepe",
            "G�rsel", "Hamidiye", "Harmandantepe", "H�rriyet", "Kağ?thane",
            "Karaağa�", "Keper", "K?l?�", "Narter", "Orta", "Sadabad",
            "Şair", "Seyriftokuş", "Sultaniye", "Talatpaşa", "T�rkel", "Yayla", "Yeşilce"
        ],
        "b�lgeler": ["Seyrantepe", "Kağ?thane", "G�ltepe", "Çağlayan"]
    },
    
    # ============================================================
    # KARTAL ?LÇES?
    # ============================================================
    "kartal": {
        "il": "istanbul",
        "il�e": "kartal",
        "mahalleler": [
            "Cevizli", "G�m�ş", "H�rriyet", "Kara", "Karl?ktepe", "Kartal",
            "K?n?k", "Kurfal?", "M.topkap?", "Orhangazi", "Petrol", "Rahmi",
            "Safa", "Saray", "Şifa", "Topselvi", "Uğur", "Yakac?k", "Yal?",
            "Yeni", "Yunus", "Zafer", "Çavuşbaş?"
        ],
        "b�lgeler": ["Kartal Merkez", "Yakac?k", "Soğanl?k", "Maltepe"]
    },
    
    # ============================================================
    # PENDIK ?LÇES?
    # ============================================================
    "pendik": {
        "il": "istanbul",
        "il�e": "pendik",
        "mahalleler": [
            "Ahmet", "Bah�elievler", "Çam", "Ç?nardere", "Denizciler",
            "Emir", "Ert�rk", "Esenler", "Fevzi", "G�rgen", "G�lyali",
            "G�neşli", "Harmandere", "?cadiye", "?�meler", "Kaynarca",
            "K?rm?z?", "Kurtk�y", "Orta", "Ramazanoğlu", "Sanayi", "Şeyhli",
            "Tellikk?z", "Velibaba", "Yeni", "Yeşil", "Yunan", "Zerkes"
        ],
        "b�lgeler": ["Pendik Merkez", "Kurtk�y", "Tuzla", "?�meler", "Çamlica"]
    },
    
    # ============================================================
    # MALTEPE ?LÇES?
    # ============================================================
    "maltepe": {
        "il": "istanbul",
        "il�e": "maltepe",
        "mahalleler": [
            "Alt?n", "Ayy?ld?z", "Bağ", "Baş?b�y�k", "B�y�kyal?", "Caml?ca",
            "Ç?nar", "Demircilik", "Dumlup?nar", "F?rat", "Gazi", "G�l",
            "G�lensah", "?de", "K���k", "Mehmet", "Orta", "Seyit", "S?ras�ğ�tler",
            "Şimşir", "Yal?", "Yamanevler", "Yeni", "Yeşil", "Z?rhl?"
        ],
        "b�lgeler": ["Maltepe Merkez", "Baş?b�y�k", "B�y�kyal?", "Ataşehir"]
    },
    
    # ============================================================
    # TUZLA ?LÇES?
    # ============================================================
    "tuzla": {
        "il": "istanbul",
        "il�e": "tuzla",
        "mahalleler": [
            "Anadolu", "Ayd?nl?", "Birlik", "Çay?r", "Deri", "Dumlup?nar",
            "Emek", "Fevzi", "F?rat", "G�m�ş", "?�meler", "Kara",
            "Kurnak�y", "Kurtk�y", "Mimar", "Orhan", "Postah", "Sanayi",
            "Şifa", "Tuzla", "Yaylак", "Yeni", "Yeşil", "Ziya"
        ],
        "b�lgeler": ["Tuzla Merkez", "?�meler", "Kurtk�y", "Ayd?nl?"]
    },
    
    # ============================================================
    # ATAŞEHIR ?LÇES?
    # ============================================================
    "ataşehir": {
        "il": "istanbul",
        "il�e": "ataşehir",
        "mahalleler": [
            "Ac?badem", "Aş?k", "Barbaros", "Fetih", "?n�n�", "?�erenk�y",
            "Kay?şdağ?", "K���k", "Mevlana", "Moda", "Örnek", "Sahra",
            "Şerifali", "Yeni", "Yeni Çaml?ca", "Yeşil", "Z?pk?n"
        ],
        "b�lgeler": ["?�erenk�y", "Kay?şdağ?", "Barbaros", "Ataşehir"]
    },
    
    # ============================================================
    # ÜMRANIYE ?LÇES?
    # ============================================================
    "�mraniye": {
        "il": "istanbul",
        "il�e": "�mraniye",
        "mahalleler": [
            "Alt?nşehir", "Armağan", "Aş?k", "Dumlup?nar", "Elmal?kent",
            "Esenşehir", "Hat?rc?", "Hekim", "Ihlamur", "?kbal", "?lky?l",
            "Kâğ?t", "Kaz?m", "Madall?", "Mimar", "Nakliyeciler", "Necip",
            "Onur", "Parseller", "Sanayi", "Tatl?su", "Tepe�st�", "Top�ular",
            "Yamanevler", "Yeni", "Yeşil", "Y�cel", "Ziver"
        ],
        "b�lgeler": ["Ümraniye Merkez", "Tepe�st�", "Çakmak", "Dudullu"]
    },
    
    # ============================================================
    # SANCAKTEPE ?LÇES?
    # ============================================================
    "sancaktepe": {
        "il": "istanbul",
        "il�e": "sancaktepe",
        "mahalleler": [
            "Abdurrahman", "Aydos", "Ey�p", "Fatih", "Hayri", "Hilal",
            "?n�n�", "Kale", "Karadeniz", "Kemal", "K�roğlu", "Mehd?",
            "Mehmet", "Merve", "Orta", "Osman", "Sar?gazi", "Şahin",
            "Taşdelen", "Yenidoğan", "Yeni", "Yunus", "Zamanta"
        ],
        "b�lgeler": ["Sar?gazi", "Sancaktepe", "Taşdelen", "K�roğlu"]
    },
    
    # ============================================================
    # ÇEKMEKÖY ?LÇES?
    # ============================================================
    "�ekmek�y": {
        "il": "istanbul",
        "il�e": "�ekmek�y",
        "mahalleler": [
            "Alemdağ", "Ayd?n", "Başbuğ", "Çaml?k", "Çekmek�y", "Ekşioğlu",
            "G�rel", "H�davendigar", "?mam", "Kalkan", "K?rkp?nar", "Koşuyolu",
            "Madimal?", "Mehmet", "Merve", "Mimar", "Nişantepe", "Ömer",
            "Reşat", "Saray", "Sultan�iftliği", "Tepe�st�", "Yayla", "Yenidoğan",
            "Yeşil", "Y?lan", "Z?pk?n"
        ],
        "b�lgeler": ["Çekmek�y Merkez", "Sultan�iftliği", "Koşuyolu"]
    },
    
    # ============================================================
    # BEYL?KDÜZÜ ?LÇES?
    # ============================================================
    "beylikd�z�": {
        "il": "istanbul",
        "il�e": "beylikd�z�",
        "mahalleler": [
            "Adnan", "Bar?ş", "B�y�kşehir", "Cumhuriyet", "Dere", "DOKTOR",
            "Eski", "G�rsel", "Kavakl?", "Kemal", "Kolay", "Marmara",
            "Merkez", "P?nar", "Sahil", "Sanayi", "Yakuplu", "Yeni",
            "Yeşil", "Zafer"
        ],
        "b�lgeler": ["Beylikd�z� Merkez", "Yakuplu", "B�y�kşehir", "G�rsel"]
    },
    
    # ============================================================
    # BAĞCILAR ?LÇES?
    # ============================================================
    "bağc?lar": {
        "il": "istanbul",
        "il�e": "bağc?lar",
        "mahalleler": [
            "Ar?", "At?şalan?", "Bağc?lar", "Barbaros", "Barlas", "Başak",
            "Ç?nar", "Demirkap?", "Emniyet", "Erler", "Fevzi", "G�man",
            "H�rriyet", "?n�n�", "Karadeniz", "Kemal", "K?ra�", "Kiraz",
            "K�yi", "Mahmut", "Merkez", "Nami", "Necip", "Oz", "Sancak",
            "Sevgi", "Sultan", "Yavuz", "Yedikule", "Yenig�n", "Yeşil", "Y?ld?z"
        ],
        "b�lgeler": ["Bağc?lar Merkez", "Mahmutbey", "K?ra�", "Kiraz"]
    },
    
    # ============================================================
    # BAYRAMPAŞA ?LÇES?
    # ============================================================
    "bayrampaşa": {
        "il": "istanbul",
        "il�e": "bayrampaşa",
        "mahalleler": [
            "Cevat", "Demet", "Edirne", "Erg�n", "?smet", "Kamera",
            "Kartaltepe", "K?ra�", "Kocatepe", "Menderes", "Merkez", "NARLIDERE",
            "Osmangazi", "Sait", "Sanayi", "Terazidere", "Yenidoğan", "Yeşil",
            "Y?ld?r?m", "Y?ld?z", "Yunus", "Zafer"
        ],
        "b�lgeler": ["Bayrampaşa Merkez", "Kartaltepe", "K?ra�", "Terazidere"]
    },
    
    # ============================================================
    # GÜNGÖREN ?LÇES?
    # ============================================================
    "g�ng�ren": {
        "il": "istanbul",
        "il�e": "g�ng�ren",
        "mahalleler": [
            "Ak?n", "Barbaros", "B�y�k", "Cevher", "G�neş", "G�ng�ren",
            "G�ven", "Habib", "H�rriyet", "?stanbul", "K mare", "Kemer",
            "Mehmet", "Merkez", "Mustafa", "Nail", "Sancak", "Seyfullah",
            "Sultan�iftliği", "Yavuz", "Yeşil", "Zafer"
        ],
        "b�lgeler": ["G�ng�ren Merkez", "G�neş", "Mustafa"]
    },
    
    # ============================================================
    # ESENLER ?LÇES?
    # ============================================================
    "esenler": {
        "il": "istanbul",
        "il�e": "esenler",
        "mahalleler": [
            "Alt?n", "At?şalan?", "Birlik", "Çifte", "Davy", "Emniyet",
            "Erler", "Esenler", "Fevzi", "Hava", "Kaz?m", "Kemal",
            "K?ra�", "Menderes", "Merkez", "Oruc", "Ozan", "Şehit", "Tuna",
            "Yavuz", "Yeni", "Yeşil", "Y?ld?r?m", "Y?ld?z", "Yunus"
        ],
        "b�lgeler": ["Esenler Merkez", "K?ra�", "At?şalan?", "Ozan"]
    },
    
    # ============================================================
    # S?L?VR? ?LÇES?
    # ============================================================
    "silivri": {
        "il": "istanbul",
        "il�e": "silivri",
        "mahalleler": [
            "Alibey", "B�y�k", "Canta", "Çay?rdere", "Çelik", "Çukuryurt",
            "Değirmenk�y", "Dere", "Ekşior", "Fener", "Gazitepe", "G�ndoğdu",
            "G�m�şyaka", "Habibler", "H�rriyet", "?hsaniye", "?lky?l", "Kad?k�y",
            "Kalk?n", "Karl?", "Kavakl?", "Kemal", "K?r?", "Kumburgaz",
            "Marmara", "Mithat", "Murat", "P?narca", "Sait", "Sanayi",
            "Selimpaşa", "Silivri", "Sinek", "Sofular", "Şahin", "Tap",
            "Yaz?", "Yenik�y", "Yeşil", "Y?ld?z", "Yusuf"
        ],
        "b�lgeler": ["Silivri Merkez", "Selimpaşa", "Kumburgaz", "Marmara"]
    },
    
    # ============================================================
    # Ş?LE ?LÇES?
    # ============================================================
    "şile": {
        "il": "istanbul",
        "il�e": "şile",
        "mahalleler": [
            "Ahmet", "Ağva", "B?�k?dere", "Cumhuriyet", "Çelebi", "Davutlar",
            "Değirmenci", "Doğanc?l?", "G�k�eali", "G�m�şyaka", "?sa", "Kabakoz",
            "Karaağa�", "Kumburgaz", "K�knar", "Merkez", "Oz", "Sofu",
            "Şahin", "Şile", "Tel", "Yanov", "Yaz?", "Yeni", "Yeşil", "Yuva"
        ],
        "b�lgeler": ["Şile Merkez", "Ağva", "Kumburgaz", "Karaağa�"]
    },
}

def search_neighborhood(location: str) -> dict:
    """Mahalle/b�lge ara."""
    normalized = location.lower()
    
    # ?l�e anahtarlar?nda ara (orijinal haliyle)
    for key in ISTANBUL_NEIGHBORHOODS:
        if key in normalized or normalized in key:
            return ISTANBUL_NEIGHBORHOODS[key]
    
    # Normalized versiyonla dene
    normalized2 = normalized.replace("?", "i").replace("ş", "s").replace("ğ", "g").replace("�", "u").replace("�", "o").replace("�", "c")
    if normalized2 in ISTANBUL_NEIGHBORHOODS:
        return ISTANBUL_NEIGHBORHOODS[normalized2]
    
    # Prefix eşleşme
    for key in ISTANBUL_NEIGHBORHOODS:
        if key.startswith(normalized2):
            return ISTANBUL_NEIGHBORHOODS[key]
    
    # Mahalle ara
    for district, data in ISTANBUL_NEIGHBORHOODS.items():
        for m in data.get("mahalleler", []):
            m_norm = m.lower().replace("?", "i").replace("ş", "s")
            if m_norm in normalized2 or normalized2 in m_norm:
                return {
                    "mahalle": m,
                    "il�e": district,
                    **data
                }
    
    return None

def get_all_districts() -> List[str]:
    """T�m il�e isimlerini d�nd�r�r."""
    return list(ISTANBUL_NEIGHBORHOODS.keys())

def get_district_info(district: str) -> Optional[dict]:
    """?l�e bilgisi d�nd�r�r."""
    normalized = district.lower().replace("?", "i").replace("ş", "s").replace("ğ", "g").replace("�", "u").replace("�", "o").replace("�", "c")
    # Doğrudan eşleşme
    if normalized in ISTANBUL_NEIGHBORHOODS:
        return ISTANBUL_NEIGHBORHOODS[normalized]
    # Prefix eşleşme
    for key in ISTANBUL_NEIGHBORHOODS:
        if key.startswith(normalized):
            return ISTANBUL_NEIGHBORHOODS[key]
    return None

def test_istanbul_neighborhoods():
    """Test."""
    print("=" * 60)
    print("?STANBUL MAHALLELER? TEST")
    print("=" * 60)
    
    # ?l�e say?s?
    districts = get_all_districts()
    print(f"\nToplam il�e: {len(districts)}")
    
    # ?lk birka� il�enin bilgisini g�ster
    for d in list(ISTANBUL_NEIGHBORHOODS.keys())[:5]:
        info = ISTANBUL_NEIGHBORHOODS[d]
        print(f"\n{d.upper()}: {len(info.get('mahalleler', []))} mahalle")
        print(f"  Örnek mahalleler: {info.get('mahalleler', [])[:5]}")
    
    # Arama testleri
    print("\n" + "=" * 60)
    print("ARAMA TESTLER?")
    print("=" * 60)
    
    for query in ["kad?k�y", "levent", "tarabya", "bostanc?", "�sk�dar"]:
        result = search_neighborhood(query)
        if result:
            il = result.get("il", "")
            il�e = result.get("il�e", "")
            print(f"\n'{query}' → il: {il}, il�e: {il�e}")
        else:
            print(f"\n'{query}' → bulunamad?")

if __name__ == "__main__":
    test_istanbul_neighborhoods()
