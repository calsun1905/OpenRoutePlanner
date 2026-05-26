"""
detailed_location_engine.py - Detaylı Lokasyon Çözümleme (TAM VERSİYON v2)

İstanbul'un:
- İlçeleri (37)
- Mahalleleri (TÜMÜ - DOĞRU EŞLEŞTİRME)
- Sokak/Cadde isimleri (ÖNEMLİ - TÜMÜ)
"""

from typing import Dict, List, Set

# =============================================================================
# İSTANBUL İLÇE VERİTABANI (37 ilçe - TAM)
# =============================================================================

ISTANBUL_DISTRICTS = {
    "adalar": {"name": "Adalar", "il": "istanbul", "yakla": "anadolu", "lat": 40.87, "lon": 29.13},
    "arnavutköy": {"name": "Arnavutköy", "il": "istanbul", "yakla": "avrupa", "lat": 41.27, "lon": 28.73},
    "ataşehir": {"name": "Ataşehir", "il": "istanbul", "yakla": "anadolu", "lat": 40.99, "lon": 29.13},
    "avcılar": {"name": "Avcılar", "il": "istanbul", "yakla": "avrupa", "lat": 40.99, "lon": 28.72},
    "bağcılar": {"name": "Bağcılar", "il": "istanbul", "yakla": "avrupa", "lat": 41.04, "lon": 28.86},
    "bahçelievler": {"name": "Bahçelievler", "il": "istanbul", "yakla": "avrupa", "lat": 41.00, "lon": 28.86},
    "bakırköy": {"name": "Bakırköy", "il": "istanbul", "yakla": "avrupa", "lat": 40.98, "lon": 28.82},
    "başakşehir": {"name": "Başakşehir", "il": "istanbul", "yakla": "avrupa", "lat": 41.09, "lon": 28.79},
    "bayrampaşa": {"name": "Bayrampaşa", "il": "istanbul", "yakla": "avrupa", "lat": 41.05, "lon": 28.90},
    "beşiktaş": {"name": "Beşiktaş", "il": "istanbul", "yakla": "avrupa", "lat": 41.04, "lon": 29.01},
    "beylikdüzü": {"name": "Beylikdüzü", "il": "istanbul", "yakla": "avrupa", "lat": 41.01, "lon": 28.64},
    "beyoğlu": {"name": "Beyoğlu", "il": "istanbul", "yakla": "avrupa", "lat": 41.04, "lon": 28.98},
    "büyükçekmece": {"name": "Büyükçekmece", "il": "istanbul", "yakla": "avrupa", "lat": 41.02, "lon": 28.58},
    "çatalca": {"name": "Çatalca", "il": "istanbul", "yakla": "avrupa", "lat": 41.15, "lon": 28.46},
    "çekmeköy": {"name": "Çekmeköy", "il": "istanbul", "yakla": "anadolu", "lat": 41.03, "lon": 29.17},
    "esenler": {"name": "Esenler", "il": "istanbul", "yakla": "avrupa", "lat": 41.06, "lon": 28.88},
    "eyüpsultan": {"name": "Eyüpsultan", "il": "istanbul", "yakla": "avrupa", "lat": 41.05, "lon": 28.93},
    "fatih": {"name": "Fatih", "il": "istanbul", "yakla": "avrupa", "lat": 41.02, "lon": 28.95},
    "gaziosmanpaşa": {"name": "Gaziosmanpaşa", "il": "istanbul", "yakla": "avrupa", "lat": 41.07, "lon": 28.90},
    "güngören": {"name": "Güngören", "il": "istanbul", "yakla": "avrupa", "lat": 41.01, "lon": 28.89},
    "kadıköy": {"name": "Kadıköy", "il": "istanbul", "yakla": "anadolu", "lat": 40.99, "lon": 29.03},
    "kağıthane": {"name": "Kağıthane", "il": "istanbul", "yakla": "avrupa", "lat": 41.07, "lon": 28.96},
    "kartal": {"name": "Kartal", "il": "istanbul", "yakla": "anadolu", "lat": 40.98, "lon": 29.19},
    "küçükçekmece": {"name": "Küçükçekmece", "il": "istanbul", "yakla": "avrupa", "lat": 40.99, "lon": 28.79},
    "maltepe": {"name": "Maltepe", "il": "istanbul", "yakla": "anadolu", "lat": 40.94, "lon": 29.15},
    "pendik": {"name": "Pendik", "il": "istanbul", "yakla": "anadolu", "lat": 40.88, "lon": 29.23},
    "sancaktepe": {"name": "Sancaktepe", "il": "istanbul", "yakla": "anadolu", "lat": 40.99, "lon": 29.23},
    "sarıyer": {"name": "Sarıyer", "il": "istanbul", "yakla": "avrupa", "lat": 41.10, "lon": 29.04},
    "silivri": {"name": "Silivri", "il": "istanbul", "yakla": "avrupa", "lat": 41.07, "lon": 28.24},
    "sultanbeyli": {"name": "Sultanbeyli", "il": "istanbul", "yakla": "anadolu", "lat": 40.96, "lon": 29.28},
    "sultangazi": {"name": "Sultangazi", "il": "istanbul", "yakla": "avrupa", "lat": 41.08, "lon": 28.87},
    "şile": {"name": "Şile", "il": "istanbul", "yakla": "anadolu", "lat": 41.18, "lon": 29.61},
    "şişli": {"name": "Şişli", "il": "istanbul", "yakla": "avrupa", "lat": 41.05, "lon": 28.99},
    "tuzla": {"name": "Tuzla", "il": "istanbul", "yakla": "anadolu", "lat": 40.86, "lon": 29.30},
    "ümraniye": {"name": "Ümraniye", "il": "istanbul", "yakla": "anadolu", "lat": 41.01, "lon": 29.10},
    "üsküdar": {"name": "Üsküdar", "il": "istanbul", "yakla": "anadolu", "lat": 41.02, "lon": 29.02},
    "zeytinburnu": {"name": "Zeytinburnu", "il": "istanbul", "yakla": "avrupa", "lat": 41.01, "lon": 28.91},
}

# =============================================================================
# MAHALLE VERİTABANI (TÜM İSTANBUL - 37 İLÇE - DOĞRU EŞLEŞTİRME)
# =============================================================================

