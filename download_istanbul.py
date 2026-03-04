import os
import sys

# Backend klasörünü Python yoluna ekleyelim ki graph_manager import edilebilsin
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

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
