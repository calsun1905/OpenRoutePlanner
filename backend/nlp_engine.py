"""
nlp_engine.py - Türkçe Doğal Dil Sorgu Ayrıştırıcı

Kullanıcının doğal dil sorgularını analiz eder ve yapılandırılmış veriye çevirir.

Desteklenen sorgu türleri:
- "Kadıköy'den Beşiktaş'a rota" → {type: "route", origin: "Kadıköy", destination: "Beşiktaş"}
- "Kadıköy ile Taksim arası" → {type: "route", origin: "Kadıköy", destination: "Taksim"}
- "Kadıköy, Beşiktaş ve Taksim'i gez" → {type: "multi", locations: ["Kadıköy", "Beşiktaş", "Taksim"]}
- "Kadıköy'de neler var?" → {type: "poi", location: "Kadıköy"}
"""

import re
from typing import Dict, List, Optional, Any
try:
    from location_storage import get_all_locations
except ImportError:
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        from location_storage import get_all_locations
    except ImportError:
        def get_all_locations(): return []



# =============================================================================
# TÜRKÇE STOP WORDS (Edatlar, Bağlaçlar)
# =============================================================================

STOP_WORDS = {
    # Edatlar
    "dan", "den", "a", "e", "ya", "ye", "ye", "a", "e",
    "ile", "ve", "veya", "veyahut", "ile", "üzere",

    # Zamirler
    "ben", "sen", "o", "biz", "siz", "onlar",
    "bana", "sana", "ona", "bize", "size", "onlara",
    "beni", "seni", "onu", "bizi", "sizi", "onları",
    "benim", "senin", "onun", "bizim", "sizin", "onların",

    # Zarflar
    "şimdi", "sonra", "bugün", "yarın", "dün",
    "buraya", "oraya", "nereye", "nerede", "nasıl",

    # Soru kelimeleri
    "mi", "mı", "mu", "mü",
    "nerede", "nereye", "nasıl", "ne", "kaç",

    # Yardımcı kelimeler
    "et", "ede", "yap", "ol", "dur",
    "rota", "çiz", "hesapla", "göster", "bul",
}

# Yer ismi olabilecek yaygın kelimeler (stop word olarak silinmemeli)
PLACE_KEYWORDS = {
    "park", "meydan", "müze", "kütüphane", "cami", "kilise",
    "sinema", "tiyatro", "okul", "hastane", "kafe", "restoran",
    "otogar", "istasyon", "havalimanı", "liman", "iskele",
    "avm", "merkez", "pazar", "çarşı", "sokak", "cadde", "bulvar",
}


# =============================================================================
# REGEX PATTERNS
# =============================================================================

# Pattern 1: "X'den/ndan Y'ye/e rota/rotası"
PATTERN_ROUTE_1 = re.compile(
    r"(.+?)(?:den|dan|ten|tan)\s+(.+?)(?:ye|a|e)\s*(?:rota|rotası|yol|güzergah|nasıl giderim|nasıl gidilir)?\s*\.?$",
    re.IGNORECASE
)

# Pattern 2: "X ile Y arası/arasında"
PATTERN_ROUTE_2 = re.compile(
    r"(.+?)\s+ile\s+(.+?)\s+ar[ăa]s[ıi]?\s*(?:kaç kilometre|kaç km|mesafe|uzaklık)?\s*\.?$",
    re.IGNORECASE
)

# Pattern 3: "X, Y ve Z'yi/i gez/rotayı yap"
PATTERN_MULTI_1 = re.compile(
    r"^(.+?)\s*,\s*(.+?)\s+ve\s+(.+?)(?:yi|yı|i|ı|ü|ü)\s+gez\s*(?:rotasıyla)?\s*\.?$",
    re.IGNORECASE
)
PATTERN_MULTI_1b = re.compile(
    r"^(.+?)\s*,\s*(.+?)\s+ve\s+(.+?)(?:nu|nü)\s+gezdir\s*\?\s*$",
    re.IGNORECASE
)

