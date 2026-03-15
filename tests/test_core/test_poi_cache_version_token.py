"""
POI cache version token davranış testi.
"""

import os
import sys

backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

from cache_manager import POICache


def test_poi_cache_isolated_by_version_token():
    cache = POICache(maxsize=10)
    cache.clear()

    cache.put("Kadıköy", "pilavcı", [{"id": 1}], version_token="dict:v1|thr:a|plan:p1")

    # Aynı place/category ama farklı token => cache miss
    miss = cache.get("Kadıköy", "pilavcı", version_token="dict:v2|thr:a|plan:p1")
    assert miss is None

    hit = cache.get("Kadıköy", "pilavcı", version_token="dict:v1|thr:a|plan:p1")
    assert hit == [{"id": 1}]
