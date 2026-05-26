# -*- coding: utf-8 -*-
"""Fix all remaining files"""
import os

root = r'c:\Users\batuf\Documents\GitHub\openroute\OpenRoutePlanner'

# Corrupt patterns to fix
FIXES = [
    (b'\xc3\x82\xc2\xb1', b'\xc4\xb1'),  # ı
    (b'\xc3\x82\xc2\xb0', b'\xc4\xb0'),  # İ
    (b'\xc3\x82\xc2\xa7', b'\xc3\xa7'),  # ç
    (b'\xc3\x82\xc2\xb6', b'\xc3\xb6'),  # ö
    (b'\xc3\x82\xc2\xbc', b'\xc3\xbc'),  # ü
    (b'\xc3\x82\xc2\x84', b'\xc3\x84'),  # Ä
    (b'\xc3\x82\xc2\x96', b'\xc3\x96'),  # Ö
    (b'\xc3\x82\xc2\x9c', b'\xc3\x9c'),  # Ü
    (b'\xc3\x82\xc2\x87', b'\xc3\x87'),  # Ç
    (b'\xc3\x83\xc2\xa7', b'\xc3\xa7'),  # ç
    (b'\xc3\x83\xc2\xb6', b'\xc3\xb6'),  # ö
    (b'\xc3\x83\xc2\xbc', b'\xc3\xbc'),  # ü
    (b'\xc3\x83\xc2\xb1', b'\xc3\xb1'),  # ı -> should be ı
    (b'\xc3\x85\xc2\xb8', b'\xc5\x9f'),  # ş
    (b'\xc3\x85\xc2\x9e', b'\xc5\x9e'),  # Ş
    (b'\xe2\x80\x9c', b'"'),
    (b'\xe2\x80\x9d', b'"'),
    (b'\xe2\x82\xac', b' '),
]

files = [
    'backend/route_config.py',
    'backend/geocoder.py',
    'backend/app.py',
    'backend/text_utils.py',
    'scripts/finetune/prepare_data.py',
]

total_fixed = 0
for rel_path in files:
    path = os.path.join(root, rel_path)
    if not os.path.exists(path):
        continue
    
    with open(path, 'rb') as f:
        data = f.read()
    
    original = data
    fixed = 0
    for bad, good in FIXES:
        if bad in data:
            count = data.count(bad)
            data = data.replace(bad, good)
            fixed += count
    
    if fixed > 0:
        with open(path, 'wb') as f:
            f.write(data)
        print(f'FIXED {fixed}x: {rel_path}')
        total_fixed += fixed
    else:
        print(f'OK: {rel_path}')

print(f'\nTotal: {total_fixed} patterns fixed')
