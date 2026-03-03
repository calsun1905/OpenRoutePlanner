"""
Test script for API endpoints
"""

import requests
import json

BASE_URL = "http://localhost:5000/api"

def test_health():
    """Test health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_save_route():
    """Test save route endpoint"""
    print("\n=== Testing Save Route ===")
    
    route_data = {
        "name": "Test Rotası",
        "description": "Bu bir test rotasıdır",
        "points": [[40.9903, 29.0291], [40.9950, 29.0350]],
        "route_coords": [[40.9903, 29.0291], [40.9920, 29.0310], [40.9950, 29.0350]],
        "distance_km": 2.5,
        "duration_minutes": 30,
        "route_type": "shortest",
        "tags": ["test", "kadıköy"]
    }
    
    response = requests.post(f"{BASE_URL}/routes/save", json=route_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        return response.json()["route"]["id"]
    return None

def test_get_routes():
    """Test get all routes endpoint"""
    print("\n=== Testing Get All Routes ===")
    response = requests.get(f"{BASE_URL}/routes")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Total routes: {data['count']}")
    if data['routes']:
        print(f"First route: {data['routes'][0]['name']}")
    return response.status_code == 200

def test_get_route(route_id):
    """Test get single route endpoint"""
    print(f"\n=== Testing Get Route {route_id} ===")
    response = requests.get(f"{BASE_URL}/routes/{route_id}")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Route name: {data['route']['name']}")
        print(f"Times used: {data['route']['times_used']}")
    return response.status_code == 200

def test_toggle_favorite(route_id):
    """Test toggle favorite endpoint"""
    print(f"\n=== Testing Toggle Favorite {route_id} ===")
    response = requests.post(f"{BASE_URL}/routes/{route_id}/favorite")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Is favorite: {data['is_favorite']}")
    return response.status_code == 200

def test_search_routes():
    """Test search routes endpoint"""
    print("\n=== Testing Search Routes ===")
    response = requests.get(f"{BASE_URL}/routes/search?q=test")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Found {data['count']} routes")
    return response.status_code == 200

def test_statistics():
    """Test statistics endpoint"""
    print("\n=== Testing Statistics ===")
    response = requests.get(f"{BASE_URL}/routes/statistics")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Total routes: {data['total_routes']}")
        print(f"Total distance: {data['total_distance_km']} km")
        print(f"Favorites: {data['favorite_count']}")
    return response.status_code == 200

def test_delete_route(route_id):
    """Test delete route endpoint"""
    print(f"\n=== Testing Delete Route {route_id} ===")
    response = requests.delete(f"{BASE_URL}/routes/{route_id}")
    print(f"Status: {response.status_code}")
    return response.status_code == 200

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("OpenRoutePlanner API Endpoint Tests")
    print("=" * 60)
    
    try:
        # Test 1: Health check
        if not test_health():
            print("\n❌ Health check failed! Is the server running?")
            return
        
        # Test 2: Save route
        route_id = test_save_route()
        if not route_id:
            print("\n❌ Save route failed!")
            return
        
        # Test 3: Get all routes
        test_get_routes()
        
        # Test 4: Get single route
        test_get_route(route_id)
        
        # Test 5: Toggle favorite
        test_toggle_favorite(route_id)
        
        # Test 6: Search routes
        test_search_routes()
        
        # Test 7: Statistics
        test_statistics()
        
        # Test 8: Delete route
        test_delete_route(route_id)
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection error! Make sure the server is running:")
        print("   cd backend")
        print("   python app.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    run_all_tests()