# Pattern 4: "X'de/da/te/ta neler var/nereler var/ne yapabilirim/neleri öner"
PATTERN_POI_QUERY = re.compile(
    r"^(.+?)\s+(?:de|da|te|ta)\s+(?:neler|nereler)\s+var\?\s*$",
    re.IGNORECASE
)
PATTERN_POI_QUERY_2 = re.compile(
    r"^(.+?)\s+(?:de|da|te|ta)\s+ne\s+yapabilirim\?\s*$",
    re.IGNORECASE
)
PATTERN_POI_QUERY_3 = re.compile(
    r"^(.+?)\s+(?:de|da|te|ta)\s+(?:neler|nereleri|neleri|neyi|bir şey)\s+(?:öner|önere|tavsiye|önerir|önerirsin|öneririm|tavsiye eder|tavsiye ederim)\s*\?\s*$",
    re.IGNORECASE
)

# Pattern 5: "X'e git / X'e nasıl giderim / yol tarifi"
PATTERN_SINGLE_DEST = re.compile(
    r"^(.+?)(?:ye|a|e)\s+(?:git|nas[ıi]l\s+giderim|güzergah|rota|yol\s+tarifi)\s*\?\s*$",
    re.IGNORECASE
)

# Pattern 6: "X'den Y'ye nasıl giderim / yol tarifi"
PATTERN_ROUTE_EXTENDED = re.compile(
    r"^(.+?)(?:den|dan|ten|tan)\s+(.+?)(?:ye|a|e)\s+nas[ıi]l\s+giderim\?\s*$|"
    r"^(.+?)(?:den|dan|ten|tan)\s+(.+?)(?:ye|a|e)\s+yol\s+tarifi\?\s*$|"
    r"^(.+?)(?:den|dan|ten|tan)\s+(.+?)(?:ye|a|e)\s+rota\s*(?:çiz|hesapla|göster)\s*\?\s*$",
    re.IGNORECASE
)


# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================

def _clean_text(text: str) -> str:
    """
    Metni temizler: fazla boşlukları siler, noktalama işaretlerini temizler.

    Args:
        text: Temizlenecek metin

    Returns:
        str: Temizlenmiş metin
    """
    # Türkçe edatları birleştirilmiş halden ayır: "X'de" → "X de"
    text = re.sub(r"('de|'da|'den|'dan|'ten|'tan|'ye|'a|'e|'i|'ı|'u|'ü|'te|'ta|'ne|'na)", r" \1", text)

    # Fazla boşlukları tek boşluğa indir
    text = re.sub(r'\s+', ' ', text)
    # Baştaki ve sondaki boşlukları sil
    text = text.strip()
    # Sadece Türkçe karakterler, boşluklar ve virgül bırak
    text = re.sub(r'[^\w\s,ğüşıöçĞÜŞİÖÇ]', '', text)
    return text


def _extract_place_names(text: str) -> List[str]:
    """
    Metinden yer isimlerini çıkarır.

    Args:
        text: Analiz edilecek metin

    Returns:
        list[str]: Yer isimleri listesi
    """
    # Kayıtlı özel lokasyonları kontrol et
    custom_locations = [loc.get("name", "").lower() for loc in get_all_locations() if loc.get("name")]
    
    # Virgül ile ayrılmış yerleri ayır
    parts = text.split(',')

    places = []
    for part in parts:
        # Stop wordsleri temizle
        words = []
        for word in part.split():
            word_lower = word.lower()
            
            # Eğer kelime kullanıcının kaydettiği özel bir lokasyonsa (Ev, İş vb.) silme!
            if word_lower in custom_locations:
                words.append(word)
                continue
                
            if word_lower not in STOP_WORDS:
                words.append(word)
        place = ' '.join(words).strip()
        if place:
            places.append(place)

    return places


