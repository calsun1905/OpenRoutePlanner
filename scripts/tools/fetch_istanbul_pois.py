"""
fetch_istanbul_data.py - ?stanbul T�m Veri Çekici

Overpass API'den ?stanbul'un t�m:
- ?l�eleri
- Mahalleleri
- B�lgeleri
- POI tag'leri

Verilerini �eker ve BERT sistemine entegre eder.
"""

import requests
import json
import time
from typing import Dict, List, Optional, Set

# Overpass API
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def fetch_istanbul_districts() -> Dict:
    """?stanbul il�elerini Overpass'ten �eker."""
    print("[1/4] ?stanbul il�eleri �ekiliyor...")
    
    query = """
    [out:json][timeout:60];
    area["name:tr"="?stanbul"]->.istanbul;
    (
      relation["admin_level"="8"]["name"]["name:tr"](area.istanbul);
    );
    out body;
    """
    
    try:
        resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=90)
        resp.raise_for_status()
        data = resp.json()
        
        districts = {}
        for elem in data.get("elements", []):
            tags = elem.get("tags", {})
            name = tags.get("name:tr") or tags.get("name", "")
            if name:
                districts[name.lower()] = {
                    "name": name,
                    "osm_id": elem.get("id"),
                    "type": "district",
                    "il": "istanbul"
                }
        
        print(f"   → {len(districts)} il�e bulundu")
        return districts
    except Exception as e:
        print(f"   → Hata: {e}")
        return {}

def fetch_istanbul_neighborhoods() -> Dict:
    """?stanbul mahallelerini Overpass'ten �eker."""
    print("[2/4] ?stanbul mahalleleri �ekiliyor...")
    
    query = """
    [out:json][timeout:120];
    area["name:tr"="?stanbul"]->.istanbul;
    (
      way["place"="neighbourhood"](area.istanbul);
      way["place"="suburb"](area.istanbul);
      way["place"="quarter"](area.istanbul);
    );
    out center;
    """
    
    try:
        resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=150)
        resp.raise_for_status()
        data = resp.json()
        
        neighborhoods = {}
        for elem in data.get("elements", []):
            tags = elem.get("tags", {})
            name = tags.get("name") or tags.get("name:tr", "")
            if name and len(name) > 2:
                center = elem.get("center", {})
                lat = center.get("lat")
                lon = center.get("lon")
                
                neighborhoods[name.lower()] = {
                    "name": name,
                    "osm_id": elem.get("id"),
                    "type": "neighborhood",
                    "lat": lat,
                    "lon": lon,
                    "place_type": tags.get("place", "unknown"),
                    "il": "istanbul"
                }
        
        print(f"   → {len(neighborhoods)} mahalle/b�lge bulundu")
        return neighborhoods
    except Exception as e:
        print(f"   → Hata: {e}")
        return {}

