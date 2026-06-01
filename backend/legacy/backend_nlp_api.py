"""
backend_nlp_api.py - Backend NLP API Entegrasyonu

BERT sorgulamas?n? backend API'ye entegre eder.
D?ş API rate limit sorunlar? i�in mock/backup veri ile �al?ş?r.
"""

import json
import os
from typing import Dict, List, Optional, Any

# =============================================================================
# BACKEND ENTEGRASYONU
# =============================================================================

def create_backend_nlp_response(segments: List[Dict]) -> Dict:
    """Backend API i�in NLP yan?t? oluşturur."""
    
    results = {
        "success": True,
        "query_type": "multi_segment" if len(segments) > 1 else "single_segment",
        "segment_count": len(segments),
        "segments": [],
        "total_results": 0,
    }
    
    for seg in segments:
        loc_data = seg.get("location_data") or {}
        
        result = {
            "location": {
                "name": seg.get("location") or "T�m ?stanbul",
                "lat": loc_data.get("lat"),
                "lon": loc_data.get("lon"),
            },
            "poi": {
                "type": seg.get("poi", ""),
                "osm_tags": seg.get("osm_tags", {}),
            },
            "osm_query": seg.get("osm_query", {}),
            "results": [],  # Ger�ek POI sonu�lar? backend'e b?rak?l?yor
            "note": seg.get("note", "POI aramas? backend API �zerinden yap?lacak"),
            "is_plural_normalized": seg.get("is_plural_normalized", False)
        }
        results["segments"].append(result)
    
    return results


def integrate_with_backend():
    """Backend API endpoint'leri i�in haz?rl?k."""
    
    # Backend'de kullan?lacak endpoint'ler
    api_spec = {
        "/api/nlp/parse": {
            "method": "POST",
            "description": "BERT sorgu ��z�mleme",
            "input": {
                "query": "string - Kullan?c? sorgusu"
            },
            "output": {
                "segments": "array - Parsellenmiş segmentler",
                "success": "boolean"
            }
        },
        "/api/poi/search": {
            "method": "POST",
            "description": "POI aramas?",
            "input": {
                "location": "string - ?l�e ad?",
                "poi_type": "string - POI t�r�",
                "osm_tags": "object - OSM tag'leri"
            },
            "output": {
                "results": "array - POI sonu�lar?"
            }
        }
    }
    
    return api_spec


# =============================================================================
# MOCK POI VER?LER? (Rate limit olmad?ğ?nda kullan?l?r)
# =============================================================================

MOCK_POI_DATABASE = {
    "kadikoy": [
        {"name": "Kad?k�y Çayc?s?", "lat": 40.9907, "lon": 29.0259, "type": "cafe", "street": "Caferağa Mah."},
        {"name": "Bossa Cafe", "lat": 40.9912, "lon": 29.0265, "type": "cafe", "street": "Moda Cd."},
        {"name": "Arkaoda Cafe", "lat": 40.9921, "lon": 29.0278, "type": "cafe", "street": "Rasimpaşa"},
    ],
    "besiktas": [
        {"name": "Swiss Otel Cafe", "lat": 41.0432, "lon": 29.0088, "type": "cafe", "street": "Barbaros Bulv."},
        {"name": "Akb�k Cafe", "lat": 41.0445, "lon": 29.0101, "type": "cafe", "street": "Akaretler"},
        {"name": "Demlik Cafe", "lat": 41.0451, "lon": 29.0112, "type": "cafe", "street": "Cihann�ma"},
    ],
    "uskudar": [
        {"name": "Çengelk�y Kahvesi", "lat": 41.0265, "lon": 29.0432, "type": "cafe", "street": "Çengelk�y"},
        {"name": "Istinye Kahve", "lat": 41.0278, "lon": 29.0445, "type": "cafe", "street": "Altunizade"},
    ],
    "sisli": [
        {"name": "Nişantaş? Kahve", "lat": 41.0501, "lon": 28.9856, "type": "cafe", "street": "Abdi ?pek�i Cd."},
        {"name": "Osmanbey Coffee", "lat": 41.0512, "lon": 28.9867, "type": "cafe", "street": "Halaskargazi Cd."},
    ],
    "fatih": [
        {"name": "S�leymaniye Kahvesi", "lat": 41.0167, "lon": 28.9612, "type": "cafe", "street": "S�leymaniye"},
        {"name": "Aksaray Poşeu", "lat": 41.0151, "lon": 28.9623, "type": "cafe", "street": "Aksaray"},
    ],
}

def get_mock_pois(location: str, poi_type: str = "cafe", limit: int = 5) -> List[Dict]:
    """Mock POI verisi d�nd�r�r (API rate limit olduğunda kullan?l?r)."""
    
    normalized_loc = location.lower().replace("?", "i").replace("ş", "s").replace("ğ", "g")
    
    pois = MOCK_POI_DATABASE.get(normalized_loc, [])
    
    # Filtrele
    if poi_type:
        pois = [p for p in pois if p.get("type") == poi_type or poi_type in p.get("type", "")]
    
    return pois[:limit]


def get_all_mock_locations() -> List[str]:
    """T�m mock lokasyonlar? d�nd�r�r."""
    return list(MOCK_POI_DATABASE.keys())


# =============================================================================
# TEST
# =============================================================================

def test_backend_integration():
    """Backend entegrasyonu testi."""
    from bert_istanbul_integration import IstanbulBERTEngine
    
    print("=" * 60)
    print("BACKEND ENTEGRASYON TEST")
    print("=" * 60)
    
    engine = IstanbulBERTEngine()
    
    test_queries = [
        "Kad?k�yde kafe",
        "Beşiktaşta bar",
        "Üsk�darda eczane",
        "kafeler",  # Solo POI
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"SORGU: {query}")
        print("="*50)
        
        result = engine.parse(query)
        
        if result["success"]:
            # Backend yan?t? oluştur
            backend_response = create_backend_nlp_response(result["segments"])
            
            print(f"✅ {backend_response['segment_count']} segment")
            print(f"   Tip: {backend_response['query_type']}")
            
            for i, seg in enumerate(result["segments"]):
                loc = seg.get("location", "N/A")
                poi = seg.get("poi", "N/A")
                
                print(f"\n   Segment {i+1}: {loc} - {poi}")
                
                # Mock POI g�ster
                if loc:
                    pois = get_mock_pois(loc, poi, limit=3)
                    if pois:
                        print(f"      Mock POI'ler:")
                        for p in pois:
                            print(f"       - {p['name']} ({p['street']})")
                    else:
                        print(f"      (Mock veri yok)")
        else:
            print(f"❌ Parseleme hatas?: {result.get('error')}")
    
    print("\n" + "=" * 60)
    print("KULLANILABILIR MOCK LOKASYONLAR:")
    print("=" * 60)
    for loc in get_all_mock_locations():
        pois = MOCK_POI_DATABASE[loc]
        print(f"  {loc}: {len(pois)} POI")


if __name__ == "__main__":
    test_backend_integration()