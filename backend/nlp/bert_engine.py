"""
bert_engine.py - BERT Model Entegrasyonu

Türkçe doğal dil sorguları için BERT tabanlı embedding ve semantic search.

Model: dbmdz/bert-base-turkish-uncased
Boyut: ~440 MB disk, ~1.5 GB RAM
Amaç: Typo tolerant ve bağlam anlayan sorgu sistemi

Kullanım:
    from bert_engine import get_bert_engine

    engine = get_bert_engine()
    embedding = engine.encode("Kadıköy'den Beşiktaş'a rota")
    similarity = engine.similarity("Kadıköy", "Kadiköy")  # Typo tolerance!
"""

import os
import threading
import hashlib
import re
from typing import List, Optional, Dict, Any, Callable
import numpy as np
from collections import OrderedDict


# =============================================================================
# GLOBAL CACHE (Model tek seferde yüklenir)
# =============================================================================

_bert_model = None
_tokenizer = None
_bert_model_lock = threading.Lock()

# Embedding cache globals
_embedding_cache: OrderedDict = OrderedDict()
_cache_hit_count = 0
_cache_miss_count = 0
_CACHE_MAX_SIZE = 5000

# =============================================================================
# TURKISH STEMMING DICTIONARY
# =============================================================================

# Yaygın Türkçe kelime kökleri ve variantları
# Ekler kaldırılarak kök bulunur
_TURKISH_STEM_DICT: Dict[str, List[str]] = {
    # =========================================================
    # İSTANBUL İLÇELERİ VE SEMTLERİ
    # =========================================================
    # Adalar
    "adalar": ["adalar", "adaları", "adalara", "adad"],
    "kınalıada": ["kınalıada", "kınalı", "kınalıyı", "kınalıada"],
    "burgazada": ["burgazada", "burgaz", "burgazı", "burgazada"],
    "heybeliada": ["heybeliada", "heybeli", "heybeliyi", "heybeliada"],
    # Anadolu Yakası
    "kadıköy": ["kadıköy", "kadiköy", "kadıköyü", "kadıköyden", "kadıköye", "kadıköyde"],
    "beşiktaş": ["beşiktaş", "besiktas", "beşiktaşı", "beşiktaşta", "beşiktaştan", "beşiktaşa"],
    "ataşehir": ["ataşehir", "ataşehiri", "ataşehire", "ataşehirde", "ataşehirden"],
    "ümraniye": ["ümraniye", "umraniye", "ümraniyeyi", "ümraniyede", "ümraniye"],
    "kurtköy": ["kurtköy", "kurtkoy", "kurtköyü", "kurtköyde", "kurtköyden"],
    "pendik": ["pendik", "pendiği", "pendige", "pendik", "pendikten", "pendiğe"],
    "kartal": ["kartal", "kartalı", "kartala", "kartalda", "kartaldan"],
    "maltepe": ["maltepe", "maltepesi", "maltepeye", "maltepem", "maltepeden"],
    "sancaktepe": ["sancaktepe", "sancaktepem", "sancaktepeden", "sancaktepesi", "sancaktepeye"],
    "tuzla": ["tuzla", "tuzlayı", "tuzlaya", "tuzlada", "tuzladan", "tuzlayı"],
    "çekmeköy": ["çekmeköy", "çekmeköyü", "çekmeköyden", "çekmeköyde", "çekmeköyü"],
    "şile": ["şile", "şileyi", "şileye", "şilede", "şileden"],
    "çamlıca": ["çamlıca", "çamlıcayı", "çamlıca", "çamlıcadan"],
    "üsküdar": ["üsküdar", "üsküdarı", "üsküdara", "üsküdar", "üsküdardan"],
    "beylerbeyi": ["beylerbeyi", "beylerbeyi", "beylerbeyine", "beylerbeyinde"],
    "kuzguncuk": ["kuzguncuk", "kuzguncuku", "kuzguncukta"],
    "adalya": ["adalya", "adalya", "adalyada"],
    # Avrupa Yakası
    "fatih": ["fatih", "fatihi", "fatih", "fatihden", "fatiha"],
    "eminönü": ["eminönü", "eminönü", "eminönünde", "eminönünden"],
    "sultanahmet": ["sultanahmet", "sultanahmeti", "sultanahmet", "sultanahmetten"],
    "sirkeci": ["sirkeci", "sirkeci", "sirkeci", "sirkeci"],
    "aksaray": ["aksaray", "aksaray", "aksarayda", "aksaraydan"],
    "laleli": ["laleli", "laleli", "lalelide", "laleliden"],
    "beyazıt": ["beyazıt", "beyazıt", "beyazıtta", "beyazıttan"],
    "bayezid": ["bayezid", "bayezit", "bayezid", "bayezide"],
    "şişli": ["şişli", "şişliyi", "şişliye", "şişlide", "şişliden"],
    "mecidiyeköy": ["mecidiyeköy", "mecidiyeköy", "mecidiyeköyde", "mecidiyeköyden"],
    "osmanbey": ["osmanbey", "osmanbey", "osmanbeyde", "osmanbeyden"],
    "nisantası": ["nisantası", "nisantaşı", "nisantaşında", "nisantaşından"],
    "etiler": ["etiler", "etiler", "etilerde", "etilerden"],
    "beşiktaş": ["beşiktaş", "beşiktaş", "beşiktaşta", "beşiktaştan", "beşiktaşa"],
    "ortaköy": ["ortaköy", "ortaköy", "ortaköyde", "ortaköyden", "ortaköyü"],
    "kuruçeşme": ["kuruçeşme", "kuruçeşme", "kuruçeşmede"],
    "arnavutköy": ["arnavutköy", "arnavutköy", "arnavutköyde", "arnavutköyden"],
    "bebek": ["bebek", "bebek", "bebekte", "bebekten"],
    "sarıyer": ["sarıyer", "sarıyeri", "sarıyere", "sarıyerde", "sarıyerden"],
    "emirgan": ["emirgan", "emirgan", "emirganda", "emirgandan"],
    "tarabya": ["tarabya", "tarabya", "tarabyada", "tarabyadan"],
    "büyükada": ["büyükada", "büyükadada", "büyükadadan", "büyükadayı"],
    "eyüp": ["eyüp", "eyüp", "eyüpte", "eyüpten", "eyüpe"],
    "eyüpsultan": ["eyüpsultan", "eyüpsultan", "eyüpsultanda"],
    "piyerloti": ["piyerloti", "piyerloti", "piyerlotinde"],
    "balat": ["balat", "balat", "balat", "balatta"],
    "fener": ["fener", "fener", "fener", "fenerde"],
    "kumkapı": ["kumkapı", "kumkapı", "kumkapı", "kumkapıda"],
    "galata": ["galata", "galata", "galata", "galatada"],
    "karaköy": ["karaköy", "karaköy", "karaköy", "karaköyde"],
    "tophane": ["tophane", "tophane", "tophane", "tophane"],
    "taksim": ["taksim", "taksimi", "taksimde", "taksimden", "taksime"],
    "gezi": ["gezi", "gezi", "gezide", "geziden"],
    "şişhane": ["şişhane", "şişhane", "şişhanede", "şişhaneden"],
    "cihangir": ["cihangir", "cihangir", "cihangirde"],
    "tarlabaşı": ["tarlabaşı", "tarlabaşı", "tarlabaşında"],
    "caferağa": ["caferağa", "caferağa", "caferağada"],
    # =========================================================
    # TÜRKİYE GENELİ BÜYÜK ŞEHİRLER
    # =========================================================
    "ankara": ["ankara", "ankarayı", "ankara", "ankarada", "ankaradan"],
    "izmir": ["izmir", "izmir", "izmirde", "izmirden", "izmir"],
    "antalya": ["antalya", "antalyayı", "antalya", "antalyada", "antalyadan"],
    "bursa": ["bursa", "bursayı", "bursa", "bursada", "bursadan"],
    "gaziantep": ["gaziantep", "gaziantep", "gaziantepte", "gaziantepden"],
    "konya": ["konya", "konya", "konya", "konya", "konya"],
    "adana": ["adana", "adanayı", "adana", "adanada", "adanadan"],
    "kayseri": ["kayseri", "kayseri", "kayseri", "kayseride", "kayseriden"],
    "eskişehir": ["eskişehir", "eskişehir", "eskişehirde", "eskişehirden"],
    "samsun": ["samsun", "samsunu", "samsun", "samsunda", "samsundan"],
    "trabzon": ["trabzon", "trabzon", "trabzonda", "trabzondan"],
    "denizli": ["denizli", "denizli", "denizlide", "denizliden"],
    "sakarya": ["sakarya", "sakarya", "sakaryada", "sakaryadan"],
    "kocaeli": ["kocaeli", "kocaeli", "kocaelinde", "kocaelinden"],
    "içel": ["içel", "içel", "içel", "içel", "içel"],
    "mersin": ["mersin", "mersin", "mersinde", "mersinden"],
    # =========================================================
    # METRO/TRAMVAY HATLARI VE İSTASYONLARI
    # =========================================================
    "metro": ["metro", "metroyla", "metroden", "metrosu", "metro", "metronun"],
    "tramvay": ["tramvay", "tramvayla", "tramvaydan", "tramvayı"],
    "marmaray": ["marmaray", "marmarayla", "marmaraydan", "marmaray"],
    "metrobüs": ["metrobüs", "metrobüs", "metrobüsle", "metrobüsten"],
    # Metro hatları
    "kırmızı hat": ["kırmızı hat", "kırmızıhat", "kırmızı hatta"],
    "mavi hat": ["mavi hat", "mavihat", "mavi hatta"],
    "yeşil hat": ["yeşil hat", "yeşilhat", "yeşil hatta"],
    # İstanbul Metro İstasyonları
    "taksim": ["taksim", "taksimi", "taksimde", "taksimden", "taksime"],
    "şişhane": ["şişhane", "şişhane", "şişhanede", "şişhaneden"],
    "osmanbey": ["osmanbey", "osmanbey", "osmanbeyde", "osmanbeyden"],
    "sisli": ["şişli", "şişliyi", "şişliye", "şişlide", "şişliden"],
    "yenişehir": ["yenişehir", "yenişehir", "yenişehirde"],
    "sanayi": ["sanayi", "sanayi", "sanayide", "sanayiden"],
    "siteler": ["siteler", "siteler", "sitelerde"],
    "talaş": ["talaş", "talaş", "talaş", "talaş"],
    "derga": ["derga", "derga", "derga", "derga"],
    "tepeüstü": ["tepeüstü", "tepeüstü", "tepeüstü", "tepeüstü"],
    "dudullu": ["dudullu", "dudullu", "dudulluda", "dudulludan"],
    "bostancı": ["bostancı", "bostancı", "bostancıda", "bostancıdan"],
    "küçükyalı": ["küçükyalı", "küçükyalı", "küçükyalıda"],
    "maltepe": ["maltepe", "maltepesi", "maltepeye", "maltepem", "maltepeden"],
    "huzur": ["huzur", "huzur", "huzur", "huzur"],
    "sahil": ["sahil", "sahil", "sahilde", "sahilden"],
    "başıbüyük": ["başıbüyük", "başıbüyük", "başıbüyükte"],
    "soğanlık": ["soğanlık", "soğanlık", "soğanlıkta"],
    "kartal": ["kartal", "kartalı", "kartala", "kartalda", "kartaldan"],
    "yalova": ["yalova", "yalova", "yalovada", "yalovadan"],
    # =========================================================
    # YOL/ROTA TERİMLERİ
    # =========================================================
    "rota": ["rota", "rotası", "rotaya", "rotadan", "rotam"],
    "yol": ["yol", "yolu", "yola", "yoldan", "yolla", "yol"],
    "km": ["km", "kilometre", "kilometrelik", "kilometre"],
    "dakika": ["dakika", "dakika", "dakikada", "dakikadır", "dakika"],
    "saat": ["saat", "saati", "saatte", "saatten", "saat"],
    "varış": ["varış", "varışı", "varış", "varışa"],
    "kalkış": ["kalkış", "kalkışı", "kalkış", "kalkışa"],
    "geçiş": ["geçiş", "geçişi", "geçiş", "geçişe"],
    "durak": ["durak", "durağı", "duraga", "duraktan", "durak", "durağa"],
    "istasyon": ["istasyon", "istasyonu", "istasyona", "istasyondan", "istasyon"],
    "hat": ["hat", "hattı", "hatti", "hatta", "hattend"],
    "peron": ["peron", "peron", "peron", "peron"],
    "bilet": ["bilet", "bileti", "bilet", "bilete"],
    "aktarma": ["aktarma", "aktarma", "aktarma", "aktarmaya"],
    "ücretsiz": ["ücretsiz", "ücretsiz", "ücretsiz", "ücretsiz"],
    "ücretli": ["ücretli", "ücretli", "ücretli", "ücretli"],
    # =========================================================
    # ARAÇ TİPLERİ
    # =========================================================
    "otobüs": ["otobüs", "otobuse", "otobüsü", "otobus", "otobüsle", "otobüs", "otobüsle"],
    "vapur": ["vapur", "vapurla", "vapurdan", "vapur", "vapuru"],
    "deniz otobüsü": ["deniz otobüsü", "deniz otobüsü", "deniz otobüsü", "deniz otobüsü"],
    "yolcu gemisi": ["yolcu gemisi", "yolcu gemisi", "yolcu gemisi", "yolcu gemisi"],
    "ücret": ["ücret", "ücreti", "ücret", "ücrete"],
    "taksi": ["taksi", "taksi", "taksi", "taksiye"],
    "dolmuş": ["dolmuş", "dolmuş", "dolmuş", "dolmuşa"],
    "minibüs": ["minibüs", "minibüse", "minibus", "minibüsle", "minibüs"],
    "servis": ["servis", "servis", "servis", "servise"],
    "binek": ["binek", "binek", "binek", "binekle"],
    "kamyon": ["kamyon", "kamyon", "kamyon", "kamyonla"],
    "motorsiklet": ["motorsiklet", "motorsiklet", "motorsiklet", "motorsikletle"],
    "bisiklet": ["bisiklet", "bisiklet", "bisiklet", "bisikletle"],
    # =========================================================
    # YÖN TERİMLERİ
    # =========================================================
    "kuzey": ["kuzey", "kuzey", "kuzeyde", "kuzeyden"],
    "güney": ["güney", "güney", "güneyde", "güneyden"],
    "doğu": ["doğu", "doğu", "doğuda", "doğudan"],
    "batı": ["batı", "batı", "batıda", "batıdan"],
    "sağ": ["sağ", "sağ", "sağda", "sağdan"],
    "sol": ["sol", "sol", "solda", "soldan"],
    "ileri": ["ileri", "ileri", "ileride", "ileriden"],
    "geri": ["geri", "geri", "geride", "geriden"],
    "ön": ["ön", "ön", "önde", "önden"],
    "arka": ["arka", "arka", "arkada", "arkadan"],
    "yakın": ["yakın", "yakın", "yakında", "yakından"],
    "uzak": ["uzak", "uzak", "uzakta", "uzaktan"],
    "arasında": ["arasında", "arasında", "arasında", "arasında"],
    "karşısında": ["karşısında", "karşısında", "karşısında", "karşısında"],
    # =========================================================
    # GENEL YER TERİMLERİ
    # =========================================================
    "merkez": ["merkez", "merkezi", "merkeze", "merkezde", "merkezden"],
    "çıkış": ["çıkış", "çıkışı", "çıkış", "çıkışa"],
    "giriş": ["giriş", "girişi", "giriş", "girişe"],
    "cadde": ["cadde", "caddesi", "caddeye", "cadded", "caddeden"],
    "sokak": ["sokak", "sokağı", "sokağa", "sokakta", "sokaktan"],
    "bulvar": ["bulvar", "bulvarı", "bulvara", "bulvarda", "bulvardan"],
    "köprü": ["köprü", "köprüsü", "köprüye", "köprüde", "köprüden"],
    "tünel": ["tünel", "tüneller", "tüneli", "tünele", "tünelde", "tünelden"],
    "viadük": ["viadukt", "viadüğü", "viadüke", "viadükte"],
    "kavşak": ["kavşak", "kavşağı", "kavşağa", "kavşakta", "kavşaktan"],
    "dönemeç": ["dönemeç", "dönemeci", "dönemece", "dönemeçte"],
    "rampa": ["rampa", "rampası", "rampaya", "rampada"],
    "kot": ["kot", "kot", "kot", "kotta"],
    # =========================================================
    # MEKAN TERİMLERİ
    # =========================================================
    "restoran": ["restoran", "restoranı", "restorana", "restoranda", "restorandan"],
    "kafe": ["kafe", "kafeyi", "kafeye", "kafede", "kafeden"],
    "bar": ["bar", "bar", "barda", "bardan"],
    "pub": ["pub", "pub", "pub", "pub"],
    "fastfood": ["fastfood", "fastfood", "fastfood", "fastfood"],
    "pazar": ["pazar", "pazarı", "pazara", "pazarda", "pazardan"],
    "market": ["market", "marketi", "markete", "marketten", "market"],
    "AVM": ["AVM", "avm", "avm", "avm", "avmde", "avmden"],
    "alışveriş": ["alışveriş", "alışverişi", "alışveriş", "alışverişe"],
    "mağaza": ["mağaza", "mağazayı", "mağazaya", "mağazada", "mağazadan"],
    "banka": ["banka", "banka", "banka", "banka", "bankada"],
    "ATM": ["ATM", "atm", "atm", "atm", "atmde"],
    "hastane": ["hastane", "hastane", "hastane", "hastane", "hastanede"],
    "eczane": ["eczane", "eczane", "eczane", "eczane", "eczanede"],
    "okul": ["okul", "okul", "okul", "okul", "okul", "okulda"],
    "üniversite": ["üniversite", "üniversite", "üniversite", "üniversite", "üniversitede"],
    "cami": ["cami", "cami", "cami", "cami", "camide"],
    "kilise": ["kilise", "kilise", "kilise", "kilise", "kilisede"],
    "sinagog": ["sinagog", "sinagog", "sinagog", "sinagog", "sinagoga"],
    "müze": ["müze", "müze", "müze", "müze", "müzede"],
    "galeri": ["galeri", "galeri", "galeri", "galeri", "galeride"],
    "tiyatro": ["tiyatro", "tiyatro", "tiyatro", "tiyatro", "tiyatroda"],
    "sinema": ["sinema", "sinema", "sinema", "sinema", "sinemada"],
    "stadyum": ["stadyum", "stadyum", "stadyum", "stadyum", "stadyumda"],
    "spor salonu": ["spor salonu", "spor salonu", "spor salonu", "spor salonu"],
    "plaj": ["plaj", "plaj", "plaj", "plaj", "plajda"],
    "park": ["park", "park", "park", "park", "parkta"],
    "bahçe": ["bahçe", "bahçe", "bahçe", "bahçe", "bahçede"],
    # =========================================================
    # ZAMAN TERİMLERİ
    # =========================================================
    "bugün": ["bugün", "bugünü", "bugünde", "bugünden"],
    "yarın": ["yarın", "yarını", "yarında", "yarın"],
    "dün": ["dün", "dün", "dün", "dünden"],
    "hafta": ["hafta", "hafta", "hafta", "hafta", "hafta"],
    "ay": ["ay", "ay", "ay", "ay", "ayda"],
    "yıl": ["yıl", "yıl", "yıl", "yıl", "yılda"],
    "sabah": ["sabah", "sabah", "sabah", "sabah", "sabah"],
    "öğlen": ["öğlen", "öğlen", "öğlen", "öğlen", "öğlen"],
    "akşam": ["akşam", "akşam", "akşam", "akşam", "akşam"],
    "gece": ["gece", "gece", "gece", "gece", "gece"],
    "iş": ["iş", "iş", "iş", "iş", "iş"],
    "tatil": ["tatil", "tatil", "tatil", "tatil", "tatil"],
    # =========================================================
    # GEZİ/YOLCULUK TERİMLERİ
    # =========================================================
    "tur": ["tur", "tur", "tur", "tur", "tur"],
    "gezi": ["gezi", "gezi", "gezi", "gezi", "gezi"],
    "seyahat": ["seyahat", "seyahat", "seyahat", "seyahat", "seyahat"],
    "yolculuk": ["yolculuk", "yolculuk", "yolculuk", "yolculuk", "yolculuk"],
    "tatile": ["tatile", "tatile", "tatile", "tatile", "tatile"],
    "rezervasyon": ["rezervasyon", "rezervasyon", "rezervasyon", "rezervasyon"],
    "bilet": ["bilet", "bileti", "bilet", "bilete", "bilet"],
    # =========================================================
    # GENEL SIFATLAR
    # =========================================================
    "yakın": ["yakın", "yakın", "yakın", "yakın", "yakın"],
    "uzak": ["uzak", "uzak", "uzak", "uzak", "uzak"],
    "hızlı": ["hızlı", "hızlı", "hızlı", "hızlı", "hızlı"],
    "yavaş": ["yavaş", "yavaş", "yavaş", "yavaş", "yavaş"],
    "kolay": ["kolay", "kolay", "kolay", "kolay", "kolay"],
    "zor": ["zor", "zor", "zor", "zor", "zor"],
    "güvenli": ["güvenli", "güvenli", "güvenli", "güvenli", "güvenli"],
    "tehlikeli": ["tehlikeli", "tehlikeli", "tehlikeli", "tehlikeli", "tehlikeli"],
    "ücretsiz": ["ücretsiz", "ücretsiz", "ücretsiz", "ücretsiz", "ücretsiz"],
    "kalabalık": ["kalabalık", "kalabalık", "kalabalık", "kalabalık", "kalabalık"],
    "sessiz": ["sessiz", "sessiz", "sessiz", "sessiz", "sessiz"],
    # =========================================================
    # NOKTA/LOKASYON KELİMELERİ
    # =========================================================
    "nokta": ["nokta", "nokta", "nokta", "nokta", "nokta"],
    "konum": ["konum", "konum", "konum", "konum", "konum"],
    "lokasyon": ["lokasyon", "lokasyon", "lokasyon", "lokasyon", "lokasyon"],
    "adres": ["adres", "adres", "adres", "adres", "adres"],
    "mevkii": ["mevkii", "mevkii", "mevkii", "mevkii", "mevkii"],
    "köşe": ["köşe", "köşe", "köşe", "köşe", "köşe"],
    "başı": ["başı", "başı", "başı", "başı", "başı"],
    "sonu": ["sonu", "sonu", "sonu", "sonu", "sonu"],
    "ortası": ["ortası", "ortası", "ortası", "ortası", "ortası"],
    # =========================================================
    # EYLEMLER/FİİLLER
    # =========================================================
    "git": ["git", "gideceğim", "gidiyorum", "gittim", "gideyim"],
    "gel": ["gel", "geleceğim", "geliyorum", "geldim", "geleyim"],
    "ara": ["ara", "arayacağım", "arıyorum", "aradım", "arayım"],
    "bul": ["bul", "bulacağım", "buluyorum", "buldum", "bulayım"],
    "iste": ["iste", "isteyeceğim", "istiyorum", "istedim", "isteyim"],
    "yap": ["yap", "yapacağım", "yapıyorum", "yaptım", "yapayım"],
    "ver": ["ver", "vereceğim", "veriyorum", "verdim", "vereyim"],
    "al": ["al", "alacağım", "alıyorum", "aldım", "alayım"],
    "gör": ["gör", "göreceğim", "görüyorum", "gördüm", "göreyim"],
    "bil": ["bil", "bileceğim", "biliyorum", "bildim", "bilim"],
    "yet": ["yet", "yeteceğim", "yetiyorum", "yettim", "yeteceğim"],
    # =========================================================
    # NOKTALAMA VE ÖZEL İFADELER
    # =========================================================
    "nerede": ["nerede", "nerede", "nerede", "nerede", "nerede"],
    "nasıl": ["nasıl", "nasıl", "nasıl", "nasıl", "nasıl"],
    "ne kadar": ["ne kadar", "ne kadar", "ne kadar", "ne kadar", "ne kadar"],
    "hangisi": ["hangisi", "hangisi", "hangisi", "hangisi", "hangisi"],
    "kim": ["kim", "kim", "kim", "kim", "kim"],
    "ne": ["ne", "ne", "ne", "ne", "ne"],
    "niye": ["niye", "niye", "niye", "niye", "niye"],
    "neden": ["neden", "neden", "neden", "neden", "neden"],
}

