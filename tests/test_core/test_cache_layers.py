import os
import sys
import time


backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

from cache_manager import RouteResponseCache, PointGraphMemoryCache


def test_route_response_cache_ttl_expiry(monkeypatch):
    monkeypatch.setenv("ROUTE_RESPONSE_CACHE_ENABLED", "1")
    monkeypatch.setenv("ROUTE_RESPONSE_CACHE_MAX_ITEMS", "16")
    monkeypatch.setenv("ROUTE_RESPONSE_CACHE_TTL_SEC", "60")

    cache = RouteResponseCache()
    cache.put("route:key", {"ok": True})
    assert cache.get("route:key") == {"ok": True}

    # TTL asimini simule et
    cache.cache.timestamps["route:key"] = time.time() - 120
    assert cache.get("route:key") is None


def test_point_graph_memory_cache_hit_miss_stats():
    cache = PointGraphMemoryCache()
    cache.clear()

    assert cache.get("point:A") is None
    cache.put("point:A", {"nodes": 10})
    assert cache.get("point:A") == {"nodes": 10}

    stats = cache.stats()
    assert stats["hits"] >= 1
    assert stats["misses"] >= 1
