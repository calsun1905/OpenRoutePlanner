"""
route_config.py - Rota Motoru Konfigürasyon Sabitleri v3.0

route_engine.py içindeki tüm hardcoded değerlerin merkezi referansı.
Şu an sadece referans amaçlı — ilerleyen aşamada route_engine.py buradan okuyacak.

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

    # =========================================================================
    # OVERLAP (ÖRTÜŞMe) EŞİKLERİ — dynamic_overlap_threshold()
    # v3.0: Asimetrik formül kullanılıyor (Jaccard değil).
    # "Yeni rotanın kenarlarının % kaçı eski rotayla örtüşüyor?"
    # Değer 1.0 = tamamen aynı yol, 0.0 = hiç ortak kenar yok.
    # =========================================================================

    "OVERLAP_THRESHOLD_SHORT": 0.90,       # mesafe < 1.0 km
    "OVERLAP_THRESHOLD_MEDIUM": 0.80,      # 1.0 ≤ mesafe < 3.0 km
    "OVERLAP_THRESHOLD_LONG": 0.75,        # 3.0 ≤ mesafe < 7.0 km
    "OVERLAP_THRESHOLD_VERY_LONG": 0.70,   # mesafe ≥ 7.0 km

    # =========================================================================
    # MESAFE SINIRLARI — overlap eşiği ve aday sayısı hesaplamalarında
    # =========================================================================

    "DISTANCE_VERY_SHORT_KM": 1.0,
    "DISTANCE_SHORT_KM": 3.0,
    "DISTANCE_LONG_KM": 7.0,

    # =========================================================================
    # YEN'S K-SHORTEST — get_max_candidates()
    # Aday rota sayısı: kısa mesafede az, uzun mesafede fazla denensin.
    # =========================================================================

    "MAX_CANDIDATES_VERY_SHORT": 50,
    "MAX_CANDIDATES_SHORT": 75,
    "MAX_CANDIDATES_LONG": 100,
    "MAX_CANDIDATES_VERY_LONG": 150,

    # =========================================================================
    # VIA-NODE (ARA NOKTA) — v3.0 YENİ
    # Endüstri standardı alternatif rota üretimi.
    # Ana rotadan uzak büyük kavşaklardan geçmeye zorlar (A → C → B).
    # =========================================================================

    # Kaç via-node rotası isteniyor (varsayılan, num_routes-1 olarak hesaplanır)
    # route_engine.py → find_via_node_routes(num_via_routes=num_routes-1)
    "VIA_NODE_DEFAULT_COUNT": 2,

    # Via-node bounding box genişletme oranı (%30) ve minimum marjin (~200m)
    # route_engine.py → (lat_max - lat_min) * 0.3, MIN_MARGIN = 0.002
    "VIA_NODE_BBOX_EXPAND_RATIO": 0.3,
    "VIA_NODE_BBOX_MIN_MARGIN": 0.002,

    # Via-node olabilmek için minimum kavşak derecesi (degree)
    # route_engine.py → if degree >= 3
    "VIA_NODE_MIN_DEGREE": 3,

    # En fazla kaç aday via-node denenir
    # route_engine.py → scored[:30]
    "VIA_NODE_MAX_CANDIDATES": 30,

    # Via-node rotaları arası maksimum overlap (kendi aralarında)
    # route_engine.py → if overlap > 0.70
    "VIA_NODE_SELF_OVERLAP_LIMIT": 0.70,

    # Via-node rotasının ana rotaya kıyasla kabul edilen maks uzunluk oranı
    # route_engine.py → max_distance_ratio=1.5
    "VIA_NODE_MAX_DISTANCE_RATIO": 1.5,

    # Rota sampling oranı (performans için her kaçıncı nokta alınır)
    # route_engine.py → main_coords[::max(1, len(main_coords) // 20)]
    "VIA_NODE_ROUTE_SAMPLE_COUNT": 20,

    # =========================================================================
    # GÖVDE-ONLY PENALTY — v3.0 YENİ
    # Zikzak önleme: Rotanın baş/son kısmına dokunma, sadece gövdeye ceza.
    # =========================================================================

    # Baş ve sondan atlanacak kenar oranı
    # route_engine.py → get_body_edges(edges, skip_ratio=0.10)
    "BODY_EDGES_SKIP_RATIO": 0.10,

    # =========================================================================
    # DİSJOINT PATHS — find_disjoint_paths() [ESKİ - v3.0'da kullanılmıyor]
    # =========================================================================

    "DISJOINT_NUM_PATHS": 2,
    "MAX_REALISTIC_ROUTES": 3,

    # =========================================================================
    # PENALTY-BASED GENERATION — apply_penalty_to_graph(), find_routes_with_penalty()
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

    "CONNECTIVITY_HIGH_MULTIPLIER": 0.75,    # connectivity ≥ 3
    "CONNECTIVITY_MEDIUM_MULTIPLIER": 0.85,  # connectivity == 2
    "CONNECTIVITY_LOW_MULTIPLIER": 0.95,     # connectivity == 1

    # =========================================================================
    # FALLBACK — get_fallback_routes()
    # =========================================================================

    "FALLBACK_NEIGHBOR_LIMIT": 3,
    "FALLBACK_DISTANCE_MULTIPLIER": 1.5,

}