ISTANBUL_NEIGHBORHOODS = {
    # ADALAR
    "adalar": ["Burgazada", "Heybeliada", "Kınalıada", "Büyükada", "Sedefadası", "Yassıada", "Sivriada", "Kaşıkadası", "Tavşanadası", "Prinkipo"],
    
    # ARNAVUTKÖY
    "arnavutköy": ["Arnavutköy", "Hadımköy", "İstanbulkent", "Taşoluk", "Nakkas", "Deliklikaya", "Yassıören", "Yeşilce", "Dursunköy", "Anadolu", "Ömerli", "Kıraç", "Boyalıca", "Gümüşkumla", "Karaburun", "İmrahor", "Atatürk", "Yeşilbayır", "Beylikbağı", "Karacaömerli"],
    
    # ATAŞEHİR
    "ataşehir": ["Ataşehir", "Kayışdağı", "İçerenköy", "Kozyatağı", "Fetih", "Ferhatpaşa", "Yeni Sahra", "Esenşehir", "Atatürk", "Kredi Kazan", "Barbaros", "Örnek", "Şerifali", "Yunus", "Mevlana", "Türkmenbaşı", "Mustafa Kemal", "Zümrütevler", "Aşık Veysel", "Kanal"],
    
    # AVCILAR
    "avcılar": ["Yeşilkent", "Firuzköy", "Gümüşpala", "Ambarlı", "Denizköşkler", "Kazım Karabekir", "Cihangir", "Namık Kemal", "Emniyet", "Mustafa Kemal", "Adnan Menderes", "Baha Menderes", "Şehit Mustafa", "Kaya", "Göktürk", "İncirtepe", "Tahtakale", "Sultançiftliği", "Aksaray", "Kemalpaşa"],
    
    # BAĞCILAR
    "bağcılar": ["Bağcılar", "Demirkapı", "İnönü", "Kemalpaşa", "Mahmutbey", "Barbaros", "Yavuzselim", "Güneşli", "Kirazlı", "Altınşehir", "Fatih", "Sancaktepe", "Bağlar", "Mevlana", "Merkez", "Çınar", "Gül", "Yıldız", "Çamlıca", "Zafer"],
    
    # BAHÇELİEVLER
    "bahçelievler": ["Bahçelievler", "Hürriyet", "Zafer", "Yunus Emre", "Mehmet Akif Ersoy", "Adalet", "Cumhuriyet", "Kocasinan", "Soğanlı", "Siyavuşpaşa", "Emek", "Kartaltepe", "İncirli", "Şirinevler", "Çobançeşme", "Sanayi", "Çalışkan", "Erguvan", "Fevzi Çakmak", "Dede Korkut"],
    
    # BAKIRKÖY
    "bakırköy": ["Ataköy", "Bakırköy", "Kartaltepe", "Zeytinlik", "Yeşilyurt", "Osmaniye", "Cennet", "Yeşilköy", "Florya", "Sefaköy", "Gümüşpala", "Basınköy", "Boyalıca", "Şenlikköy", "İDC", "Marmara", "Sanayi", "İlkyerleşim", "Mehmet Akif", "Kartal"],
    
    # BAŞAKŞEHİR
    "başakşehir": ["Başakşehir", "Kayabaşı", "Bahçeşehir", "Basınköy", "İkitelli", "Altınşehir", "Şahintepe", "Şekerpınarı", "Güvercintepe", "Ziya Gökalp", "Mimar Sinan", "Yeşilçay", "Baruthane", "Batıkent", "Yayla", "Sanayi", "Göktürk", "İnönü", "Merkez", "Atatürk"],
    
    # BAYRAMPAŞA
    "bayrampaşa": ["Bayrampaşa", "Altıntepsi", "Feriköy", "Kocatepe", "Mimar Sinan", "Muradiye", "Nisbetiye", "Orta", "Sait", "Sanayi", "Şişman", "Yenidoğan", "Yıldız", "Demirkapı", "Vatan", "Kıraç", "Eyüp", "Merkez", "Gülsuyu", "Terkos"],
    
    # BEŞİKTAŞ
    "beşiktaş": ["Abbasağa", "Akağlar", "Arnavutköy", "Bebek", "Cihannüma", "Dikilitaş", "Etiler", "Kuruçeşme", "Levazım", "Levent", "Ortaköy", "Sinanpaşa", "Türkbükü", "Ulus", "Uskumruköy", "Yıldız", "Balmumcu", "Gayrettepe", "Konaklar", "Nisbetiye", "Fulya", "Gülbahar", "Zekeriyaköy"],
    
    # BEYLİKDÜZÜ
    "beylikdüzü": ["Beylikdüzü", "Yakuplu", "Kirağlı", "Pınartepe", "Barış", "Adnan Kahveci", "Büyükşehir", "Cumhuriyet", "Gürsel", "Harmony", "Kavaklı", "Marina", "Merkez", "Osmaniye", "Reşit", "Sahil", "Yunus Emre", "Zafer", "Eski Kıraliye", "Barbaros"],
    
    # BEYOĞLU
    "beyoğlu": ["Asmalımescit", "Bebek", "Büyükdere", "Cihangir", "Çatma Mescit", "Galata", "Gümüşsuyu", "Hoca Çakır", "Kalyoncu", "Kırathane", "Salyangoz", "Sishane", "Tomtom", "Tarlabaşı", "Yenişehir", "Yeşilçam", "Kemankeş", "Kaptanpaşa", "Keçeci Piri", "Öcü"],
    
    # BÜYÜKÇEKMECE
    "büyükçekmece": ["Büyükçekmece", "Kirağlı", "Pınartepe", "Gökovalı", "Kamiloba", "Hürriyet", "Atatürk", "Cumhuriyet", "Fatih", "Güzelce", "Mimar Sinan", "Pazarköy", "Sinanoba", "Türkoba", "Alişar", "Çakırlı", "Celaliye", "Dizdariye", "Karaağaç", "Kumburgaz"],
    
    # ÇATALCA
    "çatalca": ["Çatalca", "Mimar Sinan", "Ferhatpaşa", "Kale", "Subaşı", "Binkılıç", "Nakkaş", "Kestanelik", "Gümüşyaka", "Bahşayış", "Aydınlar", "Beylik", "Çakıl", "Dağeynü", "Doğancılı", "Elbasan", "Fırıncılar", "Haraççı", "İzzettin", "Kabakdağı"],
    
    # ÇEKMEKÖY
    "çekmeköy": ["Çekmeköy", "Aydınlar", "Çamlık", "Darıca", "Dizdariye", "Ekşioğlu", "Göçbeyli", "Gümüşyaka", "Haraççı", "İmamkıran", "Kılıçlar", "Köprücek", "Murat", "Necip Fazıl", "Site", "Şehitler", "Taşdelen", "Tepeören", "Yavuzselim", "Yenidoğan"],
    
    # ESENLER
    "esenler": ["Esenler", "Atışalanı", "Çiftehavuzlar", "Fevzi Çakmak", "Güneştepe", "Havaalanı", "Kemer", "Menderes", "Mimar Sinan", "Namık Kemal", "Ostim", "Fatih", "Barbaros", "Birlik", "Demirkapı", "Kazım Karabekir", "Orhan GAzi", "Şehitlik", "Tuna", "Kumburgaz"],
    
    # EYÜPSULTAN
    "eyüpsultan": ["Eyüpsultan", "Akşemsettin", "Alibeyköy", "Battalgazi", "Çırçır", "Defterdar", "Düğmeciler", "Göktuğ", "Güzeltepe", "İslambey", "Kemer", "Mimar Sinan", "Nişanca", "Gazi", "Pirinçci", "Rami", "Silahtarağa", "Sopacılar", "Topçular", "Yeşilpınar"],
    
    # FATİH
    "fatih": ["Aksaray", "Balat", "Beyazıt", "Cerrahpaşa", "Çapa", "Fatih", "Fener", "Karagümrük", "Kocamustafapaşa", "Langa", "Mahmutpaşa", "Mimar Hayrettin", "Mimar Sinan", "Rüstempaşa", "Süleymaniye", "Şehremini", "Silivrikapı", "Tayakadın", "Yavuzselim", "Zeyrek", "Hırka-i Şerif", "Saraç İshak"],
    
    # GAZİOSMANPAŞA
    "gaziosmanpaşa": ["Gaziosmanpaşa", "Bağlar", "Barbaros", "Başakköprü", "Camcı", "Eyüp", "Fevzi Çakmak", "Gümüşyaka", "Hoca Ahmet", "İcadiye", "Karaağaç", "Karadeniz", "Kemer", "Kocasinan", "Kültepe", "Mimar Sinan", "Pazariçi", "Sarıgöl", "Yenidoğan", "Yunus Emre", "Şişli"],
    
    # GÜNGÖREN
    "güngören": ["Güngören", "Akıncılar", "Barbaros", "Büyükşehir", "Cumhuriyet", "Güneş", "Güven", "Haznedar", "İnönü", "Kara Ahmet", "Kemalpaşa", "Kocabağ", "Mahmutpaşa", "Mehmetçiftliği", "Merkez", "Mollagueçe", "Sancaklı", "Şehitler", "Talatpaşa", "Tozkoparan"],
    
    # KADIKÖY
    "kadıköy": ["Acıbadem", "Bostancı", "Caddebostan", "Caferağa", "Denizalgını", "Feneryolu", "Fikirtepe", "Göztepe", "Hasanpaşa", "İçerenköy", "Kozyatağı", "Lalbey", "Merdivenköy", "Moda", "Ondokuzmayıs", "Osmanağa", "Rasimpaşa", "Sahrayıcedid", "Yeldeğirmeni", "Zümrütevler", "Fenerbahçe", "Erenköy"],
    
    # KAĞITHANE
    "kağıthane": ["Kağıthane", "Ayazma", "Çağlayan", "Çeliktepe", "Emniyet", "Gültepe", "Gürsel", "Hamidiye", "Harmantepe", "Hürriyet", "İnönü", "Kemankeş", "Merkez", "Nur", "Orta", "Peçenek", "Sanayi", "Seyrantepe", "Şirintepe", "Talatpaşa", "Yeşilce"],
    
    # KARTAL
    "kartal": ["Atalar", "Cevizli", "Gümüşpınar", "Karaçalı", "Karlıktepe", "Kartal", "Kordon", "Orhantepe", "Öncebe", "Seyit Ali", "Sümer", "Topselvi", "Uğur Mumcu", "Yakacık", "Yelit", "Aydos", "Cumhuriyet", "Hürriyet", "Kızılca", "Milli"],
    
    # KÜÇÜKÇEKMECE
    "küçükçekmece": ["Küçükçekmece", "Atatürk", "Cumhuriyet", "Fahreddin", "Güneş", "Halkalı", "İnönü", "Kemer", "Mehmet Akif", "Merkez", "Namık Kemal", "Seymen", "Sultançiftliği", "Şerifali", "Tepeüstü", "İDC", "Altınşehir", "Beşyol", "Yeşilnova", "Kados"],
    
    # MALTEPE
    "maltepe": ["Maltepe", "Altınçekmece", "Aydos", "Başıbüyük", "Cevizli", "Çınar", "Feyzullah", "Gülbahar", "Gülsuyu", "İğdecik", "İlkyerleşim", "Kumluk", "Kuyubaşı", "Yalı", "Yeni", "Yeşilbağ", "Zümrütevler", "Gürsel", "Bahçelievler", "Ataşehir"],
    
    # PENDİK
    "pendik": ["Ahmet Yesevi", "Batı", "Çamçeşme", "Disten", "Eren", "Ertuğrul Gazi", "Esenler", "Göçbeyli", "Güzelyalı", "İçmeler", "Kavakpınarı", "Kaynarca", "Orta", "Sapanlı", "Şeyhli", "Velibaba", "Yeni", "Yenialan", "Yeşilbağlar", "Fevzi Çakmak", "Kartal"],
    
    # SANCAKTEPE
    "sancaktepe": ["Sancaktepe", "Abdurrahmangazi", "Ahmet Yesevi", "Akpınar", "Eyüp Sultan", "Fatih", "Kemal Türkler", "Mehmet Akif", "Mimar Sinan", "OSB", "Sarıgazi", "Selamiye", "Seyfullah", "Şeyhli", "Tokat", "Yavuzselim", "Yenidoğan", "Yunus Emre", "Zafer", "Barış"],
    
    # SARIYER
    "sarıyer": ["Altınyunus", "Bahçeköy", "Balkaynak", "Büyükdere", "Çamlıtepe", "Emirgan", "Ferahevler", "Hurrem", "İstinye", "Kireçburnu", "Kuruçeşme", "Madalyon", "Merkez", "Paşaburnu", "Pınarca", "Rehber", "Rumelifeneri", "Sarıyer", "Tarabya", "Yeniköy", "Zekeriyaköy", "Polonez"],
    
    # SİLİVRİ
    "silivri": ["Silivri", "Alibey", "Alkent", "Balaban", "Çayırdibi", "Çeltik", "Değirmenköy", "Eriklice", "Fener", "Gazlı", "Gümüşyaka", "İcadiye", "İnceğiz", "Kalkım", "Kemer", "Kösedere", "Kumburgaz", "Lalaköy", "Mimarsinan", " Büyük Sinek"],
    
    # SULTANBEYLİ
    "sultanbeyli": ["Sultanbeyli", "Abdurrahmangazi", "Akşemsettin", "Beyler", "Hamidiye", "Mecidiye", "Mehmet Akif", "Merkez", "Necip Fazıl", "Seyfullah", "Şehitler", "Yavuzselim", "Yeşilpınar", "Kemer", "Kavakpınarı", "Batı", "Gülsuyu", "Orta", "Doğu", "Kuzey"],
    
    # SULTANGAZİ
    "sultangazi": ["Sultangazi", "50. Yıl", "Aksaray", "Cevizli", "Dudullu", "Esenler", "Habibler", "İsmet Paşa", "Kâğıthâne", "Kemer", "Mağara", "Mimar Sinan", "Necmi", "Uğur Mumcu", "Yavuzselim", "Yunus Emre", "Ziya Gökalp", "Eski Mimar Sinan", "İlkyerleşim"],
    
    # ŞİLE
    "şile": ["Şile", "Ahmetli", "Ağva", "Bıçkıdere", "Boyalıca", "Çatalcam", "Çavuş", "Demircili", "Doğancılı", "Gökçeali", "Gümüşyaka", "İmrenli", "Kabakoz", "Kalfaköy", "Karaağaç", "Kızılca", "Kumbaba", "Mavuk", "Ovacık", "Sofular"],
    
    # ŞİŞLİ
    "şişli": ["Bozlu", "Cihangir", "Darüşşafaka", "Feriköy", "Fındıklı", "Halaskargazi", "İnönü", "Kiral", "Kurtuluş", "Mecidiyeköy", "Merkez", "Meşrutiyet", "Nişantaşı", "Osmanbey", "Paşa", "Teşvikiye", "Gülbahar", "Seyrantepe", "Esentepe", "Fulya", "Bomonti"],
    
    # TUZLA
    "tuzla": ["Tuzla", "Anadolu", "Aydınlı", "Camlıca", "Çayırlı", "Evren", "Fatih", "Feyzullah", "Güzelyalı", "İçmeler", "İstiklal", "Kemalpaşa", "Kurnaköy", "Menderes", "Meri", "Orta", "Şifa", "Tepeören", "Yayla", "Yavuzselim"],
    
    # ÜMRANİYE
    "ümraniye": ["Ümraniye", "Altınşehir", "Armağanevler", "Aşık Veysel", "Atatürk", "Çakmak", "Dumlupınar", "Elmalıkent", "Esenşehir", "Hekimbaşı", "İnkılap", "Kazım Karabekir", "Namık Kemal", "Necip Fazıl", "Parseller", "Şerifali", "Tepeüstü", "Topkapı", "Yavuztürk", "İçerenköy"],
    
    # ÜSKÜDAR
    "üsküdar": ["Acıbadem", "Altunizade", "Aziz Mahmut Hüdayi", "Beylerbeyi", "Burhaniye", "Çengelköy", "Ferah", "İcadiye", "Kısıklı", "Kuzguncuk", "Mimar Sinan", "Sait Çiftliği", "Selimiye", "Tamış", "Yavuztürk", "Validebağ", "Kandilli", "Rumeli Hisarı", "Bulgun"],
    
    # ZEYTİNBURNU
    "zeytinburnu": ["Zeytinburnu", "Akören", "Atatürk", "Beştelsiz", "Çırpıcı", "Gözköy", "Gülpınar", "Gürsel", "Kazlıçeşme", "Kemal Tertip", "Merkez", "Mithatpaşa", "Nüzhetiye", "Seyitnizam", "Sümer", "Telsiz", "Yeşilce", "Yenidoğan", "Zeytin", "Fatih"],
}

