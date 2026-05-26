"""
nominatim_poi_search.py - Nominatim API ile POI Arama

Daha güvenilir Nominatim API kullanarak POI araması yapar.
Overpass rate limit sorunları için alternatif çözüm.
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_RATE_LIMIT = 1.0  # saniye

_last_request_time = 0.0

def nominatim_query(query: str, params: Dict = None) -> Optional[Dict]:
    """Nominatim API'ye sorgu gönderir."""
    global _last_request_time
    
    # Rate limiting
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < NOMINATIM_RATE_LIMIT:
        time.sleep(NOMINATIM_RATE_LIMIT - elapsed)
    
    try:
        default_params = {
            "format": "json",
            "addressdetails": 1,
            "limit": 10,
            "user_agent": "OpenRoutePlanner/1.0"
        }
        if params:
            default_params.update(params)
        
        resp = requests.get(NOMINATIM_URL, params=default_params, timeout=30)
        resp.raise_for_status()
        _last_request_time = time.time()
        return resp.json()
    except Exception as e:
        print(f"[Nominatim] Hata: {e}")
        return None

def nominatim_reverse(lat: float, lon: float) -> Optional[Dict]:
    """Koordinattan adres bilgisi alır."""
    global _last_request_time
    
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < NOMINATIM_RATE_LIMIT:
        time.sleep(NOMINATIM_RATE_LIMIT - elapsed)
    
    try:
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "addressdetails": 1,
            "user_agent": "OpenRoutePlanner/1.0"
        }
        resp = requests.get(NOMINATIM_REVERSE_URL, params=params, timeout=30)
        resp.raise_for_status()
        _last_request_time = time.time()
        return resp.json()
    except Exception as e:
        print(f"[Nominatim Reverse] Hata: {e}")
        return None


