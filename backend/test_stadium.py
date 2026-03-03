"""
Stadyum tag'ini test et - Gerçekten var mı?
"""
import osmnx as ox

def test_stadium_tag():
    """
    İstanbul'da stadyum ara - Gerçekten var mı?
    """
    print("=" * 80)
    print("STADYUM TAG TESTİ")
    print("=" * 80)
    print()
    
    # Test 1: leisure=stadium
    print("🔍 Test 1: leisure=stadium")
    try:
        gdf = ox.features_from_place(
            "Istanbul, Turkey",
            tags={"leisure": "stadium"}
        )
        
        if len(gdf) > 0:
            print(f"   ✅ BULUNDU! {len(gdf)} adet stadyum var")
            print()
            print("   İlk 5 Stadyum:")
            for i, (idx, row) in enumerate(gdf.head(5).iterrows(), 1):
                name = row.get("name", "İsimsiz")
                print(f"   {i}. {name}")
        else:
            print("   ❌ Hiç stadyum bulunamadı")
    except Exception as e:
        print(f"   ❌ HATA: {e}")
    
    print()
    print("-" * 80)
    print()
    
    # Test 2: amenity=cafe (karşılaştırma için)
    print("🔍 Test 2: amenity=cafe (karşılaştırma)")
    try:
        gdf = ox.features_from_place(
            "Kadikoy, Istanbul, Turkey",
            tags={"amenity": "cafe"}
        )
        
        if len(gdf) > 0:
            print(f"   ✅ BULUNDU! {len(gdf)} adet kafe var")
            print()
            print("   İlk 5 Kafe:")
            for i, (idx, row) in enumerate(gdf.head(5).iterrows(), 1):
                name = row.get("name", "İsimsiz")
                print(f"   {i}. {name}")
        else:
            print("   ❌ Hiç kafe bulunamadı")
    except Exception as e:
        print(f"   ❌ HATA: {e}")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    test_stadium_tag()
