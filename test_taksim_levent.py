import sys
import os
sys.path.insert(0, 'c:/Users/batuf/Documents/GitHub/openroute/OpenRoutePlanner')
sys.path.insert(0, 'c:/Users/batuf/Documents/GitHub/openroute/OpenRoutePlanner/backend')

# Test Taksim -> Levent transit route
from multimodal_engine import find_transit_routes

# Taksim: 41.0082, 28.9782
# Levent: 41.0775, 29.0086

print("=== Taksim -> Levent Transit Route Test ===\n")

origin = {"lat": 41.0082, "lon": 28.9782}
destination = {"lat": 41.0775, "lon": 29.0086}

print(f"Origin: Taksim ({origin['lat']}, {origin['lon']})")
print(f"Destination: Levent ({destination['lat']}, {destination['lon']})")
print()

# Get transit routes
result = find_transit_routes(
    origin_lat=origin['lat'],
    origin_lon=origin['lon'],
    dest_lat=destination['lat'],
    dest_lon=destination['lon'],
    max_results=3
)

if not result:
    print("No transit routes found!")
else:
    print(f"Found {len(result)} route options:\n")
    
    for i, route in enumerate(result):
        print(f"--- Route {i+1} ---")
        print(f"  Name: {route.get('name', 'N/A')}")
        print(f"  Type: {route.get('type', 'N/A')}")
        print(f"  Transit Mode: {route.get('transit_mode', 'N/A')}")
        print(f"  Total Time: {route.get('total_time_min', 'N/A')} min")
        print(f"  Total Distance: {route.get('total_distance_m', 'N/A')} m")
        print(f"  Route Code: {route.get('route_code', 'N/A')}")
        
        segments = route.get('segments', [])
        print(f"  Segments: {len(segments)}")
        
        for j, seg in enumerate(segments):
            mode = seg.get('mode', '?')
            desc = seg.get('description', '?')
            coords = seg.get('coords', [])
            duration = seg.get('duration_min', 0)
            print(f"    [{j}] {mode}: {desc[:50]}... ({len(coords)} coords, {duration} min)")
        
        print()