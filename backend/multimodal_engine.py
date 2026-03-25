"""
multimodal_engine.py - Multimodal Rota Planlama Motoru

Yuruyus ve toplu tasima seceneklerini karsilastirarak
en iyi rotayi olusturur.

Algoritmalar:
- Yakin durak bulma (Haversine + bounding box)
- Ortak hat arama (SQLite join)
- Seyahat suresi hesaplama
- Yuruyus vs toplu tasima karsilastirmasi
"""

import math
import requests
import time as _time
from typing import List, Dict, Optional, Tuple

from ibb_transit import (
    get_stops_in_area,
    find_connecting_routes,
    get_route_info,
    _haversine_distance,
    _get_db_connection,
)


# ============================================================================
# SABITLER
# ============================================================================

# Yurume hizi: 5 km/s -> 83.3 m/dk
WALKING_SPEED_M_PER_MIN = 83.3

# Ortalama otobus bekleme suresi (dakika)
AVG_BUS_WAIT_MIN = 5

# Ortalama otobus hizi (trafik dahil, km/s)
AVG_BUS_SPEED_KMH = 18

# Maksimum yurume mesafesi duraga (metre)
MAX_WALK_TO_STOP_M = 800

# Arama yaricaplari (dar -> genis)
SEARCH_RADII = [600, 1000, 1500]

# OSRM public API
OSRM_BASE_URL = "http://router.project-osrm.org"


# ============================================================================
# OSRM ROAD-LEVEL ROUTING
# ============================================================================

def _osrm_route_coords(from_lat: float, from_lon: float,
                        to_lat: float, to_lon: float,
                        mode: str = "driving") -> List[List[float]]:
    """
    OSRM API ile iki nokta arasi yol koordinatlarini dondurur.
    Google Maps gibi yol takip eden polyline olusturur.

    Args:
        mode: "driving" veya "foot"

    Returns:
        [[lat, lon], ...] - yol uzerinden koordinatlar
    """
    try:
        url = f"{OSRM_BASE_URL}/route/v1/{mode}/{from_lon},{from_lat};{to_lon},{to_lat}"
        params = {"overview": "full", "geometries": "geojson"}
        r = requests.get(url, params=params, timeout=8)

        if r.status_code != 200:
            return [[from_lat, from_lon], [to_lat, to_lon]]

        data = r.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            return [[from_lat, from_lon], [to_lat, to_lon]]

        # GeoJSON format: [lon, lat] -> [lat, lon] cevir
        coords = data["routes"][0]["geometry"]["coordinates"]
        return [[c[1], c[0]] for c in coords]

    except Exception:
        return [[from_lat, from_lon], [to_lat, to_lon]]


def _get_bus_road_coords(stop_coords: List[List[float]]) -> List[List[float]]:
    """
    Otobus duraklari arasindaki yol koordinatlarini OSRM ile hesaplar.
    Ardiksik her iki durak icin OSRM driving sorgusu yapar ve
    sonuclari birlestirerek gercek yol takip eden polyline olusturur.

    Cok fazla durak varsa, her 3-4 duragi bir OSRM waypoint olarak gonderir
    (daha az API cagirisi).

    Args:
        stop_coords: [[lat, lon], ...] - durak koordinatlari sirali

    Returns:
        [[lat, lon], ...] - yol uzerinden koordinatlar
    """
    if len(stop_coords) < 2:
        return stop_coords

    # Durak sayisina gore batch buyuklugu ayarla
    # OSRM max ~25 waypoint kabul eder
    if len(stop_coords) <= 25:
        # Tum duraklari tek seferde OSRM'e gonder
        return _osrm_multi_waypoint(stop_coords)
    else:
        # 20'li gruplara bol ve birlestir
        all_coords = []
        for i in range(0, len(stop_coords), 19):
            chunk = stop_coords[i:i + 20]
            if len(chunk) < 2:
                all_coords.extend(chunk)
                continue
            road_coords = _osrm_multi_waypoint(chunk)
            if all_coords and road_coords:
                road_coords = road_coords[1:]  # Overlap noktasini atla
            all_coords.extend(road_coords)
        return all_coords


