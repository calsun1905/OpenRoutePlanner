import os
from pathlib import Path

# Direct character map replacements for CP1252/Latin-1 to UTF-8 mojibake inside comments/docstrings
LATIN1_REPLACEMENTS = {
    "Ä±": "ı",
    "Ã¶": "ö",
    "Ã¼": "ü",
    "Ã§": "ç",
    "Ä°": "İ",
    "ÅŸ": "ş",
    "Åž": "Ş",
    "ÄŸ": "ğ",
    "Äž": "Ğ",
    "Ã–": "Ö",
    "Ãœ": "Ü",
    "Ã‡": "Ç",
}

# Safe word level replacements inside comments/docstrings to restore lost ? and  characters
WORD_REPLACEMENTS = {
    "Bazl?": "Bazlı",
    "Bazl": "Bazlı",
    "izelgesi": "çizelgesi",
    "izelgesini": "çizelgesini",
    "izelgesi": "çizelgesi",
    "ak?şmalar?": "çakışmaları",
    "akışmalar?": "çakışmaları",
    "ak?şmalar?": "çakışmaları",
    "akışmalar?": "çakışmaları",
    "akışma": "çakışma",
    "akışma": "çakışma",
    "Başlang?": "Başlangıç",
    "başlang?": "başlangıç",
    "sreilçeri": "süreleri",  # fix potential leftovers
    "sreleri": "süreleri",
    "sre": "süre",
    "sresini": "süresini",
    "gre": "göre",
    "yntemi": "yöntemi",
    "ynetimi": "yönetimi",
    "ynlendirme": "yönlendirme",
    "yksek": "yüksek",
    "dk": "düşük",
    "ncelik": "öncelik",
    "nemli": "önemli",
    "neri": "öneri",
    "nerisi": "önerisi",
    "nerir": "önerir",
    "nerilen": "önerilen",
    "zet": "özet",
    "zeti": "özeti",
    "zellikler": "özellikler",
    "zel": "özel",
    "var?ş": "varış",
    "ayr?l?ş": "ayrılış",
    "zamanlar?n?": "zamanlarını",
    "ulaş?m": "ulaşım",
    "Ulaş?m": "Ulaşım",
    "ekilen": "çekilen",
    "ekilen": "çekilen",
    "blge": "bölge",
    "blgeler": "bölgeler",
    "blgesi": "bölgesi",
    "ok": "çok",
    "zm": "çözüm",
    "zm": "çözüm",
    "zmleyici": "çözümleyici",
    "zmler": "çözümler",
    "zmleme": "çözümleme",
    "Çzmleme": "Çözümleme",
    "ge": "geç",
    "geersiz": "geçersiz",
    "geerli": "geçerli",
    "geiş": "geçiş",
    "bağ?ml?l?k": "bağımlılık",
    "bağ?ml?l?klar?": "bağımlılıkları",
    "aral?ğ?na": "aralığına",
    "koşullar?nda": "koşullarında",
    "saatler?ne": "saatlerine",
    "se": "seç",
    "nce": "önce",
    "?karsan?z": "çıkarsanız",
    "yağ?ş": "yağış",
    "s?cakl?ğ?na": "sıcaklığına",
    "s?cakl?ğ?n?": "sıcaklığını",
    "s?cakl?k": "sıcaklık",
    "zerinden": "üzerinden",
    "zerinde": "üzerinde",
    "zerine": "üzerine",
    "gncel": "güncel",
    "Gncel": "Güncel",
    "ncelikle": "öncelikle",
    "ncelikleri": "öncelikleri",
    "ile": "ilçe",
    "ileler": "ilçeler",
    "r.": "ör.",
    "rn": "örn",
    "rneği": "örneği",
    "rnek": "örnek",
    "retildiğini": "üretildiğini",
    "retim": "üretim",
    "retilen": "üretilen",
    "retir": "üretir",
    "rn": "ürün",
    "rnler": "ürünler",
    "gnlk": "günlük",
    "Gnlk": "Günlük",
    "gn": "gün",
    "gnler": "günler",
    "gn": "günü",
    "gnnde": "gününde",
    "gnn": "günün",
    "gncelle": "güncelle",
    "gncelleme": "güncelleme",
    "gncellenir": "güncellenir",
    "gncellenmesi": "güncellenmesi",
    "gvenli": "güvenli",
    "gvenliği": "güvenliği",
    "kpr": "köprü",
    "kprs": "köprüsü",
    "kprler": "köprüler",
    "kt": "kötü",
    "ktphane": "kütüphane",
    "kk": "küçük",
    "Kk": "Küçük",
    "kkyal?": "küçükyalı",
    "Kkyal?": "Küçükyalı",
    "erevesinde": "çerçevesinde",
    "ereve": "çerçeve",
    "izgisi": "çizgisi",
    "izelge": "çizelge",
    "gsterir": "gösterir",
    "gster": "göster",
    "gsteren": "gösteren",
    "gsterim": "gösterim",
    "dner": "döner",
    "dndrr": "döndürür",
    "dnştrlmesi": "dönüştürülmesi",
    "al?şmas?na": "çalışmasına",
    "al?ş?r": "çalışır",
    "al?şma": "çalışma",
    "al?şmalar?": "çalışmaları",
    "al?şmas?": "çalışması",
    "al?şan": "çalışan",
    "gl": "güçlü",
    "g": "güç",
    "dn": "düşün",
    "dnn": "düşünün",
    "dnyan?n": "dünyanın",
    "dnya": "dünya",
    "cretsiz": "ücretsiz",
    "ye": "üye",
    "yeler": "üyeler",
    "stanbul": "İstanbul",
    "arş?dan": "çarşıdan",
    "arş?": "çarşı",
    "tr": "türü",
    "trleri": "türleri",
    "tm": "tüm",
    "Tm": "Tüm",
}

