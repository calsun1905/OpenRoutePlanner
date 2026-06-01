# Compatibility wrapper for route_engine
# Keeps original implementation in route_engine_impl.py and provides
# small compatibility shims expected by tests.

# Import all names from the implementation so existing imports still work
import route_engine_impl as _impl
from route_engine_impl import *  # noqa: F401,F403

# Compatibility alias: tests expect get_overlap_threshold(name)
# Implementation uses dynamic_overlap_threshold; expose a compatible name.

def get_overlap_threshold(distance_km: float) -> float:
    """Compatibility wrapper for dynamic_overlap_threshold.

    Args:
        distance_km: rota mesafesi (km)

    Returns:
        float: overlap threshold (0-1 arası)
    """
    return _impl.dynamic_overlap_threshold(distance_km)


def count_edge_overlap(edges1, edges2):
    """Compatibility wrapper that delegates to production implementation."""
    return _impl.count_edge_overlap(edges1, edges2)
