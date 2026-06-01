from pathlib import Path

app_path = Path(r"c:\Users\Gaming\Desktop\projects\routeplanner\OpenRoutePlanner\backend\api\app.py")

if not app_path.exists():
    print("Error: backend/api/app.py not found!")
    exit(1)

# Specific exact string replacements for log/print statements in app.py using Unicode constants
LOG_MOJIBAKE_REPLACEMENTS = {
    # yüklendi
    "y\xc3\u0192\xc2\xaf\xc3\u201a\xc2\xbf\xc3\u201a\xc2\xbdklendi": "yüklendi",
    # yükleniyor
    "y\xc3\u0192\xc6\u2019\xc3\u201a\xc2\xbckleniyor": "yükleniyor",
    # bulunamadı
    "bulunamad\u0131\xc3\u0192\xe2\u20ac\x9e\xc3\u201a\xc2\xb1": "bulunamadı",
    "bulunamad\xc3\u0192\xe2\u20ac\x9e\xc3\u201a\xc2\xb1": "bulunamadı",
    # tamamlandı
    "tamamland\xc3\u0192\xe2\u20ac\x9e\xc3\u201a\xc2\xb1": "tamamlandı",
    # hatası
    "hatas\xc3\u0192\xe2\u20ac\x9e\xc3\u201a\xc2\xb1": "hatası",
    # toplanamadı
    "toplanamad\xc3\u0192\xe2\u20ac\x9e\xc3\u201a\xc2\xb1": "toplanamadı",
    # [HATA] / Eksik parametreler icon
    "\xc3\u0192\xc2\xa2\xc3\u201a\xc2\x9d\xc3\u2026\xe2\u20ac\u2122": "[HATA]",
    # çok
    "\xc3\u0192\xc2\xaf\xc3\u201a\xc2\xbf\xc3\u201a\xc2\xbdok": "çok",
    # kullanılıyor
    "kullan\xc3\u0192\xe2\u20ac\x9e\xc3\u201a\xc2\xb1l\xc3\u0192\xe2\u20ac\x9e\xc3\u201a\xc2\xb1yor": "kullanılıyor",
    # Sonuç
    "Sonu\xc3\u0192\xc2\xaf\xc3\u201a\xc2\xbf\xc3\u201a\xc2\xbd": "Sonuç",
    # değil
    "de\xc3\u0192\xe2\u20ac\x9e\xc3\u2026\xc2\xb8il": "değil",
    # hazır
    "haz\xc3\u0192\xe2\u20ac\x9e\xc3\u201a\xc2\xb1r": "hazır",
    # hesaplanıyor
    "hesaplan\xc3\u0192\xe2\u20ac\x9e\xc3\u201a\xc2\xb1yor": "hesaplanıyor",
    # çağrısı alındı
    "\xc3\u0192\xc6\u2019\xc3\u201a\xc2\xa7a\xc3\u0192\xe2\u20ac\x9e\xc3\u2026\xc2\xb8r\xc3\u0192\xe2\u20ac\x9e\xc3\u201a\xc2\xb1s\xc3\u0192\xe2\u20ac\x9e\xc3\u201a\xc2\xb1 al\xc3\u0192\xe2\u20ac\x9e\xc3\u201a\xc2\xb1nd": "çağrısı alındı",
    # eşleşme
    "e\xc3\u0192\xe2\u20ac\xa6\xc3\u2026\xc2\xb8le\xc3\u0192\xe2\u20ac\xa6\xc3\u2026\xc2\xb8me": "eşleşme",
    # aranıyor
    "aran\xc3\u0192\xe2\u20ac\x9e\xc3\u201a\xc2\xb1yor": "aranıyor",
}

try:
    content = app_path.read_text(encoding="utf-8", errors="replace")
    original_content = content
    
    replaced_count = 0
    for bad, good in LOG_MOJIBAKE_REPLACEMENTS.items():
        if bad in content:
            content = content.replace(bad, good)
            print(f"[REPLACED] '{bad.encode('ascii', 'backslashreplace').decode('ascii')}' -> '{good}'")
            replaced_count += 1
            
    if content != original_content:
        # Create a backup first for safety
        bak_path = app_path.with_suffix(app_path.suffix + ".bak_logfix")
        bak_path.write_text(original_content, encoding="utf-8")
        
        # Save fixed content
        app_path.write_text(content, encoding="utf-8")
        print(f"\n[SUCCESS] Safely repaired {replaced_count} mojibake sequences in backend/api/app.py!")
    else:
        print("\nNo mojibake replacements matched in backend/api/app.py.")
        
except Exception as e:
    print(f"Error repairing app.py: {e}")
