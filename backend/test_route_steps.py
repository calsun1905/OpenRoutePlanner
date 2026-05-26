import json
import networkx as nx
import app as app_module
from app import app


def make_test_graph():
    G = nx.MultiDiGraph()
    # nodes: id, with x=lon, y=lat
    G.add_node(1, x=29.0000, y=41.0000)
    G.add_node(2, x=29.0010, y=41.0005)
    G.add_node(3, x=29.0020, y=41.0010)

    # edges with length in meters and name
    G.add_edge(1, 2, key=0, length=120.0, name='Ataturk Caddesi')
    G.add_edge(2, 3, key=0, length=80.0, name='Istiklal Sokak')
    return G


def test_get_route_steps_basic(monkeypatch):
    G = make_test_graph()

    # Patch functions in app module to use our test graph and deterministic behavior
    monkeypatch.setattr(app_module, "get_graph_for_points", lambda pts: G, raising=False)
    monkeypatch.setattr(app_module, "solve_tsp", lambda G_, pts: list(range(len(pts))), raising=False)
    monkeypatch.setattr(app_module, "build_alternative_routes", lambda G_, ordered_points, idx: [1, 2, 3], raising=False)
    monkeypatch.setattr(app_module, "nodes_to_coords", lambda G_, nodes: [[G_.nodes[n]['y'], G_.nodes[n]['x']] for n in nodes], raising=False)

    client = app.test_client()

    points = [[41.0000, 29.0000], [41.0005, 29.0010], [41.0010, 29.0020]]

    resp = client.post('/api/get-route-steps', json={'points': points, 'optimize': False})
    assert resp.status_code == 200, resp.data.decode()

    data = resp.get_json()
    assert 'steps' in data
    steps = data['steps']
    assert isinstance(steps, list)
    assert len(steps) >= 1

    # Check fields on first step
    first = steps[0]
    for k in ('step_id','instruction', 'distance_m', 'duration_s', 'duration_min', 'street_name', 'turn_type', 'coords', 'cumulative_distance_m'):
        assert k in first, f"Missing key {k} in step"
    # distance should be roughly 120 or sum
    assert isinstance(first['distance_m'], int)
    assert first['distance_m'] > 0

    # route_coords present
    assert 'route_coords' in data
    assert isinstance(data['route_coords'], list)


def test_missing_street_name(monkeypatch):
    # Graph with no street name -> fallback behavior
    G = nx.MultiDiGraph()
    G.add_node(1, x=29.0, y=41.0)
    G.add_node(2, x=29.001, y=41.0005)
    G.add_edge(1, 2, key=0, length=50.0)

    monkeypatch.setattr(app_module, "get_graph_for_points", lambda pts: G, raising=False)
    monkeypatch.setattr(app_module, "solve_tsp", lambda G_, pts: list(range(len(pts))), raising=False)
    monkeypatch.setattr(app_module, "build_alternative_routes", lambda G_, ordered_points, idx: [1, 2], raising=False)
    monkeypatch.setattr(app_module, "nodes_to_coords", lambda G_, nodes: [[G_.nodes[n]['y'], G_.nodes[n]['x']] for n in nodes], raising=False)

    client = app.test_client()
    points = [[41.0, 29.0], [41.0005, 29.0010]]
    resp = client.post('/api/get-route-steps', json={'points': points, 'optimize': False})
    assert resp.status_code == 200, resp.data.decode()
    data = resp.get_json()
    steps = data.get('steps', [])
    assert len(steps) >= 1
    # fallback street name should be 'yol' per implementation
    assert steps[0]['street_name'] == 'yol'


def test_roundabout_detection(monkeypatch):
    # Graph where second edge is marked as roundabout
    G = nx.MultiDiGraph()
    G.add_node(1, x=29.0, y=41.0)
    G.add_node(2, x=29.0010, y=41.0005)
    G.add_node(3, x=29.0020, y=41.0010)

    G.add_edge(1, 2, key=0, length=100.0, name='Ana Cadde')
    G.add_edge(2, 3, key=0, length=60.0, junction='roundabout', name='Kavsak Sk')

    monkeypatch.setattr(app_module, "get_graph_for_points", lambda pts: G, raising=False)
    monkeypatch.setattr(app_module, "solve_tsp", lambda G_, pts: list(range(len(pts))), raising=False)
    monkeypatch.setattr(app_module, "build_alternative_routes", lambda G_, ordered_points, idx: [1, 2, 3], raising=False)
    monkeypatch.setattr(app_module, "nodes_to_coords", lambda G_, nodes: [[G_.nodes[n]['y'], G_.nodes[n]['x']] for n in nodes], raising=False)

    client = app.test_client()
    points = [[41.0, 29.0], [41.0005, 29.0010], [41.0010, 29.0020]]
    resp = client.post('/api/get-route-steps', json={'points': points, 'optimize': False})
    assert resp.status_code == 200, resp.data.decode()
    data = resp.get_json()
    steps = data.get('steps', [])
    assert len(steps) >= 1
    # Expect at least one step to reference roundabout in turn_type or instruction
    assert any((s.get('turn_type') == 'roundabout') or ('kavşa' in s.get('instruction', '').lower()) for s in steps), "Roundabout not detected"


