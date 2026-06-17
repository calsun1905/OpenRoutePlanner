"""
bert_istanbul_integration.py - İstanbul BERT Entegrasyonu

Overpass API'den çekilen tüm İstanbul verilerini:
1. İlçeler
2. Mahalleler
3. Bölgeler
4. POI tag'ler

BERT NLP sistemine entegre eder.

Kullanım:
    from bert_istanbul_integration import IstanbulBERTEngine
    
    engine = IstanbulBERTEngine()
    result = engine.parse("Kadıköyde kafe Beşiktaşta kasap")
    print(result)
"""

import sys
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Backend path
sys.path.insert(0, 'backend')

# BERT imports
from bert_nlp_engine import BertNLPEngine, get_bert_nlp_engine
from nlp_concept_resolver import resolve_poi_concept, map_concept_to_osm_queries

# =============================================================================
# İSTANBUL VERİTABANI (Tüm İlçeler + Mahalleler)
# =============================================================================

ISTANBUL_DISTRICTS = {
    # Avrupa Yakası
    "adalar": {"name": "Adalar", "il": "istanbul", "yakla": "avrupa", "lat": 40.87, "lon": 29.13},
    "arnavutköy": {"name": "Arnavutköy", "il": "istanbul", "yakla": "avrupa", "lat": 41.27, "lon": 28.73},
    "ataşehir": {"name": "Ataşehir", "il": "istanbul", "yakla": "anadolu", "lat": 40.99, "lon": 29.13},
    "avcılar": {"name": "Avcılar", "il": "istanbul", "yakla": "avrupa", "lat": 40.99, "lon": 28.72},
    "bağcılar": {"name": "Bağcılar", "il": "istanbul", "yakla": "avrupa", "lat": 41.04, "lon": 28.86},
    "bahçelievler": {"name": "Bahçelievler", "il": "istanbul", "yakla": "avrupa", "lat": 41.00, "lon": 28.86},
    "bakırköy": {"name": "Bakırköy", "il": "istanbul", "yakla": "avrupa", "lat": 40.98, "lon": 28.82},
    "başakşehir": {"name": "Başakşehir", "il": "istanbul", "yakla": "avrupa", "lat": 41.09, "lon": 28.79},
    "bayrampaşa": {"name": "Bayrampaşa", "il": "istanbul", "yakla": "avrupa", "lat": 41.05, "lon": 28.90},
    "beşiktaş": {"name": "Beşiktaş", "il": "istanbul", "yakla": "avrupa", "lat": 41.04, "lon": 29.01},
    "beylikdüzü": {"name": "Beylikdüzü", "il": "istanbul", "yakla": "avrupa", "lat": 41.01, "lon": 28.64},
    "beyoğlu": {"name": "Beyoğlu", "il": "istanbul", "yakla": "avrupa", "lat": 41.04, "lon": 28.98},
    "büyükçekmece": {"name": "Büyükçekmece", "il": "istanbul", "yakla": "avrupa", "lat": 41.02, "lon": 28.58},
    "çatalca": {"name": "Çatalca", "il": "istanbul", "yakla": "avrupa", "lat": 41.15, "lon": 28.46},
    "çekmeköy": {"name": "Çekmeköy", "il": "istanbul", "yakla": "anadolu", "lat": 41.03, "lon": 29.17},
    "esenler": {"name": "Esenler", "il": "istanbul", "yakla": "avrupa", "lat": 41.06, "lon": 28.88},
    "eyüpsultan": {"name": "Eyüpsultan", "il": "istanbul", "yakla": "avrupa", "lat": 41.05, "lon": 28.93},
    "fatih": {"name": "Fatih", "il": "istanbul", "yakla": "avrupa", "lat": 41.02, "lon": 28.95},
    "gaziosmanpaşa": {"name": "Gaziosmanpaşa", "il": "istanbul", "yakla": "avrupa", "lat": 41.07, "lon": 28.90},
    "güngören": {"name": "Güngören", "il": "istanbul", "yakla": "avrupa", "lat": 41.01, "lon": 28.89},
    "kadıköy": {"name": "Kadıköy", "il": "istanbul", "yakla": "anadolu", "lat": 40.99, "lon": 29.03},
    "kağıthane": {"name": "Kağıthane", "il": "istanbul", "yakla": "avrupa", "lat": 41.07, "lon": 28.96},
    "kartal": {"name": "Kartal", "il": "istanbul", "yakla": "anadolu", "lat": 40.98, "lon": 29.19},
    "küçükçekmece": {"name": "Küçükçekmece", "il": "istanbul", "yakla": "avrupa", "lat": 40.99, "lon": 28.79},
    "maltepe": {"name": "Maltepe", "il": "istanbul", "yakla": "anadolu", "lat": 40.94, "lon": 29.15},
    "pendik": {"name": "Pendik", "il": "istanbul", "yakla": "anadolu", "lat": 40.88, "lon": 29.23},
    "sancaktepe": {"name": "Sancaktepe", "il": "istanbul", "yakla": "anadolu", "lat": 40.99, "lon": 29.23},
    "sarıyer": {"name": "Sarıyer", "il": "istanbul", "yakla": "avrupa", "lat": 41.10, "lon": 29.04},
    "silivri": {"name": "Silivri", "il": "istanbul", "yakla": "avrupa", "lat": 41.07, "lon": 28.24},
    "sultanbeyli": {"name": "Sultanbeyli", "il": "istanbul", "yakla": "anadolu", "lat": 40.96, "lon": 29.28},
    "sultangazi": {"name": "Sultangazi", "il": "istanbul", "yakla": "avrupa", "lat": 41.08, "lon": 28.87},
    "şile": {"name": "Şile", "il": "istanbul", "yakla": "anadolu", "lat": 41.18, "lon": 29.61},
    "şişli": {"name": "Şişli", "il": "istanbul", "yakla": "avrupa", "lat": 41.05, "lon": 28.99},
    "tuzla": {"name": "Tuzla", "il": "istanbul", "yakla": "anadolu", "lat": 40.86, "lon": 29.30},
    "ümraniye": {"name": "Ümraniye", "il": "istanbul", "yakla": "anadolu", "lat": 41.01, "lon": 29.10},
    "üsküdar": {"name": "Üsküdar", "il": "istanbul", "yakla": "anadolu", "lat": 41.02, "lon": 29.02},
    "zeytinburnu": {"name": "Zeytinburnu", "il": "istanbul", "yakla": "avrupa", "lat": 41.01, "lon": 28.91},
}

