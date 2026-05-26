#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend encoding düzeltme
"""
import os
import glob

# Script scripts/fix/ içinde; proje köküne geç
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.normpath(os.path.join(_script_dir, '..', '..'))
os.chdir(_project_root)

# Tüm backend Python dosyalarını bul
backend_files = glob.glob("backend/**/*.py", recursive=True)

print("=" * 80)
print("BACKEND ENCODING DÜZELTME")
print("=" * 80)
print()

# Bozuk → Doğru eşleştirmeler
replacements = {
    # Türkçe karakterler
    'ı': 'ı',
    'ğ': 'ğ',
    'ç': 'ç',
    'ö': 'ö',
    'ü': 'ü',
    'ş': 'ş',
    'İ': 'İ',
    'Ç': 'Ç',
    'Ä': 'Ğ',
    'Ö': 'Ö',
    'Ü': 'Ü',
    'Ş': 'Ş',
    
    # Özel karakterler
    '"': '—',
    ''': "'",
    '"': '"',
    '-�': '"',
    '…': '…',
    '…': '✅',
    'âš ï¸': '⚠️',
    
    # Kelimeler
    'değilse': 'değilse',
    'değil': 'değil',
    'dışı': 'dışı',
    'yüklendi': 'yüklendi',
    'bulunamadı': 'bulunamadı',
    'kurulu': 'kurulu',
    'modülü': 'modülü',
    'klasörünün': 'klasörünün',
}

fixed_count = 0

for filepath in backend_files:
    try:
        # Oku
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Bozuk karakter var mı?
        has_issues = any(bad in content for bad in replacements.keys())
        
        if not has_issues:
            continue
        
        # Düzelt
        for bad, good in replacements.items():
            content = content.replace(bad, good)
        
        # Yaz
        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        
        print(f"✅ {filepath}")
        fixed_count += 1
        
    except Exception as e:
        print(f"❌ {filepath}: {e}")

print()
print("=" * 80)
print(f"✅ {fixed_count} dosya düzeltildi")
print("=" * 80)
print()
print("Şimdi:")
print("1. Backend'i yeniden başlat: python backend/app.py")
print("2. Tarayıcıda Hard Refresh: Ctrl+Shift+R")
