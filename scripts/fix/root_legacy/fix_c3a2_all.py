# -*- coding: utf-8 -*-
"""Fix C3 A2 E2 patterns"""
import os

root = r'c:\Users\batuf\Documents\GitHub\openroute\OpenRoutePlanner'

files = [
    'backend/route_config.py',
    'backend/app.py',
    'scripts/finetune/prepare_data.py',
]

# C3 A2 is "â" but mixed with other bytes
FIXES = [
    (b'\xc3\xa2', b'a'),  # â -> a (simple fix)
]

total_fixed = 0
for rel_path in files:
    path = os.path.join(root, rel_path)
    if not os.path.exists(path):
        continue
    
    with open(path, 'rb') as f:
        data = f.read()
    
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
