# -*- coding: utf-8 -*-
"""
UTF-8 Mojibake Fixer - Byte-level approach
"""
import os

# Byte patterns for mojibake characters (UTF-8 bytes that appear when latin-1 is decoded as utf-8)
MOJIBAKE_FIXES = [
    # Double-encoding UTF-8: Turkish special chars
    (b'\xc3\xa2', b'a'),      # â
    (b'\xc3\xa0', b'a'),      # à  
    (b'\xc3\xa1', b'a'),      # á
    (b'\xc3\xa4', b'a'),      # ä
    (b'\xcse', b'e'),         # é (malformed)
    (b'\xc3\xa9', b'e'),      # é
    (b'\xc3\xaa', b'e'),      # ê
    (b'\xc3\xab', b'e'),      # ë
    (b'\xc3\xb6', b'o'),      # ö
    (b'\xc3\xbc', b'u'),      # ü
    (b'\xc3\xa7', b'c'),      # ç
    (b'\xc3\xb0', b'i'),      # ğ (often used as ı)
    (b'\xc3\x9f', b's'),      # ß (often used as ş)
    (b'\xc3\x90', b'I'),      # Ð (often used as İ)
    (b'\xc3\x98', b'O'),      # Ø (often used as Ö)
    (b'\xc3\x99', b'U'),      # Ù (often used as Ü)
    (b'\xc3\x9d', b'Y'),      # Ý
    (b'\xc3\x8e', b'I'),      # Î
    (b'\xc3\x8f', b'I'),      # Ï
    (b'\xc3\x8d', b'I'),      # Í
    (b'\xc3\x8c', b'I'),      # Í
    (b'\xc3\x96', b'O'),      # Ø (never used in valid UTF-8 text)
    (b'\xc3\x9c', b'U'),      # Ü
    (b'\xc3\x87', b'C'),      # Ç
    (b'\xc3\x86', b'AE'),     # Æ
    (b'\xc3\xa8', b'e'),      # è
    (b'\xc3\xac', b'i'),      # ì
    (b'\xc3\xad', b'i'),      # í
    (b'\xc3\xae', b'i'),      # î
    (b'\xc3\xaf', b'i'),      # ï
    (b'\xc3\xb2', b'o'),      # ò
    (b'\xc3\xb3', b'o'),      # ó
    (b'\xc3\xb4', b'o'),      # ô
    (b'\xc3\xb5', b'o'),      # õ
    (b'\xc3\xb8', b'o'),      # ø
    (b'\xc3\xb9', b'u'),      # ù
    (b'\xc3\xba', b'u'),      # ú
    (b'\xc3\xbb', b'u'),      # û
]

# Second pass: clean up remaining garbage
GARBAGE_CLEANUP = [
    (b'\xc3', b''),          # Remove trailing C3 bytes
    (b'\xc4', b''),          # Remove trailing C4 bytes
    (b'\xc5', b''),          # Remove trailing C5 bytes
]

# Third pass: replace remaining patterns with proper chars
FINAL_REPLACEMENTS = [
    (b'AE', b'AE'),
    (b'ss', b'ss'),
    (b'ff', b'ff'),
]


def fix_file(filepath):
    """Fix mojibake encoding in a single file"""
    if not os.path.exists(filepath):
        return False, "not found"
    
    try:
        # Read as binary
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # Check for mojibake patterns
        has_garbage = b'\xc3' in content or b'\xc4' in content
        if not has_garbage:
            return False, "no garbage"
        
        original = content
        
        # Decode as utf-8 to work with text
        try:
            text = content.decode('utf-8')
        except:
            # Try latin-1 first if utf-8 fails
            try:
                text = content.decode('latin-1')
            except:
                return False, "decode error"
        
        # Fix using text-based approach
        fixed_text = fix_text(text)
        
        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_text)
        
        return True, "fixed"
        
    except Exception as e:
        return False, str(e)


def fix_text(text):
    """Fix mojibake in text"""
    replacements = [
        # Triple-layer patterns
        ('Ãƒ¶', 'ö'), ('Ãƒ¼', 'ü'), ('Ãƒ§', 'ç'), ('ÃƒŸ', 'ğ'),
        ('Ãƒ±', 'ı'), ('Ãƒ ', 'İ'), ('Ãƒ¨', 'è'), ('Ãƒ©', 'é'),
        
        # Double-layer patterns
        ('kàƒ¶pràƒ¼', 'köprü'), ('saàƒ¸lar', 'sağlar'), 
        ('iàƒ§', 'iç'), ('deà„Å¸', 'değ'), ('tàƒ¼rk', 'türk'),
        
        # Single-layer patterns
        ('İÅ¸', 'ş'), ('Ş', 'Ş'), ('Ç', 'Ç'), ('Ö', 'Ö'),
        ('Ü', 'Ü'), ('İ', 'İ'), ('ı', 'ı'), ('ç', 'ç'),
        ('ö', 'ö'), ('ü', 'ü'), ('Ş', 'ş'), ('á', 'á'),
    ]
    
    for bad, good in replacements:
        text = text.replace(bad, good)
    
    return text


def main():
    files = [
        'backend/app.py',
        'backend/graph_manager.py',
        'backend/route_config.py',
        'backend/multimodal_engine.py',
    ]
    
    print('=' * 60)
    print('UTF-8 Mojibake Fixer - Final Version')
    print('=' * 60)
    
    fixed_count = 0
    
    for filepath in files:
        ok, result = fix_file(filepath)
        if ok:
            print('FIXED: {} ({})'.format(filepath, result))
            fixed_count += 1
        else:
            print('SKIP: {} ({})'.format(filepath, result))
    
    print('=' * 60)
    print('Done: {} files fixed'.format(fixed_count))
    print('=' * 60)


if __name__ == '__main__':
    main()