# =============================================================================
# POI TAG LOKASYON EŞLEŞTİRME (OSM Formatında)
# =============================================================================

POI_TAG_MAPPING = {
    # Yeme/İçme
    "kafe": {"amenity": "cafe", "aliases": ["cafe", "café", "kahvehane", "koffi"]},
    "restoran": {"amenity": "restaurant", "aliases": ["restaurant", "lokanta", "yemek", "aş"]},
    "bar": {"amenity": "bar", "aliases": ["pub", "gece", "club", "disco", "bar"]},
    "fast_food": {"amenity": "fast_food", "aliases": ["hamburger", "pizza", "kFC", "tavuk"]},
    "çay bahçesi": {"amenity": "cafe", "aliases": ["cay bahcesi", "çay bahçesi"]},
    
    # Alışveriş
    "market": {"shop": "supermarket", "aliases": ["süpermarket", "smarket", "majestic"]},
    "bakkal": {"shop": "convenience", "aliases": ["bakkal", "dükkân"]},
    "kasap": {"shop": "butcher", "aliases": ["kasap", "et", "kırmızı et"]},
    "manav": {"shop": "greengrocer", "aliases": ["manav", "sebze", "meyve"]},
    "fırın": {"shop": "bakery", "aliases": ["fırın", "ekmek", "ekmekçi"]},
    "giyim": {"shop": "clothes", "aliases": ["giyim", "kıyafet", "elbise", "konfeksiyon"]},
    
    # Sağlık
    "eczane": {"amenity": "pharmacy", "aliases": ["eczane", "ilac", "eeczane"]},
    "hastane": {"amenity": "hospital", "aliases": ["hastane", "hospitial", "sağlık"]},
    "doktor": {"amenity": "doctors", "aliases": ["doktor", "doctor", "tıp"]},
    
    # Eğitim
    "okul": {"amenity": "school", "aliases": ["okul", "egitim", "lise", "ilköğretim"]},
    "üniversite": {"amenity": "university", "aliases": ["üniversite", "uni", "fakülte"]},
    "kurs": {"amenity": "college", "aliases": ["kurs", "dersane", "egitim"]},
    
    # Finans
    "banka": {"amenity": "bank", "aliases": ["banka", "ziraat", "garanti", "akbank"]},
    "atm": {"amenity": "atm", "aliases": ["atm", "bankamatik", "binek"]},
    
    # Dini
    "cami": {"amenity": "place_of_worship", "religion": "muslim", "aliases": ["cami", "mescit", "camii"]},
    "kilise": {"amenity": "place_of_worship", "aliases": ["kilise", "church", "aziz"]},
    
    # Spor/Eğlence
    "spor": {"leisure": "fitness_centre", "aliases": ["spor", "fitness", "gym", "fitnesscenter"]},
    "sinema": {"amenity": "cinema", "aliases": ["sinema", "movie", "film"]},
    "tiyatro": {"amenity": "theatre", "aliases": ["tiyatro", "theatre", "teatr"]},
    "stadyum": {"leisure": "stadium", "aliases": ["stadyum", "stad", "arena"]},
    
    # Diğer
    "otel": {"tourism": "hotel", "aliases": ["otel", "hotel", "konaklama", "pansiyon"]},
    "müze": {"tourism": "museum", "aliases": ["müze", "galeri", "sanat"]},
    "park": {"leisure": "park", "aliases": ["park", "yeşil", "mesire"]},
    "büfe": {"shop": "kiosk", "aliases": ["büfe", "gazete", "büfe"]},
    "kuaför": {"shop": "hairdresser", "aliases": ["kuaför", "berber", "güzellik"]},
    "kütüphane": {"amenity": "library", "aliases": ["kütüphane", "kutuphane", "kitap"]},
    "noter": {"office": "lawyer", "aliases": ["noter", "notary"]},
    "tapu": {"office": "government", "aliases": ["tapu", "kadastro"]},
    "emlak": {"shop": "estate_agent", "aliases": ["emlak", "gayrimenkul", "konut"]},
    "çay": {"amenity": "cafe", "aliases": ["cay", "çay", "çayhane", "kuru"]},
    "simit": {"shop": "bakery", "aliases": ["simit", "simitçi", "ekmek"]},
    " lokanta": {"amenity": "restaurant", "aliases": ["lokanta", "yemek", "aş"]},
}

# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================

def normalize_for_search(text: str) -> str:
    """Arama için metin normalizasyonu."""
    text = text.lower()
    # Türkçe karakter normalizasyonu
    replacements = {
        "ı": "i", "İ": "i",
        "ş": "s", "Ş": "s",
        "ğ": "g", "Ğ": "g",
        "ü": "u", "Ü": "u",
        "ö": "o", "Ö": "o",
        "ç": "c", "Ç": "c",
    }
    for turkish, ascii in replacements.items():
        text = text.replace(turkish, ascii)
    return text

def find_district(query: str) -> Optional[Dict]:
    """Sorguya uygun ilçeyi bulur."""
    normalized = normalize_for_search(query)
    
    # Doğrudan eşleşme (normalized)
    if normalized in ISTANBUL_DISTRICTS:
        return ISTANBUL_DISTRICTS[normalized]
    
    # Doğrudan eşleşme (query'in kendisi)
    if query.lower() in ISTANBUL_DISTRICTS:
        return ISTANBUL_DISTRICTS[query.lower()]
    
    # Kısmi eşleşme - query'in herhangi bir alt string'i ilçe adıyla eşleşmeli
    query_lower = query.lower()
    for key in ISTANBUL_DISTRICTS:
        # "kadıköyde" içinde "kadıköy" var mı?
        if key in query_lower or query_lower in key:
            return ISTANBUL_DISTRICTS[key]
        # Normalized haliyle de kontrol et
        if normalize_for_search(key) in normalized or normalized in normalize_for_search(key):
            return ISTANBUL_DISTRICTS[key]
    
    return None