def _osrm_multi_waypoint(coords: List[List[float]]) -> List[List[float]]:
    """
    Birden fazla waypoint ile OSRM sorgusu yapar.
    Tum duraklarin uzerinden gecen tek bir rota dondurur.
    """
    if len(coords) < 2:
        return coords

    try:
        # OSRM format: lon1,lat1;lon2,lat2;...
        waypoints = ";".join([f"{c[1]},{c[0]}" for c in coords])
        url = f"{OSRM_BASE_URL}/route/v1/driving/{waypoints}"
        params = {"overview": "full", "geometries": "geojson"}

        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            return coords

        data = r.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            return coords

        geojson_coords = data["routes"][0]["geometry"]["coordinates"]
        return [[c[1], c[0]] for c in geojson_coords]

    except Exception:
        return coords


def _get_walk_road_coords(from_lat: float, from_lon: float,
                           to_lat: float, to_lon: float) -> List[List[float]]:
    """Yurume guzergahini OSRM foot routing ile hesaplar."""
    return _osrm_route_coords(from_lat, from_lon, to_lat, to_lon, mode="foot")


# ============================================================================
# YARDIMCI FONKSIYONLAR
# ============================================================================

def _walking_time_minutes(distance_m: float) -> float:
    """Yurume suresi (dakika)."""
    return round(distance_m / WALKING_SPEED_M_PER_MIN, 1)


def _bus_travel_time_minutes(distance_km: float) -> float:
    """Otobus seyahat suresi (dakika)."""
    if distance_km <= 0:
        return 0
    return round((distance_km / AVG_BUS_SPEED_KMH) * 60, 1)


def _get_routes_at_stop(stop_code: int) -> List[str]:
    """Bir duraktan gecen hatlari dondurur."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT route_code FROM route_stops WHERE stop_code = ?",
        (stop_code,),
    )
    routes = [row["route_code"] for row in cursor.fetchall()]
    conn.close()
    return routes


def _get_route_stop_coords(route_code: str, from_stop_code: int, to_stop_code: int) -> List[List[float]]:
    """
    Bir hat uzerindeki binis duragindan inis duragina kadar
    duraklarin koordinatlarini SIRALI dondurur.

    Her iki yon (D, G) de denenir ve from_stop -> to_stop
    sirasina uyan yon secilir.

    Returns:
        [[lat, lon], [lat, lon], ...] - binis'ten inis'e sirali koordinatlar
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Her iki yonde de dene
    for direction in ["D", "G"]:
        cursor.execute("""
            SELECT stop_code, stop_order FROM route_stops
            WHERE route_code = ? AND direction = ? AND stop_code IN (?, ?)
            ORDER BY stop_order
        """, (route_code, direction, from_stop_code, to_stop_code))

        rows = cursor.fetchall()
        if len(rows) < 2:
            continue

        # from_stop ve to_stop'un sira numaralarini bul
        from_order = None
        to_order = None
        for r in rows:
            if r["stop_code"] == from_stop_code:
                from_order = r["stop_order"]
            if r["stop_code"] == to_stop_code:
                to_order = r["stop_order"]

        if from_order is None or to_order is None:
            continue

        # from_stop, to_stop'tan ONCE gelmeli (dogru yon)
        if from_order > to_order:
            continue  # Yanlis yon, diger yonu dene

        # Aradaki tum duraklarin koordinatlarini al
        cursor.execute("""
            SELECT rs.stop_code, rs.stop_order, s.lat, s.lon
            FROM route_stops rs
            LEFT JOIN stops s ON rs.stop_code = s.code
            WHERE rs.route_code = ? AND rs.direction = ?
            AND rs.stop_order >= ? AND rs.stop_order <= ?
            ORDER BY rs.stop_order
        """, (route_code, direction, from_order, to_order))

        coords = []
        for row in cursor.fetchall():
            if row["lat"] and row["lon"]:
                coords.append([row["lat"], row["lon"]])

        if coords:
            conn.close()
            return coords

    # Hicbir yon uymadiysa, yon farketmeksizin dene
    cursor.execute("""
        SELECT stop_code, stop_order, direction FROM route_stops
        WHERE route_code = ? AND stop_code IN (?, ?)
        ORDER BY stop_order
    """, (route_code, from_stop_code, to_stop_code))

    rows = cursor.fetchall()
    if len(rows) >= 2:
        min_order = min(r["stop_order"] for r in rows)
        max_order = max(r["stop_order"] for r in rows)
        direction = rows[0]["direction"]

        cursor.execute("""
            SELECT rs.stop_code, rs.stop_order, s.lat, s.lon
            FROM route_stops rs
            LEFT JOIN stops s ON rs.stop_code = s.code
            WHERE rs.route_code = ? AND rs.direction = ?
            AND rs.stop_order >= ? AND rs.stop_order <= ?
            ORDER BY rs.stop_order
        """, (route_code, direction, min_order, max_order))

        coords = []
        for row in cursor.fetchall():
            if row["lat"] and row["lon"]:
                coords.append([row["lat"], row["lon"]])

        # Eger ilk coord from_stop'a degil to_stop'a yakinsa ters cevir
        if len(coords) >= 2:
            from_stop_data = None
            cursor.execute("SELECT lat, lon FROM stops WHERE code = ?", (from_stop_code,))
            from_stop_data = cursor.fetchone()
            if from_stop_data:
                d_first = _haversine_distance(coords[0][0], coords[0][1], from_stop_data["lat"], from_stop_data["lon"])
                d_last = _haversine_distance(coords[-1][0], coords[-1][1], from_stop_data["lat"], from_stop_data["lon"])
                if d_last < d_first:
                    coords.reverse()

            conn.close()
            return coords

    conn.close()
    return []


