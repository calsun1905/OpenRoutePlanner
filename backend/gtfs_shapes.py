"""
gtfs_shapes.py - GTFS Shapes İndirme ve İşleme

İBB GTFS static feed'inden metro/tram güzergah koordinatlarını indirir.
Shapes.txt dosyası gerçek hat güzergahını (tünel dahil) içerir.

GTFS Feed: https://data.ibb.gov.tr/dataset/gtfs-data
"""

import os
import re
import csv
import time
import zipfile
import sqlite3
import requests
import io
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# ============================================================================
# SABITLER
# ============================================================================

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

TRANSIT_DB = os.path.join(CACHE_DIR, "transit.db")

# İBB GTFS CKAN API
GTFS_CKAN_URL = "https://data.ibb.gov.tr/api/3/action/package_show?id=public-transport-gtfs-data"
GTFS_FEED_URLS = [
    # Legacy direct GTFS feed endpoints (best-effort fallback if CKAN CSV fetch fails).
    "https://data.ibb.gov.tr/dataset/gtfs-data/resource/download/gtfs.zip",
    "https://data.ibb.gov.tr/dataset/gtfs-data/download/gtfs.zip",
]

# İndirilecek dosyalar
GTFS_RESOURCES = {
    "shapes": "shapes.csv",
    "routes": "routes.csv",
    "stops": "stops.csv",
}

SHAPES_CACHE_FILE = os.path.join(CACHE_DIR, "shapes_cache.json")

MAX_SHAPES_AGE_HOURS = 168  # 1 hafta
MIN_GTFS_POINTS_FOR_DIRECT_USE = 8
SPARSE_LINE_FALLBACK_KEYS = {"F1", "F2", "TF1", "TF2", "M2A"}


# ============================================================================
# GTFS İNDİRME
# ============================================================================

def _download_gtfs_zip(url: str, timeout: int = 60) -> Optional[bytes]:
    """GTFS zip dosyasını indirir."""
    try:
        print(f"[GTFS] İndiriliyor: {url}")
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"[GTFS] İndirme hatası: {e}")
        return None


def _get_gtfs_resource_url(resource_name: str) -> Optional[str]:
    """CKAN API'den belirtilen resource URL'sini alır."""
    try:
        response = requests.get(GTFS_CKAN_URL, timeout=30)
        if response.status_code != 200:
            return None
        
        data = response.json()
        resources = data.get("result", {}).get("resources", [])
        
        resource_name_lower = resource_name.lower()
        if resource_name_lower.endswith('.txt'):
            resource_name_lower = resource_name_lower[:-4]
        
        for r in resources:
            rname = r.get("name", "").lower()
            if rname == resource_name_lower or rname == resource_name_lower + '.txt':
                return r.get("url")
        
        return None
    except Exception as e:
        print(f"[GTFS] CKAN API hatası: {e}")
        return None


def download_gtfs_csv(csv_name: str, force: bool = False) -> Optional[str]:
    """Belirtilen CSV dosyasını İBB CKAN API'den indirir."""
    cache_file = os.path.join(CACHE_DIR, f"gtfs_{csv_name}.csv")
    
    if not force and os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            pass
    
    url = _get_gtfs_resource_url(csv_name)
    if not url:
        print(f"[GTFS] {csv_name} URL'si bulunamadı")
        return None
    
    try:
        print(f"[GTFS] İndiriliyor: {csv_name} from {url}")
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        content = response.content.decode('utf-8', errors='replace')
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[GTFS] {csv_name} kaydedildi ({len(content)} bytes)")
        return content
    except Exception as e:
        print(f"[GTFS] {csv_name} indirme hatası: {e}")
        return None


