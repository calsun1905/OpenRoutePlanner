"""
route_storage.py - Rota Kaydetme ve Yükleme Sistemi

Kullanıcıların rotalarını kaydetmesini ve yüklemesini sağlar.
JSON dosya tabanlı basit depolama sistemi.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional


# Kaydedilen rotaların saklanacağı dosya
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "data")
ROUTES_FILE = os.path.join(STORAGE_DIR, "saved_routes.json")


def _ensure_storage_exists():
    """Depolama klasörünü ve dosyasını oluşturur."""
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR)
        print(f"[RouteStorage] Depolama klasörü oluşturuldu: {STORAGE_DIR}")
    
    if not os.path.exists(ROUTES_FILE):
        with open(ROUTES_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        print(f"[RouteStorage] Rota dosyası oluşturuldu: {ROUTES_FILE}")


def _load_routes() -> List[Dict]:
    """Tüm kaydedilmiş rotaları yükler."""
    _ensure_storage_exists()
    
    try:
        with open(ROUTES_FILE, "r", encoding="utf-8") as f:
            routes = json.load(f)
        return routes
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _save_routes(routes: List[Dict]):
    """Rotaları dosyaya kaydeder."""
    _ensure_storage_exists()
    
    with open(ROUTES_FILE, "w", encoding="utf-8") as f:
        json.dump(routes, f, ensure_ascii=False, indent=2)


def simplify_coords(coords: List[List[float]], tolerance: int = 3) -> List[List[float]]:
    """
    Koordinat listesini sıkıştırır — her N noktadan birini alır.
    Rota kaydetme hızını artırır.
    
    Args:
        coords: [[lat, lon], ...] listesi
        tolerance: Kaç noktada bir alınacağı (varsayılan: 3)
    
    Returns:
        Sıkıştırılmış koordinat listesi
    """
    if not coords or len(coords) <= 10:
        return coords
    return coords[::tolerance]


def save_route(
    name: str,
    points: List[List[float]],
    route_coords: List[List[float]],
    distance_km: float,
    duration_minutes: int,
    route_type: str = "shortest",
    description: str = "",
    tags: List[str] = None
) -> Dict:
    """
    Yeni bir rota kaydeder.
    
    Args:
        name: Rota adı
        points: Seçilen noktalar [[lat, lon], ...]
        route_coords: Tam rota koordinatları
        distance_km: Toplam mesafe
        duration_minutes: Tahmini süre
        route_type: Rota tipi (shortest, fastest, balanced)
        description: Rota açıklaması
        tags: Etiketler (örn: ["romantik", "tarihi"])
    
    Returns:
        dict: Kaydedilen rota bilgisi
    """
    routes = _load_routes()
    
    # Benzersiz ID oluştur
    route_id = str(uuid.uuid4())[:8]
    
    # Rota objesi
    route = {
        "id": route_id,
        "name": name,
        "description": description,
        "points": points,
        "route_coords": route_coords,
        "distance_km": distance_km,
        "duration_minutes": duration_minutes,
        "route_type": route_type,
        "tags": tags or [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "favorite": False,
        "times_used": 0
    }
    
    routes.append(route)
    _save_routes(routes)
    
    print(f"[RouteStorage] Rota kaydedildi: {route_id} - {name}")
    return route


def get_route(route_id: str) -> Optional[Dict]:
    """
    ID'ye göre rota getirir.
    
    Args:
        route_id: Rota ID'si
    
    Returns:
        dict: Rota bilgisi veya None
    """
    routes = _load_routes()
    
    for route in routes:
        if route["id"] == route_id:
            # Kullanım sayısını artır
            route["times_used"] = route.get("times_used", 0) + 1
            _save_routes(routes)
            return route
    
    return None


def get_all_routes(sort_by: str = "created_at", limit: int = None) -> List[Dict]:
    """
    Tüm rotaları getirir.
    
    Args:
        sort_by: Sıralama kriteri (created_at, name, distance_km, times_used)
        limit: Maksimum rota sayısı
    
    Returns:
        list[dict]: Rota listesi
    """
    routes = _load_routes()
    
    # Sıralama
    if sort_by == "created_at":
        routes.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    elif sort_by == "name":
        routes.sort(key=lambda x: x.get("name", "").lower())
    elif sort_by == "distance_km":
        routes.sort(key=lambda x: x.get("distance_km", 0))
    elif sort_by == "times_used":
        routes.sort(key=lambda x: x.get("times_used", 0), reverse=True)
    elif sort_by == "favorite":
        routes.sort(key=lambda x: x.get("favorite", False), reverse=True)
    
    # Limit uygula
    if limit:
        routes = routes[:limit]
    
    return routes


def update_route(route_id: str, updates: Dict) -> Optional[Dict]:
    """
    Mevcut rotayı günceller.
    
    Args:
        route_id: Rota ID'si
        updates: Güncellenecek alanlar
    
    Returns:
        dict: Güncellenmiş rota veya None
    """
    routes = _load_routes()
    
    for i, route in enumerate(routes):
        if route["id"] == route_id:
            # Güncellemeleri uygula
            route.update(updates)
            route["updated_at"] = datetime.now().isoformat()
            routes[i] = route
            _save_routes(routes)
            
            print(f"[RouteStorage] Rota güncellendi: {route_id}")
            return route
    
    return None


def delete_route(route_id: str) -> bool:
    """
    Rotayı siler.
    
    Args:
        route_id: Rota ID'si
    
    Returns:
        bool: Başarılı ise True
    """
    routes = _load_routes()
    
    for i, route in enumerate(routes):
        if route["id"] == route_id:
            routes.pop(i)
            _save_routes(routes)
            print(f"[RouteStorage] Rota silindi: {route_id}")
            return True
    
    return False


def toggle_favorite(route_id: str) -> Optional[Dict]:
    """
    Rotayı favorilere ekler/çıkarır.
    
    Args:
        route_id: Rota ID'si
    
    Returns:
        dict: Güncellenmiş rota veya None
    """
    routes = _load_routes()
    
    for i, route in enumerate(routes):
        if route["id"] == route_id:
            route["favorite"] = not route.get("favorite", False)
            route["updated_at"] = datetime.now().isoformat()
            routes[i] = route
            _save_routes(routes)
            
            status = "eklendi" if route["favorite"] else "çıkarıldı"
            print(f"[RouteStorage] Rota favorilerden {status}: {route_id}")
            return route
    
    return None


def search_routes(query: str) -> List[Dict]:
    """
    Rota adı veya açıklamasında arama yapar.
    
    Args:
        query: Arama sorgusu
    
    Returns:
        list[dict]: Eşleşen rotalar
    """
    routes = _load_routes()
    query_lower = query.lower()
    
    results = []
    for route in routes:
        name = route.get("name", "").lower()
        description = route.get("description", "").lower()
        tags = [tag.lower() for tag in route.get("tags", [])]
        
        if (query_lower in name or 
            query_lower in description or 
            any(query_lower in tag for tag in tags)):
            results.append(route)
    
    return results


def get_statistics() -> Dict:
    """
    Rota istatistiklerini döner.
    
    Returns:
        dict: İstatistikler
    """
    routes = _load_routes()
    
    if not routes:
        return {
            "total_routes": 0,
            "total_distance_km": 0,
            "total_duration_minutes": 0,
            "favorite_count": 0,
            "most_used_route": None
        }
    
    total_distance = sum(r.get("distance_km", 0) for r in routes)
    total_duration = sum(r.get("duration_minutes", 0) for r in routes)
    favorite_count = sum(1 for r in routes if r.get("favorite", False))
    
    # En çok kullanılan rota
    most_used = max(routes, key=lambda x: x.get("times_used", 0))
    
    return {
        "total_routes": len(routes),
        "total_distance_km": round(total_distance, 2),
        "total_duration_minutes": total_duration,
        "favorite_count": favorite_count,
        "most_used_route": {
            "id": most_used["id"],
            "name": most_used["name"],
            "times_used": most_used.get("times_used", 0)
        } if most_used.get("times_used", 0) > 0 else None
    }
