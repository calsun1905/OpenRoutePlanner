"""
ibb_transit.py - İBB Toplu Ulaşım Veri Modülü

İETT SOAP API ile otobüs durak ve hat verilerini çeker,
SQLite veritabanına kaydeder ve hızlı sorgulama sağlar.

API: https://api.ibb.gov.tr/iett/UlasimAnaVeri/HatDurakGuzergah.asmx
Format: SOAP → JSON
"""

import os
import re
import json
import math
import time
import csv
import io
import hashlib
import sqlite3
import requests
from typing import List, Dict, Optional, Tuple, Any

# ============================================================================
# AYARLAR
# ============================================================================

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

TRANSIT_DB = os.path.join(CACHE_DIR, "transit.db")

IBB_API_URL = "https://api.ibb.gov.tr/iett/UlasimAnaVeri/HatDurakGuzergah.asmx"
METRO_API_BASE = "https://api.ibb.gov.tr/MetroIstanbul/api/MetroMobile/V2"
GTFS_CKAN_URL = "https://data.ibb.gov.tr/api/3/action/package_show?id=public-transport-gtfs-data"

# Rate limiting (IBB API aşırı yüklenmesin)
_last_request_time = 0.0
RATE_LIMIT_SECONDS = 0.3


# ============================================================================
# SOAP XML TEMPLATELERİ
# ============================================================================

def _soap_envelope(method: str, params: dict = None) -> str:
    """SOAP XML zarfı oluşturur."""
    params_xml = ""
    if params:
        for key, value in params.items():
            params_xml += f"<tns:{key}>{value}</tns:{key}>"

    return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:tns="http://tempuri.org/">
  <soap:Body>
    <tns:{method}>
      {params_xml}
    </tns:{method}>
  </soap:Body>
</soap:Envelope>"""


def _call_ibb_api(method: str, params: dict = None) -> str:
    """
    İBB SOAP API'ye istek gönderir.

    Args:
        method: SOAP metot adı (ör: GetDurak_json)
        params: Parametreler

    Returns:
        str: SOAP response body metni
    """
    global _last_request_time

    # Rate limiting
    elapsed = time.time() - _last_request_time
    if elapsed < RATE_LIMIT_SECONDS:
        time.sleep(RATE_LIMIT_SECONDS - elapsed)

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f"http://tempuri.org/{method}",
    }

    body = _soap_envelope(method, params)

    try:
        response = requests.post(
            IBB_API_URL,
            data=body.encode("utf-8"),
            headers=headers,
            timeout=30,
        )
        _last_request_time = time.time()

        if response.status_code != 200:
            print(f"[IBB API] HTTP {response.status_code}: {method}")
            return ""

        return response.text

    except requests.Timeout:
        print(f"[IBB API] Timeout: {method}")
        return ""
    except requests.ConnectionError:
        print(f"[IBB API] Bağlantı hatası: {method}")
        return ""
    except Exception as e:
        print(f"[IBB API] Hata: {e}")
        return ""


def _parse_json_from_soap(soap_response: str) -> list:
    """SOAP response'undan JSON verisini çıkarır."""
    if not soap_response:
        return []

    # JSON arrayı bul: [...] veya tekil {...}
    start = soap_response.find("[")
    end = soap_response.rfind("]") + 1

    if start < 0 or end <= start:
        # Tekil obje dene
        start = soap_response.find("{")
        end = soap_response.rfind("}") + 1
        if start < 0 or end <= start:
            return []
        json_str = soap_response[start:end]
        try:
            return [json.loads(json_str)]
        except json.JSONDecodeError:
            return []

    json_str = soap_response[start:end]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"[IBB API] JSON parse hatası: {e}")
        return []


# ============================================================================
# KOORDİNAT PARSE
# ============================================================================

def _parse_wkt_point(wkt: str) -> Tuple[float, float]:
    """
    WKT POINT formatını (lat, lon) tuple'a çevirir.
    Giriş:  "POINT (28.879 41.088)"  → (lon, lat) sırasında
    Çıkış:  (41.088, 28.879)         → (lat, lon) sırasında
    """
    if not wkt:
        return (0.0, 0.0)

    match = re.search(r"POINT\s*\(\s*([\d.]+)\s+([\d.]+)\s*\)", wkt)
    if match:
        lon = float(match.group(1))
        lat = float(match.group(2))
        return (lat, lon)

    return (0.0, 0.0)


def _fix_encoding(text: str) -> str:
    """İBB API'den gelen bozuk Türkçe karakterleri düzeltir."""
    if not text:
        return ""

    # Latin-1 → UTF-8 dönüşümü dene
    try:
        fixed = text.encode("latin-1").decode("utf-8")
        return fixed
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass

    return text


# ============================================================================
# SQLITE VERİTABANI
# ============================================================================

