# -*- coding: utf-8 -*-
with open('frontend/js/app.js', 'rb') as f:
    data = f.read()

# Positions found
positions = [18445, 48095, 48138, 48214, 49163]

for pos in positions:
    if pos + 4 <= len(data):
        seq = data[pos:pos+4]
        print(f'Position {pos}: {seq.hex()} len={len(seq)}')
    else:
        print(f'Position {pos}: not enough data')
