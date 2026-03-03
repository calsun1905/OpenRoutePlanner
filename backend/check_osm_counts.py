import requests
import json

categories = {
    "Kafeler": {"amenity": "cafe"},
    "Restoranlar": {"amenity": "restaurant"},
    "Müzeler": {"tourism": "museum"},
    "Tekel Bayileri / İçki Satışı": {"shop": "alcohol"},
    "Bakkal / Büfe / Market": {"shop": "convenience"},
    "Hastaneler": {"amenity": "hospital"},
    "Eczaneler": {"amenity": "pharmacy"},
    "Süpermarketler": {"shop": "supermarket"}
}

overpass_url = "http://overpass-api.de/api/interpreter"

print("OSM Turkiye Veri Sayilari Cekiliyor...\n")

for name, tags in categories.items():
    key = list(tags.keys())[0]
    val = tags[key]
    
    query = f"""
    [out:json][timeout:25];
    area["ISO3166-1"="TR"][admin_level="2"]->.searchArea;
    (
      node["{key}"="{val}"](area.searchArea);
      way["{key}"="{val}"](area.searchArea);
      relation["{key}"="{val}"](area.searchArea);
    );
    out count;
    """
    
    try:
        response = requests.post(overpass_url, data={'data': query})
        data = response.json()
        count = data['elements'][0]['tags']['total']
        print(f"{name} ('{key}'='{val}'): {count} adet kayit.")
    except Exception as e:
        print(f"{name} cekilemedi: {e}")