def test_numeric_string_points_are_parsed_before_routing(monkeypatch):
    G = make_test_graph()
    captured = {}

    monkeypatch.setattr(app_module, "get_graph_for_points", lambda pts: G, raising=False)
    monkeypatch.setattr(app_module, "solve_tsp", lambda G_, pts: list(range(len(pts))), raising=False)

    def fake_builder(G_, ordered_points, idx):
        captured['ordered_points'] = ordered_points
        return [1, 2, 3]

    monkeypatch.setattr(app_module, "build_alternative_routes", fake_builder, raising=False)
    monkeypatch.setattr(app_module, "nodes_to_coords", lambda G_, nodes: [[G_.nodes[n]['y'], G_.nodes[n]['x']] for n in nodes], raising=False)

    client = app.test_client()
    points = [["41.0000", "29.0000"], ["41.0005", "29.0010"], ["41.0010", "29.0020"]]
    resp = client.post('/api/get-route-steps', json={'points': points, 'optimize': False})

    assert resp.status_code == 200, resp.data.decode()
    assert captured['ordered_points'][0] == (41.0, 29.0)
    assert isinstance(captured['ordered_points'][0][0], float)


def test_route_steps_group_consecutive_same_street(monkeypatch):
    G = nx.MultiDiGraph()
    G.add_node(1, x=29.0, y=41.0)
    G.add_node(2, x=29.001, y=41.0005)
    G.add_node(3, x=29.002, y=41.0010)
    G.add_edge(1, 2, key=0, length=90.0, name='Ayni Sokak')
    G.add_edge(2, 3, key=0, length=110.0, name='Ayni Sokak')

    monkeypatch.setattr(app_module, "get_graph_for_points", lambda pts: G, raising=False)
    monkeypatch.setattr(app_module, "solve_tsp", lambda G_, pts: list(range(len(pts))), raising=False)
    monkeypatch.setattr(app_module, "build_alternative_routes", lambda G_, ordered_points, idx: [1, 2, 3], raising=False)
    monkeypatch.setattr(app_module, "nodes_to_coords", lambda G_, nodes: [[G_.nodes[n]['y'], G_.nodes[n]['x']] for n in nodes], raising=False)

    client = app.test_client()
    points = [[41.0, 29.0], [41.0005, 29.001], [41.001, 29.002]]
    resp = client.post('/api/get-route-steps', json={'points': points, 'optimize': False})

    assert resp.status_code == 200, resp.data.decode()
    steps = resp.get_json()['steps']
    assert len(steps) == 1
    assert steps[0]['street_name'] == 'Ayni Sokak'
    assert steps[0]['distance_m'] == 200
    assert len(steps[0]['coords']) == 3


def test_get_route_includes_estimated_route_minutes_alias(monkeypatch):
    G = make_test_graph()

    monkeypatch.setattr(app_module, "get_graph_for_points", lambda pts, radius_multiplier=1.0: G, raising=False)
    monkeypatch.setattr(app_module, "solve_tsp", lambda G_, pts: list(range(len(pts))), raising=False)
    monkeypatch.setattr(app_module, "build_alternative_routes", lambda G_, ordered_points, idx: [1, 2, 3], raising=False)
    monkeypatch.setattr(app_module, "nodes_to_coords", lambda G_, nodes: [[G_.nodes[n]['y'], G_.nodes[n]['x']] for n in nodes], raising=False)

    client = app.test_client()
    points = [[41.0000, 29.0000], [41.0005, 29.0010], [41.0010, 29.0020]]
    resp = client.post('/api/get-route', json={'points': points, 'optimize': False, 'route_type': 'route_1'})

    assert resp.status_code == 200, resp.data.decode()
    data = resp.get_json()
    assert "estimated_walk_minutes" in data
    assert "estimated_route_minutes" in data
    assert data["estimated_route_minutes"] == data["estimated_walk_minutes"]


def test_cross_bosphorus_points_prefer_wide_graph_multiplier(monkeypatch):
    monkeypatch.setitem(app_module.ROUTE_CONFIG, "ROUTE_GRAPH_RADIUS_MULTIPLIERS", [1.0, 2.8, 4.2])
    monkeypatch.setitem(app_module.ROUTE_CONFIG, "ROUTE_GRAPH_PREF_MULTIPLIER", 2.8)
    monkeypatch.setitem(app_module.ROUTE_CONFIG, "ROUTE_GRAPH_FORCE_WIDE_IF_MAX_DISTANCE_M", 2000)

    points = [(41.0430, 29.0042), (41.0257, 29.0169)]
    multipliers = app_module._route_radius_multipliers(points)

    assert multipliers[0] == 2.8
    assert 1.0 in multipliers


def test_short_inner_city_points_keep_default_first_multiplier(monkeypatch):
    monkeypatch.setitem(app_module.ROUTE_CONFIG, "ROUTE_GRAPH_RADIUS_MULTIPLIERS", [1.0, 2.8, 4.2])
    monkeypatch.setitem(app_module.ROUTE_CONFIG, "ROUTE_GRAPH_PREF_MULTIPLIER", 2.8)
    monkeypatch.setitem(app_module.ROUTE_CONFIG, "ROUTE_GRAPH_FORCE_WIDE_IF_MAX_DISTANCE_M", 2000)

    points = [(41.0256, 28.9741), (41.0170, 28.9702)]
    multipliers = app_module._route_radius_multipliers(points)

    assert multipliers[0] == 1.0
