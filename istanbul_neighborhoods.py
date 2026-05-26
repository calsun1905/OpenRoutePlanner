"""
istanbul_neighborhoods.py - İstanbul Mahalleleri Veritabanı

OSM/Nominatim API'den çekilen İstanbul mahalle ve bölge verileri.
"""
from typing import Dict, List, Optional

ISTANBUL_NEIGHBORHOODS = {
    # ============================================================
    # BEŞİKTAŞ İLÇESİ
    # ============================================================
    "beşiktaş": {
        "il": "istanbul",
        "ilçe": "beşiktaş",
        "mahalleler": [
            "Abbasağa", "Akağlar", "Arnavutköy", "Bebek", "Cihannüma", 
            "Ertuğrul", "Fbbek", "Kuruçeşme", "KÜLTÜR", "Levent", 
            "Merkez", "Mimaroba", "Nişantepe", "Ortaköy", "Serencebey", 
            "Sinanpaşa", "Türkbükü", "Ulubatlı", "Yeni", "Yıldız"
        ],
        "bölgeler": ["Levent", "Etiler", "Ortaköy", "Arnavutköy", "Bebek", "Yeni Levent"]
    },
    
    # ============================================================
    # KADIKÖY İLÇESİ
    # ============================================================
    "kadıköy": {
        "il": "istanbul",
        "ilçe": "kadıköy",
        "mahalleler": [
            "Acıbadem", "Bostancı", "Caddebostan", "Caferağa", "Denizalgını",
            " Erenköy", "Feneryolu", "Fıstıkağacı", "Göztepe", "Hasanpaşa",
            "Haydarpaşa", "Kozyatağı", "Küçükyalı", "Moda", "Rasimpaşa",
            "Sahrayıcedid", "Selamiçeşme", "Zümrütevler"
        ],
        "bölgeler": ["Moda", "Bostancı", "Göztepe", "Kozyatağı", "Küçükyalı", "Haydarpaşa", "Acıbadem"]
    },
    
    # ============================================================
    # ÜSKÜDAR İLÇESİ
    # ============================================================
    "üsküdar": {
        "il": "istanbul",
        "ilçe": "üsküdar",
        "mahalleler": [
            "Acıbadem", "Altunizade", "Aziz Mahmut Hüdayi", "Beylerbeyi", "Burhaniye",
            "Cengelköy", "Çengelköy", "Emirgan", "Güzeltepe", "ICBalkon",
            "Kandilli", "Kısıklı", "Kuleli", " Kuzguncuk", "Mimar Sinan",
            "Moda", "Nakkaş", "Petek", "Selimiye", "Tantavi", "Tokatköy",
            "Yavuztürk", "Zeynep Kamil"
        ],
        "bölgeler": ["Altunizade", "Çengelköy", "Beylerbeyi", "Kuzguncuk", "Emirgan", "Tarabya"]
    },
    
    # ============================================================
    # ŞİŞLİ İLÇESİ
    # ============================================================
    "şişli": {
        "il": "istanbul",
        "ilçe": "şişli",
        "mahalleler": [
            "Bozlu", "Cihangir", "Darüşşafaka", "Feriköy", "Fındıklı",
            "Halide Edip Adıvar", "Harbiye", "İnönü", "İtibariye", "Kaptanpaşa",
            "Kuştepe", "Mahalle", "Mehmet Akif Ersoy", "Merkez", "Nisantası",
            "Osmanbey", "Pangaltı", "Sanayi", "Seyrige", "Şişli", "Tepebaşı"
        ],
        "bölgeler": ["Nişantaşı", "Mecidiyeköy", "Osmanbey", "Feriköy", "Cihangir"]
    },
    
    # ============================================================
    # FATİH İLÇESİ
    # ============================================================
    "fatih": {
        "il": "istanbul",
        "ilçe": "fatih",
        "mahalleler": [
            "Aksaray", "Balat", "Beyazıt", "Cerrahpaşa", "Çapa",
            "Emniyet", "Fener", "Haseki", "Karagümrük", "Kocamustafapaşa",
            "Langa", "Milletedar", "Musevi", "Rumelihisarı", "Samatya",
            "Saraçhane", "Süleymaniye", "Sütlüce", "Tayakadın", "Topkapi", "Vefa",
            "Yedikule", "Zeyrek"
        ],
        "bölgeler": ["Süleymaniye", "Balat", "Fener", "Samatya", "Karagümrük", "Langa"]
    },
    
    # ============================================================
    # BEYOGLU İLÇESİ
    # ============================================================
    "beyoğlu": {
        "il": "istanbul",
        "ilçe": "beyoğlu",
        "mahalleler": [
            "Arapçiftliği", "Asmalımescit", "Bedrettin", "Bostan", "Cihangir",
            "Çatma", "Demirci", "Döşeme", "Ertuğrul", "Firuzağa", "Hacımimi",
            "Halıcıoğlu", "Hamidiye", "Hüsrev", "İstiklal", "Kalyoncu", "Kamer",
            "Kılıçalipaşa", "Kocatepe", "Kurd", "Mimar", "Mimar Sinan", "Musehı",
            "Piyalepaşa", "Sahne", "Salı", "Saray", "Sıraserviler", "Şahkulu",
            "Şaksahane", "Tarlabaşı", "Tersane", "Tomtom", "Yenişehir"
        ],
        "bölgeler": ["İstiklal Caddesi", "Tarlabaşı", "Cihangir", "Asmalımescit", "Galata"]
    },
    
    # ============================================================
    # BAKIRKÖY İLÇESİ
    # ============================================================
    "bakırköy": {
        "il": "istanbul",
        "ilçe": "bakırköy",
        "mahalleler": [
            "Ataköy", "Bakırköy", "Basınköy", "Batı", "Boyalıca",
            "Cevizlik", "Degirmen", "Kartaltepe", "Kaynarca", "Kırazlı",
            "Kumkapı", "Mek", "Osmaniye", "Pazaryeri", "Sakızağacı",
            "Sanayi", "Seyrantepe", "Sofor", "Yeni", "Yeşilköy", "Zeytinlik"
        ],
        "bölgeler": ["Ataköy", "Yeşilköy", "Florya", "Zeytinlik", "Kartaltepe"]
    },
    
    # ============================================================
    # ZEYTİNBURNU İLÇESİ
    # ============================================================
    "zeytinburnu": {
        "il": "istanbul",
        "ilçe": "zeytinburnu",
        "mahalleler": [
            "Beyazıt", "Çırpıcı", "Deniz", "Gökalp", "İlkyıldız",
            "Kazlıçeşme", "Merkez", "N.topkapı", "Seyitnizam", "Şehit", "Yenidoğan",
            "Yeşil", "Zeytin", "Zeytinburnu"
        ],
        "bölgeler": ["Kazlıçeşme", "Zeytinburnu", "Çırpıcı"]
    },
    
    # ============================================================
    # EYÜPSULTAN İLÇESİ
    # ============================================================
    "eyüpsultan": {
        "il": "istanbul",
        "ilçe": "eyüpsultan",
        "mahalleler": [
            "Akşemsettin", "Alibeyköyü", "Çiftlik", "Defterdar", "Düğmeciler",
            "Emir", "Eyüpsultan", "Göktürk", "Güzel", "İhsaniye", "İslambey",
            "Karadeniz", "Kemer", "Mimar", "Nişanca", "Otağ", "Piri",
            "Rami", "Sakarya", "Sütlüce", "Topçular", "Yeşil", "Yusufpaşa"
        ],
        "bölgeler": ["Alibeyköyü", "Göktürk", "Rami", "Karadeniz", "Sütlüce"]
    },
    
    # ============================================================
    # SARIYER İLÇESİ
    # ============================================================
    "sarıyer": {
        "il": "istanbul",
        "ilçe": "sarıyer",
        "mahalleler": [
            "Ayazağa", "Büyükdere", "Cumhuriyet", "Darüşşafaka", "Demirciler",
            "Emirgân", "Erikapı", "Fera", "Fındıkzade", "Gümüşdere", "Huzur",
            "İstinye", "Kısır", "Kuruçeşme", "Murat", "PTT", "Reşit", "Rumeli",
            "Rumeli Kavağı", "Rumelifeneri", "Sariyer", "Sehrin", "Seyrantepe",
            "Tarabya", "Tokat", "Yeni", "Yukarı", "Zekeriyaköy"
        ],
        "bölgeler": ["İstinye", "Tarabya", "Emirgan", "Sarıyer Merkez", "Zekeriyaköy", "Büyükdere"]
    },
    
    # ============================================================
    # KAĞITHANE İLÇESİ
    # ============================================================
    "kağıthane": {
        "il": "istanbul",
        "ilçe": "kağıthane",
        "mahalleler": [
            "Armaganevler", "Çeliktepe", "Deresi", "Emniyet", "Gültepe",
            "Gürsel", "Hamidiye", "Harmandantepe", "Hürriyet", "Kağıthane",
            "Karaağaç", "Keper", "Kılıç", "Narter", "Orta", "Sadabad",
            "Şair", "Seyriftokuş", "Sultaniye", "Talatpaşa", "Türkel", "Yayla", "Yeşilce"
        ],
        "bölgeler": ["Seyrantepe", "Kağıthane", "Gültepe", "Çağlayan"]
    },
    
    # ============================================================
    # KARTAL İLÇESİ
    # ============================================================
    "kartal": {
        "il": "istanbul",
        "ilçe": "kartal",
        "mahalleler": [
            "Cevizli", "Gümüş", "Hürriyet", "Kara", "Karlıktepe", "Kartal",
            "Kınık", "Kurfalı", "M.topkapı", "Orhangazi", "Petrol", "Rahmi",
            "Safa", "Saray", "Şifa", "Topselvi", "Uğur", "Yakacık", "Yalı",
            "Yeni", "Yunus", "Zafer", "Çavuşbaşı"
        ],
        "bölgeler": ["Kartal Merkez", "Yakacık", "Soğanlık", "Maltepe"]
    },
    
    # ============================================================
    # PENDIK İLÇESİ
    # ============================================================
    "pendik": {
        "il": "istanbul",
        "ilçe": "pendik",
        "mahalleler": [
            "Ahmet", "Bahçelievler", "Çam", "Çınardere", "Denizciler",
            "Emir", "Ertürk", "Esenler", "Fevzi", "Gürgen", "Gülyali",
            "Güneşli", "Harmandere", "İcadiye", "İçmeler", "Kaynarca",
            "Kırmızı", "Kurtköy", "Orta", "Ramazanoğlu", "Sanayi", "Şeyhli",
            "Tellikkız", "Velibaba", "Yeni", "Yeşil", "Yunan", "Zerkes"
        ],
        "bölgeler": ["Pendik Merkez", "Kurtköy", "Tuzla", "İçmeler", "Çamlica"]
    },
    
    # ============================================================
    # MALTEPE İLÇESİ
    # ============================================================
    "maltepe": {
        "il": "istanbul",
        "ilçe": "maltepe",
        "mahalleler": [
            "Altın", "Ayyıldız", "Bağ", "Başıbüyük", "Büyükyalı", "Camlıca",
            "Çınar", "Demircilik", "Dumlupınar", "Fırat", "Gazi", "Gül",
            "Gülensah", "İde", "Küçük", "Mehmet", "Orta", "Seyit", "Sırasöğütler",
            "Şimşir", "Yalı", "Yamanevler", "Yeni", "Yeşil", "Zırhlı"
        ],
        "bölgeler": ["Maltepe Merkez", "Başıbüyük", "Büyükyalı", "Ataşehir"]
    },
    
    # ============================================================
    # TUZLA İLÇESİ
    # ============================================================
    "tuzla": {
        "il": "istanbul",
        "ilçe": "tuzla",
        "mahalleler": [
            "Anadolu", "Aydınlı", "Birlik", "Çayır", "Deri", "Dumlupınar",
            "Emek", "Fevzi", "Fırat", "Gümüş", "İçmeler", "Kara",
            "Kurnaköy", "Kurtköy", "Mimar", "Orhan", "Postah", "Sanayi",
            "Şifa", "Tuzla", "Yaylак", "Yeni", "Yeşil", "Ziya"
        ],
        "bölgeler": ["Tuzla Merkez", "İçmeler", "Kurtköy", "Aydınlı"]
    },
    
    # ============================================================
    # ATAŞEHIR İLÇESİ
    # ============================================================
    "ataşehir": {
        "il": "istanbul",
        "ilçe": "ataşehir",
        "mahalleler": [
            "Acıbadem", "Aşık", "Barbaros", "Fetih", "İnönü", "İçerenköy",
            "Kayışdağı", "Küçük", "Mevlana", "Moda", "Örnek", "Sahra",
            "Şerifali", "Yeni", "Yeni Çamlıca", "Yeşil", "Zıpkın"
        ],
        "bölgeler": ["İçerenköy", "Kayışdağı", "Barbaros", "Ataşehir"]
    },
    
    # ============================================================
    # ÜMRANIYE İLÇESİ
    # ============================================================
    "ümraniye": {
        "il": "istanbul",
        "ilçe": "ümraniye",
        "mahalleler": [
            "Altınşehir", "Armağan", "Aşık", "Dumlupınar", "Elmalıkent",
            "Esenşehir", "Hatırcı", "Hekim", "Ihlamur", "İkbal", "İlkyıl",
            "Kâğıt", "Kazım", "Madallı", "Mimar", "Nakliyeciler", "Necip",
            "Onur", "Parseller", "Sanayi", "Tatlısu", "Tepeüstü", "Topçular",
            "Yamanevler", "Yeni", "Yeşil", "Yücel", "Ziver"
        ],
        "bölgeler": ["Ümraniye Merkez", "Tepeüstü", "Çakmak", "Dudullu"]
    },
    
    # ============================================================
    # SANCAKTEPE İLÇESİ
    # ============================================================
    "sancaktepe": {
        "il": "istanbul",
        "ilçe": "sancaktepe",
        "mahalleler": [
            "Abdurrahman", "Aydos", "Eyüp", "Fatih", "Hayri", "Hilal",
            "İnönü", "Kale", "Karadeniz", "Kemal", "Köroğlu", "Mehdı",
            "Mehmet", "Merve", "Orta", "Osman", "Sarıgazi", "Şahin",
            "Taşdelen", "Yenidoğan", "Yeni", "Yunus", "Zamanta"
        ],
        "bölgeler": ["Sarıgazi", "Sancaktepe", "Taşdelen", "Köroğlu"]
    },
    
    # ============================================================
    # ÇEKMEKÖY İLÇESİ
    # ============================================================
    "çekmeköy": {
        "il": "istanbul",
        "ilçe": "çekmeköy",
        "mahalleler": [
            "Alemdağ", "Aydın", "Başbuğ", "Çamlık", "Çekmeköy", "Ekşioğlu",
            "Gürel", "Hüdavendigar", "İmam", "Kalkan", "Kırkpınar", "Koşuyolu",
            "Madimalı", "Mehmet", "Merve", "Mimar", "Nişantepe", "Ömer",
            "Reşat", "Saray", "Sultançiftliği", "Tepeüstü", "Yayla", "Yenidoğan",
            "Yeşil", "Yılan", "Zıpkın"
        ],
        "bölgeler": ["Çekmeköy Merkez", "Sultançiftliği", "Koşuyolu"]
    },
    
    # ============================================================
    # BEYLİKDÜZÜ İLÇESİ
    # ============================================================
    "beylikdüzü": {
        "il": "istanbul",
        "ilçe": "beylikdüzü",
        "mahalleler": [
            "Adnan", "Barış", "Büyükşehir", "Cumhuriyet", "Dere", "DOKTOR",
            "Eski", "Gürsel", "Kavaklı", "Kemal", "Kolay", "Marmara",
            "Merkez", "Pınar", "Sahil", "Sanayi", "Yakuplu", "Yeni",
            "Yeşil", "Zafer"
        ],
        "bölgeler": ["Beylikdüzü Merkez", "Yakuplu", "Büyükşehir", "Gürsel"]
    },
    
    # ============================================================
    # BAĞCILAR İLÇESİ
    # ============================================================
    "bağcılar": {
        "il": "istanbul",
        "ilçe": "bağcılar",
        "mahalleler": [
            "Arı", "Atışalanı", "Bağcılar", "Barbaros", "Barlas", "Başak",
            "Çınar", "Demirkapı", "Emniyet", "Erler", "Fevzi", "Güman",
            "Hürriyet", "İnönü", "Karadeniz", "Kemal", "Kıraç", "Kiraz",
            "Köyi", "Mahmut", "Merkez", "Nami", "Necip", "Oz", "Sancak",
            "Sevgi", "Sultan", "Yavuz", "Yedikule", "Yenigün", "Yeşil", "Yıldız"
        ],
        "bölgeler": ["Bağcılar Merkez", "Mahmutbey", "Kıraç", "Kiraz"]
    },
    
    # ============================================================
    # BAYRAMPAŞA İLÇESİ
    # ============================================================
    "bayrampaşa": {
        "il": "istanbul",
        "ilçe": "bayrampaşa",
        "mahalleler": [
            "Cevat", "Demet", "Edirne", "Ergün", "İsmet", "Kamera",
            "Kartaltepe", "Kıraç", "Kocatepe", "Menderes", "Merkez", "NARLIDERE",
            "Osmangazi", "Sait", "Sanayi", "Terazidere", "Yenidoğan", "Yeşil",
            "Yıldırım", "Yıldız", "Yunus", "Zafer"
        ],
        "bölgeler": ["Bayrampaşa Merkez", "Kartaltepe", "Kıraç", "Terazidere"]
    },
    
    # ============================================================
    # GÜNGÖREN İLÇESİ
    # ============================================================
    "güngören": {
        "il": "istanbul",
        "ilçe": "güngören",
        "mahalleler": [
            "Akın", "Barbaros", "Büyük", "Cevher", "Güneş", "Güngören",
            "Güven", "Habib", "Hürriyet", "İstanbul", "K mare", "Kemer",
            "Mehmet", "Merkez", "Mustafa", "Nail", "Sancak", "Seyfullah",
            "Sultançiftliği", "Yavuz", "Yeşil", "Zafer"
        ],
        "bölgeler": ["Güngören Merkez", "Güneş", "Mustafa"]
    },
    
    # ============================================================
    # ESENLER İLÇESİ
    # ============================================================
    "esenler": {
        "il": "istanbul",
        "ilçe": "esenler",
        "mahalleler": [
            "Altın", "Atışalanı", "Birlik", "Çifte", "Davy", "Emniyet",
            "Erler", "Esenler", "Fevzi", "Hava", "Kazım", "Kemal",
            "Kıraç", "Menderes", "Merkez", "Oruc", "Ozan", "Şehit", "Tuna",
            "Yavuz", "Yeni", "Yeşil", "Yıldırım", "Yıldız", "Yunus"
        ],
        "bölgeler": ["Esenler Merkez", "Kıraç", "Atışalanı", "Ozan"]
    },
    
    # ============================================================
    # SİLİVRİ İLÇESİ
    # ============================================================
    "silivri": {
        "il": "istanbul",
        "ilçe": "silivri",
        "mahalleler": [
            "Alibey", "Büyük", "Canta", "Çayırdere", "Çelik", "Çukuryurt",
            "Değirmenköy", "Dere", "Ekşior", "Fener", "Gazitepe", "Gündoğdu",
            "Gümüşyaka", "Habibler", "Hürriyet", "İhsaniye", "İlkyıl", "Kadıköy",
            "Kalkın", "Karlı", "Kavaklı", "Kemal", "Kırı", "Kumburgaz",
            "Marmara", "Mithat", "Murat", "Pınarca", "Sait", "Sanayi",
            "Selimpaşa", "Silivri", "Sinek", "Sofular", "Şahin", "Tap",
            "Yazı", "Yeniköy", "Yeşil", "Yıldız", "Yusuf"
        ],
        "bölgeler": ["Silivri Merkez", "Selimpaşa", "Kumburgaz", "Marmara"]
    },
    
    # ============================================================
    # ŞİLE İLÇESİ
    # ============================================================
    "şile": {
        "il": "istanbul",
        "ilçe": "şile",
        "mahalleler": [
            "Ahmet", "Ağva", "Bıçkıdere", "Cumhuriyet", "Çelebi", "Davutlar",
            "Değirmenci", "Doğancılı", "Gökçeali", "Gümüşyaka", "İsa", "Kabakoz",
            "Karaağaç", "Kumburgaz", "Köknar", "Merkez", "Oz", "Sofu",
            "Şahin", "Şile", "Tel", "Yanov", "Yazı", "Yeni", "Yeşil", "Yuva"
        ],
        "bölgeler": ["Şile Merkez", "Ağva", "Kumburgaz", "Karaağaç"]
    },
}

