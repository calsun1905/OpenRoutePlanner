"""
segment_extractor_v2.py - Geliştirilmiş Segment Çıkarıcı

İyileştirmeler:
1. OSM API ile küçük bölgesel yerleşim birimlerini çekme (Küçükyalı, Çınar vb.)
2. Çoğul ek normalizasyonu (kafeler → kafe, kasaplar → kasap)
3. Multi-token POI koruma ("spor salonu" ayrılmamalı)
4. Solo POI desteği (lokasyon olmadan da POI dönebilir)
"""

import sys
sys.path.insert(0, 'backend')

from typing import Dict, List, Optional, Any, Tuple
import re
import requests

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

# OSM API
OSM_API_URL = "https://nominatim.openstreetmap.org/search"
OSM_RATE_LIMIT = 1.0  # saniye

# Lokasyon suffix'leri
_LOC_SUFFIXES = ("de", "da", "te", "ta")

# Sadece apostrof sonrası veya kelime sonunda tek başına olan suffix'leri kabul et
_LOC_SUFFIX_PATTERN = re.compile(r"['\s](de|da|te|ta)$", re.IGNORECASE)

# Çoğul ekleri
_PLURAL_SUFFIXES = ("lar", "ler")

# POI kavram trigger kelimeleri (genişletilmiş)
_POI_TRIGGERS = frozenset({
    # Yiyecek/İçecek
    "kafe", "cafe", "café", "restoran", "restaurant", "yemek", "aş", "yemekhane",
    "bar", "pub", "gece", "club", "disco",
    # Market
    "kasap", "bakkal", "market", "manav", "süpermarket", "şarküteri",
    "kasaplar", "bakkallar", "marketler", "manavlar",  # Çoğul halleri
    "kafeler", "restoranlar", "barlar",  # Çoğul halleri
    # Sağlık
    "eczane", "hospital", "hastane", "klinik", "doktor", "tıp",
    "eczaneler", "hastaneler", "klinikler",  # Çoğul
    # Eğitim
    "okul", "üniversite", "fakülte", "kurs", "dersane",
    "okullar", "üniversiteler",  # Çoğul
    # Alışveriş
    "mağaza", "dükkan", "avm", "alışveriş", "çarşı",
    "mağazalar", "dükkanlar",  # Çoğul
    # Spor/Eğlence
    "spor", "salonu", "fitness", "gym", "stadyum", "sinema", "tiyatro",
    "sporlar", "salonları", "sinemalar",  # Çoğul
    # Dini
    "cami", "mescit", "kilise", "sinagog", "türbe",
    "camiler", " kiliseler",  # Çoğul
    # Diğer
    "müze", "galeri", "kütüphane", "banka", "atm", "postane",
    "müzeler", "galeriler", "kütüphaneler", "bankalar",  # Çoğul
})

# Korunan multi-token POI ifadeleri
_PROTECTED_POI_PHRASES = frozenset({
    "spor salonu", "spor salonları", "yemek salonu", "fast food",
    "süper market", "süpermarket", "alışveriş merkezi",
    "sağlık ocağı", "aile sağlığı", "toplum sağlığı",
})

# Küçük bölgesel yerleşim birimlerini OSM'den çek
_osm_cache: Dict[str, List[str]] = {}
_last_osm_call = 0.0


def search_osm_places(query: str, limit: int = 5) -> List[str]:
    """OSM API'den yer arar."""
    global _last_osm_call
    import time
    
    # Cache kontrolü
    if query in _osm_cache:
        return _osm_cache[query]
    
    # Rate limiting
    now = time.time()
    if now - _last_osm_call < OSM_RATE_LIMIT:
        time.sleep(OSM_RATE_LIMIT - (now - _last_osm_call))
    
    try:
        params = {
            "q": f"{query}, Turkey",
            "format": "json",
            "countrycodes": "tr",
            "limit": limit,
            "addressdetails": 1,
        }
        headers = {"User-Agent": "OpenRoutePlanner/1.0 (poi-search)"}
        
        resp = requests.get(OSM_API_URL, params=params, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            places = []
            for item in data:
                # Mahalle/köy gibi küçük yerleşim birimlerini de al
                addr = item.get("address", {})
                name = item.get("display_name", item.get("name", ""))
                # Kısa isim
                short_name = name.split(",")[0].strip()
                
                # Küçük yerleşim birimi mi? (neighbourhood, suburb, village, hamlet)
                place_type = addr.get("type", "")
                if place_type in ("neighbourhood", "suburb", "village", "hamlet", "quarter"):
                    if short_name and short_name not in places:
                        places.append(short_name)
                        _osm_cache[short_name] = short_name
            
            _last_osm_call = time.time()
            return places
    except Exception as e:
        print(f"[OSM Search] Hata: {e}")
    
    return []


def normalize_plural_poi(text: str) -> str:
    """Çoğul POI ifadelerini tekile çevirir."""
    if not text:
        return text
    
    # Korunan ifadeler kontrolü
    if text in _PROTECTED_POI_PHRASES:
        return text
    
    # Doğrudan çoğul ek kontrolü
    for suffix in _PLURAL_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix) + 2:
            singular = text[:-len(suffix)]
            # Ekildiğinde anlam kaybolmuyorsa çevir
            if singular in _POI_TRIGGERS or is_poi_concept_term(singular):
                return singular
            # Alternatif: "kafeler" → "kafe"
            if singular + "ler" in _POI_TRIGGERS or singular + "lar" in _POI_TRIGGERS:
                return singular
    
    return text