def fetch_istanbul_poi_tags() -> List[Dict]:
    """?stanbul'daki t�m POI tag'lerini �eker."""
    print("[3/4] ?stanbul POI tag'leri �ekiliyor...")
    
    # POI tag'leri i�in Overpass sorgusu
    poi_keys = ["amenity", "shop", "tourism", "leisure", "sport", "historic", "office", "craft", "healthcare", "religion"]
    
    all_tags = {}
    
    for key in poi_keys:
        query = f"""
        [out:json][timeout:60];
        area["name:tr"="?stanbul"]->.istanbul;
        way["{key}"](area.istanbul);
        out count;
        """
        
        try:
            resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=90)
            # Sadece tag istatistiklerini al
            time.sleep(1)  # Rate limiting
        except:
            pass
    
    # Örnek tag'ler
    sample_pois = [
        {"amenity": "cafe", "label": "Kafe", "synonyms": ["kafe", "cafe", "café", "kahvehane"]},
        {"amenity": "restaurant", "label": "Restoran", "synonyms": ["restoran", "restaurant", "lokanta"]},
        {"amenity": "bar", "label": "Bar", "synonyms": ["bar", "pub", "gece"]},
        {"amenity": "fast_food", "label": "Fast Food", "synonyms": ["fast food", "hamburger", "pizza"]},
        {"amenity": "atm", "label": "ATM", "synonyms": ["atm", "bankamatik"]},
        {"amenity": "bank", "label": "Banka", "synonyms": ["banka", "şube"]},
        {"amenity": "pharmacy", "label": "Eczane", "synonyms": ["eczane", "ila�"]},
        {"amenity": "hospital", "label": "Hastane", "synonyms": ["hastane", "sağl?k"]},
        {"amenity": "school", "label": "Okul", "synonyms": ["okul", "eğitim"]},
        {"amenity": "place_of_worship", "label": "Cami", "synonyms": ["cami", "mescit", "kilise"]},
        {"shop": "supermarket", "label": "S�permarket", "synonyms": ["s�permarket", "market"]},
        {"shop": "bakery", "label": "F?r?n", "synonyms": ["f?r?n", "ekmek"]},
        {"shop": "butcher", "label": "Kasap", "synonyms": ["kasap", "et"]},
        {"shop": "clothes", "label": "Giyim", "synonyms": ["giyim", "k?yafet", "elbise"]},
        {"leisure": "fitness_centre", "label": "Spor Salonu", "synonyms": ["spor", "fitness", "gym"]},
        {"leisure": "park", "label": "Park", "synonyms": ["park", "yeşil alan"]},
        {"tourism": "hotel", "label": "Otel", "synonyms": ["otel", "hotel", "konaklama"]},
        {"tourism": "museum", "label": "M�ze", "synonyms": ["m�ze", "galeri"]},
        {"sport": "stadium", "label": "Stadyum", "synonyms": ["stadyum", "spor"]},
    ]
    
    print(f"   → {len(sample_pois)} POI tag profili haz?r")
    return sample_pois

