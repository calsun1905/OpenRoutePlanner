# -*- coding: utf-8 -*-
import re

with open('frontend/js/app.js', 'rb') as f:
    data = f.read()

# Find all C3 XX C2 YY patterns (corruptions)
matches = list(re.finditer(b'\xc3[\x80-\xbf]\xc2[\x80-\xbf]', data))
print('Total C3 XX C2 YY patterns:', len(matches))

if matches:
    print('\nFirst 20 patterns:')
    for m in matches[:20]:
        start = m.start()
        seq = data[start:start+3]
        try:
            decoded = seq.decode('utf-8')
        except:
            decoded = '?'
        print(f'  {start}: {seq.hex()} -> [{decoded}]')
