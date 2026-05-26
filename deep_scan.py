# -*- coding: utf-8 -*-
"""Deep scan for actual encoding corruption"""
import os

root = r'c:\Users\batuf\Documents\GitHub\openroute\OpenRoutePlanner'

# Corrupted pattern signatures (multi-byte that represents wrong encoding)
CORRUPT_PATTERNS = [
    b'\xc3\x82\xc2',   # Corrupted from C0-FF Latin-1
    b'\xc3\x83\xc2',   # Another corruption
    b'\xc3\x84\xc2',
    b'\xc3\x85\xc2',
    b'\xc3\xa2\xe2',   # â with following garbage
    b'\xe2\x82\xac',   # Euro sign issues
    b'\xe2\x80\x9c',   # Smart quotes
    b'\xe2\x80\x9d',
]

# Valid UTF-8 for Turkish characters (should NOT trigger false positive)
VALID_TURKISH = [
    b'\xc4\xb1',  # ı (dotless i)
    b'\xc4\xb0',  # İ (capital I with dot)
    b'\xc5\x9f',  # ş
    b'\xc5\x9e',  # Ş
    b'\xc4\x9f',  # ğ
    b'\xc3\xb6',  # ö
    b'\xc3\xbc',  # ü
    b'\xc3\xa7',  # ç
    b'\xc3\x87',  # Ç
    b'\xc3\x96',  # Ö
    b'\xc3\x9c',  # Ü
]

results = []

for dirpath, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in ['venv', 'venv_test', '__pycache__', '.git', 'chroma_db']]
    
    for f in files:
        if not f.endswith(('.py', '.js', '.html', '.json', '.md')):
            continue
        
        path = os.path.join(dirpath, f)
        try:
            with open(path, 'rb') as fh:
                data = fh.read()
            
            # Count potential corruptions
            corruptions = 0
            for pattern in CORRUPT_PATTERNS:
                corruptions += data.count(pattern)
            
            if corruptions > 0:
                results.append((corruptions, path))
        except:
            pass

results.sort(key=lambda x: -x[0])
print('FILES WITH ACTUAL MOJIBAKE:')
for count, path in results[:30]:
    print(f'{count:4}: {path}')
