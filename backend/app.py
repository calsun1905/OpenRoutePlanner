"""
app.py - Flask API Sunucusu

Frontend ile Backend arasındaki köprü.
Rota optimizasyonu ve POI arama endpoint'leri sağlar.
"""
import os

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from graph_manager import get_graph, get_graph_for_points, search_pois
from route_engine import (
    solve_tsp,
    build_full_route,
    nodes_to_coords,
    calculate_route_stats,
    generate_google_maps_link,
)

# Frontend klasörünün yolu
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)  # Frontend'den gelen isteklere izin ver

# Global değişkenler: cache
_graph_cache = {}
_poi_cache = {}


def _get_cached_graph(place_name: str):
    """Graf objesini memory cache'te tutar (uygulama içi)."""
    if place_name not in _graph_cache:
        _graph_cache[place_name] = get_graph(place_name)
    return _graph_cache[place_name]


@app.route("/api/get-route", methods=["POST"])
def api_get_route():
    """
    Koordinat listesi alır, optimize edilmiş rota döner.
    
    Request Body:
        {
            "points": [[lat, lon], [lat, lon], ...],
            "place": "Kadikoy, Istanbul, Turkey"  (opsiyonel, varsayılan Kadıköy)
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
        data = request.get_json()

        if not data or "points" not in data:
            return jsonify({"error": "Geçersiz istek: 'points' alanı gerekli."}), 400

        points = data["points"]
        optimize = data.get("optimize", False)  # Varsayılan: sıralı bağla

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
        print(f"[API] Noktalar için graf alınıyor: {len(points)} nokta")
        G = get_graph_for_points(point_tuples)

        # 2) Sıralama: TSP optimizasyonu veya kullanıcı sırası
        if optimize and len(point_tuples) > 2:
            print(f"[API] TSP çözülüyor: {len(points)} nokta")
            optimized_order = solve_tsp(G, point_tuples)
        else:
            print(f"[API] Sıralı rota: {len(points)} nokta")
            optimized_order = list(range(len(point_tuples)))

        # 3) Sıralanmış noktalar
        ordered_points = [point_tuples[i] for i in optimized_order]

        # 4) Tam rotayı oluştur
        print("[API] Tam rota oluşturuluyor...")
        route_nodes = build_full_route(G, ordered_points)

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
        }

        print(f"[API] Rota hesaplandı: {stats['total_distance_km']} km, "
              f"~{stats['estimated_walk_minutes']} dk yürüme")
        return jsonify(response)

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
        data = request.get_json()

        if not data or "category" not in data:
            return jsonify({"error": "'category' alanı gerekli."}), 400

        place = data.get("place", "Kadikoy, Istanbul, Turkey")
        category = data["category"]

        valid_categories = ["museum", "cafe", "park", "restaurant", "library", "mosque", "hotel"]
        if category not in valid_categories:
            return jsonify({
                "error": f"Geçersiz kategori. Geçerli: {', '.join(valid_categories)}"
            }), 400

        cache_key = f"{place}::{category}"
        if cache_key in _poi_cache:
            print(f"[API] POI cache'den döndürülüyor: {cache_key}")
            pois = _poi_cache[cache_key]
        else:
            pois = search_pois(place, category)
            _poi_cache[cache_key] = pois
        return jsonify({"pois": pois})

    except Exception as e:
        print(f"[API] POI arama hatası: {e}")
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """Sunucu sağlık kontrolü."""
    return jsonify({"status": "ok", "message": "OpenTrip API çalışıyor!"})


@app.route("/")
def serve_frontend():
    """Ana sayfa — Frontend'i sun."""
    return send_from_directory(FRONTEND_DIR, "index.html")


if __name__ == "__main__":
    print("=" * 50)
    print("  OpenTrip API Sunucusu Başlatılıyor...")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
