import os
import sys

import networkx as nx


backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

import route_engine_impl as rei


def _add_node(graph: nx.MultiDiGraph, node_id: int, lat: float, lon: float) -> None:
    graph.add_node(node_id, y=lat, x=lon)


def test_nodes_to_coords_returns_empty_when_edge_missing():
    graph = nx.MultiDiGraph()
    _add_node(graph, 1, 41.0, 29.0)
    _add_node(graph, 2, 41.01, 29.01)

    coords = rei.nodes_to_coords(graph, [1, 2])
    assert coords == []


def test_path_to_edges_uses_shortest_parallel_edge_key():
    graph = nx.MultiDiGraph()
    _add_node(graph, 1, 41.0, 29.0)
    _add_node(graph, 2, 41.01, 29.01)

    key_long = graph.add_edge(1, 2, length=50.0)
    key_short = graph.add_edge(1, 2, length=10.0)

    edges = rei.path_to_edges(graph, [1, 2])

    assert edges == [(1, 2, key_short)]
    assert key_long != key_short


def test_calculate_route_stats_uses_shortest_parallel_edge_length():
    graph = nx.MultiDiGraph()
    _add_node(graph, 1, 41.0, 29.0)
    _add_node(graph, 2, 41.01, 29.01)
    _add_node(graph, 3, 41.02, 29.02)

    graph.add_edge(1, 2, length=120.0)
    graph.add_edge(1, 2, length=20.0)  # shortest secilmeli
    graph.add_edge(2, 3, length=30.0)

    stats = rei.calculate_route_stats(graph, [1, 2, 3])
    assert stats["total_distance_km"] == 0.05  # 20m + 30m


def test_build_full_route_aborts_when_segments_disconnect(monkeypatch):
    graph = nx.MultiDiGraph()
    _add_node(graph, 1, 41.0, 29.0)
    _add_node(graph, 2, 41.01, 29.01)
    _add_node(graph, 6, 41.02, 29.02)
    graph.add_edge(1, 2, length=100.0)
    # 2 -> 6 baglantisi yok

    monkeypatch.setattr(rei, "find_nearest_node", lambda _g, lat, lon: int(lat))

    route = rei.build_full_route(graph, [(1.0, 0.0), (2.0, 0.0), (6.0, 0.0)])
    assert route == []

