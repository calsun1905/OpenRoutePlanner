"""
cache_manager.py - LRU Cache Management

Graph ve POI cache'leri için LRU (Least Recently Used) implementasyonu.
Memory leak önler, performansı iyileştirir.
"""

import threading
import time
import copy
import os
from collections import OrderedDict
from typing import Any, Optional, Dict, Tuple, List
import hashlib
import json

from route_config import ROUTE_CONFIG


def _env_flag_any(names: List[str], default: bool) -> bool:
    for name in names:
        raw = os.getenv(name)
        if raw is None:
            continue
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _env_int_any(names: List[str], default: int) -> int:
    for name in names:
        raw = os.getenv(name)
        if raw is None:
            continue
        try:
            return int(raw.strip())
        except (TypeError, ValueError):
            continue
    return default


class LRUCache:
    """
    Thread-safe LRU Cache implementasyonu.

    Özellikler:
    - Maksimum boyut sınırı
    - En eski kullanılmayan öğeleri otomatik siler
    - Thread-safe (multi-threaded Flask için)
    - Hit/miss istatistikleri

    Args:
        maxsize: Maksimum cache boyutu (varsayılan: 10)
        ttl: Time-to-live saniye cinsinden (varsayılan: None - sınırsız)
    """

    def __init__(self, maxsize: int = 10, ttl: Optional[int] = None):
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: Dict[str, float] = {}
        self.lock = threading.RLock()

        # İstatistikler
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Cache'ten değer alır. Hit/miss takibi yapar."""
        with self.lock:
            # Anahtar var mı kontrol et
            if key not in self.cache:
                self.misses += 1
                return None

            # TTL kontrolü
            if self.ttl is not None:
                age = time.time() - self.timestamps[key]
                if age > self.ttl:
                    # Süresi dolmuş, sil
                    del self.cache[key]
                    del self.timestamps[key]
                    self.misses += 1
                    return None

            # LRU: En son kullanılanı başa taşı
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]

    def put(self, key: str, value: Any) -> None:
        """Cache'e değer ekler. Boyut sınırını aşarsa en eskisini siler."""
        with self.lock:
            # Anahtar varsa güncelle ve başa taşı
            if key in self.cache:
                self.cache.move_to_end(key)
            else:
                # Yeni anahtar - boyut kontrolü
                if len(self.cache) >= self.maxsize:
                    # En eski öğeyi sil (ilk öğe)
                    oldest_key, _ = self.cache.popitem(last=False)
                    if self.ttl is not None:
                        # Timestamp'i da sil
                        self.timestamps.pop(oldest_key, None)

            # Değeri ekle
            self.cache[key] = value
            if self.ttl is not None:
                self.timestamps[key] = time.time()

    def remove(self, key: str) -> bool:
        """Cache'ten değer siler."""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                if self.ttl is not None and key in self.timestamps:
                    del self.timestamps[key]
                return True
            return False

    def clear(self) -> None:
        """Tüm cache'i temizler."""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()
            self.hits = 0
            self.misses = 0

    def size(self) -> int:
        """Mevcut cache boyutu."""
        return len(self.cache)

    def stats(self) -> Dict[str, Any]:
        """Cache istatistikleri döner."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        return {
            "size": len(self.cache),
            "maxsize": self.maxsize,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1%}",
            "ttl": self.ttl
        }


class GraphCache:
    """
    OSM Graph cache yönetimi.

    Features:
    - LRU ile memory management
    - Disk cache entegrasyonu (graphml dosyaları)
    - Preloaded graphs için özel destek
    """

    def __init__(self, maxsize: int = 10):
        # Route config'den değerleri al
        self.maxsize = ROUTE_CONFIG.get("GRAPH_CACHE_MAXSIZE", maxsize)
        self.ttl = ROUTE_CONFIG.get("GRAPH_CACHE_TTL", 3600)  # 1 saat varsayılan

        # Ana cache
        self.memory_cache = LRUCache(maxsize=self.maxsize, ttl=self.ttl)

        # Preloaded graphs (üst düzey cache - asla silinmez)
        self.preloaded: Dict[str, Any] = {}

        # Cache dizini
        self.cache_dir = ROUTE_CONFIG.get("GRAPH_CACHE_DIR", "backend/data")

    def get(self, place_name: str) -> Optional[Any]:
        """Graph cache'ten alır. Memory → Preloaded → Disk sırası."""
        # 1. Preloaded kontrol (en hızlı)
        if place_name in self.preloaded:
            return self.preloaded[place_name]

        # 2. Memory cache kontrol
        graph = self.memory_cache.get(place_name)
        if graph is not None:
            return graph

        # 3. Disk cache kontrol (daha yavaş)
        # Bu kısım graph_manager.py'de handle ediliyor
        return None

    def put(self, place_name: str, graph: Any, preloaded: bool = False) -> None:
        """Graph cache'e ekler."""
        if preloaded:
            # Preloaded graph'ler silinmez
            self.preloaded[place_name] = graph
        else:
            # Normal cache - LRU uygulanır
            self.memory_cache.put(place_name, graph)

    def preload(self, graphs: Dict[str, Any]) -> None:
        """Popüler bölgeleri önceden yükler."""
        self.preloaded.update(graphs)

    def remove(self, place_name: str) -> bool:
        """Graph'u cache'ten siler."""
        removed = False
        if place_name in self.preloaded:
            del self.preloaded[place_name]
            removed = True
        removed |= self.memory_cache.remove(place_name)
        return removed

    def clear(self) -> None:
        """Tüm cache'i temizler (preloaded hariç)."""
        self.memory_cache.clear()

    def clear_all(self) -> None:
        """Her şeyi temizler (preloaded dahil)."""
        self.memory_cache.clear()
        self.preloaded.clear()

    def stats(self) -> Dict[str, Any]:
        """Cache istatistikleri."""
        return {
            "memory_cache": self.memory_cache.stats(),
            "preloaded_count": len(self.preloaded),
            "total_cached": self.memory_cache.size() + len(self.preloaded)
        }


