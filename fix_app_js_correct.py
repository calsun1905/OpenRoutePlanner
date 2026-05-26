# -*- coding: utf-8 -*-
with open('frontend/js/app.js', 'rb') as f:
    data = f.read()

# More comprehensive fixes
# Common corrupted Turkish sequences
fixes = [
    # Corrupted Turkish patterns
    (b'\xc3\x85\xc5\xb8', b'\xc5\x9f'),  # se
    (b'\xc3\x84\xc2\x9f', b'\xc4\x9f'),  # g-breve
    (b'\xc3\x82\xc2\xb1', b'\xc4\xb1'),  # dotless-i
    (b'\xc3\x82\xc2\xb0', b'\xc4\xb0'),  # I-dot
    (b'\xc3\x82\xc2\xa7', b'\xc3\xa7'),  # c-cedilla
    (b'\xc3\x82\xc2\xb6', b'\xc3\xb6'),  # o-umlaut
    (b'\xc3\x82\xc2\xbc', b'\xc3\xbc'),  # u-umlaut
    (b'\xc3\x84\xc2\xb0', b'\xc3\xb0'),  # eth
    # 3-byte patterns
    (b'\xc3\x83\xc2\xb6', b'\xc3\xb6'),
    (b'\xc3\x83\xc2\xbc', b'\xc3\xbc'),
    (b'\xc3\x83\xc2\xa7', b'\xc3\xa7'),
    (b'\xc3\x83\xc2\xb1', b'\xc3\xb1'),
    # Quotes and special chars
    (b'\xe2\x80\x9c', b'"'),
    (b'\xe2\x80\x9d', b'"'),
    (b'\xe2\x82\xac', b' '),
    (b'\xe2\x80\x93', b'-'),
    (b'\xe2\x80\x94', b'--'),
    # Other patterns
    (b'\xc3\xa2\xe2\x82\xac', b'"'),
    (b'\xc3\xa2\xe2\x80\x9c', b'"'),
    (b'\xc3\xa2', b'\xc3\xa2'),
]

original = data
changed = 0
for bad, good in fixes:
    if bad in data:
        count = data.count(bad)
        data = data.replace(bad, good)
        changed += count
        print(f'Fixed {count}x: {bad.hex()}')

if changed > 0:
    with open('frontend/js/app.js', 'wb') as f:
        f.write(data)
    print(f'Total: {changed} bytes changed')
else:
    print('No corruptions found')