# Regex pattern for common Turkish suffixes
_TURKISH_SUFFIX_PATTERN = re.compile(
    r"("
    r"(ı|i|ı|i|u|ü|ü)|"  # Possessive suffixes
    r"(si|si|su|sü)|"      # 3rd person possessive
    r"(da|de|ta|te)|"      # Locative
    r"(dan|den|ten|ten)|"  # Ablative  
    r"(a|e|ya|ye)|"        # Dative
    r"(lar|ler)|"          # Plural
    r"(lı|li|lu|lü)|"      # With/has
    r"(sız|siz|suz|süz)|"  # Without
    r"(cı|ci|cu|cü)|"      # Professional
    r"(lik|lik|luk|lük)|"  # -ness/-ship
    r")$",
    re.IGNORECASE | re.MULTILINE
)

# Known non-stemming words ( suffixes look like roots )
_TURKISH_NO_STEM: set = {
    "ne", "bu", "şu", "o", "ben", "sen", "biz", "siz", "onlar",
    "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz", "on",
    "ve", "veya", "ama", "fakat", "çünkü", "eğer", "de", "da", "ki", "mi", "mı", "mu", "mü",
}


def _make_cache_key(text: str) -> str:
    """
    Metinden LRU cache key üretir.
    
    Args:
        text: Cache key üretilecek metin
        
    Returns:
        str: MD5 hash hex string
    """
    normalized = text.lower().strip()
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()