def _get_db_connection() -> sqlite3.Connection:
    """SQLite bağlantısı döner ve gerekli tabloları oluşturur."""
    conn = sqlite3.connect(TRANSIT_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stops (
            code INTEGER PRIMARY KEY,
            name TEXT,
            lat REAL,
            lon REAL,
            district TEXT,
            direction TEXT,
            stop_type TEXT,
            smart TEXT,
            accessible TEXT,
            physical TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            code TEXT PRIMARY KEY,
            name TEXT,
            fare_type TEXT,
            length_km REAL,
            duration_min REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS route_stops (
            route_code TEXT,
            stop_code INTEGER,
            stop_order INTEGER,
            direction TEXT,
            PRIMARY KEY (route_code, stop_code, direction),
            FOREIGN KEY (route_code) REFERENCES routes(code),
            FOREIGN KEY (stop_code) REFERENCES stops(code)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metro_lines (
            id INTEGER PRIMARY KEY,
            name TEXT,
            short_description TEXT,
            long_description TEXT,
            functional_code TEXT,
            is_active INTEGER,
            first_time TEXT,
            last_time TEXT,
            color_r INTEGER,
            color_g INTEGER,
            color_b INTEGER,
            line_type TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metro_stations (
            id INTEGER PRIMARY KEY,
            name TEXT,
            description TEXT,
            lat REAL,
            lon REAL,
            is_active INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metro_line_stations (
            line_id INTEGER,
            station_id INTEGER,
            station_order INTEGER,
            PRIMARY KEY (line_id, station_id),
            FOREIGN KEY (line_id) REFERENCES metro_lines(id),
            FOREIGN KEY (station_id) REFERENCES metro_stations(id)
        )
    """)

    # Spatial index (yakın durak sorgusu için)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stops_lat ON stops(lat)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stops_lon ON stops(lon)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stops_district ON stops(district)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_route_stops_route ON route_stops(route_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_route_stops_stop ON route_stops(stop_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metro_stations_lat ON metro_stations(lat)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metro_stations_lon ON metro_stations(lon)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metro_ls_line ON metro_line_stations(line_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metro_ls_station ON metro_line_stations(station_id)")

    conn.commit()
    return conn


def _is_data_fresh(max_age_hours: int = 24) -> bool:
    """Veritabanındaki veri yeterince güncel mi kontrol eder."""
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM meta WHERE key = 'last_download'")
        row = cursor.fetchone()
        conn.close()

        if not row:
            return False

        last_download = float(row["value"])
        age_hours = (time.time() - last_download) / 3600
        return age_hours < max_age_hours

    except Exception:
        return False


def _get_stop_count() -> int:
    """Veritabanındaki durak sayısını döner."""
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM stops")
        row = cursor.fetchone()
        conn.close()
        return row["cnt"] if row else 0
    except Exception:
        return 0


# ============================================================================
# VERİ İNDİRME
# ============================================================================

def download_all_stops(force: bool = False) -> int:
    """
    İBB API'den tüm İETT duraklarını indirir ve SQLite'a kaydeder.

    Args:
        force: True ise cache'i yoksay, yeniden indir

    Returns:
        int: Kaydedilen durak sayısı
    """
    # Cache kontrolü
    if not force and _is_data_fresh(max_age_hours=24):
        count = _get_stop_count()
        if count > 0:
            print(f"[Transit] Veri güncel: {count} durak mevcut")
            return count

    print("[Transit] Tüm duraklar indiriliyor...")

    # Tüm durakları çek (DurakKodu boş → tümü)
    raw = _call_ibb_api("GetDurak_json", {"DurakKodu": ""})
    stops_data = _parse_json_from_soap(raw)

    if not stops_data:
        print("[Transit] HATA: Durak verisi alınamadı!")
        return 0

    print(f"[Transit] {len(stops_data)} durak alındı, SQLite'a yazılıyor...")

    conn = _get_db_connection()
    cursor = conn.cursor()

    # Mevcut verileri temizle
    cursor.execute("DELETE FROM stops")

    saved_count = 0
    for stop in stops_data:
        try:
            code = int(stop.get("SDURAKKODU", 0))
            name = _fix_encoding(str(stop.get("SDURAKADI", "")))
            koordinat = str(stop.get("KOORDINAT", ""))
            lat, lon = _parse_wkt_point(koordinat)

            if code == 0 or (lat == 0 and lon == 0):
                continue

            district = _fix_encoding(str(stop.get("ILCEADI", "")))
            direction = _fix_encoding(str(stop.get("SYON", "")))
            stop_type = _fix_encoding(str(stop.get("DURAK_TIPI", "")))
            smart = str(stop.get("AKILLI", ""))
            accessible = _fix_encoding(str(stop.get("ENGELLIKULLANIM", "")))
            physical = _fix_encoding(str(stop.get("FIZIKI", "")))

            cursor.execute("""
                INSERT OR REPLACE INTO stops
                (code, name, lat, lon, district, direction, stop_type, smart, accessible, physical)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, name, lat, lon, district, direction, stop_type, smart, accessible, physical))

            saved_count += 1
        except Exception as e:
            continue

    # Meta bilgisi güncelle
    cursor.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        ("last_download", str(time.time()))
    )
    cursor.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        ("stop_count", str(saved_count))
    )

    conn.commit()
    conn.close()

    print(f"[Transit] [OK] {saved_count} durak SQLite'a kaydedildi!")
    return saved_count


def download_all_routes(force: bool = False) -> int:
    """
    İBB API'den tüm İETT hat bilgilerini indirir.

    Returns:
        int: Kaydedilen hat sayısı
    """
    print("[Transit] Tüm hatlar indiriliyor...")

    raw = _call_ibb_api("GetHat_json", {"HatKodu": ""})
    routes_data = _parse_json_from_soap(raw)

    if not routes_data:
        print("[Transit] HATA: Hat verisi alınamadı!")
        return 0

    print(f"[Transit] {len(routes_data)} hat alındı, SQLite'a yazılıyor...")

    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM routes")

    saved_count = 0
    for route in routes_data:
        try:
            code = str(route.get("SHATKODU", ""))
            name = _fix_encoding(str(route.get("SHATADI", "")))
            fare = _fix_encoding(str(route.get("TARIFE", "")))
            length_km = float(route.get("HAT_UZUNLUGU", 0) or 0)
            duration_min = float(route.get("SEFER_SURESI", 0) or 0)

            if not code:
                continue

            cursor.execute("""
                INSERT OR REPLACE INTO routes
                (code, name, fare_type, length_km, duration_min)
                VALUES (?, ?, ?, ?, ?)
            """, (code, name, fare, length_km, duration_min))

            saved_count += 1
        except Exception:
            continue

    conn.commit()
    conn.close()

    print(f"[Transit] [OK] {saved_count} hat SQLite'a kaydedildi!")
    return saved_count


def download_route_stops(max_routes: int = 200, force: bool = False) -> int:
    """
    Her hat icin durak siralamasini indirir ve route_stops tablosuna kaydeder.
    IBB ibb.asmx/DurakDetay_GYY endpointini kullanir (XML format).

    Args:
        max_routes: Maksimum islenecek hat sayisi
        force: True ise mevcut verileri sil ve yeniden indir

    Returns:
        int: Kaydedilen route_stop kayit sayisi
    """
    IBB_API_URL2 = "https://api.ibb.gov.tr/iett/ibb/ibb.asmx"

    conn = _get_db_connection()
    cursor = conn.cursor()

    # Mevcut veri kontrolu
    if not force:
        cursor.execute("SELECT COUNT(*) as cnt FROM route_stops")
        existing = cursor.fetchone()["cnt"]
        if existing > 0:
            print(f"[Transit] route_stops verisi mevcut: {existing} kayit")
            conn.close()
            return existing

    print(f"[Transit] Hat-durak eslesmeleri indiriliyor (max {max_routes} hat)...")

    # En uzun hatlari once isle (daha fazla durak kapsar)
    cursor.execute("""
        SELECT code FROM routes
        ORDER BY length_km DESC
        LIMIT ?
    """, (max_routes,))
    route_codes = [row["code"] for row in cursor.fetchall()]

    if not route_codes:
        print("[Transit] HATA: routes tablosu bos!")
        conn.close()
        return 0

    # Mevcut route_stops verilerini temizle
    cursor.execute("DELETE FROM route_stops")
    conn.commit()

    saved_count = 0
    processed = 0

    for route_code in route_codes:
        processed += 1

        # Her 50 hatta bir ilerleme goster
        if processed % 50 == 0:
            print(f"[Transit]   {processed}/{len(route_codes)} hat islendi ({saved_count} kayit)")

        try:
            # Rate limiting
            global _last_request_time
            elapsed = time.time() - _last_request_time
            if elapsed < RATE_LIMIT_SECONDS:
                time.sleep(RATE_LIMIT_SECONDS - elapsed)

            # SOAP request to ibb.asmx
            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:tns="http://tempuri.org/">
  <soap:Body>
    <tns:DurakDetay_GYY>
      <tns:hat_kodu>{route_code}</tns:hat_kodu>
    </tns:DurakDetay_GYY>
  </soap:Body>
</soap:Envelope>"""

            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/DurakDetay_GYY",
            }

            response = requests.post(
                IBB_API_URL2,
                data=soap_body.encode("utf-8"),
                headers=headers,
                timeout=15,
            )
            _last_request_time = time.time()

            if response.status_code != 200:
                continue

            xml_text = response.text

            # XML'den durak bilgilerini regex ile cek
            # Her <Table>...</Table> bir durak
            tables = re.findall(r"<Table>(.*?)</Table>", xml_text, re.DOTALL)

            for table in tables:
                try:
                    code_match = re.search(r"<DURAKKODU>(\d+)</DURAKKODU>", table)
                    order_match = re.search(r"<SIRANO>(\d+)</SIRANO>", table)
                    dir_match = re.search(r"<YON>([^<]+)</YON>", table)

                    if not code_match:
                        continue

                    stop_code = int(code_match.group(1))
                    stop_order = int(order_match.group(1)) if order_match else 0
                    direction = dir_match.group(1) if dir_match else "G"

                    cursor.execute("""
                        INSERT OR IGNORE INTO route_stops
                        (route_code, stop_code, stop_order, direction)
                        VALUES (?, ?, ?, ?)
                    """, (route_code, stop_code, stop_order, direction))

                    saved_count += 1
                except Exception:
                    continue

            # Her 10 hatta bir commit
            if processed % 10 == 0:
                conn.commit()

        except Exception as e:
            continue

    conn.commit()
    conn.close()

    print(f"[Transit] [OK] {saved_count} hat-durak eslesmesi kaydedildi!")
    return saved_count


def _metro_api_get(path: str, timeout: int = 35) -> Dict[str, Any]:
    """Metro API JSON response doner."""
    try:
        resp = requests.get(f"{METRO_API_BASE}/{path}", timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            return {}
        if not data.get("Success", False):
            return {}
        return data
    except Exception as e:
        print(f"[Metro API] GET {path} hatasi: {e}")
        return {}


def _derive_line_type(line_name: str) -> str:
    if not line_name:
        return "other"
    name = line_name.upper()
    if name.startswith("M"):
        return "metro"
    if name.startswith("T"):
        return "tram"
    if name.startswith("F") or name.startswith("TF"):
        return "funicular"
    return "other"


def _normalize_ascii_token(text: str) -> str:
    """Metni karsilastirma icin normalize eder."""
    if not text:
        return ""
    return (
        str(text)
        .strip()
        .lower()
        .replace("ı", "i")
        .replace("İ", "i")
        .replace("ğ", "g")
        .replace("Ğ", "g")
        .replace("ş", "s")
        .replace("Ş", "s")
        .replace("ç", "c")
        .replace("Ç", "c")
        .replace("ö", "o")
        .replace("Ö", "o")
        .replace("ü", "u")
        .replace("Ü", "u")
    )


def _gtfs_get_resource_url(resource_name: str) -> Optional[str]:
    """CKAN API uzerinden GTFS kaynak URL'sini bulur."""
    try:
        resp = requests.get(GTFS_CKAN_URL, timeout=40)
        if resp.status_code != 200:
            return None
        data = resp.json()
        resources = data.get("result", {}).get("resources", [])
        wanted = _normalize_ascii_token(resource_name).replace(".txt", "").replace(".csv", "")
        for r in resources:
            name = _normalize_ascii_token(str(r.get("name", ""))).replace(".txt", "").replace(".csv", "")
            if name == wanted:
                return r.get("url")
        return None
    except Exception:
        return None


def _gtfs_download_csv(resource_name: str, force: bool = False) -> Optional[str]:
    """GTFS CSV dosyasini indirir (cache destekli)."""
    cache_file = os.path.join(CACHE_DIR, f"gtfs_{resource_name}.csv")
    if (not force) and os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            pass

    url = _gtfs_get_resource_url(resource_name)
    if not url:
        return None

    last_err = None
    for _ in range(3):
        try:
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()
            content = resp.content.decode("utf-8", errors="replace")
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(content)
            return content
        except Exception as e:
            last_err = e
            time.sleep(1.2)

    print(f"[GTFS] {resource_name} indirilemedi: {last_err}")
    return None


def _stable_gtfs_station_id(stop_id: str) -> int:
    """GTFS stop_id icin deterministik, cakisma olasiligi dusuk integer ID."""
    digest = hashlib.sha1(str(stop_id).encode("utf-8", errors="ignore")).hexdigest()
    return 700000000 + (int(digest[:10], 16) % 200000000)


def sync_marmaray_from_gtfs(force: bool = False) -> Dict[str, int]:
    """
    IBB GTFS (routes/trips/stop_times/stops) uzerinden Marmaray hattini
    metro graph tablolarina ekler/gunceller.
    """
    if not force:
        try:
            conn = _get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM meta WHERE key = 'marmaray_gtfs_last_sync'")
            row = cursor.fetchone()
            if row:
                age_hours = (time.time() - float(row["value"])) / 3600
                if age_hours < 24:
                    cursor.execute("SELECT id FROM metro_lines WHERE functional_code = 'GTFS-MARMARAY' LIMIT 1")
                    line_row = cursor.fetchone()
                    if line_row:
                        line_id = int(line_row["id"])
                        cursor.execute("SELECT COUNT(*) as c FROM metro_line_stations WHERE line_id = ?", (line_id,))
                        link_count = int(cursor.fetchone()["c"])
                        conn.close()
                        if link_count >= 2:
                            return {
                                "marmaray_line_id": line_id,
                                "marmaray_stations": 0,
                                "marmaray_links": link_count,
                            }
                    else:
                        conn.close()
                else:
                    conn.close()
            else:
                conn.close()
        except Exception:
            pass

    routes_csv = _gtfs_download_csv("routes", force=force)
    trips_csv = _gtfs_download_csv("trips", force=force)
    stop_times_csv = _gtfs_download_csv("stop_times", force=force)
    stops_csv = _gtfs_download_csv("stops", force=force)
    if not routes_csv or not trips_csv or not stop_times_csv or not stops_csv:
        return {"marmaray_line_id": 0, "marmaray_stations": 0, "marmaray_links": 0}

    try:
        route_rows = list(csv.DictReader(io.StringIO(routes_csv)))
        trip_rows = list(csv.DictReader(io.StringIO(trips_csv)))
        stop_rows = list(csv.DictReader(io.StringIO(stops_csv)))
    except Exception as e:
        print(f"[GTFS] CSV parse hatasi: {e}")
        return {"marmaray_line_id": 0, "marmaray_stations": 0, "marmaray_links": 0}

    marmaray_route_ids = set()
    for r in route_rows:
        rid = str(r.get("route_id") or "").strip()
        short_name = _normalize_ascii_token(r.get("route_short_name") or "")
        long_name = _normalize_ascii_token(r.get("route_long_name") or "")
        desc = _normalize_ascii_token(r.get("route_desc") or "")
        if not rid:
            continue
        if "marmaray" in f"{short_name} {long_name} {desc}":
            marmaray_route_ids.add(rid)

    if not marmaray_route_ids:
        print("[GTFS] Marmaray route_id bulunamadi")
        return {"marmaray_line_id": 0, "marmaray_stations": 0, "marmaray_links": 0}

    marmaray_trip_ids = set()
    for t in trip_rows:
        if str(t.get("route_id") or "").strip() in marmaray_route_ids:
            tid = str(t.get("trip_id") or "").strip()
            if tid:
                marmaray_trip_ids.add(tid)

    if not marmaray_trip_ids:
        print("[GTFS] Marmaray trip_id bulunamadi")
        return {"marmaray_line_id": 0, "marmaray_stations": 0, "marmaray_links": 0}

    stop_times_by_trip: Dict[str, List[Tuple[int, str]]] = {}
    try:
        st_reader = csv.DictReader(io.StringIO(stop_times_csv))
        for row in st_reader:
            tid = str(row.get("trip_id") or "").strip()
            if tid not in marmaray_trip_ids:
                continue
            sid = str(row.get("stop_id") or "").strip()
            if not sid:
                continue
            try:
                seq = int(float(row.get("stop_sequence") or 0))
            except Exception:
                continue
            if tid not in stop_times_by_trip:
                stop_times_by_trip[tid] = []
            stop_times_by_trip[tid].append((seq, sid))
    except Exception as e:
        print(f"[GTFS] stop_times parse hatasi: {e}")
        return {"marmaray_line_id": 0, "marmaray_stations": 0, "marmaray_links": 0}

    best_trip_stops: List[str] = []
    best_score = (-1, -1)
    for _, seq_rows in stop_times_by_trip.items():
        if len(seq_rows) < 2:
            continue
        seq_rows.sort(key=lambda x: x[0])
        ordered: List[str] = []
        seen = set()
        for _, sid in seq_rows:
            if sid in seen:
                continue
            seen.add(sid)
            ordered.append(sid)
        if len(ordered) < 2:
            continue
        score = (len(ordered), len(seq_rows))
        if score > best_score:
            best_score = score
            best_trip_stops = ordered

    if len(best_trip_stops) < 2:
        print("[GTFS] Marmaray stop dizisi olusturulamadi")
        return {"marmaray_line_id": 0, "marmaray_stations": 0, "marmaray_links": 0}

    stop_lookup: Dict[str, Dict[str, Any]] = {}
    for row in stop_rows:
        sid = str(row.get("stop_id") or "").strip()
        if sid:
            stop_lookup[sid] = row

    # Parent station varsa onu tercih et (platform yerine istasyon node'u)
    canonical_stops: List[str] = []
    for sid in best_trip_stops:
        base = stop_lookup.get(sid, {})
        parent = str(base.get("parent_station") or "").strip()
        canonical = parent if parent else sid
        if canonical_stops and canonical_stops[-1] == canonical:
            continue
        canonical_stops.append(canonical)

    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM metro_lines WHERE functional_code = 'GTFS-MARMARAY' OR LOWER(name) = 'marmaray' ORDER BY id LIMIT 1"
    )
    row = cursor.fetchone()
    if row:
        marmaray_line_id = int(row["id"])
    else:
        cursor.execute("SELECT COALESCE(MAX(id), 0) as max_id FROM metro_lines")
        max_id = int(cursor.fetchone()["max_id"] or 0)
        marmaray_line_id = max(9000, max_id + 1)

    cursor.execute(
        """
        INSERT OR REPLACE INTO metro_lines
        (id, name, short_description, long_description, functional_code, is_active,
         first_time, last_time, color_r, color_g, color_b, line_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            marmaray_line_id,
            "Marmaray",
            "Marmaray",
            "Halkali-Gebze Marmaray Hatti (GTFS)",
            "GTFS-MARMARAY",
            1,
            "",
            "",
            20,
            83,
            45,
            "metro",
        ),
    )

    cursor.execute("DELETE FROM metro_line_stations WHERE line_id = ?", (marmaray_line_id,))

    inserted_stations = 0
    inserted_links = 0
    order = 1
    for sid in canonical_stops:
        stop = stop_lookup.get(sid) or {}
        if not stop:
            continue
        stop_name = _fix_encoding(str(stop.get("stop_name") or stop.get("stop_desc") or sid).strip())
        try:
            lat = float(stop.get("stop_lat") or 0)
            lon = float(stop.get("stop_lon") or 0)
        except Exception:
            continue
        if lat == 0 or lon == 0:
            continue
        if not (40.5 <= lat <= 41.5 and 27.5 <= lon <= 30.5):
            continue

        station_id = _stable_gtfs_station_id(sid)
        for _ in range(50):
            cursor.execute("SELECT name, description FROM metro_stations WHERE id = ?", (station_id,))
            existing = cursor.fetchone()
            if not existing:
                break
            existing_name = _normalize_ascii_token(existing["description"] or existing["name"] or "")
            if existing_name == _normalize_ascii_token(stop_name):
                break
            station_id += 1

        cursor.execute(
            """
            INSERT OR REPLACE INTO metro_stations
            (id, name, description, lat, lon, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (station_id, stop_name, stop_name, lat, lon, 1),
        )
        inserted_stations += 1

        cursor.execute(
            """
            INSERT OR REPLACE INTO metro_line_stations
            (line_id, station_id, station_order)
            VALUES (?, ?, ?)
            """,
            (marmaray_line_id, station_id, order),
        )
        inserted_links += 1
        order += 1

    cursor.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        ("marmaray_gtfs_last_sync", str(time.time())),
    )
    conn.commit()
    conn.close()

    print(
        f"[GTFS] Marmaray sync tamamlandi: line_id={marmaray_line_id}, "
        f"stations={inserted_stations}, links={inserted_links}"
    )
    return {
        "marmaray_line_id": marmaray_line_id,
        "marmaray_stations": inserted_stations,
        "marmaray_links": inserted_links,
    }


