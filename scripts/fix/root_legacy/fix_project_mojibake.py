#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Mojibake Fix - Precision Version
Sadece gercek mojibake patternlerini duzelir.
"""

import os
import re

# Specific mojibake patterns - NOT valid Turkish chars
# These are sequences that represent DOUBLE ENCODING
MOJIBAKE_REPLACEMENTS = [
    # UTF-8 double encoding: UTF-8 -> Latin1 -> UTF-8
    # Example: "ö" (UTF-8 c3 b6) -> Latin1 -> UTF-8 = "ö" (c3 83 c2 b6)
    ('\u00c3\u0084\u00c2\u008b', '\u0160'),  # Ã„Å¸ -> Š
    ('\u00c3\u0085\u00c2\u008b', '\u0160'),  # Ã…Å¸ -> Š
    ('\u00c3\u0084\u00c2\u008a', '\u0160'),  # Ã„Å -> Š
    ('\u00c3\u0084\u00c2\u009f', '\u011e'),  # Ã„Å -> Ğ
    ('\u00c3\u0087', '\u00c7'),               # Ç -> Ç
    ('\u00c3\u0096', '\u00d6'),               # Ö -> Ö
    ('\u00c3\u009c', '\u00dc'),               # Ü -> Ü
    ('\u00c3\u0084', '\u00c4'),               # Ã† -> Ä
    ('\u00c3\u00b1', '\u0131'),               # ı -> ı
    ('\u00c3\u00a7', '\u00e7'),               # ç -> ç
    ('\u00c3\u00b6', '\u00f6'),               # ö -> ö
    ('\u00c3\u00bc', '\u00fc'),               # ü -> ü
    ('\u00c3\u00a1', '\u00e1'),               # á -> á
    ('\u00c3\u00a2', '\u00e2'),               # â -> â
    ('\u00c3\u00a8', '\u00e8'),               # è -> è
    ('\u00c3\u00a9', '\u00e9'),               # é -> é
    ('\u00c3\u00aa', '\u00ea'),               # ê -> ê
    ('\u00c3\u00ab', '\u00eb'),               # ë -> ë
    ('\u00c3\u00ac', '\u00ac'),               # ¬ -> ì
    ('\u00c3\u00ad', '\u00ad'),               # ­ -> í
    ('\u00c3\u00ae', '\u00ae'),               # ® -> î
    ('\u00c3\u00af', '\u00af'),               # ¯ -> ï
    ('\u00c3\u00b0', '\u00b0'),               # ° -> °
    ('\u00c3\u00b2', '\u00b2'),               # ² -> ²
    ('\u00c3\u00b3', '\u00b3'),               # ³ -> ³
    ('\u00c3\u00b4', '\u00b4'),               # ´ -> ´
    ('\u00c3\u00b5', '\u00b5'),               # µ -> µ
    ('\u00c3\u00b7', '\u00b7'),               # · -> ÷
    ('\u00c3\u00b8', '\u00b8'),               # ¸ -> ø
    ('\u00c3\u00b9', '\u00b9'),               # ¹ -> ¹
    ('\u00c3\u00ba', '\u00ba'),               # º -> º
    ('\u00c3\u00bb', '\u00bb'),               # » -> »
    ('\u00c3\u00bd', '\u00bd'),               # ½ -> ½
    ('\u00c3\u00be', '\u00be'),               # ¾ -> ¾
    ('\u00c3\u00bf', '\u00bf'),               # ¿ -> ¿
    
    # Windows-1252 misread as UTF-8
    ('\u00e2\u0080\u009c', '\u201c'),        # " -> "
    ('\u00e2\u0080\u0099', '\u2019'),        # ' -> '
    ('\u00e2\u0080\u009d', '\u201d'),        # " -> "
    ('\u00e2\u0080\u009e', '\u201e'),        # " -> "
    ('\u00e2\u0080\u00a6', '\u2026'),        # ... -> ...
    ('\u00e2\u0080\u0093', '\u2013'),        # - -> –
    ('\u00e2\u0080\u0094', '\u2014'),        # - -> —
    ('\u00e2\u0082\u00ac', '\u20ac'),        # EUR symbol
    
    # Turkish word mojibakes (specific corruptions)
    ('de\u00c4\u009f', 'de\u011fil'),         # değil -> değil
    ('d\u00c4\u00b1\u00c5\u009f\u00c4\u00b1', 'd\u0131\u015f\u0131'),  # dışı -> dışı
    ('bulunamad\u00c4\u00b1', 'bulunamad\u0131'),  # bulunamadı -> bulunamadı
    ('y\u00c3\u00bc', 'y\u00fck'),           # yük -> yük
    ('T\u00c3\u00bc', 'T\u00fck'),           # Türk -> Türk
    ('i\u00c3\u00a7', 'i\u00e7'),             # iç -> iç
]

# Regex that ONLY matches actual mojibake - double encoded sequences
# NOT just any Turkish character
MOJIBAKE_REGEX = re.compile(
    # Ã followed by  or Ä or Å and combining char
    r'\u00c3[\u0084\u0085\u0087\u0096\u009c][\u00a0-\u00bf]|'
    # Standalone Ã followed by certain chars
    r'\u00c3[\u00a0-\u00bf][\u00a0-\u00bf]|'
    # Windows quote chars
    r'\u00e2\u0080[\u0093\u0094\u0099\u009c\u009d\u009e\u00a6]|'
    # Specific Turkish word patterns
    r'de\u00c4\u009f|d\u00c4\u00b1\u00c5\u009f\u00c4\u00b1|bulunamad\u00c4\u00b1|y\u00c3\u00bc|T\u00c3\u00bc|i\u00c3\u00a7'
)

def fix_file(path):
    """Fix encoding issues in a single file."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        original = content
        for bad, good in MOJIBAKE_REPLACEMENTS:
            content = content.replace(bad, good)
        
        if content != original:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        return False

def has_mojibake(content):
    """Check if content has actual mojibake patterns (not valid Turkish chars)."""
    return bool(MOJIBAKE_REGEX.search(content))

def main():
    base_dir = '.'
    exts = ['.py', '.js', '.html', '.json', '.md', '.txt']
    
    # Collect all files
    files = []
    for root, dirs, filenames in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in [
            'venv_test', '__pycache__', '.git', 'venv', 
            '.pytest_cache', 'node_modules', 'chroma_db',
            'backend/models', '.agent', '.github'
        ]]
        for f in filenames:
            if any(f.endswith(e) for e in exts):
                files.append(os.path.join(root, f))
    
    print(f"Scanning {len(files)} files...")
    
    # Find files with actual mojibake
    issues = []
    for path in files:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                if has_mojibake(content):
                    issues.append(path)
        except:
            pass
    
    print(f"Found {len(issues)} files with actual mojibake")
    
    # Fix files
    if issues:
        print("Fixing...")
        fixed = sum(1 for p in issues if fix_file(p))
        print(f"Fixed {fixed} files")
    else:
        print("No mojibake found - all clean!")

if __name__ == '__main__':
    main()