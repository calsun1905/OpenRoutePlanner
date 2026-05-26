# -*- coding: utf-8 -*-
"""
UTF-8 Mojibake Fixer - Triple Layer Fix
Analyzes and fixes multi-layer UTF-8 mojibake encoding
"""
import os

def fix_file_real(filepath_or):
    """Fix triple-layer mojibake encoding"""
    if not os.path.exists(filepath_or):
        return False, "not found"
    
    # Read as binary
    with open(filepath_or, 'rb') as f:
        content = f.read()
    
    # Check if file has the characteristic mojibake bytes
    # The pattern is: invalid UTF-8 continuation bytes like 0x83, 0x86, 0x92, 0x82
    if b'\xc3\x83\xc6\x92' not in content:
        return False, "no triple-layer mojibake"
    
    # Create mapping for the specific corrupted sequences
    # These are the bytes as they appear in the corrupted file
    # and what they should decode to
    replacements = [
        (b'\xc3\x83\xc6\x92\xc3\x82\xc2\xb6', 'ö'),  # köprü word
        (b'\xc3\x83\xc6\x92\xc3\x82\xc2\xbc', 'ü'),  # ü
        (b'\xc3\x83\xc6\x92', 'ö'),                    # partial
        (b'\xc3\x83\xc6\x92\xc3\x82', 'ö'),            # partial
        (b'\xe2\x80\x9e', '"'),                         # fancy quotes
        (b'\xc3\x85\xc2\xb8', 'ş'),                    # ş
    ]
    
    result = content
    
    # Convert to string for easier manipulation
    for bad_bytes, good_char in replacements:
        result = result.replace(bad_bytes, good_char.encode('utf-8'))
    
    # Now do a second pass for remaining patterns
    # Replace garbage byte sequences
    result_str = result.decode('utf-8', errors='replace')
    
    # Common remaining patterns to fix
    more_fixes = [
        ('ÃƒÂ¶', 'ö'),
        ('ÃƒÂ¼', 'ü'),
        ('ÃƒÂ§', 'ç'),
        ('ÃƒÂŸ', 'ğ'),
        ('ÃƒÂ±', 'ı'),
        ('ÃƒÂ¨', 'è'),
        ('ÃƒÂ©', 'é'),
        ('kàƒÂ¶pràƒÂ¼', 'köprü'),
        ('saàƒÂ¸lar', 'sağlar'),
    ]
    
    for bad, good in more_fixes:
        result_str = result_str.replace(bad, good)
    
    # Write back
    if result_str != content.decode('utf-8', errors='replace'):
        with open(filepath_or, 'w', encoding='utf-8') as f:
            f.write(result_str)
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
    print('UTF-8 Mojibake Fixer - Triple Layer')
    print('=' * 60)
    
    fixed_count = 0
    
    for filepath in files:
        ok, result = fix_file_real(filepath)
        status = 'FIXED' if ok else 'SKIP'
        print('{}: {} ({})'.format(status, filepath, result))
        if ok:
            fixed_count += 1
    
    print('=' * 60)
    print('Done: {} files fixed'.format(fixed_count))
    print('=' * 60)


if __name__ == '__main__':
    main()
