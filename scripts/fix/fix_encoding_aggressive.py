#!/usr/bin/env python3
"""
Aggressive Encoding Fix - Tum dosyalari UTF-8'e cevirir
"""
import os
from pathlib import Path

def try_decode(raw_bytes):
    """Farkli encoding'lerle dene, en iyisini sec"""
    encodings = ['utf-8', 'utf-8-sig', 'windows-1254', 'iso-8859-9', 'latin-5']

    for enc in encodings:
        try:
            text = raw_bytes.decode(enc)
            # Basit kalite kontrolu: replacement char olmamali
            if '' not in text:
                return text, enc
        except:
            continue

    # Hepsi basarısız olursa UTF-8 with errors='ignore'
    return raw_bytes.decode('utf-8', errors='ignore'), 'utf-8-ignore'

def fix_all_backend_files():
    """Backend klasorundeki tum Python dosyalarini duzelt"""
    backend_dir = Path('backend')

    if not backend_dir.exists():
        print("Backend klasoru bulunamadi!")
        return

    fixed = []
    failed = []

    for py_file in backend_dir.rglob('*.py'):
        try:
            # Binary olarak oku
            with open(py_file, 'rb') as f:
                raw = f.read()

            # Orjinali UTF-8 ile okumayi dene
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    original = f.read()
            except:
                original = None

            # Eger sorun varsa, farkli encoding'leri dene
            if original and '' in original:
                # Decode et
                decoded, used_enc = try_decode(raw)

                # Eger UTF-8 ise ve BOM varsa, BOM'u kaldir
                if used_enc == 'utf-8-sig' or raw.startswith(b'\xef\xbb\xbf'):
                    if raw.startswith(b'\xef\xbb\xbf'):
                        raw = raw[3:]
                        decoded = raw.decode('utf-8')

                # Ayni mi kontrol et
                if decoded != original:
                    # Kaydet
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(decoded)
                    fixed.append(str(py_file))
                    print(f"[+] {py_file}")
                else:
                    print(f"[=] {py_file} (zaten OK)")
            else:
                print(f"[OK] {py_file}")

        except Exception as e:
            failed.append((str(py_file), str(e)))
            print(f"[!] {py_file} - {e}")

    print(f"\n=== Sonuc ===")
    print(f"Duzeltildi: {len(fixed)}")
    print(f"Basarisiz: {len(failed)}")

    if failed:
        print("\nBasarisiz dosyalar:")
        for f, err in failed:
            print(f"  {f}: {err}")

if __name__ == '__main__':
    fix_all_backend_files()
