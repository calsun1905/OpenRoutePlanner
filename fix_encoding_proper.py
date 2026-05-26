# -*- coding: utf-8 -*-
"""
UTF-8 Mojibake Fixer - Proper Implementation
Detects and fixes multi-layer mojibake encoding issues
"""
import os
import re

# Common mojibake patterns in UTF-8 text
MOJIBAKE_PATTERNS = [
    # Triple-layer patterns (most corrupted)
    ('ÃƒÂ¶', 'ö'), ('ÃƒÂ¼', 'ü'), ('ÃƒÂ§', 'ç'), ('ÃƒÂŸ', 'ğ'),
    ('ÃƒÂ±', 'ı'), ('ÃƒÂ ', 'İ'),
    
    # Double-layer patterns
    ('kàƒÂ¶pràƒÂ¼', 'köprü'),
    ('saàƒÂ¸lar', 'sağlar'),
    ('iàƒÂ§', 'iç'),
    ('deà„Å¸', 'değ'),
    ('tàƒÂ¼rk', 'türk'),
    ('bàƒÂ¶l', 'böl'),
    ('Ã†Å¸', 'ş'),
    ('Ã…Å¸', 'Ş'),
    
    # Single-layer patterns (less corrupted)
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
    ('à€', ''),
    ('àƒÂ ', 'İ'),
    ('à„Å¸', 'ş'),
]


def fix_file_proper(filepath):
    """Fix mojibake in a single file"""
    if not os.path.exists(filepath):
        return False, "not found"
    
    try:
        # Read the file content
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # Check for mojibake patterns
        has_mojibake = any(pat[0] in content for pat in MOJIBAKE_PATTERNS)
        if not has_mojibake:
            return False, "no mojibake detected"
        
        original = content
        
        # Apply fixes multiple times to handle multi-layer issues
        result = content
        for _ in range(5):  # Apply up to 5 rounds
            prev = result
            for bad, good in MOJIBAKE_PATTERNS:
                result = result.replace(bad, good)
            if result == prev:
                break
        
        # Clean up any remaining garbage
        result = re.sub(r'ÃƒÂ[A-Za-z]+', '', result)
        result = re.sub(r'Ãƒ[A-Za-z]+', '', result)
        result = re.sub(r'àƒÂ[A-Za-z]+', '', result)
        result = re.sub(r'à„[A-Za-z]+', '', result)
        
        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(result)
        
        changed = result != original
        return changed, "fixed" if changed else "no change"
        
    except Exception as e:
        return False, str(e)


def main():
    files = [
        'backend/app.py',
        'backend/graph_manager.py',
        'backend/route_config.py',
        'backend/multimodal_engine.py',
    ]
    
    print('=' * 60)
    print('UTF-8 Mojibake Fixer - Proper Implementation')
    print('=' * 60)
    
    fixed_count = 0
    
    for filepath in files:
        ok, result = fix_file_proper(filepath)
        if ok:
            print('FIXED: {}'.format(filepath))
            fixed_count += 1
        else:
            print('SKIP: {} ({})'.format(filepath, result))
    
    print('=' * 60)
    print('Done: {} files fixed'.format(fixed_count))
    print('=' * 60)


if __name__ == '__main__':
    main()
