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


def _path_distance_m(coords: List[List[float]]) -> float:
    """Verilen [lat, lon] dizi boyunca toplam mesafe (metre)."""
    if not coords or len(coords) < 2:
        return 0.0
    total = 0.0
    for i in range(len(coords) - 1):
        total += _haversine_distance(
            coords[i][0], coords[i][1],
            coords[i + 1][0], coords[i + 1][1],
        )
    return total


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


def _is_reasonable_transit_time(total_time_min: float, direct_walk_min: float, with_transfer: bool = False) -> bool:
    """
    Transit suresini asiri kotu secenekleri elemek icin kontrol eder.
    Direkt yuruyuse gore cok uzun kalani filtreler ama fazla katı davranmaz.
    """
    multiplier = 1.85 if with_transfer else 1.60
    return total_time_min <= (direct_walk_min * multiplier)


def _is_reasonable_transit_distance(total_distance_m: float, direct_walk_m: float, with_transfer: bool = False) -> bool:
    """
    Transit toplam mesafesi, direkt mesafeye gore asiri sapmasin.
    """
    multiplier = 4.2 if with_transfer else 3.0
    return total_distance_m <= (direct_walk_m * multiplier)


def _find_one_transfer_candidates(origin_stop_code: int, dest_stop_code: int, limit: int = 30) -> List[Dict]:
    """
    Tek aktarmali secenekler icin (hat A -> transfer duragi -> hat B) adaylarini bulur.
    """
    origin_routes = _get_routes_at_stop(origin_stop_code)
    dest_routes = _get_routes_at_stop(dest_stop_code)

    if not origin_routes or not dest_routes:
        return []

    # IN (...) parametreleri
    ph_origin = ",".join(["?"] * len(origin_routes))
    ph_dest = ",".join(["?"] * len(dest_routes))

    query = f"""
        SELECT DISTINCT
            a.route_code AS route_a,
            b.route_code AS route_b,
            a.stop_code AS transfer_stop_code,
            s.name AS transfer_stop_name,
            s.lat AS transfer_lat,
            s.lon AS transfer_lon
        FROM route_stops a
        JOIN route_stops b ON a.stop_code = b.stop_code
        LEFT JOIN stops s ON s.code = a.stop_code
        WHERE a.route_code IN ({ph_origin})
          AND b.route_code IN ({ph_dest})
          AND a.route_code != b.route_code
          AND a.stop_code != ?
          AND a.stop_code != ?
        LIMIT ?
    """

    params = origin_routes + dest_routes + [origin_stop_code, dest_stop_code, limit]

    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# ============================================================================
# MULTIMODAL ROTA HESAPLAMA
# ============================================================================