def _is_turkish_location(text: str) -> bool:
    """
    Metnin bir Türkçe yer ismi olup olmadığını kontrol eder.

    Args:
        text: Kontrol edilecek metin

    Returns:
        bool: Yer ismi ise True
    """
    # En az 2 karakter olmalı
    if len(text) < 2:
        return False

    # Türkçe karakter içeriyor mu?
    has_turkish = bool(re.search(r'[ğüşıöçĞÜŞİÖÇ]', text))

    # Stop word mü?
    if text.lower() in STOP_WORDS:
        return False

    # Çok kısa ve yaygın kelime mi?
    if len(text) <= 3 and text.lower() not in PLACE_KEYWORDS:
        # Yine de kontrol et - kısa yer isimleri olabilir (örn: Edirne)
        pass

    return True


# =============================================================================
# ANA FONKSİYON: parse_query
# =============================================================================

def parse_query(query: str) -> Dict[str, Any]:
    """
    Doğal dil sorgusunu analiz eder ve yapılandırılmış veriye çevirir.

    Args:
        query: Kullanıcı sorgusu (örn: "Kadıköy'den Beşiktaş'a rota")

    Returns:
        dict: Sorgu sonucu
        {
            "type": "route" | "multi" | "poi" | "single" | "unknown",
            "confidence": float (0.0 - 1.0),
            "origin": str | None,
            "destination": str | None,
            "locations": list[str] | None,
            "raw_query": str,
            "error": str | None
        }

    Örnekler:
        "Kadıköy'den Beşiktaş'a rota" → {type: "route", origin: "Kadıköy", destination: "Beşiktaş"}
        "Kadıköy, Beşiktaş ve Taksim'i gez" → {type: "multi", locations: ["Kadıköy", "Beşiktaş", "Taksim"]}
        "Kadıköy'de neler var?" → {type: "poi", location: "Kadıköy"}
    """
    if not query or not isinstance(query, str):
        return {
            "type": "unknown",
            "confidence": 0.0,
            "raw_query": query,
            "error": "Geçersiz sorgu"
        }

    # Metni temizle
    query_clean = _clean_text(query)

    # Pattern 0: X'den Y'ye nasıl giderim / yol tarifi (önce kontrol et - daha spesifik)
    match = PATTERN_ROUTE_EXTENDED.match(query_clean)
    if match:
        # 6 group var, hangi pattern eşleşti?
        origin = None
        destination = None
        for i in range(1, 7, 2):
            if match.group(i):
                origin = match.group(i).strip()
                destination = match.group(i + 1).strip()
                break

        if origin and destination:
            origin = ' '.join([w for w in origin.split() if w.lower() not in STOP_WORDS])
            destination = ' '.join([w for w in destination.split() if w.lower() not in STOP_WORDS])

            return {
                "type": "route",
                "confidence": 0.95,
                "origin": origin,
                "destination": destination,
                "raw_query": query,
                "error": None
            }

    # Pattern 1: X'den Y'ye rota
    match = PATTERN_ROUTE_1.match(query_clean)
    if match:
        origin = match.group(1).strip()
        destination = match.group(2).strip()

        # Stop words temizle
        origin = ' '.join([w for w in origin.split() if w.lower() not in STOP_WORDS])
        destination = ' '.join([w for w in destination.split() if w.lower() not in STOP_WORDS])

        return {
            "type": "route",
            "confidence": 0.95,
            "origin": origin,
            "destination": destination,
            "raw_query": query,
            "error": None
        }

    # Pattern 2: X ile Y arası
    match = PATTERN_ROUTE_2.match(query_clean)
    if match:
        origin = match.group(1).strip()
        destination = match.group(2).strip()

        origin = ' '.join([w for w in origin.split() if w.lower() not in STOP_WORDS])
        destination = ' '.join([w for w in destination.split() if w.lower() not in STOP_WORDS])

        return {
            "type": "route",
            "confidence": 0.90,
            "origin": origin,
            "destination": destination,
            "raw_query": query,
            "error": None
        }

    # Pattern 3: X, Y ve Z'yi gez
    match = PATTERN_MULTI_1.match(query_clean)
    if not match:
        match = PATTERN_MULTI_1b.match(query_clean)

    if match:
        loc1 = match.group(1).strip()
        loc2 = match.group(2).strip()
        loc3 = match.group(3).strip()

        locations = [loc1, loc2, loc3]

        # Stop words temizle
        locations = [
            ' '.join([w for w in loc.split() if w.lower() not in STOP_WORDS])
            for loc in locations
        ]

        return {
            "type": "multi",
            "confidence": 0.85,
            "locations": locations,
            "raw_query": query,
            "error": None
        }

    # Pattern 4: X'de neler var?
    match = PATTERN_POI_QUERY.match(query_clean)
    if not match:
        match = PATTERN_POI_QUERY_2.match(query_clean)
    if not match:
        match = PATTERN_POI_QUERY_3.match(query_clean)

    if match:
        location = match.group(1).strip() if match.group(1) else None

        if location:
            location = ' '.join([w for w in location.split() if w.lower() not in STOP_WORDS])

            return {
                "type": "poi",
                "confidence": 0.88,
                "location": location,
                "query_type": "search",
                "raw_query": query,
                "error": None
            }

    # Pattern 5: X'e git
    match = PATTERN_SINGLE_DEST.match(query_clean)
    if match:
        destination = match.group(1).strip()
        destination = ' '.join([w for w in destination.split() if w.lower() not in STOP_WORDS])

        return {
            "type": "single",
            "confidence": 0.80,
            "destination": destination,
            "raw_query": query,
            "error": None
        }

    # Hiçbir pattern eşleşmedi
    # Belki virgülle ayrılmış yer isimleri?
    if ',' in query_clean:
        locations = _extract_place_names(query_clean)
        if len(locations) >= 2:
            return {
                "type": "multi",
                "confidence": 0.60,
                "locations": locations,
                "raw_query": query,
                "error": None
            }

    # Son çare: tek bir yer ismi olabilir
    places = _extract_place_names(query_clean)
    if len(places) == 1:
        return {
            "type": "single",
            "confidence": 0.40,
            "destination": places[0],
            "raw_query": query,
            "error": None
        }

    return {
        "type": "unknown",
        "confidence": 0.0,
        "raw_query": query,
        "error": "Sorgu anlaşılamadı"
    }


