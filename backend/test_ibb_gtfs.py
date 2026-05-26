import requests
import re

# CKAN API kullanarak package'e erisim
url = 'https://data.ibb.gov.tr/api/3/action/package_show?id=public-transport-gtfs-data'
print(f'Trying CKAN API: {url}')

try:
    response = requests.get(url, timeout=30)
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        import json
        data = response.json()
        if data.get('result'):
            resources = data['result'].get('resources', [])
            print(f'Resources found: {len(resources)}')
            for r in resources[:5]:
                print(f"  - {r.get('name', 'unnamed')}: {r.get('url', '')}")
        else:
            print('No result in response')
    else:
        print(f'Response: {response.text[:500]}')
except Exception as e:
    print(f'Error: {e}')

# Dogrudan download sayfasini dene
url2 = 'https://data.ibb.gov.tr/dataset/public-transport-gtfs-data'
print(f'\nTrying direct page: {url2}')
try:
    response = requests.get(url2, timeout=30)
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        print(f'Content length: {len(response.text)} bytes')
        # Resource linklerini bul
        links = re.findall(r'href="([^"]*resource[^"]*download[^"]*)"', response.text)
        if links:
            print(f'Resource links: {links[:5]}')
except Exception as e:
    print(f'Error: {e}')