def find_transit_routes(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    max_results: int = 4,
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

                    direct_leg_stop_coords = _get_route_stop_coords(
                        conn.get("route_code", conn.get("code", "")),
                        o_stop["code"],
                        d_stop["code"],
                    )
                    if len(direct_leg_stop_coords) >= 2:
                        bus_distance_m = _path_distance_m(direct_leg_stop_coords)
                    else:
                        bus_distance_m = _haversine_distance(
                            o_stop["lat"], o_stop["lon"],
                            d_stop["lat"], d_stop["lon"]
                        )
                    bus_time = _bus_travel_time_minutes(bus_distance_m / 1000)
                    walk_from_stop = _walking_time_minutes(d_stop["distance_m"])

                    total_time = walk_to_stop + wait_time + bus_time + walk_from_stop
                    total_distance_m = o_stop["distance_m"] + bus_distance_m + d_stop["distance_m"]

                    # Asiri kotu secenekleri ele
                    if (
                        _is_reasonable_transit_time(total_time, direct_walk_min)
                        and _is_reasonable_transit_distance(total_distance_m, direct_walk_m)
                    ):
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

                # Tek aktarmali secenekler (A hatti -> transfer -> B hatti)
                transfer_candidates = _find_one_transfer_candidates(
                    o_stop["code"], d_stop["code"], limit=35
                )
                for candidate in transfer_candidates:
                    route_a = candidate.get("route_a")
                    route_b = candidate.get("route_b")
                    transfer_stop_code = candidate.get("transfer_stop_code")

                    if not route_a or not route_b or not transfer_stop_code:
                        continue

                    # Yon uygun mu? (origin -> transfer) ve (transfer -> dest)
                    leg1_stop_coords = _get_route_stop_coords(route_a, o_stop["code"], transfer_stop_code)
                    leg2_stop_coords = _get_route_stop_coords(route_b, transfer_stop_code, d_stop["code"])
                    if len(leg1_stop_coords) < 2 or len(leg2_stop_coords) < 2:
                        continue

                    transfer_lat = candidate.get("transfer_lat")
                    transfer_lon = candidate.get("transfer_lon")
                    if transfer_lat is None or transfer_lon is None:
                        continue

                    walk_to_stop = _walking_time_minutes(o_stop["distance_m"])
                    walk_from_stop = _walking_time_minutes(d_stop["distance_m"])
                    wait1 = AVG_BUS_WAIT_MIN
                    wait2 = max(3, int(AVG_BUS_WAIT_MIN * 0.8))

                    bus1_distance_m = _path_distance_m(leg1_stop_coords)
                    bus2_distance_m = _path_distance_m(leg2_stop_coords)
                    bus1_time = _bus_travel_time_minutes(bus1_distance_m / 1000)
                    bus2_time = _bus_travel_time_minutes(bus2_distance_m / 1000)

                    total_time = walk_to_stop + wait1 + bus1_time + wait2 + bus2_time + walk_from_stop
                    total_distance_m = o_stop["distance_m"] + bus1_distance_m + bus2_distance_m + d_stop["distance_m"]
                    if (
                        not _is_reasonable_transit_time(total_time, direct_walk_min, with_transfer=True)
                        or not _is_reasonable_transit_distance(total_distance_m, direct_walk_m, with_transfer=True)
                    ):
                        continue

                    route_a_info = get_route_info(route_a) or {}
                    route_b_info = get_route_info(route_b) or {}

                    transit_options.append({
                        "type": "transit_transfer",
                        "route_code": f"{route_a}->{route_b}",
                        "route_codes": [route_a, route_b],
                        "route_name": f"{route_a_info.get('name', route_a)} + {route_b_info.get('name', route_b)}",
                        "origin_stop": {
                            "code": o_stop["code"],
                            "name": o_stop["name"],
                            "lat": o_stop["lat"],
                            "lon": o_stop["lon"],
                            "walk_distance_m": o_stop["distance_m"],
                            "walk_time_min": walk_to_stop,
                        },
                        "transfer_stop": {
                            "code": transfer_stop_code,
                            "name": candidate.get("transfer_stop_name", "Transfer"),
                            "lat": transfer_lat,
                            "lon": transfer_lon,
                        },
                        "dest_stop": {
                            "code": d_stop["code"],
                            "name": d_stop["name"],
                            "lat": d_stop["lat"],
                            "lon": d_stop["lon"],
                            "walk_distance_m": d_stop["distance_m"],
                            "walk_time_min": walk_from_stop,
                        },
                        "wait_time_min": wait1 + wait2,
                        "bus_time_min": bus1_time + bus2_time,
                        "total_time_min": round(total_time, 1),
                        "total_walk_m": o_stop["distance_m"] + d_stop["distance_m"],
                        "bus_distance_m": round(bus1_distance_m + bus2_distance_m),
                        "transfer_count": 1,
                        "transfer_routes": [
                            {
                                "route_code": route_a,
                                "from_code": o_stop["code"],
                                "to_code": transfer_stop_code,
                                "from_name": o_stop["name"],
                                "to_name": candidate.get("transfer_stop_name", "Transfer"),
                                "wait_min": wait1,
                            },
                            {
                                "route_code": route_b,
                                "from_code": transfer_stop_code,
                                "to_code": d_stop["code"],
                                "from_name": candidate.get("transfer_stop_name", "Transfer"),
                                "to_name": d_stop["name"],
                                "wait_min": wait2,
                            },
                        ],
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
    walking_road_coords = _get_walk_road_coords(
        origin_lat, origin_lon, dest_lat, dest_lon
    )

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
            "coords": walking_road_coords,
        }],
    }]

    # Transit secenekleri ekle
    for opt in unique_options:
        walk_to_stop_coords = _get_walk_road_coords(
            origin_lat, origin_lon,
            opt["origin_stop"]["lat"], opt["origin_stop"]["lon"]
        )
        walk_from_stop_coords = _get_walk_road_coords(
            opt["dest_stop"]["lat"], opt["dest_stop"]["lon"],
            dest_lat, dest_lon
        )

        if opt.get("transfer_count") == 1 and opt.get("transfer_routes"):
            transfer_legs = opt["transfer_routes"]
            bus_segments = []
            for idx, leg in enumerate(transfer_legs):
                leg_stop_coords = _get_route_stop_coords(
                    leg["route_code"], leg["from_code"], leg["to_code"]
                )
                if not leg_stop_coords:
                    continue
                leg_road_coords = _get_bus_road_coords(leg_stop_coords)
                leg_distance_m = _path_distance_m(leg_stop_coords)
                bus_segments.append({
                    "mode": "bus",
                    "description": f"{leg['route_code']} hatti",
                    "route_code": leg["route_code"],
                    "from_stop": leg["from_name"],
                    "to_stop": leg["to_name"],
                    "distance_m": round(leg_distance_m),
                    "duration_min": _bus_travel_time_minutes(leg_distance_m / 1000),
                    "wait_min": leg.get("wait_min", AVG_BUS_WAIT_MIN),
                    "coords": leg_road_coords,
                    "stop_coords": leg_stop_coords,
                })

            if not bus_segments:
                continue

            transfer_wait_total = 0.0
            for seg in bus_segments:
                transfer_wait_total += float(seg.get("wait_min", 0))
            bus_total_time = 0.0
            for seg in bus_segments:
                bus_total_time += float(seg.get("duration_min", 0))
            final_total_time = (
                float(opt["origin_stop"]["walk_time_min"])
                + transfer_wait_total
                + bus_total_time
                + float(opt["dest_stop"]["walk_time_min"])
            )

            segments = [{
                "mode": "walk",
                "description": f"Duraga yuru: {opt['origin_stop']['name']}",
                "distance_m": opt["origin_stop"]["walk_distance_m"],
                "duration_min": opt["origin_stop"]["walk_time_min"],
                "coords": walk_to_stop_coords,
            }]
            segments.extend(bus_segments)
            segments.append({
                "mode": "walk",
                "description": "Duraktan hedefe yuru",
                "distance_m": opt["dest_stop"]["walk_distance_m"],
                "duration_min": opt["dest_stop"]["walk_time_min"],
                "coords": walk_from_stop_coords,
            })

            result.append({
                "type": "transit",
                "icon": "bus",
                "name": f"{transfer_legs[0]['route_code']} + {transfer_legs[1]['route_code']} Aktarmali",
                "description": (
                    f"{opt['origin_stop']['name']} -> {opt['transfer_stop']['name']} -> "
                    f"{opt['dest_stop']['name']}"
                ),
                "total_time_min": round(final_total_time, 1),
                "total_distance_m": opt["total_walk_m"] + opt["bus_distance_m"],
                "route_code": opt["route_code"],
                "route_name": opt.get("route_name", ""),
                "transfer_count": 1,
                "segments": segments,
            })
        else:
            route_display = opt["route_code"]
            bus_stop_coords = _get_route_stop_coords(
                opt["route_code"],
                opt["origin_stop"]["code"],
                opt["dest_stop"]["code"],
            )
            if not bus_stop_coords:
                bus_stop_coords = [
                    [opt["origin_stop"]["lat"], opt["origin_stop"]["lon"]],
                    [opt["dest_stop"]["lat"], opt["dest_stop"]["lon"]],
                ]
            bus_road_coords = _get_bus_road_coords(bus_stop_coords)

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
                        "coords": walk_to_stop_coords,
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
                        "coords": bus_road_coords,
                        "stop_coords": bus_stop_coords,
                    },
                    {
                        "mode": "walk",
                        "description": "Duraktan hedefe yuru",
                        "distance_m": opt["dest_stop"]["walk_distance_m"],
                        "duration_min": opt["dest_stop"]["walk_time_min"],
                        "coords": walk_from_stop_coords,
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
