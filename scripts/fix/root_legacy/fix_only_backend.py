# -*- coding: utf-8 -*-
"""Fix remaining backend files only"""
import os

root = r'c:\Users\batuf\Documents\GitHub\openroute\OpenRoutePlanner'

files = [
    'backend/route_config.py',
    'backend/app.py',
    'scripts/finetune/prepare_data.py',
]

# Fix C3 83 C2 XX patterns
FIXES = [
    (b'\xc3\x83\xc2\xa0', b'\xc3\xa0'), (b'\xc3\x83\xc2\xa1', b'\xc3\xa1'),
    (b'\xc3\x83\xc2\xa2', b'\xc3\xa2'), (b'\xc3\x83\xc2\xa3', b'\xc3\xa3'),
    (b'\xc3\x83\xc2\xa4', b'\xc3\xa4'), (b'\xc3\x83\xc2\xa5', b'\xc3\xa5'),
    (b'\xc3\x83\xc2\xa6', b'\xc3\xa6'), (b'\xc3\x83\xc2\xa7', b'\xc3\xa7'),
    (b'\xc3\x83\xc2\xa8', b'\xc3\xa8'), (b'\xc3\x83\xc2\xa9', b'\xc3\xa9'),
    (b'\xc3\x83\xc2\xaa', b'\xc3\xaa'), (b'\xc3\x83\xc2\xab', b'\xc3\xab'),
    (b'\xc3\x83\xc2\xac', b'\xc3\xac'), (b'\xc3\x83\xc2\xad', b'\xc3\xad'),
    (b'\xc3\x83\xc2\xae', b'\xc3\xae'), (b'\xc3\x83\xc2\xaf', b'\xc3\xaf'),
    (b'\xc3\x83\xc2\xb0', b'\xc3\xb0'), (b'\xc3\x83\xc2\xb1', b'\xc3\xb1'),
    (b'\xc3\x83\xc2\xb2', b'\xc3\xb2'), (b'\xc3\x83\xc2\xb3', b'\xc3\xb3'),
    (b'\xc3\x83\xc2\xb4', b'\xc3\xb4'), (b'\xc3\x83\xc2\xb5', b'\xc3\xb5'),
    (b'\xc3\x83\xc2\xb6', b'\xc3\xb6'), (b'\xc3\x83\xc2\xb7', b'\xc3\xb7'),
    (b'\xc3\x83\xc2\xb8', b'\xc3\xb8'), (b'\xc3\x83\xc2\xb9', b'\xc3\xb9'),
    (b'\xc3\x83\xc2\xba', b'\xc3\xba'), (b'\xc3\x83\xc2\xbb', b'\xc3\xbb'),
    (b'\xc3\x83\xc2\xbc', b'\xc3\xbc'), (b'\xc3\x83\xc2\xbd', b'\xc3\xbd'),
    (b'\xc3\x83\xc2\xbe', b'\xc3\xbe'), (b'\xc3\x83\xc2\xbf', b'\xc3\xbf'),
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
