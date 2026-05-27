"""
Cache policy evaluation tests.
"""

import os
import sys


backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

from cache_manager import evaluate_cache_policy


def test_evaluate_cache_policy_warns_for_low_hit_rate_and_high_utilization():
    stats = {
        "graph": {
            "memory_cache": {
                "size": 9,
                "maxsize": 10,
                "hits": 2,
                "misses": 48,
            }
        },
        "poi": {
            "size": 48,
            "maxsize": 50,
            "hits": 5,
            "misses": 30,
        },
        "multimodal_compare": {
            "enabled": True,
            "size": 200,
            "max_items": 220,
            "hits": 1,
            "misses": 30,
        },
    }

    policy = evaluate_cache_policy(stats)
    assert policy["status"] == "warn"
    assert policy["warnings"]


def test_evaluate_cache_policy_ok_for_healthy_caches():
    stats = {
        "graph": {
            "memory_cache": {
                "size": 4,
                "maxsize": 10,
                "hits": 80,
                "misses": 20,
            }
        },
        "poi": {
            "size": 10,
            "maxsize": 50,
            "hits": 40,
            "misses": 10,
        },
        "multimodal_compare": {
            "enabled": False,
            "size": 0,
            "max_items": 220,
            "hits": 0,
            "misses": 0,
        },
    }

    policy = evaluate_cache_policy(stats)
    assert policy["status"] == "ok"
    assert policy["warnings"] == []