# =============================================================================
# TEST FONKSİYONLARI
# =============================================================================

def test_parser():
    """
    Parser'ı test eder. Çeşitli sorgu örnekleri ile çalıştırır.
    """
    test_queries = [
        "Kadıköy'den Beşiktaş'a rota",
        "Kadıköy ile Taksim arası",
        "Kadıköy, Beşiktaş ve Taksim'i gez",
        "Kadıköy'de neler var?",
        "Taksim'e git",
        "İstanbul'dan Ankara'ya nasıl giderim",
        "Moda'da neleri önerirsin",
        "Beşiktaş, Ortaköy ve Eminönü'nü gezdir",
        "Kadıköy'den Taksim Meydanı'na yol tarifi",
        "Boğaz turu yap",  # Bilinmeyen tip
    ]

    print("=" * 60)
    print("NLP Engine Test Sonuçları")
    print("=" * 60)

    for query in test_queries:
        result = parse_query(query)
        print(f"\nSorgu: {query}")
        print(f"Tip: {result['type']} | Güven: {result['confidence']:.2f}")
        if result['error']:
            print(f"Hata: {result['error']}")
        else:
            if result.get('origin'):
                print(f"  Başlangıç: {result['origin']}")
            if result.get('destination'):
                print(f"  Varış: {result['destination']}")
            if result.get('locations'):
                print(f"  Yerler: {result['locations']}")
            if result.get('location'):
                print(f"  Konum: {result['location']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_parser()
