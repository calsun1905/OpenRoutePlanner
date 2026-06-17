# -*- coding: utf-8 -*-
with open('frontend/js/app.js', 'rb') as f:
    data = f.read()

# Fix UTF-8 encoding issues in app.js
# 0xC3 0x85 + 0xC5 0xB8 = corrupted ş
# Correct UTF-8 for ş is 0xC5 0x9F
fixes = [
    (b'\xc3\x85\xc5\xb8', b'\xc5\x9f'),  # Corrupted ş -> ş
    (b'\xc3\x84\xc2\xb0', b'\xc3\xb0'),  # Corrupted ğ -> ğ
    (b'\xc3\x82\xc2\xbf', b'\xc3\xbf'),  # Corrupted ÿ -> ÿ
    (b'\xc3\x83\xc2\xbc', b'\xc3\xbc'),  # Corrupted ü -> ü
    (b'\xc3\x82\xc2\xb1', b'\xc4\xb1'),  # Corrupted ı -> ı
    (b'\xc3\x82\xc2\xb0', b'\xc4\xb0'),  # Corrupted İ -> İ
    (b'\xe2\x80\x9c', b'"'),  # Left quote
    (b'\xe2\x80\x9d', b'"'),  # Right quote
    (b'\xe2\x82\xac', b' '),  # Euro sign -> space
]

original = data
for bad, good in fixes:
    data = data.replace(bad, good)

# Check if there was any change
if data != original:
    with open('frontend/js/app.js', 'wb') as f:
        f.write(data)
    print(f'Fixed: {(len(original) - len(data))} bytes changed')
else:
    print('No changes needed - file appears to be valid UTF-8')
    
# Now do text replacements
with open('frontend/js/app.js', 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()

text_fixes = [
    ('kaydedilmiş', 'kaydedilmiş'),
    ('kaydedilmiş', 'kaydedilmiş'),
    ('ş', 'ş'),
    ('Ç', 'Ç'),
    ('Ö', 'Ö'),
    ('Ü', 'Ü'),
    ('Ç', 'Ç'),
    ('á', 'á'),
    ('â', 'â'),
    ('à', 'İ'),
]

original = text
for bad, good in text_fixes:
    text = text.replace(bad, good)

if text != original:
    with open('frontend/js/app.js', 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'Text fixes applied')
else:
    print('No text changes needed')