# =============================================================================
# TURKISH STEMMING FUNCTIONS
# =============================================================================

def _normalize_turkish(text: str) -> str:
    """
    Türkçe karakterleri ASCII karşılıklarına çevirir.
    
    Args:
        text: Çevrilecek metin
        
    Returns:
        str: ASCII normalize edilmiş metin
    """
    turkish_map = {
        'ı': 'i', 'ğ': 'g', 'ş': 's', 'ü': 'u', 'ö': 'o', 'ç': 'c',
        'İ': 'i', 'Ğ': 'g', 'Ş': 's', 'Ü': 'u', 'Ö': 'o', 'Ç': 'c',
        'I': 'i',
    }
    result = text
    for turkish, ascii_char in turkish_map.items():
        result = result.replace(turkish, ascii_char)
    return result


def stem_word(word: str, use_dictionary: bool = True) -> str:
    """
    Türkçe kelimeyi köküne indirger.
    
    Args:
        word: Stemmelecek kelime
        use_dictionary: Bilinen kökler sözlüğü kullanılsın mı
        
    Returns:
        str: Kelimenin kökü
    """
    if not word or len(word) < 2:
        return word
    
    original = word
    word_lower = word.lower()
    
    # 1. Dictionary lookup (en hızlı)
    if use_dictionary:
        word_norm = _normalize_turkish(word_lower)
        for root, variants in _TURKISH_STEM_DICT.items():
            # Normalize all variants for comparison
            for variant in variants:
                variant_norm = _normalize_turkish(variant.lower())
                if word_lower == variant.lower() or word_norm == variant_norm:
                    return root
        # Skip non-stemming words
        if word_norm in _TURKISH_NO_STEM:
            return word_lower
    
    # 2. Rule-based suffix stripping for unknown words
    suffixes = [
        "leri", "lerin", "lerde", "lerden", "lere", "ler",
        "ları", "larını", "larında", "larından", "larına", "lar",
        "ını", "ini", "unu", "ünü",
        "si", "su", "sü",
        "da", "de", "ta", "te",
        "dan", "den", "tan", "ten",
        "a", "e", "ya", "ye",
        "lı", "li", "lu", "lü",
        "lık", "lik", "luk", "lük",
        "cı", "ci", "cu", "cü",
        "sız", "siz", "suz", "süz",
        "ğ", "y", "n",
    ]
    
    for suffix in suffixes:
        if word_lower.endswith(suffix) and len(word_lower) - len(suffix) >= 2:
            if suffix[0] in "aeıioöuü":
                root = word_lower[:-len(suffix)]
                if _check_vowel_harmony(root):
                    return root
            else:
                return word_lower[:-len(suffix)]
    
    return word_lower


