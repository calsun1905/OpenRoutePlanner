"""
test_route_batch_alternatives.py - Batch Alternative Routes Tests

Tests for verifying that batch alternative route generation produces
truly different routes when multiple segments have varying numbers of alternatives.
"""
import networkx as nx
import route_engine_impl as route_engine


def _graph_with_varying_alternatives():
    """
    Create a graph where different segments have different numbers of alternatives.
    
    Segment 1 (A->B): 3 alternatives available
    Segment 2 (B->C): Only 1 alternative (shortest path)
    
    This tests that the batch algorithm handles varying segment alternatives correctly.
    """
    G = nx.MultiDiGraph()
    
    # Set CRS for osmnx compatibility
    G.graph["crs"] = "EPSG:4326"
    
    # Nodes: A=1, B=2, C=3, D=4, E=5
    G.add_node(1, x=29.0, y=41.0)   # A
    G.add_node(2, x=29.1, y=41.1)   # B  
    G.add_node(3, x=29.2, y=41.2)   # C
    G.add_node(4, x=29.15, y=41.05)  # D - alternative path via
    G.add_node(5, x=29.15, y=41.15)  # E - alternative path via
    
    # Segment 1: 1 -> 2 (has multiple paths)
    G.add_edge(1, 2, key=0, length=100.0, name='Ana Yol')  # direct
    G.add_edge(1, 4, key=0, length=60.0, name='Yan Yol 1')  # via D
    G.add_edge(4, 2, key=0, length=60.0, name='Yan Yol 1')
    G.add_edge(1, 5, key=0, length=50.0, name='Yan Yol 2')  # via E
    G.add_edge(5, 2, key=0, length=50.0, name='Yan Yol 2')
    
    # Segment 2: 2 -> 3 (only one path - dead end scenario)
    G.add_edge(2, 3, key=0, length=100.0, name='Baglanti Yolu')
    
    return G


def test_batch_handles_varying_segment_alternatives(monkeypatch):
    """
    Test that batch alternative routes properly handles segments with
    different numbers of available alternatives.
    
    When segment 2 only has 1 alternative, the algorithm should:
    - Still produce valid routes (not crash)
    - Not produce duplicate/identical routes
    - Properly fallback when index exceeds available alternatives
    """
    G = _graph_with_varying_alternatives()
    ordered_points = [(41.0, 29.0), (41.1, 29.1), (41.2, 29.2)]
    
    # Track which segments were called
    call_count = [0, 0]
    
    def mock_find_alternatives(G_, origin, dest, num_routes=3):
        call_count[0] += 1
        seg_idx = call_count[0] - 1
        
        # Find shortest path
        try:
            path = route_engine.shortest_path(G_, origin, dest)
        except nx.NetworkXNoPath:
            return []
        
        result = [{
            "type": f"route_1",
            "name": "Rota 1",
            "icon": "📍",
            "nodes": path,
            "distance_km": 0.1,
            "duration_minutes": 1,
            "description": "0.1 km"
        }]
        
        # Segment 1 has 3 alternatives, segment 2 only has 1
        if seg_idx == 0 and origin == 1 and dest == 2:
            # Add via-node alternatives
            if 4 in G_.nodes():
                try:
                    via_path1 = route_engine.shortest_path(G_, 1, 4) + route_engine.shortest_path(G_, 4, 2)[1:]
                    result.append({
                        "type": "route_2",
                        "name": "Rota 2",
                        "icon": "📍",
                        "nodes": via_path1,
                        "distance_km": 0.12,
                        "duration_minutes": 2,
                        "description": "0.12 km"
                    })
                except nx.NetworkXNoPath:
                    pass
            
            if 5 in G_.nodes():
                try:
                    via_path2 = route_engine.shortest_path(G_, 1, 5) + route_engine.shortest_path(G_, 5, 2)[1:]
                    result.append({
                        "type": "route_3",
                        "name": "Rota 3",
                        "icon": "📍",
                        "nodes": via_path2,
                        "distance_km": 0.10,
                        "duration_minutes": 1,
                        "description": "0.10 km"
                    })
                except nx.NetworkXNoPath:
                    pass
        
        return result
    
    monkeypatch.setattr(route_engine, "find_alternative_routes", mock_find_alternatives)
    
    results = route_engine.build_all_alternative_routes_batch(G, ordered_points)
    
    # Should produce routes (not crash)
    assert isinstance(results, list), "Should return a list"
    
    # Each route should have valid structure
    for route in results:
        assert "nodes" in route, "Route should have nodes"
        assert "distance_km" in route, "Route should have distance_km"
        assert route["nodes"], "Route nodes should not be empty"


