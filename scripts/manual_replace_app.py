# -*- coding: utf-8 -*-
"""
Apply targeted manual replacements in backend/app.py for remaining mojibake tokens.
"""
import os
p = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', 'app.py')
if not os.path.exists(p):
    print('missing', p); raise SystemExit(1)
with open(p, 'r', encoding='utf-8', errors='replace') as f:
    s = f.read()
orig = s
REPL = [
    ('g???zergah', 'g?zergah'),
    ('g???ncel', 'g?ncel'),
    ('metrob???s', 'metrob?s'),
    ('otob???s', 'otob?s'),
    ('m???ze', 'm?ze'),
    ('???sk???dar', '?sk?dar'),
    ('kad?k???y', 'kad?k?y'),
    ('ka???', 'ka?'),
    ('a????k', 'a??k'),
    ('y???klendi', 'y?klendi'),
    ('mod???l???', 'mod?l'),
    ('Ba??????lat', 'Ba?lat'),
    ('Ba??????lat?????l?????yor', 'Ba?lat?l?yor'),
    ('tamamland?????', 'tamamland?'),
    ('hatas?????', 'hatas?'),
    ('donan?????m', 'donan?m'),
    ('s?????n?????rlar', 's?n?rlar'),
    ('g???zergah', 'g?zergah'),
]
for a,b in REPL:
    s = s.replace(a, b)
if s != orig:
    bak = p + '.prebak3'
    if not os.path.exists(bak):
        with open(bak, 'w', encoding='utf-8') as f:
            f.write(orig)
        print('WROTE BACKUP', bak)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(s)
    print('APPLIED replacements to', p)
else:
    print('No changes needed')
