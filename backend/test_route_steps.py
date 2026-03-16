import json
import networkx as nx
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
    app.get_graph_for_points = lambda pts: G
    app.solve_tsp = lambda G_, pts: list(range(len(pts)))
    app.build_alternative_routes = lambda G_, ordered_points, idx: [1, 2, 3]
    app.nodes_to_coords = lambda G_, nodes: [[G_.nodes[n]['y'], G_.nodes[n]['x']] for n in nodes]

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

    app.get_graph_for_points = lambda pts: G
    app.solve_tsp = lambda G_, pts: list(range(len(pts)))
    app.build_alternative_routes = lambda G_, ordered_points, idx: [1, 2]
    app.nodes_to_coords = lambda G_, nodes: [[G_.nodes[n]['y'], G_.nodes[n]['x']] for n in nodes]

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

    app.get_graph_for_points = lambda pts: G
    app.solve_tsp = lambda G_, pts: list(range(len(pts)))
    app.build_alternative_routes = lambda G_, ordered_points, idx: [1, 2, 3]
    app.nodes_to_coords = lambda G_, nodes: [[G_.nodes[n]['y'], G_.nodes[n]['x']] for n in nodes]

    client = app.test_client()
    points = [[41.0, 29.0], [41.0005, 29.0010], [41.0010, 29.0020]]
    resp = client.post('/api/get-route-steps', json={'points': points, 'optimize': False})
    assert resp.status_code == 200, resp.data.decode()
    data = resp.get_json()
    steps = data.get('steps', [])
    assert len(steps) >= 1
    # Expect at least one step to reference roundabout in turn_type or instruction
    assert any((s.get('turn_type') == 'roundabout') or ('kavşa' in s.get('instruction', '').lower()) for s in steps), "Roundabout not detected"
