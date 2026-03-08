"""
100 Farklı Rota Testi - Alternatif Rota Analizi

 amaç:
- 100 farklı rota senaryosu test et
- Alternatif rotaları değerlendir
- Skorla (overlap, mesafe, performans)
- Sonuçları logla ve analiz et
"""

import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Tuple
import random

# API endpoint
API_BASE = "http://127.0.0.1:5000/api"

# Test senaryoları - İstanbul içi farklı bölgeler
ROUTE_SCENARIOS = [
    # Kadıköy bölgeleri
    ("Kadıköy", "Moda", "Caferağa", "Fenerbahçe"),
    ("Kadıköy", "Bağdat Caddesi", "Bostancı", "Kozyatağı"),
    ("Kadıköy", "Fenerbahçe", "Göztepe", "Bostancı"),

    # Beşiktaş bölgeleri
    ("Beşiktaş", "Ortaköy", "Bebek", "Etiler"),
    ("Beşiktaş", "Levent", "Etiler", "Gayrettepe"),
    ("Beşiktaş", "Bebek", "Rumeli Hisarı", "Tarabya"),

    # Beyoğlu bölgeleri
    ("Taksim", "İstiklal Caddesi", "Cihangir", "Karaköy"),
    ("Taksim", "Şişhane", "Karaköy", "Eminönü"),
    ("Taksim", "Harbiye", "Maçka", "Nişantaşı"),

    # Şişli bölgeleri
    ("Şişli", "Mecidiyeköy", "Levent", "Gayrettepe"),
    ("Şişli", "Teşvikiye", "Nişantaşı", "Maçka"),
    ("Şişli", "Levent", "Maslak", "Ayazağa"),

    # Sarıyer bölgeleri
    ("Sarıyer", "Rumeli Hisarı", "Bebek", "Tarabya"),
    ("Sarıyer", "Yeniköy", "Kandilli", "Rumeli Hisarı"),
    ("Sarıyer", "Tarabya", "Bebek", "Etiler"),

    # Üsküdar bölgeleri
    ("Üsküdar", "Kuzguncuk", "Beylerbeyi", "Çengelköy"),
    ("Üsküdar", "Salacak", "Harem", "Kadıköy"),
    ("Üsküdar", "Beylerbeyi", "Kandilli", "Anadoluhisarı"),

    # Boğaz geçişleri
    ("Kadıköy", "Beşiktaş"),
    ("Üsküdar", "Eminönü"),
    ("Kadıköy", "Karaköy"),
    ("Üsküdar", "Beşiktaş"),

    # Uzun mesafe
    ("Kadıköy", "Sarıyer"),
    ("Üsküdar", "Sarıyer"),
    ("Kadıköy", "Levent"),
    ("Bostancı", "Etiler"),

    # Kısa mesafe (dikkat: overlap yüksek olabilir)
    ("Kadıköy", "Moda"),
    ("Taksim", "Cihangir"),
    ("Beşiktaş", "Ortaköy"),
    ("Şişli", "Mecidiyeköy"),
]

# Diğer senaryoları otomatik üret
BASE_LOCATIONS = [
    "Kadıköy", "Beşiktaş", "Taksim", "Şişli", "Üsküdar",
    "Sarıyer", "Bostancı", "Levent", "Etiler", "Karaköy",
    "Eminönü", "Bebek", "Ortaköy", "Mecidiyeköy", "Nişantaşı",
    "Kozyatağı", "Göztepe", "Bostancı", "Fenerbahçe", "Moda",
    "Caferağa", "Salacak", "Harem", "Kuzguncuk", "Beylerbeyi",
    "Çengelköy", "Kandilli", "Anadoluhisarı", "Rumeli Hisarı", "Tarabya",
    "Yeniköy", "İstiklal Caddesi", "Cihangir", "Harbiye", "Maçka",
    "Gayrettepe", "Levent", "Maslak", "Ayazağa", "Teşvikiye",
]


def generate_test_routes(count: int = 100) -> List[List[str]]:
    """100 farklı rota senaryosu üret"""
    routes = []

    # Önce tanımlı senaryoları ekle
    routes.extend([list(route) for route in ROUTE_SCENARIOS])

    # Kalanları rastgele üret
    while len(routes) < count:
        num_points = random.randint(2, 5)
        route = random.sample(BASE_LOCATIONS, num_points)
        route_str = " -> ".join(route)

        # Benzersiz olmasını sağla
        if route_str not in [" -> ".join(r) for r in routes]:
            routes.append(route)

    return routes[:count]


