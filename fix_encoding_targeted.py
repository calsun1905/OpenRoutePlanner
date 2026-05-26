# -*- coding: utf-8 -*-
"""
UTF-8 Mojibake Fixer - Targeted Byte-Level Fix
"""
import os
import re

# Byte sequences that need to be fixed
# These are the exact bytes causing mojibake
BYTE_FIXES = [
    # Pattern: 0xc3 0x82 0xc2 followed by a Latin-1 high byte
    # This represents a character that was double-encoded
    
    # ı (dotless i) - U+0131
    # Original: C4 B1 (UTF-8 for ı)
    # Corrupted: C3 82 C2 B1
    (b'\xc3\x82\xc2\xb1', b'\xc4\xb1'),
    
    # İ (capital I with dot) - U+0130
    # Original: C4 B0 (UTF-8 for İ)
    # Corrupted: C3 82 C2 B0
    (b'\xc3\x82\xc2\xb0', b'\xc4\xb0'),
    
    # ş (s-cedilla) - U+015F
    # Original: C5 9F (UTF-8 for ş)
    # Corrupted: C3 85 C2 B8
    (b'\xc3\x85\xc2\xb8', b'\xc5\x9f'),
    
    # Ş (S-cedilla)
    (b'\xc3\x85\xc2\x9e', b'\xc5\x9e'),
    
    # ğ (g-breve) - U+011F
    # Original: C4 9F (UTF-8 for ğ)
    # Corrupted: C3 84 C2 9F  (wait, this is different)
    # Let me check: C4 in UTF-8 is a 2-byte sequence, so 0xC4 followed by 0x9F
    # When C4 9F is interpreted as Latin-1 and re-encoded as UTF-8:
    # C4 -> C3 84
    # 9F -> C2 9F
    (b'\xc3\x84\xc2\x9f', b'\xc4\x9f'),
    
    # ı with different corruption pattern
    (b'\xc3\x82\xc2\xb1', b'\xc4\xb1'),
    
    # ö (o-umlaut) - U+00F6
    # Original: C3 B6
    # Various corruptions
    (b'\xc3\x82\xc2\xb6', b'\xc3\xb6'),
    (b'\xc3\x83\xc2\xb6', b'\xc3\xb6'),
    
    # ü (u-umlaut) - U+00FC
    (b'\xc3\x82\xc2\xbc', b'\xc3\xbc'),
    (b'\xc3\x83\xc2\xbc', b'\xc3\xbc'),
    
    # ç (c-cedilla) - U+00E7
    (b'\xc3\x82\xc2\xa7', b'\xc3\xa7'),
    (b'\xc3\x83\xc2\xa7', b'\xc3\xa7'),
    
    # Other corrupted sequences
    (b'\xc3\x82\xc2\x86', b'\xc3\x86'),  # Æ
    (b'\xc3\x82\xc2\x84', b'\xc3\x84'),  # Ä
    (b'\xc3\x82\xc2\x96', b'\xc3\x96'),  # Ö
    (b'\xc3\x82\xc2\x9c', b'\xc3\x9c'),  # Ü
    (b'\xc3\x82\xc2\x87', b'\xc3\x87'),  # Ç
    (b'\xc3\x82\xc2\x8d', b'\xc3\x8d'),  # Í
    (b'\xc3\x82\xc2\x8c', b'\xc3\x8c'),  # Í
    (b'\xc3\x82\xc2\x8e', b'\xc3\x8e'),  # Î
    (b'\xc3\x82\xc2\x8f', b'\xc3\x8f'),  # Ï
    (b'\xc3\x82\xc2\x90', b'\xc3\x90'),  # Ð
    (b'\xc3\x82\xc2\x91', b'\xc3\x91'),  # Ñ
    (b'\xc3\x82\xc2\x92', b'\xc3\x92'),  # Ò
    (b'\xc3\x82\xc2\x93', b'\xc3\x93'),  # Ó
    (b'\xc3\x82\xc2\x94', b'\xc3\x94'),  # Ô
    (b'\xc3\x82\xc2\x95', b'\xc3\x95'),  # Õ
    (b'\xc3\x82\xc2\x98', b'\xc3\x98'),  # Ø
    (b'\xc3\x82\xc2\x99', b'\xc3\x99'),  # Ù
    (b'\xc3\x82\xc2\x9a', b'\xc3\x9a'),  # Ú
    (b'\xc3\x82\xc2\x9b', b'\xc3\x9b'),  # Ü
    (b'\xc3\x82\xc2\x9d', b'\xc3\x9d'),  # Ý
    
    # 3-byte corruptions: C3 83 C2 XX
    (b'\xc3\x83\xc2\xb0', b'\xc3\xb0'),  # ð
    (b'\xc3\x83\xc2\xa0', b'\xc3\xa0'),  # à
    (b'\xc3\x83\xc2\xa1', b'\xc3\xa1'),  # á
    (b'\xc3\x83\xc2\xa2', b'\xc3\xa2'),  # â
    (b'\xc3\x83\xc2\xa3', b'\xc3\xa3'),  # ã
    (b'\xc3\x83\xc2\xa4', b'\xc3\xa4'),  # ä
    (b'\xc3\x83\xc2\xa5', b'\xc3\xa5'),  # å
    (b'\xc3\x83\xc2\xa6', b'\xc3\xa6'),  # æ
    (b'\xc3\x83\xc2\xa7', b'\xc3\xa7'),  # ç
    (b'\xc3\x83\xc2\xa8', b'\xc3\xa8'),  # è
    (b'\xc3\x83\xc2\xa9', b'\xc3\xa9'),  # é
    (b'\xc3\x83\xc2\xaa', b'\xc3\xaa'),  # ê
    (b'\xc3\x83\xc2\xab', b'\xc3\xab'),  # ë
    (b'\xc3\x83\xc2\xac', b'\xc3\xac'),  # ì
    (b'\xc3\x83\xc2\xad', b'\xc3\xad'),  # í
    (b'\xc3\x83\xc2\xae', b'\xc3\xae'),  # î
    (b'\xc3\x83\xc2\xaf', b'\xc3\xaf'),  # ï
    (b'\xc3\x83\xc2\xb1', b'\xc3\xb1'),  # ñ
    (b'\xc3\x83\xc2\xb2', b'\xc3\xb2'),  # ò
    (b'\xc3\x83\xc2\xb3', b'\xc3\xb3'),  # ó
    (b'\xc3\x83\xc2\xb4', b'\xc3\xb4'),  # ô
    (b'\xc3\x83\xc2\xb5', b'\xc3\xb5'),  # õ
    (b'\xc3\x83\xc2\xb6', b'\xc3\xb6'),  # ö
    (b'\xc3\x83\xc2\xb7', b'\xc3\xb7'),  # ÷
    (b'\xc3\x83\xc2\xb8', b'\xc3\xb8'),  # ø
    (b'\xc3\x83\xc2\xb9', b'\xc3\xb9'),  # ù
    (b'\xc3\x83\xc2\xba', b'\xc3\xba'),  # ú
    (b'\xc3\x83\xc2\xbb', b'\xc3\xbb'),  # û
    (b'\xc3\x83\xc2\xbc', b'\xc3\xbc'),  # ü
    (b'\xc3\x83\xc2\xbd', b'\xc3\xbd'),  # ý
    (b'\xc3\x83\xc2\xbe', b'\xc3\xbe'),  # þ
    (b'\xc3\x83\xc2\xbf', b'\xc3\xbf'),  # ÿ
    
    # Common garbage pattern: â¬"
    (b'\xc3\xa2\xe2\x82\xac', b' '),
    (b'\xe2\x82\xac', b'EUR'),
    (b'\xe2\x80\x9e', b'"'),
    (b'\xe2\x80\x9c', b'"'),
]


def fix_file_targeted(filepath):
    """Fix mojibake byte sequences"""
    if not os.path.exists(filepath):
        return False, "not found"
    
    with open(filepath, 'rb') as f:
        content = f.read()
    
    original = content
    
    # Apply all byte-level fixes
    for bad, good in BYTE_FIXES:
        content = content.replace(bad, good)
    
    if content != original:
        with open(filepath, 'wb') as f:
            f.write(content)
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
    print('UTF-8 Mojibake Fixer - Targeted Byte-Level')
    print('=' * 60)
    
    fixed = 0
    for f in files:
        ok, result = fix_file_targeted(f)
        print('{}: {} ({})'.format('FIXED' if ok else 'OK', f, result))
        if ok:
            fixed += 1
    
    print('=' * 60)
    print('Done: {} files fixed'.format(fixed))
    print('=' * 60)


if __name__ == '__main__':
    main()
