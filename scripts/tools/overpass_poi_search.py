"""
overpass_poi_search.py - Overpass API ile POI Arama

BERT sorgular?n? Overpass API'ye �evirir ve ger�ek POI sonu�lar?n? d�nd�r�r.
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_RATE_LIMIT = 5.0  # Overpass rate limit art?r?ld? (saniye)

_last_request_time = 0.0

def overpass_query(query: str, timeout: int = 90) -> Optional[Dict]:
    """Overpass API'ye sorgu g�nderir."""
    global _last_request_time
    
    # Rate limiting - Overpass API 1 sorgu/saniye limitli
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < OVERPASS_RATE_LIMIT:
        wait_time = OVERPASS_RATE_LIMIT - elapsed
        print(f"[Overpass] Rate limit beklemesi: {wait_time:.1f}s")
        time.sleep(wait_time)
    
    try:
        resp = requests.post(
            OVERPASS_URL, 
            data={"data": query}, 
            timeout=timeout,
            headers={"User-Agent": "OpenRoutePlanner/1.0"}
        )
        resp.raise_for_status()
        _last_request_time = time.time()
        return resp.json()
    except Exception as e:
        print(f"[Overpass] Hata: {e}")
        return None

def build_osm_query(district_lat: float, district_lon: float, osm_tags: Dict, radius: int = 5000) -> str:
    """OSM tag'lerinden Overpass sorgusu oluşturur."""
    tag_parts = []
    for key, value in osm_tags.items():
        if key not in ("aliases", "location", "lat", "lon"):
            tag_parts.append(f'"{key}"="{value}"')
    
    if not tag_parts:
        return ""
    
    tags_str = "".join(f"[{t}]" for t in tag_parts)
    
    query = f"""
    [out:json][timeout:{60}];
    (
      node(tags)(around:{radius},{district_lat},{district_lon}){tags_str};
      way(tags)(around:{radius},{district_lat},{district_lon}){tags_str};
    );
    out center;
    """
    
    return query

def search_pois_by_district(
    district_name: str,
    district_lat: float,
    district_lon: float,
    osm_tags: Dict,
    limit: int = 20
) -> List[Dict]:
    """Bir il�edeki POI'leri arar."""
    
    # Overpass sorgusu oluştur
    overpass_query_str = build_osm_query(district_lat, district_lon, osm_tags)
    
    if not overpass_query_str:
        return []
    
    # Sorgula
    result = overpass_query(overpass_query_str)
    
    if not result:
        return []
    
    pois = []
    for elem in result.get("elements", [])[:limit]:
        tags = elem.get("tags", {})
        
        # Koordinat al
        if "center" in elem:
            lat = elem["center"]["lat"]
            lon = elem["center"]["lon"]
        else:
            lat = elem.get("lat")
            lon = elem.get("lon")
        
        if lat and lon:
            pois.append({
                "name": tags.get("name", "?simsiz"),
                "lat": lat,
                "lon": lon,
                "type": tags.get("amenity") or tags.get("shop") or tags.get("leisure") or "other",
                "osm_id": elem.get("id"),
                "tags": tags,
            })
    
    return pois

def search_pois_by_city(city: str, osm_tags: Dict, limit: int = 50) -> List[Dict]:
    """Bir şehirdeki POI'leri arar (lokasyon belirtilmediyse)."""
    
    # ?stanbul koordinatlar?
    istanbul_center = {"lat": 41.0082, "lon": 28.9784}
    
    tag_parts = []
    for key, value in osm_tags.items():
        if key not in ("aliases", "location", "lat", "lon"):
            tag_parts.append(f'"{key}"="{value}"')
    
    if not tag_parts:
        return []
    
    tags_str = "".join(f"[{t}]" for t in tag_parts)
    
    query = f"""
    [out:json][timeout:90];
    area["name:tr"="?stanbul"]->.istanbul;
    (
      node["name"](area.istanbul){tags_str};
      way["name"](area.istanbul){tags_str};
    );
    out center;
    """
    
    result = overpass_query(query)
    
    if not result:
        return []
    
    pois = []
    for elem in result.get("elements", [])[:limit]:
        tags = elem.get("tags", {})
        
        if "center" in elem:
            lat = elem["center"]["lat"]
            lon = elem["center"]["lon"]
        else:
            lat = elem.get("lat")
            lon = elem.get("lon")
        
        if lat and lon:
            pois.append({
                "name": tags.get("name", "?simsiz"),
                "lat": lat,
                "lon": lon,
                "type": tags.get("amenity") or tags.get("shop") or tags.get("leisure") or "other",
                "osm_id": elem.get("id"),
                "tags": tags,
            })
    
    return pois


class OverpassPOISearch:
    """Overpass API ile POI arama motoru."""
    
    def __init__(self):
        self.rate_limit = OVERPASS_RATE_LIMIT
        print("[OverpassPOI] Motor haz?r")
    
    def search(self, segment: Dict, limit: int = 20) -> List[Dict]:
        """
        Segment'teki bilgilere g�re POI arar.
        
        Args:
            segment: {
                "location": "kad?k�y",
                "location_data": {"lat": 40.99, "lon": 29.03},
                "poi": "kafe",
                "osm_tags": {"amenity": "cafe"}
            }
            limit: Maksimum sonu�
            
        Returns:
            POI listesi
        """
        location_data = segment.get("location_data", {})
        osm_tags = segment.get("osm_tags", {})
        
        lat = location_data.get("lat")
        lon = location_data.get("lon")
        
        if lat and lon:
            # ?l�e bazl? arama
            return search_pois_by_district(
                segment.get("location", ""),
                lat, lon,
                osm_tags,
                limit
            )
        else:
            # Şehir bazl? arama (lokasyon belirtilmediyse)
            return search_pois_by_city("istanbul", osm_tags, limit)
    
    def search_multi_segments(self, segments: List[Dict], limit_per_segment: int = 20) -> Dict[int, List[Dict]]:
        """Birden fazla segment i�in POI arar."""
        results = {}
        
        for i, segment in enumerate(segments):
            pois = self.search(segment, limit_per_segment)
            results[i] = pois
            time.sleep(self.rate_limit)  # Rate limiting
        
        return results


def test_overpass_search():
    """Test."""
    print("=" * 60)
    print("OVERPASS POI ARAMA TEST")
    print("=" * 60)
    
    from bert_istanbul_integration import IstanbulBERTEngine
    
    engine = IstanbulBERTEngine()
    searcher = OverpassPOISearch()
    
    test_queries = [
        "Kad?k�yde kafe",
        "Beşiktaşta bar",
        "kafeler",  # Lokasyon yok
    ]
    
    for query in test_queries:
        print(f"\n--- {query} ---")
        
        result = engine.parse(query)
        
        if result["success"]:
            for i, segment in enumerate(result["segments"]):
                print(f"\n  Segment {i+1}: {segment['location']} - {segment['poi']}")
                
                # Overpass aramas?
                pois = searcher.search(segment, limit=5)
                
                if pois:
                    print(f"    → {len(pois)} POI bulundu:")
                    for poi in pois[:5]:
                        print(f"      - {poi['name']} ({poi['type']})")
                        print(f"        Lat: {poi['lat']:.6f}, Lon: {poi['lon']:.6f}")
                else:
                    print(f"    → POI bulunamad?")


if __name__ == "__main__":
    test_overpass_search()