#!/usr/bin/env python
"""Transit sistemi testi - ornek rotalar"""

import sys
sys.path.insert(0, '.')

from multimodal_engine import _build_graph_metro_option

print("=" * 60)
print("Istanbul Transit Sistemi Testi")
print("=" * 60)

# Test senaryolari
test_cases = [
    {
        "name": "Taksim -> Kadikoy (M4 hatti)",
        "origin_lat": 41.0388,
        "origin_lon": 28.9889,
        "dest_lat": 40.9903,
        "dest_lon": 29.0291,
    },
    {
        "name": "Sishane -> Levent (M2 hatti)",
        "origin_lat": 41.0550,
        "origin_lon": 29.0150,
        "dest_lat": 41.0850,
        "dest_lon": 29.0200,
    },
    {
        "name": "Kadikoy -> Bostanci (M4 hatti)",
        "origin_lat": 40.9903,
        "origin_lon": 29.0291,
        "dest_lat": 40.9878,
        "dest_lon": 29.0286,
    },
]

for i, tc in enumerate(test_cases, 1):
    print(f"\n{i}. {tc['name']}")
    print(f"   Baslangic: {tc['origin_lat']}, {tc['origin_lon']}")
    print(f"   Hedef: {tc['dest_lat']}, {tc['dest_lon']}")
    
    result = _build_graph_metro_option(
        origin_lat=tc['origin_lat'],
        origin_lon=tc['origin_lon'],
        dest_lat=tc['dest_lat'],
        dest_lon=tc['dest_lon'],
        direct_walk_min=120,
        direct_walk_m=10000,
    )
    
    if result:
        print(f"   OK: Rota bulundu!")
        print(f"   Rota adi: {result.get('name')}")
        print(f"   Toplam sure: {result.get('total_time_min')} dk")
        print(f"   Aktarma: {result.get('transfer_count')}")
        print(f"   Segment sayisi: {len(result.get('segments', []))}")
        
        for j, seg in enumerate(result.get('segments', [])):
            mode = seg.get('mode')
            desc = seg.get('description', '')
            coords_count = len(seg.get('coords', []))
            print(f"      Segment {j+1}: [{mode.upper()}] {desc} ({coords_count} koordinat)")
    else:
        print(f"   HATA: Metro rotasi bulunamadi")

print("\n" + "=" * 60)
print("Test tamamlandi")
print("=" * 60)