# -*- coding: utf-8 -*-
import os

with open('frontend/js/app.js', 'rb') as f:
    data = f.read()

idx = data.find(b'kay')
if idx > 0:
    print('app.js kay found at', idx)
    for i in range(idx, min(idx + 50, len(data))):
        b = data[i]
        c = chr(b) if 32 <= b < 127 else '?'
        print(f'{i}: 0x{b:02x} ({b}) [{c}]')

# Also search for corruption patterns
for pattern in [b'\xc3', b'\xc4', b'\xe2']:
    idx = data.find(pattern)
    if idx > 0:
        print(f'\nFound 0x{pattern.hex()} at {idx}')
        for i in range(idx, min(idx + 10, len(data))):
            b = data[i]
            c = chr(b) if 32 <= b < 127 else '?'
            print(f'  {i}: 0x{b:02x} [{c}]')
