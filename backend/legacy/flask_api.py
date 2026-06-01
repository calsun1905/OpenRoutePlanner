"""
flask_api.py - Flask REST API for Location & POI Engine.
"""

from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify, request

from complete_location_poi_engine import CompleteLocationPOIEngine

app = Flask(__name__)
engine = CompleteLocationPOIEngine()


def _error(message: str, *, code: str, status: int):
    return jsonify({"success": False, "error_code": code, "error": message}), status


def _read_json_body() -> tuple[dict[str, Any] | None, tuple | None]:
    data = request.get_json(silent=True)
    if data is None:
        return None, _error("JSON body gerekli.", code="invalid_input", status=400)
    if not isinstance(data, dict):
        return None, _error("JSON body bir obje olmalidir.", code="invalid_input", status=400)
    return data, None


@app.route("/api/nlp/parse", methods=["POST"])
def parse_query():
    try:
        data, err = _read_json_body()
        if err:
            return err

        query = str(data.get("query", "") or "").strip()
        if not query:
            return _error("'query' zorunlu ve bos olamaz.", code="invalid_input", status=400)

        return jsonify(engine.parse_query(query))
    except Exception as exc:
        return _error(f"Sunucu hatasi: {exc}", code="internal_error", status=500)


@app.route("/api/poi/search", methods=["POST"])
def search_poi():
    try:
        data, err = _read_json_body()
        if err:
            return err

        location = str(data.get("location", "") or "").strip()
        poi_type = str(data.get("poi_type", "") or "").strip()
        limit_raw = data.get("limit", 10)

        if not location and not poi_type:
            return _error(
                "En az bir filtre gerekli: 'location' veya 'poi_type'.",
                code="invalid_input",
                status=400,
            )

        try:
            limit = int(limit_raw)
        except (TypeError, ValueError):
            return _error("'limit' sayi olmalidir.", code="invalid_input", status=400)
        if limit < 1 or limit > 50:
            return _error("'limit' 1-50 araliginda olmalidir.", code="invalid_input", status=400)

        query = f"{location} {poi_type}".strip() if location else poi_type
        result = engine.parse_query(query)
        pois = result.get("pois", [])
        if isinstance(pois, list):
            pois = pois[:limit]
        else:
            pois = []

        return jsonify(
            {
                "success": bool(result.get("success")),
                "pois": pois,
                "result_count": len(pois),
                "location": result.get("location"),
                "poi_type": result.get("poi_type"),
            }
        )
    except Exception as exc:
        return _error(f"Sunucu hatasi: {exc}", code="internal_error", status=500)


@app.route("/api/locations", methods=["GET"])
def get_locations():
    try:
        districts = []
        for key, data in engine.districts.items():
            districts.append(
                {
                    "key": key,
                    "name": data["name"],
                    "il": data["il"],
                    "yakla": data.get("yakla", ""),
                    "lat": data["lat"],
                    "lon": data["lon"],
                }
            )
        return jsonify({"success": True, "districts": districts, "count": len(districts)})
    except Exception as exc:
        return _error(f"Sunucu hatasi: {exc}", code="internal_error", status=500)


@app.route("/api/poi/types", methods=["GET"])
def get_poi_types():
    try:
        types = []
        for key, data in engine.poi_types.items():
            types.append(
                {
                    "key": key,
                    "description": data["description"],
                    "aliases": data["aliases"],
                    "osm_tags": data["osm_tags"],
                }
            )
        return jsonify({"success": True, "types": types, "count": len(types)})
    except Exception as exc:
        return _error(f"Sunucu hatasi: {exc}", code="internal_error", status=500)


@app.route("/api/stats", methods=["GET"])
def get_stats():
    try:
        return jsonify({"success": True, "stats": engine.get_stats()})
    except Exception as exc:
        return _error(f"Sunucu hatasi: {exc}", code="internal_error", status=500)


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "Location & POI API calisiyor", "version": "1.0"})


def _env_bool(name: str, default: bool) -> bool:
    raw = str(os.getenv(name, str(default))).strip().lower()
    return raw in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    host = os.getenv("FLASK_API_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_API_PORT", "5000"))
    debug = _env_bool("FLASK_API_DEBUG", False)
    app.run(host=host, port=port, debug=debug)

