"""
segment_extractor.py - Multi-Location + Multi-POI Segment Çıkarıcı

Problem: "Kadıköyde kafe Beşiktaşta kasap" gibi sorgularda sadece son POI alınıyor.
Çözüm: Her lokasyon-POI çifti için ayrı segment oluştur.

Kullanım:
    from segment_extractor import extract_segments
    
    segments = extract_segments("Kadıköyde kafe Beşiktaşta kasap")
    # → [
    #     {"location": "kadıköy", "poi": "kafe", "osm_query": {...}},
    #     {"location": "beşiktaş", "poi": "kasap", "osm_query": {...}}
    # ]
"""

import sys
sys.path.insert(0, 'backend')

from typing import Dict, List, Optional, Any, Tuple
from bert_nlp_engine import (
    normalize_query_text,
    extract_candidate_spans,
    _singularize_tr_token,
    normalize_place_key,
    is_poi_concept_term,
)
from nlp_concept_resolver import (
    resolve_poi_concept,
    map_concept_to_osm_queries,
)

# Lokasyon suffix'leri (role_hint = "loc")
_LOC_SUFFIXES = ("de", "da", "te", "ta")

# POI kavram trigger kelimeleri
_POI_TRIGGERS = frozenset({
    "kafe", "cafe", "café",
    "restoran", "restaurant", "yemek",
    "kasap", "bakkal", "market", "manav",
    "eczane", "bar", "pub", "gece",
    "spor", "salonu", "fitness",
    "cami", "kilise", "sinagog",
    "müze", "galeri",
    "banka", "atm",
})


