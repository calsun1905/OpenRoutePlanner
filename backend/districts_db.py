"""
districts_db.py - Turkiye Ilce Veritabani

Turkiye'deki tum ilceleri iceren veritabani.
Hizli arama icin SQLite kullanir.
"""

import sqlite3
import os

# Veritabani yolu
DB_PATH = os.path.join(os.path.dirname(__file__), "cache", "districts_turkey.db")

# Turkiye illeri ve ilceleri
TURKEY_DISTRICTS = {
    "Adana": ["Aladag", "Ceyhan", "Cukurova", "Feke", "Imamoglu", "Karaisali", "Karatas", "Kozan", "Pozanti", "Saimbeyli", "Saricam", "Seyhan", "Tufanbeyli", "Yumurtalik", "Yuregir"],
    "Adiyaman": ["Besni", "Celikhan", "Gerger", "Golbasi", "Kahi", "Kahta", "Samsat", "Sincik", "Tut", "Adiyaman Merkez"],
    "Afyonkarahisar": ["Afyon Merkez", "Basmakcik", "Bayat", "Bolvadin", "Cay", "Cobanlar", "Dazkiri", "Dinar", "Emirdag", "Evciler", "Hocalar", "Ihsaniye", "Iscehisar", "Kiziloren", "Sandikli", "Sinanpasa", "Sultandagi", "Suhut"],
    "Agri": ["Agri Merkez", "Dogubayazit", "Diyadin", "Eleşkirt", "Hamur", "Patnos", "Taslicay", "Tutak"],
    "Aksaray": ["Aksaray Merkez", "Agacoren", "Eskil", "Guzelyurt", "Gulagac", "Nazilli", "Sariyahsi", "Sultanhani"],
    "Amasya": ["Amasya Merkez", "Gumushacikoy", "Goyuncak", "Hamamozu", "Merzifon", "Suluova", "Taskopru", "Tasova"],
    "Ankara": ["Altindag", "Ayaş", "Bala", "Beypazari", "Camlidere", "Cankaya", "Cubuk", "Elmadağ", "Etimesgut", "Evren", "Golbasi", "Gudul", "Haymana", "Kalecik", "Keçioren", "Kizilcahamam", "Mamak", "Nallihan", "Polatli", "Pursaklar", "Sincan", "Sereflikochisar", "Yenimahalle"],
    "Antalya": ["Akseki", "Alanya", "Demre", "Elmali", "Finike", "Gazipasa", "Gundogmus", "Ibradi", "Kale", "Kaş", "Kemer", "Kepez", "Korkuteli", "Kumluca", "Manavgat", "Muratpasa", "Serik", "Antalya Merkez"],
    "Ardahan": ["Ardahan Merkez", "Cildir", "Damal", "Gole", "Hanak", "Posof"],
    "Artvin": ["Ardanuç", "Arhavi", "Borcka", "Catalpinar", "Hopa", "Kemalpasa", "Murgul", "Savsat", "Şavşat", "Yusufeli", "Artvin Merkez"],
    "Aydin": ["Bozdogan", "Buharkent", "Cine", "Didim", "Efeler", "Germencik", "Incirliova", "Karacasu", "Karpuzlu", "Koçarli", "Kusadasi", "Kuyucak", "Nazilli", "Soke", "Sultanhisar", "Yenipazar", "Aydin Merkez"],
    "Balikesir": ["Altieylul", "Ayvalik", "Balya", "Bandirma", "Bigadiç", "Burhaniye", "Dursunbey", "Edremit", "Erdek", "Gomeç", "Gonen", "Havran", "Ivrindi", "Karesi", "Kepsut", "Manyas", "Marmara", "Savaştepe", "Sindirgi", "Susurluk", "Balikesir Merkez"],
    "Bartin": ["Amasra", "Bartin Merkez", "Kurucaşile", "Ulus"],
    "Batman": ["Batman Merkez", "Besiri", "Gercus", "Kozluk", "Sason", "Hasankeyf"],
    "Bayburt": ["Aydintespe", "Bayburt Merkez", "Demirözü"],
    "Bilecik": ["Bilecik Merkez", "Bozuyuk", "Golpazari", "Inhisar", "Osmaneli", "Pazaryeri", "Sogut", "Yenipazar"],
    "Bingol": ["Bingol Merkez", "Adakli", "Genç", "Karliova", "Kigi", "Solhan", "Yayladere", "Yedisu"],
    "Bitlis": ["Bitlis Merkez", "Adilcevaz", "Ahlat", "Guroymak", "Hizan", "Mutki", "Tatvan"],
    "Bolu": ["Bolu Merkez", "Dortdivan", "Gerede", "Goynuk", "Kibriscik", "Mengen", "Mudurnu", "Seben", "Yenicaga"],
    "Burdur": ["Burdur Merkez", "Ağlasun", "Bucak", "Cavdir", "Golhisar", "Karamanli", "Kemer", "Tefenni", "Yesilova"],
    "Bursa": ["Bursa Merkez", "Büyükorhan", "Gemlik", "Gursu", "Harmancik", "Inegol", "Iznik", "Karacabey", "Keles", "Kestel", "Mudanya", "Mustafakemalpasa", "Nilufer", "Orhangazi", "Orhaneli", "Yenisehir", "Yildirim"],
    "Canakkale": ["Ayvacik", "Bayramic", "Biga", "Bozcaada", "Canakkale Merkez", "Can", "Eceabat", "Ezine", "Gelibolu", "Gokceada", "Lapseki", "Yenice"],
    "Canakiri": ["Canakiri Merkez", "Çerkkez", "Elmali", "Ilgaz", "Kizilirmak", "Korgun", "Osmancik", "Yaprakli"],
    "Corum": ["Alaca", "Bayat", "Boğazkale", "Corum Merkez", "Dodurga", "Iskilip", "Kargi", "Laçin", "Mecitözü", "Oğuzlar", "Osmancik", "Sungurlu", "Uğurludağ"],
    "Denizli": ["Acipayam", "Babadağ", "Bekilli", "Buldan", "Cal", "Çameli", "Çardak", "Çivril", "Denizli Merkez", "Goncali", "Honaz", "Kale", "Saraykoy", "Serinhisar", "Tavas"],
    "Diyarbakir": ["Baglar", "Bismil", "Çinar", "Çermik", "Dicle", "Diyarbakir Merkez", "Eğil", "Ergani", "Hani", "Hazro", "Kocakoy", "Kulp", "Lice", "Silvan", "Sur", "Yenişehir"],
    "Duzce": ["Duzce Merkez", "Akçakoca", "Cumayeri", "Cilimli", "Golyaka", "Gumusova", "Kaynasli", "Yigilca"],
    "Edirne": ["Edirne Merkez", "Enez", "Havsa", "Ipsala", "Keşan", "Lalapasa", "Meriç", "Suloglu", "Uzunkopru"],
    "Elazig": ["Agin", "Alacakaya", "Arıcak", "Baskil", "Elazig Merkez", "Karakocan", "Keban", "Kovancilar", "Maden", "Palu", "Sivrice"],
    "Erzincan": ["Çağlayan", "Erzincan Merkez", "Ilica", "Kemah", "Kemaliye", "Refahiye", "Tercan", "Uzunlu", "Yaylabaşı"],
    "Erzurum": ["Askale", "Cat", "Erzurum Merkez", "Hinis", "Horasan", "Ispir", "Karaçoban", "Karsiyaka", "Narman", "Oltu", "Olur", "Pazaryolu", "Şenkaya", "Tekman", "Tortum", "Uzundere"],
    "Eskisehir": ["Alpu", "Beylikova", "Çifteler", "Eskisehir Merkez", "Günyüzü", "Han", "Inonu", "Mahmudiye", "Mihalgazi", "Mihaliççik", "Sivrihisar"],
    "Gaziantep": ["Araban", "Gaziantep Merkez", "Islahiye", "Karkamis", "Nizip", "Nurdagi", "Oguzeli", "Şahinbey", "Şehitkamil", "Yavuzeli"],
    "Giresun": ["Alucra", "Bulancak", "Çamoluk", "Çanakci", "Dereli", "Dogankent", "Espinoy", "Giresun Merkez", "Gorele", "Guce", "Kesap", "Piraziz", "Şebinkarahisar", "Tirebolu", "Yaglidere"],
    "Gumushane": ["Gumushane Merkez", "Kelkit", "Kose", "Kurtun", "Şiran", "Torul"],
    "Hakkari": ["Cukurca", "Hakkari Merkez", "Semdinli", "Şemdinli", "Yuksekova"],
    "Hatay": ["Altinozu", "Arsuz", "Defne", "Dortyol", "Erzin", "Hassa", "Hatay Merkez", "Kirikhan", "Kumlu", "Payas", "Reyhanli", "Samandag", "Yayladagi"],
    "Isparta": ["Atabey", "Egridir", "Gelendost", "Isparta Merkez", "Keçiborlu", "Senirkent", "Sütçuler", "Şarkikaraağaç", "Uluborlu", "Yalvaç", "Yenisarbademli"],
    "Mersin": ["Anamur", "Aydincik", "Bozyazi", "Çamliyayla", "Erdemli", "Gulnar", "Mersin Merkez", "Mut", "Silifke", "Tarsus"],
    "Istanbul": ["Adalar", "Arnavutkoy", "Atasehir", "Avcilar", "Bagcilar", "Bahcelievler", "Bakirkoy", "Basaksehir", "Bayrampasa", "Besiktas", "Beykoz", "Beylikduzu", "Beyoglu", "Buyukcekmece", "Catalca", "Cekmekoy", "Esenler", "Esenyurt", "Eyupsultan", "Fatih", "Gaziosmanpasa", "Gungoren", "Kadikoy", "Kagithane", "Kartal", "Kucukcekmece", "Maltepe", "Pendik", "Sancaktepe", "Sariyer", "Silivri", "Sultanbeyli", "Sultangazi", "Sile", "Sisli", "Tuzla", "Umraniye", "Uskudar", "Zeytinburnu"],
    "Izmir": ["Aliağa", "Balçova", "Bayindir", "Bayrakli", "Bergama", "Beydağ", "Bornova", "Buca", "Çeşme", "Çiğli", "Dikili", "Foça", "Gaziemir", "Guzelbahce", "Izmir Merkez", "Karlisiyaka", "Kemalpasa", "Kınık", "Kiraz", "Konak", "Menderes", "Menemen", "Narlidere", "Odemiş", "Seferihisar", "Selçuk", "Tire", "Torbali", "Urla"],
    "Kahramanmaras": ["Afşin", "Andirin", "Caglayancerit", "Dulkadiroğlu", "Ekinözü", "Elbistan", "Goksun", "Kahramanmaras Merkez", "Nurhak", "Pazarcik", "Turkoğlu"],
    "Karabuk": ["Eflani", "Eskipazar", "Karabuk Merkez", "Ovacik", "Safranbolu", "Yenice"],
    "Karaman": ["Ayranci", "Basyayla", "Ermenek", "Karaman Merkez", "Kazimkarabekir"],
    "Kars": ["Akyaka", "Arpaçay", "Digor", "Kagizman", "Kars Merkez", "Karakose", "Selim", "Susuz"],
    "Kastamonu": ["Abana", "Araç", "Azdavay", "Bozkurt", "Cide", "Catalzeytin", "Daday", "Devrekani", "Doğanyurt", "Ihsangazi", "Inebolu", "Kastamonu Merkez", "Küre", "Pinarbasi", "Seydiler", "Taskopru", "Tosya"],
    "Kayseri": ["Bunyan", "Develi", "Felahiye", "Hacilar", "Incesu", "Kocasinan", "Melikgazi", "Ozel Idaresi", "Pinarbasi", "Sarioglan", "Sarioglu", "Talas", "Tomarza", "Yahyali", "Yesilhisar", "Kayseri Merkez"],
    "Kirikkale": ["Bahsili", "Baliseyh", "Celebi", "Delice", "Karakeci", "Keskin", "Kirikkale Merkez", "Sulakyurt", "Yahsihan"],
    "Kirklareli": ["Babaeski", "Demirkoy", "Kırklareli Merkez", "Kofçaz", "Luleburgaz", "Pehlivankoy", "Pinarhisar", "Vize"],
    "Kirsehir": ["Akçakent", "Akpinar", "Boztepe", "Cicekdaği", "Kaman", "Kirsehir Merkez", "Mucur", "Sulama"],
    "Kocaeli": ["Bahcecik", "Darica", "Derince", "Dilovasi", "Gebze", "Golcuk", "Izmit", "Kandıra", "Karamursel", "Kartepe", "Korfez"],
    "Konya": ["Ahirli", "Akoren", "Aksehir", "Altinekin", "Beysehir", "Bozkir", "Cihanbeyli", "Cumra", "Derbent", "Doganhisar", "Emirgazi", "Eregli", "Güneysinir", "Hadim", "Halkapinar", "Hüyük", "Ilgın", "Kadinhani", "Karapinar", "Karatay", "Kulu", "Meram", "Sarayonu", "Selçuklu", "Seydişehir", "Taskent", "Tuzlukcu", "Yalıhüyük", "Yunak"],
    "Kutahya": ["Altıntas", "Aslanapa", "Domaniç", "Dumlupinar", "Emet", "Gediz", "Hisarcik", "Kutahya Merkez", "Pazarlar", "Şaphane", "Simav", "Tavsanli"],
    "Malatya": ["Akçadag", "Arapgir", "Arguvan", "Darende", "Dogansehir", "Doğanyol", "Hekimhan", "Kale", "Kuluncak", "Malatya Merkez", "Pütürge", "Yazihan", "Yesilyurt"],
    "Manisa": ["Akhisar", "Ahmetli", "Demirci", "Golmarmara", "Gordes", "Kirkağaç", "Kocaoba (Koprubasi)", "Kula", "Manisa Merkez", "Salihli", "Sarıgol", "Soma", "Turgutlu", "Şehzadeler"],
    "Mardin": ["Dargecit", "Derik", "Kiziltepe", "Mardin Merkez", "Mazidagi", "Midyat", "Nusaybin", "Omerli", "Savur", "Yesilli"],
    "Mersin": ["Anamur", "Aydincik", "Bozyazi", "Çamliyayla", "Erdemli", "Gulnar", "Mersin Merkez", "Mut", "Silifke", "Tarsus"],
    "Mugla": ["Bodrum", "Dalaman", "Datca", "Fethiye", "Kavaklidere", "Koycegiz", "Marmaris", "Mentes", "Milas", "Mugla Merkez", "Ortaca", "Ula", "Yatagan"],
    "Mus": ["Bulanik", "Hasköy", "Korkut", "Malazgirt", "Mus Merkez", "Varto"],
    "Nevsehir": ["Acigol", "Avanos", "Derinkuyu", "Gulsehir", "Hacibektas", "Kozakli", "Nevsehir Merkez", "Urgup"],
    "Nigde": ["Altunhisar", "Bor", "Camardi", "Ciftlik", "Kozakli", "Nigde Merkez", "Ulukisla"],
    "Ordu": ["Akkuş", "Altinordu", "Aybasti", "Çamas", "Fatsa", "Golbasi", "Gulyali", "Gurgentepe", "Ikizce", "Kabaduz", "Kabatas", "Korgan", "Kumru", "Mesudiye", "Ordu Merkez", "Persembe", "Ulubey", "Unye"],
    "Osmaniye": ["Bahce", "Duzici", "Hasanbeyli", "Kadirli", "Osmaniye Merkez", "Sumbas", "Toprakkale"],
    "Rize": ["Ardesen", "Cayeli", "Derepazari", "Findikli", "Guneysu", "Hemsin", "Ikizdere", "Kalkandere", "Pazar", "Rize Merkez"],
    "Sakarya": ["Adapazari", "Akyazi", "Arifiye", "Erenler", "Ferizli", "Geyve", "Hendek", "Karapürçek", "Karasu", "Kaynarca", "Kocaali", "Pamukova", "Sakarya Merkez", "Sapanca", "Serdivan", "Söğütlü", "Tarakli"],
    "Samsun": ["Alaçam", "Asarcik", "Atakum", "Ayvacik", "Bafra", "Canik", "Çarşamba", "Havza", "Ilkadim", "Kavak", "Ladik", "Ondokuzmayis", "Salipazari", "Samsun Merkez", "Tekkekoy", "Terme", "Vezirkopru", "Yakakent"],
    "Sanliurfa": ["Akcakale", "Birecik", "Bozova", "Ceylanpinar", "Eyyubiye", "Halfeti", "Haliliye", "Hilvan", "Karakopru", "Siverek", "Suruç", "Viranşehir"],
    "Siirt": ["Baykan", "Eruh", "Kurtalan", "Pervari", "Siirt Merkez", "Sirvan", "Tillo"],
    "Sinop": ["Ayancik", "Boyabat", "Dikmen", "Durağan", "Erfelek", "Gerze", "Sinop Merkez", "Turhal"],
    "Sivas": ["Akincilar", "Altinyayla", "Divrigi", "Dogansar", "Gemerek", "Gurun", "Hafik", "Imranli", "Kangal", "Koyulhisar", "Sivas Merkez", "Suşehri", "Şarkisla", "Yildizeli", "Zara"],
    "Tekirdag": ["Çerkezkoy", "Çorlu", "Ergene", "Hayrabolu", "Kapakli", "Malkara", "Marmara Ereğlisi", "Muratli", "Saray", "Suloglu", "Tekirdag Merkez"],
    "Tokat": ["Almus", "Artova", "Basma", "Erbaa", "Niksar", "Pazar", "Reşadiye", "Sulusaray", "Tokat Merkez", "Turhal", "Yeşilyurt", "Zile"],
    "Trabzon": ["Akcaabat", "Arsin", "Besikduzu", "Carşibaba", "Dernekpazari", "Duzkoy", "Hayrat", "Koprubasi", "Macka", "Of", "Sürmene", "Salpazari", "Tonya", "Trabzon Merkez", "Vakfikebir", "Yomra"],
    "Tunceli": ["Çemişgezek", "Hozat", "Mazgirt", "Nazimiye", "Ovacik", "Pertek", "Pulumur", "Tunceli Merkez"],
    "Sanliurfa": ["Akcakale", "Birecik", "Bozova", "Ceylanpinar", "Eyyubiye", "Halfeti", "Haliliye", "Hilvan", "Karakopru", "Siverek", "Suruç", "Viranşehir"],
    "Usak": ["Banaz", "Eski Usak", "Karahalli", "Sivasli", "Ulubey", "Usak Merkez"],
    "Van": ["Bahcesaray", "Baskale", "Caldiran", "Catak", "Edremit", "Erciş", "Gevaş", "Gürpinar", "Ipekyolu", "Muradiye", "Özalp", "Özdemiş", "Saray", "Tuşba", "Van Merkez"],
    "Yalova": ["Altinova", "Armutlu", "Cinarcik", "Termal", "Yalova Merkez"],
    "Yozgat": ["Akdağmadeni", "Aydıncık", "Bogazliyan", "Çandır", "Çayiral", "Çekerek", "Kadışehri", "Karahisar", "Keskin", "Sarıkaya", "Sorgun", "Sefaatli", "Yeni Saraykent", "Yerkoy", "Yozgat Merkez"],
    "Zonguldak": ["Alapli", "Çaycuma", "Devrek", "Ereğli", "Gokcebey", "Kilimli", "Kozlu", "Zonguldak Merkez"]
}