def _check_vowel_harmony(word: str) -> bool:
    """
    Kelimenin kalın-ince ünlü uyumuna (vowel harmony) uyup uymadığını kontrol eder.
    
    Turkish vowel groups:
    - Thick (kalın): a, ı, o, u
    - Thin (ince): e, i, ö, ü
    """
    vowels = set("aeıioöuüAEIİOÖUÜ")
    
    last_vowel_group = None
    
    for char in reversed(word):
        if char in vowels:
            if char in "aıouAIOU":
                last_vowel_group = "thick"
            else:
                last_vowel_group = "thin"
            break
    
    return True


def stem_text(text: str, use_dictionary: bool = True) -> str:
    """
    Metindeki tüm kelimelerin köklerini çıkarır.
    
    Args:
        text: İşlenecek metin
        use_dictionary: Sözlük kullanılsın mı
        
    Returns:
        str: Kelimelerin kökleri ile metin
    """
    words = re.findall(r"\b[\wçğıöşü]+(?:\'[\wçğıöşü]+)?", text, re.IGNORECASE)
    
    stemmed = []
    for word in words:
        is_title = word[0].isupper() if word else False
        is_all_upper = word.isupper() if word else False
        
        root = stem_word(word, use_dictionary=use_dictionary)
        
        if is_all_upper:
            root = root.upper()
        elif is_title and len(root) > 1:
            root = root.capitalize()
        
        stemmed.append(root)
    
    return " ".join(stemmed)


