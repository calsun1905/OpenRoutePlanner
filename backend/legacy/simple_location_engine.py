"""
simple_location_engine.py - Basit Lokasyon Ç�z�mleme

Sadece il�e ve il isimlerini eşleştirir.
POI veritaban? gerektirmez.
"""

import json
from typing import Dict, List, Optional

# =============================================================================
# TÜRK?YE ?LÇE VER?TABANI (?stanbul - 37 il�e)
# =============================================================================

TURKEY_LOCATIONS = {
    # ?STANBUL - Avrupa Yakas?
    "adalar": {"name": "Adalar", "il": "istanbul", "yakla": "avrupa", "lat": 40.87, "lon": 29.13},
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
# YARDIMCI FONKS?YONLAR
# =============================================================================

def normalize(text: str) -> str:
    """Metni normalize eder (T�rk�e karakterler)."""
    text = text.lower()
    replacements = {
        "?": "i", "?": "i",
        "ş": "s", "Ş": "s",
        "ğ": "g", "Ğ": "g",
        "�": "u", "Ü": "u",
        "�": "o", "Ö": "o",
        "�": "c", "Ç": "c",
    }
    for turkish, ascii_char in replacements.items():
        text = text.replace(turkish, ascii_char)
    return text

def find_location(query: str) -> Optional[Dict]:
    """Sorguya uygun lokasyonu bulur."""
    
    # Önce normalize et
    normalized = normalize(query)
    
    # Suffix kald?r (da, de, ta, te)
    suffixes = ["da", "de", "ta", "te"]
    base = normalized
    for suffix in suffixes:
        if normalized.endswith(suffix):
            base = normalized[:-len(suffix)]
            break
    
    # Doğrudan eşleşme
    if base in TURKEY_LOCATIONS:
        return TURKEY_LOCATIONS[base]
    
    # Sorgunun kendisini de dene (suffix kald?rmadan)
    if query.lower() in TURKEY_LOCATIONS:
        return TURKEY_LOCATIONS[query.lower()]
    
    # Sorgu i�inde lokasyon ara
    query_lower = query.lower()
    for key in TURKEY_LOCATIONS:
        # "kad?k�yde" i�inde "kad?k�y" var m??
        # Önce sorguyu normalize et
        query_norm = normalize(query_lower)
        key_norm = normalize(key)
        
        if key_norm in query_norm or query_norm in key_norm:
            return TURKEY_LOCATIONS[key]
    
    return None

def extract_location_segments(query: str) -> List[Dict]:
    """Sorgudan lokasyon segmentlerini �?kar?r."""
    segments = []
    words = query.split()
    
    current_location = None
    
    for word in words:
        word_norm = normalize(word)
        
        # Suffix kald?r
        base = word_norm
        removed_suffix = None
        for suffix in ["da", "de", "ta", "te"]:
            if word_norm.endswith(suffix):
                base = word_norm[:-len(suffix)]
                removed_suffix = suffix
                break
        
        # Lokasyon kontrol�
        location = find_location(base)
        
        if location:
            # Önceki lokasyonu kaydet (varsa)
            if current_location:
                segments.append(current_location)
            
            current_location = {
                "name": location["name"],
                "il": location["il"],
                "yakla": location.get("yakla", ""),
                "lat": location["lat"],
                "lon": location["lon"],
                "full_name": f"{location['name']}, {location['il'].title()}",
            }
    
    # Son lokasyonu ekle
    if current_location:
        segments.append(current_location)
    
    return segments


def parse_location_query(query: str) -> Dict:
    """
    Sorguyu ��z�mler.
    
    Args:
        query: "Kad?k�yde cafe" veya "Beşiktaşta bar"
    
    Returns:
        {
            "success": True,
            "locations": [...],
            "query": "..."
        }
    """
    query = query.strip()
    if not query:
        return {"success": False, "error": "Boş sorgu", "locations": []}
    
    locations = extract_location_segments(query)
    
    return {
        "success": len(locations) > 0,
        "query": query,
        "locations": locations,
        "location_count": len(locations),
    }


# =============================================================================
# TEST
# =============================================================================

def test_location_engine():
    """Test."""
    print("=" * 60)
    print("LOKASYON ÇÖZÜMLEME TEST")
    print("=" * 60)
    
    test_queries = [
        "Kad?k�yde cafe",
        "Beşiktaşta bar",
        "Üsk�darda eczane",
        "?stanbul Kad?k�y",
        "Kad?k�y Beşiktaşta cafe",
        "sar?yerde spor",
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"SORGU: {query}")
        print("="*50)
        
        result = parse_location_query(query)
        
        if result["success"]:
            print(f"✅ {result['location_count']} lokasyon bulundu:")
            
            for loc in result["locations"]:
                print(f"\n  📍 {loc['name']}, {loc['il'].title()}")
                print(f"     Yakla: {loc['yakla']}")
                print(f"     Koordinat: {loc['lat']:.4f}, {loc['lon']:.4f}")
                print(f"     Tam ad: {loc['full_name']}")
        else:
            print(f"❌ Lokasyon bulunamad?: {result.get('error')}")
    
    print("\n" + "=" * 60)
    print(f"TOPLAM ?LÇE: {len(TURKEY_LOCATIONS)}")
    print("="*60)
    
    # ?stanbul il�eleri listesi
    print("\n📋 ?STANBUL ?LÇELER?:")
    for key in sorted(TURKEY_LOCATIONS.keys()):
        loc = TURKEY_LOCATIONS[key]
        print(f"  - {loc['name']} ({loc['yakla']})")


if __name__ == "__main__":
    test_location_engine()