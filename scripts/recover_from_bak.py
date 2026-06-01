# -*- coding: utf-8 -*-
"""
Recover encoding from .bak files using multiple decode/transform heuristics.
"""
import os
import sys

TARGETS = [
    ("backend/app.py.bak", "backend/app.py"),
]

TURKISH_CHARS = set("ğ�ş�?�?ĞÜŞÇÖ?âîÂÎ")

TRANSFORMS = []

def t_utf8(raw):
    try:
        return raw.decode('utf-8')
    except Exception:
        return raw.decode('utf-8', errors='replace')

def t_latin1(raw):
    return raw.decode('latin-1')

def t_cp1254(raw):
    try:
        return raw.decode('cp1254')
    except Exception:
        return raw.decode('latin-1', errors='replace')

# fix mojibake like "�" -> "�"
def fix_mojibake_roundtrip(s: str) -> str:
    try:
        return s.encode('latin-1', errors='replace').decode('utf-8', errors='replace')
    except Exception:
        return s

# compose helper
TRANSFORMS.append(lambda b: t_utf8(b))
TRANSFORMS.append(lambda b: fix_mojibake_roundtrip(t_utf8(b)))
TRANSFORMS.append(lambda b: t_latin1(b))
TRANSFORMS.append(lambda b: fix_mojibake_roundtrip(t_latin1(b)))
TRANSFORMS.append(lambda b: t_cp1254(b))
TRANSFORMS.append(lambda b: fix_mojibake_roundtrip(t_cp1254(b)))

REPLACEMENTS = [
    ("�", "�"), ("�", "�"), ("?", "?"), ("�", "�"), ("ÅŸ", "ş"), ("Ü", "Ü"), ("Ö", "Ö"), ("Ç", "Ç"),
    ("Â", ""), ("Ã‚", "Â"), ("â€™", "'"), ("â€?", "-"), ("â€œ", '"'), ("â€", '"'), ("â€", '"'),
]


def score_text(s: str) -> int:
    # score by number of turkish chars and number of non-ASCII letters
    turk = sum(1 for c in s if c in TURKISH_CHARS)
    non_ascii = sum(1 for c in s if ord(c) > 127)
    # penalize replacement char
    repl = s.count('\ufffd')
    return turk * 10 + non_ascii - repl * 20


def apply_replacements(s: str) -> str:
    out = s
    for a, b in REPLACEMENTS:
        out = out.replace(a, b)
    return out


def recover(bak_path, out_path):
    if not os.path.exists(bak_path):
        print(f"SKIP missing: {bak_path}")
        return False
    raw = open(bak_path, 'rb').read()
    candidates = []
    for t in TRANSFORMS:
        try:
            c = t(raw)
        except Exception as e:
            c = ''
        c = apply_replacements(c)
        candidates.append(c)

    best = max(candidates, key=lambda s: score_text(s))

    # backup existing target
    if os.path.exists(out_path):
        prebak = out_path + '.prebak'
        if not os.path.exists(prebak):
            with open(out_path, 'rb') as f:
                open(prebak, 'wb').write(f.read())
            print(f'WROTE backup: {prebak}')

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(best)
    print(f'RECOVERED: {out_path}')
    return True


def main():
    base = os.path.dirname(os.path.dirname(__file__))
    ok = False
    for bak_rel, out_rel in TARGETS:
        bak = os.path.normpath(os.path.join(base, bak_rel))
        out = os.path.normpath(os.path.join(base, out_rel))
        try:
            if recover(bak, out):
                ok = True
        except Exception as e:
            print('ERROR', e)
    if not ok:
        return 2
    return 0

if __name__ == '__main__':
    sys.exit(main())
