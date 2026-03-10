"""
app.py - Flask API Sunucusu

Frontend ile Backend arasındaki köprü.
Rota optimizasyonu ve POI arama endpoint'leri sağlar.
"""
import os

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_compress import Compress
from graph_manager import (
    get_graph,
    get_graph_for_points,
    search_pois,
    preload_popular_regions,
    is_preloaded,
    get_preloaded_graph
)
from geocoder import geocode, reverse_geocode, geocode_batch, geocode_suggest, purge_old_geocodes
from route_engine import (
    solve_tsp,
    build_full_route,
    build_alternative_routes,
    build_all_alternative_routes_batch,
    nodes_to_coords,
    calculate_route_stats,
    generate_google_maps_link,
)
from route_storage import (
    save_route,
    get_route,
    get_all_routes,
    get_routes_count,
    update_route,
    delete_route,
    toggle_favorite,
    search_routes,
    get_statistics,
)
from time_planner import (
    create_timeline,
    format_duration,
    check_time_conflicts,
    optimize_schedule,
)
from location_storage import (
    save_location,
    get_all_locations,
    get_locations_count,
    update_location,
    delete_location,
    toggle_location_favorite,
)
from storage_db import ensure_db, run_sqlite_maintenance
from nlp_engine import parse_query as regex_parse_query
from cache_manager import get_graph_cache, get_poi_cache

# Hava durumu servisi (OpenMeteo API entegrasyonu)
try:
    from weather_service import (
        get_current_weather,
        get_hourly_forecast,
        check_route_weather,
        get_service_status,
        clear_cache as clear_weather_cache,
        health_check as weather_health_check
    )
    WEATHER_SERVICE_AVAILABLE = True
    print("[app.py] Hava durumu servisi yüklendi")
except ImportError as e:
    WEATHER_SERVICE_AVAILABLE = False
    print(f"[app.py] Hava durumu servisi bulunamadı: {str(e)} [WARN]")

# BERT NLP Engine (opsiyonel - kurulu değilse regex fallback kullanılır)
try:
    from bert_nlp_engine import get_bert_nlp_engine, is_bert_available
    BERT_NLP_AVAILABLE = is_bert_available()
    _BERT_NLP_ERROR = None
    if BERT_NLP_AVAILABLE:
        print("[app.py] BERT NLP Engine yüklendi")
    else:
        print("[app.py] BERT NLP Engine bulunamadı, regex fallback aktif [WARN]")
except ImportError as e:
    BERT_NLP_AVAILABLE = False
    _BERT_NLP_ERROR = str(e)
    print("[app.py] BERT NLP Engine modülü bulunamadı, regex fallback aktif [WARN]")

# Frontend klasörünün yolu
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)  # Frontend'den gelen isteklere izin ver
Compress(app)  # gzip compression aktif et - %60-70 bandwidth tasarrufu

# Global değişkenler: LRU cache manager
_graph_cache_manager = get_graph_cache()
_poi_cache_manager = get_poi_cache()
_startup_initialized = False


def initialize_runtime() -> None:
    """
    Calisma zamani baslangic gorevlerini bir kez calistirir.
    Flask calisma seklinden bagimsiz olarak ayni davranir.
    """
    global _startup_initialized
    if _startup_initialized:
        return

    ensure_db(run_analyze=True)
    run_sqlite_maintenance(checkpoint_mode="PASSIVE")
    purge_old_geocodes(days=90)

    # Populer bölgelerin grafilerini ön yükle
    # İlk rota hesaplamalarını %80 daha hızlı yapar
    preload_popular_regions()

    _startup_initialized = True



def _get_cached_graph(place_name: str):
    """
    Graf objesini LRU cache'te alır (uygulama içi).
    Önce preload kontrolü yapar, sonra LRU cache'e bakar, en son disk'ten okur.
    """
    # Önce LRU cache'ten kontrol et
    graph = _graph_cache_manager.get(place_name)
    if graph is not None:
        return graph

    # Disk'ten yükle ve cache'e ekle
    graph = get_graph(place_name)
    _graph_cache_manager.put(place_name, graph)
    return graph

initialize_runtime()


def _disable_bert_runtime(exc: Exception) -> None:
    """Runtime'da BERT kullanılamaz hale geldiğinde fallback moduna geç."""
    global BERT_NLP_AVAILABLE, _BERT_NLP_ERROR
    BERT_NLP_AVAILABLE = False
    _BERT_NLP_ERROR = str(exc)
    print(f"[NLP WARN] BERT devre dışı bırakıldı: {_BERT_NLP_ERROR}")


def _build_regex_fallback_result(query: str) -> dict:
    """Regex parser sonucunu BERT endpoint sözleşmesine uyarlar."""
    result = regex_parse_query(query)
    result["detected_places"] = result.get("detected_places", [])
    result["parse_time"] = float(result.get("parse_time", 0.0) or 0.0)
    result["engine"] = "regex-fallback"
    return result



