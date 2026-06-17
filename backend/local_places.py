"""
local_places.py - Önceden tanımlı yerler (Geocoder fallback)

Popüler semtler, il merkezleri ve landmark'lar.
Nominatim API'ye gitmeden önce bu tabloya bakılır.
"""

from typing import List, Optional
from storage_db import get_connection, ensure_db

# Başlangıç verisi — popüler yerler (name, display_name, lat, lon, place_type, search_terms)
SEED_PLACES = [
    # İstanbul
    ("Taksim", "Taksim, Beyoğlu, İstanbul, Türkiye", 41.0370, 28.9850, "semt", "taksim meydanı"),
    ("Kadıköy", "Kadıköy, İstanbul, Türkiye", 40.9927, 29.0234, "semt", "kadikoy kadiköy"),
    ("Beşiktaş", "Beşiktaş, İstanbul, Türkiye", 41.0422, 29.0066, "semt", "besiktas beşiktaş"),
    ("Üsküdar", "Üsküdar, İstanbul, Türkiye", 41.0225, 29.0150, "semt", "uskudar üsküdar"),
    ("Sultanahmet", "Sultanahmet, Fatih, İstanbul, Türkiye", 41.0054, 28.9768, "semt", "sultanahmet meydanı"),
    ("Galata Kulesi", "Galata Kulesi, Beyoğlu, İstanbul, Türkiye", 41.0256, 28.9742, "landmark", "galata"),
    ("Moda", "Moda, Kadıköy, İstanbul, Türkiye", 40.9878, 29.0295, "semt", "moda sahil"),
    ("Bebek", "Bebek, Beşiktaş, İstanbul, Türkiye", 41.0772, 29.0433, "semt", "bebek sahil"),
    ("Ortaköy", "Ortaköy, Beşiktaş, İstanbul, Türkiye", 41.0553, 29.0266, "semt", "ortakoy ortaköy"),
    ("Levent", "Levent, Beşiktaş, İstanbul, Türkiye", 41.0818, 29.0108, "semt", "levent"),
    ("Maslak", "Maslak, Sarıyer, İstanbul, Türkiye", 41.1068, 29.0205, "semt", "maslak"),
    ("Maltepe", "Maltepe, İstanbul, Türkiye", 40.9353, 29.1288, "semt", "maltepe"),
    ("Kartal", "Kartal, İstanbul, Türkiye", 40.9084, 29.1811, "semt", "kartal"),
    ("Bakırköy", "Bakırköy, İstanbul, Türkiye", 40.9820, 28.8779, "semt", "bakirkoy bakırköy"),
    ("Fatih", "Fatih, İstanbul, Türkiye", 41.0186, 28.9497, "semt", "fatih"),
    ("Beyoğlu", "Beyoğlu, İstanbul, Türkiye", 41.0311, 28.9744, "semt", "beyoglu beyoğlu"),
    ("Şişli", "Şişli, İstanbul, Türkiye", 41.0602, 28.9877, "semt", "sisli şişli"),
    ("Mecidiyeköy", "Mecidiyeköy, Şişli, İstanbul, Türkiye", 41.0695, 28.9756, "semt", "mecidiyekoy"),
    ("Kozyatağı", "Kozyatağı, Kadıköy, İstanbul, Türkiye", 40.9689, 29.0778, "semt", "kozyatagi"),
    ("Bostancı", "Bostancı, Kadıköy, İstanbul, Türkiye", 40.9650, 29.0783, "semt", "bostanci"),
    # İstanbul resmi ilçeleri
    ("Adalar", "Adalar, İstanbul, Türkiye", 40.8748, 29.1294, "ilce", "adalar princes islands"),
    ("Arnavutköy", "Arnavutköy, İstanbul, Türkiye", 41.1842, 28.7407, "ilce", "arnavutkoy arnavutköy"),
    ("Ataşehir", "Ataşehir, İstanbul, Türkiye", 40.9833, 29.1278, "ilce", "atasehir ataşehir"),
    ("Avcılar", "Avcılar, İstanbul, Türkiye", 40.9792, 28.7214, "ilce", "avcilar avcılar"),
    ("Bağcılar", "Bağcılar, İstanbul, Türkiye", 41.0390, 28.8567, "ilce", "bagcilar bağcılar"),
    ("Bahçelievler", "Bahçelievler, İstanbul, Türkiye", 40.9975, 28.8506, "ilce", "bahcelievler bahçelievler"),
    ("Başakşehir", "Başakşehir, İstanbul, Türkiye", 41.0931, 28.8028, "ilce", "basaksehir başakşehir"),
    ("Bayrampaşa", "Bayrampaşa, İstanbul, Türkiye", 41.0467, 28.9006, "ilce", "bayrampasa bayrampaşa"),
    ("Beykoz", "Beykoz, İstanbul, Türkiye", 41.1239, 29.1083, "ilce", "beykoz"),
    ("Beylikdüzü", "Beylikdüzü, İstanbul, Türkiye", 41.0017, 28.6419, "ilce", "beylikduzu beylikdüzü"),
    ("Büyükçekmece", "Büyükçekmece, İstanbul, Türkiye", 41.0207, 28.5850, "ilce", "buyukcekmece büyükçekmece"),
    ("Çatalca", "Çatalca, İstanbul, Türkiye", 41.1432, 28.4615, "ilce", "catalca çatalca"),
    ("Çekmeköy", "Çekmeköy, İstanbul, Türkiye", 41.0350, 29.1786, "ilce", "cekmekoy çekmeköy"),
    ("Esenler", "Esenler, İstanbul, Türkiye", 41.0435, 28.8760, "ilce", "esenler"),
    ("Esenyurt", "Esenyurt, İstanbul, Türkiye", 41.0343, 28.6801, "ilce", "esenyurt"),
    ("Eyüpsultan", "Eyüpsultan, İstanbul, Türkiye", 41.0478, 28.9339, "ilce", "eyupsultan eyüpsultan eyup eyüp"),
    ("Gaziosmanpaşa", "Gaziosmanpaşa, İstanbul, Türkiye", 41.0575, 28.9157, "ilce", "gaziosmanpasa gaziosmanpaşa"),
    ("Güngören", "Güngören, İstanbul, Türkiye", 41.0220, 28.8721, "ilce", "gungoren güngören"),
    ("Kağıthane", "Kağıthane, İstanbul, Türkiye", 41.0850, 28.9725, "ilce", "kagithane kağıthane"),
    ("Küçükçekmece", "Küçükçekmece, İstanbul, Türkiye", 40.9919, 28.7717, "ilce", "kucukcekmece küçükçekmece"),
    ("Pendik", "Pendik, İstanbul, Türkiye", 40.8794, 29.2581, "ilce", "pendik"),
    ("Sancaktepe", "Sancaktepe, İstanbul, Türkiye", 41.0024, 29.2319, "ilce", "sancaktepe"),
    ("Sarıyer", "Sarıyer, İstanbul, Türkiye", 41.1663, 29.0502, "ilce", "sariyer sarıyer"),
    ("Silivri", "Silivri, İstanbul, Türkiye", 41.0732, 28.2479, "ilce", "silivri"),
    ("Sultanbeyli", "Sultanbeyli, İstanbul, Türkiye", 40.9607, 29.2707, "ilce", "sultanbeyli"),
    ("Sultangazi", "Sultangazi, İstanbul, Türkiye", 41.1065, 28.8684, "ilce", "sultangazi"),
    ("Şile", "Şile, İstanbul, Türkiye", 41.1754, 29.6133, "ilce", "sile şile"),
    ("Tuzla", "Tuzla, İstanbul, Türkiye", 40.8164, 29.3009, "ilce", "tuzla"),
    ("Ümraniye", "Ümraniye, İstanbul, Türkiye", 41.0164, 29.1248, "ilce", "umraniye ümraniye"),
    ("Zeytinburnu", "Zeytinburnu, İstanbul, Türkiye", 40.9940, 28.9047, "ilce", "zeytinburnu"),
    ("Kapalıçarşı", "Kapalıçarşı, Fatih, İstanbul, Türkiye", 41.0106, 28.9680, "landmark", "kapalicarsi grand bazaar"),
    # Ankara
    ("Kızılay", "Kızılay, Çankaya, Ankara, Türkiye", 39.9212, 32.8597, "semt", "kizilay kızılay"),
    ("Çankaya", "Çankaya, Ankara, Türkiye", 39.9212, 32.8628, "semt", "cankaya çankaya"),
    ("Ulus", "Ulus, Altındağ, Ankara, Türkiye", 39.9429, 32.8605, "semt", "ulus"),
    ("Tunalı", "Tunalı Hilmi Caddesi, Çankaya, Ankara, Türkiye", 39.9090, 32.8597, "semt", "tunali"),
    ("Anıtkabir", "Anıtkabir, Çankaya, Ankara, Türkiye", 39.9255, 32.8370, "landmark", "anitkabir"),
    # İzmir
    ("Konak", "Konak, İzmir, Türkiye", 38.4192, 27.1287, "semt", "konak meydanı"),
    ("Alsancak", "Alsancak, Konak, İzmir, Türkiye", 38.4389, 27.1418, "semt", "alsancak"),
    ("Karşıyaka", "Karşıyaka, İzmir, Türkiye", 38.4595, 27.1118, "semt", "karsiyaka karşıyaka"),
    ("Bornova", "Bornova, İzmir, Türkiye", 38.4667, 27.2167, "semt", "bornova"),
    ("Kordon", "Kordon, Alsancak, İzmir, Türkiye", 38.4350, 27.1450, "semt", "kordon"),
    # Antalya
    ("Lara", "Lara, Muratpaşa, Antalya, Türkiye", 36.8747, 30.7633, "semt", "lara plaj"),
    ("Kaleiçi", "Kaleiçi, Muratpaşa, Antalya, Türkiye", 36.8842, 30.7056, "semt", "kaleici"),
    # Bursa
    ("Osmangazi", "Osmangazi, Bursa, Türkiye", 40.1885, 29.0610, "semt", "osmangazi"),
    ("Nilüfer", "Nilüfer, Bursa, Türkiye", 40.2128, 28.9828, "semt", "nilufer"),
    # İl merkezleri (önemli şehirler)
    ("İstanbul", "İstanbul, Türkiye", 41.0082, 28.9784, "il_merkez", "istanbul"),
    ("Ankara", "Ankara, Türkiye", 39.9334, 32.8597, "il_merkez", "ankara"),
    ("İzmir", "İzmir, Türkiye", 38.4192, 27.1287, "il_merkez", "izmir"),
    ("Antalya", "Antalya, Türkiye", 36.8969, 30.7133, "il_merkez", "antalya"),
    ("Bursa", "Bursa, Türkiye", 40.1885, 29.0610, "il_merkez", "bursa"),
    ("Adana", "Adana, Türkiye", 37.0000, 35.3213, "il_merkez", "adana"),
    ("Konya", "Konya, Türkiye", 37.8746, 32.4932, "il_merkez", "konya"),
    ("Gaziantep", "Gaziantep, Türkiye", 37.0662, 37.3833, "il_merkez", "gaziantep"),
    ("Kayseri", "Kayseri, Türkiye", 38.7312, 35.4787, "il_merkez", "kayseri"),
    ("Eskişehir", "Eskişehir, Türkiye", 39.7767, 30.5206, "il_merkez", "eskisehir"),
]


