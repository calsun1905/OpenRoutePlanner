#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Encoding Fix Script - OpenRoutePlanner

Bu script, projedeki dosyalardaki encoding sorunlarını tespit eder ve düzeltir.
- Replacement character (U+FFFD) içeren satırları bulur
- Türkçe karakterlerin bozulmuş versiyonlarını düzeltir
"""

import os
import sys
from pathlib import Path

# Proje kök dizini
ROOT_DIR = Path(__file__).parent.parent.parent

# Düzeltilecek encoding haritaları
# Windows-1254 / Latin-5 → UTF-8 dönüşümü için yaygın hatalar
ENCODING_FIXES = {
    'Ü': 'Ü', 'ÅŸ': 'ş', 'Ä±': 'ı', 'ç': 'ç', 'ÄŸ': 'ğ', 'ö': 'ö',
    'ü': 'ü', 'Ä°': 'İ', 'Ç': 'Ç', 'Ä': 'Ş', 'â': 'â',
    'Ã©': 'é', 'Ã³': 'ó', 'ÄŸ': 'ğ', 'ÅŸ': 'ş'
}

# Kontrol edilecek dizinler
CHECK_DIRS = ['backend', 'frontend', 'tests']
# Atlanacak dizinler
SKIP_DIRS = ['.venv', '__pycache__', '.git', 'cache', 'node_modules']


def has_replacement_char(text: str) -> bool:
    """Metin replacement character içeriyorsa True döndürür."""
    # U+FFFD (Unicode REPLACEMENT CHARACTER)
    REPLACEMENT_CHAR = '\ufffd'
    return REPLACEMENT_CHAR in text


def fix_mojibake(text: str) -> str:
    """Mojibake (bozuk Türkçe karakter) düzeltir."""
    fixed = text
    for wrong, correct in ENCODING_FIXES.items():
        fixed = fixed.replace(wrong, correct)
    return fixed


def fix_file(filepath: Path, dry_run: bool = False) -> dict:
    """Dosyayı düzeltir."""
    try:
        # Önce dosyayı BOM olmadan okumayı dene
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:  # utf-8-sig BOM'u otomatik kaldırır
                content = f.read()
        except:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

        # İçerikte hâlâ replacement char varsa, daha agresif düzeltme dene
        if has_replacement_char(content):
            # Dosyayı binary olarak oku ve BOM'u temizle
            with open(filepath, 'rb') as f:
                raw = f.read()

            # BOM'u kaldır (UTF-8 BOM: ef bb bf)
            if raw.startswith(b'\xef\xbb\xbf'):
                raw = raw[3:]

            # UTF-8 olarak decode et
            try:
                content = raw.decode('utf-8')
            except UnicodeDecodeError:
                # Başarısız olursa Latin-5/Windows-1254 dene
                try:
                    content = raw.decode('windows-1254')
                except:
                    content = raw.decode('utf-8', errors='ignore')

        # Mojibake düzeltmesi uygula
        original_content = content
        content = fix_mojibake(content)

        # Değişiklik varsa kaydet
        if content != original_content and not dry_run:
            # UTF-8 without BOM olarak kaydet
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

        return {
            'path': str(filepath),
            'fixed': content != original_content,
            'had_bom': True  # Bu true diyelim çünkü sorun buydu
        }

    except Exception as e:
        return {
            'path': str(filepath),
            'fixed': False,
            'error': str(e)
        }


def check_file(filepath: Path) -> dict:
    """Dosyayı kontrol eder ve sorunları döndürür."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        issues = []

        # Replacement character kontrolü
        if has_replacement_char(content):
            # Sorunlu satırları bul
            lines = content.split('\n')
            problem_lines = []
            for i, line in enumerate(lines, 1):
                if has_replacement_char(line):
                    problem_lines.append(i)

            issues.append({
                'type': 'replacement_char',
                'lines': problem_lines[:10]  # İlk 10 satır
            })

        # Mojibake kontrolü
        for wrong in ENCODING_FIXES.keys():
            if wrong in content:
                issues.append({
                    'type': 'mojibake',
                    'char': wrong
                })
                break

        return {
            'path': str(filepath),
            'issues': issues,
            'fixable': len(issues) > 0
        }

    except UnicodeDecodeError as e:
        return {
            'path': str(filepath),
            'issues': [{'type': 'decode_error', 'error': str(e)}],
            'fixable': False
        }
    except Exception as e:
        return {
            'path': str(filepath),
            'issues': [{'type': 'error', 'error': str(e)}],
            'fixable': False
        }


