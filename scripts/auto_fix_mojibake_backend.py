#!/usr/bin/env python3
"""
Auto-fix common mojibake issues in OpenRoutePlanner/backend Python files.
- Backs up each file to <file>.bak
- Tries several decode/encode heuristics and picks the one that reduces mojibake tokens
- Edits files in-place when improvement is detected

Run from repository root:
    OpenRoutePlanner\.venv\Scripts\python.exe OpenRoutePlanner\scripts\auto_fix_mojibake_backend.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Directories to scan (expandable)
DIRS_TO_SCAN = [ROOT / "backend", ROOT / "scripts", ROOT / "frontend", ROOT / "artifacts"]

# Include the Unicode replacement char \ufffd to catch files that show ?
MOJIBAKE_RE = re.compile(r'[???????????\u00c3\u00c2\uFFFD]')

# File extensions we'll attempt to auto-fix. Backups are created for safety.
CANDIDATE_EXT = ['.py', '.md', '.csv', '.jsonl', '.js', '.ts']

strategies = []

# Strategy functions: accept text, return fixed_text

def identity(s):
    return s

strategies.append(('identity', identity))

# Strategy: interpret as latin-1 bytes then decode as utf-8
def latin1_to_utf8(s):
    try:
        b = s.encode('latin-1', errors='replace')
        return b.decode('utf-8', errors='replace')
    except Exception:
        return s
strategies.append(('latin1->utf8', latin1_to_utf8))

# Strategy: encode utf-8 bytes then decode latin-1 (reverse)
def utf8_to_latin1(s):
    try:
        b = s.encode('utf-8', errors='replace')
        return b.decode('latin-1', errors='replace')
    except Exception:
        return s
strategies.append(('utf8->latin1', utf8_to_latin1))

# Strategy: do a common sequence replacement map
REPLACEMENTS = [
    ('??�', '?'), ('??�', '?'), ('??�', '?'), ('??�', '?'), ('??�', '?'), ('??�', '?'),
    ('???', '?'), ('????', '?'), ('????', '?'), ('??�', '?'), ('??�', '?'), ('?? ', '?'),
    ('???', '?'), ('??', '?'), ('??', '?'), ('??', '?'), ('??', '?'), ('??', '?')
]

def replacements_map(s):
    r = s
    for a,b in REPLACEMENTS:
        r = r.replace(a,b)
    return r
strategies.append(('map-replace', replacements_map))

# Utility to score how "mojibakey" a string is (count occurrences of suspicious sequences)
SUSPICIOUS = re.compile(r'?\W|?[\w]|?|?|?|?|?')

def score(s):
    return len(SUSPICIOUS.findall(s))


def try_fix(text):
    best = text
    best_score = score(text)
    best_name = 'identity'
    for name, fn in strategies:
        try:
            cand = fn(text)
        except Exception:
            cand = text
        sc = score(cand)
        if sc < best_score:
            best = cand
            best_score = sc
            best_name = name
        # Also try applying the replacements map on top of this candidate
        try:
            cand_mapped = replacements_map(cand)
        except Exception:
            cand_mapped = cand
        sc2 = score(cand_mapped)
        if sc2 < best_score:
            best = cand_mapped
            best_score = sc2
            best_name = f"{name}+map-replace"
    return best_name, best, best_score


def process_file(path: Path, dry_run=False):
    txt = path.read_text(encoding='utf-8', errors='replace')
    if not MOJIBAKE_RE.search(txt):
        return False, 'no_match'
    name, fixed, sc = try_fix(txt)
    if fixed == txt:
        return False, 'no_change'
    # safety: avoid changing code structure lines that look like shebangs or non-comment ascii-only
    # We'll backup and write fixed file
    bak = path.with_suffix(path.suffix + '.bak')
    bak.write_text(txt, encoding='utf-8')
    if not dry_run:
        path.write_text(fixed, encoding='utf-8')
    return True, name


def main():
    changed = []
    scanned = 0
    for base in DIRS_TO_SCAN:
        if not base.exists():
            # skip missing dirs
            continue
        for ext in CANDIDATE_EXT:
            for p in sorted(base.rglob(f'*{ext}')):
                scanned += 1
                ok, reason = process_file(p, dry_run=False)
                if ok:
                    changed.append((p, reason))
                else:
                    # no change or no match
                    pass
    print(f"Scanned {scanned} files. Modified {len(changed)} files.")
    for p, reason in changed:
        print(f"Fixed: {p} (by {reason})")
    return 0

if __name__ == '__main__':
    sys.exit(main())
