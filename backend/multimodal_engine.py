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
    get_metro_stations_in_area,
    get_metro_lines_for_station,
    get_metro_line_stations,
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
AVG_METRO_SPEED_KMH = 34

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

    def _sample_waypoints(coords: List[List[float]], max_waypoints: int = 20) -> List[List[float]]:
        if len(coords) <= max_waypoints:
            return coords
        # OSRM'e tum duraklari dayatmak bazen sacma zigzag uretir.
        # Bu nedenle esit aralikli ornekleyip ilk/son duragi koruyoruz.
        sampled = [coords[0]]
        step = max(1, int((len(coords) - 2) / max(1, (max_waypoints - 2))))
        idx = step
        while idx < len(coords) - 1 and len(sampled) < (max_waypoints - 1):
            sampled.append(coords[idx])
            idx += step
        sampled.append(coords[-1])
        return sampled

    stop_path_dist = _path_distance_m(stop_coords)

    if len(stop_coords) <= 25:
        query_coords = _sample_waypoints(stop_coords, max_waypoints=20)
        road_coords = _osrm_multi_waypoint(query_coords)
    else:
        all_coords = []
        for i in range(0, len(stop_coords), 19):
            chunk = stop_coords[i:i + 20]
            if len(chunk) < 2:
                all_coords.extend(chunk)
                continue
            query_chunk = _sample_waypoints(chunk, max_waypoints=16)
            road_chunk = _osrm_multi_waypoint(query_chunk)
            if all_coords and road_chunk:
                road_chunk = road_chunk[1:]  # Overlap noktasini atla
            all_coords.extend(road_chunk)
        road_coords = all_coords if len(all_coords) >= 2 else stop_coords

    road_dist = _path_distance_m(road_coords)
    # Google Maps benzeri, asiri sapmayan bir cizim icin kalite kontrolu.
    # OSRM detour'u cok buyukse veya cok kucukse durak polyline'ina geri don.
    if stop_path_dist > 0:
        if road_dist > (stop_path_dist * 1.85) or road_dist < (stop_path_dist * 0.55):
            return stop_coords

    return road_coords if len(road_coords) >= 2 else stop_coords


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


def _metro_travel_time_minutes(distance_km: float) -> float:
    """Metro/tram/funikuler ortalama sure (dakika)."""
    if distance_km <= 0:
        return 0
    return round((distance_km / AVG_METRO_SPEED_KMH) * 60, 1)


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


def _normalize_station_name(name: str) -> str:
    if not name:
        return ""
    return (
        name.lower()
        .replace("-", " ")
        .replace("_", " ")
        .replace("ı", "i")
        .replace("ö", "o")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ç", "c")
        .replace("ğ", "g")
        .strip()
    )


def _get_line_path_between_stations(line_id: int, from_station_id: int, to_station_id: int) -> List[Dict]:
    stations = get_metro_line_stations(line_id)
    if len(stations) < 2:
        return []
    from_idx = None
    to_idx = None
    for i, st in enumerate(stations):
        if st["id"] == from_station_id:
            from_idx = i
        if st["id"] == to_station_id:
            to_idx = i
    if from_idx is None or to_idx is None:
        return []
    if from_idx <= to_idx:
        return stations[from_idx:to_idx + 1]
    seg = stations[to_idx:from_idx + 1]
    seg.reverse()
    return seg


def _find_metro_transfer_pairs(
    line_a_stations: List[Dict],
    line_b_stations: List[Dict],
    max_distance_m: float = 260.0,
) -> List[Tuple[Dict, Dict]]:
    """
    Iki farkli metro hatti arasinda aktarma olabilecek istasyon ciftlerini bulur.
    Once isim eslesmesini, sonra fiziksel yakinligi kullanir.
    """
    a_name_map = {_normalize_station_name(s.get("description") or s.get("name")): s for s in line_a_stations}
    b_name_map = {_normalize_station_name(s.get("description") or s.get("name")): s for s in line_b_stations}

    pairs: List[Tuple[Dict, Dict]] = []
    seen_ids = set()

    # 1) Isim bazli guclu eslesme
    for nm, a_st in a_name_map.items():
        if not nm or nm not in b_name_map:
            continue
        b_st = b_name_map[nm]
        key = (a_st["id"], b_st["id"])
        if key in seen_ids:
            continue
        seen_ids.add(key)
        pairs.append((a_st, b_st))

    # 2) Fiziksel yakinlik bazli eslesme
    # Interchange istasyon isimleri her zaman birebir ayni gelmeyebiliyor.
    close_pairs = []
    for a_st in line_a_stations:
        for b_st in line_b_stations:
            dist = _haversine_distance(a_st["lat"], a_st["lon"], b_st["lat"], b_st["lon"])
            if dist <= max_distance_m:
                close_pairs.append((dist, a_st, b_st))

    close_pairs.sort(key=lambda x: x[0])
    for _, a_st, b_st in close_pairs[:4]:
        key = (a_st["id"], b_st["id"])
        if key in seen_ids:
            continue
        seen_ids.add(key)
        pairs.append((a_st, b_st))
        if len(pairs) >= 5:
            break

    return pairs