def download_metro_data(force: bool = False) -> Dict[str, int]:
    """
    Metro Istanbul API'den tum rayli sistem hat ve istasyonlarini indirir.
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    if not force:
        cursor.execute("SELECT value FROM meta WHERE key = 'metro_last_download'")
        row = cursor.fetchone()
        if row:
            try:
                age_hours = (time.time() - float(row["value"])) / 3600
                if age_hours < 24:
                    cursor.execute("SELECT COUNT(*) as c FROM metro_lines")
                    line_count = cursor.fetchone()["c"]
                    cursor.execute("SELECT COUNT(*) as c FROM metro_stations")
                    station_count = cursor.fetchone()["c"]
                    if line_count > 0 and station_count > 0:
                        conn.close()
                        return {
                            "metro_lines": int(line_count),
                            "metro_stations": int(station_count),
                            "metro_line_stations": 0,
                        }
            except Exception:
                pass

    lines_resp = _metro_api_get("GetLines")
    stations_resp = _metro_api_get("GetStations")
    lines = lines_resp.get("Data", []) if lines_resp else []
    stations = stations_resp.get("Data", []) if stations_resp else []

    if not lines or not stations:
        conn.close()
        return {"metro_lines": 0, "metro_stations": 0, "metro_line_stations": 0}

    cursor.execute("DELETE FROM metro_line_stations")
    cursor.execute("DELETE FROM metro_stations")
    cursor.execute("DELETE FROM metro_lines")

    inserted_lines = 0
    for line in lines:
        try:
            line_id = int(line.get("Id"))
            name = str(line.get("Name", "")).strip()
            color = line.get("Color") or {}
            cursor.execute(
                """
                INSERT OR REPLACE INTO metro_lines
                (id, name, short_description, long_description, functional_code, is_active,
                 first_time, last_time, color_r, color_g, color_b, line_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    line_id,
                    name,
                    str(line.get("ShortDescription", "")),
                    str(line.get("LongDescription", "")),
                    str(line.get("FunctionalCode", "")),
                    1 if bool(line.get("IsActive", True)) else 0,
                    str(line.get("FirstTime", "")),
                    str(line.get("LastTime", "")),
                    int(color.get("Color_R", 0) or 0),
                    int(color.get("Color_G", 0) or 0),
                    int(color.get("Color_B", 0) or 0),
                    _derive_line_type(name),
                ),
            )
            inserted_lines += 1
        except Exception:
            continue

    inserted_stations = 0
    inserted_links = 0
    for st in stations:
        try:
            station_id = int(st.get("Id"))
            line_id = int(st.get("LineId"))
            detail = st.get("DetailInfo") or {}
            lat = float(detail.get("Latitude", 0) or 0)
            lon = float(detail.get("Longitude", 0) or 0)
            if lat == 0 or lon == 0:
                continue
            cursor.execute(
                """
                INSERT OR REPLACE INTO metro_stations
                (id, name, description, lat, lon, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    station_id,
                    str(st.get("Name", "")),
                    str(st.get("Description", "")),
                    lat,
                    lon,
                    1 if bool(st.get("IsActive", True)) else 0,
                ),
            )
            inserted_stations += 1
            cursor.execute(
                """
                INSERT OR REPLACE INTO metro_line_stations
                (line_id, station_id, station_order)
                VALUES (?, ?, ?)
                """,
                (line_id, station_id, int(st.get("Order", 0) or 0)),
            )
            inserted_links += 1
        except Exception:
            continue

    cursor.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        ("metro_last_download", str(time.time())),
    )
    conn.commit()
    conn.close()

    print(
        f"[Metro] [OK] {inserted_lines} hat, {inserted_stations} istasyon, "
        f"{inserted_links} baglanti kaydedildi"
    )
    return {
        "metro_lines": inserted_lines,
        "metro_stations": inserted_stations,
        "metro_line_stations": inserted_links,
    }


def initialize_transit_data(force: bool = False) -> dict:
    """
    Transit verilerini baslatir (duraklar + hatlar + hat-durak eslesmeleri).
    Ilk calistirmada 1-2 dakika surebilir.

    Returns:
        dict: {"stops": int, "routes": int, "route_stops": int}
    """
    print("=" * 50)
    print("  IBB Transit Verileri Yukleniyor...")
    print("=" * 50)

    start_time = time.time()

    stop_count = download_all_stops(force=force)
    route_count = download_all_routes(force=force)
    route_stop_count = download_route_stops(max_routes=900, force=force)
    metro_result = download_metro_data(force=force)
    marmaray_result = sync_marmaray_from_gtfs(force=force)

    elapsed = round(time.time() - start_time, 1)
    print(f"[Transit] Toplam sure: {elapsed}s")
    print(
        f"[Transit] {stop_count} durak, {route_count} hat, {route_stop_count} esleme, "
        f"{metro_result.get('metro_lines', 0)} metro hatti yuklendi, "
        f"Marmaray link: {marmaray_result.get('marmaray_links', 0)}"
    )

    return {
        "stops": stop_count,
        "routes": route_count,
        "route_stops": route_stop_count,
        **metro_result,
        **marmaray_result,
    }


# ============================================================================
# SORGULAMA FONKSİYONLARI
# ============================================================================

def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """İki koordinat arası mesafe (metre)."""
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def get_stops_in_area(lat: float, lon: float, radius_m: float = 500) -> List[Dict]:
    """
    Belirtilen koordinat etrafındaki durakları döner.

    Args:
        lat, lon: Merkez koordinat
        radius_m: Yarıçap (metre)

    Returns:
        Yakındaki duraklar listesi (mesafeye göre sıralı)
    """
    # Bounding box hesapla (hızlı ön filtreleme)
    delta_lat = radius_m / 111000  # ~111km per degree
    delta_lon = radius_m / (111000 * math.cos(math.radians(lat)))

    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT code, name, lat, lon, district, direction, stop_type, smart, accessible
        FROM stops
        WHERE lat BETWEEN ? AND ?
          AND lon BETWEEN ? AND ?
    """, (lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon))

    rows = cursor.fetchall()
    conn.close()

    # Haversine ile gerçek mesafe filtrele
    results = []
    for row in rows:
        dist = _haversine_distance(lat, lon, row["lat"], row["lon"])
        if dist <= radius_m:
            results.append({
                "code": row["code"],
                "name": row["name"],
                "lat": row["lat"],
                "lon": row["lon"],
                "district": row["district"],
                "direction": row["direction"],
                "stop_type": row["stop_type"],
                "smart": row["smart"],
                "accessible": row["accessible"],
                "distance_m": round(dist),
            })

    # Mesafeye göre sırala
    results.sort(key=lambda x: x["distance_m"])
    return results