def search_neighborhood(location: str) -> dict:
    """Mahalle/bölge ara."""
    normalized = location.lower()
    
    # İlçe anahtarlarında ara (orijinal haliyle)
    for key in ISTANBUL_NEIGHBORHOODS:
        if key in normalized or normalized in key:
            return ISTANBUL_NEIGHBORHOODS[key]
    
    # Normalized versiyonla dene
    normalized2 = normalized.replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c")
    if normalized2 in ISTANBUL_NEIGHBORHOODS:
        return ISTANBUL_NEIGHBORHOODS[normalized2]
    
    # Prefix eşleşme
    for key in ISTANBUL_NEIGHBORHOODS:
        if key.startswith(normalized2):
            return ISTANBUL_NEIGHBORHOODS[key]
    
    # Mahalle ara
    for district, data in ISTANBUL_NEIGHBORHOODS.items():
        for m in data.get("mahalleler", []):
            m_norm = m.lower().replace("ı", "i").replace("ş", "s")
            if m_norm in normalized2 or normalized2 in m_norm:
                return {
                    "mahalle": m,
                    "ilçe": district,
                    **data
                }
    
    return None

def get_all_districts() -> List[str]:
    """Tüm ilçe isimlerini döndürür."""
    return list(ISTANBUL_NEIGHBORHOODS.keys())

