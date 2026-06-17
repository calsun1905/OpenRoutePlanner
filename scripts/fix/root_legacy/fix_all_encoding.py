# -*- coding: utf-8 -*-
"""
UTF-8 Encoding Fixer - ALL Files
"""
import os

REPLACEMENTS = [
    # Triple-layer patterns
    ('Ãƒ¶', 'ö'), ('Ãƒ¼', 'ü'), ('Ãƒ§', 'ç'), ('Ãƒ±', 'ı'),
    ('Ãƒ ', 'İ'), ('Ãƒ¨', 'è'), ('Ãƒ©', 'é'), ('Ãƒª', 'ê'),
    # Double-layer patterns
    ('kàƒ¶pràƒ¼', 'köprü'), ('saàƒ¸lar', 'sağlar'),
    ('iàƒ§', 'iç'), ('deà„Å¸', 'değ'), ('tàƒ¼rk', 'türk'),
    ('bàƒ¶l', 'böl'), ('àƒ ', 'İ'), ('à„Å¸', 'ş'),
    # Single-layer patterns
    ('İÅ¸', 'ş'), ('Ş', 'Ş'), ('Ç', 'Ç'), ('Ö', 'Ö'),
    ('Ü', 'Ü'), ('İ', 'İ'), ('ı', 'ı'), ('ç', 'ç'),
    ('ö', 'ö'), ('ü', 'ü'), ('Ş', 'ş'), ('á', 'á'),
    ('â', 'â'), ('à€', 'EUR'),
]

def fix_file(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
        
        original = text
        for bad, good in REPLACEMENTS:
            text = text.replace(bad, good)
        
        if text != original:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            return True
    except Exception as e:
        print(f'  ERROR: {e}')
    return False

def main():
    root = r'c:\Users\batuf\Documents\GitHub\openroute\OpenRoutePlanner'
    targets = [
        'frontend/js/app.js',
        'progress.md',
        'scripts/fix/fix_backend.py',
        'scripts/finetune/prepare_data.py',
        'scripts/tools/deep_scan.py',
        'backend/route_config.py',
        'scripts/fix/fix_encoding.py',
        'backend/graph_manager.py',
        'scripts/tools/scan_encoding.py',
    ]
    
    print('=' * 60)
    print('FIXING ALL ENCODING ISSUES')
    print('=' * 60)
    
    fixed = 0
    for rel_path in targets:
        path = os.path.join(root, rel_path)
        if os.path.exists(path):
            if fix_file(path):
                print(f'FIXED: {rel_path}')
                fixed += 1
            else:
                print(f'OK: {rel_path}')
        else:
            print(f'SKIP: {rel_path} (not found)')
    
    print('=' * 60)
    print(f'Done: {fixed} files fixed')
    print('=' * 60)

if __name__ == '__main__':
    main()
