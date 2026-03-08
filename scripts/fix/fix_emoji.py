#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emoji düzeltme - Sadece kritik dosyalar
"""
import os

# Script scripts/fix/ içinde; proje köküne geç
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.normpath(os.path.join(_script_dir, '..', '..'))
os.chdir(_project_root)

files = [
    "backend/app.py",
]

# Emoji düzeltmeleri
emoji_fixes = {
    'âš ï¸': '⚠️',
    'âœ…': '✅',
    'ğŸ"': '📍',
    'ğŸ—º': '🗺️',
    'ğŸš€': '🚀',
    'ğŸ"Š': '📊',
    'ğŸ'¾': '💾',
    'ğŸ"': '🔍',
    'ğŸŽ¯': '🎯',
}

print("=" * 80)
print("EMOJI DÜZELTME")
print("=" * 80)
print()

for filepath in files:
    if not os.path.exists(filepath):
        print(f"⚠️  {filepath}: Dosya bulunamadı")
        continue
    
    # Oku
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Düzelt
    original = content
    for bad, good in emoji_fixes.items():
        content = content.replace(bad, good)
    
    if content != original:
        # Yaz
        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        print(f"✅ {filepath}: Düzeltildi")
    else:
        print(f"⏭️  {filepath}: Zaten temiz")

print()
print("=" * 80)
print("✅ Tamamlandı!")
print("=" * 80)