@app.route("/api/get-route", methods=["POST"])
def api_get_route():
    """
    Koordinat listesi alır, optimize edilmiş rota döner.
    
    Request Body:
        {
            "points": [[lat, lon], [lat, lon], ...],
            "place": "Kadikoy, Istanbul, Turkey"  (opsiyonel, varsayılan Kadıköy),
            "route_type": "route_1" | "route_2" | "route_3"  (opsiyonel, varsayılan route_1)
        }
    
    Response:
        {
            "optimized_order": [0, 2, 1, ...],
            "route_coords": [[lat, lon], ...],
            "total_distance_km": 4.5,
            "estimated_walk_minutes": 55,
            "google_maps_link": "https://..."
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data or "points" not in data:
            return jsonify({"error": "Geçersiz istek: 'points' alanı gerekli."}), 400

        points = data["points"]
        optimize = data.get("optimize", False)  # Varsayılan: sıralı bağla
        route_type = data.get("route_type", "route_1")  # route_1, route_2, route_3

        print(f"[API] Get-route: {len(points)} nokta, optimize={optimize}, route_type={route_type}")

        # Eski tip compatibility
        if route_type == "shortest": route_type = "route_1"
        elif route_type == "fastest": route_type = "route_2"
        elif route_type == "balanced": route_type = "route_3"

        # Validasyon
        if not isinstance(points, list) or len(points) < 2:
            return jsonify({"error": "En az 2 nokta gereklidir."}), 400

        for i, p in enumerate(points):
            if not isinstance(p, list) or len(p) != 2:
                return jsonify({"error": f"Nokta {i} geçersiz format. [lat, lon] olmalı."}), 400
            try:
                float(p[0])
                float(p[1])
            except (ValueError, TypeError):
                return jsonify({"error": f"Nokta {i} geçersiz koordinat."}), 400

        # 1) Seçilen noktaları kapsayan grafı al (otomatik bölge algılama)
        point_tuples = [(p[0], p[1]) for p in points]
        # print(f"[API] Noktalar için graf alınıyor: {len(points)} nokta"))
        G = get_graph_for_points(point_tuples)

        # 2) Sıralama: TSP optimizasyonu veya kullanıcı sırası
        if optimize and len(point_tuples) > 2:
            # print(f"[API] TSP çözülüyor: {len(points)} nokta"))
            optimized_order = solve_tsp(G, point_tuples)
        else:
            # print(f"[API] Sıralı rota: {len(points)} nokta"))
            optimized_order = list(range(len(point_tuples)))

        # 3) Sıralanmış noktalar
        ordered_points = [point_tuples[i] for i in optimized_order]

        # 4) Tam rotayı oluştur (alternatif rota tipi ile)
        # route_type "route_1"|"route_2"|"route_3" string -> route_index 0|1|2 int (build_alternative_routes int bekliyor)
        route_index = {"route_1": 0, "route_2": 1, "route_3": 2}.get(route_type, 0)
        route_nodes = build_alternative_routes(G, ordered_points, route_index)

        if not route_nodes:
            return jsonify({"error": "Rota hesaplanamadı. Noktalar harita alanı dışında olabilir."}), 400

        # 5) Koordinatlara çevir
        route_coords = nodes_to_coords(G, route_nodes)

        # 6) İstatistikler
        stats = calculate_route_stats(G, route_nodes)

        # 7) Google Maps linki
        maps_link = generate_google_maps_link(ordered_points)

        response = {
            "optimized_order": optimized_order,
            "route_coords": route_coords,
            "total_distance_km": stats["total_distance_km"],
            "estimated_walk_minutes": stats["estimated_walk_minutes"],
            "google_maps_link": maps_link,
            "route_type": route_type,
        }

        print(f"[API] Rota tamamlandi: {stats['total_distance_km']}km, {stats['estimated_walk_minutes']}dk")
        return jsonify(response)

    except Exception as e:
        print(f"[API] Hata: {e}")
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/get-alternative-routes", methods=["POST"])
def api_get_alternative_routes():
    """
    Aynı noktalar için 3 farklı alternatif rota döner.

    Basit sistem:
    - 3 rota: "Rota 1", "Rota 2", "Rota 3"
    - Hepsi kısa rotaya yakın mesafede
    - Geometrik olarak farklı sokaklardan geçer

    Request Body:
        {
            "points": [[lat, lon], [lat, lon], ...],
            "optimize": true/false
        }

    Response:
        {
            "alternatives": [
                {
                    "type": "route_1",
                    "name": "Rota 1",
                    "icon": "@",
                    "route_coords": [[lat, lon], ...],
                    "distance_km": 4.5,
                    "duration_minutes": 55,
                    "description": "4.5 km"
                },
                {
                    "type": "route_2",
                    "name": "Rota 2",
                    "icon": "@",
                    ...
                },
                {
                    "type": "route_3",
                    "name": "Rota 3",
                    "icon": "@",
                    ...
                }
            ]
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data or "points" not in data:
            return jsonify({"error": "Geçersiz istek: 'points' alanı gerekli."}), 400

        points = data["points"]
        optimize = data.get("optimize", False)

        print(f"[API] Get-alternative-routes: {len(points)} nokta, optimize={optimize}")

        # Validasyon
        if not isinstance(points, list) or len(points) < 2:
            return jsonify({"error": "En az 2 nokta gereklidir."}), 400

        point_tuples = [(p[0], p[1]) for p in points]

        G = get_graph_for_points(point_tuples)

        # TSP optimizasyonu
        if optimize and len(point_tuples) > 2:
            optimized_order = solve_tsp(G, point_tuples)
        else:
            optimized_order = list(range(len(point_tuples)))

        ordered_points = [point_tuples[i] for i in optimized_order]

        # PERFORMANS: Segment alternatifleri tek seferde hesaplanır (3x yerine 1x)
        try:
            batch_results = build_all_alternative_routes_batch(G, ordered_points)
        except Exception as e:
            print(f"[API] Alternatif rota batch hatası: {e}")
            batch_results = []

        alternatives = []
        for alt in batch_results:
            route_coords = nodes_to_coords(G, alt["nodes"])
            alternatives.append({
                "type": alt["type"],
                "name": alt["name"],
                "icon": alt["icon"],
                "route_coords": route_coords,
                "distance_km": alt["distance_km"],
                "duration_minutes": alt["duration_minutes"],
                "description": alt["description"],
                "google_maps_link": generate_google_maps_link(ordered_points)
            })

        if not alternatives:
            return jsonify({"error": "Hiçbir alternatif rota hesaplanamadı."}), 400

        # Aynı rotaları filtrele: Birebir aynı koordinat listesi = tek rota
        def _coords_equal(a, b):
            if len(a) != len(b):
                return False
            for i in range(len(a)):
                if abs(a[i][0] - b[i][0]) > 1e-6 or abs(a[i][1] - b[i][1]) > 1e-6:
                    return False
            return True

        unique = []
        for alt in alternatives:
            if not any(_coords_equal(alt["route_coords"], u["route_coords"]) for u in unique):
                unique.append(alt)

        print(f"[API] {len(unique)} alternatif rota")
        return jsonify({"alternatives": unique})

    except Exception as e:
        print(f"[API] Hata: {e}")
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/search-pois", methods=["POST"])
def api_search_pois():
    """
    Belirtilen bölgede POI arar.
    
    Request Body:
        {
            "place": "Kadikoy, Istanbul, Turkey",
            "category": "museum"
        }
    
    Response:
        {
            "pois": [
                {"name": "...", "lat": ..., "lon": ..., "category": "museum"},
                ...
            ]
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data or "category" not in data:
            return jsonify({"error": "'category' alanı gerekli."}), 400

        place = data.get("place", "Kadikoy, Istanbul, Turkey")
        category = data["category"]

        print(f"[API] Search-pois: {place}, kategori={category}")

        from osm_poi_dictionary import POI_MAPPING

        # Validasyon: Eğer kelime sözlükte yoksa ve önceden tanımlanmış bir ingilizce anahtar değilse hata verilebilir.
        # Ancak esneklik için sadece sözlük kontrolü yapalım. Eğer backend'de yoksa, fallback tag ile çalışır.
        if category.lower() not in POI_MAPPING and not category.isascii():
            pass # We will allow any category phrase that could be matched, to avoid failing valid English OSM categories too.

        # LRU cache kullan
        pois = _poi_cache_manager.get(place, category)
        if pois is None:
            pois = search_pois(place, category)
            _poi_cache_manager.put(place, category, pois)

        print(f"[API] {len(pois)} POI bulundu")
        return jsonify({"pois": pois})

    except Exception as e:
        # print(f"[API] POI arama hatası: {e}"))
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """Sunucu sağlık kontrolü."""
    return jsonify({"status": "ok", "message": "OpenTrip API çalışıyor!"})


@app.route("/api/geocode/suggest", methods=["GET"])
def api_geocode_suggest():
    """
    Yazarken öneri için: Kısmi yer ismi -> coklu sonuc doner (autocomplete).

    Query: ?q=Kadıköy&limit=6
    """
    try:
        q = request.args.get("q", "").strip()
        limit = min(int(request.args.get("limit", 6)), 10)
        result = geocode_suggest(q, limit=limit)
        return jsonify(result)
    except Exception as e:
        print(f"[API] Geocode suggest hatası: {e}")
        return jsonify({"status": "success", "suggestions": []})


@app.route("/api/geocode", methods=["POST"])
def api_geocode():
    """
    Yer ismini koordinata çevirir.

    Request Body:
        {
            "place": "Kadıköy Parkı, İstanbul"
        }

    Response:
        {
            "status": "success",
            "lat": 40.990,
            "lon": 29.029,
            "display_name": "Kadıköy Parkı, İstanbul, Türkiye",
            "cached": false
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data or "place" not in data:
            return jsonify({"error": "'place' alanı gerekli."}), 400

        place_name = data["place"]

        print(f"[API] Geocode: {place_name}")

        result = geocode(place_name)

        if result["status"] == "error":
            print(f"[API] Geocode HATA: {result['message']}")
            return jsonify(result), 404

        print(f"[API] Geocode Sonuc: ({result['lat']:.6f}, {result['lon']:.6f})")
        return jsonify(result)

    except Exception as e:
        print(f"[API] Geocode hatası: {e}")
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/reverse-geocode", methods=["POST"])
def api_reverse_geocode():
    """
    Koordinatı yer ismine çevirir.

    Request Body:
        {
            "lat": 40.990,
            "lon": 29.029
        }

    Response:
        {
            "status": "success",
            "display_name": "Kadıköy, İstanbul, Türkiye",
            "address": "{...}",
            "cached": false
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data or "lat" not in data or "lon" not in data:
            return jsonify({"error": "'lat' ve 'lon' alanları gerekli."}), 400

        lat = data["lat"]
        lon = data["lon"]
        result = reverse_geocode(lat, lon)

        if result["status"] == "error":
            return jsonify(result), 404

        return jsonify(result)

    except Exception as e:
        print(f"[API] Reverse geocode hatası: {e}")
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/geocode/batch", methods=["POST"])
def api_geocode_batch():
    """
    Toplu geocoding işlemi.

    Request Body:
        {
            "places": ["Kadıköy", "Beşiktaş", "Taksim"]
        }

    Response:
        {
            "results": [
                {"status": "success", "lat": 40.99, "lon": 29.03, ...},
                {"status": "success", "lat": 41.04, "lon": 29.00, ...},
                ...
            ]
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data or "places" not in data:
            return jsonify({"error": "'places' alanı gerekli (liste)."}), 400

        places = data["places"]

        if not isinstance(places, list):
            return jsonify({"error": "'places' bir liste olmalı."}), 400

        if len(places) > 10:
            return jsonify({"error": "En fazla 10 yer adı aynı anda işlenebilir."}), 400

        results = geocode_batch(places)
        return jsonify({"results": results})

    except Exception as e:
        print(f"[API] Batch geocode hatası: {e}")
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/")
def serve_frontend():
    """Ana sayfa - Frontend'i sun."""
    response = send_from_directory(FRONTEND_DIR, "index.html")
    # HTML dosyası için cache header (kısa süre)
    response.headers["Cache-Control"] = "public, max-age=300"  # 5 dakika
    return response


@app.route("/<path:filepath>")
def serve_static_files(filepath):
    """
    Statik dosyaları sun (CSS, JS, görseller vb.).
    Cache headers ile daha hızlı yüklenme.
    """
    response = send_from_directory(FRONTEND_DIR, filepath)

    # Dosya uzantısına göre cache süresi belirle
    if filepath.endswith((".css", ".js")):
        # CSS/JS dosyaları 1 saat cache
        response.headers["Cache-Control"] = "public, max-age=3600"
    elif filepath.endswith((".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp")):
        # Görsel dosyalar 1 gün cache
        response.headers["Cache-Control"] = "public, max-age=86400"
    else:
        # Diğer dosyalar 5 dakika cache
        response.headers["Cache-Control"] = "public, max-age=300"

    return response


# =============================================================================
# ROTA KAYDETME VE YÜKLEME API'LERİ
# =============================================================================

@app.route("/api/routes/save", methods=["POST"])
def api_save_route():
    """
    Rotayı kaydeder.
    
    Request Body:
        {
            "name": "Kadıköy Turu",
            "description": "Kadıköy'de gezilecek yerler",
            "points": [[lat, lon], ...],
            "route_coords": [[lat, lon], ...],
            "distance_km": 4.5,
            "duration_minutes": 55,
            "route_type": "shortest",
            "tags": ["tarihi", "kültürel"]
        }
    
    Response:
        {
            "status": "success",
            "route": {...},
            "message": "Rota kaydedildi"
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "Geçersiz veya eksik JSON gövdesi."}), 400
        
        # Zorunlu alanlar
        required_fields = ["name", "points", "route_coords", "distance_km", "duration_minutes"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"'{field}' alanı gerekli."}), 400
        
        # Rotayı kaydet
        route = save_route(
            name=data["name"],
            points=data["points"],
            route_coords=data["route_coords"],
            distance_km=data["distance_km"],
            duration_minutes=data["duration_minutes"],
            route_type=data.get("route_type", "route_1"),
            description=data.get("description", ""),
            tags=data.get("tags", [])
        )
        
        return jsonify({
            "status": "success",
            "route": route,
            "message": f"'{route['name']}' rotası kaydedildi!"
        })
    
    except Exception as e:
        print(f"[API] Rota kaydetme hatası: {e}")
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/routes", methods=["GET"])
def api_get_routes():
    """
    Tüm kaydedilmiş rotaları getirir (Pagination destekli).

    Query Parameters:
        sort_by: created_at, name, distance_km, times_used, favorite
        limit: Maksimum rota sayısı (varsayılan 20)
        offset: Başlangıç index'i (varsayılan 0)
        page: Sayfa numarası (limit ile hesaplanır, offset alternatifi)

    Response:
        {
            "routes": [...],
            "count": 5,
            "total": 150,
            "page": 1,
            "pages": 8
        }
    """
    try:
        sort_by = request.args.get("sort_by", "created_at")

        # Pagination parametreleri
        limit = request.args.get("limit", 20, type=int)
        offset = request.args.get("offset", 0, type=int)
        page = request.args.get("page", 1, type=int)

        # Page parametresini offset'e çevir
        if page > 1:
            offset = (page - 1) * limit

        # Toplam sayıyı al
        total = get_routes_count()

        # Rotaları getir
        routes = get_all_routes(sort_by=sort_by, limit=limit, offset=offset)

        # Sayfa bilgisi
        pages = (total + limit - 1) // limit if total > 0 else 1
        current_page = (offset // limit) + 1

        return jsonify({
            "routes": routes,
            "count": len(routes),
            "total": total,
            "page": current_page,
            "pages": pages,
            "limit": limit,
            "offset": offset
        })
    
    except Exception as e:
        # print(f"[API] Rota listeleme hatası: {e}"))
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/routes/<route_id>", methods=["GET"])
def api_get_route_by_id(route_id):
    """
    Belirli bir rotayı getirir.
    
    Response:
        {
            "route": {...}
        }
    """
    try:
        route = get_route(route_id)
        
        if not route:
            return jsonify({"error": "Rota bulunamadı"}), 404
        
        return jsonify({"route": route})
    
    except Exception as e:
        # print(f"[API] Rota getirme hatası: {e}"))
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/routes/<route_id>", methods=["PUT"])
def api_update_route(route_id):
    """
    Rotayı günceller.
    
    Request Body:
        {
            "name": "Yeni İsim",
            "description": "Yeni açıklama",
            "tags": ["yeni", "etiketler"]
        }
    
    Response:
        {
            "status": "success",
            "route": {...}
        }
    """
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "Geçersiz veya eksik JSON gövdesi."}), 400
        
        route = update_route(route_id, data)
        
        if not route:
            return jsonify({"error": "Rota bulunamadı"}), 404
        
        return jsonify({
            "status": "success",
            "route": route,
            "message": "Rota güncellendi"
        })
    
    except Exception as e:
        print(f"[API] Rota güncelleme hatası: {e}")
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/routes/<route_id>", methods=["DELETE"])
def api_delete_route(route_id):
    """
    Rotayı siler.
    
    Response:
        {
            "status": "success",
            "message": "Rota silindi"
        }
    """
    try:
        success = delete_route(route_id)
        
        if not success:
            return jsonify({"error": "Rota bulunamadı"}), 404
        
        return jsonify({
            "status": "success",
            "message": "Rota silindi"
        })
    
    except Exception as e:
        # print(f"[API] Rota silme hatası: {e}"))
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/routes/<route_id>/favorite", methods=["POST"])
def api_toggle_favorite(route_id):
    """
    Rotayı favorilere ekler/çıkarır.
    
    Response:
        {
            "status": "success",
            "route": {...},
            "is_favorite": true
        }
    """
    try:
        route = toggle_favorite(route_id)
        
        if not route:
            return jsonify({"error": "Rota bulunamadı"}), 404
        
        return jsonify({
            "status": "success",
            "route": route,
            "is_favorite": route.get("favorite", False)
        })
    
    except Exception as e:
        # print(f"[API] Favori işlemi hatası: {e}"))
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/routes/search", methods=["GET"])
def api_search_routes():
    """
    Rota arama.
    
    Query Parameters:
        q: Arama sorgusu
    
    Response:
        {
            "routes": [...],
            "count": 3
        }
    """
    try:
        query = request.args.get("q", "")
        
        if not query:
            return jsonify({"error": "Arama sorgusu gerekli"}), 400
        
        routes = search_routes(query)
        
        return jsonify({
            "routes": routes,
            "count": len(routes)
        })
    
    except Exception as e:
        print(f"[API] Rota arama hatası: {e}")
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/routes/statistics", methods=["GET"])
def api_route_statistics():
    """
    Rota istatistikleri.
    
    Response:
        {
            "total_routes": 10,
            "total_distance_km": 45.2,
            "total_duration_minutes": 550,
            "favorite_count": 3,
            "most_used_route": {...}
        }
    """
    try:
        stats = get_statistics()
        return jsonify(stats)
    
    except Exception as e:
        # print(f"[API] İstatistik hatası: {e}"))
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


# =============================================================================
# ZAMAN PLANLAMA API'LERİ
# =============================================================================

@app.route("/api/timeline/create", methods=["POST"])
def api_create_timeline():
    """
    Rota için zaman çizelgesi oluşturur.
    
    Request Body:
        {
            "points": [
                {"name": "Kadıköy", "lat": 40.99, "lon": 29.03},
                {"name": "Moda", "lat": 40.98, "lon": 29.04}
            ],
            "segment_distances": [1.2, 0.8],  # km cinsinden
            "start_time": "09:00",
            "visit_duration": 30,  # dakika (varsayılan)
            "transport_mode": "walking",
            "custom_durations": {0: 45, 1: 60}  # Ã–zel süreler (opsiyonel)
        }
    
    Response:
        {
            "start_time": "09:00",
            "end_time": "14:30",
            "total_duration_minutes": 330,
            "schedule": [...]
        }
    """
    try:
        data = request.get_json(silent=True)
        
        # Zorunlu alanlar
        if not data or "points" not in data:
            return jsonify({"error": "'points' alanı gerekli"}), 400
        
        points = data["points"]
        segment_distances = data.get("segment_distances", [])
        start_time = data.get("start_time", "09:00")
        visit_duration = data.get("visit_duration", 30)
        transport_mode = data.get("transport_mode", "walking")
        custom_durations = data.get("custom_durations", {})
        
        # String key'leri int'e çevir
        if custom_durations:
            custom_durations = {int(k): v for k, v in custom_durations.items()}
        
        timeline = create_timeline(
            points=points,
            segment_distances=segment_distances,
            start_time=start_time,
            visit_duration=visit_duration,
            transport_mode=transport_mode,
            custom_durations=custom_durations
        )
        
        if "error" in timeline:
            return jsonify(timeline), 400
        
        return jsonify(timeline)
    
    except Exception as e:
        # print(f"[API] Timeline oluşturma hatası: {e}"))
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/timeline/check-conflicts", methods=["POST"])
def api_check_conflicts():
    """
    Zaman çizelgesinde çakışmaları kontrol eder.
    
    Request Body:
        {
            "schedule": [...],
            "opening_hours": {
                0: {"open": "09:00", "close": "18:00"},
                1: {"open": "10:00", "close": "20:00"}
            }
        }
    
    Response:
        {
            "warnings": [
                {
                    "point_index": 2,
                    "warning": "Bu saat kapalı olabilir",
                    "arrival_time": "20:00"
                }
            ]
        }
    """
    try:
        data = request.get_json(silent=True)
        
        if not data or "schedule" not in data:
            return jsonify({"error": "'schedule' alanı gerekli"}), 400
        
        schedule = data["schedule"]
        opening_hours = data.get("opening_hours", {})
        
        # String key'leri int'e çevir
        if opening_hours:
            opening_hours = {int(k): v for k, v in opening_hours.items()}
        
        warnings = check_time_conflicts(schedule, opening_hours)
        
        return jsonify({"warnings": warnings})
    
    except Exception as e:
        print(f"[API] Çakışma kontrolü hatası: {e}")
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/timeline/optimize", methods=["POST"])
def api_optimize_timeline():
    """
    Zaman çizelgesini optimize eder ve öneriler sunar.
    
    Request Body:
        {
            "schedule": [...],
            "max_duration_minutes": 360,  # 6 saat
            "preferred_end_time": "18:00"
        }
    
    Response:
        {
            "suggestions": [
                {
                    "type": "duration_exceeded",
                    "message": "Toplam süre 1s 30dk fazla",
                    "suggestion": "Ziyaret sürelerini azaltın"
                }
            ]
        }
    """
    try:
        data = request.get_json(silent=True)
        
        if not data or "schedule" not in data:
            return jsonify({"error": "'schedule' alanı gerekli"}), 400
        
        schedule = data["schedule"]
        max_duration = data.get("max_duration_minutes")
        preferred_end = data.get("preferred_end_time")
        
        result = optimize_schedule(schedule, max_duration, preferred_end)
        
        return jsonify(result)
    
    except Exception as e:
        # print(f"[API] Optimizasyon hatası: {e}"))
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


# =============================================================================
# KULLANICI LOKASYON API'LERİ
# =============================================================================

@app.route("/api/locations", methods=["GET"])
def api_get_locations():
    """
    Kaydedilmiş tüm lokasyonları getirir.
    Pagination desteği eklenmiştir (limit, offset, page).
    """
    try:
        sort_by = request.args.get("sort_by", "created_at")
        limit = request.args.get("limit", 20, type=int)
        offset = request.args.get("offset", 0, type=int)
        page = request.args.get("page", 1, type=int)

        # Page parametresi varsa offset'i hesapla
        if page > 1:
            offset = (page - 1) * limit

        total = get_locations_count()
        locations = get_all_locations(sort_by=sort_by, limit=limit, offset=offset)

        # Toplam sayfa sayısını hesapla
        pages = (total + limit - 1) // limit if total > 0 else 1
        current_page = (offset // limit) + 1

        return jsonify({
            "locations": locations,
            "count": len(locations),
            "total": total,
            "page": current_page,
            "pages": pages,
            "limit": limit,
            "offset": offset
        })
    except Exception as e:
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/locations", methods=["POST"])
def api_save_location():
    """
    Yeni bir lokasyon kaydeder.
    """
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "Geçersiz veya eksik JSON gövdesi."}), 400
        
        required_fields = ["name", "lat", "lon"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"'{field}' alanı gerekli."}), 400
                
        location = save_location(
            name=data["name"],
            lat=data["lat"],
            lon=data["lon"],
            icon_type=data.get("icon_type", "star"),
            address=data.get("address", "")
        )
        
        return jsonify({
            "status": "success",
            "location": location,
            "message": f"'{location['name']}' konumu kaydedildi!"
        })
    except Exception as e:
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/locations/<location_id>", methods=["DELETE"])
def api_delete_location(location_id):
    """
    Lokasyonu siler.
    """
    try:
        success = delete_location(location_id)
        
        if not success:
            return jsonify({"error": "Lokasyon bulunamadı"}), 404
            
        return jsonify({
            "status": "success",
            "message": "Lokasyon silindi"
        })
    except Exception as e:
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/locations/<location_id>", methods=["PUT"])
def api_update_location(location_id):
    """
    Lokasyonu günceller.
    """
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "Geçersiz veya eksik JSON gövdesi."}), 400

        location = update_location(location_id, data)
        
        if not location:
            return jsonify({"error": "Lokasyon bulunamadı"}), 404
            
        return jsonify({
            "status": "success",
            "location": location,
            "message": "Lokasyon güncellendi"
        })
    except Exception as e:
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/locations/<location_id>/favorite", methods=["POST"])
def api_toggle_location_favorite(location_id):
    """
    Lokasyonun favori durumunu değiştirir.
    """
    try:
        location = toggle_location_favorite(location_id)
        
        if not location:
            return jsonify({"error": "Lokasyon bulunamadı"}), 404
            
        return jsonify({
            "status": "success",
            "location": location,
            "is_favorite": location.get("favorite", False),
            "message": "Favorilere eklendi *" if location.get("favorite") else "Favorilerden cikarildi"
        })
    except Exception as e:
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


# =============================================================================
# BERT NLP ENDPOINTS
# =============================================================================

@app.route("/api/nlp/parse", methods=["POST"])
def api_nlp_parse():
    """
    Doğal dil sorgusunu analiz eder ve yapılandırılmış veri döner.

    Request Body:
        {
            "query": "Kadıköy'den Beşiktaş'a rota çiz"
        }

    Response:
        {
            "type": "route",           # route | poi | multi | single | unknown
            "confidence": 0.85,
            "origin": "Kadıköy",
            "destination": "Beşiktaş",
            "locations": null,         # multi için
            "location": null,          # poi için
            "detected_places": [
                {"place": "Kadıköy", "similarity": 0.92},
                {"place": "Beşiktaş", "similarity": 0.88}
            ],
            "parse_time": 0.15,
            "error": null
        }
    """
    try:
        print(f"\n{'='*60}")
        print(f"[NLP API] Parse çağrısı alındı")
        global BERT_NLP_AVAILABLE
        data = request.get_json(silent=True)

        if not data or "query" not in data:
            print(f"[NLP API] ❌ Eksik parametreler")
            return jsonify({"error": "'query' alanı gerekli"}), 400

        query_value = data["query"]
        if not isinstance(query_value, str):
            print(f"[NLP API] ❌ Query metin olmalı")
            return jsonify({"error": "'query' alanı metin olmalı"}), 400

        query = query_value.strip()

        if not query or len(query) < 2:
            print(f"[NLP API] ❌ Sorgu çok kısa")
            return jsonify({"error": "Sorgu çok kısa"}), 400

        print(f"[NLP API] 📥 Sorgu: '{query}'")
        print(f"[NLP API] 🔧 BERT_NLP_AVAILABLE: {BERT_NLP_AVAILABLE}")

        if not BERT_NLP_AVAILABLE:
            print(f"[NLP API] ❌ BERT motoru ZORUNLU! Regex fallback KALDIRILDI.")
            return jsonify({"error": "BERT motoru gereklidir. Transformers ve PyTorch kurun."}), 503

        print(f"[NLP API] 🤖 BERT motoru kullanılıyor...")
        try:
            nlp_engine = get_bert_nlp_engine()
            result = nlp_engine.parse(query)
            result["engine"] = "bert-nlp"
            print(f"[NLP API] ✅ BERT parse başarılı")
        except Exception as bert_exc:
            print(f"[NLP API] ❌ BERT hatası: {bert_exc}")
            return jsonify({"error": f"BERT motoru hatası: {str(bert_exc)}"}), 500

        confidence = float(result.get("confidence", 0.0) or 0.0)
        print(f"[NLP API] 📊 Sonuç:")
        print(f"[NLP API]    - Tip: {result.get('type', 'unknown')}")
        print(f"[NLP API]    - Confidence: {confidence:.2f}")
        print(f"[NLP API]    - Engine: {result.get('engine', 'unknown')}")
        if result.get('origin'):
            print(f"[NLP API]    - Rota: {result['origin']} → {result.get('destination', '?')}")
        if result.get('detected_places'):
            print(f"[NLP API]    - Tespit edilen yerler: {[p['place'] for p in result['detected_places']]}")
        print(f"[NLP API] 📤 Dönen response: {result}")
        print(f"{'='*60}\n")

        return jsonify(result)

    except Exception as e:
        print(f"[NLP ERROR] {str(e)}")
        return jsonify({"error": f"NLP hatası: {str(e)}"}), 500


@app.route("/api/nlp/status", methods=["GET"])
def api_nlp_status():
    """
    NLP engine durumunu kontrol eder.

    Response:
        {
            "available": true,
            "engine": "bert-nlp",
            "model": "dbmdz/bert-base-turkish-uncased"
        }
    """
    return jsonify({
        "available": BERT_NLP_AVAILABLE,
        "engine": "bert-nlp" if BERT_NLP_AVAILABLE else "regex-fallback",
        "model": "dbmdz/bert-base-turkish-uncased" if BERT_NLP_AVAILABLE else None,
        "bert_available": BERT_NLP_AVAILABLE,
        "last_error": _BERT_NLP_ERROR
    })


@app.route("/api/nlp/similarity", methods=["POST"])
def api_nlp_similarity():
    """
    İki metin arasındaki semantic similarity'yi hesaplar.

    Request Body:
        {
            "text1": "Kadıköy",
            "text2": "Kadiköy"
        }

    Response:
        {
            "similarity": 0.92,
            "text1": "Kadıköy",
            "text2": "Kadiköy"
        }
    """
    try:
        print(f"\n{'='*60}")
        print(f"[NLP API] Similarity çağrısı alındı")
        if not BERT_NLP_AVAILABLE:
            print(f"[NLP API] ❌ BERT engine aktif değil!")
            return jsonify({"error": "BERT engine aktif değil"}), 503

        data = request.get_json(silent=True)
        print(f"[NLP API] 📥 Gelen request: {data}")

        if not data or "text1" not in data or "text2" not in data:
            print(f"[NLP API] ❌ Eksik parametreler")
            return jsonify({"error": "'text1' ve 'text2' alanları gerekli"}), 400

        text1 = data["text1"].strip()
        text2 = data["text2"].strip()
        print(f"[NLP API] 🔤 Text1: '{text1}' | Text2: '{text2}'")

        if not text1 or not text2:
            print(f"[NLP API] ❌ Boş metin")
            return jsonify({"error": "Metinler boş olamaz"}), 400

        print(f"[NLP API] 🔄 BERT engine yükleniyor...")
        from bert_engine import get_bert_engine
        engine = get_bert_engine()
        print(f"[NLP API] ✅ BERT engine hazır")

        print(f"[NLP API] 🧮 Benzerlik hesaplanıyor...")
        similarity = engine.similarity(text1, text2)
        print(f"[NLP API] ✅ Sonuç: {similarity:.4f}")

        result = {
            "similarity": float(similarity),
            "text1": text1,
            "text2": text2
        }
        print(f"[NLP API] 📤 Dönen response: {result}")
        print(f"{'='*60}\n")

        return jsonify(result)

    except Exception as e:
        print(f"[NLP ERROR] Similarity: {str(e)}")
        return jsonify({"error": f"Benzerlik hesaplanamadı: {str(e)}"}), 500


@app.route("/api/nlp/best-match", methods=["POST"])
def api_nlp_best_match():
    """
    Sorguya en yakın adayı bulur (typo tolerant).

    Request Body:
        {
            "query": "kadikoy",
            "candidates": ["Kadıköy", "Beşiktaş", "Taksim"],
            "threshold": 0.75
        }

    Response:
        {
            "match": "Kadıköy",
            "similarity": 0.92,
            "index": 0
        }
    """
    try:
        print(f"\n{'='*60}")
        print(f"[NLP API] Best Match çağrısı alındı")
        if not BERT_NLP_AVAILABLE:
            print(f"[NLP API] ❌ BERT engine aktif değil!")
            return jsonify({"error": "BERT engine aktif değil"}), 503

        data = request.get_json(silent=True)
        print(f"[NLP API] 📥 Gelen request: query='{data.get('query')}', {len(data.get('candidates', []))} aday")

        if not data or "query" not in data or "candidates" not in data:
            print(f"[NLP API] ❌ Eksik parametreler")
            return jsonify({"error": "'query' ve 'candidates' alanları gerekli"}), 400

        query = data["query"].strip()
        candidates = data["candidates"]
        threshold = data.get("threshold", 0.75)
        print(f"[NLP API] 🔍 Query: '{query}' | Threshold: {threshold}")
        print(f"[NLP API] 📋 Adaylar: {candidates}")

        if not query:
            print(f"[NLP API] ❌ Boş sorgu")
            return jsonify({"error": "Sorgu boş olamaz"}), 400

        if not isinstance(candidates, list) or len(candidates) == 0:
            print(f"[NLP API] ❌ Geçersiz adaylar")
            return jsonify({"error": "'candidates' bir liste olmalı"}), 400

        print(f"[NLP API] 🔄 BERT engine yükleniyor...")
        from bert_engine import get_bert_engine
        engine = get_bert_engine()
        print(f"[NLP API] ✅ BERT engine hazır")

        print(f"[NLP API] 🧮 En iyi eşleşme aranıyor...")
        result = engine.find_best_match(query, candidates, threshold=threshold)

        if result:
            print(f"[NLP API] ✅ Eşleşme bulundu: {result['match']} (benzerlik: {result['similarity']:.4f})")
            print(f"[NLP API] 📤 Dönen response: {result}")
        else:
            print(f"[NLP API] ❌ Eşleşme bulunamadı")
            result = {
                "match": None,
                "similarity": 0.0,
                "index": -1,
                "message": f"Eşleşme bulunamadı (threshold: {threshold})"
            }
        print(f"{'='*60}\n")

        return jsonify(result)

    except Exception as e:
        print(f"[NLP ERROR] Best match: {str(e)}")
        return jsonify({"error": f"Eşleşme bulunamadı: {str(e)}"}), 500


# =============================================================================
# HAVA DURUMU ENDPOINTS (OpenMeteo API)
# =============================================================================

@app.route("/api/weather", methods=["GET"])
def api_get_weather():
    """
    Belirli bir konum için güncel hava durumunu getirir.

    Query Parameters:
        lat (float, required): Enlem (-90 ile 90 arasi)
        lon (float, required): Boylam (-180 ile 180 arasi)

    Response:
        {
            "success": true,
            "data": {
                "location": {"lat": 41.0082, "lon": 28.9784, "timezone": "Europe/Istanbul"},
                "current": {
                    "timestamp": "2026-03-10T14:00:00+00:00",
                    "temperature": 15.5,
                    "apparent_temperature": 14.2,
                    "humidity": 65,
                    "precipitation": 0.0,
                    "weather_code": 0,
                    "weather_description": "Clear sky",
                    "weather_tr": "Acik gokyuzu",
                    "weather_emoji": "☀️",
                    "wind_speed": 12.5,
                    "wind_direction": 180
                },
                "cache_hit": false
            }
        }
    """
    if not WEATHER_SERVICE_AVAILABLE:
        return jsonify({"error": "Hava durumu servisi mevcut degil"}), 503

    try:
        # Query parameters
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)

        if lat is None or lon is None:
            return jsonify({"error": "'lat' ve 'lon' parametreleri gerekli"}), 400

        print(f"[Weather] Current weather request: lat={lat}, lon={lon}")

        result = get_current_weather(lat, lon)

        if result.get("success"):
            return jsonify(result)
        else:
            return jsonify({"error": "Hava durumu alinamadi"}), 500

    except Exception as e:
        print(f"[Weather ERROR] {str(e)}")
        return jsonify({"error": f"Sunucu hatasi: {str(e)}"}), 500


@app.route("/api/weather/forecast", methods=["GET"])
def api_get_weather_forecast():
    """
    Belirli bir konum için saatlik hava tahmini getirir.

    Query Parameters:
        lat (float, required): Enlem
        lon (float, required): Boylam
        hours (int, optional): Forecast saati (varsayilan 24, max 168)
        timezone (string, optional): Timezone (varsayilan auto)

    Response:
        {
            "success": true,
            "data": {
                "location": {"lat": 41.0082, "lon": 28.9784, "timezone": "Europe/Istanbul"},
                "hourly": {
                    "time": ["2026-03-10T14:00", "2026-03-10T15:00", ...],
                    "temperature": [15.5, 16.2, ...],
                    "precipitation": [0.0, 0.0, ...],
                    "precipitation_probability": [0, 5, ...],
                    "weather_code": [0, 0, ...],
                    "wind_speed": [12.5, 14.0, ...]
                },
                "cache_hit": false
            }
        }
    """
    if not WEATHER_SERVICE_AVAILABLE:
        return jsonify({"error": "Hava durumu servisi mevcut degil"}), 503

    try:
        # Query parameters
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        hours = request.args.get("hours", 24, type=int)
        timezone = request.args.get("timezone", "auto")

        if lat is None or lon is None:
            return jsonify({"error": "'lat' ve 'lon' parametreleri gerekli"}), 400

        print(f"[Weather] Forecast request: lat={lat}, lon={lon}, hours={hours}")

        result = get_hourly_forecast(lat, lon, hours)

        if result.get("success"):
            return jsonify(result)
        else:
            return jsonify({"error": "Hava tahmini alinamadi"}), 500

    except ValueError as e:
        return jsonify({"error": f"Gecersiz parametre: {str(e)}"}), 400
    except Exception as e:
        print(f"[Weather ERROR] {str(e)}")
        return jsonify({"error": f"Sunucu hatasi: {str(e)}"}), 500


@app.route("/api/weather/check-route", methods=["POST"])
def api_check_route_weather():
    """
    Rota boyunca hava durumunu kontrol eder.

    Request Body:
        {
            "points": [
                {"lat": 41.0082, "lon": 28.9784, "name": "Kadikoy"},
                {"lat": 41.0422, "lon": 29.0067, "name": "Besiktas"}
            ],
            "start_time": "2026-03-10T14:00:00"  # optional
        }

    Response:
        {
            "success": true,
            "data": {
                "route_weather": [
                    {
                        "point": "Kadikoy",
                        "lat": 41.0082,
                        "lon": 28.9784,
                        "weather": {...}
                    },
                    ...
                ],
                "warnings": ["Besiktas'ta hafif yagmur bekleniyor"],
                "overall_conditions": "clear"
            }
        }
    """
    if not WEATHER_SERVICE_AVAILABLE:
        return jsonify({"error": "Hava durumu servisi mevcut degil"}), 503

    try:
        data = request.get_json(silent=True)

        if not data or "points" not in data:
            return jsonify({"error": "'points' alani gerekli"}), 400

        points = data["points"]
        start_time = data.get("start_time")

        if not points or len(points) == 0:
            return jsonify({"error": "En az bir nokta gerekli"}), 400

        print(f"[Weather] Route check: {len(points)} points")

        result = check_route_weather(points, start_time)

        if result.get("success"):
            return jsonify(result)
        else:
            return jsonify({"error": "Rota hava kontrolü basarisiz"}), 500

    except Exception as e:
        print(f"[Weather ERROR] {str(e)}")
        return jsonify({"error": f"Sunucu hatasi: {str(e)}"}), 500


@app.route("/api/weather/status", methods=["GET"])
def api_weather_status():
    """
    Hava durumu servisi durumunu dondurür.

    Response:
        {
            "service": "weather_service",
            "status": "operational",
            "cache_stats": {...},
            "config": {...}
        }
    """
    if not WEATHER_SERVICE_AVAILABLE:
        return jsonify({
            "service": "weather_service",
            "status": "unavailable",
            "error": "Servis bulunamadi"
        }), 503

    try:
        status = get_service_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({
            "service": "weather_service",
            "status": "error",
            "error": str(e)
        }), 500


@app.route("/api/weather/health", methods=["GET"])
def api_weather_health():
    """
    Hava durumu servisi saglik kontrolü.

    Response:
        {"healthy": true}
    """
    if not WEATHER_SERVICE_AVAILABLE:
        return jsonify({"healthy": False, "error": "Servis mevcut degil"}), 503

    try:
        is_healthy = weather_health_check()
        return jsonify({"healthy": is_healthy})
    except Exception as e:
        return jsonify({"healthy": False, "error": str(e)}), 500


@app.route("/api/weather/clear-cache", methods=["POST"])
def api_weather_clear_cache():
    """
    Hava durumu cache'ini temizler.

    Response:
        {"status": "success", "cleared": 5}
    """
    if not WEATHER_SERVICE_AVAILABLE:
        return jsonify({"error": "Hava durumu servisi mevcut degil"}), 503

    try:
        count = clear_weather_cache()
        return jsonify({
            "status": "success",
            "cleared": count,
            "message": f"{count} cache entry silindi"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("  OpenTrip API Sunucusu Başlatılıyor...")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(debug=False, port=5000)

