# -*- coding: utf-8 -*-
import os, sys
base = os.path.dirname(os.path.dirname(__file__))
path = os.path.join(base, 'backend', 'app.py')
if not os.path.exists(path):
    print('missing', path); sys.exit(1)
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    txt = f.read()
orig = txt
try:
    repaired = txt.encode('latin-1', errors='replace').decode('utf-8', errors='replace')
except Exception as e:
    repaired = txt
if repaired != orig:
    bak = path + '.roundtripbak'
    with open(bak, 'w', encoding='utf-8') as f:
        f.write(orig)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(repaired)
    print('WROTE', path)
else:
    print('No change')
