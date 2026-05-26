# -*- coding: utf-8 -*-
"""
UTF-8 Mojibake Fixer - Comprehensive Version
Fixes all layers of mojibake encoding issues
"""
import os
import re

# Byte-level replacements for triple-layer mojibake
# Pattern: original char encoded as UTF-8, then as Latin-1, then decoded as UTF-8
BYTE_MOJIBAKE_MAP = [
    # Triple-layer Turkish chars
    (b'\xc3\x83\xc2\xb6', b'\xc3\xb6'),  # ö
    (b'\xc3\x83\xc2\xbc', b'\xc3\xbc'),  # ü
    (b'\xc3\x83\xc2\xa7', b'\xc3\xa7'),  # ç
    (b'\xc3\x83\xc2\xa0', b'\xc3\xa0'),  # à (space sometimes)
    (b'\xc3\x83\xc2\xb0', b'\xc3\xb0'),  # ð (used as ı)
    (b'\xc3\x84\xc2\xb1', b'\xc4\xb1'),  # ı
    (b'\xc3\x84\xc2\xb0', b'\xc4\xb0'),  # İ
    (b'\xc3\x84\xc5\xb8', b'\xc4\x9f'),  # ğ
    (b'\xc3\x85\xc2\xb8', b'\xc5\x9f'),  # ş
    (b'\xc3\x85\xc2\x9e', b'\xc5\x9e'),  # Ş
    (b'\xc3\x83\xc2\x86', b'\xc3\x86'),  # Æ
    (b'\xc3\x83\xc2\x84', b'\xc3\x84'),  # Ä
    (b'\xc3\x83\xc2\x96', b'\xc3\x96'),  # Ö
    (b'\xc3\x83\xc2\x9c', b'\xc3\x9c'),  # Ü
    (b'\xc3\x83\xc2\x87', b'\xc3\x87'),  # Ç
    (b'\xc3\x83\xc2\x8d', b'\xc3\x8d'),  # Í
    (b'\xc3\x83\xc2\x8c', b'\xc3\x8c'),  # Í
    (b'\xc3\x83\xc2\x8e', b'\xc3\x8e'),  # Î
    (b'\xc3\x83\xc2\x8f', b'\xc3\x8f'),  # Ï
    (b'\xc3\x83\xc2\x90', b'\xc3\x90'),  # Ð
    (b'\xc3\x83\xc2\x91', b'\xc3\x91'),  # Ñ
    (b'\xc3\x83\xc2\x92', b'\xc3\x92'),  # Ò
    (b'\xc3\x83\xc2\x93', b'\xc3\x93'),  # Ó
    (b'\xc3\x83\xc2\x94', b'\xc3\x94'),  # Ô
    (b'\xc3\x83\xc2\x95', b'\xc3\x95'),  # Õ
    (b'\xc3\x83\xc2\x98', b'\xc3\x98'),  # Ø
    (b'\xc3\x83\xc2\x99', b'\xc3\x99'),  # Ù
    (b'\xc3\x83\xc2\x9a', b'\xc3\x9a'),  # Ú
    (b'\xc3\x83\xc2\x9b', b'\xc3\x9b'),  # Ü
    (b'\xc3\x83\xc2\x9d', b'\xc3\x9d'),  # Ý
    # Other corrupted bytes
    (b'\xc3\xa2\xe2\x82\xac\xe2\x80\x9d', b"---"),  # â¬ -> garbage
    (b'\xe2\x80\x9e', b'"'),           # fancy open quote
    (b'\xe2\x80\x9c', b'"'),           # fancy close quote
    (b'\xe2\x82\xac', b'EUR'),         # euro sign
    (b'\xc3\xa2', b'a'),               # â
    (b'\xc2\xa0', b' '),               # non-breaking space
]

# Text-level replacements for remaining mojibake
TEXT_MOJIBAKE_MAP = [
    # Triple-layer text patterns
    ('ÃƒÂ¶', 'ö'),
    ('ÃƒÂ¼', 'ü'),
    ('ÃƒÂ§', 'ç'),
    ('ÃƒÂ±', 'ı'),
    ('ÃƒÂ ', 'İ'),
    ('ÃƒÂ¨', 'è'),
    ('ÃƒÂ©', 'é'),
    ('ÃƒÂª', 'ê'),
    ('ÃƒÂ¶', 'ö'),
    ('ÃƒÂ¼', 'ü'),
    # Double-layer text patterns
    ('kàƒÂ¶pràƒÂ¼', 'köprü'),
    ('saàƒÂ¸lar', 'sağlar'),
    ('iàƒÂ§', 'iç'),
    ('deà„Å¸', 'değ'),
    ('tàƒÂ¼rk', 'türk'),
    ('bàƒÂ¶l', 'böl'),
    ('Ã†Å¸', 'ş'),
    ('Ã…Å¸', 'Ş'),
    ('Ã‡', 'Ç'),
    ('Ã–', 'Ö'),
    ('Ãœ', 'Ü'),
    ('Ã†', 'İ'),
    ('Ã±', 'ı'),
    ('Ã§', 'ç'),
    ('Ã¶', 'ö'),
    ('Ã¼', 'ü'),
    ('Ã„Å¸', 'ş'),
    ('Ã¡', 'á'),
    ('Ã¢', 'â'),
    ('à€', 'EUR'),
    ('Ã', 'A'),
    ('àƒÂ', 'İ'),
]

# Regex patterns for cleanup
CLEANUP_PATTERNS = [
    r'ÃƒÂ[A-Za-z0-9]+',
    r'Ãƒ[A-Za-z0-9]+',
    r'àƒÂ[A-Za-z0-9]+',
    r'à„[A-Za-z0-9]+',
    r'â¬[^A-Za-z]*',
]


def fix_file_comprehensive(filepath):
    """Fix all types of mojibake encoding in a file"""
    if not os.path.exists(filepath):
        return False, "not found"
    
    # Read as binary
    with open(filepath, 'rb') as f:
        content = f.read()
    
    original = content
    
    # Step 1: Apply byte-level fixes
    for bad_bytes, good_bytes in BYTE_MOJIBAKE_MAP:
        content = content.replace(bad_bytes, good_bytes)
    
    # Step 2: Decode and apply text-level fixes
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        # Fallback: decode with replacement
        text = content.decode('utf-8', errors='replace')
    
    original_text = text
    
    # Apply text replacements (multiple iterations for nested patterns)
    for _ in range(3):
        prev = text
        for bad, good in TEXT_MOJIBAKE_MAP:
            text = text.replace(bad, good)
        if text == prev:
            break
    
    # Apply regex cleanup
    for pattern in CLEANUP_PATTERNS:
        text = re.sub(pattern, '', text)
    
    # Step 3: Write back if changed
    if text != original_text:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        return True, "fixed"
    
    return False, "no change"


def main():
    files = [
        'backend/app.py',
        'backend/graph_manager.py',
        'backend/route_config.py',
        'backend/multimodal_engine.py',
    ]
    
    print('=' * 60)
    print('UTF-8 Mojibake Fixer - Comprehensive Version')
    print('=' * 60)
    
    fixed_count = 0
    
    for filepath in files:
        ok, result = fix_file_comprehensive(filepath)
        status = 'FIXED' if ok else 'OK'
        print('{}: {} ({})'.format(status, filepath, result))
        if ok:
            fixed_count += 1
    
    print('=' * 60)
    print('Done: {} files processed, {} fixed'.format(len(files), fixed_count))
    print('=' * 60)


if __name__ == '__main__':
    main()