class POICache:
    """
    POI (Points of Interest) cache yönetimi.

    Features:
    - LRU ile memory management
    - Category-based cache keys
    - Spatial-aware caching (opsiyonel)
    """

    def __init__(self, maxsize: int = 50):
        self.maxsize = ROUTE_CONFIG.get("POI_CACHE_MAXSIZE", maxsize)
        self.ttl = ROUTE_CONFIG.get("POI_CACHE_TTL", 1800)  # 30 dakika
        self.cache = LRUCache(maxsize=self.maxsize, ttl=self.ttl)

    def _make_key(self, place: str, category: str, version_token: Optional[str] = None) -> str:
        """Cache key oluşturur (opsiyonel version pin ile)."""
        token = (version_token or "v:default").strip()
        key = f"{place}::{category}::{token}"
        # Key'i kısaltmak için hash kullan
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def get(self, place: str, category: str, version_token: Optional[str] = None) -> Optional[Any]:
        """POI cache'ten alır."""
        key = self._make_key(place, category, version_token=version_token)
        return self.cache.get(key)

    def put(self, place: str, category: str, pois: Any, version_token: Optional[str] = None) -> None:
        """POI cache'e ekler."""
        key = self._make_key(place, category, version_token=version_token)
        self.cache.put(key, pois)

    def remove(self, place: str, category: str, version_token: Optional[str] = None) -> bool:
        """POI cache'ten siler."""
        key = self._make_key(place, category, version_token=version_token)
        return self.cache.remove(key)

    def clear(self) -> None:
        """Tüm POI cache'ini temizler."""
        self.cache.clear()

    def stats(self) -> Dict[str, Any]:
        """POI cache istatistikleri."""
        return self.cache.stats()


