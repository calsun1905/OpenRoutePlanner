import networkx as nx
import os
import time

import graph_manager
import route_engine_impl as route_engine


def _simple_graph():
    G = nx.MultiDiGraph()
    G.add_node(1, x=29.0, y=41.0)
    G.add_node(2, x=29.1, y=41.1)
    G.add_node(3, x=29.2, y=41.2)
    G.add_edge(1, 2, key=0, length=100.0)
    return G


def test_build_alternative_routes_rejects_partial_route(monkeypatch):
    G = _simple_graph()
    points = [(41.0, 29.0), (41.1, 29.1), (41.2, 29.2)]

    monkeypatch.setattr(route_engine, "find_nearest_node", lambda G_, lat, lon: {29.0: 1, 29.1: 2, 29.2: 3}[round(lon, 1)])

    def fake_alternatives(G_, origin, dest, num_routes=3):
        if (origin, dest) == (1, 2):
            return [{"nodes": [1, 2]}]
        return []

    monkeypatch.setattr(route_engine, "find_alternative_routes", fake_alternatives)
    monkeypatch.setattr(route_engine, "shortest_path", lambda G_, origin, dest: [])

    assert route_engine.build_alternative_routes(G, points, route_index=0) == []


def test_batch_routes_rejects_unreachable_segment(monkeypatch):
    G = _simple_graph()
    points = [(41.0, 29.0), (41.1, 29.1), (41.2, 29.2)]

    monkeypatch.setattr(route_engine, "find_nearest_node", lambda G_, lat, lon: {29.0: 1, 29.1: 2, 29.2: 3}[round(lon, 1)])

    def fake_alternatives(G_, origin, dest, num_routes=3):
        if (origin, dest) == (1, 2):
            return [{"nodes": [1, 2], "distance_km": 0.1, "duration_minutes": 1}]
        return []

    monkeypatch.setattr(route_engine, "find_alternative_routes", fake_alternatives)

    assert route_engine.build_all_alternative_routes_batch(G, points) == []


def test_expanded_graph_radius_really_grows_for_bridge_detours(monkeypatch, tmp_path):
    captured = {}

    def fake_graph_from_point(center, dist, network_type="walk", retain_all=False):
        captured["dist"] = dist
        captured["retain_all"] = retain_all
        G = nx.MultiDiGraph()
        G.add_node(1, x=center[1], y=center[0])
        G.add_node(2, x=center[1] + 0.001, y=center[0] + 0.001)
        G.add_edge(1, 2, key=0, length=100.0)
        return G

    monkeypatch.setattr(graph_manager, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(graph_manager.ox, "graph_from_point", fake_graph_from_point)
    monkeypatch.setattr(graph_manager.ox, "save_graphml", lambda *args, **kwargs: None)

    points = [(41.0, 29.0), (41.09, 29.0)]
    graph_manager.get_graph_for_points(points, radius_multiplier=1.8)

    assert captured["retain_all"] is True
    assert captured["dist"] > 8000


def test_snap_distance_uses_edge_geometry_not_only_edge_endpoints(monkeypatch):
    class FakeGeometry:
        coords = [(29.0, 41.0), (29.02, 41.0)]

    G = nx.MultiDiGraph()
    G.add_node(1, x=29.0, y=41.0)
    G.add_node(2, x=29.02, y=41.0)
    G.add_edge(1, 2, key=0, length=1800.0, geometry=FakeGeometry())

    monkeypatch.setattr(graph_manager.ox, "nearest_edges", lambda *args, **kwargs: (1, 2, 0))

    _, snap_m = graph_manager.find_nearest_node_with_distance(G, 41.0, 29.01)

    assert snap_m < 5


def test_fallback_routes_do_not_fabricate_reverse_destination_edge():
    G = nx.MultiDiGraph()
    G.add_node(1, x=29.0, y=41.0)
    G.add_node(2, x=29.1, y=41.0)
    G.add_node(3, x=29.2, y=41.0)
    G.add_node(4, x=29.3, y=41.0)

    G.add_edge(1, 2, key=0, length=100.0)
    G.add_edge(2, 4, key=0, length=100.0)
    G.add_edge(4, 3, key=0, length=100.0)
    G.add_edge(1, 3, key=0, length=500.0)
    # 3 -> 4 exists, but 4 -> 3 is the only valid connector into destination.
    # Older fallback logic used successors(3), then appended 3 directly and
    # could create an invalid 4 -> 3 leg if the direction did not exist.
    G.remove_edge(4, 3, key=0)
    G.add_edge(3, 4, key=0, length=100.0)

    routes = route_engine.get_fallback_routes(G, 1, 3)

    assert routes
    for route in routes:
        assert route_engine._is_valid_path(G, route["nodes"])


def test_point_graph_cache_is_pruned_to_configured_limit(monkeypatch, tmp_path):
    monkeypatch.setattr(graph_manager, "DATA_DIR", str(tmp_path))
    monkeypatch.setitem(graph_manager.ROUTE_CONFIG, "GRAPH_POINT_CACHE_MAX_FILES", 3)

    base_ts = int(time.time())
    for idx in range(5):
        fpath = tmp_path / f"point_fake_{idx}.graphml"
        fpath.write_text("x", encoding="utf-8")
        os.utime(fpath, (base_ts + idx, base_ts + idx))

    graph_manager._prune_point_graph_cache()

    survivors = sorted(p.name for p in tmp_path.glob("point_*.graphml"))
    assert len(survivors) == 3
    assert "point_fake_4.graphml" in survivors
    assert "point_fake_3.graphml" in survivors
