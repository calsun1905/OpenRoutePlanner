"""
route_config.py - Rota Motoru Konfigürasyon Sabitleri v3.2

route_engine.py içindeki tüm hardcoded değerlerin merkezi referansı.

Kullanım:
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

    # OSM network tipi:
    # - walk: sadece yurunebilir yollar
    # - all_public: tum kamusal yollar (kopruler dahil, tercih edilen)
    "OSM_NETWORK_TYPE": "all_public",

    # Graf indirme yarıçapı (metre)
    "GRAPH_RADIUS_MIN_M": 500,
    "GRAPH_RADIUS_PADDING_M": 300,
    # Bogaz gecisi gibi deniz asiri rotalarda kopruleri kapsamak icin ust sinir yuksek tutuldu.
    "GRAPH_RADIUS_MAX_M": 20000,
    # API rota hesaplamasinda sirasiyla denenecek yaricap carpanlari.
    "ROUTE_GRAPH_RADIUS_MULTIPLIERS": [1.0, 2.8, 4.2],
    # Uzak noktalarda (iki yaka vb.) once genis grafik denensin.
    "ROUTE_GRAPH_PREF_MULTIPLIER": 2.8,
    "ROUTE_GRAPH_FORCE_WIDE_IF_MAX_DISTANCE_M": 2000,

    # =========================================================================
    # CACHE YÖNETİMİ — LRU Cache Ayarları
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
    "POI_CACHE_SOFT_TTL_DAYS": 14,
    "POI_CACHE_HARD_TTL_DAYS": 30,
    "POI_CACHE_EMPTY_TTL_HOURS": 24,
    "POI_ARCHIVE_MAX_PER_KEY": 5,

    # =========================================================================
    # OVERLAP (ÖRTÜŞME) EŞİKLERİ — dynamic_overlap_threshold()
    # =========================================================================

    "OVERLAP_THRESHOLD_SHORT": 0.90,       # mesafe < 1.0 km
    "OVERLAP_THRESHOLD_MEDIUM": 0.80,      # 1.0 <= mesafe < 3.0 km
    "OVERLAP_THRESHOLD_LONG": 0.75,        # 3.0 <= mesafe < 7.0 km
    "OVERLAP_THRESHOLD_VERY_LONG": 0.70,   # mesafe >= 7.0 km

    # =========================================================================
    # MESAFE SINIRLARI
    # =========================================================================

    "DISTANCE_VERY_SHORT_KM": 1.0,
    "DISTANCE_SHORT_KM": 3.0,
    "DISTANCE_LONG_KM": 7.0,

    # =========================================================================
    # YEN'S K-SHORTEST — get_max_candidates()
    # =========================================================================

    "MAX_CANDIDATES_VERY_SHORT": 50,
    "MAX_CANDIDATES_SHORT": 75,
    "MAX_CANDIDATES_LONG": 100,
    "MAX_CANDIDATES_VERY_LONG": 150,

    # =========================================================================
    # VIA-NODE (ARA NOKTA) — v3.0
    # =========================================================================

    "VIA_NODE_DEFAULT_COUNT": 2,
    "VIA_NODE_BBOX_EXPAND_RATIO": 0.3,
    "VIA_NODE_BBOX_MIN_MARGIN": 0.002,
    "VIA_NODE_MIN_DEGREE": 3,
    "VIA_NODE_MAX_CANDIDATES": 30,
    "VIA_NODE_SELF_OVERLAP_LIMIT": 0.70,
    "VIA_NODE_MAX_DISTANCE_RATIO": 1.5,
    "VIA_NODE_ROUTE_SAMPLE_COUNT": 20,
    "VIA_NODE_ROUTE_SAMPLE_MIN": 8,
    "VIA_NODE_ROUTE_SAMPLE_MAX": 80,
    "VIA_NODE_SAMPLE_PER_KM": 6.0,

    # =========================================================================
    # GÖVDE-ONLY PENALTY — v3.0
    # =========================================================================

    "BODY_EDGES_SKIP_RATIO": 0.10,

    # =========================================================================
    # DİSJOINT PATHS
    # =========================================================================

    "DISJOINT_NUM_PATHS": 2,
    "MAX_REALISTIC_ROUTES": 3,

    # =========================================================================
    # PENALTY-BASED GENERATION
    # =========================================================================

    "PENALTY_FACTOR": 2.0,
    "PENALTY_EXTRA_CANDIDATES": 1,

    # =========================================================================
    # CONNECTİVİTY BAZLI DİNAMİK EŞİK ÇARPANLARI
    # =========================================================================

    "CONNECTIVITY_HIGH_MULTIPLIER": 0.75,
    "CONNECTIVITY_MEDIUM_MULTIPLIER": 0.85,
    "CONNECTIVITY_LOW_MULTIPLIER": 0.95,

    # =========================================================================
    # FALLBACK — get_fallback_routes()
    # =========================================================================

    "FALLBACK_NEIGHBOR_LIMIT": 3,
    "FALLBACK_DISTANCE_MULTIPLIER": 1.5,

    # =========================================================================
    # POI — büyük idari alan (il/ilçe) için parçalı (grid) tarama
    # =========================================================================

    "POI_BOUNDARY_CHUNK_MIN_KM": 12.0,
    "POI_CHUNK_CELL_KM": 4.0,
    "POI_CHUNK_MAX_CELLS": 36,

    # =========================================================================
    # ROUTING WEIGHT & BRIDGE PENALTY
    # Köprü kenarlarına soft penalty uygulayarak kara yolunu tercih ettirir.
    # =========================================================================

    "ROUTING_WEIGHT_KEY": "routing_length",
    "BRIDGE_PENALTY_FACTOR": 1.8,

    # =========================================================================
    # SNAP KALİTE PARAMETRELERİ
    # find_nearest_node_with_distance() içinde kullanılır.
    # =========================================================================

    "SNAP_MAX_NEIGHBOR_CANDIDATES": 4,
    "SNAP_BRIDGE_PENALTY_M": 45.0,
    "SNAP_EDGE_NEAR_THRESHOLD_M": 25.0,
    "SNAP_NODE_EDGE_GAP_MAX_M": 110.0,
    # Kullanici noktasi belirgin sekilde bir yakadaysa, karsi yakadaki node'lara
    # snap etmeyi guclu sekilde caydirir.
    "SNAP_CROSS_SHORE_PENALTY_M": 2000.0,
    # API kabul limiti: bundan daha kotu snap varsa daha genis grafikle tekrar dene.
    "ROUTE_SNAP_MAX_DISTANCE_M": 900.0,
    "ALT_ROUTE_DEDUP_EPSILON_MIN_DEG": 1e-6,
    "ALT_ROUTE_DEDUP_EPSILON_MAX_DEG": 2.5e-5,

    # =========================================================================
    # POINT GRAPH CACHE — disk temizliği
    # =========================================================================

    "GRAPH_POINT_CACHE_MAX_FILES": 20,
    "POINT_GRAPH_MEMORY_CACHE_MAXSIZE": 24,
    "POINT_GRAPH_MEMORY_CACHE_TTL_SEC": 900,
    "ROUTE_RESPONSE_CACHE_ENABLED": True,
    "ROUTE_RESPONSE_CACHE_MAX_ITEMS": 500,
    "ROUTE_RESPONSE_CACHE_TTL_SEC": 180,
    "ROUTE_RESPONSE_CACHE_CONFIG_VERSION": "v1",
    "CACHE_POLICY_MIN_SAMPLES": 20,
    "CACHE_POLICY_MIN_HIT_RATE": 0.20,
    "CACHE_POLICY_UTILIZATION_WARN": 0.90,
    "NLP_MAX_CANDIDATE_SPANS": 24,
    "NLP_QUEUE_TIMEOUT_SEC": 20,
    "MULTIMODAL_QUEUE_TIMEOUT_SEC": 25,

    # =========================================================================
    # MULTIMODAL — SU GEÇİŞİ KORUMASI
    # =========================================================================

    "MULTIMODAL_ENFORCE_WATER_CROSSING_GUARDS": True,
    "MULTIMODAL_ALLOWED_MODES_MAX": 4,
    "MULTIMODAL_MAX_TRANSIT_OPTIONS": 8,
    "MULTIMODAL_COMPARE_MAX_CONCURRENCY": 2,
    "MULTIMODAL_COMPARE_CACHE_ENABLED": True,
    "MULTIMODAL_COMPARE_CACHE_MAX_ITEMS": 220,
    "MULTIMODAL_COMPARE_CACHE_TTL_SEC": 300,
    "MULTIMODAL_TRANSIT_LOOKUP_CACHE_MAX_ITEMS": 2500,
    "MULTIMODAL_TRANSIT_LOOKUP_CACHE_TTL_SEC": 900,
    "MULTIMODAL_MAX_WALK_TO_STOP_M": 800,
    "MULTIMODAL_MAX_WALK_TO_STOP_MEDIUM_M": 1000,
    "MULTIMODAL_MAX_WALK_TO_STOP_LONG_M": 1200,
    "MULTIMODAL_WALK_EXPAND_MEDIUM_TRIGGER_M": 20000,
    "MULTIMODAL_WALK_EXPAND_LONG_TRIGGER_M": 50000,
    "MULTIMODAL_MAX_RAIL_TRANSFER_WALK_M": 1500,

}
