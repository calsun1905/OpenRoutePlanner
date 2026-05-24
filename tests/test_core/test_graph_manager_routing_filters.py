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