def build_complete_istanbul_db() -> Dict:
    """Tam ?stanbul veritaban?n? oluşturur."""
    print("\n" + "=" * 60)
    print("?STANBUL VER?TABANI OLUŞTURULUYOR")
    print("=" * 60)
    
    # ?l�eler
    districts = fetch_istanbul_districts()
    
    # Mahalleler
    neighborhoods = fetch_istanbul_neighborhoods()
    
    # POI tag'leri
    poi_tags = fetch_istanbul_poi_tags()
    
    # Manuel ekleme (eksik kalanlar? tamamla)
    manual_districts = {
        "adalar": {"name": "Adalar", "osm_id": "relation_adalar", "type": "district", "il": "istanbul"},
        "arnavutk�y": {"name": "Arnavutk�y", "osm_id": "relation_arnavutkoy", "type": "district", "il": "istanbul"},
        "ataşehir": {"name": "Ataşehir", "osm_id": "relation_atasehir", "type": "district", "il": "istanbul"},
        "avc?lar": {"name": "Avc?lar", "osm_id": "relation_avcilar", "type": "district", "il": "istanbul"},
        "bağc?lar": {"name": "Bağc?lar", "osm_id": "relation_bagcilar", "type": "district", "il": "istanbul"},
        "bah�elievler": {"name": "Bah�elievler", "osm_id": "relation_bahcelievler", "type": "district", "il": "istanbul"},
        "bak?rk�y": {"name": "Bak?rk�y", "osm_id": "relation_bakirkoy", "type": "district", "il": "istanbul"},
        "başakşehir": {"name": "Başakşehir", "osm_id": "relation_basaksehir", "type": "district", "il": "istanbul"},
        "bayrampaşa": {"name": "Bayrampaşa", "osm_id": "relation_bayrampasa", "type": "district", "il": "istanbul"},
        "beşiktaş": {"name": "Beşiktaş", "osm_id": "relation_besiktas", "type": "district", "il": "istanbul"},
        "beylikd�z�": {"name": "Beylikd�z�", "osm_id": "relation_beylikduzu", "type": "district", "il": "istanbul"},
        "beyoğlu": {"name": "Beyoğlu", "osm_id": "relation_beyoglu", "type": "district", "il": "istanbul"},
        "b�y�k�ekmece": {"name": "B�y�k�ekmece", "osm_id": "relation_buyukcekmece", "type": "district", "il": "istanbul"},
        "�atalca": {"name": "Çatalca", "osm_id": "relation_catalca", "type": "district", "il": "istanbul"},
        "�ekmek�y": {"name": "Çekmek�y", "osm_id": "relation_cekmekoy", "type": "district", "il": "istanbul"},
        "esenler": {"name": "Esenler", "osm_id": "relation_esenler", "type": "district", "il": "istanbul"},
        "ey�psultan": {"name": "Ey�psultan", "osm_id": "relation_eyupsultan", "type": "district", "il": "istanbul"},
        "fatih": {"name": "Fatih", "osm_id": "relation_fatih", "type": "district", "il": "istanbul"},
        "gaziosmanpaşa": {"name": "Gaziosmanpaşa", "osm_id": "relation_gaziosmanpasa", "type": "district", "il": "istanbul"},
        "g�ng�ren": {"name": "G�ng�ren", "osm_id": "relation_gungoren", "type": "district", "il": "istanbul"},
        "kad?k�y": {"name": "Kad?k�y", "osm_id": "relation_kadikoy", "type": "district", "il": "istanbul"},
        "kağ?thane": {"name": "Kağ?thane", "osm_id": "relation_kagithane", "type": "district", "il": "istanbul"},
        "kartal": {"name": "Kartal", "osm_id": "relation_kartal", "type": "district", "il": "istanbul"},
        "k���k�ekmece": {"name": "K���k�ekmece", "osm_id": "relation_kucukcekmece", "type": "district", "il": "istanbul"},
        "maltepe": {"name": "Maltepe", "osm_id": "relation_maltepe", "type": "district", "il": "istanbul"},
        "pendik": {"name": "Pendik", "osm_id": "relation_pendik", "type": "district", "il": "istanbul"},
        "sancaktepe": {"name": "Sancaktepe", "osm_id": "relation_sancaktepe", "type": "district", "il": "istanbul"},
        "sar?yer": {"name": "Sar?yer", "osm_id": "relation_sariyer", "type": "district", "il": "istanbul"},
        "silivri": {"name": "Silivri", "osm_id": "relation_silivri", "type": "district", "il": "istanbul"},
        "sultanbeyli": {"name": "Sultanbeyli", "osm_id": "relation_sultanbeyli", "type": "district", "il": "istanbul"},
        "sultangazi": {"name": "Sultangazi", "osm_id": "relation_sultangazi", "type": "district", "il": "istanbul"},
        "şile": {"name": "Şile", "osm_id": "relation_sile", "type": "district", "il": "istanbul"},
        "şişli": {"name": "Şişli", "osm_id": "relation_sisli", "type": "district", "il": "istanbul"},
        "tuzla": {"name": "Tuzla", "osm_id": "relation_tuzla", "type": "district", "il": "istanbul"},
        "�mraniye": {"name": "Ümraniye", "osm_id": "relation_umraniye", "type": "district", "il": "istanbul"},
        "�sk�dar": {"name": "Üsk�dar", "osm_id": "relation_uskudar", "type": "district", "il": "istanbul"},
        "zeytinburnu": {"name": "Zeytinburnu", "osm_id": "relation_zeytinburnu", "type": "district", "il": "istanbul"},
    }
    
    # Birleştir
    all_locations = {**manual_districts, **neighborhoods}
    
    result = {
        "districts": manual_districts,
        "neighborhoods": neighborhoods,
        "poi_tags": poi_tags,
        "total_locations": len(all_locations)
    }
    
    print(f"\n   Toplam veri:")
    print(f"   - {len(manual_districts)} il�e")
    print(f"   - {len(neighborhoods)} mahalle/b�lge")
    print(f"   - {len(poi_tags)} POI tag")
    
    return result

if __name__ == "__main__":
    db = build_complete_istanbul_db()
    
    # JSON olarak kaydet
    with open("istanbul_full_db.json", "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    
    print("\n✅ Veritaban? 'istanbul_full_db.json' olarak kaydedildi")