def get_district_info(district: str) -> Optional[dict]:
    """İlçe bilgisi döndürür."""
    normalized = district.lower().replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c")
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
    print("İSTANBUL MAHALLELERİ TEST")
    print("=" * 60)
    
    # İlçe sayısı
    districts = get_all_districts()
    print(f"\nToplam ilçe: {len(districts)}")
    
    # İlk birkaç ilçenin bilgisini göster
    for d in list(ISTANBUL_NEIGHBORHOODS.keys())[:5]:
        info = ISTANBUL_NEIGHBORHOODS[d]
        print(f"\n{d.upper()}: {len(info.get('mahalleler', []))} mahalle")
        print(f"  Örnek mahalleler: {info.get('mahalleler', [])[:5]}")
    
    # Arama testleri
    print("\n" + "=" * 60)
    print("ARAMA TESTLERİ")
    print("=" * 60)
    
    for query in ["kadıköy", "levent", "tarabya", "bostancı", "üsküdar"]:
        result = search_neighborhood(query)
        if result:
            il = result.get("il", "")
            ilçe = result.get("ilçe", "")
            print(f"\n'{query}' → il: {il}, ilçe: {ilçe}")
        else:
            print(f"\n'{query}' → bulunamadı")

if __name__ == "__main__":
    test_istanbul_neighborhoods()