class RouteResponseCache:
    """
    /api/get-route ve benzeri endpoint cevaplari icin ortak TTL+LRU cache.
    """

    def __init__(self):
        cfg_enabled = bool(ROUTE_CONFIG.get("ROUTE_RESPONSE_CACHE_ENABLED", True))
        cfg_max_items = int(ROUTE_CONFIG.get("ROUTE_RESPONSE_CACHE_MAX_ITEMS", 500))
        cfg_ttl = int(ROUTE_CONFIG.get("ROUTE_RESPONSE_CACHE_TTL_SEC", 180))

        self.enabled = _env_flag_any(
            ["ROUTE_RESPONSE_CACHE_ENABLED", "ORP_ROUTE_RESPONSE_CACHE_ENABLED"],
            cfg_enabled,
        )
        self.max_items = max(
            10,
            _env_int_any(
                ["ROUTE_RESPONSE_CACHE_MAX_ITEMS", "ORP_ROUTE_RESPONSE_CACHE_MAX_ITEMS"],
                cfg_max_items,
            ),
        )
        self.ttl_sec = max(
            1,
            _env_int_any(
                ["ROUTE_RESPONSE_CACHE_TTL_SEC", "ORP_ROUTE_RESPONSE_CACHE_TTL_SEC"],
                cfg_ttl,
            ),
        )
        self.cache = LRUCache(maxsize=self.max_items, ttl=self.ttl_sec)

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
        value = self.cache.get(key)
        if value is None:
            return None
        return copy.deepcopy(value)

    def put(self, key: str, value: Any) -> None:
        if not self.enabled:
            return
        self.cache.put(key, copy.deepcopy(value))

    def clear(self) -> None:
        self.cache.clear()

    def stats(self) -> Dict[str, Any]:
        base = self.cache.stats()
        return {
            "enabled": bool(self.enabled),
            "size": int(base.get("size", 0)),
            "max_items": int(self.max_items),
            "maxsize": int(self.max_items),
            "hits": int(base.get("hits", 0)),
            "misses": int(base.get("misses", 0)),
            "hit_rate": base.get("hit_rate", "0.0%"),
            "ttl_sec": int(self.ttl_sec),
        }


class PointGraphMemoryCache:
    """
    graph_manager.get_graph_for_points icin disk ustu RAM katmani.
    """

    def __init__(self):
        cfg_maxsize = int(ROUTE_CONFIG.get("POINT_GRAPH_MEMORY_CACHE_MAXSIZE", 24))
        cfg_ttl = int(ROUTE_CONFIG.get("POINT_GRAPH_MEMORY_CACHE_TTL_SEC", 900))
        self.maxsize = max(
            1,
            _env_int_any(
                ["POINT_GRAPH_MEMORY_CACHE_MAXSIZE", "ORP_POINT_GRAPH_MEMORY_CACHE_MAXSIZE"],
                cfg_maxsize,
            ),
        )
        self.ttl_sec = max(
            1,
            _env_int_any(
                ["POINT_GRAPH_MEMORY_CACHE_TTL_SEC", "ORP_POINT_GRAPH_MEMORY_CACHE_TTL_SEC"],
                cfg_ttl,
            ),
        )
        self.cache = LRUCache(maxsize=self.maxsize, ttl=self.ttl_sec)

    def get(self, key: str) -> Optional[Any]:
        return self.cache.get(key)

    def put(self, key: str, value: Any) -> None:
        self.cache.put(key, value)

    def clear(self) -> None:
        self.cache.clear()

    def stats(self) -> Dict[str, Any]:
        base = self.cache.stats()
        return {
            "size": int(base.get("size", 0)),
            "maxsize": int(self.maxsize),
            "hits": int(base.get("hits", 0)),
            "misses": int(base.get("misses", 0)),
            "hit_rate": base.get("hit_rate", "0.0%"),
            "ttl_sec": int(self.ttl_sec),
        }


# Global singleton instances
_graph_cache: Optional[GraphCache] = None
_poi_cache: Optional[POICache] = None
_route_response_cache: Optional[RouteResponseCache] = None
_point_graph_memory_cache: Optional[PointGraphMemoryCache] = None
_cache_lock = threading.Lock()