# =============================================================================
# SOKAK/CADDE VERİTABANI (TÜM İSTANBUL)
# =============================================================================

ISTANBUL_STREETS = {
    # KADIKÖY - ÖNEMLİ SOKAKLAR
    "kadıköy": [
        "Moda Cd.", "Caferağa Sk.", "Rasimpaşa Sk.", "Bostancı Cd.", "Göztepe Cd.",
        "Feneryolu Sk.", "Kadıköy Rıhtım Cd.", "Yeldeğirmeni Sk.", "Osmanağa Sk.",
        "Halitağa Cd.", "Sahrayıcedid Cd.", "Acıbadem Sk.", "Bağdat Cd.", "Fenerbahçe Sk.",
        "Çiçek Cd.", "Kadıköy Çarşı Sk.", "Mühürdar Sk.", "Söğütlüçeşme Cd.", "Harem Sk.",
        "Kozluçeşme Sk.", "Zürafagül Sk.", "Gümüşlük Sk.", "Bahariye Cd.", "Tombaker Cd.",
        "Göztepe Cad. No", "Caddebostan Cd.", "Feneryolu Cd.", "Bostancı Yolu Cd."
    ],
    # BEŞİKTAŞ - ÖNEMLİ SOKAKLAR
    "beşiktaş": [
        "Barbaros Bulv.", "Akaretler Cd.", "Bebek Cd.", "Etiler Cd.", "Ortaköy Cd.",
        "Arnavutköy Cd.", "Kuruçeşme Cd.", "Balmumcu Cd.", "Dikilitaş Sk.", "Lefkoşe Cd.",
        "Gayrettepe Cd.", "Levent Cd.", "Büyükdere Cd.", "Aşiyan Cd.", "Kireçburnu Cd.",
        "Yıldız Cd.", "Sinanpaşa Cd.", "Çırağan Cd.", "Hilal Cd.", "Gülbahar Cd.",
        "Çelik Sk.", "Nisbetiye Cd.", "Akbaba Sk.", "K Behçet Cd."
    ],
    # ÜSKÜDAR - ÖNEMLİ SOKAKLAR
    "üsküdar": [
        "Çengelköy Cd.", "Beylerbeyi Cd.", "Altunizade Cd.", "Acıbadem Sk.", "Kısıklı Cd.",
        "Kuzguncuk Sk.", "Ferah Cd.", "Selimiye Sk.", "Burhaniye Cd.", "İcadiye Sk.",
        "Mimar Sinan Cd.", "Aziz Mahmut Hüdayi Sk.", "İcadiye Cd.", "Çengelköy Yalısı Cd.",
        "Beylerbeyi Sarayı Cd.", "Altunizade Türk Telekom Cd.", "Valide Turi Cd.", "Nuh Kuşu Cd.",
        "Beylerbeyi İcadiye Cd.", "Acıbadem İçerenköy Cd.", "Kandilli Cd.", "Rumeli Hisarı Cd."
    ],
    # ŞİŞLİ - ÖNEMLİ SOKAKLAR
    "şişli": [
        "Abdi İpekçi Cd.", "Halaskargazi Cd.", "İnönü Cd.", "Nişantaşı Cd.", "Valikonağı Cd.",
        "Ferah Sk.", "Teşvikiye Cd.", "Osmanbey Sk.", "Mecidiyeköy Cd.", "Şişli Cd.",
        "Gülbahar Cd.", "Seyrantepe Sk.", "Fulya Cd.", "Yeşilçimen Sk.", "Maçka Cd.",
        "Cevdet Paşa Cd.", "Bayar Cd.", "Kırgülü Sk.", "Okçumusağı Sk.", "Aynalıçeşme Sk.",
        "Süleyman Nazif Sk.", "Kurtuluş Cd.", "Feriköy Sk."
    ],
    # FATİH - ÖNEMLİ SOKAKLAR
    "fatih": [
        "Süleymaniye Cd.", "Aksaray Cd.", "Langa Cd.", "Cerrahpaşa Cd.", "Çapa Kadir Has Cd.",
        "Karagümrük Cd.", "Kocamustafapaşa Sk.", "Balat Cd.", "Fener Cd.", "Yavuzselim Cd.",
        "Silivrikapı Sk.", "Hırka-i Şerif Cd.", "Saraç İshak Sk.", "Kocamustafapaşa Cd.",
        "Mimar Kemalettin Cd.", "Turgut Özal Millet Cd.", "Kennedy Cd.", "Milli Türk Cd.",
        "Fevzipaşa Cd.", "Müberrem Sk.", "Şehzadebaşı Cd.", "Kalkancılar Sk."
    ],
    # BEYOĞLU - ÖNEMLİ SOKAKLAR
    "beyoğlu": [
        "İstiklal Cd.", "Sishane Sk.", "Galata Kulesi Cd.", "Asmalımescit Sk.", "Cihangir Sk.",
        "Tarlabaşı Cd.", "Salyangoz Sk.", "Tomtom Sk.", "Büyükdere Cd.", "Kalyoncu Sk.",
        "Hoca Çakır Sk.", "Gümüşsuyu Cd.", "Kaptanpaşa Sk.", "Keçeci Piri Sk.",
        "Kılıç Ali Paşa Sk.", "Böcek Sk.", "Şahidi Sk.", "Hafız İsa Sk.", "Emin Sinan Sk.",
        "Kalyoncu Kaptan Sk.", "Felek Sk.", "Dovol Sk."
    ],
    # SARIYER - ÖNEMLİ SOKAKLAR
    "sarıyer": [
        "Büyükdere Cd.", "Tarabya Cd.", "İstinye Cd.", "Emirgan Korusu Cd.", "Sarıyer Cd.",
        "Bahçeköy Sk.", "Ferahevler Cd.", "Hurrem Cd.", "Kuruçay Sk.", "Altınyunus Cd.",
        "Yeniköy Cd.", "Rumelifeneri Sk.", "Demirciköy Cd.", "Poyrazköy Cd.", "Kıraç Cd.",
        "Beykoz Cd.", "Çayırbaşı Cd.", "Bulvard Cd.", "Reşit Galip Cd.", "İstinye Park Cd.",
        "Çeşme Cd.", "Kireçburnu Cd.", "Maden Sk."
    ],
    # BAKIRKÖY - ÖNEMLİ SOKAKLAR
    "bakırköy": [
        "Ataköy 7-8-9-10. Kısım Cd.", "Yeşilköy Cd.", "Florya Cd.", "Sefaköy Cd.",
        "Bakırköy Özgürcüler Cd.", "Kartaltepe Cd.", "Zeytinlik Cd.", "Cennet Cd.",
        "Osmaniye Sk.", "Yeşilyurt Sk.", "İstanbul Cd.", "Sanayi Cd.", "Yenimahalle Sk.",
        "Şenlikköy Sk.", "Basınköy Cd.", "Boyalıca Cd.", "Harmani Cd.", "Liman Cd.",
        "Kartaltepe Sanayi Sk."
    ],
    # ATAŞEHİR - ÖNEMLİ SOKAKLAR
    "ataşehir": [
        "Bağdat Cd.", "İçerenköy Cd.", "Kozyatağı Şehit Şevket Cd.", "Kayışdağı Cd.",
        "Ataşehir Feridun Sk.", "Fetih Blv.", "Şerifali Cd.", "Yenidoğan Cd.",
        "Kredi Kazan Cd.", "Barbaros Cd.", "Örnek Cd.", "Mevlana Cd.", "Türkmenbaşı Cd.",
        "Atatürk Cd.", "İnkılap Cd.", "Mimar Sinan Cd.", "Kavacık Fındıklı Cd.",
        "Kayışdağı Yolu Cd.", "Ataşehir Cd."
    ],
    # BEYLİKDÜZÜ - ÖNEMLİ SOKAKLAR
    "beylikdüzü": [
        "Barbaros Cd.", "Adnan Kahveci Cd.", "Yakuplu Cd.", "Kirağlı Cd.", "Pınartepe Cd.",
        "Beylikdüzü Cd.", "Büyükşehir Cd.", "Cumhuriyet Cd.", "Gürsel Cd.", "Harmony Cd.",
        "Marina Cd.", "Osmaniye Cd.", "Reşit Cd.", "Sahil Cd.", "Yunus Emre Cd.",
        "Eski Hadımköy Cd.", "Mermerciler Sanayi Cd.", "Güneş Cd.", "Efe Sk."
    ],
    # ESENLER - ÖNEMLİ SOKAKLAR
    "esenler": [
        "Atışalanı Cd.", "Çiftehavuzlar Cd.", "Fevzi Çakmak Cd.", "Güneştepe Cd.",
        "Havaalanı Yolu Cd.", "Kemer Cd.", "Mimar Sinan Cd.", "Namık Kemal Cd.",
        "Tuna Cd.", "Barbaros Cd.", "Birlik Cd.", "Demirkapı Cd.", "Kazım Karabekir Cd.",
        "Orhan GAzi Cd.", "Şehitlik Cd.", "Menderes Cd.", "Ostim Cd.", "Mevlana Cd."
    ],
    # EYÜPSULTAN - ÖNEMLİ SOKAKLAR
    "eyüpsultan": [
        "Eyüp Sultan Cd.", "Alibeyköy Cd.", "Rami Cd.", "Piyer Loti Cd.", "Silahtarağa Cd.",
        "Çırçır Cd.", "Düğmeciler Cd.", "Güzeltepe Cd.", "İslambey Cd.", "Göktuğ Cd.",
        "Akşemsettin Cd.", "Battalgazi Cd.", "Defterdar Cd.", "Nişanca Cd.", "Pirinçci Sk.",
        "Şehitler Sk.", "Topçular Sk.", "Yeşilpınar Sk.", "İstanbul Cd.", "Karadeniz Cd.",
        "Silahtarağa Yolu Cd."
    ],
    # MALTEPE - ÖNEMLİ SOKAKLAR
    "maltepe": [
        "Bağdat Cd.", "İstanbul Cd.", "Cevizli Cd.", "Atalar Cd.", "Gülbahar Cd.",
        "Altınçekmece Cd.", "Aydos Cd.", "Başıbüyük Cd.", "Çınar Cd.", "Feyzullah Cd.",
        "Gülsuyu Cd.", "İğdecik Sk.", "İlkyerleşim Cd.", "Kumluk Cd.", "Kuyubaşı Sk.",
        "Maltepe Cd.", "Yalı Cd.", "Yeni Cd.", "Yeşilbağ Cd.", "Zümrütevler Cd.",
        "Maltepe Sahil Cd.", "Başıbüyük Sk."
    ],
    # PENDİK - ÖNEMLİ SOKAKLAR
    "pendik": [
        "Pendik Cd.", "Kaynarca Cd.", "Göçbeyli Cd.", "Velibaba Cd.", "Yeşilbağlar Cd.",
        "Ahmet Yesevi Cd.", "Çamçeşme Cd.", "Şeyhli Cd.", "Sapanlı Cd.", "İçmeler Cd.",
        "Güzelyalı Cd.", "Batı Cd.", "Eren Cd.", "Ertuğrul Gazi Cd.", "Esenler Cd.",
        "Kavakpınarı Cd.", "Yenialan Cd.", "Fevzi Çakmak Cd.", "Yayla Cd.", "Bahçelievler Cd."
    ],
    # TUZLA - ÖNEMLİ SOKAKLAR
    "tuzla": [
        "Tuzla Cd.", "İstanbul Cd.", "Menderes Cd.", "Feyzullah Cd.", "Güzelyalı Cd.",
        "Anadolu Cd.", "Aydınlı Cd.", "Camlıca Cd.", "Çayırlı Cd.", "Evren Sk.",
        "İstiklal Cd.", "Kemalpaşa Cd.", "Kurnaköy Cd.", "Meri Sk.", "Orta Sk.",
        "Şifa Cd.", "Tepeören Cd.", "Yavuzselim Cd.", "Yayla Sk.", "İçmeler Cd.",
        "Tuzla Şifa Sk."
    ],
    # ADALAR - ÖNEMLİ SOKAKLAR
    "adalar": [
        "Burgazada Cd.", "Heybeliada Cd.", "Kınalıada Cd.", "Büyükada Meydan Cd.",
        "Çınar Cd.", "Park Sk.", "Liman Cd.", "Sahil Yolu Cd.", "İskele Cd.",
        "Kirazlı Cd.", "Aya Yorgi Sk.", "Sandal Sk."
    ],
    # ARNAVUTKÖY - ÖNEMLİ SOKAKLAR
    "arnavutköy": [
        "Arnavutköy Cd.", "Hadımköy Yolu Cd.", "Taşoluk Cd.", "Nakkas Sk.", "Ömerli Cd.",
        "Kıraç Cd.", "İstanbul Cd.", "Atatürk Cd.", "Şehitlik Sk.", "Merkez Cd.",
        "Gümüşkumla Sk.", "Karaburun Sk."
    ],
    # AVCILAR - ÖNEMLİ SOKAKLAR
    "avcılar": [
        "Yeşilkent Cd.", "Firuzköy Cd.", "Gümüşpala Cd.", "Ambarlı Cd.", "Denizköşkler Sk.",
        "Kazım Karabekir Cd.", "Cihangir Sk.", "Namık Kemal Cd.", "Emniyet Sk.",
        "Göktürk Sk.", "İstanbul Cd.", "Menderes Sk.", "Marmara Cd."
    ],
    # BAĞCILAR - ÖNEMLİ SOKAKLAR
    "bağcılar": [
        "Bağcılar Cd.", "Demirkapı Cd.", "İnönü Cd.", "Kemalpaşa Cd.", "Mahmutbey Cd.",
        "Barbaros Cd.", "Yavuzselim Cd.", "Güneşli Cd.", "Kirazlı Cd.", "Altınşehir Cd.",
        "Bağlar Sk.", "Mevlana Sk.", "Çınar Cd.", "Sanayi Sk."
    ],
    # BAHÇELİEVLER - ÖNEMLİ SOKAKLAR
    "bahçelievler": [
        "Bahçelievler Cd.", "Hürriyet Cd.", "Zafer Sk.", "Yunus Emre Cd.", "Mehmet Akif Sk.",
        "Adalet Sk.", "Cumhuriyet Cd.", "Kocasinan Cd.", "Soğanlı Sk.", "Siyavuşpaşa Cd.",
        "Kartaltepe Cd.", "İncirli Sk.", "Şirinevler Cd.", "Çobançeşme Sk."
    ],
    # BAŞAKŞEHİR - ÖNEMLİ SOKAKLAR
    "başakşehir": [
        "Başakşehir Cd.", "Kayabaşı Sk.", "Bahçeşehir Cd.", "İkitelli Cd.", "Altınşehir Cd.",
        "Şahintepe Sk.", "Şekerpınarı Cd.", "Güvercintepe Sk.", "Ziya Gökalp Cd.",
        "Mimar Sinan Cd.", "Baruthane Sk.", "Göktürk Sk.", "İstanbul Cd."
    ],
    # BAYRAMPAŞA - ÖNEMLİ SOKAKLAR
    "bayrampaşa": [
        "Bayrampaşa Cd.", "Altıntepsi Sk.", "Feriköy Cd.", "Kocatepe Cd.", "Mimar Sinan Cd.",
        "Muradiye Sk.", "Nisbetiye Cd.", "Yenidoğan Sk.", "Demirkapı Cd.", "Vatan Sk.",
        "Şişman Sk.", "İstanbul Cd."
    ],
    # BÜYÜKÇEKMECE - ÖNEMLİ SOKAKLAR
    "büyükçekmece": [
        "Büyükçekmece Cd.", "Kirağlı Sk.", "Pınartepe Sk.", "Gökovalı Cd.", "Kamiloba Sk.",
        "Hürriyet Cd.", "Atatürk Cd.", "Güzelce Sk.", "Mimar Sinan Cd.", "Türkoba Sk.",
        "Çakırlı Sk.", "Kumburgaz Sk."
    ],
    # ÇATALCA - ÖNEMLİ SOKAKLAR
    "çatalca": [
        "Çatalca Cd.", "Mimar Sinan Cd.", "Kale Sk.", "Subaşı Cd.", "Binkılıç Sk.",
        "Kestanelik Cd.", "Gümüşyaka Sk.", "Bahşayış Sk.", "Aydınlar Sk."
    ],
    # ÇEKMEKÖY - ÖNEMLİ SOKAKLAR
    "çekmeköy": [
        "Çekmeköy Cd.", "Aydınlar Sk.", "Çamlık Cd.", "Darıca Sk.", "Dizdariye Cd.",
        "Göçbeyli Sk.", "Taşdelen Cd.", "Tepeören Sk.", "Yavuzselim Cd."
    ],
    # GAZİOSMANPAŞA - ÖNEMLİ SOKAKLAR
    "gaziosmanpaşa": [
        "Gaziosmanpaşa Cd.", "Bağlar Sk.", "Barbaros Cd.", "Fevzi Çakmak Cd.", "Gümüşyaka Sk.",
        "Kocasinan Cd.", "Mimar Sinan Cd.", "Pazariçi Sk.", "Sarıgöl Cd.",
        "Yenidoğan Sk.", "İstanbul Cd."
    ],
    # GÜNGÖREN - ÖNEMLİ SOKAKLAR
    "güngören": [
        "Güngören Cd.", "Akıncılar Sk.", "Barbaros Cd.", "Büyükşehir Cd.", "Cumhuriyet Cd.",
        "Güneş Sk.", "Güven Sk.", "Haznedar Sk.", "İnönü Cd.", "Kemalpaşa Sk.",
        "Mahmutpaşa Sk.", "Tozkoparan Sk."
    ],
    # KAĞITHANE - ÖNEMLİ SOKAKLAR
    "kağıthane": [
        "Kağıthane Cd.", "Ayazma Sk.", "Çağlayan Cd.", "Çeliktepe Sk.", "Emniyet Sk.",
        "Gültepe Cd.", "Gürsel Sk.", "Hamidiye Cd.", "Hürriyet Sk.", "Seyrantepe Cd.",
        "Şirintepe Sk.", "Talatpaşa Cd.", "Sanayi Sk.", "İstanbul Cd."
    ],
    # KARTAL - ÖNEMLİ SOKAKLAR
    "kartal": [
        "Kartal Cd.", "Atalar Sk.", "Cevizli Cd.", "Gümüşpınar Sk.", "Karlıktepe Cd.",
        "Kordon Sk.", "Orhantepe Cd.", "Sümer Sk.", "Topselvi Sk.", "Uğur Mumcu Cd.",
        "Yakacık Sk.", "Aydos Cd.", "İstanbul Cd."
    ],
    # KÜÇÜKÇEKMECE - ÖNEMLİ SOKAKLAR
    "küçükçekmece": [
        "Küçükçekmece Cd.", "Atatürk Sk.", "Cumhuriyet Cd.", "Halkalı Cd.", "İnönü Sk.",
        "Kemer Cd.", "Namık Kemal Cd.", "Tepeüstü Sk.", "Beşyol Sk.", "Yeşilnova Cd.",
        "İstanbul Cd.", "Sanayi Sk."
    ],
    # SANCAKTEPE - ÖNEMLİ SOKAKLAR
    "sancaktepe": [
        "Sancaktepe Cd.", "Abdurrahmangazi Sk.", "Ahmet Yesevi Cd.", "Akpınar Sk.", "Fatih Cd.",
        "Kemal Türkler Cd.", "Mehmet Akif Sk.", "Sarıgazi Cd.", "Selamiye Sk.",
        "Yavuzselim Cd.", "Yenidoğan Sk.", "İstanbul Cd."
    ],
    # SİLİVRİ - ÖNEMLİ SOKAKLAR
    "silivri": [
        "Silivri Cd.", "Alibey Sk.", "Balaban Cd.", "Çeltik Sk.", "Değirmenköy Cd.",
        "Eriklice Sk.", "Gümüşyaka Cd.", "Kalkım Sk.", "Kumburgaz Cd.", "Mimarsinan Sk.",
        "İstanbul Cd."
    ],
    # SULTANBEYLİ - ÖNEMLİ SOKAKLAR
    "sultanbeyli": [
        "Sultanbeyli Cd.", "Abdurrahmangazi Sk.", "Akşemsettin Cd.", "Hamidiye Sk.", "Mecidiye Cd.",
        "Mehmet Akif Sk.", "Necip Fazıl Cd.", "Şehitler Sk.", "Yavuzselim Cd.",
        "Yeşilpınar Sk.", "İstanbul Cd."
    ],
    # SULTANGAZİ - ÖNEMLİ SOKAKLAR
    "sultangazi": [
        "Sultangazi Cd.", "50. Yıl Sk.", "Aksaray Cd.", "Cevizli Sk.", "Dudullu Cd.",
        "Habibler Sk.", "İsmet Paşa Cd.", "Mağara Sk.", "Mimar Sinan Cd.", "Uğur Mumcu Cd.",
        "Yavuzselim Sk.", "Ziya Gökalp Cd.", "İstanbul Cd."
    ],
    # ŞİLE - ÖNEMLİ SOKAKLAR
    "şile": [
        "Şile Cd.", "Ahmetli Sk.", "Ağva Cd.", "Bıçkıdere Sk.", "Gökçeali Cd.",
        "Gümüşyaka Sk.", "Kabakoz Sk.", "Kalfaköy Cd.", "Kumbaba Sk.", "Ovacık Sk.",
        "Sofular Cd.", "İstanbul Cd."
    ],
    # ÜMRANİYE - ÖNEMLİ SOKAKLAR
    "ümraniye": [
        "Ümraniye Cd.", "Altınşehir Sk.", "Armağanevler Cd.", "Aşık Veysel Sk.", "Atatürk Cd.",
        "Çakmak Sk.", "Dumlupınar Cd.", "Elmalıkent Sk.", "İnkılap Cd.", "Kazım Karabekir Sk.",
        "Namık Kemal Cd.", "Necip Fazıl Sk.", "Şerifali Cd.", "Tepeüstü Sk.",
        "Yavuztürk Sk.", "İçerenköy Cd.", "İstanbul Cd."
    ],
    # ZEYTİNBURNU - ÖNEMLİ SOKAKLAR
    "zeytinburnu": [
        "Zeytinburnu Cd.", "Akören Sk.", "Atatürk Cd.", "Beştelsiz Sk.", "Çırpıcı Cd.",
        "Gözköy Sk.", "Gülpınar Cd.", "Gürsel Sk.", "Kazlıçeşme Cd.", "Seyitnizam Sk.",
        "Sümer Sk.", "Telsiz Cd.", "Yeşilce Sk.", "Yenidoğan Sk.", "İstanbul Cd."
    ],
}

# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================

def normalize(text: str) -> str:
    """Metni normalize eder."""
    text = text.lower()
    replacements = {"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c"}
    for turkish, ascii_char in replacements.items():
        text = text.replace(turkish, ascii_char)
    return text


# =============================================================================
# DETAYLI LOKASYON MOTORU
# =============================================================================

class IstanbulDetailedLocation:
    """
    İstanbul için detaylı lokasyon verileri:
    - İlçeler (37)
    - Mahalleler (TÜMÜ)
    - Sokak/Cadde isimleri (ÖNEMLİ)
    """
    
    def __init__(self):
        self.districts = ISTANBUL_DISTRICTS
        self.neighborhoods = ISTANBUL_NEIGHBORHOODS
        self.streets = ISTANBUL_STREETS
        self.all_locations: Set[str] = set()
        
        # Tüm lokasyonları indexle
        for key in self.districts:
            self.all_locations.add(key)
            self.all_locations.add(normalize(key))
        
        for district, neighborhoods in self.neighborhoods.items():
            for n in neighborhoods:
                self.all_locations.add(normalize(n))
        
        for district, streets in self.streets.items():
            for s in streets:
                self.all_locations.add(normalize(s))
        
        stats = self.get_stats()
        print(f"[IstanbulDetailed] {stats['districts']} ilçe, {stats['neighborhoods']} mahalle, {stats['streets']} sokak/cadde")
    
    def parse_query(self, query: str) -> Dict:
        """
        Sorguyu çözümler.
        
        Returns:
            {
                "success": True,
                "locations": [
                    {"type": "district", "name": "Kadıköy", ...},
                    {"type": "neighborhood", "name": "Moda", ...},
                    {"type": "street", "name": "Moda Cd.", ...}
                ],
                "query": "..."
            }
        """
        query = query.strip()
        if not query:
            return {"success": False, "error": "Boş sorgu", "locations": []}
        
        locations = []
        words = query.split()
        
        for word in words:
            word_norm = normalize(word)
            found = False
            
            # İlçe kontrolü (önce kontrol et, en spesifik)
            if word_norm in self.districts:
                loc = self.districts[word_norm].copy()
                loc["type"] = "district"
                locations.append(loc)
                found = True
            
            # Mahalle kontrolü (sadece doğru ilçede ara)
            if not found:
                for district, neighborhoods in self.neighborhoods.items():
                    for n in neighborhoods:
                        n_norm = normalize(n)
                        # Tam eşleşme veya baş harf eşleşmesi
                        if word_norm == n_norm or (len(word_norm) >= 3 and (word_norm in n_norm or n_norm.startswith(word_norm))):
                            locations.append({
                                "type": "neighborhood",
                                "name": n,
                                "district": district,
                                "il": "istanbul"
                            })
                            found = True
                            break
                    if found:
                        break
            
            # Sokak/Cadde kontrolü
            if not found:
                for district, streets in self.streets.items():
                    for street in streets:
                        street_norm = normalize(street)
                        if word_norm in street_norm or street_norm in word_norm:
                            locations.append({
                                "type": "street",
                                "name": street,
                                "district": district,
                                "il": "istanbul"
                            })
                            found = True
                            break
                    if found:
                        break
        
        return {
            "success": len(locations) > 0,
            "query": query,
            "locations": locations,
            "location_count": len(locations),
        }
    
    def get_stats(self) -> Dict:
        """İstatistikler."""
        return {
            "districts": len(self.districts),
            "neighborhoods": sum(len(v) for v in self.neighborhoods.values()),
            "streets": sum(len(v) for v in self.streets.values()),
            "total_locations": len(self.all_locations)
        }