def _is_poi_token(text: str) -> bool:
    """Token'ın POI kavramı olup olmadığını kontrol eder."""
    if not text or len(text) < 2:
        return False
    
    # Çoğul normalizasyonu
    normalized = normalize_plural_poi(text)
    
    # Doğrudan POI trigger kontrolü
    if normalized in _POI_TRIGGERS or text in _POI_TRIGGERS:
        return True
    
    # Ek soyulmuş haliyle kontrol
    singular = _singularize_tr_token(normalized)
    if singular in _POI_TRIGGERS or singular in ("kafe", "kasap", "restoran", "bar"):
        return True
    
    # nlp_concept_resolver kontrolü
    if is_poi_concept_term(normalized) or is_poi_concept_term(text):
        return True
    
    return False


def _is_location_suffix_span(span: Dict[str, Any]) -> bool:
    """Span'ın lokasyon suffix'i içerip içermediğini kontrol eder."""
    surface = span.get("surface", "").lower()
    # Sadece apostrof ile ayrılmış suffix'leri kabul et: "Kadıköy'de", "Beşiktaş'ta"
    # Bitistik suffix'leri ("Kadıköyde") kabul etme - bunlar yer adının parçası
    for suffix in _LOC_SUFFIXES:
        # Apostrof sonrası kontrol: "kadıköy'de"
        if f"'{suffix}" in surface:
            return True
        # Apostrof yok ama kelime apostrof içeriyorsa: "kadıköyde" - kabul etme
    return False


def _extract_location_base(surface: str) -> str:
    """Lokasyon yüzeyinden base'i (suffix'siz hali) çıkarır."""
    surface = surface.lower()
    # Sadece apostrof sonrası suffix'leri kabul et
    for suffix in _LOC_SUFFIXES:
        marker = f"'{suffix}"
        if marker in surface:
            return surface.split(marker)[0]
    # Apostrof yoksa base'i değiştirme - bitişik suffix yer adının parçası
    return surface


def extract_location_poi_segments(
    query: str,
    detected_places: Optional[List[Dict[str, Any]]] = None,
    use_osm: bool = True,
) -> List[Dict[str, Any]]:
    """
    Sorguyu lokasyon-POI segmentlerine ayırır (geliştirilmiş).
    
    Args:
        query: Kullanıcı sorgusu
        detected_places: BertNLPEngine'den alınan yerler
        use_osm: Küçük yerleşim birimlerini OSM'den çek
    """
    normalized_query = normalize_query_text(query or "")
    if not normalized_query:
        return []
    
    # 1. Bilinmeyen küçük yerleri OSM'den ara
    small_places = []
    if use_osm:
        # Query'deki bilinmeyen kelimeleri tespit et
        words = normalized_query.split()
        for word in words:
            if len(word) >= 4:  # En az 4 karakter
                # Ek kontrolü yap (da/de/ta/te)
                base_word = word
                for suffix in _LOC_SUFFIXES:
                    if word.endswith(suffix):
                        base_word = word[:-len(suffix)]
                        break
                
                if base_word and base_word not in ("kadıköy", "beşiktaş", "taksim", "üsküdar", "şişli"):
                    found = search_osm_places(base_word)
                    small_places.extend(found)
    
    # 2. Aday span'ları çıkar
    spans = extract_candidate_spans(query, max_ngram=3)
    
    # 3. Lokasyon ve POI span'larını ayır
    location_spans = []
    poi_spans = []
    processed_poi_texts = set()
    
    for span in spans:
        normalized = span.get("normalized", "")
        role_hint = span.get("role_hint")
        surface = span.get("surface", "").lower()
        span_start = span.get("start", 0)
        span_end = span.get("end", 0)
        
        # Çoğul POI normalizasyonu
        if role_hint is None:
            normalized = normalize_plural_poi(normalized)
        
        # Lokasyon span'leri - role_hint="loc" veya apostrof sonrası suffix
        is_loc = _is_location_suffix_span(span)
        if role_hint == "loc" or is_loc:
            # Base'i belirle - bert_nlp_engine zaten normalize ediyor
            # normalized değeri doğru (suffix kaldırılmış), onu kullan
            base = normalized
            
            location_spans.append({
                "text": normalized,
                "base": base,  # normalized = base (suffix zaten kaldırılmış)
                "surface": span.get("surface", ""),
                "start": span_start,
                "end": span_end,
                "token_count": span.get("token_count", 1),
            })
        # POI span'leri - role_hint yok ve POI trigger kelime
        elif role_hint is None and _is_poi_token(normalized):
            poi_text = normalize_plural_poi(normalized)
            if poi_text not in processed_poi_texts:
                poi_spans.append({
                    "text": poi_text,
                    "original": normalized,
                    "surface": span.get("surface", ""),
                    "start": span_start,
                    "end": span_end,
                    "token_count": span.get("token_count", 1),
                })
                processed_poi_texts.add(poi_text)
    
    # 4. Küçük yerleşim birimlerini lokasyon olarak ekle
    for place in small_places:
        if not any(loc["base"] == place for loc in location_spans):
            location_spans.append({
                "text": place,
                "base": place,
                "surface": place,
                "start": -1,  # Bilinmiyor
                "end": -1,
                "token_count": 1,
                "source": "osm",
            })
    
    # 5. Segmentleri oluştur
    segments = _build_segments_v2(location_spans, poi_spans)
    
    return segments


