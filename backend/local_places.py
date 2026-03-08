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


def _seed_if_empty() -> None:
    """local_places tablosu boşsa başlangıç verilerini ekler."""
    ensure_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM local_places")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    for name, display_name, lat, lon, place_type, search_terms in SEED_PLACES:
        cursor.execute(
            """
            INSERT INTO local_places (name, display_name, lat, lon, place_type, search_terms)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, display_name, lat, lon, place_type, search_terms),
        )
    conn.commit()
    conn.close()
    print(f"[LocalPlaces] {len(SEED_PLACES)} yer eklendi.")


def lookup(place_name: str) -> Optional[dict]:
    """
    Yer ismine göre local_places tablosunda arama yapar.
    Tam veya kısmi eşleşme (name, search_terms).

    Returns:
        dict: {"lat", "lon", "display_name", "address"} veya None
    """
    _seed_if_empty()

    if not place_name or len(place_name.strip()) < 2:
        return None

    query = place_name.strip().lower()
    conn = get_connection()
    cursor = conn.cursor()

    # Önce tam eşleşme (name)
    cursor.execute(
        "SELECT name, display_name, lat, lon FROM local_places WHERE LOWER(name) = ? LIMIT 1",
        (query,),
    )
    row = cursor.fetchone()

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
    cursor.execute(
        "SELECT id FROM local_places WHERE LOWER(name) = ? LIMIT 1",
        (normalized_name.lower(),),
    )
    exists = cursor.fetchone()

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