ACTIVE_PYTHON_FILES = [
    "backend/nlp_engine.py",
    "backend/time_planner.py",
    "backend/districts_db.py",
    "backend/spatial_index.py",
    "backend/graph_manager.py",
    "backend/ibb_transit.py",
    "backend/tag_grounder.py",
    "backend/response_utils.py",
    "backend/gtfs_shapes.py",
    "backend/weather_service.py",
    "backend/weather_utils.py",
    "backend/cache_manager.py",
    "backend/multimodal_engine.py",
    "backend/route_storage.py",
    "backend/nlp_concept_resolver.py",
    "backend/logging_config.py",
    "backend/models.py",
    "backend/location_storage.py",
    "backend/storage_db.py",
    "backend/osm_poi_dictionary.py",
    "backend/route_config.py",
    "backend/app.py",
    "backend/rag_service.py"
]

project_root = Path(r"c:\Users\Gaming\Desktop\projects\routeplanner\OpenRoutePlanner")

def clean_text_segment(text):
    """Applies replacements to a safe text segment (comment or docstring line)."""
    # 1. Direct Latin-1 characters
    for bad, good in LATIN1_REPLACEMENTS.items():
        text = text.replace(bad, good)
    # 2. Vocabulary words
    for bad, good in WORD_REPLACEMENTS.items():
        text = text.replace(bad, good)
    return text

def fix_python_file(rel_path):
    file_path = project_root / rel_path
    if not file_path.exists():
        return False, "Not found"
        
    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        original_content = "\n".join(lines)
        
        in_docstring = False
        docstring_char = None
        new_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Check for docstring toggling
            if not in_docstring:
                if stripped.startswith('"""') or '"""' in stripped:
                    in_docstring = True
                    docstring_char = '"""'
                elif stripped.startswith("'''") or "'''" in stripped:
                    in_docstring = True
                    docstring_char = "'''"
                    
            # Process the line based on state
            if in_docstring:
                # Replace in the whole line since we are inside a docstring
                processed_line = clean_text_segment(line)
                
                # Check for docstring end
                # (Handle case where it starts and ends on same line safely)
                if docstring_char in stripped and stripped.count(docstring_char) % 2 == 0 and stripped.startswith(docstring_char):
                    in_docstring = False
                elif docstring_char in stripped and not stripped.startswith(docstring_char):
                    in_docstring = False
                elif docstring_char in stripped and stripped.startswith(docstring_char) and len(stripped) > 3:
                    in_docstring = False
            else:
                # We are in normal code. Only replace in comments!
                if '#' in line:
                    parts = line.split('#', 1)
                    code_part = parts[0]
                    comment_part = parts[1]
                    processed_line = code_part + '#' + clean_text_segment(comment_part)
                else:
                    processed_line = line
                    
            new_lines.append(processed_line)
            
            # If docstring was toggled off during this line, update state
            if in_docstring and docstring_char in stripped and not stripped.startswith(docstring_char):
                in_docstring = False
                
        fixed_content = "\n".join(new_lines)
        if fixed_content != original_content:
            file_path.write_text(fixed_content, encoding="utf-8")
            return True, "Successfully repaired comments/docstrings"
        else:
            return False, "No comments/docstrings needed repair"
            
    except Exception as e:
        return False, f"Error: {e}"

def main():
    print("=" * 70)
    print("SAFE COMMENT & DOCSTRING MOJIBAKE REPAIRER")
    print("=" * 70)
    
    repaired_count = 0
    for rel_path in ACTIVE_PYTHON_FILES:
        ok, status = fix_python_file(rel_path)
        if ok:
            print(f"[REPAIRED] {rel_path} - {status}")
            repaired_count += 1
        else:
            if status != "No comments/docstrings needed repair" and status != "Not found":
                print(f"[ERROR] {rel_path} - {status}")
                
    print("\n" + "=" * 70)
    print(f"REPAIR COMPLETED! Restored files: {repaired_count}/{len(ACTIVE_PYTHON_FILES)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