def _ensure_seed_places() -> None:
    """Eksik başlangıç yerlerini local_places tablosuna ekler."""
    ensure_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM local_places WHERE name IS NOT NULL")
    existing_names = {str(row["name"]).strip().casefold() for row in cursor.fetchall()}
    inserted = 0
    for name, display_name, lat, lon, place_type, search_terms in SEED_PLACES:
        name_key = name.strip().casefold()
        if name_key in existing_names:
            continue
        cursor.execute(
            """
            INSERT INTO local_places (name, display_name, lat, lon, place_type, search_terms)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, display_name, lat, lon, place_type, search_terms),
        )
        existing_names.add(name_key)
        inserted += 1
    conn.commit()
    conn.close()
    if inserted > 0:
        print(f"[LocalPlaces] {inserted} eksik seed yer eklendi.")


def lookup(place_name: str) -> Optional[dict]:
    """
    Yer ismine göre local_places tablosunda arama yapar.
    Tam veya kısmi eşleşme (name, search_terms).

    Returns:
        dict: {"lat", "lon", "display_name", "address"} veya None
    """
    _ensure_seed_places()

    if not place_name or len(place_name.strip()) < 2:
        return None

    query = place_name.strip().lower()
    query_key = place_name.strip().casefold()
    conn = get_connection()
    cursor = conn.cursor()

    # Önce tam eşleşme (name)
    cursor.execute("SELECT name, display_name, lat, lon FROM local_places WHERE name IS NOT NULL")
    row = next((item for item in cursor.fetchall() if str(item["name"]).strip().casefold() == query_key), None)

    # Tam eşleşme yoksa search_terms veya name içinde ara
    if not row:
        cursor.execute(
            """
            SELECT name, display_name, lat, lon FROM local_places
            WHERE LOWER(name) LIKE ? OR LOWER(search_terms) LIKE ?
            LIMIT 1
            """,
            (f"%{query}%", f"%{query}%"),
        )
        row = cursor.fetchone()

    conn.close()

    if row:
        return {
            "lat": row["lat"],
            "lon": row["lon"],
            "display_name": row["display_name"],
            "address": "",
        }
    return None


def save_dynamic_place(
    name: str,
    display_name: str,
    lat: float,
    lon: float,
    search_terms: str = ""
) -> None:
    """
    OSM'den gelen dinamik yeri local_places tablosuna cache'ler.
    Aynı ada sahip kayıt varsa tekrar eklemez.
    """
    ensure_db()

    if not name or len(name.strip()) < 2:
        return

    normalized_name = name.strip()
    normalized_display = (display_name or normalized_name).strip()
    normalized_terms = (search_terms or normalized_display).strip().lower()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM local_places WHERE name IS NOT NULL")
    exists = any(
        str(row["name"]).strip().casefold() == normalized_name.casefold()
        for row in cursor.fetchall()
    )

    if exists:
        conn.close()
        return

    cursor.execute(
        """
        INSERT INTO local_places (name, display_name, lat, lon, place_type, search_terms)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (normalized_name, normalized_display, lat, lon, "osm_dynamic", normalized_terms),
    )
    conn.commit()
    conn.close()


