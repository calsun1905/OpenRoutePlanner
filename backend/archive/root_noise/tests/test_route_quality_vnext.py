import networkx as nx

import graph_manager
import route_engine_impl as route_engine


def _add_edge_bidir(G, u, v, **attrs):
    G.add_edge(u, v, key=0, **attrs)
    G.add_edge(v, u, key=0, **attrs)


def test_routing_weight_applies_bridge_penalty(monkeypatch):
    monkeypatch.setitem(graph_manager.ROUTE_CONFIG, "ROUTING_WEIGHT_KEY", "routing_length")
    monkeypatch.setitem(graph_manager.ROUTE_CONFIG, "BRIDGE_PENALTY_FACTOR", 1.8)

    G = nx.MultiDiGraph()
    G.add_node(1, x=29.0, y=41.0)
    G.add_node(2, x=29.001, y=41.0)
    G.add_node(3, x=29.002, y=41.0)
    _add_edge_bidir(G, 1, 2, length=100.0, bridge="yes")
    _add_edge_bidir(G, 2, 3, length=100.0)

    G = graph_manager._apply_routing_edge_weights(G)

    assert G.get_edge_data(1, 2)[0]["routing_length"] == 180.0
    assert G.get_edge_data(2, 3)[0]["routing_length"] == 100.0


def test_shortest_path_prefers_non_bridge_when_soft_penalty_enabled(monkeypatch):
    monkeypatch.setitem(graph_manager.ROUTE_CONFIG, "ROUTING_WEIGHT_KEY", "routing_length")
    monkeypatch.setitem(graph_manager.ROUTE_CONFIG, "BRIDGE_PENALTY_FACTOR", 1.8)
    monkeypatch.setitem(route_engine.ROUTE_CONFIG, "ROUTING_WEIGHT_KEY", "routing_length")

    G = nx.MultiDiGraph()
    for node_id, x in ((1, 29.0), (2, 29.001), (3, 29.002), (4, 29.003)):
        G.add_node(node_id, x=x, y=41.0)

    # Bridge path: physically shorter (200m) but weighted longer (360m).
    _add_edge_bidir(G, 1, 2, length=100.0, bridge="yes")
    _add_edge_bidir(G, 2, 4, length=100.0, bridge="yes")

    # Land path: physically longer (300m) but no bridge penalty.
    _add_edge_bidir(G, 1, 3, length=150.0)
    _add_edge_bidir(G, 3, 4, length=150.0)

    graph_manager._apply_routing_edge_weights(G)
    nodes = route_engine.shortest_path(G, 1, 4)

    assert nodes == [1, 3, 4]


def test_penalty_generation_uses_routing_weight_as_base(monkeypatch):
    monkeypatch.setitem(route_engine.ROUTE_CONFIG, "ROUTING_WEIGHT_KEY", "routing_length")

    G = nx.MultiDiGraph()
    G.add_node(1, x=29.0, y=41.0)
    G.add_node(2, x=29.001, y=41.0)
    G.add_edge(1, 2, key=0, length=100.0, routing_length=180.0)

    penalized = route_engine.apply_penalty_to_graph(G, used_edges=[(1, 2, 0)], penalty_factor=2.0)
    assert penalized.get_edge_data(1, 2)[0]["penalty_length"] == 360.0


def test_snap_prefers_non_bridge_neighbor_candidate(monkeypatch):
    monkeypatch.setitem(graph_manager.ROUTE_CONFIG, "SNAP_MAX_NEIGHBOR_CANDIDATES", 4)
    monkeypatch.setitem(graph_manager.ROUTE_CONFIG, "SNAP_BRIDGE_PENALTY_M", 45.0)
    monkeypatch.setitem(graph_manager.ROUTE_CONFIG, "SNAP_EDGE_NEAR_THRESHOLD_M", 25.0)
    monkeypatch.setitem(graph_manager.ROUTE_CONFIG, "SNAP_NODE_EDGE_GAP_MAX_M", 110.0)

    G = nx.MultiDiGraph()
    G.add_node(1, x=29.0000, y=41.0000)
    G.add_node(2, x=29.0020, y=41.0000)
    G.add_node(3, x=29.0010, y=41.0007)
    _add_edge_bidir(G, 1, 2, length=200.0, bridge="yes")
    _add_edge_bidir(G, 1, 3, length=50.0)

    monkeypatch.setattr(graph_manager.ox, "nearest_edges", lambda *args, **kwargs: (1, 2, 0))

    node_id, snap_m = graph_manager.find_nearest_node_with_distance(G, 41.0000, 29.0010)

    assert node_id == 3
    assert snap_m < 5.0


def test_snap_gap_rule_rejects_too_far_first_candidate(monkeypatch):
    monkeypatch.setitem(graph_manager.ROUTE_CONFIG, "SNAP_MAX_NEIGHBOR_CANDIDATES", 4)
    monkeypatch.setitem(graph_manager.ROUTE_CONFIG, "SNAP_EDGE_NEAR_THRESHOLD_M", 30.0)
    monkeypatch.setitem(graph_manager.ROUTE_CONFIG, "SNAP_NODE_EDGE_GAP_MAX_M", 70.0)

    G = nx.MultiDiGraph()
    G.add_node(1, x=29.0000, y=41.0000)
    G.add_node(2, x=29.0040, y=41.0000)
    G.add_node(3, x=29.0020, y=41.0003)
    _add_edge_bidir(G, 1, 2, length=420.0, bridge="yes")
    _add_edge_bidir(G, 1, 3, length=35.0)

    monkeypatch.setattr(graph_manager.ox, "nearest_edges", lambda *args, **kwargs: (1, 2, 0))

    # Force bridge endpoint to have an artificially attractive score.
    orig_penalty = graph_manager._edge_semantic_penalty_m

    def patched_penalty(data):
        if str((data or {}).get("bridge", "")).lower() == "yes":
            return -400.0
        return orig_penalty(data)

    monkeypatch.setattr(graph_manager, "_edge_semantic_penalty_m", patched_penalty)

    node_id, snap_m = graph_manager.find_nearest_node_with_distance(G, 41.0000, 29.0020)

    assert node_id == 3
    assert snap_m < 10.0
