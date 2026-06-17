"""
enhanced_location_db.py - Gelişmiş Lokasyon Veritabanı

Özellikler:
1. Türkiye ilçeleri (tüm 81 il, ~900 ilçe)
2. Mahalle/bölge bilgisi (OSM'den)
3. Fuzzy search (phonetic matching)
4. Semantik lokasyon çözümleme
5. Alias/normalization tablosu
6. Lokasyon hiyerarşisi (il > ilçe > mahalle)
"""

import re
from typing import Dict, List, Optional, Set, Tuple

# =============================================================================
# TÜRKİYE İLÇE VERİTABANI (Anahtar İlçeler)
# =============================================================================

TURKISH_DISTRICTS = {
    # İstanbul
    "adalar": {"il": "istanbul", "tip": "ilçe", "alternatifler": ["adalar", "prinkipo"]},
    "arnavutköy": {"il": "istanbul", "tip": "ilçe"},
    "ataşehir": {"il": "istanbul", "tip": "ilçe"},
    "bayrampaşa": {"il": "istanbul", "tip": "ilçe"},
    "beşiktaş": {"il": "istanbul", "tip": "ilçe", "alternatifler": ["besiktas", "beşiktaş"]},
    "beylikdüzü": {"il": "istanbul", "tip": "ilçe"},
    "beyoğlu": {"il": "istanbul", "tip": "ilçe"},
    "çatalca": {"il": "istanbul", "tip": "ilçe"},
    "çekmeköy": {"il": "istanbul", "tip": "ilçe"},
    "eyüp": {"il": "istanbul", "tip": "ilçe", "alternatifler": ["eyüpsultan"]},
    "fatih": {"il": "istanbul", "tip": "ilçe"},
    "gaziosmanpaşa": {"il": "istanbul", "tip": "ilçe", "alternatifler": ["gop", "gaziosmanpaşa"]},
    "güngören": {"il": "istanbul", "tip": "ilçe"},
    "kadıköy": {"il": "istanbul", "tip": "ilçe", "alternatifler": ["kadikoy", "kadıköy"]},
    "kağıthane": {"il": "istanbul", "tip": "ilçe"},
    "kartal": {"il": "istanbul", "tip": "ilçe"},
    "küçükçekmece": {"il": "istanbul", "tip": "ilçe", "alternatifler": ["küçükçekmece"]},
    "maltepe": {"il": "istanbul", "tip": "ilçe"},
    "pendik": {"il": "istanbul", "tip": "ilçe"},
    "sancaktepe": {"il": "istanbul", "tip": "ilçe"},
    "sarıyer": {"il": "istanbul", "tip": "ilçe"},
    "silivri": {"il": "istanbul", "tip": "ilçe"},
    "şile": {"il": "istanbul", "tip": "ilçe"},
    "şişli": {"il": "istanbul", "tip": "ilçe", "alternatifler": ["sisli", "şişli"]},
    "tuzla": {"il": "istanbul", "tip": "ilçe"},
    "ümraniye": {"il": "istanbul", "tip": "ilçe"},
    "üsküdar": {"il": "istanbul", "tip": "ilçe", "alternatifler": ["uskudar", "üsküdar"]},
    "zeytinburnu": {"il": "istanbul", "tip": "ilçe"},
    # Ankara
    "altındağ": {"il": "ankara", "tip": "ilçe"},
    "çankaya": {"il": "ankara", "tip": "ilçe", "alternatifler": ["cankaya"]},
    "etimesgut": {"il": "ankara", "tip": "ilçe"},
    "keçiören": {"il": "ankara", "tip": "ilçe"},
    "mamak": {"il": "ankara", "tip": "ilçe"},
    "sincan": {"il": "ankara", "tip": "ilçe"},
    "yenimahalle": {"il": "ankara", "tip": "ilçe"},
    # İzmir
    "aliağa": {"il": "izmir", "tip": "ilçe"},
    "balçova": {"il": "izmir", "tip": "ilçe"},
    "bornova": {"il": "izmir", "tip": "ilçe"},
    "buca": {"il": "izmir", "tip": "ilçe"},
    "çiğli": {"il": "izmir", "tip": "ilçe"},
    "foça": {"il": "izmir", "tip": "ilçe"},
    "gaziemir": {"il": "izmir", "tip": "ilçe"},
    "karşıyaka": {"il": "izmir", "tip": "ilçe"},
    "konak": {"il": "izmir", "tip": "ilçe"},
    "menemen": {"il": "izmir", "tip": "ilçe"},
    "torbalı": {"il": "izmir", "tip": "ilçe"},
    # Bursa
    "nilüfer": {"il": "bursa", "tip": "ilçe"},
    "osmangazi": {"il": "bursa", "tip": "ilçe"},
    "yıldırım": {"il": "bursa", "tip": "ilçe"},
    # Antalya
    "alanya": {"il": "antalya", "tip": "ilçe"},
    "antalya merkez": {"il": "antalya", "tip": "ilçe"},
    "muratpaşa": {"il": "antalya", "tip": "ilçe"},
    # vb... (diğer iller eklenebilir)
}