def _build_metro_options(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    direct_walk_min: float,
    direct_walk_m: float,
    max_results: int = 4,
) -> List[Dict]:
    """Metro API verisinden direkt ve tek aktarmali secenekler uretir."""
    options = []
    search_radii = [900, 1600, 2600, 4000, 5500]

    origin_candidates = []
    dest_candidates = []
    for radius in search_radii:
        origin_candidates = get_metro_stations_in_area(origin_lat, origin_lon, radius)
        dest_candidates = get_metro_stations_in_area(dest_lat, dest_lon, radius)
        if origin_candidates and dest_candidates:
            break

    if not origin_candidates or not dest_candidates:
        return []

    origin_candidates = origin_candidates[:15]
    dest_candidates = dest_candidates[:15]

    seen = set()
    for o in origin_candidates:
        for d in dest_candidates:
            o_lines = get_metro_lines_for_station(o["id"])
            d_lines = get_metro_lines_for_station(d["id"])
            if not o_lines or not d_lines:
                continue

            # Direkt ayni hat
            d_lines_by_id = {ln["id"]: ln for ln in d_lines}
            for o_line in o_lines:
                line_id = o_line["id"]
                if line_id not in d_lines_by_id:
                    continue
                line_path = _get_line_path_between_stations(line_id, o["id"], d["id"])
                if len(line_path) < 2:
                    continue
                rail_coords = [[s["lat"], s["lon"]] for s in line_path]
                rail_distance_m = _path_distance_m(rail_coords)
                walk_to = _walking_time_minutes(o["distance_m"])
                walk_from = _walking_time_minutes(d["distance_m"])
                wait_time = 4.0
                rail_time = _metro_travel_time_minutes(rail_distance_m / 1000)
                total_time = walk_to + wait_time + rail_time + walk_from

                if total_time > max(direct_walk_min * 2.5, 90):
                    continue
                if (o["distance_m"] + rail_distance_m + d["distance_m"]) > max(direct_walk_m * 5.5, 22000):
                    continue

                key = ("direct", line_id, o["id"], d["id"])
                if key in seen:
                    continue
                seen.add(key)
                line_name = o_line.get("name", f"L{line_id}")
                options.append({
                    "type": "transit",
                    "transit_mode": "metro",
                    "icon": "metro",
                    "name": f"{line_name} Metro",
                    "description": f"{o['description']} -> {d['description']}",
                    "total_time_min": round(total_time, 1),
                    "total_distance_m": round(o["distance_m"] + rail_distance_m + d["distance_m"]),
                    "route_code": line_name,
                    "route_name": o_line.get("long_description", line_name),
                    "transfer_count": 0,
                    "segments": [
                        {
                            "mode": "walk",
                            "description": f"Istasyona yuru: {o['description']}",
                            "distance_m": o["distance_m"],
                            "duration_min": walk_to,
                            "coords": _get_walk_road_coords(origin_lat, origin_lon, o["lat"], o["lon"]),
                        },
                        {
                            "mode": "rail",
                            "description": f"{line_name} hatti",
                            "route_code": line_name,
                            "from_stop": o["description"],
                            "to_stop": d["description"],
                            "distance_m": round(rail_distance_m),
                            "duration_min": rail_time,
                            "wait_min": wait_time,
                            "coords": rail_coords,
                            "stop_coords": rail_coords,
                        },
                        {
                            "mode": "walk",
                            "description": "Istasyondan hedefe yuru",
                            "distance_m": d["distance_m"],
                            "duration_min": walk_from,
                            "coords": _get_walk_road_coords(d["lat"], d["lon"], dest_lat, dest_lon),
                        },
                    ],
                })

            # Tek aktarma (isim bazli transfer)
            o_lines_map = {ln["id"]: ln for ln in o_lines}
            d_lines_map = {ln["id"]: ln for ln in d_lines}
            for line_a_id, line_a in o_lines_map.items():
                a_stations = get_metro_line_stations(line_a_id)
                if len(a_stations) < 2:
                    continue

                for line_b_id, line_b in d_lines_map.items():
                    if line_a_id == line_b_id:
                        continue
                    b_stations = get_metro_line_stations(line_b_id)
                    if len(b_stations) < 2:
                        continue
                    transfer_pairs = _find_metro_transfer_pairs(a_stations, b_stations)
                    if not transfer_pairs:
                        continue

                    for transfer_a, transfer_b in transfer_pairs[:3]:
                        leg1 = _get_line_path_between_stations(line_a_id, o["id"], transfer_a["id"])
                        leg2 = _get_line_path_between_stations(line_b_id, transfer_b["id"], d["id"])
                        if len(leg1) < 2 or len(leg2) < 2:
                            continue

                        coords1 = [[s["lat"], s["lon"]] for s in leg1]
                        coords2 = [[s["lat"], s["lon"]] for s in leg2]
                        dist1 = _path_distance_m(coords1)
                        dist2 = _path_distance_m(coords2)
                        walk_to = _walking_time_minutes(o["distance_m"])
                        walk_from = _walking_time_minutes(d["distance_m"])
                        wait1 = 4.0
                        wait2 = 4.0
                        rail1 = _metro_travel_time_minutes(dist1 / 1000)
                        rail2 = _metro_travel_time_minutes(dist2 / 1000)
                        total_time = walk_to + wait1 + rail1 + wait2 + rail2 + walk_from

                        total_distance = o["distance_m"] + dist1 + dist2 + d["distance_m"]
                        if total_time > max(direct_walk_min * 3.1, 110):
                            continue
                        if total_distance > max(direct_walk_m * 6.2, 28000):
                            continue

                        key = ("transfer", line_a_id, line_b_id, o["id"], d["id"], transfer_a["id"], transfer_b["id"])
                        if key in seen:
                            continue
                        seen.add(key)

                        name_a = line_a.get("name", f"L{line_a_id}")
                        name_b = line_b.get("name", f"L{line_b_id}")
                        transfer_desc = transfer_a.get("description") or transfer_a.get("name") or "Transfer"
                        options.append({
                            "type": "transit",
                            "transit_mode": "metro",
                            "icon": "metro",
                            "name": f"{name_a} + {name_b} Aktarmali",
                            "description": f"{o['description']} -> {transfer_desc} -> {d['description']}",
                            "total_time_min": round(total_time, 1),
                            "total_distance_m": round(total_distance),
                            "route_code": f"{name_a}->{name_b}",
                            "route_name": f"{name_a} + {name_b}",
                            "transfer_count": 1,
                            "segments": [
                                {
                                    "mode": "walk",
                                    "description": f"Istasyona yuru: {o['description']}",
                                    "distance_m": o["distance_m"],
                                    "duration_min": walk_to,
                                    "coords": _get_walk_road_coords(origin_lat, origin_lon, o["lat"], o["lon"]),
                                },
                                {
                                    "mode": "rail",
                                    "description": f"{name_a} hatti",
                                    "route_code": name_a,
                                    "from_stop": o["description"],
                                    "to_stop": transfer_desc,
                                    "distance_m": round(dist1),
                                    "duration_min": rail1,
                                    "wait_min": wait1,
                                    "coords": coords1,
                                    "stop_coords": coords1,
                                },
                                {
                                    "mode": "rail",
                                    "description": f"{name_b} hatti",
                                    "route_code": name_b,
                                    "from_stop": transfer_desc,
                                    "to_stop": d["description"],
                                    "distance_m": round(dist2),
                                    "duration_min": rail2,
                                    "wait_min": wait2,
                                    "coords": coords2,
                                    "stop_coords": coords2,
                                },
                                {
                                    "mode": "walk",
                                    "description": "Istasyondan hedefe yuru",
                                    "distance_m": d["distance_m"],
                                    "duration_min": walk_from,
                                    "coords": _get_walk_road_coords(d["lat"], d["lon"], dest_lat, dest_lon),
                                },
                            ],
                        })

    options.sort(key=lambda x: x["total_time_min"])

    # Ayni hat kombinasyonunu farkli istasyon secimiyle tekrar gostermeyi azalt.
    unique = []
    seen = set()
    for opt in options:
        transfer_count = int(opt.get("transfer_count", 0))
        if transfer_count == 0:
            key = ("metro_direct", str(opt.get("route_code", "")))
        else:
            key = ("metro_transfer", str(opt.get("route_code", "")))
        if key in seen:
            continue
        seen.add(key)
        unique.append(opt)
        if len(unique) >= max_results:
            break

    return unique


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

    metro_options = _build_metro_options(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        direct_walk_min=direct_walk_min,
        direct_walk_m=direct_walk_m,
        max_results=5,
    )
    result.extend(metro_options)
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
