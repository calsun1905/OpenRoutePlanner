"""
OSM Tag Kontrolü - Bir tag'in gerçekten var olup olmadığını kontrol eder
"""
import requests

def check_tag_exists(key, value):
    """
    Taginfo API'den bir tag'in var olup olmadığını kontrol eder
    
    Args:
        key: OSM key (örn: "leisure", "amenity")
        value: OSM value (örn: "stadium", "cafe")
    
    Returns:
        dict: Tag bilgileri ve istatistikler
    """
    url = "https://taginfo.openstreetmap.org/api/4/tag/stats"
    params = {
        "key": key,
        "value": value
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if "data" in data and len(data["data"]) > 0:
            stats = data["data"][0]
            return {
                "exists": True,
                "count": stats.get("count", 0),
                "count_nodes": stats.get("count_nodes", 0),
                "count_ways": stats.get("count_ways", 0),
                "count_relations": stats.get("count_relations", 0),
            }
        else:
            return {"exists": False, "count": 0}
    except Exception as e:
        print(f"Hata: {e}")
        return {"exists": False, "error": str(e)}


def check_all_categories():
    """
    graph_manager.py'deki tüm kategorileri kontrol eder
    """
    # graph_manager.py'deki tag_map
    categories = {
        "stadium": {"leisure": "stadium"},
        "cafe": {"amenity": "cafe"},
        "museum": {"tourism": "museum"},
        "bakery": {"shop": "bakery"},
        "zoo": {"tourism": "zoo"},
        "castle": {"historic": "castle"},
        "pharmacy": {"amenity": "pharmacy"},
        "bookshop": {"shop": "books"},
        "gym": {"leisure": "fitness_centre"},
        "swimming_pool": {"leisure": "swimming_pool"},
    }
    
    print("=" * 80)
    print("OSM TAG KONTROLÜ - Gerçek Hayatta Var mı?")
    print("=" * 80)
    print()
    
    results = []
    
    for category_name, tags in categories.items():
        # İlk key-value çiftini al
        key = list(tags.keys())[0]
        value = list(tags.values())[0]
        
        print(f"🔍 Kontrol ediliyor: {category_name} → {key}={value}")
        
        result = check_tag_exists(key, value)
        
        if result.get("exists"):
            count = result.get("count", 0)
            nodes = result.get("count_nodes", 0)
            ways = result.get("count_ways", 0)
            
            print(f"   ✅ VAR! Dünyada {count:,} adet bulundu")
            print(f"      - Nokta (node): {nodes:,}")
            print(f"      - Çizgi (way): {ways:,}")
            
            results.append({
                "category": category_name,
                "tag": f"{key}={value}",
                "exists": True,
                "count": count
            })
        else:
            print(f"   ❌ YOK! Bu tag kullanılmıyor")
            results.append({
                "category": category_name,
                "tag": f"{key}={value}",
                "exists": False,
                "count": 0
            })
        
        print()
    
    # Özet
    print("=" * 80)
    print("ÖZET")
    print("=" * 80)
    
    # En popüler 5
    results_sorted = sorted(results, key=lambda x: x["count"], reverse=True)
    
    print("\n📊 En Popüler 5 Kategori:")
    for i, r in enumerate(results_sorted[:5], 1):
        if r["exists"]:
            print(f"{i}. {r['category']:15} → {r['count']:>10,} adet")
    
    # Var olmayanlar
    not_exists = [r for r in results if not r["exists"]]
    if not_exists:
        print("\n❌ Var Olmayan Kategoriler:")
        for r in not_exists:
            print(f"   - {r['category']} ({r['tag']})")
    
    return results


if __name__ == "__main__":
    check_all_categories()