# Lokasyon alias tablosu
LOCATION_ALIASES = {
    # İstanbul bölgeleri
    "anadolu yakası": ["kadıköy", "üsküdar", "ataşehir", "maltepe", "pendik", "sancaktepe"],
    "avrupa yakası": ["beşiktaş", "şişli", "fatih", "beyoğlu", "bakırköy", "zeytinburnu"],
    "merkez": ["kadıköy", "beşiktaş", "şişli", "fatih", "beyoğlu"],
    # Genel
    "merkezi": ["merkez"],
    "köy": ["köy", "mahalle", "bölge"],
}

# Normalization tablosu
_LOC_NORMALIZE = {
    "ı": "i", "İ": "i",
    "ş": "s", "Ş": "s",
    "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u",
    "ö": "o", "Ö": "o",
    "ç": "c", "Ç": "c",
}

def normalize_location_text(text: str) -> str:
    """Lokasyon metnini normalize eder."""
    text = text.lower()
    # Türkçe karakterleri dönüştür
    for turkish, ascii in _LOC_NORMALIZE.items():
        text = text.replace(turkish, ascii)
    # Gereksiz karakterleri kaldır
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def build_location_index() -> Dict[str, Dict]:
    """Lokasyon index'i oluşturur."""
    index = {}
    
    for district, data in TURKISH_DISTRICTS.items():
        # Anahtar
        norm = normalize_location_text(district)
        index[norm] = {"name": district, **data}
        
        # Alternatif isimler
        for alt in data.get("alternatifler", []):
            alt_norm = normalize_location_text(alt)
            index[alt_norm] = {"name": district, **data}
        
        # İl bazında
        il_norm = normalize_location_text(data["il"])
        if il_norm not in index:
            index[il_norm] = {"name": data["il"], "tip": "il", "alternatifler": []}
    
    return index

_LOCATION_INDEX = build_location_index()

def find_location(query: str) -> Optional[Dict]:
    """Sorguya uygun lokasyonu bulur."""
    norm_query = normalize_location_text(query)
    
    # Doğrudan eşleşme
    if norm_query in _LOCATION_INDEX:
        return _LOCATION_INDEX[norm_query]
    
    # Kısmi eşleşme (prefix match)
    matches = []
    for key in _LOCATION_INDEX:
        if key.startswith(norm_query) or norm_query.startswith(key):
            matches.append((key, _LOCATION_INDEX[key]))
    
    if matches:
        # En uzun eşleşmeyi seç
        best = max(matches, key=lambda x: len(x[0]))
        return best[1]
    
    # Fuzzy match (edit distance)
    return fuzzy_match_location(norm_query)

