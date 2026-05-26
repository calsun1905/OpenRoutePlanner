import os
import sys

import networkx as nx


backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

import graph_manager


def test_outdoor_graph_rejects_building_passage_shortcut():
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, length=1, highway="footway", tunnel="building_passage")
    graph.add_edge(1, 3, length=10, highway="footway")
    graph.add_edge(3, 2, length=10, highway="residential")

    filtered = graph_manager._filter_outdoor_walk_graph(graph)

    assert not filtered.has_edge(1, 2)
    assert nx.shortest_path(filtered, 1, 2, weight="length") == [1, 3, 2]


def test_outdoor_graph_rejects_indoor_and_private_edges():
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, length=1, highway="corridor", indoor="yes")
    graph.add_edge(2, 3, length=1, highway="footway", access="private")
    graph.add_edge(1, 4, length=10, highway="pedestrian")
    graph.add_edge(4, 3, length=10, highway="footway")

    filtered = graph_manager._filter_outdoor_walk_graph(graph)

    assert not filtered.has_edge(1, 2)
    assert not filtered.has_edge(2, 3)
    assert filtered.has_edge(1, 4)
    assert filtered.has_edge(4, 3)


def test_bridge_edges_are_kept_even_when_access_tag_is_restrictive():
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, length=120, highway="motorway", bridge="yes", access="no")
    graph.add_edge(2, 3, length=80, highway="residential")

    filtered = graph_manager._filter_outdoor_walk_graph(graph)

    assert filtered.has_edge(1, 2)
    assert filtered.has_edge(2, 3)


def test_cross_bosphorus_uses_all_public_when_configured_walk(monkeypatch, tmp_path):
    calls = {}

    def fake_graph_from_point(center, dist, network_type, retain_all=False):
        calls["network_type"] = network_type
        calls["retain_all"] = retain_all
        graph = nx.MultiDiGraph()
        graph.add_node(1, x=29.0000, y=41.0000)
        graph.add_node(2, x=29.1000, y=41.0500)
        graph.add_edge(1, 2, key=0, length=1000, bridge="yes")
        return graph

    monkeypatch.setattr(graph_manager, "DATA_DIR", str(tmp_path))
    monkeypatch.setitem(graph_manager.ROUTE_CONFIG, "OSM_NETWORK_TYPE", "walk")
    monkeypatch.setitem(graph_manager.ROUTE_CONFIG, "GRAPH_RADIUS_MIN_M", 500)
    monkeypatch.setitem(graph_manager.ROUTE_CONFIG, "GRAPH_RADIUS_PADDING_M", 300)
    monkeypatch.setitem(graph_manager.ROUTE_CONFIG, "GRAPH_RADIUS_MAX_M", 20000)
    monkeypatch.setattr(graph_manager.ox, "graph_from_point", fake_graph_from_point)
    monkeypatch.setattr(graph_manager.ox, "save_graphml", lambda G, path: None)

    points = [(41.0000, 29.0000), (41.0500, 29.1000)]
    graph_manager.get_graph_for_points(points)

    assert calls.get("network_type") == "all_public"
    assert calls.get("retain_all") is False
