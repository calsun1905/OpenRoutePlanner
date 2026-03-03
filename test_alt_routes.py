import requests

url = "http://localhost:5000/api/get-alternative-routes"
payload = {
    "points": [[41.0117, 28.9818], [40.9903, 29.0291]], # Example: Taksim to Kadikoy (different sides of sea, maybe hard? Let's use two points on the same side)
    "optimize": False
}
print("Testing Taksim -> Sirkeci:")
payload["points"] = [[41.0368, 28.9850], [41.0150, 28.9750]]
res = requests.post(url, json=payload)
data = res.json()

if "alternatives" in data:
    for alt in data["alternatives"]:
        print(f"Type: {alt['type']}, Distance: {alt['distance_km']} km, Duration: {alt['duration_minutes']} min, Nodes: {len(alt['route_coords'])}")
else:
    print(data)
