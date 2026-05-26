# -*- coding: utf-8 -*-
"""
UTF-8 encoding fixer script v4 - Direct approach
"""
import os
import re

# The mojibake patterns as they appear in UTF-8 text
MOJIBAKE_MAP = [
    # Triple-layer patterns (UTF-8 decoded as Latin-1, encoded as UTF-8, decoded again)
    ('Ãƒ¶', 'ö'),
    ('Ãƒ¼', 'ü'),
    ('Ãƒ§', 'ç'),
    ('ÃƒŸ', 'ğ'),
    ('Ãƒ±', 'ı'),
    ('Ãƒ ', 'İ'),
    ('Ãƒ¨', 'è'),
    ('Ãƒ©', 'é'),
    ('Ãƒª', 'ê'),
    ('Ãƒ¶', 'ö'),
    
    # Double-layer patterns
    ('kàƒ¶pràƒ¼', 'köprü'),
    ('saàƒ¸lar', 'sağlar'),
    ('iàƒ§', 'iç'),
    ('deà„Å¸', 'değ'),
    ('tàƒ¼rk', 'türk'),
    ('bàƒ¶l', 'böl'),
    
    # Single-layer patterns (already in file as UTF-8 text)
    ('İÅ¸', 'ş'),
    ('Ş', 'Ş'),
    ('Ç', 'Ç'),
    ('Ç', 'Ç'),
    ('Ö', 'Ö'),
    ('Ö', 'Ö'),
    ('Ü', 'Ü'),
    ('Ü', 'Ü'),
    ('İ', 'İ'),
    ('ı', 'ı'),
    ('ç', 'ç'),
    ('ö', 'ö'),
    ('ü', 'ü'),
    ('Ş', 'ş'),
    ('Ş', 'Ş'),
    ('á', 'á'),
    ('â', 'â'),
    ('à€', ''),
]

# This approach: read binary, decode each line by finding the mojibake patterns in bytes
def fix_text(text):
    """Fix mojibake in text"""
    for bad, good in MOJIBAKE_MAP:
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
    print('UTF-8 Fixer v4 - Direct Replace')
    print('=' * 60)
    
    total_fixed = 0
    
    for filepath in files:
        if not os.path.exists(filepath):
            print('SKIP: {}'.format(filepath))
            continue
        
        # Read file
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        fixed = fix_text(content)
        
        if fixed != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed)
            print('FIXED: {}'.format(filepath))
            total_fixed += 1
        else:
            print('OK: {}'.format(filepath))
    
    print('=' * 60)
    print('Done: {} files fixed'.format(total_fixed))
    print('=' * 60)


if __name__ == '__main__':
    main()