def extract_location_poi_segments(
    query: str,
    detected_places: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Sorguyu lokasyon-POI segmentlerine ayırır.
    
    "Kadıköyde kafe Beşiktaşta kasap" 
    → [{"location": "kadıköy", "poi": "kafe"}, {"location": "beşiktaş", "poi": "kasap"}]
    
    Args:
        query: Kullanıcı sorgusu
        detected_places: BertNLPEngine'den alınan tespit edilmiş yerler
    
    Returns:
        Segment listesi, her biri {location, poi, osm_query, confidence}
    """
    normalized_query = normalize_query_text(query or "")
    if not normalized_query:
        return []
    
    # 1. Aday span'ları çıkar
    spans = extract_candidate_spans(query, max_ngram=3)
    
    # 2. Lokasyon span'larını ayır (role_hint = "loc" veya suffix'li)
    location_spans = []
    poi_spans = []
    
    for span in spans:
        normalized = span.get("normalized", "")
        role_hint = span.get("role_hint")
        
        # Lokasyon span'leri
        if role_hint == "loc" or _is_location_suffix_span(span):
            location_spans.append({
                "text": normalized,
                "surface": span.get("surface", ""),
                "start": span.get("start", 0),
                "end": span.get("end", 0),
                "token_count": span.get("token_count", 1),
            })
        # POI span'leri (role_hint yok ve POI trigger kelime)
        elif role_hint is None and _is_poi_token(normalized):
            poi_spans.append({
                "text": normalized,
                "surface": span.get("surface", ""),
                "start": span.get("start", 0),
                "end": span.get("end", 0),
                "token_count": span.get("token_count", 1),
            })
    
    # 3. Segmentleri oluştur (sıralı eşleştirme)
    segments = _build_segments(location_spans, poi_spans)
    
    return segments


def _is_location_suffix_span(span: Dict[str, Any]) -> bool:
    """Span'ın lokasyon suffix'i (da/de/ta/te) içerip içermediğini kontrol eder."""
    surface = span.get("surface", "").lower()
    for suffix in _LOC_SUFFIXES:
        if surface.endswith(suffix) and len(surface) > len(suffix) + 2:
            return True
    return False


def _is_poi_token(text: str) -> bool:
    """Token'ın POI kavramı olup olmadığını kontrol eder."""
    if not text or len(text) < 2:
        return False
    
    # Doğrudan POI trigger kontrolü
    if text in _POI_TRIGGERS:
        return True
    
    # Ek soyulmuş haliyle kontrol
    singular = _singularize_tr_token(text)
    if singular in _POI_TRIGGERS:
        return True
    
    # nlp_concept_resolver kontrolü
    if is_poi_concept_term(text):
        return True
    
    return False


def _build_segments(
    location_spans: List[Dict[str, Any]],
    poi_spans: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Lokasyon ve POI span'larını sıralı eşleştirerek segment oluşturur.
    
    Algoritma:
    - Her POI span'ı için, kendinden önceki en yakın lokasyon span'ını bul
    - Eğer POI span, herhangi bir lokasyondan sonra geliyorsa o lokasyona bağla
    """
    if not location_spans or not poi_spans:
        return []
    
    segments = []
    seen_poi = set()
    seen_loc = set()
    
    # POI span'larını sırala
    sorted_pois = sorted(poi_spans, key=lambda x: x.get("start", 0))
    sorted_locs = sorted(location_spans, key=lambda x: x.get("start", 0))
    
    for poi in sorted_pois:
        poi_text = poi.get("text", "")
        if not poi_text or poi_text in seen_poi:
            continue
        
        # Bu POI'den önceki en yakın lokasyonu bul
        best_loc = None
        for loc in sorted_locs:
            loc_text = loc.get("text", "")
            if not loc_text or loc_text in seen_loc:
                continue
            # Lokasyon POI'den önce gelmeli
            if loc.get("start", 0) < poi.get("start", 0):
                best_loc = loc
            else:
                break
        
        if best_loc:
            poi_resolved = resolve_poi_concept(poi_text)
            osm_query = map_concept_to_osm_queries(poi_resolved.concept or poi_text)
            
            segments.append({
                "location": best_loc.get("text", ""),
                "location_surface": best_loc.get("surface", ""),
                "poi": poi_resolved.concept or poi_text,
                "poi_surface": poi.get("surface", ""),
                "source": poi_resolved.source,
                "confidence": float(poi_resolved.confidence),
                "osm_query": osm_query[0] if osm_query else {},
                "location_start": best_loc.get("start", 0),
                "poi_start": poi.get("start", 0),
            })
            
            seen_poi.add(poi_text)
            # Aynı lokasyon birden fazla POI'ye bağlanabilir
        else:
            # Lokasyon yoksa sadece POI olarak ekle (solo poi)
            poi_resolved = resolve_poi_concept(poi_text)
            osm_query = map_concept_to_osm_queries(poi_resolved.concept or poi_text)
            
            segments.append({
                "location": None,
                "location_surface": None,
                "poi": poi_resolved.concept or poi_text,
                "poi_surface": poi.get("surface", ""),
                "source": poi_resolved.source,
                "confidence": float(poi_resolved.confidence),
                "osm_query": osm_query[0] if osm_query else {},
                "location_start": None,
                "poi_start": poi.get("start", 0),
            })
            seen_poi.add(poi_text)
    
    return segments


def test_segment_extraction():
    """Test fonksiyonu"""
    test_queries = [
        "Kadıköyde kafe Beşiktaşta kasap",
        "Taksimde restaurant Besiktasta bar",
        "Üsküdarda eczane Kadıköyde spor salonu",
        "Sadece kasap",
        "Beşiktaşta kafe",
    ]
    
    print("=" * 70)
    print("SEGMENT EXTRACTION TEST")
    print("=" * 70)
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"SORGU: {query}")
        print(f"{'='*60}")
        
        segments = extract_location_poi_segments(query)
        
        print(f"\nTOPLAM SEGMENT: {len(segments)}")
        for i, seg in enumerate(segments):
            print(f"\n  Segment {i+1}:")
            print(f"    location: {seg['location']}")
            print(f"    poi: {seg['poi']}")
            print(f"    source: {seg['source']}")
            print(f"    confidence: {seg['confidence']}")
            print(f"    osm_query: {seg['osm_query']}")


if __name__ == "__main__":
    test_segment_extraction()