def search_pois_by_location(
    location_name: str,
    location_lat: float,
    location_lon: float,
    poi_type: str,
    osm_tag: str,
    osm_value: str,
    radius_km: float = 5.0,
    limit: int = 20
) -> List[Dict]:
    """Bir lokasyonun yakınındaki POI'leri arar."""
    
    # Nominatim ile POI araması
    search_query = f"{poi_type} near {location_name}, Istanbul, Turkey"
    
    params = {
        "q": search_query,
        "format": "json",
        "addressdetails": 1,
        "limit": limit,
    }
    
    results = nominatim_query(search_query, params)
    
    if not results:
        # Alternatif sorgu
        search_query = f"{poi_type} {location_name} Istanbul"
        results = nominatim_query(search_query, params)
    
    pois = []
    for item in results[:limit]:
        lat = float(item.get("lat", 0))
        lon = float(item.get("lon", 0))
        
        if lat and lon:
            # Mesafe kontrolü (km cinsinden)
            import math
            R = 6371  # Earth radius in km
            dlat = math.radians(lat - location_lat)
            dlon = math.radians(lon - location_lon)
            a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(location_lat)) * math.cos(math.radians(lat)) * math.sin(dlon/2) * math.sin(dlon/2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            distance = R * c
            
            if distance <= radius_km:
                address = item.get("address", {})
                
                pois.append({
                    "name": item.get("display_name", "İsimsiz"),
                    "lat": lat,
                    "lon": lon,
                    "distance_km": round(distance, 2),
                    "type": osm_value,
                    "osm_id": item.get("osm_id"),
                    "class": item.get("class"),
                    "icon": item.get("icon"),
                    "address": {
                        "city": address.get("city", address.get("town", address.get("village", ""))),
                        "district": address.get("suburb", address.get("neighbourhood", "")),
                        "street": address.get("road", ""),
                    }
                })
    
    # Mesafeye göre sırala
    pois.sort(key=lambda x: x.get("distance_km", 999))
    
    return pois

def search_pois_by_city(
    city: str,
    poi_type: str,
    osm_tag: str,
    osm_value: str,
    limit: int = 50
) -> List[Dict]:
    """Bir şehirdeki POI'leri arar (lokasyon belirtilmediyse)."""
    
    search_query = f"{poi_type} {city} Turkey"
    
    params = {
        "q": search_query,
        "format": "json",
        "addressdetails": 1,
        "limit": limit,
        "countrycodes": "tr",
    }
    
    results = nominatim_query(search_query, params)
    
    pois = []
    for item in results[:limit]:
        lat = float(item.get("lat", 0))
        lon = float(item.get("lon", 0))
        
        if lat and lon:
            address = item.get("address", {})
            
            pois.append({
                "name": item.get("display_name", "İsimsiz"),
                "lat": lat,
                "lon": lon,
                "type": osm_value,
                "osm_id": item.get("osm_id"),
                "class": item.get("class"),
                "address": {
                    "city": address.get("city", address.get("town", address.get("village", ""))),
                    "district": address.get("suburb", address.get("neighbourhood", "")),
                    "street": address.get("road", ""),
                }
            })
    
    return pois


class NominatimPOISearch:
    """Nominatim API ile POI arama motoru."""
    
    # POI type mapping
    POI_TYPES = {
        "kafe": ("cafe", "amenity", "cafe"),
        "restoran": ("restaurant", "amenity", "restaurant"),
        "bar": ("bar", "amenity", "bar"),
        "kasap": ("butcher", "shop", "butcher"),
        "manav": ("supermarket", "shop", "supermarket"),
        "market": ("supermarket", "shop", "supermarket"),
        "eczane": ("pharmacy", "amenity", "pharmacy"),
        "hastane": ("hospital", "amenity", "hospital"),
        "okul": ("school", "amenity", "school"),
        "banka": ("bank", "amenity", "bank"),
        "atm": ("atm", "amenity", "atm"),
        "park": ("park", "leisure", "park"),
        "spor": ("gym", "leisure", "fitness_centre"),
        "sinema": ("cinema", "amenity", "cinema"),
    }
    
    def __init__(self):
        self.rate_limit = NOMINATIM_RATE_LIMIT
        print("[NominatimPOI] Motor hazır")
    
    def search(self, segment: Dict, limit: int = 20) -> List[Dict]:
        """
        Segment'teki bilgilere göre POI arar.
        
        Args:
            segment: {
                "location": "kadıköy",
                "location_data": {"lat": 40.99, "lon": 29.03},
                "poi": "kafe",
                "osm_tags": {"amenity": "cafe"}
            }
            limit: Maksimum sonuç
            
        Returns:
            POI listesi
        """
        location_data = segment.get("location_data", {}) or {}
        osm_tags = segment.get("osm_tags", {}) or {}
        poi = segment.get("poi", "")
        location = segment.get("location", "")
        
        lat = location_data.get("lat")
        lon = location_data.get("lon")
        
        # OSM tag'lerini al
        osm_tag = None
        osm_value = None
        for key, value in osm_tags.items():
            if key not in ("aliases", "location", "lat", "lon"):
                osm_tag = key
                osm_value = value
                break
        
        poi_type = poi.replace("_", " ")
        
        if lat and lon:
            # İlçe bazlı arama
            return search_pois_by_location(
                location or "Istanbul",
                lat, lon,
                poi_type,
                osm_tag or "amenity",
                osm_value or poi,
                radius_km=5.0,
                limit=limit
            )
        else:
            # Şehir bazlı arama
            return search_pois_by_city(
                "Istanbul",
                poi_type,
                osm_tag or "amenity",
                osm_value or poi,
                limit=limit
            )


def test_nominatim_search():
    """Test."""
    print("=" * 60)
    print("NOMINATIM POI ARAMA TEST")
    print("=" * 60)
    
    from bert_istanbul_integration import IstanbulBERTEngine
    
    engine = IstanbulBERTEngine()
    searcher = NominatimPOISearch()
    
    test_queries = [
        "Kadıköyde kafe",
        "Beşiktaşta bar",
        "kafeler",  # Lokasyon yok
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"SORGU: {query}")
        print("="*50)
        
        result = engine.parse(query)
        
        if result["success"]:
            for i, segment in enumerate(result["segments"]):
                print(f"\n  Segment {i+1}: {segment['location']} - {segment['poi']}")
                
                # Nominatim araması
                pois = searcher.search(segment, limit=5)
                
                if pois:
                    print(f"    ✅ {len(pois)} POI bulundu:")
                    for poi in pois[:5]:
                        dist = poi.get("distance_km", "")
                        dist_str = f" ({dist}km)" if dist else ""
                        print(f"      📍 {poi['name']}{dist_str}")
                        addr = poi.get("address", {})
                        if addr.get("district"):
                            print(f"         📌 {addr['district']}")
                else:
                    print(f"    ❌ POI bulunamadı")
        else:
            print(f"  ❌ Parseleme hatası")


if __name__ == "__main__":
    test_nominatim_search()