def search_stops(query: str, limit: int = 20) -> List[Dict]:
    """
    Durak adı ile arama yapar.

    Args:
        query: Arama metni
        limit: Maksimum sonuç

    Returns:
        Eşleşen duraklar listesi
    """
    if not query or len(query) < 2:
        return []

    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT code, name, lat, lon, district, direction, stop_type
        FROM stops
        WHERE name LIKE ? OR district LIKE ?
        LIMIT ?
    """, (f"%{query}%", f"%{query}%", limit))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_route_info(route_code: str) -> Optional[Dict]:
    """
    Hat detay bilgisini döner.

    Args:
        route_code: Hat kodu (ör: "500T")

    Returns:
        Hat bilgileri veya None
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM routes WHERE code = ?", (route_code,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)

    # Cache'te yoksa API'den çek
    raw = _call_ibb_api("GetHat_json", {"HatKodu": route_code})
    data = _parse_json_from_soap(raw)

    if data:
        route = data[0]
        return {
            "code": str(route.get("SHATKODU", "")),
            "name": _fix_encoding(str(route.get("SHATADI", ""))),
            "fare_type": _fix_encoding(str(route.get("TARIFE", ""))),
            "length_km": float(route.get("HAT_UZUNLUGU", 0) or 0),
            "duration_min": float(route.get("SEFER_SURESI", 0) or 0),
        }

    return None


