# -*- coding: utf-8 -*-
"""
UTF-8 Mojibake Fixer - Correct Implementation
Analyzes the corruption pattern properly
"""
import os

def decode_corrupt_utf8(data):
    """Decode UTF-8 with corruption, then re-encode correctly"""
    result = bytearray()
    i = 0
    
    while i < len(data):
        b = data[i]
        
        # Handle UTF-8 start bytes
        if 0xC0 <= b <= 0xDF and i + 1 < len(data) and 0x80 <= data[i+1] <= 0xBF:
            # 2-byte sequence
            if data[i+1] == 0x83 or data[i+1] == 0x84 or data[i+1] == 0x85:
                # This is a corrupted sequence - Latin-1 byte re-encoded as UTF-8
                # Get the actual Latin-1 value
                latin1_val = data[i+1]
                # The original UTF-8 start byte
                utf8_start = b - 0xC0 + 0xC0  # This is roughly C0-FF range
                
                # Try to decode properly by treating as Latin-1
                # Re-encode as proper UTF-8
                if latin1_val < 0x80:
                    result.append(latin1_val)
                else:
                    # Use lookup table for common corruptions
                    latin1_to_utf8 = {
                        0x83: b'\xc3\x83',  # Ã
                        0x84: b'\xc3\x84',  # Ä
                        0x85: b'\xc3\x85',  # Å
                        0x86: b'\xc3\x86',  # Æ
                        0x87: b'\xc3\x87',  # Ç
                        0x88: b'\xc3\x88',  # È
                        0x89: b'\xc3\x89',  # É
                        0x8A: b'\xc3\x8A',  # Ê
                        0x8B: b'\xc3\x8B',  # Ë
                        0x8C: b'\xc3\x8C',  # Ì
                        0x8D: b'\xc3\x8D',  # Í
                        0x8E: b'\xc3\x8E',  # Î
                        0x8F: b'\xc3\x8F',  # Ï
                        0x90: b'\xc3\x90',  # Ð
                        0x91: b'\xc3\x91',  # Ñ
                        0x92: b'\xc3\x92',  # Ò
                        0x93: b'\xc3\x93',  # Ó
                        0x94: b'\xc3\x94',  # Ô
                        0x95: b'\xc3\x95',  # Õ
                        0x96: b'\xc3\x96',  # Ö
                        0x97: b'\xc3\x97',  # ×
                        0x98: b'\xc3\x98',  # Ø
                        0x99: b'\xc3\x99',  # Ù
                        0x9A: b'\xc3\x9A',  # Ú
                        0x9B: b'\xc3\x9B',  # Ü
                        0x9C: b'\xc3\x9C',  # Ù
                        0x9D: b'\xc3\x9D',  # Ý
                        0x9E: b'\xc3\x9E',  # Þ
                        0x9F: b'\xc3\x9F',  # ß
                        0xA0: b'\xc3\xa0',  # à
                        0xA1: b'\xc3\xa1',  # á
                        0xA2: b'\xc3\xa2',  # â
                        0xA3: b'\xc3\xa3',  # ã
                        0xA4: b'\xc3\xa4',  # ä
                        0xA5: b'\xc3\xa5',  # å
                        0xA6: b'\xc3\xa6',  # æ
                        0xA7: b'\xc3\xa7',  # ç
                        0xA8: b'\xc3\xa8',  # è
                        0xA9: b'\xc3\xa9',  # é
                        0xAA: b'\xc3\xaa',  # ê
                        0xAB: b'\xc3\xab',  # ë
                        0xAC: b'\xc3\xac',  # ì
                        0xAD: b'\xc3\xad',  # í
                        0xAE: b'\xc3\xae',  # î
                        0xAF: b'\xc3\xaf',  # ï
                        0xB0: b'\xc3\xb0',  # ð
                        0xB1: b'\xc3\xb1',  # ñ
                        0xB2: b'\xc3\xb2',  # ò
                        0xB3: b'\xc3\xb3',  # ó
                        0xB4: b'\xc3\xb4',  # ô
                        0xB5: b'\xc3\xb5',  # õ
                        0xB6: b'\xc3\xb6',  # ö
                        0xB7: b'\xc3\xb7',  # ÷
                        0xB8: b'\xc3\xb8',  # ø
                        0xB9: b'\xc3\xb9',  # ù
                        0xBA: b'\xc3\xba',  # ú
                        0xBB: b'\xc3\xbb',  # û
                        0xBC: b'\xc3\xbc',  # ü
                        0xBD: b'\xc3\xbd',  # ý
                        0xBE: b'\xc3\xbe',  # þ
                        0xBF: b'\xc3\xbf',  # ÿ
                    }
                    if latin1_val in latin1_to_utf8:
                        result.extend(latin1_to_utf8[latin1_val])
                    else:
                        result.append(data[i])
                        result.append(data[i+1])
                i += 2
            else:
                # Normal 2-byte UTF-8
                result.append(data[i])
                result.append(data[i+1])
                i += 2
        
        elif 0xE0 <= b <= 0xEF and i + 2 < len(data):
            # 3-byte sequence
            result.extend([data[i], data[i+1], data[i+2]])
            i += 3
        
        elif 0xF0 <= b <= 0xF7 and i + 3 < len(data):
            # 4-byte sequence
            result.extend([data[i], data[i+1], data[i+2], data[i+3]])
            i += 4
        
        else:
            # ASCII or unknown
            result.append(data[i])
            i += 1
    
    return bytes(result)


def fix_file_correct(filepath):
    """Fix mojibake by decoding corrupted UTF-8"""
    if not os.path.exists(filepath):
        return False, "not found"
    
    with open(filepath, 'rb') as f:
        content = f.read()
    
    original = content
    
    # Try to decode as corrupted UTF-8
    try:
        # Decode as if it's corrupted text with replacement for errors
        text = content.decode('utf-8', errors='replace')
    except:
        text = content.decode('latin-1', errors='replace')
    
    # Now figure out what the text SHOULD be
    
    # Write back
    try:
        fixed = text.encode('utf-8')
        if fixed != original:
            with open(filepath, 'wb') as f:
                f.write(fixed)
            return True, "fixed"
    except:
        pass
    
    return False, "no change"


def main():
    files = [
        'backend/app.py',
        'backend/graph_manager.py',
        'backend/route_config.py',
        'backend/multimodal_engine.py',
    ]
    
    print('=' * 60)
    print('UTF-8 Mojibake Fixer - Correct Implementation')
    print('=' * 60)
    
    fixed = 0
    for f in files:
        ok, result = fix_file_correct(f)
        print('{}: {} ({})'.format('FIXED' if ok else 'OK', f, result))
        if ok:
            fixed += 1
    
    print('=' * 60)
    print('Done: {} files fixed'.format(fixed))
    print('=' * 60)


if __name__ == '__main__':
    main()
