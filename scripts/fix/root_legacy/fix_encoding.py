# -*- coding: utf-8 -*-
"""
UTF-8 encoding fixer script
Projedeki bozuk UTF-8 karakterleri duzeltir
"""
import os
import re

def fix_mojibake_characters(text):
    """Mojibake karakterleri duzgün Turkcxe karakterlere cevirir"""
    
    # Single-layer mojibake (Latin-1 misinterpreted as UTF-8)
    single_layer = [
        ('\xc3\xa2', 'a'),  # â
        ('\xc3\x82', 'A'),  # 
        ('\xc3\xa0', 'a'),  # à
        ('\xc3\xa1', 'a'),  # á
        ('\xc3\xa4', 'a'),  # ä
        ('\xc3\x84', 'A'),  # Ä
        ('\xc3\xa9', 'e'),  # é
        ('\xc3\x89', 'E'),  # É
        ('\xc3\xb6', 'o'),  # ö
        ('\xc3\x96', 'O'),  # Ö
        ('\xc3\xbc', 'u'),  # ü
        ('\xc3\x9c', 'U'),  # Ü
        ('\xc3\xa7', 'c'),  # ç
        ('\xc3\x87', 'C'),  # Ç
        ('\xc3\xb0', 'i'),  # ğ (used as ı)
        ('\xc3\x90', 'I'),  # Ð (used as İ)
        ('\xc3\x9f', 's'),  # ß (used as ş)
        ('\xc3\x98', 'O'),  # Ø (used as Ö)
        ('\xc3\x99', 'U'),  # Ù (used as Ü)
        ('\xc3\x9a', 'U'),  # Ú
        ('\xc3\x9b', 'U'),  # Ü
        ('\xc3\x9d', 'Y'),  # Ý
        ('\xc3\x8e', 'I'),  # Î
        ('\xc3\x8f', 'I'),  # Ï
        ('\xc3\x8d', 'I'),  # Í
        ('\xc3\x8c', 'I'),  # Í
        ('\xc3\xaa', 'e'),  # ê
        ('\xc3\xab', 'e'),  # ë
        ('\xc3\xac', 'i'),  # ì
        ('\xc3\xad', 'i'),  # í
        ('\xc3\xae', 'i'),  # î
        ('\xc3\xaf', 'i'),  # ï
        ('\xc3\xb2', 'o'),  # ò
        ('\xc3\xb3', 'o'),  # ó
        ('\xc3\xb4', 'o'),  # ô
        ('\xc3\xb5', 'o'),  # õ
        ('\xc3\xb8', 'o'),  # ø
        ('\xc3\xb9', 'u'),  # ù
        ('\xc3\xba', 'u'),  # ú
        ('\xc3\xbb', 'u'),  # û
    ]
    
    result = text
    
    # Apply all replacements
    for bad, good in single_layer:
        result = result.replace(bad, good)
    
    # Clean up remaining garbage
    result = re.sub(r'xc3', '', result)
    
    # Additional Turkish specific fixes (already in UTF-8 form)
    result = result.replace('\xc4\xb1', 'i')  # ı
    result = result.replace('\xc4\xb0', 'I')  # İ
    result = result.replace('\xc4\x9f', 'g')  # ğ
    result = result.replace('\xc5\x9e', 'G')  # Ğ
    result = result.replace('\xc5\x9f', 's')  # ş
    result = result.replace('\xc5\xa0', 'S')  # Ş
    result = result.replace('\xc3\xbc', 'u')  # ü
    result = result.replace('\xc3\x9c', 'U')  # Ü
    result = result.replace('\xc3\xb6', 'o')  # ö
    result = result.replace('\xc3\x96', 'O')  # Ö
    result = result.replace('\xc3\xa7', 'c')  # ç
    result = result.replace('\xc3\x87', 'C')  # Ç
    
    return result


def process_file(filepath):
    """Bir dosyadaki encoding problemlerini duzeltir"""
    if not os.path.exists(filepath):
        print('SKIP: {} (not found)'.format(filepath))
        return False
    
    # Binary olarak oku
    with open(filepath, 'rb') as f:
        content = f.read()
    
    # UTF-8 olarak decode et
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        encodings = ['latin-1', 'cp1254', 'iso-8859-9', 'windows-1254']
        text = None
        for enc in encodings:
            try:
                text = content.decode(enc)
                print('  Decoded with {}'.format(enc))
                break
            except:
                continue
        
        if text is None:
            print('ERROR: Cannot decode {}'.format(filepath))
            return False
    
    # Mojibake kontrol - look for common mojibake patterns
    has_mojibake = bool(re.search(r'[Ã\x83â\x83ÄÅ§öüÃ\x9fÃ\x8d]', text))
    
    if has_mojibake:
        print('FIXING: {}'.format(filepath))
        fixed = fix_mojibake_characters(text)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed)
        print('  Fixed: {}'.format(filepath))
        return True
    else:
        print('OK: {}'.format(filepath))
        return False


def main():
    """Ana islem"""
    backend_files = [
        'backend/app.py',
        'backend/graph_manager.py',
        'backend/route_config.py',
        'backend/multimodal_engine.py',
    ]
    
    print('=' * 60)
    print('UTF-8 Encoding Fixer v3')
    print('=' * 60)
    
    fixed_count = 0
    for filepath in backend_files:
        if process_file(filepath):
            fixed_count += 1
    
    print('=' * 60)
    print('Tamamlandi: {} dosya duzeltildi'.format(fixed_count))
    print('=' * 60)


if __name__ == '__main__':
    main()