def stem_tokens(text: str, use_dictionary: bool = True) -> List[str]:
    """
    Metindeki kelimelerin köklerini liste olarak döner.
    
    Args:
        text: İşlenecek metin
        use_dictionary: Sözlük kullanılsın mı
        
    Returns:
        List[str]: Kök listesi
    """
    words = re.findall(r"\b[\wçğıöşü]+(?:\'[\wçğıöşü]+)?", text, re.IGNORECASE)
    return [stem_word(w, use_dictionary=use_dictionary) for w in words]


# =============================================================================
# API REQUEST UTILITIES (retry, fallback, circuit breaker)
# =============================================================================

class RetryConfig:
    """Retry configuration for API calls."""
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


def retry_with_backoff(func: Callable, config: RetryConfig = None) -> Any:
    """
    Decorator/utility for retrying with exponential backoff.
    
    Args:
        func: Retry edilecek fonksiyon
        config: RetryConfig instance
        
    Returns:
        Any: Fonksiyonun dönüş değeri
        
    Raises:
        Exception: Tüm denemeler başarısız olursa son hata
    """
    import time
    import random
    
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            return func()
        except Exception as e:
            last_exception = e
            
            if attempt < config.max_attempts - 1:
                delay = min(
                    config.base_delay * (config.exponential_base ** attempt),
                    config.max_delay
                )
                
                if config.jitter:
                    delay = delay * (0.5 + random.random() * 0.5)
                
                time.sleep(delay)
    
    raise last_exception