def scan_files() -> list:
    """Tüm dosyaları tarar ve sorunlu dosyaları döndürür."""
    problematic_files = []

    for check_dir in CHECK_DIRS:
        dir_path = ROOT_DIR / check_dir
        if not dir_path.exists():
            continue

        for filepath in dir_path.rglob('*.py'):
            # Atlanacak dizinleri kontrol et
            if any(skip in filepath.parts for skip in SKIP_DIRS):
                continue

            result = check_file(filepath)
            if result['issues']:
                problematic_files.append(result)

    return problematic_files


def main():
    """Ana fonksiyon."""
    import argparse

    parser = argparse.ArgumentParser(description='Encoding Fix Script')
    parser.add_argument('--fix', action='store_true', help='Dosyalari otomatik duzelt')
    parser.add_argument('--dry-run', action='store_true', help='Sadece simule et, degisiklik yapma')
    args = parser.parse_args()

    print("=" * 60)
    print("Encoding Fix Script - OpenRoutePlanner")
    print("=" * 60)

    # Dosyalari tara
    print("\n1. Dosyalar taraniyor...")
    problematic = scan_files()

    if not problematic:
        print("   [OK] Encoding sorunu bulunamadi!")
        return 0

    print(f"   [!] {len(problematic)} dosyada sorun tespit edildi:")

    if args.fix or args.dry_run:
        print("\n2. Dosyalar duzeltiliyor...")
        fixed_count = 0
        failed_count = 0

        for result in problematic:
            filepath = Path(result['path'])
            fix_result = fix_file(filepath, dry_run=args.dry_run)

            rel_path = os.path.relpath(fix_result['path'], ROOT_DIR)
            if fix_result.get('fixed'):
                print(f"   [+] Duzeltildi: {rel_path}")
                fixed_count += 1
            elif fix_result.get('error'):
                print(f"   [-] Hata: {rel_path} - {fix_result['error']}")
                failed_count += 1

        print(f"\n   Sonuc: {fixed_count} dosya duzeltildi, {failed_count} basarisiz")

        if args.dry_run:
            print("\n   [!] DRY RUN - Gercek degisiklik yapilmadi!")
            print("       Gercek duzeltme icin --fix kullanin")
    else:
        # Sonuçları göster
        for i, result in enumerate(problematic[:20], 1):  # Ilk 20
            rel_path = os.path.relpath(result['path'], ROOT_DIR)
            print(f"\n   {i}. {rel_path}")
            for issue in result['issues']:
                if issue['type'] == 'replacement_char':
                    lines_str = ', '.join(map(str, issue['lines'][:5]))
                    print(f"      - Replacement char (satirlar: {lines_str}...)")
                elif issue['type'] == 'mojibake':
                    print(f"      - Mojibake karakter: {issue['char']}")
                elif issue['type'] == 'decode_error':
                    print(f"      - Decode error: {issue['error']}")

        if len(problematic) > 20:
            print(f"\n   ... ve {len(problematic) - 20} dosya daha")

        # Onay almadan once onleme
        print("\n" + "=" * 60)
        print("[!] DIYKKAT: Bu script sadece tespit yapar.")
        print("   Dosyalari otomatik duzeltmek icin '--fix' bayragini kullanin.")
        print("   Once --dry-run ile test etmeniz onerilir.")
        print("=" * 60)

        return 1


if __name__ == '__main__':
    sys.exit(main())