def create_database():
    """Veritabanini olusturur ve ilceleri ekler."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tablo olustur
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS districts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            province TEXT,
            district TEXT,
            full_name TEXT,
            search_key TEXT
        )
    """)

    # Index olustur (hizli arama icin)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_district ON districts(district)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_province ON districts(province)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_full_name ON districts(full_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_key ON districts(search_key)")

    # Ilceleri ekle
    for province, districts in TURKEY_DISTRICTS.items():
        for district in districts:
            full_name = f"{district}, {province}"
            search_key = f"{province.lower()} {district.lower()}"

            cursor.execute("""
                INSERT OR IGNORE INTO districts (province, district, full_name, search_key)
                VALUES (?, ?, ?, ?)
            """, (province, district, full_name, search_key))

    conn.commit()
    conn.close()

    print(f"Veritabani olusturuldu: {DB_PATH}")


def search_districts(query: str, limit: int = 10) -> list:
    """Ilce arar.

    Args:
        query: Arama sorgusu (ornek: "Kadikoy", "Istanbul", "Kadikoy Istanbul")
        limit: Maksimum sonuc sayisi

    Returns:
        list: [{"province": "...", "district": "...", "full_name": "..."}, ...]
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query_lower = f"%{query.lower()}%"

    cursor.execute("""
        SELECT province, district, full_name
        FROM districts
        WHERE search_key LIKE ?
        ORDER BY
            CASE WHEN district LIKE ? THEN 1 ELSE 2 END,
            district
        LIMIT ?
    """, (query_lower, f"{query_lower}%", limit))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return results


def get_all_provinces() -> list:
    """Tum illeri döner."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT province FROM districts ORDER BY province")
    results = [row[0] for row in cursor.fetchall()]

    conn.close()
    return results


def get_districts_by_province(province: str) -> list:
    """Bir ilin tum ilcelerini döner."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT district FROM districts
        WHERE province = ?
        ORDER BY district
    """, (province,))

    results = [row[0] for row in cursor.fetchall()]
    conn.close()
    return results


def print_stats():
    """Veritabani istatistiklerini yazdirir."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Toplam ilce sayisi
    cursor.execute("SELECT COUNT(*) FROM districts")
    total = cursor.fetchone()[0]

    # Il sayisi
    cursor.execute("SELECT COUNT(DISTINCT province) FROM districts")
    provinces = cursor.fetchone()[0]

    conn.close()

    print(f"Toplam il: {provinces}")
    print(f"Toplam ilce: {total}")
    print(f"Veritabani: {DB_PATH}")


if __name__ == "__main__":
    # Ilk calistirmada veritabanini olustur
    create_database()
    print_stats()

    # Test aramalari
    print("\n--- Arama Testleri ---")
    queries = ["Kadikoy", "Istanbul", "Ankara", "Izmir", "Bursa"]

    for q in queries:
        results = search_districts(q)
        print(f"\n'{q}' araması ({len(results)} sonuc):")
        for r in results[:3]:
            print(f"  - {r['full_name']}")
