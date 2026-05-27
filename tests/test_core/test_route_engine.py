"""
Route Engine Unit Tests

Basic unit tests for route engine helper behavior and regressions.
"""

import os
import sys

import networkx as nx
import pytest


backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)


class TestOverlapThresholds:
    def test_overlap_very_short_distance(self):
        from route_engine import get_overlap_threshold

        assert get_overlap_threshold(0.5) == 0.90

    def test_overlap_short_distance(self):
        from route_engine import get_overlap_threshold

        assert get_overlap_threshold(2.0) == 0.80

    def test_overlap_medium_distance(self):
        from route_engine import get_overlap_threshold

        assert get_overlap_threshold(5.0) == 0.75

    def test_overlap_long_distance(self):
        from route_engine import get_overlap_threshold

        assert get_overlap_threshold(10.0) == 0.70


class TestMaxCandidates:
    def test_max_candidates_very_short(self):
        from route_engine import get_max_candidates

        assert get_max_candidates(0.5) == 50

    def test_max_candidates_short(self):
        from route_engine import get_max_candidates

        assert get_max_candidates(2.0) == 75

    def test_max_candidates_medium(self):
        from route_engine import get_max_candidates

        assert get_max_candidates(5.0) == 100

    def test_max_candidates_long(self):
        from route_engine import get_max_candidates

        assert get_max_candidates(10.0) == 150


class TestConfigIntegration:
    def test_walk_speed_from_config(self):
        from route_engine import ROUTE_CONFIG

        assert "WALK_SPEED_KMH" in ROUTE_CONFIG
        assert ROUTE_CONFIG["WALK_SPEED_KMH"] == 5.0

    def test_overlap_thresholds_in_config(self):
        from route_engine import ROUTE_CONFIG

        assert "OVERLAP_THRESHOLD_SHORT" in ROUTE_CONFIG
        assert "OVERLAP_THRESHOLD_MEDIUM" in ROUTE_CONFIG
        assert "OVERLAP_THRESHOLD_LONG" in ROUTE_CONFIG
        assert "OVERLAP_THRESHOLD_VERY_LONG" in ROUTE_CONFIG

    def test_max_candidates_in_config(self):
        from route_engine import ROUTE_CONFIG

        assert "MAX_CANDIDATES_VERY_SHORT" in ROUTE_CONFIG
        assert "MAX_CANDIDATES_SHORT" in ROUTE_CONFIG
        assert "MAX_CANDIDATES_LONG" in ROUTE_CONFIG
        assert "MAX_CANDIDATES_VERY_LONG" in ROUTE_CONFIG

    def test_penalty_factor_in_config(self):
        from route_engine import ROUTE_CONFIG

        assert "PENALTY_FACTOR" in ROUTE_CONFIG
        assert ROUTE_CONFIG["PENALTY_FACTOR"] == 2.0


class TestEdgeOverlap:
    def test_no_overlap(self):
        from route_engine import count_edge_overlap

        edges1 = [(1, 2), (2, 3), (3, 4)]
        edges2 = [(5, 6), (6, 7), (7, 8)]
        assert count_edge_overlap(edges1, edges2) == 0.0

    def test_full_overlap(self):
        from route_engine import count_edge_overlap

        edges1 = [(1, 2), (2, 3), (3, 4)]
        edges2 = [(1, 2), (2, 3), (3, 4)]
        assert count_edge_overlap(edges1, edges2) == 1.0

    def test_partial_overlap(self):
        from route_engine import count_edge_overlap

        edges1 = [(1, 2), (2, 3), (3, 4), (4, 5)]
        edges2 = [(2, 3), (3, 4)]
        overlap = count_edge_overlap(edges1, edges2)
        assert overlap == 1.0

    def test_direction_sensitive_overlap(self):
        from route_engine import count_edge_overlap

        edges1 = [(1, 2), (2, 3)]
        edges2 = [(2, 1), (2, 3)]
        assert count_edge_overlap(edges1, edges2) == 0.5


def test_solve_tsp_raises_for_unreachable_waypoints(monkeypatch):
    import route_engine_impl as route_impl

    G = nx.DiGraph()
    G.add_node(1, y=0.0, x=0.0)
    G.add_node(2, y=0.0, x=1.0)
    G.add_node(3, y=10.0, x=10.0)
    G.add_edge(1, 2, routing_length=1.0)
    G.add_edge(2, 1, routing_length=1.0)

    points = [(0.0, 0.0), (0.0, 1.0), (10.0, 10.0)]
    node_map = {(0.0, 0.0): 1, (0.0, 1.0): 2, (10.0, 10.0): 3}
    monkeypatch.setattr(route_impl, "find_nearest_node", lambda _g, lat, lon: node_map[(lat, lon)])

    with pytest.raises(route_impl.UnreachableWaypointsError) as exc:
        route_impl.solve_tsp(G, points)

    assert exc.value.to_payload()["details"]["unreachable_pairs"] == [[0, 2], [1, 2]]


def test_solve_tsp_preserves_duplicate_node_indices(monkeypatch):
    import route_engine_impl as route_impl

    G = nx.DiGraph()
    G.add_node(1, y=0.0, x=0.0)
    G.add_node(2, y=0.0, x=1.0)
    G.add_edge(1, 2, routing_length=1.0)
    G.add_edge(2, 1, routing_length=1.0)

    points = [(0.0, 0.0), (0.0, 0.0), (0.0, 1.0)]
    node_map = {(0.0, 0.0): 1, (0.0, 1.0): 2}
    monkeypatch.setattr(route_impl, "find_nearest_node", lambda _g, lat, lon: node_map[(lat, lon)])

    ordered = route_impl.solve_tsp(G, points)
    assert sorted(ordered) == [0, 1, 2]
    assert ordered.count(0) == 1
    assert ordered.count(1) == 1
    assert ordered.index(0) + 1 == ordered.index(1)


def test_find_via_node_routes_handles_missing_node_coordinates():
    import route_engine_impl as route_impl

    G = nx.MultiDiGraph()
    G.add_node(1, y=41.0, x=29.0)
    G.add_node(2)  # missing x/y on purpose
    G.add_edge(1, 2, key=0, routing_length=1.0, length=1.0)
    G.add_edge(2, 1, key=0, routing_length=1.0, length=1.0)

    routes = route_impl.find_via_node_routes(
        G=G,
        origin_node=1,
        dest_node=2,
        main_route_nodes=[1, 2],
    )
    assert routes == []


def test_dynamic_via_sample_count_bounds():
    from route_engine import ROUTE_CONFIG, calculate_via_route_sample_count

    min_samples = int(ROUTE_CONFIG["VIA_NODE_ROUTE_SAMPLE_MIN"])
    max_samples = int(ROUTE_CONFIG["VIA_NODE_ROUTE_SAMPLE_MAX"])

    short_value = calculate_via_route_sample_count(main_km=0.2, coord_count=200)
    long_value = calculate_via_route_sample_count(main_km=50.0, coord_count=200)

    assert short_value >= min_samples
    assert long_value <= max_samples
    assert long_value >= short_value


def test_multidigraph_penalty_respects_edge_key():
    from route_engine import apply_penalty_to_graph

    G = nx.MultiDiGraph()
    G.add_edge(1, 2, key=0, routing_length=10.0, length=10.0)
    G.add_edge(1, 2, key=1, routing_length=20.0, length=20.0)

    penalized = apply_penalty_to_graph(G, used_edges=[(1, 2, 0)], penalty_factor=3.0)
    assert penalized[1][2][0]["penalty_length"] == 30.0
    assert penalized[1][2][1]["penalty_length"] == 20.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