def _build_segments_v2(
    location_spans: List[Dict[str, Any]],
    poi_spans: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Geliştirilmiş segment oluşturma."""
    if not poi_spans:
        return []
    
    segments = []
    sorted_pois = sorted(poi_spans, key=lambda x: x.get("start", 0))
    sorted_locs = sorted(location_spans, key=lambda x: x.get("start", 0) if x.get("start", 0) >= 0 else float('inf'))
    
    for poi in sorted_pois:
        poi_text = poi.get("text", "")
        if not poi_text:
            continue
        
        # Çoğul tekile çevir
        singular_poi = normalize_plural_poi(poi_text)
        
        # Bu POI'den önceki en yakın lokasyonu bul
        best_loc = None
        for loc in sorted_locs:
            loc_text = loc.get("base", "")
            if not loc_text:
                continue
            # Lokasyon POI'den önce gelmeli veya bilinmiyor
            loc_start = loc.get("start", 0)
            poi_start = poi.get("start", 0)
            
            if loc_start < 0:  # OSM'den gelen bilinmeyen lokasyon
                best_loc = loc
            elif loc_start < poi_start:
                best_loc = loc
        
        # POI çözümle
        poi_resolved = resolve_poi_concept(singular_poi)
        concept = poi_resolved.concept or singular_poi
        osm_query = map_concept_to_osm_queries(concept)
        
        segment = {
            "location": best_loc.get("base") if best_loc else None,
            "location_surface": best_loc.get("surface") if best_loc else None,
            "poi": concept,
            "poi_surface": poi.get("surface", ""),
            "source": poi_resolved.source,
            "confidence": float(poi_resolved.confidence),
            "osm_query": osm_query[0] if osm_query else {},
            "is_plural_normalized": singular_poi != poi_text,
        }
        
        segments.append(segment)
    
    return segments


def test_segment_extraction_v2():
    """Test fonksiyonu"""
    test_queries = [
        "Kadıköyde kafe Beşiktaşta kasap",
        "Küçükyalıda kafe",
        "Çınarda restaurant",
        "kafeler",  # Sadece çoğul
        "kasaplar",  # Sadece çoğul
        "Beşiktaşta kafeler",
    ]
    
    print("=" * 70)
    print("SEGMENT EXTRACTION V2 - TEST")
    print("=" * 70)
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"SORGU: {query}")
        print(f"{'='*60}")
        
        segments = extract_location_poi_segments(query, use_osm=True)
        
        print(f"TOPLAM SEGMENT: {len(segments)}")
        for i, seg in enumerate(segments):
            print(f"\n  Segment {i+1}:")
            print(f"    location: {seg['location']}")
            print(f"    poi: {seg['poi']}")
            print(f"    osm_query: {seg['osm_query']}")
            if seg.get('is_plural_normalized'):
                print(f"    (çoğul normalizasyonu uygulandı)")


if __name__ == "__main__":
    test_segment_extraction_v2()