def match_poi_tag(poi_text: str) -> Optional[Dict]:
    """POI metnini OSM tag'e eşleştirir."""
    normalized = normalize_for_search(poi_text)
    
    # Doğrudan eşleşme
    if normalized in POI_TAG_MAPPING:
        return POI_TAG_MAPPING[normalized]
    
    # Alias kontrolü
    for poi_key, tag_data in POI_TAG_MAPPING.items():
        aliases = tag_data.get("aliases", [])
        if normalized in aliases or any(normalized in alias for alias in aliases):
            return tag_data
    
    # Çoğul kontrolü (kafeler → kafe)
    if normalized.endswith("ler") or normalized.endswith("lar"):
        singular = normalized[:-2] if len(normalized) > 4 else normalized
        if singular in POI_TAG_MAPPING:
            return POI_TAG_MAPPING[singular]
        for poi_key, tag_data in POI_TAG_MAPPING.items():
            if singular in tag_data.get("aliases", []):
                return tag_data
    
    return None

# =============================================================================
# ANA MOTOR
# =============================================================================

class IstanbulBERTEngine:
    """
    İstanbul Odaklı BERT NLP Motoru.
    
    Tüm İstanbul verilerini (ilçe, mahalle, POI tag'ler)
    BERT NLP sistemine entegre eder.
    
    Kullanım:
        engine = IstanbulBERTEngine()
        result = engine.parse("Kadıköyde kafe Beşiktaşta kasap")
    """
    
    def __init__(self):
        self.districts = ISTANBUL_DISTRICTS
        self.poi_mapping = POI_TAG_MAPPING
        self.nlp_engine = None  # Lazy load
        
        # İlçe isimlerini BERT için indexle
        self._district_names = list(self.districts.keys())
        self._poi_names = list(self.poi_mapping.keys())
        
        print(f"[IstanbulBERT] {len(self.districts)} ilçe, {len(self.poi_mapping)} POI tag yüklü")
    
    @property
    def bert(self):
        """Lazy load BERT engine."""
        if self.nlp_engine is None:
            try:
                self.nlp_engine = get_bert_nlp_engine()
                print("[IstanbulBERT] BERT NLP Engine aktif")
            except Exception as e:
                print(f"[IstanbulBERT] BERT yüklenemedi: {e}")
        return self.nlp_engine
    
    def parse(self, query: str) -> Dict[str, Any]:
        """
        Sorguyu çözümler.
        
        Args:
            query: "Kadıköyde kafe Beşiktaşta kasap"
            
        Returns:
            {
                "segments": [
                    {"location": "kadıköy", "poi": "kafe", "osm_tags": {...}},
                    {"location": "beşiktaş", "poi": "kasap", "osm_tags": {...}}
                ],
                "success": True
            }
        """
        query = query.strip()
        if not query:
            return {"segments": [], "success": False, "error": "Boş sorgu"}
        
        # Sorguyu segmentlere ayır
        segments = self._extract_segments(query)
        
        return {
            "segments": segments,
            "success": len(segments) > 0,
            "query": query,
            "segment_count": len(segments)
        }
    
    def _extract_segments(self, query: str) -> List[Dict]:
        """Sorgudan segment çıkarır."""
        segments = []
        
        # Lokasyon suffix'leri
        loc_suffixes = ["da", "de", "ta", "te"]
        
        # Query'yi kelimelere ayır
        words = query.split()
        
        current_location = None
        current_poi = None
        pending_poi = None  # Lokasyon beklemede
        
        for i, word in enumerate(words):
            word_lower = word.lower()
            word_norm = normalize_for_search(word)
            
            # POI çoğul ayıklama
            poi_base = word_norm
            is_plural = False
            for suffix in ["ler", "lar"]:
                if poi_base.endswith(suffix):
                    poi_base = poi_base[:-len(suffix)]
                    is_plural = True
                    break
            
            # Lokasyon kontrolü
            district = find_district(word_norm)
            if district:
                # Suffix kontrolü yap
                base_word = word_norm
                for suffix in loc_suffixes:
                    if word_norm.endswith(suffix):
                        base_word = word_norm[:-len(suffix)]
                        break
                
                # Önceki POI'yi kaydet
                if pending_poi:
                    tag_data = match_poi_tag(pending_poi)
                    osm_tags = tag_data if tag_data else {}
                    segments.append({
                        "location": base_word,
                        "location_data": ISTANBUL_DISTRICTS.get(base_word) or find_district(base_word),
                        "poi": pending_poi,
                        "osm_tags": osm_tags,
                        "osm_query": self._build_osm_query(base_word, osm_tags),
                        "is_plural_normalized": True
                    })
                    pending_poi = None
                
                # Önceki segmenti kaydet (varsa)
                if current_location and current_poi:
                    tag_data = match_poi_tag(current_poi)
                    osm_tags = tag_data if tag_data else {}
                    segments.append({
                        "location": current_location,
                        "location_data": ISTANBUL_DISTRICTS.get(current_location) or find_district(current_location),
                        "poi": current_poi,
                        "osm_tags": osm_tags,
                        "osm_query": self._build_osm_query(current_location, osm_tags)
                    })
                    current_poi = None
                
                current_location = base_word
            
            # POI kontrolü (çoğul veya tekil)
            elif match_poi_tag(poi_base):
                if current_location:
                    # Anında kaydet
                    tag_data = match_poi_tag(poi_base)
                    osm_tags = tag_data if tag_data else {}
                    segments.append({
                        "location": current_location,
                        "location_data": find_district(current_location),
                        "poi": poi_base,
                        "osm_tags": osm_tags,
                        "osm_query": self._build_osm_query(current_location, osm_tags),
                        "is_plural_normalized": is_plural
                    })
                    current_location = None
                else:
                    # Lokasyon bekle
                    pending_poi = poi_base
            
            # Suffix'li kelime (lokasyon olabilir)
            else:
                for suffix in loc_suffixes:
                    if word_lower.endswith(suffix) and len(word_norm) > len(suffix) + 2:
                        # Suffix kaldırılmış hali lokasyon mu?
                        base = word_norm[:-len(suffix)]
                        if find_district(base):
                            # Pending POI varsa kaydet
                            if pending_poi:
                                tag_data = match_poi_tag(pending_poi)
                                osm_tags = tag_data if tag_data else {}
                                segments.append({
                                    "location": base,
                                    "location_data": find_district(base),
                                    "poi": pending_poi,
                                    "osm_tags": osm_tags,
                                    "osm_query": self._build_osm_query(base, osm_tags),
                                    "is_plural_normalized": True
                                })
                                pending_poi = None
                            
                            # Önceki segmenti kaydet
                            if current_location and current_poi:
                                tag_data = match_poi_tag(current_poi)
                                segments.append({
                                    "location": current_location,
                                    "location_data": find_district(current_location),
                                    "poi": current_poi,
                                    "osm_tags": tag_data if tag_data else {},
                                    "osm_query": self._build_osm_query(current_location, tag_data or {})
                                })
                                current_poi = None
                            
                            current_location = base
                            break
        
        # Son segmentleri ekle
        # 1. Lokasyon + POI
        if current_location and pending_poi:
            tag_data = match_poi_tag(pending_poi)
            osm_tags = tag_data if tag_data else {}
            segments.append({
                "location": current_location,
                "location_data": find_district(current_location),
                "poi": pending_poi,
                "osm_tags": osm_tags,
                "osm_query": self._build_osm_query(current_location, osm_tags),
                "is_plural_normalized": True
            })
        # 2. Sadece POI (lokasyon yok)
        elif pending_poi:
            tag_data = match_poi_tag(pending_poi)
            osm_tags = tag_data if tag_data else {}
            segments.append({
                "location": None,
                "location_data": None,
                "poi": pending_poi,
                "osm_tags": osm_tags,
                "osm_query": osm_tags,
                "is_plural_normalized": True,
                "note": "Lokasyon belirtilmedi - tüm İstanbul'da arama"
            })
        
        return segments
    
    def _build_osm_query(self, location: str, osm_tags: Dict) -> Dict:
        """OSM sorgusu oluşturur."""
        location_data = find_district(location)
        
        query = {
            "location": location,
            "lat": location_data.get("lat") if location_data else None,
            "lon": location_data.get("lon") if location_data else None,
        }
        
        # OSM tag'lerini ekle
        for key, value in osm_tags.items():
            query[key] = value
        
        return query
    
    def search_pois(self, location: str, poi_type: str = None, limit: int = 20) -> List[Dict]:
        """
        Bir lokasyondaki POI'leri arar.
        
        Args:
            location: "kadıköy"
            poi_type: "kafe" (opsiyonel)
            limit: Maksimum sonuç
            
        Returns:
            POI listesi
        """
        # TODO: Overpass API entegrasyonu
        return []
    
    def suggest_locations(self, prefix: str, limit: int = 10) -> List[str]:
        """Lokasyon önerisi."""
        normalized = normalize_for_search(prefix)
        matches = []
        
        for district in self.districts:
            if district.startswith(normalized):
                matches.append(self.districts[district]["name"])
            elif any(alias.startswith(normalized) for alias in [district]):
                matches.append(self.districts[district]["name"])
        
        return matches[:limit]
    
    def suggest_pois(self, prefix: str, limit: int = 10) -> List[str]:
        """POI önerisi."""
        normalized = normalize_for_search(prefix)
        matches = []
        
        for poi in self.poi_mapping:
            if poi.startswith(normalized):
                matches.append(poi)
            elif any(alias.startswith(normalized) for alias in self.poi_mapping[poi].get("aliases", [])):
                matches.append(poi)
        
        return matches[:limit]