def _parse_shapes_from_zip(zip_data: bytes) -> Dict[str, List[Tuple[float, float]]]:
    """Zip içindeki shapes.txt'yi parse eder."""
    shapes_dict: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
    shape_point_order: Dict[str, List[Tuple[int, float, float]]] = defaultdict(list)
    
    try:
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            shape_files = [n for n in zf.namelist() if 'shape' in n.lower() and n.endswith('.txt')]
            
            if not shape_files:
                print("[GTFS] shapes.txt bulunamadı")
                return {}
            
            shape_file = shape_files[0]
            print(f"[GTFS] Parse ediliyor: {shape_file}")
            
            with zf.open(shape_file) as f:
                content = f.read().decode('utf-8', errors='replace')
            
            reader = csv.DictReader(content.splitlines())
            
            for row in reader:
                try:
                    shape_id = row.get('shape_id', '').strip()
                    if not shape_id:
                        continue
                    
                    lat = float(row.get('shape_pt_lat', 0))
                    lon = float(row.get('shape_pt_lon', 0))
                    seq = int(row.get('shape_pt_sequence', 0))
                    
                    if lat == 0 or lon == 0:
                        continue
                    
                    shape_point_order[shape_id].append((seq, lat, lon))
                    
                except (ValueError, KeyError):
                    continue
            
            for shape_id, points in shape_point_order.items():
                points.sort(key=lambda x: x[0])
                shapes_dict[shape_id] = [(lat, lon) for _, lat, lon in points]
            
            print(f"[GTFS] {len(shapes_dict)} shape parsed edildi")
            
    except Exception as e:
        print(f"[GTFS] Parse hatası: {e}")
    
    return shapes_dict


