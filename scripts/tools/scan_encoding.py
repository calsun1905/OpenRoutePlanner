#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bozuk karakter tarayıcı
"""
import os
import re

# Script scripts/tools/ içinde; proje köküne geç
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.normpath(os.path.join(_script_dir, '..', '..'))
os.chdir(_project_root)

# Bozuk karakter pattern'leri
BAD_PATTERNS = [
    'â€"', 'â€™', 'â€œ', 'â€�', 'â€¦',
    'Ã', 'Ä', 'Å', 'Ã©', 'Ã§'
]

files_to_check = [
    "frontend/js/app.js",
    "frontend/index.html",
    "frontend/css/style.css",
    "backend/app.py",
    "backend/graph_manager.py",
]

print("=" * 80)
print("BOZUK KARAKTER TARAMASI")
print("=" * 80)
print()

total_issues = 0

for filepath in files_to_check:
    if not os.path.exists(filepath):
        continue
    
    print(f"📄 {filepath}:")
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    issues = []
    for i, line in enumerate(lines, 1):
        for pattern in BAD_PATTERNS:
            if pattern in line:
                issues.append((i, line.strip()[:80]))
                break
    
    if issues:
        print(f"  ❌ {len(issues)} satırda sorun bulundu:")
        for line_num, line_text in issues[:5]:  # İlk 5'i göster
            print(f"     Line {line_num}: {line_text}")
        if len(issues) > 5:
            print(f"     ... ve {len(issues) - 5} satır daha")
        total_issues += len(issues)
    else:
        print(f"  ✅ Temiz")
    
    print()

print("=" * 80)
print(f"TOPLAM: {total_issues} satırda bozuk karakter bulundu")
print("=" * 80)

if total_issues > 0:
    print()
    print("🔧 Düzeltmek için:")
    print("   python scripts/fix/fix_backend.py")
