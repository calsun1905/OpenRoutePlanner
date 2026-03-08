import os
import sys

# Script scripts/tools/ içinde; backend OpenRoutePlanner/backend'de
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.join(_script_dir, '..', '..')
sys.path.insert(0, os.path.join(_project_root, 'backend'))

from graph_manager import get_graph

def download_istanbul():
    print("--- Tüm İstanbul Haritası İndirme Testi Başlıyor (UYARI: UZUN SÜREBİLİR) ---")
    
    region = "Istanbul, Turkey"
    
    print(f"\nİndiriliyor: {region}...")
    print("Milyonlarca düğüm indireceği için bu işlem OSM sunucularından dolayı dakikalar hatta saatler sürebilir.")
    try:
        G = get_graph(region)
        nodes_count = len(G.nodes)
        edges_count = len(G.edges)
        print(f"✅ Bitti! {region} başarıyla indirildi.")
        print(f"📊 İstatistikler: {nodes_count} düğüm (kavşak), {edges_count} kenar (yol/sokak).")
    except Exception as e:
        print(f"❌ Hata oluştu ({region}): {e}")

if __name__ == "__main__":
    download_istanbul()
    print("\nTest bitti.")
