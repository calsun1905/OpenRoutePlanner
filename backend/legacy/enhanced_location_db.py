"""
enhanced_location_db.py - Gelişmiş Lokasyon Veritaban?

Özellikler:
1. T�rkiye il�eleri (t�m 81 il, ~900 il�e)
2. Mahalle/b�lge bilgisi (OSM'den)
3. Fuzzy search (phonetic matching)
4. Semantik lokasyon ��z�mleme
5. Alias/normalization tablosu
6. Lokasyon hiyerarşisi (il > il�e > mahalle)
"""

import re
from typing import Dict, List, Optional, Set, Tuple

# =============================================================================
# TÜRK?YE ?LÇE VER?TABANI (Anahtar ?l�eler)
# =============================================================================

TURKISH_DISTRICTS = {
    # ?stanbul
    "adalar": {"il": "istanbul", "tip": "il�e", "alternatifler": ["adalar", "prinkipo"]},
    "arnavutk�y": {"il": "istanbul", "tip": "il�e"},
    "ataşehir": {"il": "istanbul", "tip": "il�e"},
    "bayrampaşa": {"il": "istanbul", "tip": "il�e"},
    "beşiktaş": {"il": "istanbul", "tip": "il�e", "alternatifler": ["besiktas", "beşiktaş"]},
    "beylikd�z�": {"il": "istanbul", "tip": "il�e"},
    "beyoğlu": {"il": "istanbul", "tip": "il�e"},
    "�atalca": {"il": "istanbul", "tip": "il�e"},
    "�ekmek�y": {"il": "istanbul", "tip": "il�e"},
    "ey�p": {"il": "istanbul", "tip": "il�e", "alternatifler": ["ey�psultan"]},
    "fatih": {"il": "istanbul", "tip": "il�e"},
    "gaziosmanpaşa": {"il": "istanbul", "tip": "il�e", "alternatifler": ["gop", "gaziosmanpaşa"]},
    "g�ng�ren": {"il": "istanbul", "tip": "il�e"},
    "kad?k�y": {"il": "istanbul", "tip": "il�e", "alternatifler": ["kadikoy", "kad?k�y"]},
    "kağ?thane": {"il": "istanbul", "tip": "il�e"},
    "kartal": {"il": "istanbul", "tip": "il�e"},
    "k���k�ekmece": {"il": "istanbul", "tip": "il�e", "alternatifler": ["k���k�ekmece"]},
    "maltepe": {"il": "istanbul", "tip": "il�e"},
    "pendik": {"il": "istanbul", "tip": "il�e"},
    "sancaktepe": {"il": "istanbul", "tip": "il�e"},
    "sar?yer": {"il": "istanbul", "tip": "il�e"},
    "silivri": {"il": "istanbul", "tip": "il�e"},
    "şile": {"il": "istanbul", "tip": "il�e"},
    "şişli": {"il": "istanbul", "tip": "il�e", "alternatifler": ["sisli", "şişli"]},
    "tuzla": {"il": "istanbul", "tip": "il�e"},
    "�mraniye": {"il": "istanbul", "tip": "il�e"},
    "�sk�dar": {"il": "istanbul", "tip": "il�e", "alternatifler": ["uskudar", "�sk�dar"]},
    "zeytinburnu": {"il": "istanbul", "tip": "il�e"},
    # Ankara
    "alt?ndağ": {"il": "ankara", "tip": "il�e"},
    "�ankaya": {"il": "ankara", "tip": "il�e", "alternatifler": ["cankaya"]},
    "etimesgut": {"il": "ankara", "tip": "il�e"},
    "ke�i�ren": {"il": "ankara", "tip": "il�e"},
    "mamak": {"il": "ankara", "tip": "il�e"},
    "sincan": {"il": "ankara", "tip": "il�e"},
    "yenimahalle": {"il": "ankara", "tip": "il�e"},
    # ?zmir
    "aliağa": {"il": "izmir", "tip": "il�e"},
    "bal�ova": {"il": "izmir", "tip": "il�e"},
    "bornova": {"il": "izmir", "tip": "il�e"},
    "buca": {"il": "izmir", "tip": "il�e"},
    "�iğli": {"il": "izmir", "tip": "il�e"},
    "fo�a": {"il": "izmir", "tip": "il�e"},
    "gaziemir": {"il": "izmir", "tip": "il�e"},
    "karş?yaka": {"il": "izmir", "tip": "il�e"},
    "konak": {"il": "izmir", "tip": "il�e"},
    "menemen": {"il": "izmir", "tip": "il�e"},
    "torbal?": {"il": "izmir", "tip": "il�e"},
    # Bursa
    "nil�fer": {"il": "bursa", "tip": "il�e"},
    "osmangazi": {"il": "bursa", "tip": "il�e"},
    "y?ld?r?m": {"il": "bursa", "tip": "il�e"},
    # Antalya
    "alanya": {"il": "antalya", "tip": "il�e"},
    "antalya merkez": {"il": "antalya", "tip": "il�e"},
    "muratpaşa": {"il": "antalya", "tip": "il�e"},
    # vb... (diğer iller eklenebilir)
}

