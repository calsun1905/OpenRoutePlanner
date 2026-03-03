"""
location_storage.py - Kullanıcı Lokasyon Kaydetme ve Yükleme Sistemi

Kullanıcıların harita üzerinden özel isimlerle ("Ev", "Okul", vb.)
konum kaydetmesini ve bu listeyi yönetmesini sağlar.
JSON dosya tabanlı basit depolama sistemi.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional


# Kaydedilen lokasyonların saklanacağı dosya
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "data")
LOCATIONS_FILE = os.path.join(STORAGE_DIR, "saved_locations.json")


def _ensure_storage_exists():
    """Depolama klasörünü ve dosyasını oluşturur."""
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR)
        print(f"[LocationStorage] Depolama klasörü oluşturuldu: {STORAGE_DIR}")
    
    if not os.path.exists(LOCATIONS_FILE):
        with open(LOCATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        print(f"[LocationStorage] Lokasyon dosyası oluşturuldu: {LOCATIONS_FILE}")


def _load_locations() -> List[Dict]:
    """Tüm kaydedilmiş lokasyonları yükler."""
    _ensure_storage_exists()
    
    try:
        with open(LOCATIONS_FILE, "r", encoding="utf-8") as f:
            locations = json.load(f)
        return locations
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _save_locations(locations: List[Dict]):
    """Lokasyonları dosyaya kaydeder."""
    _ensure_storage_exists()
    
    with open(LOCATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(locations, f, ensure_ascii=False, indent=2)


def save_location(
    name: str,
    lat: float,
    lon: float,
    icon_type: str = "star",
    address: str = ""
) -> Dict:
    """
    Yeni bir lokasyon kaydeder.
    
    Args:
        name: Lokasyon adı (örn: "Ev", "Spor Salonu")
        lat: Enlem
        lon: Boylam
        icon_type: İkon tipi (home, work, school, gym, market, star vb.)
        address: Açık adres (opsiyonel)
    
    Returns:
        dict: Kaydedilen lokasyon bilgisi
    """
    locations = _load_locations()
    
    # Benzersiz ID oluştur
    location_id = str(uuid.uuid4())[:8]
    
    # Lokasyon objesi
    location = {
        "id": location_id,
        "name": name,
        "lat": lat,
        "lon": lon,
        "icon_type": icon_type,
        "address": address,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "times_used": 0
    }
    
    locations.append(location)
    _save_locations(locations)
    
    print(f"[LocationStorage] Lokasyon kaydedildi: {location_id} - {name} ({icon_type})")
    return location


def get_all_locations(sort_by: str = "created_at", limit: int = None) -> List[Dict]:
    """
    Tüm lokasyonları getirir.
    
    Args:
        sort_by: Sıralama kriteri (created_at, name, times_used)
        limit: Maksimum lokasyon sayısı
    
    Returns:
        list[dict]: Lokasyon listesi
    """
    locations = _load_locations()
    
    # Sıralama
    if sort_by == "created_at":
        locations.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    elif sort_by == "name":
        locations.sort(key=lambda x: x.get("name", "").lower())
    elif sort_by == "times_used":
        locations.sort(key=lambda x: x.get("times_used", 0), reverse=True)
    
    # Limit uygula
    if limit:
        locations = locations[:limit]
    
    return locations


def increment_usage(location_id: str) -> Optional[Dict]:
    """
    Lokasyonun kullanım sayısını artırır.
    
    Args:
        location_id: Lokasyon ID'si
    
    Returns:
        dict: Güncellenmiş lokasyon veya None
    """
    locations = _load_locations()
    
    for i, loc in enumerate(locations):
        if loc["id"] == location_id:
            loc["times_used"] = loc.get("times_used", 0) + 1
            loc["updated_at"] = datetime.now().isoformat()
            locations[i] = loc
            _save_locations(locations)
            return loc
            
    return None


def update_location(location_id: str, updates: Dict) -> Optional[Dict]:
    """
    Mevcut lokasyonu günceller.
    
    Args:
        location_id: Lokasyon ID'si
        updates: Güncellenecek alanlar
    
    Returns:
        dict: Güncellenmiş lokasyon veya None
    """
    locations = _load_locations()
    
    for i, loc in enumerate(locations):
        if loc["id"] == location_id:
            # Güncellemeleri uygula
            loc.update(updates)
            loc["updated_at"] = datetime.now().isoformat()
            locations[i] = loc
            _save_locations(locations)
            
            print(f"[LocationStorage] Lokasyon güncellendi: {location_id}")
            return loc
    
    return None


def delete_location(location_id: str) -> bool:
    """
    Lokasyonu siler.
    
    Args:
        location_id: Lokasyon ID'si
    
    Returns:
        bool: Başarılı ise True
    """
    locations = _load_locations()
    
    for i, loc in enumerate(locations):
        if loc["id"] == location_id:
            locations.pop(i)
            _save_locations(locations)
            print(f"[LocationStorage] Lokasyon silindi: {location_id}")
            return True
    
    return False

def search_locations_by_name(query: str) -> List[Dict]:
    """
    NLP aramaları için lokasyon adında arama yapar (Case-insensitive tam veya kısmi eşleşme).
    
    Args:
        query: Aranacak isim ("Ev", "Okul" vs.)
        
    Returns:
        list[dict]: Eşleşen lokasyonlar
    """
    locations = _load_locations()
    query_lower = query.lower()
    
    results = []
    for loc in locations:
        if query_lower in loc["name"].lower():
            results.append(loc)
            
    return results
