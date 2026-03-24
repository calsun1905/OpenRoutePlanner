"""
route_config.py - Rota Motoru KonfigÃ¼rasyon Sabitleri v3.1

route_engine.py iÃ§indeki tÃ¼m hardcoded deÄŸerlerin merkezi referansÄ±.
Åu an sadece referans amaÃ§lÄ± â€” ilerleyen aÅŸamada route_engine.py buradan okuyacak.

KullanÄ±m (ileride):
    from route_config import ROUTE_CONFIG
    walk_speed = ROUTE_CONFIG["WALK_SPEED_KMH"]
"""

ROUTE_CONFIG = {

    # =========================================================================
    # GENEL
    # =========================================================================

    # YÃ¼rÃ¼me hÄ±zÄ± (km/saat). calculate_route_stats() iÃ§inde kullanÄ±lÄ±r.
    "WALK_SPEED_KMH": 5.0,

    # VarsayÄ±lan kaÃ§ alternatif rota isteneceÄŸi.
    "DEFAULT_NUM_ROUTES": 3,

    # Graf indirme yarÄ±Ã§apÄ± (metre)
    "GRAPH_RADIUS_MIN_M": 500,
    "GRAPH_RADIUS_PADDING_M": 300,
    "GRAPH_RADIUS_MAX_M": 3500,

    # =========================================================================
    # CACHE YÃ–NETÄ°MÄ° â€” LRU Cache AyarlarÄ±
    # =========================================================================

    # Graph cache maksimum boyutu (RAM'de tutulan graf sayÄ±sÄ±)
    "GRAPH_CACHE_MAXSIZE": 10,

    # Graph cache TTL (saniye) - 1 saat sonra yeniden yÃ¼klenir
    "GRAPH_CACHE_TTL": 3600,

    # Graph cache dizini (disk)
    "GRAPH_CACHE_DIR": "backend/data",

    # POI cache maksimum boyutu
    "POI_CACHE_MAXSIZE": 50,

    # POI cache TTL (saniye) - 30 dakika
    "POI_CACHE_TTL": 1800,

    # POI kalici cache tazelik pencereleri
    # Soft TTL: bu sureden sonra cache gosterilir ama arkada yenileme tetiklenir.
    "POI_CACHE_SOFT_TTL_DAYS": 7,
    # Hard TTL: bu sureden sonra cache artik gecersiz sayilir, canli sorgu zorunlu olur.
    "POI_CACHE_HARD_TTL_DAYS": 30,
    # Bos sonuc cache'i daha kisa sureli tutulur (yeni acilan mekanlari yakalamak icin).
    "POI_CACHE_EMPTY_TTL_HOURS": 24,

    # =========================================================================
    # OVERLAP (Ã–RTÃœÅMe) EÅÄ°KLERÄ° â€” dynamic_overlap_threshold()
    # v3.0: Asimetrik formÃ¼l kullanÄ±lÄ±yor (Jaccard deÄŸil).
    # "Yeni rotanÄ±n kenarlarÄ±nÄ±n % kaÃ§Ä± eski rotayla Ã¶rtÃ¼ÅŸÃ¼yor?"
    # DeÄŸer 1.0 = tamamen aynÄ± yol, 0.0 = hiÃ§ ortak kenar yok.
    # =========================================================================

    "OVERLAP_THRESHOLD_SHORT": 0.90,       # mesafe < 1.0 km
    "OVERLAP_THRESHOLD_MEDIUM": 0.80,      # 1.0 â‰¤ mesafe < 3.0 km
    "OVERLAP_THRESHOLD_LONG": 0.75,        # 3.0 â‰¤ mesafe < 7.0 km
    "OVERLAP_THRESHOLD_VERY_LONG": 0.70,   # mesafe â‰¥ 7.0 km

    # =========================================================================
    # MESAFE SINIRLARI â€” overlap eÅŸiÄŸi ve aday sayÄ±sÄ± hesaplamalarÄ±nda
    # =========================================================================

    "DISTANCE_VERY_SHORT_KM": 1.0,
    "DISTANCE_SHORT_KM": 3.0,
    "DISTANCE_LONG_KM": 7.0,

    # =========================================================================
    # YEN'S K-SHORTEST â€” get_max_candidates()
    # Aday rota sayÄ±sÄ±: kÄ±sa mesafede az, uzun mesafede fazla denensin.
    # =========================================================================

    "MAX_CANDIDATES_VERY_SHORT": 50,
    "MAX_CANDIDATES_SHORT": 75,
    "MAX_CANDIDATES_LONG": 100,
    "MAX_CANDIDATES_VERY_LONG": 150,

    # =========================================================================
    # VIA-NODE (ARA NOKTA) â€” v3.0 YENÄ°
    # EndÃ¼stri standardÄ± alternatif rota Ã¼retimi.
    # Ana rotadan uzak bÃ¼yÃ¼k kavÅŸaklardan geÃ§meye zorlar (A â†’ C â†’ B).
    # =========================================================================

    # KaÃ§ via-node rotasÄ± isteniyor (varsayÄ±lan, num_routes-1 olarak hesaplanÄ±r)
    # route_engine.py â†’ find_via_node_routes(num_via_routes=num_routes-1)
    "VIA_NODE_DEFAULT_COUNT": 2,

    # Via-node bounding box geniÅŸletme oranÄ± (%30) ve minimum marjin (~200m)
    # route_engine.py â†’ (lat_max - lat_min) * 0.3, MIN_MARGIN = 0.002
    "VIA_NODE_BBOX_EXPAND_RATIO": 0.3,
    "VIA_NODE_BBOX_MIN_MARGIN": 0.002,

    # Via-node olabilmek iÃ§in minimum kavÅŸak derecesi (degree)
    # route_engine.py â†’ if degree >= 3
    "VIA_NODE_MIN_DEGREE": 3,

    # En fazla kaÃ§ aday via-node denenir
    # route_engine.py â†’ scored[:30]
    "VIA_NODE_MAX_CANDIDATES": 30,

    # Via-node rotalarÄ± arasÄ± maksimum overlap (kendi aralarÄ±nda)
    # route_engine.py â†’ if overlap > 0.70
    "VIA_NODE_SELF_OVERLAP_LIMIT": 0.70,

    # Via-node rotasÄ±nÄ±n ana rotaya kÄ±yasla kabul edilen maks uzunluk oranÄ±
    # route_engine.py â†’ max_distance_ratio=1.5
    "VIA_NODE_MAX_DISTANCE_RATIO": 1.5,

    # Rota sampling oranÄ± (performans iÃ§in her kaÃ§Ä±ncÄ± nokta alÄ±nÄ±r)
    # route_engine.py â†’ main_coords[::max(1, len(main_coords) // 20)]
    "VIA_NODE_ROUTE_SAMPLE_COUNT": 20,

    # =========================================================================
    # GÃ–VDE-ONLY PENALTY â€” v3.0 YENÄ°
    # Zikzak Ã¶nleme: RotanÄ±n baÅŸ/son kÄ±smÄ±na dokunma, sadece gÃ¶vdeye ceza.
    # =========================================================================

    # BaÅŸ ve sondan atlanacak kenar oranÄ±
    # route_engine.py â†’ get_body_edges(edges, skip_ratio=0.10)
    "BODY_EDGES_SKIP_RATIO": 0.10,

    # =========================================================================
    # DÄ°SJOINT PATHS â€” find_disjoint_paths() [ESKÄ° - v3.0'da kullanÄ±lmÄ±yor]
    # =========================================================================

    "DISJOINT_NUM_PATHS": 2,
    "MAX_REALISTIC_ROUTES": 3,

    # =========================================================================
    # PENALTY-BASED GENERATION â€” apply_penalty_to_graph(), find_routes_with_penalty()
    # v3.0: Her iterasyonda penalty graf YENÄ°DEN oluÅŸturuluyor.
    # =========================================================================

    # CezalandÄ±rma Ã§arpanÄ±: kullanÄ±lmÄ±ÅŸ kenar bu kadar pahalÄ± gÃ¶rÃ¼nÃ¼r.
    "PENALTY_FACTOR": 2.0,

    # Penalty Ã§aÄŸrÄ±sÄ±nda kaÃ§ ekstra aday denen
    "PENALTY_EXTRA_CANDIDATES": 1,

    # =========================================================================
    # CONNECTÄ°VÄ°TY BAZLI DÄ°NAMÄ°K EÅÄ°K Ã‡ARPANLARI
    # dynamic_overlap_threshold_connectivity() iÃ§inde kullanÄ±lÄ±r.
    # =========================================================================

    "CONNECTIVITY_HIGH_MULTIPLIER": 0.75,    # connectivity â‰¥ 3
    "CONNECTIVITY_MEDIUM_MULTIPLIER": 0.85,  # connectivity == 2
    "CONNECTIVITY_LOW_MULTIPLIER": 0.95,     # connectivity == 1

    # =========================================================================
    # FALLBACK â€” get_fallback_routes()
    # =========================================================================

    "FALLBACK_NEIGHBOR_LIMIT": 3,
    "FALLBACK_DISTANCE_MULTIPLIER": 1.5,

}
