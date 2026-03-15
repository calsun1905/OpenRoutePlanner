"""
Hızlı Rota Testi - 20 Senaryo
"""
import requests
import json
import time
from datetime import datetime

API_BASE = "http://127.0.0.1:5000/api"

# Test senaryoları - İstanbul
TEST_ROUTES = [
    # Kısa mesafe
    ["Kadıköy", "Moda"],
    ["Taksim", "Cihangir"],
    ["Beşiktaş", "Ortaköy"],

    # Orta mesafe
    ["Kadıköy", "Beşiktaş"],
    ["Taksim", "Kadıköy"],
    ["Şişli", "Kadıköy"],
    ["Üsküdar", "Taksim"],

    # Uzun mesafe
    ["Kadıköy", "Sarıyer"],
    ["Bostancı", "Etiler"],
    ["Kozyatağı", "Levent"],

    # Çok noktalı
    ["Kadıköy", "Moda", "Caferağa"],
    ["Taksim", "Cihangir", "Karaköy"],
    ["Beşiktaş", "Ortaköy", "Bebek"],
    ["Şişli", "Mecidiyeköy", "Levent"],

    # Boğaz geçişleri
    ["Üsküdar", "Eminönü"],
    ["Kadıköy", "Karaköy"],
    ["Kadıköy", "Beşiktaş", "Sarıyer"],

    # Diğer bölgeler
    ["Bostancı", "Göztepe", "Kadıköy"],
    ["Levent", "Maslak", "Sarıyer"],
    ["Taksim", "Şişli", "Levent", "Etiler"],
    ["Kadıköy", "Fenerbahçe", "Göztepe", "Bostancı"],
    ["Üsküdar", "Kuzguncuk", "Beylerbeyi", "Çengelköy"],
]

def geocode(place):
    try:
        r = requests.post(f"{API_BASE}/geocode", json={"place": place}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success":
                return (data["lat"], data["lon"])
    except Exception as e:
        print(f"    Geocode error for {place}: {e}")
    return None

def run_route(route_points, route_id):
    print(f"\n[{route_id:02d}] {' -> '.join(route_points)}")

    # Geocode
    points = []
    for name in route_points:
        coord = geocode(name)
        if coord:
            points.append(coord)
            print(f"  + {name}: {coord}")
        else:
            print(f"  X {name}: FAILED")
            return None

    # Ana rota
    try:
        start = time.time()
        r = requests.post(f"{API_BASE}/get-route",
                         json={"points": points, "route_type": "route_1"},
                         timeout=30)
        main_time = time.time() - start

        if r.status_code != 200:
            print(f"  X Route FAILED: {r.status_code}")
            return None

        main = r.json()
        print(f"  + Main: {main.get('total_distance_km', 0):.2f}km ({main_time:.1f}s)")

        # Alternatif rotalar
        start = time.time()
        r = requests.post(f"{API_BASE}/get-alternative-routes",
                         json={"points": points},
                         timeout=60)
        alt_time = time.time() - start

        if r.status_code != 200:
            print(f"  X Alternatives FAILED")
            return main

        alts = r.json()
        alt_routes = alts.get("alternatives", [])

        print(f"  + Alts: {len(alt_routes)} routes ({alt_time:.1f}s)")

        # Overlap hesapla
        main_coords = main.get("route_coords", [])
        overlaps = []

        for alt in alt_routes:
            alt_coords = alt.get("route_coords", [])
            if main_coords and alt_coords:
                set1 = set((round(lat, 5), round(lon, 5)) for lat, lon in main_coords)
                set2 = set((round(lat, 5), round(lon, 5)) for lat, lon in alt_coords)
                overlap = len(set1 & set2) / len(set2) * 100 if set2 else 0
                overlaps.append(overlap)
                print(f"    - {alt.get('type', 'unknown')}: {alt.get('total_distance_km', 0):.2f}km, overlap %{overlap:.1f}")

        return {
            "route": " -> ".join(route_points),
            "num_points": len(points),
            "main_distance": main.get("total_distance_km", 0),
            "main_time": main_time,
            "alt_count": len(alt_routes),
            "alt_time": alt_time,
            "overlaps": overlaps,
            "avg_overlap": sum(overlaps)/len(overlaps) if overlaps else 0,
            "total_time": main_time + alt_time,
        }

    except Exception as e:
        print(f"  X ERROR: {e}")
        return None

def main():
    print("="*60)
    print(" " * 15 + "ROTA TESTİ - 20 SENARYO")
    print("=" * 60)
    print(f"Start: {datetime.now().strftime('%H:%M:%S')}\n")

    results = []
    for i, route in enumerate(TEST_ROUTES, 1):
        result = run_route(route, i)
        if result:
            results.append(result)

    print("\n" + "=" * 60)
    print("RAPOR")
    print("=" * 60)

    if results:
        print(f"Başarılı: {len(results)}/{len(TEST_ROUTES)}")

        overlaps = [r["avg_overlap"] for r in results if r["avg_overlap"] > 0]
        if overlaps:
            print(f"\nOverlap:")
            print(f"  Ortalama: %{sum(overlaps)/len(overlaps):.1f}")
            print(f"  Min: %{min(overlaps):.1f}")
            print(f"  Max: %{max(overlaps):.1f}")

            cats = {
                "excellent (<20%)": sum(1 for o in overlaps if o < 20),
                "good (20-40%)": sum(1 for o in overlaps if 20 <= o < 40),
                "ok (40-60%)": sum(1 for o in overlaps if 40 <= o < 60),
                "poor (>60%)": sum(1 for o in overlaps if o >= 60),
            }
            for cat, count in cats.items():
                print(f"  {cat}: {count}")

        times = [r["total_time"] for r in results]
        print(f"\nZaman:")
        print(f"  Ortalama: {sum(times)/len(times):.1f}s")
        print(f"  Min: {min(times):.1f}s")
        print(f"  Max: {max(times):.1f}s")

    # Kaydet
    timestamp = datetime.now().strftime("%d%m%Y_%H%M")
    with open(f"test_results_{timestamp}.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nKaydedildi: test_results_{timestamp}.json")
    print(f"End: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()
