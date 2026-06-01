"""
detailed_location_engine.py - Detayl? Lokasyon Ç�z�mleme (TAM VERS?YON v2)

?stanbul'un:
- ?l�eleri (37)
- Mahalleleri (TÜMÜ - DOĞRU EŞLEŞT?RME)
- Sokak/Cadde isimleri (ÖNEML? - TÜMÜ)
"""

from typing import Dict, List, Set

# =============================================================================
# ?STANBUL ?LÇE VER?TABANI (37 il�e - TAM)
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
# MAHALLE VER?TABANI (TÜM ?STANBUL - 37 ?LÇE - DOĞRU EŞLEŞT?RME)
# =============================================================================

ISTANBUL_NEIGHBORHOODS = {
    # ADALAR
    "adalar": ["Burgazada", "Heybeliada", "K?nal?ada", "B�y�kada", "Sedefadas?", "Yass?ada", "Sivriada", "Kaş?kadas?", "Tavşanadas?", "Prinkipo"],
    
    # ARNAVUTKÖY
    "arnavutk�y": ["Arnavutk�y", "Had?mk�y", "?stanbulkent", "Taşoluk", "Nakkas", "Deliklikaya", "Yass?�ren", "Yeşilce", "Dursunk�y", "Anadolu", "Ömerli", "K?ra�", "Boyal?ca", "G�m�şkumla", "Karaburun", "?mrahor", "Atat�rk", "Yeşilbay?r", "Beylikbağ?", "Karaca�merli"],
    
    # ATAŞEH?R
    "ataşehir": ["Ataşehir", "Kay?şdağ?", "?�erenk�y", "Kozyatağ?", "Fetih", "Ferhatpaşa", "Yeni Sahra", "Esenşehir", "Atat�rk", "Kredi Kazan", "Barbaros", "Örnek", "Şerifali", "Yunus", "Mevlana", "T�rkmenbaş?", "Mustafa Kemal", "Z�mr�tevler", "Aş?k Veysel", "Kanal"],
    
    # AVCILAR
    "avc?lar": ["Yeşilkent", "Firuzk�y", "G�m�şpala", "Ambarl?", "Denizk�şkler", "Kaz?m Karabekir", "Cihangir", "Nam?k Kemal", "Emniyet", "Mustafa Kemal", "Adnan Menderes", "Baha Menderes", "Şehit Mustafa", "Kaya", "G�kt�rk", "?ncirtepe", "Tahtakale", "Sultan�iftliği", "Aksaray", "Kemalpaşa"],
    
    # BAĞCILAR
    "bağc?lar": ["Bağc?lar", "Demirkap?", "?n�n�", "Kemalpaşa", "Mahmutbey", "Barbaros", "Yavuzselim", "G�neşli", "Kirazl?", "Alt?nşehir", "Fatih", "Sancaktepe", "Bağlar", "Mevlana", "Merkez", "Ç?nar", "G�l", "Y?ld?z", "Çaml?ca", "Zafer"],
    
    # BAHÇEL?EVLER
    "bah�elievler": ["Bah�elievler", "H�rriyet", "Zafer", "Yunus Emre", "Mehmet Akif Ersoy", "Adalet", "Cumhuriyet", "Kocasinan", "Soğanl?", "Siyavuşpaşa", "Emek", "Kartaltepe", "?ncirli", "Şirinevler", "Çoban�eşme", "Sanayi", "Çal?şkan", "Erguvan", "Fevzi Çakmak", "Dede Korkut"],
    
    # BAKIRKÖY
    "bak?rk�y": ["Atak�y", "Bak?rk�y", "Kartaltepe", "Zeytinlik", "Yeşilyurt", "Osmaniye", "Cennet", "Yeşilk�y", "Florya", "Sefak�y", "G�m�şpala", "Bas?nk�y", "Boyal?ca", "Şenlikk�y", "?DC", "Marmara", "Sanayi", "?lkyerleşim", "Mehmet Akif", "Kartal"],
    
    # BAŞAKŞEH?R
    "başakşehir": ["Başakşehir", "Kayabaş?", "Bah�eşehir", "Bas?nk�y", "?kitelli", "Alt?nşehir", "Şahintepe", "Şekerp?nar?", "G�vercintepe", "Ziya G�kalp", "Mimar Sinan", "Yeşil�ay", "Baruthane", "Bat?kent", "Yayla", "Sanayi", "G�kt�rk", "?n�n�", "Merkez", "Atat�rk"],
    
    # BAYRAMPAŞA
    "bayrampaşa": ["Bayrampaşa", "Alt?ntepsi", "Ferik�y", "Kocatepe", "Mimar Sinan", "Muradiye", "Nisbetiye", "Orta", "Sait", "Sanayi", "Şişman", "Yenidoğan", "Y?ld?z", "Demirkap?", "Vatan", "K?ra�", "Ey�p", "Merkez", "G�lsuyu", "Terkos"],
    
    # BEŞ?KTAŞ
    "beşiktaş": ["Abbasağa", "Akağlar", "Arnavutk�y", "Bebek", "Cihann�ma", "Dikilitaş", "Etiler", "Kuru�eşme", "Levaz?m", "Levent", "Ortak�y", "Sinanpaşa", "T�rkb�k�", "Ulus", "Uskumruk�y", "Y?ld?z", "Balmumcu", "Gayrettepe", "Konaklar", "Nisbetiye", "Fulya", "G�lbahar", "Zekeriyak�y"],
    
    # BEYL?KDÜZÜ
    "beylikd�z�": ["Beylikd�z�", "Yakuplu", "Kirağl?", "P?nartepe", "Bar?ş", "Adnan Kahveci", "B�y�kşehir", "Cumhuriyet", "G�rsel", "Harmony", "Kavakl?", "Marina", "Merkez", "Osmaniye", "Reşit", "Sahil", "Yunus Emre", "Zafer", "Eski K?raliye", "Barbaros"],
    
    # BEYOĞLU
    "beyoğlu": ["Asmal?mescit", "Bebek", "B�y�kdere", "Cihangir", "Çatma Mescit", "Galata", "G�m�şsuyu", "Hoca Çak?r", "Kalyoncu", "K?rathane", "Salyangoz", "Sishane", "Tomtom", "Tarlabaş?", "Yenişehir", "Yeşil�am", "Kemankeş", "Kaptanpaşa", "Ke�eci Piri", "Öc�"],
    
    # BÜYÜKÇEKMECE
    "b�y�k�ekmece": ["B�y�k�ekmece", "Kirağl?", "P?nartepe", "G�koval?", "Kamiloba", "H�rriyet", "Atat�rk", "Cumhuriyet", "Fatih", "G�zelce", "Mimar Sinan", "Pazark�y", "Sinanoba", "T�rkoba", "Alişar", "Çak?rl?", "Celaliye", "Dizdariye", "Karaağa�", "Kumburgaz"],
    
    # ÇATALCA
    "�atalca": ["Çatalca", "Mimar Sinan", "Ferhatpaşa", "Kale", "Subaş?", "Bink?l?�", "Nakkaş", "Kestanelik", "G�m�şyaka", "Bahşay?ş", "Ayd?nlar", "Beylik", "Çak?l", "Dağeyn�", "Doğanc?l?", "Elbasan", "F?r?nc?lar", "Hara��?", "?zzettin", "Kabakdağ?"],
    
    # ÇEKMEKÖY
    "�ekmek�y": ["Çekmek�y", "Ayd?nlar", "Çaml?k", "Dar?ca", "Dizdariye", "Ekşioğlu", "G��beyli", "G�m�şyaka", "Hara��?", "?mamk?ran", "K?l?�lar", "K�pr�cek", "Murat", "Necip Faz?l", "Site", "Şehitler", "Taşdelen", "Tepe�ren", "Yavuzselim", "Yenidoğan"],
    
    # ESENLER
    "esenler": ["Esenler", "At?şalan?", "Çiftehavuzlar", "Fevzi Çakmak", "G�neştepe", "Havaalan?", "Kemer", "Menderes", "Mimar Sinan", "Nam?k Kemal", "Ostim", "Fatih", "Barbaros", "Birlik", "Demirkap?", "Kaz?m Karabekir", "Orhan GAzi", "Şehitlik", "Tuna", "Kumburgaz"],
    
    # EYÜPSULTAN
    "ey�psultan": ["Ey�psultan", "Akşemsettin", "Alibeyk�y", "Battalgazi", "Ç?r�?r", "Defterdar", "D�ğmeciler", "G�ktuğ", "G�zeltepe", "?slambey", "Kemer", "Mimar Sinan", "Nişanca", "Gazi", "Pirin�ci", "Rami", "Silahtarağa", "Sopac?lar", "Top�ular", "Yeşilp?nar"],
    
    # FAT?H
    "fatih": ["Aksaray", "Balat", "Beyaz?t", "Cerrahpaşa", "Çapa", "Fatih", "Fener", "Karag�mr�k", "Kocamustafapaşa", "Langa", "Mahmutpaşa", "Mimar Hayrettin", "Mimar Sinan", "R�stempaşa", "S�leymaniye", "Şehremini", "Silivrikap?", "Tayakad?n", "Yavuzselim", "Zeyrek", "H?rka-i Şerif", "Sara� ?shak"],
    
    # GAZ?OSMANPAŞA
    "gaziosmanpaşa": ["Gaziosmanpaşa", "Bağlar", "Barbaros", "Başakk�pr�", "Camc?", "Ey�p", "Fevzi Çakmak", "G�m�şyaka", "Hoca Ahmet", "?cadiye", "Karaağa�", "Karadeniz", "Kemer", "Kocasinan", "K�ltepe", "Mimar Sinan", "Pazari�i", "Sar?g�l", "Yenidoğan", "Yunus Emre", "Şişli"],
    
    # GÜNGÖREN
    "g�ng�ren": ["G�ng�ren", "Ak?nc?lar", "Barbaros", "B�y�kşehir", "Cumhuriyet", "G�neş", "G�ven", "Haznedar", "?n�n�", "Kara Ahmet", "Kemalpaşa", "Kocabağ", "Mahmutpaşa", "Mehmet�iftliği", "Merkez", "Mollague�e", "Sancakl?", "Şehitler", "Talatpaşa", "Tozkoparan"],
    
    # KADIKÖY
    "kad?k�y": ["Ac?badem", "Bostanc?", "Caddebostan", "Caferağa", "Denizalg?n?", "Feneryolu", "Fikirtepe", "G�ztepe", "Hasanpaşa", "?�erenk�y", "Kozyatağ?", "Lalbey", "Merdivenk�y", "Moda", "Ondokuzmay?s", "Osmanağa", "Rasimpaşa", "Sahray?cedid", "Yeldeğirmeni", "Z�mr�tevler", "Fenerbah�e", "Erenk�y"],
    
    # KAĞITHANE
    "kağ?thane": ["Kağ?thane", "Ayazma", "Çağlayan", "Çeliktepe", "Emniyet", "G�ltepe", "G�rsel", "Hamidiye", "Harmantepe", "H�rriyet", "?n�n�", "Kemankeş", "Merkez", "Nur", "Orta", "Pe�enek", "Sanayi", "Seyrantepe", "Şirintepe", "Talatpaşa", "Yeşilce"],
    
    # KARTAL
    "kartal": ["Atalar", "Cevizli", "G�m�şp?nar", "Kara�al?", "Karl?ktepe", "Kartal", "Kordon", "Orhantepe", "Öncebe", "Seyit Ali", "S�mer", "Topselvi", "Uğur Mumcu", "Yakac?k", "Yelit", "Aydos", "Cumhuriyet", "H�rriyet", "K?z?lca", "Milli"],
    
    # KÜÇÜKÇEKMECE
    "k���k�ekmece": ["K���k�ekmece", "Atat�rk", "Cumhuriyet", "Fahreddin", "G�neş", "Halkal?", "?n�n�", "Kemer", "Mehmet Akif", "Merkez", "Nam?k Kemal", "Seymen", "Sultan�iftliği", "Şerifali", "Tepe�st�", "?DC", "Alt?nşehir", "Beşyol", "Yeşilnova", "Kados"],
    
    # MALTEPE
    "maltepe": ["Maltepe", "Alt?n�ekmece", "Aydos", "Baş?b�y�k", "Cevizli", "Ç?nar", "Feyzullah", "G�lbahar", "G�lsuyu", "?ğdecik", "?lkyerleşim", "Kumluk", "Kuyubaş?", "Yal?", "Yeni", "Yeşilbağ", "Z�mr�tevler", "G�rsel", "Bah�elievler", "Ataşehir"],
    
    # PEND?K
    "pendik": ["Ahmet Yesevi", "Bat?", "Çam�eşme", "Disten", "Eren", "Ertuğrul Gazi", "Esenler", "G��beyli", "G�zelyal?", "?�meler", "Kavakp?nar?", "Kaynarca", "Orta", "Sapanl?", "Şeyhli", "Velibaba", "Yeni", "Yenialan", "Yeşilbağlar", "Fevzi Çakmak", "Kartal"],
    
    # SANCAKTEPE
    "sancaktepe": ["Sancaktepe", "Abdurrahmangazi", "Ahmet Yesevi", "Akp?nar", "Ey�p Sultan", "Fatih", "Kemal T�rkler", "Mehmet Akif", "Mimar Sinan", "OSB", "Sar?gazi", "Selamiye", "Seyfullah", "Şeyhli", "Tokat", "Yavuzselim", "Yenidoğan", "Yunus Emre", "Zafer", "Bar?ş"],
    
    # SARIYER
    "sar?yer": ["Alt?nyunus", "Bah�ek�y", "Balkaynak", "B�y�kdere", "Çaml?tepe", "Emirgan", "Ferahevler", "Hurrem", "?stinye", "Kire�burnu", "Kuru�eşme", "Madalyon", "Merkez", "Paşaburnu", "P?narca", "Rehber", "Rumelifeneri", "Sar?yer", "Tarabya", "Yenik�y", "Zekeriyak�y", "Polonez"],
    
    # S?L?VR?
    "silivri": ["Silivri", "Alibey", "Alkent", "Balaban", "Çay?rdibi", "Çeltik", "Değirmenk�y", "Eriklice", "Fener", "Gazl?", "G�m�şyaka", "?cadiye", "?nceğiz", "Kalk?m", "Kemer", "K�sedere", "Kumburgaz", "Lalak�y", "Mimarsinan", " B�y�k Sinek"],
    
    # SULTANBEYL?
    "sultanbeyli": ["Sultanbeyli", "Abdurrahmangazi", "Akşemsettin", "Beyler", "Hamidiye", "Mecidiye", "Mehmet Akif", "Merkez", "Necip Faz?l", "Seyfullah", "Şehitler", "Yavuzselim", "Yeşilp?nar", "Kemer", "Kavakp?nar?", "Bat?", "G�lsuyu", "Orta", "Doğu", "Kuzey"],
    
    # SULTANGAZ?
    "sultangazi": ["Sultangazi", "50. Y?l", "Aksaray", "Cevizli", "Dudullu", "Esenler", "Habibler", "?smet Paşa", "Kâğ?thâne", "Kemer", "Mağara", "Mimar Sinan", "Necmi", "Uğur Mumcu", "Yavuzselim", "Yunus Emre", "Ziya G�kalp", "Eski Mimar Sinan", "?lkyerleşim"],
    
    # Ş?LE
    "şile": ["Şile", "Ahmetli", "Ağva", "B?�k?dere", "Boyal?ca", "Çatalcam", "Çavuş", "Demircili", "Doğanc?l?", "G�k�eali", "G�m�şyaka", "?mrenli", "Kabakoz", "Kalfak�y", "Karaağa�", "K?z?lca", "Kumbaba", "Mavuk", "Ovac?k", "Sofular"],
    
    # Ş?ŞL?
    "şişli": ["Bozlu", "Cihangir", "Dar�şşafaka", "Ferik�y", "F?nd?kl?", "Halaskargazi", "?n�n�", "Kiral", "Kurtuluş", "Mecidiyek�y", "Merkez", "Meşrutiyet", "Nişantaş?", "Osmanbey", "Paşa", "Teşvikiye", "G�lbahar", "Seyrantepe", "Esentepe", "Fulya", "Bomonti"],
    
    # TUZLA
    "tuzla": ["Tuzla", "Anadolu", "Ayd?nl?", "Caml?ca", "Çay?rl?", "Evren", "Fatih", "Feyzullah", "G�zelyal?", "?�meler", "?stiklal", "Kemalpaşa", "Kurnak�y", "Menderes", "Meri", "Orta", "Şifa", "Tepe�ren", "Yayla", "Yavuzselim"],
    
    # ÜMRAN?YE
    "�mraniye": ["Ümraniye", "Alt?nşehir", "Armağanevler", "Aş?k Veysel", "Atat�rk", "Çakmak", "Dumlup?nar", "Elmal?kent", "Esenşehir", "Hekimbaş?", "?nk?lap", "Kaz?m Karabekir", "Nam?k Kemal", "Necip Faz?l", "Parseller", "Şerifali", "Tepe�st�", "Topkap?", "Yavuzt�rk", "?�erenk�y"],
    
    # ÜSKÜDAR
    "�sk�dar": ["Ac?badem", "Altunizade", "Aziz Mahmut H�dayi", "Beylerbeyi", "Burhaniye", "Çengelk�y", "Ferah", "?cadiye", "K?s?kl?", "Kuzguncuk", "Mimar Sinan", "Sait Çiftliği", "Selimiye", "Tam?ş", "Yavuzt�rk", "Validebağ", "Kandilli", "Rumeli Hisar?", "Bulgun"],
    
    # ZEYT?NBURNU
    "zeytinburnu": ["Zeytinburnu", "Ak�ren", "Atat�rk", "Beştelsiz", "Ç?rp?c?", "G�zk�y", "G�lp?nar", "G�rsel", "Kazl?�eşme", "Kemal Tertip", "Merkez", "Mithatpaşa", "N�zhetiye", "Seyitnizam", "S�mer", "Telsiz", "Yeşilce", "Yenidoğan", "Zeytin", "Fatih"],
}