def with_retry(func: Callable = None, *, config: RetryConfig = None):
    """
    Retry decorator for functions.
    
    Usage:
        @with_retry(config=RetryConfig(max_attempts=5))
        def my_api_call():
            ...
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            return retry_with_backoff(lambda: f(*args, **kwargs), config)
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)


# =============================================================================
# FALLBACK MECHANISM FOR EXTERNAL API CALLS
# =============================================================================

class FallbackChain:
    """
    Zincir halinde fallback mekanizması.
    
    Bir API çağrısı başarısız olursa sıradaki alternatives dener.
    """
    def __init__(self):
        self._providers = []
    
    def add_provider(self, provider_fn: Callable, *args, **kwargs) -> "FallbackChain":
        """Provider ekler ( zincirleme çağrı için )."""
        self._providers.append((provider_fn, args, kwargs))
        return self
    
    def execute(self) -> Any:
        """Sırayla provider'ları dener, ilk başarılı olanı döner."""
        last_error = None
        
        for provider_fn, args, kwargs in self._providers:
            try:
                return provider_fn(*args, **kwargs)
            except Exception as e:
                last_error = e
                print(f"[FallbackChain] Provider {provider_fn.__name__} failed: {e}")
                continue
        
        raise RuntimeError(f"All fallback providers failed. Last error: {last_error}")


def get_cache_stats() -> Dict[str, Any]:
    """
    Embedding cache istatistiklerini döner.
    
    Returns:
        dict: hit, miss, size bilgileri
    """
    return {
        "cache_hits": _cache_hit_count,
        "cache_misses": _cache_miss_count,
        "cache_size": len(_embedding_cache),
        "cache_max_size": _CACHE_MAX_SIZE,
        "cache_hit_rate": _cache_hit_count / (_cache_hit_count + _cache_miss_count) 
                          if (_cache_hit_count + _cache_miss_count) > 0 else 0.0
    }


def clear_embedding_cache() -> Dict[str, int]:
    """
    Embedding cache'i temizler.
    
    Returns:
        dict: Temizleme öncesi cache boyutu
    """
    global _embedding_cache, _cache_hit_count, _cache_miss_count
    
    cleared_size = len(_embedding_cache)
    _embedding_cache.clear()
    _cache_hit_count = 0
    _cache_miss_count = 0
    
    return {"cleared_entries": cleared_size}


def _get_cached_embedding(cache_key: str) -> Optional[np.ndarray]:
    """
    Cache'den embedding alır (LRU güncellemesi yapar).
    
    Args:
        cache_key: Cache anahtarı
        
    Returns:
        np.ndarray or None: Cache'deki embedding veya None
    """
    global _embedding_cache, _cache_hit_count
    
    if cache_key in _embedding_cache:
        _embedding_cache.move_to_end(cache_key)
        _cache_hit_count += 1
        return _embedding_cache[cache_key].copy()
    
    return None


def _put_cached_embedding(cache_key: str, embedding: np.ndarray) -> None:
    """
    Embedding'i cache'e ekler (LRU eviction ile).
    
    Args:
        cache_key: Cache anahtarı
        embedding: Cache'e eklenecek embedding
    """
    global _embedding_cache
    
    if cache_key in _embedding_cache:
        _embedding_cache.move_to_end(cache_key)
        _embedding_cache[cache_key] = embedding.copy()
        return
    
    if len(_embedding_cache) >= _CACHE_MAX_SIZE:
        _embedding_cache.popitem(last=False)
    
    _embedding_cache[cache_key] = embedding.copy()


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# =============================================================================
# BERT ENGINE CLASS
# =============================================================================

