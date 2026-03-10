"""
cache_manager.py - LRU Cache Management

Graph ve POI cache'leri için LRU (Least Recently Used) implementasyonu.
Memory leak önler, performansı iyileştirir.
"""

import threading
import time
from collections import OrderedDict
from typing import Any, Optional, Dict, Tuple
import hashlib
import json

from route_config import ROUTE_CONFIG


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
                    self.cache.popitem(last=False)
                    if self.ttl is not None:
                        # Timestamp'ı da sil (eğer varsa)
                        oldest = next(iter(self.cache))
                        if oldest in self.timestamps:
                            del self.timestamps[oldest]

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

    def _make_key(self, place: str, category: str) -> str:
        """Cache key oluşturur."""
        key = f"{place}::{category}"
        # Key'i kısaltmak için hash kullan
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def get(self, place: str, category: str) -> Optional[Any]:
        """POI cache'ten alır."""
        key = self._make_key(place, category)
        return self.cache.get(key)

    def put(self, place: str, category: str, pois: Any) -> None:
        """POI cache'e ekler."""
        key = self._make_key(place, category)
        self.cache.put(key, pois)

    def remove(self, place: str, category: str) -> bool:
        """POI cache'ten siler."""
        key = self._make_key(place, category)
        return self.cache.remove(key)

    def clear(self) -> None:
        """Tüm POI cache'ini temizler."""
        self.cache.clear()

    def stats(self) -> Dict[str, Any]:
        """POI cache istatistikleri."""
        return self.cache.stats()


# Global singleton instances
_graph_cache: Optional[GraphCache] = None
_poi_cache: Optional[POICache] = None
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


def get_all_cache_stats() -> Dict[str, Any]:
    """Tüm cache istatistiklerini döner."""
    return {
        "graph": get_graph_cache().stats(),
        "poi": get_poi_cache().stats()
    }