def get_graph_cache() -> GraphCache:
    """Global graph cache singleton'ı döner."""
    global _graph_cache
    if _graph_cache is None:
        with _cache_lock:
            if _graph_cache is None:
                _graph_cache = GraphCache(maxsize=10)
    return _graph_cache


def get_poi_cache() -> POICache:
    """Global POI cache singleton'ı döner."""
    global _poi_cache
    if _poi_cache is None:
        with _cache_lock:
            if _poi_cache is None:
                _poi_cache = POICache(maxsize=50)
    return _poi_cache


def get_route_response_cache() -> RouteResponseCache:
    """Global route response cache singleton."""
    global _route_response_cache
    if _route_response_cache is None:
        with _cache_lock:
            if _route_response_cache is None:
                _route_response_cache = RouteResponseCache()
    return _route_response_cache


def get_point_graph_memory_cache() -> PointGraphMemoryCache:
    """Global point-graph memory cache singleton."""
    global _point_graph_memory_cache
    if _point_graph_memory_cache is None:
        with _cache_lock:
            if _point_graph_memory_cache is None:
                _point_graph_memory_cache = PointGraphMemoryCache()
    return _point_graph_memory_cache


def get_all_cache_stats() -> Dict[str, Any]:
    """Tüm cache istatistiklerini döner."""
    return {
        "graph": get_graph_cache().stats(),
        "poi": get_poi_cache().stats(),
        "route_response_cache": get_route_response_cache().stats(),
        "point_graph_memory_cache": get_point_graph_memory_cache().stats(),
    }


def evaluate_cache_policy(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cache istatistiklerinden basit policy/saglik degerlendirmesi uretir.
    """
    min_samples = int(ROUTE_CONFIG.get("CACHE_POLICY_MIN_SAMPLES", 20))
    min_hit_rate = float(ROUTE_CONFIG.get("CACHE_POLICY_MIN_HIT_RATE", 0.20))
    util_warn = float(ROUTE_CONFIG.get("CACHE_POLICY_UTILIZATION_WARN", 0.90))

    warnings: List[str] = []

    def _evaluate_bucket(name: str, bucket: Dict[str, Any]) -> None:
        if not isinstance(bucket, dict):
            return
        size = int(bucket.get("size", 0) or 0)
        maxsize = int(bucket.get("maxsize", bucket.get("max_items", 0)) or 0)
        hits = int(bucket.get("hits", 0) or 0)
        misses = int(bucket.get("misses", 0) or 0)
        total = hits + misses
        hit_rate = (hits / total) if total > 0 else 0.0

        if maxsize > 0:
            utilization = size / maxsize
            if utilization >= util_warn:
                warnings.append(
                    f"{name} cache utilization high ({size}/{maxsize}, {utilization:.0%})"
                )

        if total >= min_samples and hit_rate < min_hit_rate:
            warnings.append(
                f"{name} cache hit rate low ({hit_rate:.0%}, samples={total})"
            )

    graph_stats = (stats.get("graph") or {}).get("memory_cache", {})
    poi_stats = stats.get("poi") or {}
    multimodal_stats = stats.get("multimodal_compare") or {}
    route_response_stats = stats.get("route_response_cache") or {}
    point_graph_stats = stats.get("point_graph_memory_cache") or {}

    _evaluate_bucket("graph.memory", graph_stats if isinstance(graph_stats, dict) else {})
    _evaluate_bucket("poi", poi_stats if isinstance(poi_stats, dict) else {})
    _evaluate_bucket("multimodal.compare", multimodal_stats if isinstance(multimodal_stats, dict) else {})
    _evaluate_bucket("route.response", route_response_stats if isinstance(route_response_stats, dict) else {})
    _evaluate_bucket("graph.point_memory", point_graph_stats if isinstance(point_graph_stats, dict) else {})

    return {
        "status": "warn" if warnings else "ok",
        "warnings": warnings,
        "thresholds": {
            "min_samples": min_samples,
            "min_hit_rate": min_hit_rate,
            "utilization_warn": util_warn,
        },
    }
