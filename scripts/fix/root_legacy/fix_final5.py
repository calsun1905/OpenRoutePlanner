# -*- coding: utf-8 -*-
with open('frontend/js/app.js', 'rb') as f:
    data = f.read()

FIXES = [
    (b'\xc3\xaf\xc2\xb8', b'\xc3\xb8'),  # ø
    (b'\xc3\x85\xc2\xbe', b'\xc3\xbe'),  # þ
    (b'\xc3\x82\xc2\xa6', b'\xc3\xa6'),  # æ
    (b'\xc3\x82\xc2\xa2', b'\xc3\xa2'),  # â
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