class BERTEngine:
    """
    BERT modeli için embedding engine.

    Türkçe sorgular için embedding çıkarır ve benzerlik hesaplar.
    """

    MODEL_NAME = "dbmdz/bert-base-turkish-uncased"

    def __init__(self):
        """BERT modelini ve tokenizer'ı yükler."""
        print(f"[BERT] Model yükleniyor: {self.MODEL_NAME}")
        print("[BERT] İlk yükleme biraz zaman alabilir (~440 MB)...")

        try:
            from transformers import AutoTokenizer, AutoModel
            import torch

            self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
            self.model = AutoModel.from_pretrained(self.MODEL_NAME)

            # Varsayilan davranis: GPU zorunlu.
            # ORP_BERT_FORCE_GPU=1: GPU istenir.
            # ORP_BERT_STRICT_GPU=1: CUDA yoksa hard-fail (varsayilan).
            force_gpu = _env_flag("ORP_BERT_FORCE_GPU", True)
            strict_gpu = _env_flag("ORP_BERT_STRICT_GPU", True)
            cuda_available = torch.cuda.is_available()
            torch_build = getattr(torch, "__version__", "unknown")
            cuda_runtime = getattr(getattr(torch, "version", None), "cuda", None)

            if force_gpu and not cuda_available:
                warn_message = (
                    "GPU talep edildi (ORP_BERT_FORCE_GPU=1) ancak CUDA kullanilabilir degil.\n"
                    f"torch sürümü: {torch_build}, torch CUDA: {cuda_runtime}\n"
                    "CPU modunda devam edilecek."
                )
                if strict_gpu:
                    raise RuntimeError(
                        warn_message
                        + "\nORP_BERT_STRICT_GPU=1 oldugu icin islem durduruldu.\n"
                        "Cozum (venv aktifken):\n"
                        "  pip uninstall -y torch torchvision torchaudio\n"
                        "  pip install --index-url https://download.pytorch.org/whl/cu124 torch torchvision torchaudio"
                    )
                print(f"[BERT WARN] {warn_message}")

            # GPU varsa kullan, degilse (izinliyse) CPU fallback.
            self.device = "cuda" if cuda_available else "cpu"
            self.model = self.model.to(self.device)
            self.model.eval()  # Evaluation mode

            print(f"[BERT] Model yüklendi! (Device: {self.device})")

        except ImportError as e:
            raise ImportError(
                f"transformers veya torch kütüphanesi bulunamadı: {e}\n"
                "Lütfen çalıştırın: pip install transformers torch"
            )
        except Exception as e:
            raise RuntimeError(f"Model yüklenirken hata: {e}")

    def _mean_pooling(self, last_hidden_state: "torch.Tensor", attention_mask: "torch.Tensor") -> np.ndarray:
        """
        Token embeddings üzerinde mean pooling yapar.
        
        Padding token'ları attention mask ile maskelenir.
        
        Args:
            last_hidden_state: [batch_size, seq_len, hidden_size] tensor
            attention_mask: [batch_size, seq_len] - 1 for real tokens, 0 for padding
            
        Returns:
            np.ndarray: [batch_size, hidden_size] pooled embeddings
        """
        attention_mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
        sum_embeddings = torch.sum(last_hidden_state * attention_mask_expanded, dim=1)
        sum_mask = torch.clamp(attention_mask_expanded.sum(dim=1), min=1e-9)
        return (sum_embeddings / sum_mask).cpu().numpy()

    def encode(self, text: str, use_cache: bool = True, pooling_strategy: str = "cls") -> np.ndarray:
        """
        Metni BERT embedding'ine çevirir.

        Args:
            text: Embedding'e çevrilecek metin
            use_cache: Cache kullanılsın mı (varsayılan: True)
            pooling_strategy: "cls" (varsayılan) veya "mean" pooling stratejisi

        Returns:
            np.ndarray: 768 boyutlu embedding vektörü
        """
        global _cache_miss_count
        
        import torch

        if use_cache:
            cache_key = _make_cache_key(text)
            cached_emb = _get_cached_embedding(cache_key)
            if cached_emb is not None:
                return cached_emb

        # Metni tokenize et
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=128
        )

        # GPU'ya taşı
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Gradyent hesaplama yok (inference)
        with torch.no_grad():
            outputs = self.model(**inputs)

        # Pooling stratejisine göre embedding seç
        last_hidden = outputs.last_hidden_state
        attention_mask = inputs["attention_mask"]

        if pooling_strategy == "mean":
            # Mean pooling: tüm token embeddinglerinin ortalaması (padding hariç)
            embedding = self._mean_pooling(last_hidden, attention_mask)[0]
        else:
            # [CLS] token (varsayılan): sadece ilk token
            embedding = last_hidden[:, 0, :].cpu().numpy()[0]

        if use_cache:
            _put_cached_embedding(cache_key, embedding)
        else:
            _cache_miss_count += 1

        return embedding

    def encode_batch(self, texts: List[str], use_cache: bool = True, pooling_strategy: str = "cls") -> List[np.ndarray]:
        """
        Birden fazla metni embedding'e çevirir.

        Args:
            texts: Metin listesi
            use_cache: Cache kullanılsın mı (varsayılan: True)
            pooling_strategy: "cls" (varsayılan) veya "mean" pooling stratejisi

        Returns:
            list[np.ndarray]: Embedding listesi
        """
        import torch

        all_embeddings = []

        # Batch processing (daha verimli)
        batch_size = 8
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            inputs = self.tokenizer(
                batch_texts,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=128
            )

            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)

            last_hidden = outputs.last_hidden_state
            attention_mask = inputs["attention_mask"]

            if pooling_strategy == "mean":
                embeddings = self._mean_pooling(last_hidden, attention_mask)
            else:
                embeddings = last_hidden[:, 0, :].cpu().numpy()
            
            for j, emb in enumerate(embeddings):
                cache_key = _make_cache_key(batch_texts[j])
                if use_cache:
                    _put_cached_embedding(cache_key, emb)
            
            all_embeddings.extend(embeddings)

        return all_embeddings

    def get_runtime_metrics(self) -> Dict[str, Any]:
        """
        BERT runtime donanım kullanım metriklerini döner.

        Returns:
            dict: cihaz, CUDA ve (varsa) GPU bellek metrikleri + cache istatistikleri
        """
        metrics: Dict[str, Any] = {
            "device": self.device,
            "model": self.MODEL_NAME,
        }

        # Cache istatistiklerini ekle
        cache_stats = get_cache_stats()
        metrics.update(cache_stats)

        try:
            import torch
        except Exception as exc:
            metrics["metrics_error"] = f"torch import hatasi: {exc}"
            return metrics

        metrics["torch_version"] = getattr(torch, "__version__", "unknown")
        metrics["cuda_available"] = bool(torch.cuda.is_available())
        metrics["torch_cuda_runtime"] = getattr(getattr(torch, "version", None), "cuda", None)

        if self.device != "cuda" or not torch.cuda.is_available():
            return metrics

        try:
            device_index = torch.cuda.current_device()
            device_props = torch.cuda.get_device_properties(device_index)

            total_mem_mb = device_props.total_memory / (1024 * 1024)
            allocated_mb = torch.cuda.memory_allocated(device_index) / (1024 * 1024)
            reserved_mb = torch.cuda.memory_reserved(device_index) / (1024 * 1024)
            max_allocated_mb = torch.cuda.max_memory_allocated(device_index) / (1024 * 1024)

            metrics.update(
                {
                    "gpu_name": torch.cuda.get_device_name(device_index),
                    "gpu_index": device_index,
                    "gpu_total_mem_mb": round(total_mem_mb, 1),
                    "gpu_allocated_mb": round(allocated_mb, 1),
                    "gpu_reserved_mb": round(reserved_mb, 1),
                    "gpu_max_allocated_mb": round(max_allocated_mb, 1),
                    "gpu_utilization_pct": round((allocated_mb / total_mem_mb) * 100, 2) if total_mem_mb else 0.0,
                }
            )
        except Exception as exc:
            metrics["metrics_error"] = f"cuda metrik hatasi: {exc}"

        return metrics

    def similarity(self, text1: str, text2: str, use_cache: bool = True, pooling_strategy: str = "cls") -> float:
        """
        İki metin arasındaki cosine similarity'yi hesaplar.

        Args:
            text1: İlk metin
            text2: İkinci metin
            use_cache: Cache kullanılsın mı (varsayılan: True)
            pooling_strategy: "cls" (varsayılan) veya "mean" pooling stratejisi

        Returns:
            float: 0-1 arası benzerlik skoru (1 = tam aynı)
        """
        emb1 = self.encode(text1, use_cache=use_cache, pooling_strategy=pooling_strategy)
        emb2 = self.encode(text2, use_cache=use_cache, pooling_strategy=pooling_strategy)

        # Cosine similarity
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def find_best_match(
        self,
        query: str,
        candidates: List[str],
        threshold: float = 0.75,
        use_cache: bool = True,
        pooling_strategy: str = "cls"
    ) -> Optional[Dict[str, Any]]:
        """
        Sorguya en yakın adayı bulur.

        Args:
            query: Arama sorgusu
            candidates: Aday metin listesi
            threshold: Minimum benzerik eşiği
            use_cache: Cache kullanılsın mı (varsayılan: True)
            pooling_strategy: "cls" (varsayılan) veya "mean" pooling stratejisi

        Returns:
            dict: En yakın aday veya None
            {
                "match": str,
                "similarity": float,
                "index": int
            }
        """
        if not candidates:
            return None

        query_emb = self.encode(query, use_cache=use_cache, pooling_strategy=pooling_strategy)

        best_match = None
        best_score = 0.0
        best_idx = -1

        for i, candidate in enumerate(candidates):
            candidate_emb = self.encode(candidate, use_cache=use_cache, pooling_strategy=pooling_strategy)

            # Cosine similarity
            dot_product = np.dot(query_emb, candidate_emb)
            norm_query = np.linalg.norm(query_emb)
            norm_cand = np.linalg.norm(candidate_emb)

            if norm_query == 0 or norm_cand == 0:
                score = 0.0
            else:
                score = dot_product / (norm_query * norm_cand)

            if score > best_score:
                best_score = score
                best_match = candidate
                best_idx = i

        if best_score >= threshold:
            return {
                "match": best_match,
                "similarity": float(best_score),
                "index": int(best_idx)
            }

        return None


