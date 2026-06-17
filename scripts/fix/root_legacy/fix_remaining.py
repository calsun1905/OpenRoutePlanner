# -*- coding: utf-8 -*-
"""Fix remaining C3 XX C2 YY patterns"""
with open('frontend/js/app.js', 'rb') as f:
    data = f.read()

FIXES = [
    (b'\xc3\x82\xc2\x9e', b'\xc5\x9e'),  # Ş
    (b'\xc3\x82\xc2\xb8', b'\xc5\x9f'),  # ş
    (b'\xc3\x85\xc2\xb8', b'\xc5\x9f'),  # ş
    (b'\xc3\x85\xc2\x9e', b'\xc5\x9e'),  # Ş
    (b'\xc3\xaf\xc2\xbf', b'\xc3\xbf'),  # ÿ
]

total = 0
for bad, good in FIXES:
    if bad in data:
        count = data.count(bad)
        data = data.replace(bad, good)
        total += count
        print(f'Fixed {count}x: {bad.hex()}')

if total > 0:
    with open('frontend/js/app.js', 'wb') as f:
        f.write(data)
    print(f'Total: {total} fixed')
else:
    print('No patterns found')