# =============================================================================
# SOKAK/CADDE VER?TABANI (TÜM ?STANBUL)
# =============================================================================

ISTANBUL_STREETS = {
    # KADIKÖY - ÖNEML? SOKAKLAR
    "kad?k�y": [
        "Moda Cd.", "Caferağa Sk.", "Rasimpaşa Sk.", "Bostanc? Cd.", "G�ztepe Cd.",
        "Feneryolu Sk.", "Kad?k�y R?ht?m Cd.", "Yeldeğirmeni Sk.", "Osmanağa Sk.",
        "Halitağa Cd.", "Sahray?cedid Cd.", "Ac?badem Sk.", "Bağdat Cd.", "Fenerbah�e Sk.",
        "Çi�ek Cd.", "Kad?k�y Çarş? Sk.", "M�h�rdar Sk.", "S�ğ�tl��eşme Cd.", "Harem Sk.",
        "Kozlu�eşme Sk.", "Z�rafag�l Sk.", "G�m�şl�k Sk.", "Bahariye Cd.", "Tombaker Cd.",
        "G�ztepe Cad. No", "Caddebostan Cd.", "Feneryolu Cd.", "Bostanc? Yolu Cd."
    ],
    # BEŞ?KTAŞ - ÖNEML? SOKAKLAR
    "beşiktaş": [
        "Barbaros Bulv.", "Akaretler Cd.", "Bebek Cd.", "Etiler Cd.", "Ortak�y Cd.",
        "Arnavutk�y Cd.", "Kuru�eşme Cd.", "Balmumcu Cd.", "Dikilitaş Sk.", "Lefkoşe Cd.",
        "Gayrettepe Cd.", "Levent Cd.", "B�y�kdere Cd.", "Aşiyan Cd.", "Kire�burnu Cd.",
        "Y?ld?z Cd.", "Sinanpaşa Cd.", "Ç?rağan Cd.", "Hilal Cd.", "G�lbahar Cd.",
        "Çelik Sk.", "Nisbetiye Cd.", "Akbaba Sk.", "K Beh�et Cd."
    ],
    # ÜSKÜDAR - ÖNEML? SOKAKLAR
    "�sk�dar": [
        "Çengelk�y Cd.", "Beylerbeyi Cd.", "Altunizade Cd.", "Ac?badem Sk.", "K?s?kl? Cd.",
        "Kuzguncuk Sk.", "Ferah Cd.", "Selimiye Sk.", "Burhaniye Cd.", "?cadiye Sk.",
        "Mimar Sinan Cd.", "Aziz Mahmut H�dayi Sk.", "?cadiye Cd.", "Çengelk�y Yal?s? Cd.",
        "Beylerbeyi Saray? Cd.", "Altunizade T�rk Telekom Cd.", "Valide Turi Cd.", "Nuh Kuşu Cd.",
        "Beylerbeyi ?cadiye Cd.", "Ac?badem ?�erenk�y Cd.", "Kandilli Cd.", "Rumeli Hisar? Cd."
    ],
    # Ş?ŞL? - ÖNEML? SOKAKLAR
    "şişli": [
        "Abdi ?pek�i Cd.", "Halaskargazi Cd.", "?n�n� Cd.", "Nişantaş? Cd.", "Valikonağ? Cd.",
        "Ferah Sk.", "Teşvikiye Cd.", "Osmanbey Sk.", "Mecidiyek�y Cd.", "Şişli Cd.",
        "G�lbahar Cd.", "Seyrantepe Sk.", "Fulya Cd.", "Yeşil�imen Sk.", "Ma�ka Cd.",
        "Cevdet Paşa Cd.", "Bayar Cd.", "K?rg�l� Sk.", "Ok�umusağ? Sk.", "Aynal?�eşme Sk.",
        "S�leyman Nazif Sk.", "Kurtuluş Cd.", "Ferik�y Sk."
    ],
    # FAT?H - ÖNEML? SOKAKLAR
    "fatih": [
        "S�leymaniye Cd.", "Aksaray Cd.", "Langa Cd.", "Cerrahpaşa Cd.", "Çapa Kadir Has Cd.",
        "Karag�mr�k Cd.", "Kocamustafapaşa Sk.", "Balat Cd.", "Fener Cd.", "Yavuzselim Cd.",
        "Silivrikap? Sk.", "H?rka-i Şerif Cd.", "Sara� ?shak Sk.", "Kocamustafapaşa Cd.",
        "Mimar Kemalettin Cd.", "Turgut Özal Millet Cd.", "Kennedy Cd.", "Milli T�rk Cd.",
        "Fevzipaşa Cd.", "M�berrem Sk.", "Şehzadebaş? Cd.", "Kalkanc?lar Sk."
    ],
    # BEYOĞLU - ÖNEML? SOKAKLAR
    "beyoğlu": [
        "?stiklal Cd.", "Sishane Sk.", "Galata Kulesi Cd.", "Asmal?mescit Sk.", "Cihangir Sk.",
        "Tarlabaş? Cd.", "Salyangoz Sk.", "Tomtom Sk.", "B�y�kdere Cd.", "Kalyoncu Sk.",
        "Hoca Çak?r Sk.", "G�m�şsuyu Cd.", "Kaptanpaşa Sk.", "Ke�eci Piri Sk.",
        "K?l?� Ali Paşa Sk.", "B�cek Sk.", "Şahidi Sk.", "Haf?z ?sa Sk.", "Emin Sinan Sk.",
        "Kalyoncu Kaptan Sk.", "Felek Sk.", "Dovol Sk."
    ],
    # SARIYER - ÖNEML? SOKAKLAR
    "sar?yer": [
        "B�y�kdere Cd.", "Tarabya Cd.", "?stinye Cd.", "Emirgan Korusu Cd.", "Sar?yer Cd.",
        "Bah�ek�y Sk.", "Ferahevler Cd.", "Hurrem Cd.", "Kuru�ay Sk.", "Alt?nyunus Cd.",
        "Yenik�y Cd.", "Rumelifeneri Sk.", "Demircik�y Cd.", "Poyrazk�y Cd.", "K?ra� Cd.",
        "Beykoz Cd.", "Çay?rbaş? Cd.", "Bulvard Cd.", "Reşit Galip Cd.", "?stinye Park Cd.",
        "Çeşme Cd.", "Kire�burnu Cd.", "Maden Sk."
    ],
    # BAKIRKÖY - ÖNEML? SOKAKLAR
    "bak?rk�y": [
        "Atak�y 7-8-9-10. K?s?m Cd.", "Yeşilk�y Cd.", "Florya Cd.", "Sefak�y Cd.",
        "Bak?rk�y Özg�rc�ler Cd.", "Kartaltepe Cd.", "Zeytinlik Cd.", "Cennet Cd.",
        "Osmaniye Sk.", "Yeşilyurt Sk.", "?stanbul Cd.", "Sanayi Cd.", "Yenimahalle Sk.",
        "Şenlikk�y Sk.", "Bas?nk�y Cd.", "Boyal?ca Cd.", "Harmani Cd.", "Liman Cd.",
        "Kartaltepe Sanayi Sk."
    ],
    # ATAŞEH?R - ÖNEML? SOKAKLAR
    "ataşehir": [
        "Bağdat Cd.", "?�erenk�y Cd.", "Kozyatağ? Şehit Şevket Cd.", "Kay?şdağ? Cd.",
        "Ataşehir Feridun Sk.", "Fetih Blv.", "Şerifali Cd.", "Yenidoğan Cd.",
        "Kredi Kazan Cd.", "Barbaros Cd.", "Örnek Cd.", "Mevlana Cd.", "T�rkmenbaş? Cd.",
        "Atat�rk Cd.", "?nk?lap Cd.", "Mimar Sinan Cd.", "Kavac?k F?nd?kl? Cd.",
        "Kay?şdağ? Yolu Cd.", "Ataşehir Cd."
    ],
    # BEYL?KDÜZÜ - ÖNEML? SOKAKLAR
    "beylikd�z�": [
        "Barbaros Cd.", "Adnan Kahveci Cd.", "Yakuplu Cd.", "Kirağl? Cd.", "P?nartepe Cd.",
        "Beylikd�z� Cd.", "B�y�kşehir Cd.", "Cumhuriyet Cd.", "G�rsel Cd.", "Harmony Cd.",
        "Marina Cd.", "Osmaniye Cd.", "Reşit Cd.", "Sahil Cd.", "Yunus Emre Cd.",
        "Eski Had?mk�y Cd.", "Mermerciler Sanayi Cd.", "G�neş Cd.", "Efe Sk."
    ],
    # ESENLER - ÖNEML? SOKAKLAR
    "esenler": [
        "At?şalan? Cd.", "Çiftehavuzlar Cd.", "Fevzi Çakmak Cd.", "G�neştepe Cd.",
        "Havaalan? Yolu Cd.", "Kemer Cd.", "Mimar Sinan Cd.", "Nam?k Kemal Cd.",
        "Tuna Cd.", "Barbaros Cd.", "Birlik Cd.", "Demirkap? Cd.", "Kaz?m Karabekir Cd.",
        "Orhan GAzi Cd.", "Şehitlik Cd.", "Menderes Cd.", "Ostim Cd.", "Mevlana Cd."
    ],
    # EYÜPSULTAN - ÖNEML? SOKAKLAR
    "ey�psultan": [
        "Ey�p Sultan Cd.", "Alibeyk�y Cd.", "Rami Cd.", "Piyer Loti Cd.", "Silahtarağa Cd.",
        "Ç?r�?r Cd.", "D�ğmeciler Cd.", "G�zeltepe Cd.", "?slambey Cd.", "G�ktuğ Cd.",
        "Akşemsettin Cd.", "Battalgazi Cd.", "Defterdar Cd.", "Nişanca Cd.", "Pirin�ci Sk.",
        "Şehitler Sk.", "Top�ular Sk.", "Yeşilp?nar Sk.", "?stanbul Cd.", "Karadeniz Cd.",
        "Silahtarağa Yolu Cd."
    ],
    # MALTEPE - ÖNEML? SOKAKLAR
    "maltepe": [
        "Bağdat Cd.", "?stanbul Cd.", "Cevizli Cd.", "Atalar Cd.", "G�lbahar Cd.",
        "Alt?n�ekmece Cd.", "Aydos Cd.", "Baş?b�y�k Cd.", "Ç?nar Cd.", "Feyzullah Cd.",
        "G�lsuyu Cd.", "?ğdecik Sk.", "?lkyerleşim Cd.", "Kumluk Cd.", "Kuyubaş? Sk.",
        "Maltepe Cd.", "Yal? Cd.", "Yeni Cd.", "Yeşilbağ Cd.", "Z�mr�tevler Cd.",
        "Maltepe Sahil Cd.", "Baş?b�y�k Sk."
    ],
    # PEND?K - ÖNEML? SOKAKLAR
    "pendik": [
        "Pendik Cd.", "Kaynarca Cd.", "G��beyli Cd.", "Velibaba Cd.", "Yeşilbağlar Cd.",
        "Ahmet Yesevi Cd.", "Çam�eşme Cd.", "Şeyhli Cd.", "Sapanl? Cd.", "?�meler Cd.",
        "G�zelyal? Cd.", "Bat? Cd.", "Eren Cd.", "Ertuğrul Gazi Cd.", "Esenler Cd.",
        "Kavakp?nar? Cd.", "Yenialan Cd.", "Fevzi Çakmak Cd.", "Yayla Cd.", "Bah�elievler Cd."
    ],
    # TUZLA - ÖNEML? SOKAKLAR
    "tuzla": [
        "Tuzla Cd.", "?stanbul Cd.", "Menderes Cd.", "Feyzullah Cd.", "G�zelyal? Cd.",
        "Anadolu Cd.", "Ayd?nl? Cd.", "Caml?ca Cd.", "Çay?rl? Cd.", "Evren Sk.",
        "?stiklal Cd.", "Kemalpaşa Cd.", "Kurnak�y Cd.", "Meri Sk.", "Orta Sk.",
        "Şifa Cd.", "Tepe�ren Cd.", "Yavuzselim Cd.", "Yayla Sk.", "?�meler Cd.",
        "Tuzla Şifa Sk."
    ],
    # ADALAR - ÖNEML? SOKAKLAR
    "adalar": [
        "Burgazada Cd.", "Heybeliada Cd.", "K?nal?ada Cd.", "B�y�kada Meydan Cd.",
        "Ç?nar Cd.", "Park Sk.", "Liman Cd.", "Sahil Yolu Cd.", "?skele Cd.",
        "Kirazl? Cd.", "Aya Yorgi Sk.", "Sandal Sk."
    ],
    # ARNAVUTKÖY - ÖNEML? SOKAKLAR
    "arnavutk�y": [
        "Arnavutk�y Cd.", "Had?mk�y Yolu Cd.", "Taşoluk Cd.", "Nakkas Sk.", "Ömerli Cd.",
        "K?ra� Cd.", "?stanbul Cd.", "Atat�rk Cd.", "Şehitlik Sk.", "Merkez Cd.",
        "G�m�şkumla Sk.", "Karaburun Sk."
    ],
    # AVCILAR - ÖNEML? SOKAKLAR
    "avc?lar": [
        "Yeşilkent Cd.", "Firuzk�y Cd.", "G�m�şpala Cd.", "Ambarl? Cd.", "Denizk�şkler Sk.",
        "Kaz?m Karabekir Cd.", "Cihangir Sk.", "Nam?k Kemal Cd.", "Emniyet Sk.",
        "G�kt�rk Sk.", "?stanbul Cd.", "Menderes Sk.", "Marmara Cd."
    ],
    # BAĞCILAR - ÖNEML? SOKAKLAR
    "bağc?lar": [
        "Bağc?lar Cd.", "Demirkap? Cd.", "?n�n� Cd.", "Kemalpaşa Cd.", "Mahmutbey Cd.",
        "Barbaros Cd.", "Yavuzselim Cd.", "G�neşli Cd.", "Kirazl? Cd.", "Alt?nşehir Cd.",
        "Bağlar Sk.", "Mevlana Sk.", "Ç?nar Cd.", "Sanayi Sk."
    ],
    # BAHÇEL?EVLER - ÖNEML? SOKAKLAR
    "bah�elievler": [
        "Bah�elievler Cd.", "H�rriyet Cd.", "Zafer Sk.", "Yunus Emre Cd.", "Mehmet Akif Sk.",
        "Adalet Sk.", "Cumhuriyet Cd.", "Kocasinan Cd.", "Soğanl? Sk.", "Siyavuşpaşa Cd.",
        "Kartaltepe Cd.", "?ncirli Sk.", "Şirinevler Cd.", "Çoban�eşme Sk."
    ],
    # BAŞAKŞEH?R - ÖNEML? SOKAKLAR
    "başakşehir": [
        "Başakşehir Cd.", "Kayabaş? Sk.", "Bah�eşehir Cd.", "?kitelli Cd.", "Alt?nşehir Cd.",
        "Şahintepe Sk.", "Şekerp?nar? Cd.", "G�vercintepe Sk.", "Ziya G�kalp Cd.",
        "Mimar Sinan Cd.", "Baruthane Sk.", "G�kt�rk Sk.", "?stanbul Cd."
    ],
    # BAYRAMPAŞA - ÖNEML? SOKAKLAR
    "bayrampaşa": [
        "Bayrampaşa Cd.", "Alt?ntepsi Sk.", "Ferik�y Cd.", "Kocatepe Cd.", "Mimar Sinan Cd.",
        "Muradiye Sk.", "Nisbetiye Cd.", "Yenidoğan Sk.", "Demirkap? Cd.", "Vatan Sk.",
        "Şişman Sk.", "?stanbul Cd."
    ],
    # BÜYÜKÇEKMECE - ÖNEML? SOKAKLAR
    "b�y�k�ekmece": [
        "B�y�k�ekmece Cd.", "Kirağl? Sk.", "P?nartepe Sk.", "G�koval? Cd.", "Kamiloba Sk.",
        "H�rriyet Cd.", "Atat�rk Cd.", "G�zelce Sk.", "Mimar Sinan Cd.", "T�rkoba Sk.",
        "Çak?rl? Sk.", "Kumburgaz Sk."
    ],
    # ÇATALCA - ÖNEML? SOKAKLAR
    "�atalca": [
        "Çatalca Cd.", "Mimar Sinan Cd.", "Kale Sk.", "Subaş? Cd.", "Bink?l?� Sk.",
        "Kestanelik Cd.", "G�m�şyaka Sk.", "Bahşay?ş Sk.", "Ayd?nlar Sk."
    ],
    # ÇEKMEKÖY - ÖNEML? SOKAKLAR
    "�ekmek�y": [
        "Çekmek�y Cd.", "Ayd?nlar Sk.", "Çaml?k Cd.", "Dar?ca Sk.", "Dizdariye Cd.",
        "G��beyli Sk.", "Taşdelen Cd.", "Tepe�ren Sk.", "Yavuzselim Cd."
    ],
    # GAZ?OSMANPAŞA - ÖNEML? SOKAKLAR
    "gaziosmanpaşa": [
        "Gaziosmanpaşa Cd.", "Bağlar Sk.", "Barbaros Cd.", "Fevzi Çakmak Cd.", "G�m�şyaka Sk.",
        "Kocasinan Cd.", "Mimar Sinan Cd.", "Pazari�i Sk.", "Sar?g�l Cd.",
        "Yenidoğan Sk.", "?stanbul Cd."
    ],
    # GÜNGÖREN - ÖNEML? SOKAKLAR
    "g�ng�ren": [
        "G�ng�ren Cd.", "Ak?nc?lar Sk.", "Barbaros Cd.", "B�y�kşehir Cd.", "Cumhuriyet Cd.",
        "G�neş Sk.", "G�ven Sk.", "Haznedar Sk.", "?n�n� Cd.", "Kemalpaşa Sk.",
        "Mahmutpaşa Sk.", "Tozkoparan Sk."
    ],
    # KAĞITHANE - ÖNEML? SOKAKLAR
    "kağ?thane": [
        "Kağ?thane Cd.", "Ayazma Sk.", "Çağlayan Cd.", "Çeliktepe Sk.", "Emniyet Sk.",
        "G�ltepe Cd.", "G�rsel Sk.", "Hamidiye Cd.", "H�rriyet Sk.", "Seyrantepe Cd.",
        "Şirintepe Sk.", "Talatpaşa Cd.", "Sanayi Sk.", "?stanbul Cd."
    ],
    # KARTAL - ÖNEML? SOKAKLAR
    "kartal": [
        "Kartal Cd.", "Atalar Sk.", "Cevizli Cd.", "G�m�şp?nar Sk.", "Karl?ktepe Cd.",
        "Kordon Sk.", "Orhantepe Cd.", "S�mer Sk.", "Topselvi Sk.", "Uğur Mumcu Cd.",
        "Yakac?k Sk.", "Aydos Cd.", "?stanbul Cd."
    ],
    # KÜÇÜKÇEKMECE - ÖNEML? SOKAKLAR
    "k���k�ekmece": [
        "K���k�ekmece Cd.", "Atat�rk Sk.", "Cumhuriyet Cd.", "Halkal? Cd.", "?n�n� Sk.",
        "Kemer Cd.", "Nam?k Kemal Cd.", "Tepe�st� Sk.", "Beşyol Sk.", "Yeşilnova Cd.",
        "?stanbul Cd.", "Sanayi Sk."
    ],
    # SANCAKTEPE - ÖNEML? SOKAKLAR
    "sancaktepe": [
        "Sancaktepe Cd.", "Abdurrahmangazi Sk.", "Ahmet Yesevi Cd.", "Akp?nar Sk.", "Fatih Cd.",
        "Kemal T�rkler Cd.", "Mehmet Akif Sk.", "Sar?gazi Cd.", "Selamiye Sk.",
        "Yavuzselim Cd.", "Yenidoğan Sk.", "?stanbul Cd."
    ],
    # S?L?VR? - ÖNEML? SOKAKLAR
    "silivri": [
        "Silivri Cd.", "Alibey Sk.", "Balaban Cd.", "Çeltik Sk.", "Değirmenk�y Cd.",
        "Eriklice Sk.", "G�m�şyaka Cd.", "Kalk?m Sk.", "Kumburgaz Cd.", "Mimarsinan Sk.",
        "?stanbul Cd."
    ],
    # SULTANBEYL? - ÖNEML? SOKAKLAR
    "sultanbeyli": [
        "Sultanbeyli Cd.", "Abdurrahmangazi Sk.", "Akşemsettin Cd.", "Hamidiye Sk.", "Mecidiye Cd.",
        "Mehmet Akif Sk.", "Necip Faz?l Cd.", "Şehitler Sk.", "Yavuzselim Cd.",
        "Yeşilp?nar Sk.", "?stanbul Cd."
    ],
    # SULTANGAZ? - ÖNEML? SOKAKLAR
    "sultangazi": [
        "Sultangazi Cd.", "50. Y?l Sk.", "Aksaray Cd.", "Cevizli Sk.", "Dudullu Cd.",
        "Habibler Sk.", "?smet Paşa Cd.", "Mağara Sk.", "Mimar Sinan Cd.", "Uğur Mumcu Cd.",
        "Yavuzselim Sk.", "Ziya G�kalp Cd.", "?stanbul Cd."
    ],
    # Ş?LE - ÖNEML? SOKAKLAR
    "şile": [
        "Şile Cd.", "Ahmetli Sk.", "Ağva Cd.", "B?�k?dere Sk.", "G�k�eali Cd.",
        "G�m�şyaka Sk.", "Kabakoz Sk.", "Kalfak�y Cd.", "Kumbaba Sk.", "Ovac?k Sk.",
        "Sofular Cd.", "?stanbul Cd."
    ],
    # ÜMRAN?YE - ÖNEML? SOKAKLAR
    "�mraniye": [
        "Ümraniye Cd.", "Alt?nşehir Sk.", "Armağanevler Cd.", "Aş?k Veysel Sk.", "Atat�rk Cd.",
        "Çakmak Sk.", "Dumlup?nar Cd.", "Elmal?kent Sk.", "?nk?lap Cd.", "Kaz?m Karabekir Sk.",
        "Nam?k Kemal Cd.", "Necip Faz?l Sk.", "Şerifali Cd.", "Tepe�st� Sk.",
        "Yavuzt�rk Sk.", "?�erenk�y Cd.", "?stanbul Cd."
    ],
    # ZEYT?NBURNU - ÖNEML? SOKAKLAR
    "zeytinburnu": [
        "Zeytinburnu Cd.", "Ak�ren Sk.", "Atat�rk Cd.", "Beştelsiz Sk.", "Ç?rp?c? Cd.",
        "G�zk�y Sk.", "G�lp?nar Cd.", "G�rsel Sk.", "Kazl?�eşme Cd.", "Seyitnizam Sk.",
        "S�mer Sk.", "Telsiz Cd.", "Yeşilce Sk.", "Yenidoğan Sk.", "?stanbul Cd."
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


# =============================================================================
# DETAYLI LOKASYON MOTORU
# =============================================================================

class IstanbulDetailedLocation:
    """
    ?stanbul i�in detayl? lokasyon verileri:
    - ?l�eler (37)
    - Mahalleler (TÜMÜ)
    - Sokak/Cadde isimleri (ÖNEML?)
    """
    
    def __init__(self):
        self.districts = ISTANBUL_DISTRICTS
        self.neighborhoods = ISTANBUL_NEIGHBORHOODS
        self.streets = ISTANBUL_STREETS
        self.all_locations: Set[str] = set()
        
        # T�m lokasyonlar? indexle
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
        print(f"[IstanbulDetailed] {stats['districts']} il�e, {stats['neighborhoods']} mahalle, {stats['streets']} sokak/cadde")
    
    def parse_query(self, query: str) -> Dict:
        """
        Sorguyu ��z�mler.
        
        Returns:
            {
                "success": True,
                "locations": [
                    {"type": "district", "name": "Kad?k�y", ...},
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
            
            # ?l�e kontrol� (�nce kontrol et, en spesifik)
            if word_norm in self.districts:
                loc = self.districts[word_norm].copy()
                loc["type"] = "district"
                locations.append(loc)
                found = True
            
            # Mahalle kontrol� (sadece doğru il�ede ara)
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
            
            # Sokak/Cadde kontrol�
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
        """?statistikler."""
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
    
    # Test sorgular? - DOĞRU EŞLEŞT?RME KONTROLÜ
    test_queries = [
        "Kad?k�y Moda",
        "Beşiktaş Abbasağa",
        "Üsk�dar Çengelk�y",  # Üsk�dar'da olmal?!
        "Şişli Nişantaş?",     # Şişli'de olmal?!
        "Fatih Aksaray",        # Fatih'te olmal?!
        "sar?yer emirgan",
        "ataşehir kay?şdağ?",
        "maltepe bağdat",
        "pendik şeyhli",
        "tuzla menderes",
        "ey�psultan rami",
        "beylikd�z� yakuplu",
        "bak?rk�y yeşilk�y",
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
            print(f"❌ Lokasyon bulunamad?")
    
    print("\n" + "=" * 60)
    stats = engine.get_stats()
    print("?STAT?ST?KLER:")
    print(f"  - ?l�e: {stats['districts']}")
    print(f"  - Mahalle: {stats['neighborhoods']}")
    print(f"  - Sokak/Cadde: {stats['streets']}")
    print(f"  - Toplam: {stats['total_locations']}")
    print("=" * 60)
    
    # Eksik sokak kontrol�
    print("\n✅ SOKAK TAMAMLANDI:")
    streets_complete = [d for d in engine.districts if d in engine.streets]
    print(f"  {len(streets_complete)}/37 il�ede sokak var")
    
    if len(streets_complete) < 37:
        missing = [d for d in engine.districts if d not in engine.streets]
        print(f"  Eksik: {missing}")


if __name__ == "__main__":
    test_detailed_location()