def get_routes_for_stop(stop_code: int) -> List[Dict]:
    """
    Bir duraktan geçen tüm hatları döner.

    Önce route_stops tablosuna bakar, yoksa API'den çeker.
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.code, r.name, r.fare_type, r.length_km, r.duration_min
        FROM route_stops rs
        JOIN routes r ON rs.route_code = r.code
        WHERE rs.stop_code = ?
        ORDER BY r.code
    """, (stop_code,))

    rows = cursor.fetchall()
    conn.close()

    if rows:
        return [dict(row) for row in rows]

    # Cache'te yoksa bilgi yok, boş döndür
    return []


def find_connecting_routes(stop_a: int, stop_b: int) -> List[Dict]:
    """
    İki durak arası direkt bağlantı olan hatları bulur.

    Args:
        stop_a: Başlangıç durak kodu
        stop_b: Bitiş durak kodu

    Returns:
        Ortak hatlar listesi
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT rs1.route_code, r.name, r.length_km, r.duration_min
        FROM route_stops rs1
        JOIN route_stops rs2 ON rs1.route_code = rs2.route_code
        JOIN routes r ON rs1.route_code = r.code
        WHERE rs1.stop_code = ? AND rs2.stop_code = ?
    """, (stop_a, stop_b))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_metro_stations_in_area(lat: float, lon: float, radius_m: float = 800) -> List[Dict]:
    """Belirtilen koordinata yakin metro/rayli sistem istasyonlarini doner."""
    delta_lat = radius_m / 111000
    delta_lon = radius_m / (111000 * max(0.1, math.cos(math.radians(lat))))

    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ms.id, ms.name, ms.description, ms.lat, ms.lon
        FROM metro_stations ms
        WHERE ms.lat BETWEEN ? AND ?
          AND ms.lon BETWEEN ? AND ?
        """,
        (lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon),
    )
    rows = cursor.fetchall()
    conn.close()

    out = []
    for row in rows:
        dist = _haversine_distance(lat, lon, row["lat"], row["lon"])
        if dist <= radius_m:
            out.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "lat": row["lat"],
                    "lon": row["lon"],
                    "distance_m": round(dist),
                }
            )
    out.sort(key=lambda x: x["distance_m"])
    return out


def get_metro_lines_for_station(station_id: int) -> List[Dict]:
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ml.id, ml.name, ml.long_description, ml.line_type, ml.is_active
        FROM metro_line_stations mls
        JOIN metro_lines ml ON ml.id = mls.line_id
        WHERE mls.station_id = ?
        ORDER BY ml.name
        """,
        (station_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_metro_line_stations(line_id: int) -> List[Dict]:
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ms.id, ms.name, ms.description, ms.lat, ms.lon, mls.station_order
        FROM metro_line_stations mls
        JOIN metro_stations ms ON ms.id = mls.station_id
        WHERE mls.line_id = ?
        ORDER BY mls.station_order
        """,
        (line_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_statistics() -> dict:
    """Transit verisi istatistikleri."""
    conn = _get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM stops")
    stop_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM routes")
    route_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(DISTINCT district) as cnt FROM stops WHERE district != ''")
    district_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT value FROM meta WHERE key = 'last_download'")
    row = cursor.fetchone()
    last_download = float(row["value"]) if row else 0

    cursor.execute("SELECT COUNT(*) as cnt FROM metro_lines")
    metro_line_count = cursor.fetchone()["cnt"]
    cursor.execute("SELECT COUNT(*) as cnt FROM metro_stations")
    metro_station_count = cursor.fetchone()["cnt"]

    conn.close()

    return {
        "stops": stop_count,
        "routes": route_count,
        "districts": district_count,
        "metro_lines": metro_line_count,
        "metro_stations": metro_station_count,
        "last_download": last_download,
        "data_fresh": _is_data_fresh(),
    }


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("IBB Transit Test")
    print("=" * 50)

    # 1. Veri indir
    result = initialize_transit_data()
    print(f"\nSonuç: {result}")

    # 2. Yakın durak sorgusu (Kadıköy)
    print("\n--- Kadıköy yakını duraklar ---")
    stops = get_stops_in_area(40.9903, 29.0291, 300)
    for s in stops[:5]:
        print(f"  {s['code']} | {s['name']} | {s['distance_m']}m | {s['district']}")

    # 3. Durak arama
    print("\n--- 'moda' araması ---")
    results = search_stops("moda")
    for r in results[:5]:
        print(f"  {r['code']} | {r['name']} | {r['district']}")

    # 4. İstatistik
    print(f"\nİstatistik: {get_statistics()}")