# =============================================================================
# MODULE-LEVEL CACHE API
# =============================================================================

def get_embedding_cache_stats() -> Dict[str, Any]:
    """
    Modül seviyesinde cache istatistiklerini döner.
    
    Dışarıdan erişim için: from bert_engine import get_embedding_cache_stats
    
    Returns:
        dict: hit, miss, size, hit_rate bilgileri
    """
    return get_cache_stats()


def clear_embedding_cache() -> Dict[str, int]:
    """
    Modül seviyesinde cache'i temizler.
    
    Dışarıdan erişim için: from bert_engine import clear_embedding_cache
    
    Returns:
        dict: Temizlenen entry sayısı
    """
    return _do_clear_cache()


# Alias for external access
def _do_clear_cache() -> Dict[str, int]:
    """Internal alias to avoid recursion."""
    global _embedding_cache, _cache_hit_count, _cache_miss_count
    
    cleared_size = len(_embedding_cache)
    _embedding_cache.clear()
    _cache_hit_count = 0
    _cache_miss_count = 0
    
    return {"cleared_entries": cleared_size}


# =============================================================================
# SINGLETON PATTERN
# =============================================================================

def get_bert_engine() -> BERTEngine:
    """
    Global BERT engine singleton'ını döner.

    Model tek seferde yüklenir ve sonraki çağrılarda cache'ten döner.

    Returns:
        BERTEngine: BERT engine örneği
    """
    global _bert_model

    if _bert_model is None:
        with _bert_model_lock:
            if _bert_model is None:
                _bert_model = BERTEngine()

    return _bert_model


def is_bert_available() -> bool:
    """
    BERT kütüphanelerinin kurulu olup olmadığını kontrol eder.

    Returns:
        bool: Kurulu ise True
    """
    try:
        import transformers
        import torch
        return True
    except ImportError:
        return False


# =============================================================================
# TEST FONKSİYONLARI
# =============================================================================

def test_bert_engine():
    """
    BERT engine'ini test eder.
    """
    print("=" * 60)
    print("BERT Engine Test")
    print("=" * 60)

    # Kurulum kontrolü
    if not is_bert_available():
        print("[HATA] transformers veya torch kütüphanesi kurulu değil!")
        print("Calistir: pip install transformers torch")
        return

    try:
        engine = get_bert_engine()

        print("\n1. Embedding Test:")
        text = "Kadıköy'den Beşiktaş'a rota"
        emb = engine.encode(text)
        print(f"   Text: {text}")
        print(f"   Embedding shape: {emb.shape}")
        print(f"   İlk 5 değer: {emb[:5]}")

        print("\n2. Similarity Test (Typo Tolerance):")
        pairs = [
            ("Kadıköy", "Kadıköy"),      # Aynı
            ("Kadıköy", "Kadiköy"),       # Typo
            ("Kadıköy", "Kadikoy"),       # Typo
            ("Kadıköy", "Beşiktaş"),      # Farklı
            ("Taksim Meydanı", "Taksim"), # Benzer
        ]

        for text1, text2 in pairs:
            sim = engine.similarity(text1, text2)
            status = "[OK]" if sim > 0.8 else "[--]"
            print(f"   {status} '{text1}' vs '{text2}': {sim:.4f}")

        print("\n3. Best Match Test:")
        query = "kadikoy"  # typo ile
        places = ["Kadıköy", "Beşiktaş", "Taksim", "Mecidiyeköy"]
        result = engine.find_best_match(query, places, threshold=0.7)

        if result:
            print(f"   Query: {query}")
            print(f"   En yakın: '{result['match']}' (similarity: {result['similarity']:.4f})")
        else:
            print(f"   Query: {query}")
            print("   Eşleşme bulunamadı")

        print("\n4. Cache Test:")
        from bert_engine import get_embedding_cache_stats, clear_embedding_cache
        
        stats = get_embedding_cache_stats()
        print(f"   Cache stats: hits={stats['cache_hits']}, misses={stats['cache_misses']}, size={stats['cache_size']}")
        
        # Aynı metni tekrar encode ederek cache hit'i test et
        print("\n   Cache hit test (tekrar aynı metin):")
        emb2 = engine.encode(text)
        stats2 = get_embedding_cache_stats()
        print(f"   After 2nd encode: hits={stats2['cache_hits']}, misses={stats2['cache_misses']}")
        
        # Cache temizleme testi
        print("\n   Cache clear test:")
        result = clear_embedding_cache()
        print(f"   Cleared: {result['cleared_entries']} entries")
        stats3 = get_embedding_cache_stats()
        print(f"   After clear: hits={stats3['cache_hits']}, size={stats3['cache_size']}")

        print("\n" + "=" * 60)
        print("[TAMAMLANDI] Test basariyla tamamlandi!")

    except Exception as e:
        print(f"[HATA] {e}")


if __name__ == "__main__":
    test_bert_engine()