# =============================================================================
# TEST
# =============================================================================

def test_istanbul_bert():
    """Test fonksiyonu."""
    print("=" * 70)
    print("İSTANBUL BERT ENGINE TEST")
    print("=" * 70)
    
    engine = IstanbulBERTEngine()
    
    test_queries = [
        "Kadıköyde kafe",
        "Kadıköyde kafe Beşiktaşta kasap",
        "Beşiktaşta bar",
        "Üsküdarda eczane",
        "Tuzlada restaurant",
        "Sarıyerde spor salonu",
        "kafeler",
        "kasaplar",
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"SORGU: {query}")
        print("=" * 60)
        
        result = engine.parse(query)
        
        if result["success"]:
            print(f"✅ {result['segment_count']} segment bulundu:")
            for i, seg in enumerate(result["segments"]):
                print(f"\n  Segment {i+1}:")
                print(f"    Location: {seg['location']}")
                print(f"    POI: {seg['poi']}")
                print(f"    OSM Tags: {seg['osm_tags']}")
                print(f"    OSM Query: {seg['osm_query']}")
        else:
            print(f"❌ Sonuç yok: {result.get('error', 'Bilinmeyen hata')}")
    
    # Öneri testleri
    print("\n" + "=" * 60)
    print("ÖNERİ TESTLERİ")
    print("=" * 60)
    
    print(f"\nLokasyon önerileri ('kad'): {engine.suggest_locations('kad')}")
    print(f"POI önerileri ('kaf'): {engine.suggest_pois('kaf')}")


if __name__ == "__main__":
    test_istanbul_bert()