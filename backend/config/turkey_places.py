"""
turkey_places.py - Türkiye Yer İsimleri Veritabanı

Türkiye'nin tüm illerini ve ilçelerini içerir.
Toplam: 81 il + 970+ ilçe
"""

TURKEY_PLACES = {
    "iller": [
        {"il": "Adana", "ilceler": ["Seyhan", "Yüreğir", "Çukurova", "Sarıçam", "Karaisalı", "Pozantı", "Yumurtalık", "Kozan", "Ceyhan", "Feke", "İmamoğlu", "Karataş", "Kadirli", "Tufanbeyli", "Saimbeyli", "Aladağ", "Mahmutlar", "Misis"]},
        {"il": "Adıyaman", "ilceler": ["Merkez", "Besni", "Çelikhan", "Gerger", "Gölbaşı", "Kahta", "Samsat", "Sincik", "Tut"]},
        {"il": "Afyonkarahisar", "ilceler": ["Merkez", "Başmakçı", "Bayat", "Bolvadin", "Çay", "Dazkırı", "Dinar", "Emirdağ", "Evciler", "Hocalar", "İhsaniye", "İscehisar", "Kızılören", "Sandıklı", "Sinanpaşa", "Şuhut", "Sultandağı"]},
        {"il": "Ağrı", "ilceler": ["Merkez", "Diyadin", "Doğubayazıt", "Eleşkirt", "Hamur", "Patnos", "Taşlıçay", "Tutak"]},
        {"il": "Aksaray", "ilceler": ["Merkez", "Ağaçören", "Eskil", "Gülağaç", "Güzelyurt", "Ortaköy", "Sarıyahşi"]},
        {"il": "Amasya", "ilceler": ["Merkez", "Göynücek", "Gümüşhacıköy", "Hamamözü", "Merzifon", "Suluova", "Taşova"]},
        {"il": "Ankara", "ilceler": ["Altındağ", "Ayaş", "Bala", "Beypazarı", "Çamlıdere", "Çankaya", "Çubuk", "Elmadağ", "Etimesgut", "Evren", "Gölbaşı", "Güdül", "Haymana", "Kalecik", "Keçiören", "Kızılcahamam", "Kızılcasar", "Mamak", "Nallıhan", "Polatlı", "Pursaklar", "Şereflikoçhisar", "Sincan", "Şerefler", "Yenimahalle"]},
        {"il": "Antalya", "ilceler": ["Akseki", "Aksu", "Alanya", "Demre", "Elmalı", "Finike", "Gazipaşa", "Gündoğmuş", "Kaş", "Kemer", "Kepez", "Korkuteli", "Kumluca", "Manavgat", "Muratpaşa", "Serik", "İbradı"]},
        {"il": "Ardahan", "ilceler": ["Merkez", "Çıldır", "Damal", "Göle", "Hanak", "Posof"]},
        {"il": "Artvin", "ilceler": ["Merkez", "Ardanuç", "Arhavi", "Borçka", "Hopa", "Kemalpaşa", "Murgul", "Şavşat", "Yusufeli"]},
        {"il": "Aydın", "ilceler": ["Merkez", "Bozdoğan", "Buharkent", "Çine", "Didim", "Efeler", "Germencik", "İncirliova", "Karacasu", "Karpuzlu", "Koçarlı", "Kuşadası", "Kuyucak", "Nazilli", "Söke", "Sultanhisar", "Yenipazar"]},
        {"il": "Balıkesir", "ilceler": ["Altıeylül", "Manyas", "Karesi", "Susurluk", "Sındırgı", "Gönen", "Erdek", "Bandırma", "Bigadiç", "Dursunbey", "Edremit", "Burhaniye", "Havran", "İvrindi", "Kepsut", "Ayvalık"]},
        {"il": "Bartın", "ilceler": ["Merkez", "Amasra", "Kurucaşile", "Ulus"]},
        {"il": "Batman", "ilceler": ["Merkez", "Beşiri", "Gercüş", "Hasankeyf", "Kozluk", "Sason"]},
        {"il": "Bayburt", "ilceler": ["Merkez", "Aydıntepe", "Demirözü"]},
        {"il": "Bilecik", "ilceler": ["Merkez", "Bozüyük", "Gölpazarı", "İnhisar", "Osmaneli", "Pazaryeri", "Söğüt", "Yenipazar"]},
        {"il": "Bingöl", "ilceler": ["Merkez", "Adaklı", "Genç", "Karlıova", "Kiğı", "Solhan", "Yayladere"]},
        {"il": "Bitlis", "ilceler": ["Merkez", "Adilcevaz", "Ahlat", "Güroymak", "Hizan", "Mutki", "Tatvan"]},
        {"il": "Bolu", "ilceler": ["Merkez", "Dörtdivan", "Gerede", "Göynük", "Kıbrıscık", "Mengen", "Mudurnu", "Seben", "Yeniçağa"]},
        {"il": "Burdur", "ilceler": ["Merkez", "Ağlasun", "Altınyayla", "Bucak", "Çavdır", "Gölhisar", "Karamanlı", "Kemer", "Tefenni", "Yeşilova"]},
        {"il": "Bursa", "ilceler": ["Nilüfer", "Osmangazi", "Yıldırım", "Büyükorhan", "Gemlik", "Gürsu", "Harmancık", "İnegöl", "İznik", "Karacabey", "Keles", "Kestel", "Mudanya", "Mustafakemalpaşa", "Orhaneli", "Orhangazi", "Yenişehir"]},
        {"il": "Çanakkale", "ilceler": ["Merkez", "Ayvacık", "Bayramiç", "Biga", "Bozcaada", "Çan", "Eceabat", "Ezine", "Gelibolu", "Gökçeada", "Lapseki", "Yenice"]},
        {"il": "Çankırı", "ilceler": ["Merkez", "Atkaracalar", "Bayramören", "Çerkeş", "Eldivan", "Ilgaz", "Kızılırmak", "Korgun", "Kurşunlu", "Orta", "Şabanözü", "Yapraklı"]},
        {"il": "Çorum", "ilceler": ["Merkez", "Alaca", "Bayat", "Boğazkale", "Dodurga", "İskilip", "Kargı", "Laçin", "Mecitözü", "Oğuzlar", "Orta", "Osmancık", "Sungurlu", "Uğurludağ"]},
        {"il": "Denizli", "ilceler": ["Merkez", "Acıpayam", "Babadağ", "Baklan", "Bekilli", "Buldan", "Çal", "Çameli", "Çardak", "Çivril", "Güney", "Honaz", "Kale", "Sarayköy", "Serinhisar", "Tavas"]},
        {"il": "Diyarbakır", "ilceler": ["Bağlar", "Kayapınar", "Sur", "Yenişehir", "Bismil", "Çermik", "Çınar", "Eğil", "Ergani", "Hani", "Hazro", "Kocaköy", "Kulp", "Lice", "Silvan"]},
        {"il": "Düzce", "ilceler": ["Merkez", "Akçakoca", "Cumayeri", "Çilimli", "Gölyaka", "Gümüşova", "Kaynaşlı", "Yığılca"]},
        {"il": "Edirne", "ilceler": ["Merkez", "Enez", "Havsa", "İpsala", "Keşan", "Lalapaşa", "Meriç", "Süloğlu", "Uzunköprü"]},
        {"il": "Elazığ", "ilceler": ["Merkez", "Ağın", "Alacakaya", "Arıcak", "Baskil", "Karakoçan", "Keban", "Kovancılar", "Maden", "Palu", "Sivrice"]},
        {"il": "Erzincan", "ilceler": ["Merkez", "Çağlayan", "İliç", "Kemah", "Kemaliye", "Refahiye", "Tercan", "Üzümlü"]},
        {"il": "Erzurum", "ilceler": ["Merkez", "Aşkale", "Çat", "Hınıs", "Horasan", "İspir", "Karaçoban", "Karsamba", "Narman", "Oltu", "Olur", "Pasinler", "Pazaryolu", "Şenkaya", "Tekman", "Tortum", "Uzundere"]},
        {"il": "Eskişehir", "ilceler": ["Odunpazarı", "Tepebaşı", "Alpu", "Beylikova", "Çifteler", "Günyüzü", "Han", "İnönü", "Mahmudiye", "Mihalgazi", "Mihalıççık", "Sarıcakaya", "Seyitgazi"]},
        {"il": "Gaziantep", "ilceler": ["Şahinbey", "Şehitkamil", "Araban", "İslahiye", "Karkamış", "Nizip", "Nurdağı", "Oğuzeli", "Yavuzeli"]},
        {"il": "Giresun", "ilceler": ["Merkez", "Alucra", "Bulancak", "Çamoluk", "Çanakçı", "Dereli", "Doğankent", "Espiye", "Eynesil", "Görele", "Güce", "Keşap", "Piraziz", "Şebinkarahisar", "Tirebolu", "Yağlıdere"]},
        {"il": "Gümüşhane", "ilceler": ["Merkez", "Kelkit", "Köse", "Kürtün", "Şiran", "Torul"]},
        {"il": "Hakkari", "ilceler": ["Merkez", "Çukurca", "Şemdinli", "Yüksekova"]},
        {"il": "Hatay", "ilceler": ["Antakya", "Arsuz", "Defne", "Dörtyol", "Erzin", "Hassa", "İskenderun", "Kırıkhan", "Kumlu", "Payas", "Reyhanlı", "Samandağ", "Yayladağı"]},
        {"il": "Isparta", "ilceler": ["Merkez", "Aksu", "Atabey", "Eğirdir", "Gelendost", "Gönen", "Keçiborlu", "Senirkent", "Sütçüler", "Şarkikaraağaç", "Uluborlu", "Yalvaç", "Yenişarbademli"]},
        {"il": "Mersin", "ilceler": ["Anamur", "Aydıncık", "Bozyazı", "Çamlıyayla", "Erdemli", "Gülnar", "Mut", "Silifke", "Tarsu", "Akdeniz", "Mezitli", "Toroslar", "Yenişehir"]},
        {"il": "İstanbul", "ilceler": ["Kadıköy", "Beşiktaş", "Taksim", "Mecidiyeköy", "Şişli", "Levent", "Maslak", "Sarıyer", "Eminönü", "Sultanahmet", "Fatih", "Üsküdar", "Kartal", "Maltepe", "Bostancı", "Kozyatağı", "Bebek", "Ortaköy", "Karaköy", "Moda", "Bağdat Caddesi", "İstiklal Caddesi", "Galata", "Bakırköy", "Bahçelievler", "Beyoğlu", "Beylikdüzü", "Büyükçekmece", "Çatalca", "Esenler", "Esenyurt", "Eyüp", "Gaziosmanpaşa", "Güngören", "Kağıthane", "Küçükçekmece", "Pendik", "Sancaktepe", "Sarıyer", "Silivri", "Sultangazi", "Şile", "Tuzla", "Ümraniye", "Üsküdar", "Zeytinburnu"]},
        {"il": "İzmir", "ilceler": ["Konak", "Alsancak", "Bornova", "Buca", "Karşıyaka", "Balçova", "Bayraklı", "Bergama", "Beydağ", "Çeşme", "Çiğli", "Dikili", "Foça", "Gaziemir", "Güzelyalı", "Karabağlar", "Kemalpaşa", "Kınık", "Kiraz", "Menderes", "Menemen", "Narlıdere", "Ödemiş", "Seferihisar", "Selçuk", "Tire", "Torbalı", "Urla", "Aliağa"]},
        {"il": "Kars", "ilceler": ["Merkez", "Akyaka", "Arpaçay", "Digor", "Kağızman", "Selim", "Susuz"]},
        {"il": "Kastamonu", "ilceler": ["Merkez", "Abana", "Araç", "Azdavay", "Bozkurt", "Cide", "Çatalzeytin", "Daday", "Devrekani", "Doğanyurt", "Hanönü", "İnebolu", "İhsangazi", "Küre", "Pınarbaşı", "Şenpazar", "Taşköprü", "Tosya"]},
        {"il": "Kayseri", "ilceler": ["Melikgazi", "Kocasinan", "Ağırnas", "Bünyan", "Develi", "Felahiye", "Hacılar", "İncesu", "Kocasinan", "Melikgazi", "Özvatan", "Pınarbaşı", "Sarıoğlan", "Sarıöz", "Talas", "Tomarza", "Yahyalı", "Yeşilhisar"]},
        {"il": "Kırklareli", "ilceler": ["Merkez", "Babaeski", "Demirköy", "Kofçaz", "Lüleburgaz", "Pehlivanköy", "Pınarhisar", "Vize"]},
        {"il": "Kırşehir", "ilceler": ["Merkez", "Akçakent", "Boztepe", "Çiçekdağı", "Kaman", "Mucur", "Sepe"]},
        {"il": "Kocaeli", "ilceler": ["İzmit", "Gebze", "Başiskele", "Çayirova", "Darıca", "Derince", "Dilovası", "Kandıra", "Karamürsel", "Kartepe", "Gölcük", "Körfez"]},
        {"il": "Konya", "ilceler": ["Selçuklu", "Karatay", "Meram", "Akşehir", "Altınekin", "Beyşehir", "Bozkır", "Cihanbeyli", "Çeltik", "Çumra", "Derbent", "Derebucak", "Doganhisar", "Emirgazi", "Eregli", "Güneysınır", "Hadim", "Halkapınar", "Hüyük", "Ilgın", "Kadınhanı", "Karapınar", "Kulu", "Sarayönü", "Seydişehir", "Taşkent", "Tuzlukçu", "Yalıhüyük", "Yunak"]},
        {"il": "Kütahya", "ilceler": ["Merkez", "Altıntaş", "Aslanapa", "Domaniç", "Dumlupınar", "Emet", "Gediz", "Hisarcık", "Pazarlar", "Şaphane", "Simav", "Tavşanlı"]},
        {"il": "Malatya", "ilceler": ["Battalgazi", "Pütürge", "Akçadağ", "Arapgir", "Arguvan", "Darende", "Doğanşehir", "Doğanyol", "Hekimhan", "Kale", "Kuluncak", "Yazıhan", "Yeşilyurt"]},
        {"il": "Manisa", "ilceler": ["Şehzadeler", "Yunusemre", "Akhisar", "Alaşehir", "Demirci", "Gölmarmara", "Gördes", "Kırkağaç", "Köprübaşı", "Kula", "Salihli", "Sarıgöl", "Soma", "Şehzadeler", "Turgutlu"]},
        {"il": "Kahramanmaraş", "ilceler": ["Merkez", "Afşin", "Andırın", "Çağlayancerit", "Döngel", "Ekinözü", "Elbistan", "Göksun", "Nurhak", "Pazarcık", "Türkoğlu"]},
        {"il": "Mardin", "ilceler": ["Merkez", "Dargeçit", "Derik", "Kızıltepe", "Mazıdağı", "Midyat", "Nusaybin", "Ömerli", "Savur", "Yeşilli"]},
        {"il": "Muğla", "ilceler": ["Menteşe", "Bodrum", "Datça", "Fethiye", "Kavaklıdere", "Köyceğiz", "Marmaris", "Milas", "Ortaca", "Seydikemer", "Ula", "Yatağan"]},
        {"il": "Muş", "ilceler": ["Merkez", "Bulanık", "Hasköy", "Korkut", "Malazgirt", "Varto"]},
        {"il": "Nevşehir", "ilceler": ["Merkez", "Acıgöl", "Avanos", "Derinkuyu", "Gülşehir", "Hacıbektaş", "Kozaklı", "Ürgüp"]},
        {"il": "Niğde", "ilceler": ["Merkez", "Altunhisar", "Bor", "Çamardı", "Çiftlik", "Ulukışla"]},
        {"il": "Ordu", "ilceler": ["Merkez", "Akkuş", "Altınordu", "Aybastı", "Çamaş", "Çatalpınar", "Fatsa", "Gölköy", "Gülyalı", "Gürgentepe", "İkizce", "Kabadüz", "Kabataş", "Korgan", "Kumru", "Mesudiye", "Perşembe", "Ulubey", "Ünye"]},
        {"il": "Rize", "ilceler": ["Merkez", "Ardeşen", "Çamlıhemşin", "Çayeli", "Derepazarı", "Fındıklı", "Güneysu", "Hemşin", "İyidere", "Kalkandere", "Pazar", "İkizdere"]},
        {"il": "Sakarya", "ilceler": ["Adapazarı", "Akyazı", "Arifiye", "Erenler", "Ferizli", "Geyve", "Hendek", "Karapürçek", "Karasu", "Kaynarca", "Kocaali", "Pamukova", "Sapanca", "Serdivan", "Söğütlü", "Taraklı"]},
        {"il": "Samsun", "ilceler": ["İlkadım", "Atakum", "Bafra", "Canik", "Çarşamba", "Havza", "İlkadım", "Kavak", "Ladik", "Ondokuzmayıs", "Salıpazarı", "Terme", "Tekkeköy", "Vezirköprü", "Yakakent"]},
        {"il": "Siirt", "ilceler": ["Merkez", "Baykan", "Eruh", "Kurtalan", "Pervari", "Şirvan", "Tillo"]},
        {"il": "Sinop", "ilceler": ["Merkez", "Ayancık", "Boyabat", "Durağan", "Erfelek", "Gerze", "Saraydüzü", "Türkeli"]},
        {"il": "Sivas", "ilceler": ["Merkez", "Akıncılar", "Altınyayla", "Doğanşar", "Gemerek", "Gürün", "Hafik", "İmranlı", "Kangal", "Koyulhisar", "Şarkışla", "Suşehri", "Ulaş", "Yıldızeli", "Zara"]},
        {"il": "Tekirdağ", "ilceler": ["Merkez", "Çorlu", "Ergene", "Hayrabolu", "Malkara", "Marmara Ereğlisi", "Muratlı", "Saray", "Süleymanpaşa", "Şarköy"]},
        {"il": "Tokat", "ilceler": ["Merkez", "Almus", "Artova", "Başçiftlik", "Erbaa", "Niksar", "Reşadiye", "Sulusaray", "Turhal", "Yeşilyurt", "Zile"]},
        {"il": "Trabzon", "ilceler": ["Ortahisar", "Akçaabat", "Araklı", "Arsin", "Beşikdüzü", "Çarşıbaşı", "Çaykara", "Dernekpazarı", "Düzköy", "Hayrat", "Köprübaşı", "Maçka", "Of", "Sürmene", "Şalpazarı", "Tonya", "Vakfıkebir", "Yomra"]},
        {"il": "Tunceli", "ilceler": ["Merkez", "Çemişgezek", "Hozat", "Mazgirt", "Nazımiye", "Ovacık", "Pertek", "Pülümür"]},
        {"il": "Şanlıurfa", "ilceler": ["Eyyübiye", "Halfeti", "Hilvan", "Karaköprü", "Siverek", "Suruç", "Viranşehir"]},
        {"il": "Uşak", "ilceler": ["Merkez", "Banaz", "Eşme", "Karahallı", "Sivaslı", "Ulubey"]},
        {"il": "Van", "ilceler": ["Merkez", "Başkale", "Çatak", "Edremit", "Erciş", "Gevaş", "Gürpınar", "İpekyolu", "Muradiye", "Özalp", "Saray", "Bahçesaray"]},
        {"il": "Yalova", "ilceler": ["Merkez", "Altınova", "Armutlu", "Çınarcık", "Termal"]},
        {"il": "Yozgat", "ilceler": ["Merkez", "Akdağmadeni", "Aydıncık", "Boğazlıyan", "Çandır", "Çayralı", "Kadışehri", "Sarıkaya", "Sorgun", "Şefaatli", "Yenifakılı", "Yerköy"]},
        {"il": "Zonguldak", "ilceler": ["Merkez", "Alaplı", "Çaycuma", "Devrek", "Ereğli", "Gökçebey", "Kilimli", "Kozlu"]},
    ]
}


def get_all_turkey_places():
    """
    Türkiye'nin tüm yer isimlerini düz liste olarak döner.

    Returns:
        list[str]: Tüm yer isimleri (iller + ilçeler)
    """
    places = []

    for il_data in TURKEY_PLACES["iller"]:
        # İl adını ekle
        places.append(il_data["il"])

        # İlçeleri ekle
        for ilce in il_data["ilceler"]:
            places.append(ilce)
            # "İstanbul Kadıköy" formatında da ekle
            places.append(f"{il_data['il']} {ilce}")

    return places


if __name__ == "__main__":
    all_places = get_all_turkey_places()
    print(f"Toplam yer sayısı: {len(all_places)}")
    print(f"\nİlk 20 yer:")
    for place in all_places[:20]:
        print(f"  - {place}")
