import os
import sys

# Script scripts/tools/ içinde; backend OpenRoutePlanner/backend'de
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.join(_script_dir, '..', '..')
sys.path.insert(0, os.path.join(_project_root, 'backend'))

from graph_manager import get_graph

def download_maps():
    print("--- Harita Ön İndirme (Pre-fetching) Testi Başlıyor ---")
    
    # Test için tek bir bölge belirleyelim
    regions_to_download = [
        "Kadikoy, Istanbul, Turkey",
        # İstersen ileride buraya "Besiktas, Istanbul, Turkey" vs. ekleyebiliriz
    ]
    
    for region in regions_to_download:
        print(f"\nİndiriliyor: {region}...")
        try:
            # get_graph fonksiyonu zaten OSM'den indirip .graphml olarak kaydeden mantığa sahip.
            # Sadece çağırmamız yeterli.
            G = get_graph(region)
            nodes_count = len(G.nodes)
            edges_count = len(G.edges)
            print(f"✅ Bitti! {region} başarıyla indirildi.")
            print(f"📊 İstatistikler: {nodes_count} düğüm (kavşak), {edges_count} kenar (yol/sokak).")
        except Exception as e:
            print(f"❌ Hata oluştu ({region}): {e}")

if __name__ == "__main__":
    download_maps()
    print("\nTest tamamlandı. 'backend/data/' klasörünü kontrol ederek indirilen .graphml boyutlarına bakabiliriz.")