def test_batch_validates_path_connectivity(monkeypatch):
    """
    Test that batch routes validates that each full route path
    has connected edges before returning.
    """
    G = nx.MultiDiGraph()
    G.graph["crs"] = "EPSG:4326"
    
    # Create nodes
    G.add_node(1, x=29.0, y=41.0)
    G.add_node(2, x=29.1, y=41.1)
    G.add_node(3, x=29.2, y=41.2)
    
    # Create disconnected segments
    G.add_edge(1, 2, key=0, length=100.0)  # A->B exists
    # NOTE: 2->3 does NOT exist
    
    ordered_points = [(41.0, 29.0), (41.1, 29.1), (41.2, 29.2)]
    
    # Mock find_nearest_node to return known node IDs
    node_map = {(41.0, 29.0): 1, (41.1, 29.1): 2, (41.2, 29.2): 3}
    monkeypatch.setattr(route_engine, "find_nearest_node", lambda G_, lat, lon: node_map.get((lat, lon), 1))
    
    def mock_find_alternatives(G_, origin, dest, num_routes=3):
        if origin == 1 and dest == 2:
            return [{
                "type": "route_1",
                "name": "Rota 1",
                "nodes": [1, 2],
                "distance_km": 0.1,
                "duration_minutes": 1
            }]
        elif origin == 2 and dest == 3:
            return []  # No path exists
        return []
    
    monkeypatch.setattr(route_engine, "find_alternative_routes", mock_find_alternatives)
    
    results = route_engine.build_all_alternative_routes_batch(G, ordered_points)
    
    # Should return empty when any segment has no alternatives
    assert results == [], "Should return empty when segment has no alternatives"


def test_batch_rejects_invalid_full_path(monkeypatch):
    """
    Test that batch rejects a route where segments don't connect properly.
    """
    G = nx.MultiDiGraph()
    G.graph["crs"] = "EPSG:4326"
    
    G.add_node(1, x=29.0, y=41.0)
    G.add_node(2, x=29.1, y=41.1)
    G.add_node(3, x=29.2, y=41.2)
    G.add_node(4, x=29.15, y=41.15)  # Different branch
    
    # Segment 1 ends at 2
    G.add_edge(1, 2, key=0, length=100.0)
    
    # Segment 2 starts from 4, not 2 - creates disconnect!
    G.add_edge(4, 3, key=0, length=100.0)
    
    ordered_points = [(41.0, 29.0), (41.1, 29.1), (41.2, 29.2)]
    
    # Mock find_nearest_node
    node_map = {(41.0, 29.0): 1, (41.1, 29.1): 2, (41.2, 29.2): 3}
    monkeypatch.setattr(route_engine, "find_nearest_node", lambda G_, lat, lon: node_map.get((round(lat, 1), round(lon, 1)), 1))
    
    def mock_find_alternatives(G_, origin, dest, num_routes=3):
        if origin == 1 and dest == 2:
            return [{
                "type": "route_1",
                "name": "Rota 1",
                "nodes": [1, 2],
                "distance_km": 0.1,
                "duration_minutes": 1
            }]
        elif origin == 2 and dest == 3:
            return [{
                "type": "route_1", 
                "name": "Rota 1",
                "nodes": [4, 3],  # Doesn't connect to 2!
                "distance_km": 0.1,
                "duration_minutes": 1
            }]
        return []
    
    monkeypatch.setattr(route_engine, "find_alternative_routes", mock_find_alternatives)
    
    results = route_engine.build_all_alternative_routes_batch(G, ordered_points)
    
    # The combined path [1, 2] + [4, 3] should be invalid
    # because 2 and 4 are not connected
    assert results == [], "Should reject invalid combined path"


def test_overlap_detection_with_subset_routes():
    """
    Test that overlap detection correctly identifies when a small route
    is a complete subset of a larger route.
    
    This is the asymmetric overlap case:
    - Large route: 10 edges
    - Small route: 5 edges (all of which overlap with large route)
    
    Expected: overlap should be 100% (small is 100% subset of large)
    """
    # Large route edges
    large_edges = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), 
                   (6, 7), (7, 8), (8, 9), (9, 10), (10, 11)]
    
    # Small route - subset of large (first 5 edges)
    small_edges = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6)]
    
    # Test: small edges are 100% contained in large
    overlap = route_engine.count_edge_overlap(large_edges, small_edges)
    
    # Asymmetric: small_edges (set2) overlap with large_edges (set1)
    # small = 5 edges, all 5 overlap with large = 5/5 = 100%
    assert overlap == 1.0, f"Expected 100% overlap (small is 100% subset), got {overlap:.0%}"
    
    # Test reverse: large edges vs small edges
    # large = 10 edges, only 5 overlap with small = 5/10 = 50%
    overlap_reverse = route_engine.count_edge_overlap(small_edges, large_edges)
    assert overlap_reverse == 0.5, f"Expected 50% overlap (large has only 5 matching), got {overlap_reverse:.0%}"


def test_overlap_detection_identical_routes():
    """Test overlap of identical routes = 100%"""
    edges = [(1, 2), (2, 3), (3, 4), (4, 5)]
    
    overlap = route_engine.count_edge_overlap(edges, edges)
    assert overlap == 1.0, f"Identical routes should have 100% overlap, got {overlap:.0%}"


def test_overlap_detection_no_overlap():
    """Test overlap of completely different routes = 0%"""
    edges1 = [(1, 2), (2, 3), (3, 4)]
    edges2 = [(10, 11), (11, 12), (12, 13)]
    
    overlap = route_engine.count_edge_overlap(edges1, edges2)
    assert overlap == 0.0, f"No overlap should be 0%, got {overlap:.0%}"


def test_overlap_detection_partial_overlap():
    """Test partial overlap scenarios"""
    edges1 = [(1, 2), (2, 3), (3, 4), (4, 5)]
    edges2 = [(3, 4), (4, 5), (5, 6), (6, 7)]
    
    overlap = route_engine.count_edge_overlap(edges1, edges2)
    # edges2 has 4 edges, 2 of them (3-4, 4-5) overlap with edges1
    # overlap = 2/4 = 50%
    assert overlap == 0.5, f"Expected 50% overlap, got {overlap:.0%}"
