"""
route_config.py - Rota Motoru Konfigürasyon Sabitleri v3.1

route_engine.py içindeki tüm hardcoded değerlerin merkezi referansı.
Şu an sadece referans amaçlı  " ilerleyen aşamada route_engine.py buradan okuyacak.

Kullanım (ileride):
    from route_config import ROUTE_CONFIG
    walk_speed = ROUTE_CONFIG["WALK_SPEED_KMH"]
"""

ROUTE_CONFIG = {

    # =========================================================================
    # GENEL
    # =========================================================================

    # Yürüme hızı (km/saat). calculate_route_stats() içinde kullanılır.
    "WALK_SPEED_KMH": 5.0,

    # Varsayılan kaç alternatif rota isteneceği.
    "DEFAULT_NUM_ROUTES": 3,

    # Graf indirme yarıçapı (metre)
    "GRAPH_RADIUS_MIN_M": 500,
    "GRAPH_RADIUS_PADDING_M": 300,
    "GRAPH_RADIUS_MAX_M": 3500,

    # =========================================================================
    # CACHE YÖNETİMİ  " LRU Cache Ayarları
    # =========================================================================

    # Graph cache maksimum boyutu (RAM'de tutulan graf sayısı)
    "GRAPH_CACHE_MAXSIZE": 10,

    # Graph cache TTL (saniye) - 1 saat sonra yeniden yüklenir
    "GRAPH_CACHE_TTL": 3600,

    # Graph cache dizini (disk)
    "GRAPH_CACHE_DIR": "backend/data",

    # POI cache maksimum boyutu
    "POI_CACHE_MAXSIZE": 50,

    # POI cache TTL (saniye) - 30 dakika
    "POI_CACHE_TTL": 1800,

    # POI kalici cache tazelik pencereleri
    # Soft TTL: bu sureden sonra cache gosterilir ama arkada yenileme tetiklenir.
    "POI_CACHE_SOFT_TTL_DAYS": 14,
    # Hard TTL: bu sureden sonra cache artik gecersiz sayilir, canli sorgu zorunlu olur.
    "POI_CACHE_HARD_TTL_DAYS": 30,
    # Bos sonuc cache'i daha kisa sureli tutulur (yeni acilan mekanlari yakalamak icin).
    "POI_CACHE_EMPTY_TTL_HOURS": 24,
    # Ana pois tablosu guncellenmeden once kopyalanan eski surum sayisi (yer + kategori basina).
    "POI_ARCHIVE_MAX_PER_KEY": 5,

    # =========================================================================
    # OVERLAP (ÖRTÜŞMe) EŞİKLERİ  " dynamic_overlap_threshold()
    # v3.0: Asimetrik formül kullanılıyor (Jaccard değil).
    # "Yeni rotanın kenarlarının % kaçı eski rotayla örtüşüyor?"
    # Değer 1.0 = tamamen aynı yol, 0.0 = hiç ortak kenar yok.
    # =========================================================================

    "OVERLAP_THRESHOLD_SHORT": 0.90,       # mesafe < 1.0 km
    "OVERLAP_THRESHOLD_MEDIUM": 0.80,      # 1.0 a‰¤ mesafe < 3.0 km
    "OVERLAP_THRESHOLD_LONG": 0.75,        # 3.0 a‰¤ mesafe < 7.0 km
    "OVERLAP_THRESHOLD_VERY_LONG": 0.70,   # mesafe a‰¥ 7.0 km

    # =========================================================================
    # MESAFE SINIRLARI  " overlap eşiği ve aday sayısı hesaplamalarında
    # =========================================================================

    "DISTANCE_VERY_SHORT_KM": 1.0,
    "DISTANCE_SHORT_KM": 3.0,
    "DISTANCE_LONG_KM": 7.0,

    # =========================================================================
    # YEN'S K-SHORTEST  " get_max_candidates()
    # Aday rota sayısı: kısa mesafede az, uzun mesafede fazla denensin.
    # =========================================================================

    "MAX_CANDIDATES_VERY_SHORT": 50,
    "MAX_CANDIDATES_SHORT": 75,
    "MAX_CANDIDATES_LONG": 100,
    "MAX_CANDIDATES_VERY_LONG": 150,

    # =========================================================================
    # VIA-NODE (ARA NOKTA)  " v3.0 YENİ
    # Endüstri standardı alternatif rota üretimi.
    # Ana rotadan uzak büyük kavşaklardan geçmeye zorlar (A a†’ C a†’ B).
    # =========================================================================

    # Kaç via-node rotası isteniyor (varsayılan, num_routes-1 olarak hesaplanır)
    # route_engine.py a†’ find_via_node_routes(num_via_routes=num_routes-1)
    "VIA_NODE_DEFAULT_COUNT": 2,

    # Via-node bounding box genişletme oranı (%30) ve minimum marjin (~200m)
    # route_engine.py a†’ (lat_max - lat_min) * 0.3, MIN_MARGIN = 0.002
    "VIA_NODE_BBOX_EXPAND_RATIO": 0.3,
    "VIA_NODE_BBOX_MIN_MARGIN": 0.002,

    # Via-node olabilmek için minimum kavşak derecesi (degree)
    # route_engine.py a†’ if degree >= 3
    "VIA_NODE_MIN_DEGREE": 3,

    # En fazla kaç aday via-node denenir
    # route_engine.py a†’ scored[:30]
    "VIA_NODE_MAX_CANDIDATES": 30,

    # Via-node rotaları arası maksimum overlap (kendi aralarında)
    # route_engine.py a†’ if overlap > 0.70
    "VIA_NODE_SELF_OVERLAP_LIMIT": 0.70,

    # Via-node rotasının ana rotaya kıyasla kabul edilen maks uzunluk oranı
    # route_engine.py a†’ max_distance_ratio=1.5
    "VIA_NODE_MAX_DISTANCE_RATIO": 1.5,

    # Rota sampling oranı (performans için her kaçıncı nokta alınır)
    # route_engine.py a†’ main_coords[::max(1, len(main_coords) // 20)]
    "VIA_NODE_ROUTE_SAMPLE_COUNT": 20,

    # =========================================================================
    # GÖVDE-ONLY PENALTY  " v3.0 YENİ
    # Zikzak önleme: Rotanın baş/son kısmına dokunma, sadece gövdeye ceza.
    # =========================================================================

    # Baş ve sondan atlanacak kenar oranı
    # route_engine.py a†’ get_body_edges(edges, skip_ratio=0.10)
    "BODY_EDGES_SKIP_RATIO": 0.10,

    # =========================================================================
    # DİSJOINT PATHS  " find_disjoint_paths() [ESKİ - v3.0'da kullanılmıyor]
    # =========================================================================

    "DISJOINT_NUM_PATHS": 2,
    "MAX_REALISTIC_ROUTES": 3,

    # =========================================================================
    # PENALTY-BASED GENERATION  " apply_penalty_to_graph(), find_routes_with_penalty()
    # v3.0: Her iterasyonda penalty graf YENİDEN oluşturuluyor.
    # =========================================================================

    # Cezalandırma çarpanı: kullanılmış kenar bu kadar pahalı görünür.
    "PENALTY_FACTOR": 2.0,

    # Penalty çağrısında kaç ekstra aday denen
    "PENALTY_EXTRA_CANDIDATES": 1,

    # =========================================================================
    # CONNECTİVİTY BAZLI DİNAMİK EŞİK ÇARPANLARI
    # dynamic_overlap_threshold_connectivity() içinde kullanılır.
    # =========================================================================

    "CONNECTIVITY_HIGH_MULTIPLIER": 0.75,    # connectivity a‰¥ 3
    "CONNECTIVITY_MEDIUM_MULTIPLIER": 0.85,  # connectivity == 2
    "CONNECTIVITY_LOW_MULTIPLIER": 0.95,     # connectivity == 1

    # =========================================================================
    # FALLBACK  " get_fallback_routes()
    # =========================================================================

    "FALLBACK_NEIGHBOR_LIMIT": 3,
    "FALLBACK_DISTANCE_MULTIPLIER": 1.5,

    # POI — buyuk idari alan (il/ilce) icin parcali (grid) tarama
    # Bbox en/boyu bu km degerini asinca tek features_from_place yerine izgara hucresi sorgulari.
    "POI_BOUNDARY_CHUNK_MIN_KM": 12.0,
    "POI_CHUNK_CELL_KM": 4.0,
    "POI_CHUNK_MAX_CELLS": 36,

}