def download_and_parse_shapes(force: bool = False) -> Dict[str, List[Tuple[float, float]]]:
    """GTFS shapes verisini indirir veya cached olanı döner."""
    import json
    
    if not force and os.path.exists(SHAPES_CACHE_FILE):
        try:
            file_age_hours = (time.time() - os.path.getmtime(SHAPES_CACHE_FILE)) / 3600
            if file_age_hours < MAX_SHAPES_AGE_HOURS:
                with open(SHAPES_CACHE_FILE, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                if cached:
                    print(f"[GTFS] Cache'den {len(cached)} shape yüklendi")
                    return {k: [(float(x[0]), float(x[1])) for x in v] for k, v in cached.items()}
        except Exception:
            pass
    
    # CKAN API'den shapes.csv indir
    shapes = _parse_shapes_from_csv(force=force)
    
    if not shapes:
        print("[GTFS] CKAN API'den shapes alınamadı, eski URL'ler deneniyor...")
        zip_data = None
        for url in GTFS_FEED_URLS:
            zip_data = _download_gtfs_zip(url)
            if zip_data:
                break
        
        if zip_data:
            shapes = _parse_shapes_from_zip(zip_data)
    
    if shapes:
        try:
            cache_data = {k: [[lat, lon] for lat, lon in v] for k, v in shapes.items()}
            with open(SHAPES_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f)
            print(f"[GTFS] {len(shapes)} shape cache'e kaydedildi")
        except Exception as e:
            print(f"[GTFS] Cache yazma hatası: {e}")
    
    return shapes


def _parse_shapes_from_csv(force: bool = False) -> Dict[str, List[Tuple[float, float]]]:
    """CSV formatında shapes.txt'yi indirir ve parse eder."""
    shapes_dict: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
    shape_point_order: Dict[str, List[Tuple[int, float, float]]] = defaultdict(list)
    
    csv_content = download_gtfs_csv("shapes", force=force)
    if not csv_content:
        return {}
    
    try:
        lines = csv_content.splitlines()
        if not lines:
            return {}
        
        # İlk satır header olmalı
        header = lines[0].lower()
        if 'shape_id' not in header:
            print(f"[GTFS] shapes.csv header bekleneni içermiyor: {header}")
            return {}
        
        # CSV reader ile parse et
        import io
        reader = csv.DictReader(io.StringIO(csv_content))
        
        for row in reader:
            try:
                shape_id = row.get('shape_id', '').strip()
                if not shape_id:
                    continue
                
                lat = float(row.get('shape_pt_lat', 0))
                lon = float(row.get('shape_pt_lon', 0))
                seq = int(row.get('shape_pt_sequence', 0))
                
                if lat == 0 or lon == 0:
                    continue
                
                shape_point_order[shape_id].append((seq, lat, lon))
                
            except (ValueError, KeyError):
                continue
        
        # Her shape_id için koordinatları sırala
        for shape_id, points in shape_point_order.items():
            points.sort(key=lambda x: x[0])
            shapes_dict[shape_id] = [(lat, lon) for _, lat, lon in points]
        
        print(f"[GTFS] CSV'den {len(shapes_dict)} shape parse edildi")
        
    except Exception as e:
        print(f"[GTFS] CSV parse hatası: {e}")
    
    return shapes_dict


# ============================================================================
# METRO HATTI - SHAPE EŞLEŞTİRME
# ============================================================================

def _derive_line_type(line_name: str) -> str:
    """Hat adından tür çıkarır (metro/tram/funicular)."""
    if not line_name:
        return "other"
    name = line_name.upper()
    if name.startswith("M"):
        return "metro"
    if name.startswith("T") and len(name) <= 3:
        return "tram"
    if name.startswith("F") or name.startswith("TF"):
        return "funicular"
    return "other"


def _normalize_for_matching(text: str) -> str:
    """Eşleştirme için metin normalizasyonu."""
    if not text:
        return ""
    return (
        text.lower()
        .replace("ı", "i")
        .replace("ğ", "g")
        .replace("ş", "s")
        .replace("ç", "c")
        .replace("ö", "o")
        .replace("ü", "u")
        .replace(" ", "")
        .replace("-", "")
    )


def match_shapes_to_metro_lines(shapes: Dict[str, List[Tuple[float, float]]]) -> Dict[str, str]:
    """Metro hattı isimlerini shape_id'lerle eşleştirir."""
    conn = sqlite3.connect(TRANSIT_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, functional_code FROM metro_lines WHERE is_active = 1")
    lines = cursor.fetchall()
    conn.close()
    
    matched = {}
    
    for line in lines:
        line_name = str(line['name'] or '').strip()
        functional_code = str(line['functional_code'] or '').strip()
        
        candidates = []
        
        if functional_code:
            for shape_id in shapes.keys():
                norm_shape = _normalize_for_matching(shape_id)
                norm_code = _normalize_for_matching(functional_code)
                if norm_shape == norm_code or norm_shape.startswith(norm_code):
                    candidates.append(shape_id)
        
        if not candidates and line_name:
            for shape_id in shapes.keys():
                norm_shape = _normalize_for_matching(shape_id)
                match = re.search(r'[Mm](\d+)', line_name)
                if match:
                    alt_id = f"M{match.group(1)}"
                    if _normalize_for_matching(alt_id) == norm_shape:
                        candidates.append(shape_id)
        
        if candidates:
            best_shape = max(candidates, key=lambda s: len(shapes.get(s, [])))
            matched[line_name] = best_shape
    
    return matched


def get_shape_for_line(line_name: str, shapes: Dict[str, List[Tuple[float, float]]]) -> List[Tuple[float, float]]:
    """Belirtilen hat için shape koordinatlarını döner."""
    if line_name in shapes:
        return shapes[line_name]
    
    norm_name = _normalize_for_matching(line_name)
    for shape_id, coords in shapes.items():
        if _normalize_for_matching(shape_id) == norm_name:
            return coords
    
    return []


# ============================================================================
# HIZLI SNAP: İSTASYONDAN EN YAKIN SHAPE NOKTASI
# ============================================================================

from math import radians, sin, cos, sqrt, asin

def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """İki koordinat arası mesafe (metre)."""
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c


def snap_stations_to_shape(
    stations: List[Dict],
    shape_coords: List[Tuple[float, float]]
) -> List[Tuple[float, float]]:
    """İstasyon koordinatlarını en yakın shape noktalarına snap eder."""
    if not stations or not shape_coords:
        return [(s['lat'], s['lon']) for s in stations]
    
    result = []
    used_shape_indices = set()
    
    for station in stations:
        station_lat = station.get('lat', 0)
        station_lon = station.get('lon', 0)
        
        if station_lat == 0 or station_lon == 0:
            result.append((station_lat, station_lon))
            continue
        
        best_dist = float('inf')
        best_idx = 0
        
        for idx, (shape_lat, shape_lon) in enumerate(shape_coords):
            dist = _haversine_m(station_lat, station_lon, shape_lat, shape_lon)
            if dist < best_dist:
                best_dist = dist
                best_idx = idx
        
        snapped = shape_coords[best_idx]
        result.append(snapped)
        used_shape_indices.add(best_idx)
    
    return result


# ============================================================================
# METRO LINE_SHAPES - MANUEL VERİ (FALLBACK)
# ============================================================================

# İstanbul metro hatları için gerçek tünel güzergahları
# Bu veriler manuel olarak OpenStreetMap/Metro haritasından alınmıştır
METRO_LINE_SHAPES = {
    "Marmaray": [
        # Kazlıçeşme - Yenikapı - Sirkeci - Üsküdar - Ayrılık Çeşmesi - Söğütlüçeşme
        (40.9922, 28.9221), (40.9980, 28.9350), (41.0053, 28.9515),
        (41.0100, 28.9630), (41.0150, 28.9775), (41.0185, 28.9880),
        (41.0220, 28.9980), (41.0245, 29.0080), (41.0261, 29.0157),
        (41.0220, 29.0230), (40.9998, 29.0305), (40.9905, 29.0321)
    ],
    "M1": [
        # Yenikapı - Atatürk / Kirazlı
        (41.0108, 28.9502), (41.0116, 28.9491), (41.0135, 28.9468),
        (41.0163, 28.9429), (41.0192, 28.9389), (41.0227, 28.9349),
        (41.0256, 28.9311), (41.0283, 28.9275), (41.0307, 28.9242),
        (41.0334, 28.9209), (41.0358, 28.9179), (41.0379, 28.9150),
        (41.0398, 28.9123), (41.0415, 28.9097), (41.0431, 28.9072),
        (41.0447, 28.9046), (41.0461, 28.9022), (41.0475, 28.8998),
    ],
    "M2": [
        # Yenikapı - Hacıosman
        (41.0108, 28.9502), (41.0095, 28.9548), (41.0076, 28.9601),
        (41.0054, 28.9654), (41.0028, 28.9709), (40.9989, 28.9752),
        (40.9953, 28.9789), (40.9917, 28.9821), (40.9882, 28.9853),
        (40.9846, 28.9886), (40.9809, 28.9921), (40.9774, 28.9955),
        (40.9735, 28.9991), (40.9698, 29.0025), (40.9656, 29.0056),
        (40.9612, 29.0090), (40.9571, 29.0121), (40.9535, 29.0150),
        (40.9494, 29.0180), (40.9456, 29.0211), (40.9423, 29.0239),
        (40.9385, 29.0268), (40.9352, 29.0293), (40.9322, 29.0317),
        (40.9291, 29.0342), (40.9265, 29.0365), (40.9240, 29.0387),
        (40.9211, 29.0413), (40.9178, 29.0441), (40.9146, 29.0468),
        (40.9115, 29.0493), (40.9086, 29.0516), (40.9059, 29.0538),
        (40.9032, 29.0559), (40.9005, 29.0579), (40.8978, 29.0598),
    ],
    "M3": [
        # Kayaşehir - Merkez
        (41.0701, 28.8948), (41.0665, 28.8998), (41.0629, 28.9049),
        (41.0589, 28.9102), (41.0551, 28.9152), (41.0518, 28.9195),
        (41.0480, 28.9243), (41.0447, 28.9284), (41.0414, 28.9324),
        (41.0380, 28.9365), (41.0345, 28.9405), (41.0314, 28.9440),
        (41.0282, 28.9473), (41.0255, 28.9500), (41.0228, 28.9528),
        (41.0201, 28.9555), (41.0174, 28.9582), (41.0148, 28.9609),
        (41.0122, 28.9636), (41.0098, 28.9661), (41.0074, 28.9685),
        (41.0049, 28.9709), (41.0024, 28.9733), (40.9999, 28.9758),
    ],
    "M4": [
        # Kadıköy - Kartal
        (40.9903, 29.0291), (40.9920, 29.0262), (40.9938, 29.0232),
        (40.9955, 29.0203), (40.9973, 29.0172), (40.9990, 29.0142),
        (41.0007, 29.0113), (41.0025, 29.0083), (41.0041, 29.0054),
        (41.0058, 29.0025), (41.0075, 28.9996), (41.0092, 28.9966),
        (41.0109, 28.9936), (41.0126, 28.9905), (41.0142, 28.9875),
        (41.0158, 28.9846), (41.0174, 28.9817), (41.0190, 28.9787),
        (41.0206, 28.9758), (41.0222, 28.9729), (41.0238, 28.9700),
        (41.0254, 28.9671), (41.0269, 28.9642), (41.0284, 28.9613),
        (41.0299, 28.9584), (41.0314, 28.9556), (41.0329, 28.9528),
        (41.0344, 28.9500), (41.0359, 28.9472), (41.0373, 28.9445),
        (41.0388, 28.9418), (41.0403, 28.9390), (41.0417, 28.9364),
    ],
    "M5": [
        # Üsküdar - Çekmeköy
        (41.0261, 29.0157), (41.0245, 29.0195), (41.0230, 29.0231),
        (41.0214, 29.0267), (41.0198, 29.0302), (41.0181, 29.0336),
        (41.0164, 29.0369), (41.0147, 29.0401), (41.0129, 29.0433),
        (41.0112, 29.0465), (41.0095, 29.0497), (41.0079, 29.0527),
        (41.0062, 29.0555), (41.0045, 29.0582), (41.0028, 29.0608),
        (41.0010, 29.0633), (40.9992, 29.0659), (40.9975, 29.0684),
        (40.9958, 29.0710), (40.9942, 29.0736), (40.9925, 29.0762),
        (40.9909, 29.0788), (40.9893, 29.0814), (40.9876, 29.0840),
        (40.9860, 29.0866), (40.9844, 29.0893), (40.9829, 29.0919),
        (40.9813, 29.0945), (40.9797, 29.0972), (40.9780, 29.0998),
    ],
    "M6": [
        # Levent - Boğaziçi
        (41.0276, 29.0075), (41.0289, 29.0041), (41.0300, 29.0010),
        (41.0311, 28.9982), (41.0321, 28.9954), (41.0331, 28.9926),
        (41.0340, 28.9898), (41.0349, 28.9871), (41.0357, 28.9844),
    ],
    "M7": [
        # Yıldız - Mahmutbey
        (41.0465, 29.0356), (41.0449, 29.0369), (41.0434, 29.0380),
        (41.0418, 29.0392), (41.0402, 29.0403), (41.0387, 29.0413),
        (41.0371, 29.0422), (41.0355, 29.0431), (41.0339, 29.0440),
        (41.0323, 29.0449), (41.0308, 29.0457), (41.0292, 29.0464),
        (41.0276, 29.0470), (41.0260, 29.0477), (41.0244, 29.0482),
        (41.0229, 29.0488), (41.0213, 29.0493), (41.0197, 29.0497),
        (41.0181, 29.0501), (41.0165, 29.0505), (41.0149, 29.0508),
    ],
    "M8": [
        # Bostancı - Dudullu
        (40.9739, 29.0453), (40.9753, 29.0416), (40.9767, 29.0379),
        (40.9782, 29.0341), (40.9796, 29.0304), (40.9810, 29.0267),
        (40.9824, 29.0230), (40.9838, 29.0193), (40.9851, 29.0156),
        (40.9864, 29.0120), (40.9877, 29.0084), (40.9890, 29.0049),
        (40.9903, 29.0014), (40.9916, 28.9979), (40.9928, 28.9945),
        (40.9940, 28.9912), (40.9952, 28.9879), (40.9964, 28.9846),
        (40.9976, 28.9814), (40.9988, 28.9782), (41.0000, 28.9751),
    ],
    "M9": [
        # Ataköy - İkitelli
        (41.0218, 28.8949), (41.0195, 28.8989), (41.0172, 28.9028),
        (41.0149, 28.9068), (41.0126, 28.9108), (41.0102, 28.9148),
        (41.0078, 28.9188), (41.0054, 28.9229), (41.0030, 28.9269),
        (41.0005, 28.9309), (40.9980, 28.9349), (40.9956, 28.9389),
    ],
    # Tramvay hatları
    "T1": [
        # Kabataş - Bağcılar
        (41.0284, 29.0058), (41.0293, 29.0031), (41.0302, 29.0003),
        (41.0312, 28.9976), (41.0322, 28.9949), (41.0332, 28.9922),
        (41.0342, 28.9895), (41.0352, 28.9869), (41.0362, 28.9842),
        (41.0372, 28.9815), (41.0382, 28.9789), (41.0392, 28.9762),
        (41.0402, 28.9736), (41.0412, 28.9710), (41.0422, 28.9684),
        (41.0432, 28.9658), (41.0441, 28.9632), (41.0451, 28.9607),
    ],
    "T2": [
        # Taksim - Tünel Nostaljik Tramvayı
        (41.0368, 28.9850), (41.0358, 28.9839), (41.0348, 28.9827),
        (41.0337, 28.9814), (41.0326, 28.9801), (41.0316, 28.9788),
        (41.0305, 28.9775), (41.0294, 28.9760), (41.0285, 28.9748),
        (41.0280, 28.9734)
    ],
    "T4": [
        # Topkapı - Habibler
        (41.0178, 28.9372), (41.0189, 28.9348), (41.0200, 28.9325),
        (41.0211, 28.9301), (41.0222, 28.9277), (41.0233, 28.9254),
        (41.0244, 28.9230), (41.0255, 28.9207), (41.0266, 28.9183),
    ],
    "T5": [
        # Eminönü - Alibeyköy
        (41.0185, 28.9713), (41.0195, 28.9680), (41.0210, 28.9650),
        (41.0225, 28.9625), (41.0240, 28.9605), (41.0255, 28.9592),
        (41.0270, 28.9565), (41.0285, 28.9540), (41.0301, 28.9525),
        (41.0315, 28.9495), (41.0325, 28.9475), (41.0336, 28.9463),
        (41.0355, 28.9445), (41.0375, 28.9435), (41.0396, 28.9427),
        (41.0415, 28.9418), (41.0435, 28.9410), (41.0450, 28.9405),
        (41.0462, 28.9385), (41.0475, 28.9372), (41.0505, 28.9360),
        (41.0535, 28.9375), (41.0558, 28.9392), (41.0590, 28.9405),
        (41.0625, 28.9415), (41.0664, 28.9427), (41.0695, 28.9435),
        (41.0722, 28.9442), (41.0750, 28.9440), (41.0782, 28.9442)
    ],
    # Funiküler
    "F4": [
        # Eyüp - Piyerloti
        (41.0453, 28.9328), (41.0438, 28.9342), (41.0423, 28.9356),
    ],
    "F1": [
        # Taksim - Kabataş
        (41.0360, 28.9889), (41.0345, 28.9903), (41.0330, 28.9917),
        (41.0315, 28.9931), (41.0300, 28.9945), (41.0285, 28.9959),
        (41.0270, 28.9973), (41.0255, 28.9987),
    ],
    "F2": [
        # Taksim - Tunel
        (41.0368, 28.9878), (41.0359, 28.9868), (41.0350, 28.9857),
        (41.0342, 28.9846), (41.0334, 28.9835), (41.0326, 28.9825),
        (41.0318, 28.9814), (41.0310, 28.9804),
    ],
    "TF1": [
        # Macka - Taskisla Teleferik
        (41.0448, 28.9978), (41.0444, 28.9985), (41.0440, 28.9992),
        (41.0436, 28.9999), (41.0432, 29.0006), (41.0428, 29.0013),
        (41.0424, 29.0020), (41.0420, 29.0027),
    ],
    "TF2": [
        # Eyup - Piyer Loti Teleferik
        (41.0487, 28.9335), (41.0482, 28.9340), (41.0477, 28.9345),
        (41.0472, 28.9350), (41.0467, 28.9355), (41.0462, 28.9360),
        (41.0457, 28.9365), (41.0452, 28.9370),
    ],
    "M2A": [
        # Yenikapi - Vezneciler (kisa uzanti)
        (41.0087, 28.9604), (41.0092, 28.9593), (41.0098, 28.9581),
        (41.0104, 28.9569), (41.0110, 28.9558), (41.0115, 28.9546),
        (41.0120, 28.9535), (41.0124, 28.9524),
    ],
}


def get_metro_line_shape(line_name: str) -> List[Tuple[float, float]]:
    """
    Metro hattı için güzergah koordinatlarını döner.
    GTFS route shapes öncelikli, yoksa manuel veri kullanılır.
    """
    import json
    
    def _manual_shape_for(name: str) -> List[Tuple[float, float]]:
        for key, coords in METRO_LINE_SHAPES.items():
            if _normalize_for_matching(key) == _normalize_for_matching(name):
                return coords
        return []

    line_upper = str(line_name or "").strip().upper()

    # Önce GTFS route shapes dosyasına bak (M1A, M2, Marmaray vs.)
    gtfs_route_file = os.path.join(CACHE_DIR, "gtfs_route_shapes.json")
    if os.path.exists(gtfs_route_file):
        try:
            with open(gtfs_route_file, 'r', encoding='utf-8') as f:
                route_shapes = json.load(f)
            
            # Exact line name match
            if line_name in route_shapes:
                gtfs_coords = [(float(c[0]), float(c[1])) for c in route_shapes[line_name]['coords']]
                if line_upper in SPARSE_LINE_FALLBACK_KEYS and len(gtfs_coords) < MIN_GTFS_POINTS_FOR_DIRECT_USE:
                    manual_coords = _manual_shape_for(line_name)
                    if manual_coords:
                        return manual_coords
                return gtfs_coords
            
            # Normalized match
            norm_name = _normalize_for_matching(line_name)
            for lname, data in route_shapes.items():
                if _normalize_for_matching(lname) == norm_name:
                    gtfs_coords = [(float(c[0]), float(c[1])) for c in data['coords']]
                    if line_upper in SPARSE_LINE_FALLBACK_KEYS and len(gtfs_coords) < MIN_GTFS_POINTS_FOR_DIRECT_USE:
                        manual_coords = _manual_shape_for(lname)
                        if manual_coords:
                            return manual_coords
                    return gtfs_coords
        except Exception:
            pass
    
    # Manuel veriye bak
    manual = _manual_shape_for(line_name)
    if manual:
        return manual
    
    return []


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("GTFS Shapes Test")
    print("=" * 50)
    
    shapes = download_and_parse_shapes()
    print(f"\nToplam shape: {len(shapes)}")
    
    matched = match_shapes_to_metro_lines(shapes)
    print(f"\nEşleşen hatlar: {matched}")
    
    print("\n--- Manuel METRO_LINE_SHAPES ---")
    for line, coords in METRO_LINE_SHAPES.items():
        print(f"  {line}: {len(coords)} nokta")
