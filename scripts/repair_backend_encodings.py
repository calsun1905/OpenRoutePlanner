# -*- coding: utf-8 -*-
"""
Try multiple decode/transform heuristics on backend .py files and pick best-scored candidate.
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(__file__))
BACKEND_DIR = os.path.join(BASE, 'backend')

TURKISH_CHARS = set("ğ�ş�?�?ĞÜŞÇÖ?âîÂÎ")

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

def fix_mojibake_roundtrip(s: str) -> str:
    try:
        return s.encode('latin-1', errors='replace').decode('utf-8', errors='replace')
    except Exception:
        return s

TRANSFORMS = [
    lambda b: t_utf8(b),
    lambda b: fix_mojibake_roundtrip(t_utf8(b)),
    lambda b: t_latin1(b),
    lambda b: fix_mojibake_roundtrip(t_latin1(b)),
    lambda b: t_cp1254(b),
    lambda b: fix_mojibake_roundtrip(t_cp1254(b)),
]

REPLACEMENTS = [
    ("�", "�"), ("�", "�"), ("?", "?"), ("�", "�"), ("ÅŸ", "ş"), ("Ü", "Ü"), ("Ö", "Ö"), ("Ç", "Ç"),
    ("Â", ""), ("â€™", "'"), ("â€?", "-"), ("â€œ", '"'), ("â€", '"'), ("â€", '"'),
]


def score_text(s: str) -> int:
    turk = sum(1 for c in s if c in TURKISH_CHARS)
    non_ascii = sum(1 for c in s if ord(c) > 127)
    repl = s.count('\ufffd')
    return turk * 10 + non_ascii - repl * 20


def apply_replacements(s: str) -> str:
    out = s
    for a, b in REPLACEMENTS:
        out = out.replace(a, b)
    return out


def process_file(path: str) -> bool:
    try:
        raw = open(path, 'rb').read()
    except Exception as e:
        print('READ ERR', path, e)
        return False

    candidates = []
    for t in TRANSFORMS:
        try:
            c = t(raw)
        except Exception:
            c = ''
        c = apply_replacements(c)
        candidates.append(c)

    best = max(candidates, key=lambda s: score_text(s))
    current = None
    try:
        current = open(path, 'r', encoding='utf-8', errors='replace').read()
    except Exception:
        current = ''

    if best and best != current and score_text(best) > score_text(current):
        pre = path + '.prebak2'
        if not os.path.exists(pre):
            open(pre, 'wb').write(raw)
            print('Backup written:', pre)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(best)
        print('Fixed:', path)
        return True
    return False


def main():
    changed = 0
    for fname in os.listdir(BACKEND_DIR):
        if not fname.endswith('.py'):
            continue
        path = os.path.join(BACKEND_DIR, fname)
        if process_file(path):
            changed += 1
    print('Done. Changed:', changed)
    return 0

if __name__ == '__main__':
    sys.exit(main())
