#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Derin encoding taraması - TÜM dosyaları kontrol et
"""
import os
import glob

# Script scripts/tools/ içinde; proje köküne geç
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.normpath(os.path.join(_script_dir, '..', '..'))
os.chdir(_project_root)

# Bozuk karakter pattern'leri (genişletilmiş)
BAD_PATTERNS = [
    # Türkçe karakterler
    'Ä±', 'ÄŸ', 'Ã§', 'Ã¶', 'Ã¼', 'ÅŸ', 'Ä°', 'Ã‡', 'Ä', 'Ã–', 'Ãœ', 'Åž',
    # Özel karakterler
    'â€"', 'â€™', 'â€œ', 'â€�', 'â€¦', 'âœ', 'âš', 'ğŸ',
    # Diğer
    'Ã©', 'Ã ', 'Ã¨', 'Ã«', 'Ã¯', 'Ã´', 'Ã»',
]

print("=" * 80)
print("DERİN ENCODING TARAMASI - TÜM DOSYALAR")
print("=" * 80)
print()

# Tüm dosyaları bul
all_files = []
all_files += glob.glob("backend/**/*.py", recursive=True)
all_files += glob.glob("frontend/**/*.js", recursive=True)
all_files += glob.glob("frontend/**/*.html", recursive=True)
all_files += glob.glob("frontend/**/*.css", recursive=True)
all_files += glob.glob("*.md", recursive=False)
all_files += glob.glob("*.py", recursive=False)

print(f"📁 Toplam {len(all_files)} dosya taranıyor...")
print()

total_issues = 0
problematic_files = []

for filepath in sorted(all_files):
    if not os.path.exists(filepath):
        continue
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Bozuk karakter var mı?
        issues = []
        for pattern in BAD_PATTERNS:
            if pattern in content:
                count = content.count(pattern)
                issues.append((pattern, count))
        
        if issues:
            print(f"❌ {filepath}:")
            for pattern, count in issues[:5]:  # İlk 5'i göster
                # Pattern'i güvenli göster
                safe_pattern = repr(pattern)[1:-1]
                print(f"   '{safe_pattern}' → {count} kez")
            if len(issues) > 5:
                print(f"   ... ve {len(issues) - 5} pattern daha")
            print()
            total_issues += sum(count for _, count in issues)
            problematic_files.append(filepath)
        
    except Exception as e:
        print(f"⚠️  {filepath}: Okunamadı - {e}")

print("=" * 80)
print(f"SONUÇ: {total_issues} bozuk karakter bulundu")
print(f"       {len(problematic_files)} dosyada sorun var")
print("=" * 80)

if problematic_files:
    print()
    print("🔧 Sorunlu Dosyalar:")
    for f in problematic_files:
        print(f"   - {f}")
    print()
    print("Düzeltmek için:")
    print("   python scripts/fix/fix_backend.py")
else:
    print()
    print("✅ TÜM DOSYALAR TEMİZ!")
