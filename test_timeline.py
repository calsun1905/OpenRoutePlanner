"""
Test script for Timeline API
"""

import requests
import json

BASE_URL = "http://localhost:5000/api"

def test_create_timeline():
    """Test timeline creation"""
    print("\n=== Testing Timeline Creation ===")
    
    timeline_data = {
        "points": [
            {"name": "Kadıköy", "lat": 40.9903, "lon": 29.0291},
            {"name": "Moda", "lat": 40.9850, "lon": 29.0350},
            {"name": "Fenerbahçe", "lat": 40.9800, "lon": 29.0400}
        ],
        "segment_distances": [0.8, 0.7],  # km
        "start_time": "09:00",
        "visit_duration": 30,
        "transport_mode": "walking"
    }
    
    response = requests.post(f"{BASE_URL}/timeline/create", json=timeline_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Timeline Created Successfully!")
        print(f"Start Time: {data['start_time']}")
        print(f"End Time: {data['end_time']}")
        print(f"Total Duration: {data['total_duration_minutes']} minutes")
        print(f"Travel Time: {data['total_travel_time_minutes']} minutes")
        print(f"Visit Time: {data['total_visit_time_minutes']} minutes")
        
        print(f"\n📅 Schedule:")
        for item in data['schedule']:
            print(f"\n  {item['point_index'] + 1}. {item['point_name']}")
            print(f"     Arrival: {item['arrival_time']}")
            print(f"     Departure: {item['departure_time']}")
            print(f"     Visit: {item['visit_duration_minutes']} min")
            if item['next_travel_time_minutes'] > 0:
                print(f"     Travel to next: {item['next_travel_time_minutes']} min")
        
        return data
    else:
        print(f"❌ Error: {response.json()}")
        return None

def test_check_conflicts():
    """Test conflict checking"""
    print("\n=== Testing Conflict Checking ===")
    
    schedule = [
        {
            "point_index": 0,
            "point_name": "Müze",
            "arrival_time": "20:00",
            "departure_time": "20:30",
            "visit_duration_minutes": 30,
            "next_travel_time_minutes": 15
        }
    ]
    
    opening_hours = {
        "0": {"open": "09:00", "close": "18:00"}
    }
    
    conflict_data = {
        "schedule": schedule,
        "opening_hours": opening_hours
    }
    
    response = requests.post(f"{BASE_URL}/timeline/check-conflicts", json=conflict_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data['warnings']:
            print(f"\n⚠️ Warnings Found:")
            for warning in data['warnings']:
                print(f"  - {warning['point_name']}: {warning['warning']}")
                print(f"    Arrival: {warning['arrival_time']}")
                print(f"    Opening Hours: {warning['opening_hours']}")
        else:
            print(f"\n✅ No conflicts found!")
        return data
    else:
        print(f"❌ Error: {response.json()}")
        return None

def test_optimize_schedule():
    """Test schedule optimization"""
    print("\n=== Testing Schedule Optimization ===")
    
    schedule = [
        {
            "point_index": 0,
            "point_name": "Nokta 1",
            "arrival_time": "09:00",
            "departure_time": "10:30",
            "visit_duration_minutes": 90,
            "next_travel_time_minutes": 30
        },
        {
            "point_index": 1,
            "point_name": "Nokta 2",
            "arrival_time": "11:00",
            "departure_time": "13:00",
            "visit_duration_minutes": 120,
            "next_travel_time_minutes": 20
        },
        {
            "point_index": 2,
            "point_name": "Nokta 3",
            "arrival_time": "13:20",
            "departure_time": "14:50",
            "visit_duration_minutes": 90,
            "next_travel_time_minutes": 0
        }
    ]
    
    optimize_data = {
        "schedule": schedule,
        "max_duration_minutes": 240,  # 4 saat
        "preferred_end_time": "14:00"
    }
    
    response = requests.post(f"{BASE_URL}/timeline/optimize", json=optimize_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n📊 Optimization Results:")
        print(f"Total Duration: {data['total_duration_minutes']} minutes")
        
        if data['suggestions']:
            print(f"\n💡 Suggestions:")
            for suggestion in data['suggestions']:
                print(f"  - Type: {suggestion['type']}")
                print(f"    Message: {suggestion['message']}")
                if 'suggestion' in suggestion:
                    print(f"    Suggestion: {suggestion['suggestion']}")
        else:
            print(f"\n✅ Schedule is optimal!")
        
        return data
    else:
        print(f"❌ Error: {response.json()}")
        return None

def test_different_transport_modes():
    """Test different transport modes"""
    print("\n=== Testing Different Transport Modes ===")
    
    points = [
        {"name": "Start", "lat": 40.9903, "lon": 29.0291},
        {"name": "End", "lat": 40.9850, "lon": 29.0350}
    ]
    
    segment_distances = [1.0]  # 1 km
    
    modes = ["walking", "cycling", "driving"]
    
    for mode in modes:
        timeline_data = {
            "points": points,
            "segment_distances": segment_distances,
            "start_time": "09:00",
            "visit_duration": 30,
            "transport_mode": mode
        }
        
        response = requests.post(f"{BASE_URL}/timeline/create", json=timeline_data)
        
        if response.status_code == 200:
            data = response.json()
            travel_time = data['schedule'][0]['next_travel_time_minutes']
            print(f"\n{mode.upper()}:")
            print(f"  Distance: 1 km")
            print(f"  Travel Time: {travel_time} minutes")
            print(f"  End Time: {data['end_time']}")
        else:
            print(f"\n❌ {mode} failed: {response.json()}")

def run_all_tests():
    """Run all timeline tests"""
    print("=" * 60)
    print("OpenRoutePlanner Timeline API Tests")
    print("=" * 60)
    
    try:
        # Test 1: Create timeline
        timeline = test_create_timeline()
        
        if not timeline:
            print("\n❌ Timeline creation failed!")
            return
        
        # Test 2: Check conflicts
        test_check_conflicts()
        
        # Test 3: Optimize schedule
        test_optimize_schedule()
        
        # Test 4: Different transport modes
        test_different_transport_modes()
        
        print("\n" + "=" * 60)
        print("✅ All timeline tests completed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection error! Make sure the server is running:")
        print("   cd backend")
        print("   python app.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()
