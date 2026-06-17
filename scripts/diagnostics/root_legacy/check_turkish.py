# -*- coding: utf-8 -*-
with open('frontend/js/app.js', 'rb') as f:
    data = f.read()

# Search for Turkish patterns
searches = [
    (b'Hen', 'Hen'),
    (b'yok', 'yok'),
    (b'yeriniz', 'yeriniz'),
    (b'rota', 'rota'),
    (b'Kay', 'Kay'),
]

for pattern, name in searches:
    idx = data.find(pattern)
    if idx > 0:
        print(f'\n=== {name} found at {idx} ===')
        for i in range(idx, min(idx + 30, len(data))):
            b = data[i]
            c = chr(b) if 32 <= b < 127 else '?'
            print(f'{i}: 0x{b:02x} [{c}]')
    else:
        print(f'{name}: NOT FOUND')