def get_dynamic_place_names(limit: int = 500) -> List[str]:
    """
    local_places içindeki dinamik OSM cache adlarını döner.
    """
    ensure_db()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT name
        FROM local_places
        WHERE place_type = 'osm_dynamic'
        ORDER BY id DESC
        LIMIT ?
        """,
        (int(limit),),
    )
    rows = cursor.fetchall()
    conn.close()

    return [row["name"] for row in rows if row["name"]]


def get_all_local_place_names(limit: int = 2000, include_dynamic: bool = True) -> List[str]:
    """
    local_places tablosundaki yer adlarını döner.

    Args:
        limit: Maksimum kayıt sayısı
        include_dynamic: False ise place_type='osm_dynamic' kayıtlarını hariç tutar
    """
    _ensure_seed_places()

    conn = get_connection()
    cursor = conn.cursor()
    sql = """
        SELECT name
        FROM local_places
        WHERE name IS NOT NULL AND TRIM(name) != ''
    """
    if not include_dynamic:
        sql += "\n        AND place_type != 'osm_dynamic'"
    sql += """
        ORDER BY id DESC
        LIMIT ?
    """
    cursor.execute(sql, (int(limit),))
    rows = cursor.fetchall()
    conn.close()
    return [row["name"] for row in rows if row["name"]]