def geocode_place(place_name: str) -> Tuple[float, float]:
    """Yer ismini koordinata çevir"""
    try:
        response = requests.get(f"{API_BASE}/geocode", params={"query": place_name}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and data.get("results"):
                result = data["results"][0]
                return (result["lat"], result["lon"])
    except Exception as e:
        print(f"[ERROR] Geocode failed for {place_name}: {e}")
    return None


def calculate_route(points: List[Tuple[float, float]], route_type: str = "route_1") -> Dict:
    """Rota hesapla"""
    try:
        response = requests.post(
            f"{API_BASE}/get-route",
            json={"points": points, "route_type": route_type},
            timeout=60
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.text}
    except Exception as e:
        return {"error": str(e)}


def get_alternative_routes(points: List[Tuple[float, float]]) -> Dict:
    """Alternatif rotaları al"""
    try:
        response = requests.post(
            f"{API_BASE}/get-alternative-routes",
            json={"points": points},
            timeout=60
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.text}
    except Exception as e:
        return {"error": str(e)}


def calculate_overlap_ratio(route1_coords: List[List[float]], route2_coords: List[List[float]]) -> float:
    """İki rota arasındaki overlap oranını hesapla (basit yaklaşım)"""
    if not route1_coords or not route2_coords:
        return 0.0

    set1 = set((round(lat, 5), round(lon, 5)) for lat, lon in route1_coords)
    set2 = set((round(lat, 5), round(lon, 5)) for lat, lon in route2_coords)

    if not set2:
        return 0.0

    # Asimetrik overlap: route2'nin % kaçı route1 ile aynı
    intersection = set1 & set2
    return len(intersection) / len(set2) * 100 if set2 else 0.0


def score_alternative_routes(main_route: Dict, alternatives: Dict) -> Dict:
    """Alternatif rotaları skorla"""
    scores = {
        "total_routes": 0,
        "routes": [],
        "avg_overlap": 0,
        "min_overlap": 100,
        "max_overlap": 0,
    }

    if main_route.get("error") or alternatives.get("error"):
        return scores

    main_coords = main_route.get("route_coords", [])
    if not main_coords:
        return scores

    alt_routes = alternatives.get("alternative_routes", [])
    scores["total_routes"] = len(alt_routes) + 1  # Ana rota + alternatifler

    overlaps = []
    for alt in alt_routes:
        alt_coords = alt.get("route_coords", [])
        overlap = calculate_overlap_ratio(main_coords, alt_coords)

        scores["routes"].append({
            "type": alt.get("type", "unknown"),
            "distance_km": alt.get("distance_km", 0),
            "overlap_percent": round(overlap, 2),
        })

        overlaps.append(overlap)
        scores["min_overlap"] = min(scores["min_overlap"], overlap)
        scores["max_overlap"] = max(scores["max_overlap"], overlap)

    if overlaps:
        scores["avg_overlap"] = round(sum(overlaps) / len(overlaps), 2)

    return scores


def run_single_test(route_names: List[str], test_id: int) -> Dict:
    """Tek rota testi çalıştır"""
    print(f"\n[TEST {test_id:03d}] {' -> '.join(route_names)}")

    # Geocoding
    print(f"  [1/4] Geocoding {len(route_names)} places...")
    points = []
    for name in route_names:
        coord = geocode_place(name)
        if coord:
            points.append(coord)
            print(f"    ✓ {name}: {coord}")
        else:
            print(f"    ✗ {name}: FAILED")
            return {
                "test_id": test_id,
                "route": " -> ".join(route_names),
                "status": "geocode_failed",
                "failed_at": name
            }

    # Ana rota
    print(f"  [2/4] Calculating main route...")
    start_time = time.time()
    main_route = calculate_route(points, "route_1")
    main_time = time.time() - start_time

    if main_route.get("error"):
        print(f"    ✗ Main route FAILED: {main_route['error']}")
        return {
            "test_id": test_id,
            "route": " -> ".join(route_names),
            "status": "route_failed",
            "error": main_route.get("error")
        }

    print(f"    ✓ Main route: {main_route.get('distance_km', 0):.2f}km, {main_time:.2f}s")

    # Alternatif rotalar
    print(f"  [3/4] Getting alternative routes...")
    start_time = time.time()
    alternatives = get_alternative_routes(points)
    alt_time = time.time() - start_time

    if alternatives.get("error"):
        print(f"    ✗ Alternatives FAILED: {alternatives['error']}")
        return {
            "test_id": test_id,
            "route": " -> ".join(route_names),
            "status": "alternatives_failed",
            "main_distance": main_route.get("distance_km", 0),
            "error": alternatives.get("error")
        }

    # Skorlama
    print(f"  [4/4] Scoring alternatives...")
    scores = score_alternative_routes(main_route, alternatives)

    result = {
        "test_id": test_id,
        "route": " -> ".join(route_names),
        "num_points": len(points),
        "status": "success",
        "main_route": {
            "distance_km": main_route.get("distance_km", 0),
            "duration_min": main_route.get("estimated_walk_minutes", 0),
            "calculation_time_sec": round(main_time, 2),
        },
        "alternatives": {
            "total": scores["total_routes"],
            "avg_overlap": scores["avg_overlap"],
            "min_overlap": round(scores["min_overlap"], 2),
            "max_overlap": round(scores["max_overlap"], 2),
            "calculation_time_sec": round(alt_time, 2),
            "routes": scores["routes"],
        },
        "total_time_sec": round(main_time + alt_time, 2),
    }

    # Özet
    print(f"  ✓ Total routes: {scores['total_routes']}")
    print(f"  ✓ Avg overlap: {scores['avg_overlap']}%")
    print(f"  ✓ Time: {result['total_time_sec']}s")

    return result


def analyze_results(results: List[Dict]) -> Dict:
    """Test sonuçlarını analiz et"""
    total = len(results)
    success = sum(1 for r in results if r["status"] == "success")
    failed = total - success

    # Başarılı testlerin analizi
    success_results = [r for r in results if r["status"] == "success"]

    # Overlap analizi
    overlaps = [r["alternatives"]["avg_overlap"] for r in success_results if r["alternatives"]["avg_overlap"] > 0]

    # Mesafe analizi
    distances = [r["main_route"]["distance_km"] for r in success_results]

    # Performans analizi
    times = [r["total_time_sec"] for r in success_results]

    # Overlap kategorileri
    overlap_categories = {
        "excellent": sum(1 for o in overlaps if 0 <= o < 20),
        "good": sum(1 for o in overlaps if 20 <= o < 40),
        "acceptable": sum(1 for o in overlaps if 40 <= o < 60),
        "poor": sum(1 for o in overlaps if 60 <= o < 80),
        "very_poor": sum(1 for o in overlaps if o >= 80),
    }

    return {
        "total_tests": total,
        "successful": success,
        "failed": failed,
        "success_rate": round(success / total * 100, 2) if total > 0 else 0,
        "overlap_stats": {
            "avg": round(sum(overlaps) / len(overlaps), 2) if overlaps else 0,
            "min": round(min(overlaps), 2) if overlaps else 0,
            "max": round(max(overlaps), 2) if overlaps else 0,
            "categories": overlap_categories,
        },
        "distance_stats": {
            "avg": round(sum(distances) / len(distances), 2) if distances else 0,
            "min": round(min(distances), 2) if distances else 0,
            "max": round(max(distances), 2) if distances else 0,
        },
        "performance_stats": {
            "avg": round(sum(times) / len(times), 2) if times else 0,
            "min": round(min(times), 2) if times else 0,
            "max": round(max(times), 2) if times else 0,
        },
    }


def main():
    """Ana test fonksiyonu"""
    print("=" * 70)
    print(" " * 15 + "100 ROTA TESTİ - ALTERNATİF ROTA ANALİZİ")
    print("=" * 70)
    print(f"Başlangıç: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 70)

    # Test rotalarını üret
    print("\n[0/4] Test senaryoları oluşturuluyor...")
    routes = generate_test_routes(100)
    print(f"  ✓ {len(routes)} benzersiz rota senaryosu hazırlandı")

    # Testleri çalıştır
    print("\n[1/4] Testler çalıştırılıyor...")
    results = []
    for i, route_names in enumerate(routes, 1):
        result = run_single_test(route_names, i)
        results.append(result)

        # Her 10 testte bir özet
        if i % 10 == 0:
            success_count = sum(1 for r in results if r["status"] == "success")
            print(f"\n  --- {i}/{len(routes)} test tamamlandı, {success_count} başarılı ---\n")

    # Sonuçları analiz et
    print("\n[2/4] Sonuçlar analiz ediliyor...")
    analysis = analyze_results(results)

    # Logları kaydet
    print("\n[3/4] Loglar kaydediliyor...")
    timestamp = datetime.now().strftime("%d.%m.%Y_%H%M")
    log_file = f"test_100_routes_{timestamp}.json"

    with open(log_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "analysis": analysis,
        }, f, ensure_ascii=False, indent=2)

    print(f"  ✓ Log kaydedildi: {log_file}")

    # Rapor yazdır
    print("\n[4/4] TEST RAPORU:")
    print("=" * 70)
    print(f"Toplam Test:        {analysis['total_tests']}")
    print(f"Başarılı:           {analysis['successful']} (%{analysis['success_rate']})")
    print(f"Başarısız:          {analysis['failed']}")
    print()
    print("Overlap İstatistikleri:")
    print(f"  Ortalama:         %{analysis['overlap_stats']['avg']}")
    print(f"  Min:              %{analysis['overlap_stats']['min']}")
    print(f"  Max:              %{analysis['overlap_stats']['max']}")
    print()
    print("Overlap Kategorileri:")
    for category, count in analysis['overlap_stats']['categories'].items():
        print(f"  {category:15s}: {count}")
    print()
    print("Mesafe İstatistikleri:")
    print(f"  Ortalama:         {analysis['distance_stats']['avg']} km")
    print(f"  Min:              {analysis['distance_stats']['min']} km")
    print(f"  Max:              {analysis['distance_stats']['max']} km")
    print()
    print("Performans İstatistikleri:")
    print(f"  Ortalama:         {analysis['performance_stats']['avg']} sn")
    print(f"  Min:              {analysis['performance_stats']['min']} sn")
    print(f"  Max:              {analysis['performance_stats']['max']} sn")
    print("=" * 70)
    print(f"Bitiş: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 70)

    return results, analysis


if __name__ == "__main__":
    main()