def _get_nearby_routes(lat: float, lon: float, radius: int = 500) -> List[Dict]:
    """Belirli yaricaptaki duraklardan gecen hatlari toplar."""
    stops = get_stops_in_area(lat, lon, radius)
    route_set = {}
    for stop in stops[:15]:
        routes = _get_routes_at_stop(stop["code"])
        for r in routes:
            if r not in route_set:
                route_set[r] = {
                    "route_code": r,
                    "stop_name": stop["name"],
                    "stop_code": stop["code"],
                    "distance_m": stop["distance_m"],
                }
    return list(route_set.values())


# ============================================================================
# MULTIMODAL ROTA HESAPLAMA
# ============================================================================

def find_transit_routes(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    max_results: int = 3,
) -> List[Dict]:
    """
    Iki nokta arasi toplu tasima seceneklerini bulur.

    Algoritma:
    1. Baslangic noktasina yakin duraklari bul
    2. Bitis noktasina yakin duraklari bul
    3. Ortak hat ara (artan yaricaplarla)
    4. Her secenegin toplam suresini hesapla
    5. En iyi secenekleri dondur
    """

    # Direkt yurume mesafesi
    direct_walk_m = _haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon)
    direct_walk_min = _walking_time_minutes(direct_walk_m)

    # Artan yaricaplarla dene
    transit_options = []

    for radius in SEARCH_RADII:
        # Baslangica yakin duraklar
        origin_stops = get_stops_in_area(origin_lat, origin_lon, radius)
        # Hedefe yakin duraklar
        dest_stops = get_stops_in_area(dest_lat, dest_lon, radius)

        if not origin_stops or not dest_stops:
            continue

        # Her baslangic duragi icin
        for o_stop in origin_stops[:10]:
            if o_stop["distance_m"] > MAX_WALK_TO_STOP_M:
                continue

            for d_stop in dest_stops[:10]:
                if d_stop["distance_m"] > MAX_WALK_TO_STOP_M:
                    continue

                # Ortak hat bul
                connections = find_connecting_routes(o_stop["code"], d_stop["code"])

                for conn in connections:
                    walk_to_stop = _walking_time_minutes(o_stop["distance_m"])
                    wait_time = AVG_BUS_WAIT_MIN

                    bus_distance_m = _haversine_distance(
                        o_stop["lat"], o_stop["lon"],
                        d_stop["lat"], d_stop["lon"]
                    )
                    bus_time = _bus_travel_time_minutes(bus_distance_m / 1000)
                    walk_from_stop = _walking_time_minutes(d_stop["distance_m"])

                    total_time = walk_to_stop + wait_time + bus_time + walk_from_stop

                    # Sadece yurumekten daha iyi olan secenekleri ekle
                    if total_time < direct_walk_min * 0.9:
                        transit_options.append({
                            "type": "transit",
                            "route_code": conn.get("route_code", conn.get("code", "")),
                            "route_name": conn.get("name", ""),
                            "origin_stop": {
                                "code": o_stop["code"],
                                "name": o_stop["name"],
                                "lat": o_stop["lat"],
                                "lon": o_stop["lon"],
                                "walk_distance_m": o_stop["distance_m"],
                                "walk_time_min": walk_to_stop,
                            },
                            "dest_stop": {
                                "code": d_stop["code"],
                                "name": d_stop["name"],
                                "lat": d_stop["lat"],
                                "lon": d_stop["lon"],
                                "walk_distance_m": d_stop["distance_m"],
                                "walk_time_min": walk_from_stop,
                            },
                            "wait_time_min": wait_time,
                            "bus_time_min": bus_time,
                            "total_time_min": round(total_time, 1),
                            "total_walk_m": o_stop["distance_m"] + d_stop["distance_m"],
                            "bus_distance_m": round(bus_distance_m),
                        })

        # Yeterli secenek bulunduysa daha genis arama yapma
        if transit_options:
            break

    # Surelerine gore sirala
    transit_options.sort(key=lambda x: x["total_time_min"])

    # Ayni hat kodunu tekrar gosterme
    seen_routes = set()
    unique_options = []
    for opt in transit_options:
        key = opt["route_code"]
        if key not in seen_routes:
            seen_routes.add(key)
            unique_options.append(opt)
            if len(unique_options) >= max_results:
                break

    # Yurume secenegi her zaman ekle
    result = [{
        "type": "walking",
        "icon": "walking",
        "name": "Yuruyus",
        "description": f"Direkt yurume ({round(direct_walk_m)}m)",
        "total_time_min": round(direct_walk_min, 1),
        "total_distance_m": round(direct_walk_m),
        "segments": [{
            "mode": "walk",
            "description": "Direkt yurume",
            "distance_m": round(direct_walk_m),
            "duration_min": round(direct_walk_min, 1),
            "coords": [[origin_lat, origin_lon], [dest_lat, dest_lon]],
        }],
    }]

    # Transit secenekleri ekle
    for opt in unique_options:
        route_display = opt["route_code"]

        # Bus route koordinatlarini al
        bus_coords = _get_route_stop_coords(
            opt["route_code"],
            opt["origin_stop"]["code"],
            opt["dest_stop"]["code"],
        )
        # Fallback: duz cizgi
        if not bus_coords:
            bus_coords = [
                [opt["origin_stop"]["lat"], opt["origin_stop"]["lon"]],
                [opt["dest_stop"]["lat"], opt["dest_stop"]["lon"]],
            ]

        result.append({
            "type": "transit",
            "icon": "bus",
            "name": f"{route_display} Otobus",
            "description": f"{opt['origin_stop']['name']} -> {opt['dest_stop']['name']}",
            "total_time_min": opt["total_time_min"],
            "total_distance_m": opt["total_walk_m"] + opt["bus_distance_m"],
            "route_code": opt["route_code"],
            "route_name": opt.get("route_name", ""),
            "segments": [
                {
                    "mode": "walk",
                    "description": f"Duraga yuru: {opt['origin_stop']['name']}",
                    "distance_m": opt["origin_stop"]["walk_distance_m"],
                    "duration_min": opt["origin_stop"]["walk_time_min"],
                    "coords": [
                        [origin_lat, origin_lon],
                        [opt["origin_stop"]["lat"], opt["origin_stop"]["lon"]],
                    ],
                },
                {
                    "mode": "bus",
                    "description": f"{route_display} hatti",
                    "route_code": opt["route_code"],
                    "from_stop": opt["origin_stop"]["name"],
                    "to_stop": opt["dest_stop"]["name"],
                    "distance_m": opt["bus_distance_m"],
                    "duration_min": opt["bus_time_min"],
                    "wait_min": opt["wait_time_min"],
                    "coords": bus_coords,
                },
                {
                    "mode": "walk",
                    "description": "Duraktan hedefe yuru",
                    "distance_m": opt["dest_stop"]["walk_distance_m"],
                    "duration_min": opt["dest_stop"]["walk_time_min"],
                    "coords": [
                        [opt["dest_stop"]["lat"], opt["dest_stop"]["lon"]],
                        [dest_lat, dest_lon],
                    ],
                },
            ],
        })

    return result