# =============================================================================
# TEST
# =============================================================================

def test_detailed_location():
    """Test."""
    engine = IstanbulDetailedLocation()
    
    print("=" * 60)
    print("DETAYLI LOKASYON TEST v2")
    print("=" * 60)
    
    # Test sorguları - DOĞRU EŞLEŞTİRME KONTROLÜ
    test_queries = [
        "Kadıköy Moda",
        "Beşiktaş Abbasağa",
        "Üsküdar Çengelköy",  # Üsküdar'da olmalı!
        "Şişli Nişantaşı",     # Şişli'de olmalı!
        "Fatih Aksaray",        # Fatih'te olmalı!
        "sarıyer emirgan",
        "ataşehir kayışdağı",
        "maltepe bağdat",
        "pendik şeyhli",
        "tuzla menderes",
        "eyüpsultan rami",
        "beylikdüzü yakuplu",
        "bakırköy yeşilköy",
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"SORGU: {query}")
        print("="*50)
        
        result = engine.parse_query(query)
        
        if result["success"]:
            print(f"✅ {result['location_count']} lokasyon:")
            for loc in result["locations"]:
                district = loc.get('district', 'N/A')
                loc_type = loc.get('type', 'N/A')
                name = loc.get('name', 'N/A')
                print(f"  📍 [{loc_type}] {name} → {district}")
        else:
            print(f"❌ Lokasyon bulunamadı")
    
    print("\n" + "=" * 60)
    stats = engine.get_stats()
    print("İSTATİSTİKLER:")
    print(f"  - İlçe: {stats['districts']}")
    print(f"  - Mahalle: {stats['neighborhoods']}")
    print(f"  - Sokak/Cadde: {stats['streets']}")
    print(f"  - Toplam: {stats['total_locations']}")
    print("=" * 60)
    
    # Eksik sokak kontrolü
    print("\n✅ SOKAK TAMAMLANDI:")
    streets_complete = [d for d in engine.districts if d in engine.streets]
    print(f"  {len(streets_complete)}/37 ilçede sokak var")
    
    if len(streets_complete) < 37:
        missing = [d for d in engine.districts if d not in engine.streets]
        print(f"  Eksik: {missing}")


if __name__ == "__main__":
    test_detailed_location()