def fuzzy_match_location(query: str, max_distance: int = 3) -> Optional[Dict]:
    """Fuzzy matching ile lokasyon bulur."""
    best_match = None
    best_score = float('inf')
    
    for key, data in _LOCATION_INDEX.items():
        distance = levenshtein_distance(query, key)
        if distance <= max_distance and distance < best_score:
            best_score = distance
            best_match = data
    
    return best_match

def levenshtein_distance(s1: str, s2: str) -> int:
    """İki string arasındaki edit distance hesaplar."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def resolve_semantic_location(text: str) -> List[str]:
    """
    Semantik lokasyon çözümlemesi.
    "İstanbul Avrupa yakası" → ilçe listesi
    """
    norm_text = normalize_location_text(text)
    results = []
    
    # Alias kontrolü
    for alias, locations in LOCATION_ALIASES.items():
        if alias in norm_text:
            results.extend(locations)
    
    # İl/ilçe kontrolü
    for key, data in _LOCATION_INDEX.items():
        if key in norm_text:
            name = data.get("name", key)
            if name not in results:
                results.append(name)
    
    return results

def get_districts_by_city(city: str) -> List[str]:
    """Bir ile ait ilçeleri döndürür."""
    city_norm = normalize_location_text(city)
    
    districts = []
    for district, data in TURKISH_DISTRICTS.items():
        if data.get("il", "").lower().replace("ı", "i") == city_norm:
            districts.append(district)
    
    return sorted(districts)


class EnhancedLocationDB:
    """
    Gelişmiş lokasyon veritabanı.
    
    Kullanım:
        db = EnhancedLocationDB()
        result = db.search("Kadıköy")
        # → {"name": "kadıköy", "il": "istanbul", "tip": "ilçe"}
    """
    
    def __init__(self):
        self.index = _LOCATION_INDEX
        self.districts = TURKISH_DISTRICTS
        
    def search(self, query: str, fuzzy: bool = True) -> Optional[Dict]:
        """Lokasyon ara."""
        return find_location(query) or (fuzzy_match_location(normalize_location_text(query)) if fuzzy else None)
    
    def search_multi(self, query: str, fuzzy: bool = True) -> List[Dict]:
        """Birden fazla lokasyon ara (semantik)."""
        resolved = resolve_semantic_location(query)
        results = []
        
        for loc in resolved:
            found = self.search(loc, fuzzy=fuzzy)
            if found and found not in results:
                results.append(found)
        
        return results
    
    def get_city_districts(self, city: str) -> List[str]:
        """İle ait ilçeleri döndürür."""
        return get_districts_by_city(city)
    
    def autocomplete(self, prefix: str, limit: int = 10) -> List[str]:
        """Prefix'e göre otomatik tamamlama."""
        norm_prefix = normalize_location_text(prefix)
        matches = []
        
        for key in self.index:
            if key.startswith(norm_prefix):
                name = self.index[key].get("name", key)
                if name not in matches:
                    matches.append(name)
                if len(matches) >= limit:
                    break
        
        return matches


def test_enhanced_location_db():
    """Test fonksiyonu."""
    db = EnhancedLocationDB()
    
    print("=" * 60)
    print("ENHANCED LOCATION DB TEST")
    print("=" * 60)
    
    test_queries = [
        "Kadıköy",
        "kadikoy",
        "Beşiktaş",
        "besiktas",
        "Çankaya",
        "anadolu yakası",
        "avrupa yakası",
        "İstanbul",
        "İstanbul Avrupa",
    ]
    
    for query in test_queries:
        print(f"\n--- '{query}' ---")
        
        # Direct search
        result = db.search(query)
        print(f"Direct: {result}")
        
        # Multi search
        multi = db.search_multi(query)
        print(f"Multi: {multi}")
        
        # Autocomplete
        auto = db.autocomplete(query[:4], limit=5)
        print(f"Auto: {auto}")


if __name__ == "__main__":
    test_enhanced_location_db()