def compare_routes(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
) -> Dict:
    """
    Yuruyus ve toplu tasima seceneklerini karsilastirir.
    Direkt baglanti bulunamazsa yakin hatlari bilgi olarak dondurur.
    """
    options = find_transit_routes(origin_lat, origin_lon, dest_lat, dest_lon)

    walking = options[0]
    transit = [o for o in options if o["type"] == "transit"]

    # Oneri
    recommended = "walking"
    reason = "Yuruyus en hizli secenek"

    if transit:
        best_transit = transit[0]
        if best_transit["total_time_min"] < walking["total_time_min"]:
            recommended = "transit"
            saved = round(walking["total_time_min"] - best_transit["total_time_min"], 1)
            reason = f"Toplu tasima {saved} dk daha hizli"
        else:
            reason = "Yuruyus daha hizli veya benzer surede"

    # Yakin hatlari bilgi olarak ekle (direkt baglanti olmasa bile)
    nearby_origin = _get_nearby_routes(origin_lat, origin_lon, 500)
    nearby_dest = _get_nearby_routes(dest_lat, dest_lon, 500)

    return {
        "options": options,
        "walking": walking,
        "transit_options": transit,
        "recommended": recommended,
        "recommendation_reason": reason,
        "nearby_routes": {
            "origin": [{"route_code": r["route_code"], "stop_name": r["stop_name"], "distance_m": r["distance_m"]} for r in nearby_origin[:5]],
            "destination": [{"route_code": r["route_code"], "stop_name": r["stop_name"], "distance_m": r["distance_m"]} for r in nearby_dest[:5]],
        },
    }


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("Multimodal Rota Test")
    print("=" * 50)

    # Kadikoy -> Moda arasi
    result = compare_routes(40.9903, 29.0291, 40.9835, 29.0344)

    print(f"\nOneri: {result['recommended']}")
    print(f"Neden: {result['recommendation_reason']}")
    print(f"\nSecenekler:")
    for opt in result["options"]:
        print(f"  {opt['icon']} {opt['name']} - {opt['total_time_min']} dk")
        for seg in opt.get("segments", []):
            print(f"    [{seg['mode']}] {seg.get('description', '')} - {seg['duration_min']} dk")

    # Yakin hatlar
    nr = result.get("nearby_routes", {})
    print(f"\nBaslangic yakin hatlar: {[r['route_code'] for r in nr.get('origin', [])]}")
    print(f"Hedef yakin hatlar: {[r['route_code'] for r in nr.get('destination', [])]}")
