import requests

# İBB GTFS URLs - farklı formatlar
urls = [
    "https://data.ibb.gov.tr/dataset/gtfs-data/resource/0c8e2c10-83d8-4b0e-9f0a-3e6f8c9d7b2a/download",
    "https://data.ibb.gov.tr/dataset/gtfs-data/resource/gtfs-static/download",
    "https://data.ibb.gov.tr/api/3/action/package_show?id=gtfs-data",
]

for url in urls:
    print(f"Trying: {url}")
    try:
        response = requests.get(url, timeout=30, stream=True)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Content-Length: {response.headers.get('Content-Length', 'unknown')}")
            print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
            # Check if it's a zip file
            content = response.content[:100]
            if content[:4] == b'PK\x03\x04':
                print("Valid ZIP file!")
            else:
                print(f"First 100 chars: {content[:100]}")
    except Exception as e:
        print(f"Error: {e}")
    print()

# İBB ana sayfasını kontrol et
print("Checking data.ibb.gov.tr main page...")
try:
    response = requests.get("https://data.ibb.gov.tr/dataset/gtfs-data", timeout=30)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        # GTFS ile ilgili linkleri ara
        import re
        links = re.findall(r'href="([^"]*gtfs[^"]*)"', response.text, re.IGNORECASE)
        print(f"GTFS related links: {links[:10]}")
except Exception as e:
    print(f"Error: {e}")