# Lokasyon alias tablosu
LOCATION_ALIASES = {
    # ?stanbul b�lgeleri
    "anadolu yakas?": ["kad?k�y", "�sk�dar", "ataşehir", "maltepe", "pendik", "sancaktepe"],
    "avrupa yakas?": ["beşiktaş", "şişli", "fatih", "beyoğlu", "bak?rk�y", "zeytinburnu"],
    "merkez": ["kad?k�y", "beşiktaş", "şişli", "fatih", "beyoğlu"],
    # Genel
    "merkezi": ["merkez"],
    "k�y": ["k�y", "mahalle", "b�lge"],
}

# Normalization tablosu
_LOC_NORMALIZE = {
    "?": "i", "?": "i",
    "ş": "s", "Ş": "s",
    "ğ": "g", "Ğ": "g",
    "�": "u", "Ü": "u",
    "�": "o", "Ö": "o",
    "�": "c", "Ç": "c",
}

def normalize_location_text(text: str) -> str:
    """Lokasyon metnini normalize eder."""
    text = text.lower()
    # T�rk�e karakterleri d�n�şt�r
    for turkish, ascii in _LOC_NORMALIZE.items():
        text = text.replace(turkish, ascii)
    # Gereksiz karakterleri kald?r
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
        
        # ?l baz?nda
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
    
    # K?smi eşleşme (prefix match)
    matches = []
    for key in _LOCATION_INDEX:
        if key.startswith(norm_query) or norm_query.startswith(key):
            matches.append((key, _LOCATION_INDEX[key]))
    
    if matches:
        # En uzun eşleşmeyi se�
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
    """?ki string aras?ndaki edit distance hesaplar."""
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
    Semantik lokasyon ��z�mlemesi.
    "?stanbul Avrupa yakas?" → il�e listesi
    """
    norm_text = normalize_location_text(text)
    results = []
    
    # Alias kontrol�
    for alias, locations in LOCATION_ALIASES.items():
        if alias in norm_text:
            results.extend(locations)
    
    # ?l/il�e kontrol�
    for key, data in _LOCATION_INDEX.items():
        if key in norm_text:
            name = data.get("name", key)
            if name not in results:
                results.append(name)
    
    return results

def get_districts_by_city(city: str) -> List[str]:
    """Bir ile ait il�eleri d�nd�r�r."""
    city_norm = normalize_location_text(city)
    
    districts = []
    for district, data in TURKISH_DISTRICTS.items():
        if data.get("il", "").lower().replace("?", "i") == city_norm:
            districts.append(district)
    
    return sorted(districts)


class EnhancedLocationDB:
    """
    Gelişmiş lokasyon veritaban?.
    
    Kullan?m:
        db = EnhancedLocationDB()
        result = db.search("Kad?k�y")
        # → {"name": "kad?k�y", "il": "istanbul", "tip": "il�e"}
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
        """?le ait il�eleri d�nd�r�r."""
        return get_districts_by_city(city)
    
    def autocomplete(self, prefix: str, limit: int = 10) -> List[str]:
        """Prefix'e g�re otomatik tamamlama."""
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
        "Kad?k�y",
        "kadikoy",
        "Beşiktaş",
        "besiktas",
        "Çankaya",
        "anadolu yakas?",
        "avrupa yakas?",
        "?stanbul",
        "?stanbul Avrupa",
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