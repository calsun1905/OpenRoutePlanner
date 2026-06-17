"""
bert_nlp_engine.py - Tam BERT Tabanlı NLP Sistemi

Regex YOK! Her şey BERT embedding'leri ile çalışır.

Sistem:
1. Sorgu tipi sınıflandırma (BERT semantic search)
2. Yer ismi çıkarımı (NER + OpenStreetMap matching)
3. Typo tolerant yer ismi düzeltme
4. Bağlam anlama (origin/destination tespiti)

Model: dbmdz/bert-base-turkish-uncased
Yer Verisi: OpenStreetMap (Nominatim API)
"""

import os
import re
import time
import threading
import requests
import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

# OSM API Retry Ayarları
_ORP_OSM_RETRY_MAX = max(1, int(os.getenv("ORP_OSM_RETRY_MAX", "3")))
_ORP_OSM_RETRY_DELAY = max(0.5, float(os.getenv("ORP_OSM_RETRY_DELAY", "1.0")))


def _osm_retry_request(url: str, **kwargs) -> requests.Response:
    """
    OSM API istekleri için retry mekanizması.
    Rate limit ve geçici ağ hatalarına karşı dayanıklılık sağlar.
    """
    last_exception = None
    for attempt in range(_ORP_OSM_RETRY_MAX):
        try:
            response = requests.get(url, **kwargs)
            # 429 Too Many Requests veya 5xx hatalarında retry yap
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < _ORP_OSM_RETRY_MAX - 1:
                    # Exponential backoff with jitter
                    delay = _ORP_OSM_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 0.5)
                    print(f"[OSM Retry] Status {response.status_code}, {delay:.1f}s bekleyecek (deneme {attempt + 1}/{_ORP_OSM_RETRY_MAX})")
                    time.sleep(delay)
                    continue
            return response
        except requests.exceptions.RequestException as e:
            last_exception = e
            if attempt < _ORP_OSM_RETRY_MAX - 1:
                delay = _ORP_OSM_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 0.5)
                print(f"[OSM Retry] Hata: {e}, {delay:.1f}s bekleyecek (deneme {attempt + 1}/{_ORP_OSM_RETRY_MAX})")
                time.sleep(delay)
            continue
    raise last_exception if last_exception else RuntimeError(f"OSM API retry failed after {_ORP_OSM_RETRY_MAX} attempts")

# BERT engine'i import et
try:
    from bert_engine import get_bert_engine, is_bert_available
    from turkey_places import get_all_turkey_places
except ImportError:
    # Aynı dizinde yoksa backend altında ara
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from bert_engine import get_bert_engine, is_bert_available
    try:
        from turkey_places import get_all_turkey_places
    except ImportError:
        get_all_turkey_places = None

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

try:
    from local_places import save_dynamic_place, get_dynamic_place_names, get_all_local_place_names
except ImportError:
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        from local_places import save_dynamic_place, get_dynamic_place_names, get_all_local_place_names
    except ImportError:
        def save_dynamic_place(*args, **kwargs): return None
        def get_dynamic_place_names(limit=500): return []
        def get_all_local_place_names(limit=2000, include_dynamic=True): return []

try:
    from osm_poi_dictionary import POI_MAPPING as OSM_POI_MAPPING
except ImportError:
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        from osm_poi_dictionary import POI_MAPPING as OSM_POI_MAPPING
    except ImportError:
        OSM_POI_MAPPING = {}

try:
    from nlp_concept_resolver import (
        resolve_poi_from_tokens,
        resolve_poi_from_tokens_with_debug,
        map_concept_to_osm_queries,
        PoiResolution,
    )
except ImportError:
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        from nlp_concept_resolver import (
            resolve_poi_from_tokens,
            resolve_poi_from_tokens_with_debug,
            map_concept_to_osm_queries,
            PoiResolution,
        )
    except ImportError:
        resolve_poi_from_tokens = None
        resolve_poi_from_tokens_with_debug = None
        map_concept_to_osm_queries = None
        PoiResolution = None

try:
    from text_utils import tr_lower
except ImportError:
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        from text_utils import tr_lower
    except ImportError:
        def tr_lower(text):
            if not text: return ""
            return str(text).replace("İ", "i").replace("I", "ı").lower()



# =============================================================================
# SORGU TİPLERİ İÇİN BERT EMBEDding TEMPLATES
# =============================================================================
# Her sorgu tipi için "örnek cümle embedding'leri" tutuyoruz
# Kullanıcı sorgusunu bu template'lerle karşılaştıracağız

DEFAULT_QUERY_TEMPLATES = {
    "route": [
        "Kadikoy'den Besiktas'a rota",
        "Taksim'den Kadikoy'e gitmek istiyorum",
        "Ankara'dan Istanbul'a nasil giderim",
        "Baslangictan varisa yol tarifi",
        "Iki nokta arasi guzergah",
    ],
    "poi": [
        "Kadikoy'de neler var",
        "Taksim'de ne yapabilirim",
        "Besiktas'ta nereler var",
        "Bu bolgede mekan ariyorum",
        "Yakinda neleri gezebilirim",
    ],
    "multi": [
        "Kadikoy, Taksim ve Besiktas'i gez",
        "Uc yer birden rota yap",
        "Birden fazla nokta ziyaret",
        "Coklu durakli gezi",
    ],
    "single": [
        "Taksim'e git",
        "Kadikoy'e nasil giderim",
        "Bu yere varmak istiyorum",
        "Tek bir hedef belirle",
    ]
}

DEFAULT_HARD_NEGATIVE_TEMPLATES = [
    "merhaba",
    "selam",
    "nasilsin",
    "tesekkur ederim",
    "yardim eder misin",
    "saat kac",
]

INTENT_TEMPLATE_TYPES = ("route", "poi", "multi", "single")
_INTENT_TEMPLATE_PATH = os.getenv(
    "ORP_INTENT_TEMPLATE_PATH",
    str(Path(__file__).resolve().parent / "data" / "intent_templates_tr.json"),
)


def load_intent_template_bundle(path: Optional[str] = None) -> Tuple[Dict[str, List[str]], List[str]]:
    """
    Intent template bundle dosyasini yukler.
    Dosya yoksa default template/hard-negative listesiyle devam edilir.
    """
    template_map = {
        key: list(values)
        for key, values in DEFAULT_QUERY_TEMPLATES.items()
    }
    hard_negatives = list(DEFAULT_HARD_NEGATIVE_TEMPLATES)
    bundle_path = Path(path or _INTENT_TEMPLATE_PATH)
    if not bundle_path.is_file():
        return template_map, hard_negatives

    try:
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[BERT NLP] Intent template bundle okunamadi ({bundle_path}): {exc}")
        return template_map, hard_negatives

    loaded_templates = payload.get("templates", {})
    if isinstance(loaded_templates, dict):
        for key in INTENT_TEMPLATE_TYPES:
            values = loaded_templates.get(key)
            if isinstance(values, list):
                cleaned = [str(item).strip() for item in values if str(item).strip()]
                if cleaned:
                    template_map[key] = cleaned

    loaded_negatives = payload.get("hard_negatives", [])
    if isinstance(loaded_negatives, list):
        cleaned_negatives = [str(item).strip() for item in loaded_negatives if str(item).strip()]
        if cleaned_negatives:
            hard_negatives = cleaned_negatives

    return template_map, hard_negatives


QUERY_TEMPLATES, HARD_NEGATIVE_TEMPLATES = load_intent_template_bundle()
# Query intenti artik kelime listesiyle override edilmiyor.
# BERT skor dagilimi + yapisal sinyaller (role_hint, yer sayisi, poi_concept)
# birlesik sekilde kullaniliyor.
INTENT_MARGIN_MIN = 0.03
HARD_NEGATIVE_UNKNOWN_THRESHOLD = 0.74
HARD_NEGATIVE_PENALTY_THRESHOLD = 0.64


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Iki embedding arasinda cosine similarity hesaplar."""
    norm = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
    if norm <= 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / norm)


def should_force_unknown_with_hard_negative(
    best_score: float,
    second_best_score: float,
    hard_negative_score: float,
) -> bool:
    """
    Hard-negative benzerligi yuksekse ve intent marji darsa unknown'a zorlar.
    """
    margin = float(best_score) - float(second_best_score)
    return (
        float(hard_negative_score) >= HARD_NEGATIVE_UNKNOWN_THRESHOLD
        and float(best_score) < 0.82
        and margin < 0.14
    )


def apply_intent_conflict_matrix(
    initial_type: str,
    confidence: float,
    *,
    has_poi_cue: bool,
    has_multi_cue: bool,
    direction_hints: bool,
    unique_place_count: int,
    low_margin: bool,
    route_intent_cue: bool = False,
    strong_route_pair: bool = False,
) -> Tuple[str, float, Dict[str, Any]]:
    """
    Intent conflict matrix uygular.

    Legacy type'lara (route/poi/multi/single) map edilir ve
    çakışma durumunda deterministic öncelik kullanılır.
    """
    final_type = initial_type
    final_conf = float(confidence)
    reason = "none"

    # 1) Direction varsa route baskın (özellikle >=2 lokasyon)
    if direction_hints and unique_place_count >= 2 and strong_route_pair:
        final_type = "route"
        final_conf = max(final_conf, 0.80)
        reason = "direction+confident-pair=>route"
    # 2) POI cue varsa ve yön sinyali yoksa POI baskın
    elif has_poi_cue and not direction_hints:
        if initial_type in {"poi", "unknown", "single"} or low_margin:
            final_type = "poi"
            final_conf = max(final_conf, 0.75)
            reason = "poi-cue-no-direction=>poi"
    # 3) Çoklu lokasyon sinyali
    elif has_multi_cue and not direction_hints:
        if initial_type in {"multi", "unknown"} or low_margin:
            final_type = "multi"
            final_conf = max(final_conf, 0.78)
            reason = "multi-cue=>multi"

    matrix_meta = {
        "initial_type": initial_type,
        "final_type": final_type,
        "reason": reason,
        "signals": {
            "has_poi_cue": bool(has_poi_cue),
            "has_multi_cue": bool(has_multi_cue),
            "direction_hints": bool(direction_hints),
            "route_intent_cue": bool(route_intent_cue),
            "strong_route_pair": bool(strong_route_pair),
            "unique_place_count": int(unique_place_count),
            "low_margin": bool(low_margin),
        },
    }
    return final_type, float(final_conf), matrix_meta

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9ÇĞİÖŞÜçğıöşü]+(?:['’`][A-Za-z0-9ÇĞİÖŞÜçğıöşü]+)?")
FROM_SUFFIXES = ("den", "dan", "ten", "tan", "nden", "ndan")
TO_SUFFIXES_APOSTROPHE = ("ye", "ya", "e", "a", "na", "ne")
TO_SUFFIXES_PLAIN = ("ye", "ya", "na", "ne")
LOC_SUFFIXES = ("de", "da", "te", "ta")
OBJECT_SUFFIXES = ("i", "ı", "u", "ü")
COMMON_ALIASES = {
    "adalar": "adalar",
    "arnavutkoy": "arnavutköy",
    "atasehir": "ataşehir",
    "avcilar": "avcılar",
    "bagcilar": "bağcılar",
    "bahcelievler": "bahçelievler",
    "basaksehir": "başakşehir",
    "bayrampasa": "bayrampaşa",
    "kadikoy": "kadıköy",
    "besiktas": "beşiktaş",
    "beykoz": "beykoz",
    "beylikduzu": "beylikdüzü",
    "beyoglu": "beyoğlu",
    "buyukcekmece": "büyükçekmece",
    "catalca": "çatalca",
    "cekmekoy": "çekmeköy",
    "esenler": "esenler",
    "esenyurt": "esenyurt",
    "eyup": "eyüp",
    "eyupsultan": "eyüpsultan",
    "gaziosmanpasa": "gaziosmanpaşa",
    "gungoren": "güngören",
    "kagithane": "kağıthane",
    "uskudar": "üsküdar",
    "sisli": "şişli",
    "kucukcekmece": "küçükçekmece",
    "cankaya": "çankaya",
    "kizilay": "kızılay",
    "goztepe": "göztepe",
    "ortakoy": "ortaköy",
    "bakirkoy": "bakırköy",
    "bostanci": "bostancı",
    "karakoy": "karaköy",
    "eminonu": "eminönü",
    "taksim": "taksim",
    "moda": "moda",
    "maltepe": "maltepe",
    "kartal": "kartal",
    "pendik": "pendik",
    "sancaktepe": "sancaktepe",
    "sariyer": "sarıyer",
    "silivri": "silivri",
    "sultanbeyli": "sultanbeyli",
    "sultangazi": "sultangazi",
    "sile": "şile",
    "tuzla": "tuzla",
    "umraniye": "ümraniye",
    "zeytinburnu": "zeytinburnu",
}

ACTION_WORD_SUFFIXES = (
    "yorum", "iyorum", "ıyorum", "uyorum",
    "yoruz", "iyoruz", "ıyoruz", "uyoruz",
    "elim", "alım", "alim",
    "mek", "mak",
)

ACTION_ROOT_HINTS = {
    "git", "gez", "ara", "goster", "göster", "planla", "hesapla",
    "dolas", "dolaş", "ciz", "çiz",
}
MULTI_STOP_TOKENS = {
    "gez", "gezi", "gezisi", "tur", "turu", "plan", "plani", "planı",
    "dolas", "dolaş", "rota", "rotasi", "rotası",
}
NON_LOCATION_STOP_TOKENS = MULTI_STOP_TOKENS | {
    "ve", "ile", "arasi", "arası", "guzergah", "güzergah", "yol", "tarifi",
    "nasil", "nasıl", "giderim", "gitmek", "istiyorum", "bugun", "bugün",
    "hava", "saat", "kac", "kaç", "metro", "marmaray", "otobus", "otobüs",
    "otobusle", "otobüsle", "tramvay", "vapur", "toplu", "tasima", "taşıma",
    "var", "mi", "mı", "yer", "yerler", "mekan", "mekanlar", "gezilecek", "goster", "göster",
    "nerede", "yenir", "civar", "civarın", "civarinda", "civarında",
    "cevresinde", "çevresinde", "yakinda", "yakında",
}
GENERIC_POI_BROWSE_TERMS = frozenset({"mekan", "mekanlar", "yer", "yerler"})
ROUTE_INTENT_TERMS = (
    "rota", "yol tarifi", "giderim", "gidelim", "git", "güzergah", "guzergah",
    "ulasim", "ulaşım", "toplu taşıma", "toplu tasima",
)


def _env_flag(name: str, default: bool) -> bool:
    """ENV'den bool değer okur."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    """ENV'den float değer okur."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    """ENV'den int değer okur."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return default


_TR_FOLD_TABLE = str.maketrans(
    {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
    }
)


def normalize_place_key(value: str) -> str:
    """Yer adı karşılaştırmaları için normalize anahtar üretir."""
    text = (value or "").replace("’", "'").replace("`", "'")
    text = tr_lower(re.sub(r"\s+", " ", text).strip())
    text = re.sub(r"[^a-z0-9çğıöşü\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return COMMON_ALIASES.get(text, text)


def is_likely_action_token(token: str) -> bool:
    """
    Kelimenin eylem/niyet belirten bir token olma olasılığını döner.
    Bu tür token'lar tek başına lokasyon adayı olarak alınmamalıdır.
    """
    normalized = normalize_place_key(token)
    if not normalized:
        return True
    if normalized in ACTION_ROOT_HINTS:
        return True
    if normalized in NON_LOCATION_STOP_TOKENS:
        return True
    return len(normalized) >= 4 and normalized.endswith(ACTION_WORD_SUFFIXES)


def _singularize_tr_token(token: str) -> str:
    """Basit çoğul eklerini budar (mekanlar -> mekan)."""
    lowered = normalize_place_key(token)
    if lowered in COMMON_ALIASES.values():
        return lowered
    for suffix in ("lar", "ler"):
        if lowered.endswith(suffix) and len(lowered) > len(suffix) + 2:
            return lowered[:-len(suffix)]
    return lowered


def _normalize_poi_mapping(raw_mapping: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    normalized: Dict[str, Dict[str, str]] = {}
    for phrase, tags in (raw_mapping or {}).items():
        norm_phrase = normalize_place_key(phrase)
        if not norm_phrase:
            continue
        if isinstance(tags, dict):
            normalized[norm_phrase] = {str(k): str(v) for k, v in tags.items() if k and v}
    return normalized


NORMALIZED_POI_MAPPING = _normalize_poi_mapping(OSM_POI_MAPPING)
POI_CONCEPT_TERMS = frozenset(NORMALIZED_POI_MAPPING.keys())
POI_CONCEPT_TOKENS = frozenset(
    _singularize_tr_token(token)
    for term in POI_CONCEPT_TERMS
    for token in term.split()
    if len(token) >= 3
)
POI_CONCEPT_FOLDED = {
    term.translate(_TR_FOLD_TABLE): term
    for term in POI_CONCEPT_TERMS
}
POI_CONCEPT_TOKEN_FOLDED = {
    token.translate(_TR_FOLD_TABLE): token
    for token in POI_CONCEPT_TOKENS
}


def is_poi_concept_term(value: str) -> bool:
    """
    Değerin POI tipi ifade edip etmediğini döner.
    Sözlük bazlıdır, fakat tek bir anahtar listesine bağlı kalmak yerine
    normalize + token tabanlı değerlendirme yapar.
    """
    normalized = normalize_place_key(value)
    if not normalized:
        return False
    if normalized in POI_CONCEPT_TERMS:
        return True
    singular = _singularize_tr_token(normalized)
    if singular in POI_CONCEPT_TERMS:
        return True
    folded = singular.translate(_TR_FOLD_TABLE)
    if folded in POI_CONCEPT_FOLDED or folded in POI_CONCEPT_TOKEN_FOLDED:
        return True
    return any(_singularize_tr_token(token) in POI_CONCEPT_TOKENS for token in normalized.split())


def canonicalize_poi_concept_token(value: str) -> str:
    normalized = _singularize_tr_token(normalize_place_key(value))
    folded = normalized.translate(_TR_FOLD_TABLE)
    return POI_CONCEPT_FOLDED.get(folded) or POI_CONCEPT_TOKEN_FOLDED.get(folded) or normalized


def _collect_poi_tokens(query: str, detected_places: Optional[List[Dict[str, Any]]] = None) -> List[str]:
    """POI konsepti için lokasyon dışı normalize token listesi çıkarır."""
    normalized_query = normalize_query_text(query or "")
    if not normalized_query:
        return []

    occupied_ranges: List[Tuple[int, int]] = []
    for place in detected_places or []:
        start = int(place.get("start", -1))
        end = int(place.get("end", -1))
        if start >= 0 and end > start:
            occupied_ranges.append((start, end))

    concept_tokens: List[str] = []
    seen = set()

    def in_occupied_range(start: int, end: int) -> bool:
        for occ_start, occ_end in occupied_ranges:
            if start >= occ_start and end <= occ_end:
                return True
        return False

    for match in TOKEN_PATTERN.finditer(normalized_query):
        token_surface = match.group(0)
        token_normalized, role_hint = normalize_token_with_role(token_surface)
        token_normalized = _singularize_tr_token(token_normalized)
        raw_token_normalized = _singularize_tr_token(normalize_place_key(token_surface))

        # Bazi durumlarda "cami" gibi mekan token'lari da yer span'i icine girebiliyor.
        # POI kavram token'larini bu nedenle agresif sekilde elememek gerekir.
        if in_occupied_range(match.start(), match.end()) and not is_poi_concept_term(token_normalized):
            continue

        if len(token_normalized) < 2:
            continue
        if role_hint in {"from", "to", "loc"} and not is_poi_concept_term(token_normalized):
            # "eczane" gibi kelimeler plain suffix kuraliyla yanlis role-hint alabilir.
            # Ham token POI terimiyse role-hint'i yok sayip konsepte geri al.
            if is_poi_concept_term(raw_token_normalized):
                token_normalized = canonicalize_poi_concept_token(raw_token_normalized)
            else:
                continue
        elif is_poi_concept_term(token_normalized):
            token_normalized = canonicalize_poi_concept_token(token_normalized)
        if is_likely_action_token(token_normalized):
            continue
        if token_normalized in NON_LOCATION_STOP_TOKENS:
            continue
        if token_normalized in seen:
            continue

        seen.add(token_normalized)
        concept_tokens.append(token_normalized)

    return concept_tokens


def extract_poi_concept_with_meta(query: str, detected_places: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    POI sorgusundan konsepti çözer ve kaynak/güven metadatası döner.
    """
    concept_tokens = _collect_poi_tokens(query, detected_places)
    if not concept_tokens:
        return {
            "concept": "",
            "source": "unknown",
            "confidence": 0.0,
            "status": "unknown",
            "tokens": [],
            "candidates": [],
            "debug_plan": {"tokens": [], "ngrams": [], "attempts": [], "selected": {}},
            "osm_queries": [],
        }

    # Yeni resolver varsa önce onu kullan (faz-1 hibrit akış)
    if resolve_poi_from_tokens is not None:
        try:
            debug_plan = None
            if resolve_poi_from_tokens_with_debug is not None:
                resolved, debug_plan = resolve_poi_from_tokens_with_debug(concept_tokens)
            else:
                resolved = resolve_poi_from_tokens(concept_tokens)
            concept = (resolved.concept or "").strip() if resolved else ""
            if concept:
                osm_queries = map_concept_to_osm_queries(concept) if map_concept_to_osm_queries is not None else []
                return {
                    "concept": concept,
                    "source": getattr(resolved, "source", "morph+dict"),
                    "confidence": float(getattr(resolved, "confidence", 0.9) or 0.9),
                    "status": getattr(resolved, "status", "success"),
                    "candidates": getattr(resolved, "candidates", []),
                    "tokens": concept_tokens,
                    "debug_plan": debug_plan or {},
                    "osm_queries": osm_queries,
                }
        except Exception:
            pass

    # Geri uyumluluk fallback (eski davranış)
    prioritized = [t for t in concept_tokens if is_poi_concept_term(t)]
    remaining = [t for t in concept_tokens if t not in prioritized]
    ordered = prioritized + remaining
    concept = " ".join(ordered[:4]).strip()
    if concept:
        osm_queries = map_concept_to_osm_queries(concept) if map_concept_to_osm_queries is not None else []
        return {
            "concept": concept,
            "source": "legacy",
            "confidence": 0.70,
            "status": "success",
            "tokens": concept_tokens,
            "candidates": ordered,
            "debug_plan": {
                "tokens": concept_tokens,
                "ngrams": [],
                "attempts": [],
                "selected": {"concept": concept, "source": "legacy", "confidence": 0.70, "status": "success"},
            },
            "osm_queries": osm_queries,
        }

    return {
        "concept": "",
        "source": "unknown",
        "confidence": 0.0,
        "status": "unknown",
        "tokens": concept_tokens,
        "candidates": ordered,
        "debug_plan": {"tokens": concept_tokens, "ngrams": [], "attempts": [], "selected": {}},
        "osm_queries": [],
    }


def extract_poi_concept(query: str, detected_places: Optional[List[Dict[str, Any]]] = None) -> str:
    """Geri uyum için sadece konsept string döner."""
    return extract_poi_concept_with_meta(query, detected_places).get("concept", "")


def _extract_explicit_multi_places(query: str) -> List[str]:
    """Virgül/ve ile verilen açık çoklu listeyi basitçe çıkarır."""
    text = normalize_query_text(query or "")
    if not text or ("," not in text and " ve " not in text):
        return []

    parts: List[str] = []
    if "," in text and " ve " in text:
        # Örn: "kadıköy, taksim ve beşiktaş'ı gez"
        left, right = text.split(" ve ", 1)
        left_parts = [p.strip() for p in left.split(",") if p.strip()]
        parts.extend(left_parts)
        parts.append(right.strip())
    else:
        parts = [p.strip() for p in re.split(r",|\s+ve\s+", text) if p.strip()]

    extracted: List[str] = []
    for part in parts:
        candidate = None
        for match in TOKEN_PATTERN.finditer(part):
            stem, role_hint = normalize_token_with_role(match.group(0))
            stem = _singularize_tr_token(stem)
            if not stem or is_likely_action_token(stem):
                continue
            if stem in NON_LOCATION_STOP_TOKENS:
                continue
            if role_hint in {"from", "to"}:
                continue
            candidate = stem
            break

        if candidate and candidate not in extracted:
            extracted.append(candidate)

    return extracted


def _extract_plain_multi_places(query: str, limit: int = 4) -> List[str]:
    """Virgülsüz çoklu liste cümlelerinden aday yerleri çıkarır."""
    text = normalize_query_text(query or "")
    if not text:
        return []

    directional_suffix_tokens = set(FROM_SUFFIXES) | set(TO_SUFFIXES_APOSTROPHE) | set(TO_SUFFIXES_PLAIN) | set(LOC_SUFFIXES)

    items: List[str] = []
    for match in TOKEN_PATTERN.finditer(text):
        token = match.group(0)
        stem, role_hint = normalize_token_with_role(token)
        stem = _singularize_tr_token(stem)
        if not stem or is_likely_action_token(stem):
            continue
        if role_hint in {"from", "to"}:
            continue
        if len(stem) < 4:
            continue
        if stem in MULTI_STOP_TOKENS:
            continue
        if stem in directional_suffix_tokens:
            continue
        if len(stem) <= 5 and stem[:1] in {"y", "n"} and stem[1:] in directional_suffix_tokens:
            continue
        if stem in items:
            continue
        items.append(stem)
        if len(items) >= limit:
            break
    return items


def build_place_lookup_keys(value: str) -> List[str]:
    """Yer lookup için varyasyonlu anahtar listesi üretir."""
    base = normalize_place_key(value)
    if not base:
        return []

    keys = set()
    variants = {base}

    # Türkçe buffer harfi nedeniyle kayıp/ekli "y" varyantı.
    if base.endswith("y") and len(base) > 2:
        variants.add(base[:-1])
    else:
        variants.add(base + "y")

    for item in variants:
        if not item:
            continue
        keys.add(item)
        keys.add(item.translate(_TR_FOLD_TABLE))
        aliased = COMMON_ALIASES.get(item)
        if aliased:
            keys.add(aliased)
            keys.add(aliased.translate(_TR_FOLD_TABLE))

    return [k for k in keys if k]


def normalize_query_text(text: str) -> str:
    """Apostrof ve boşluk varyasyonlarını normalize eder."""
    return re.sub(r"\s+", " ", text.replace("’", "'").replace("`", "'")).strip()


def normalize_token_with_role(token: str) -> Tuple[str, Optional[str]]:
    """
    Token'ı normalize eder ve varsa rol ipucu üretir.
    Örnek: "Kadıköy'den" -> ("kadıköy", "from")
    """
    # Turkce ek ayrisi:
    # "besiktas'tan" -> (besiktas, from), "uskudar'a" -> (uskudar, to)
    cleaned = normalize_query_text(token).strip(".,;:!?()[]{}\"")
    lowered = tr_lower(cleaned)

    if not lowered:
        return "", None

    raw_key = normalize_place_key(lowered)
    if is_poi_concept_term(raw_key):
        return raw_key, None

    role_hint = None
    stem = lowered
    known_roots = set(COMMON_ALIASES.keys()) | set(COMMON_ALIASES.values())

    # Apostrof bulunan token'larda ekler daha guvenli ayrilir.
    # Apostrof yoksa plain suffix setiyle devam edilir.
    if "'" in lowered:
        base, suffix = lowered.rsplit("'", 1)
        if suffix in FROM_SUFFIXES:
            stem, role_hint = base, "from"
        elif suffix in TO_SUFFIXES_APOSTROPHE:
            stem, role_hint = base, "to"
        elif suffix in LOC_SUFFIXES:
            stem, role_hint = base, "loc"
        elif suffix in OBJECT_SUFFIXES:
            stem, role_hint = base, None
    else:
        for suffix in FROM_SUFFIXES:
            if lowered.endswith(suffix) and len(lowered) > len(suffix) + 2:
                stem, role_hint = lowered[:-len(suffix)], "from"
                break
        if role_hint is None:
            for suffix in TO_SUFFIXES_PLAIN:
                if lowered.endswith(suffix) and len(lowered) > len(suffix) + 2:
                    stem, role_hint = lowered[:-len(suffix)], "to"
                    break
        if role_hint is None:
            for suffix in ("e", "a"):
                base = lowered[:-len(suffix)] if lowered.endswith(suffix) else ""
                if base and (base in known_roots or COMMON_ALIASES.get(base) in known_roots):
                    stem, role_hint = base, "to"
                    break
        if role_hint is None:
            for suffix in LOC_SUFFIXES:
                # "-da/-de/-ta/-te" plain ek soyma kuralı çok agresif olursa
                # "Galata" gibi gerçek yer adlarını yanlış kırpar.
                # Bu yüzden daha uzun tokenlarda uygula.
                if lowered.endswith(suffix) and len(lowered) > len(suffix) + 4:
                    stem, role_hint = lowered[:-len(suffix)], "loc"
                    break
        if role_hint is None:
            for suffix in OBJECT_SUFFIXES:
                base = lowered[:-len(suffix)] if lowered.endswith(suffix) else ""
                if base and (base in known_roots or COMMON_ALIASES.get(base) in known_roots):
                    stem = base
                    break

    # Son adimda yazim/alias normalize edilir.
    stem = stem.strip(".,;:!?()[]{}\"'")
    stem = COMMON_ALIASES.get(stem, stem)
    return stem, role_hint


def has_explicit_route_pattern(query: str, detected_places: Optional[List[Dict[str, Any]]] = None) -> bool:
    """
    Dogal Turkce rota kaliplarini route niyeti olarak tanir.
    """
    normalized = normalize_query_text(query or "")
    if not normalized:
        return False

    if re.search(r"\b\w+(?:'?(?:den|dan|ten|tan|nden|ndan))\b.*\b\w+(?:'?(?:ye|ya|e|a|na|ne))\b", tr_lower(normalized)):
        return True

    places = detected_places or []
    role_hints = {item.get("role_hint") for item in places if item.get("role_hint")}
    if {"from", "to"} <= role_hints:
        return True

    return False


def is_route_candidate_confident(candidate: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(candidate, dict):
        return False
    similarity = float(candidate.get("similarity", 0.0) or 0.0)
    source = str(candidate.get("match_source", "") or "")
    token_count = int(candidate.get("token_count", 1) or 1)
    if source == "lookup-exact":
        return True
    if token_count > 1:
        return similarity >= 0.78
    return similarity >= 0.82


def has_confident_route_pair(detected_places: List[Dict[str, Any]]) -> bool:
    """
    Yalnizca iki ucu da guvenilir ise route rescue'e izin ver.
    """
    if len(detected_places or []) < 2:
        return False

    from_candidates = [item for item in detected_places if item.get("role_hint") == "from"]
    to_candidates = [item for item in detected_places if item.get("role_hint") == "to"]
    if not from_candidates or not to_candidates:
        return False

    for from_item in from_candidates:
        if not is_route_candidate_confident(from_item):
            continue
        for to_item in to_candidates:
            if from_item.get("place") == to_item.get("place"):
                continue
            if is_route_candidate_confident(to_item):
                return True
    return False


def extract_candidate_spans(query: str, max_ngram: int = 3) -> List[Dict[str, Any]]:
    """
    Sorgudan Türkçe ekleri soyulmuş, metin pozisyonu korunmuş aday span'ler çıkarır.
    """
    normalized_query = normalize_query_text(query)
    token_matches = []

    for match in TOKEN_PATTERN.finditer(normalized_query):
        surface = match.group(0)
        normalized, role_hint = normalize_token_with_role(surface)

        if len(normalized) < 2:
            continue

        if role_hint is None and (normalized in NON_LOCATION_STOP_TOKENS or is_poi_concept_term(normalized)):
            continue

        if role_hint is None and is_likely_action_token(normalized):
            continue

        token_matches.append({
            "surface": surface,
            "normalized": normalized,
            "start": match.start(),
            "end": match.end(),
            "role_hint": role_hint,
            "token_count": 1,
        })

    spans = []
    seen = set()

    def add_span(surface: str, normalized: str, start: int, end: int, role_hint: Optional[str], token_count: int):
        key = (start, end, normalized)
        if key in seen:
            return
        seen.add(key)
        spans.append({
            "surface": surface,
            "normalized": normalized,
            "start": start,
            "end": end,
            "role_hint": role_hint,
            "token_count": token_count,
        })

    for token in token_matches:
        add_span(**token)

    for size in range(2, max_ngram + 1):
        for i in range(len(token_matches) - size + 1):
            chunk = token_matches[i:i + size]
            between_text = normalized_query[chunk[0]["end"]:chunk[-1]["start"]]
            role_hints = {item["role_hint"] for item in chunk if item["role_hint"]}

            if "," in between_text or len(role_hints) > 1:
                continue

            surface = normalized_query[chunk[0]["start"]:chunk[-1]["end"]]
            normalized = " ".join(item["normalized"] for item in chunk)
            role_hint = next((item["role_hint"] for item in reversed(chunk) if item["role_hint"]), None)

            add_span(
                surface=surface,
                normalized=normalized,
                start=chunk[0]["start"],
                end=chunk[-1]["end"],
                role_hint=role_hint,
                token_count=size,
            )

    spans.sort(key=lambda item: (item["start"], -item["token_count"]))
    return spans


# =============================================================================
# YER İSMİ VERİTABANI (OpenStreetMap entegrasyonu için)
# =============================================================================

class PlaceDatabase:
    """
    Yer ismi veritabanı.

    Hibrit sistem:
    1. Başlangıçta static Türkiye verisi
    2. Bulunamazsa OpenStreetMap API'den dinamik çek
    3. Otomatik cache'leme
    """

    # OSM API ayarları
    OSM_API_URL = "https://nominatim.openstreetmap.org/search"
    OSM_RATE_LIMIT = 1.0  # saniye

    def __init__(
        self,
        use_osm: bool = None,
        prefer_osm_first: bool = False,
        seed_dynamic_cache: bool = True,
        seed_local_places: bool = True,
        seed_static_places: bool = True,
        seed_user_locations: bool = True,
    ):
        self._places = {}  # {name: embedding}
        self._place_names = []  # List[str]
        self._place_name_to_index = {}  # {name: index}
        self._normalized_place_lookup = {}  # {normalized_key: canonical_name}
        self._embeddings = None  # np.ndarray matrix
        self._embedding_matrix_dirty = True
        
        # OSM usage from env ORP_USE_OSM (default False if not set)
        osm_from_env = os.getenv("ORP_USE_OSM", "").lower()
        if osm_from_env in ("1", "true", "yes", "on"):
            self._use_osm = True
        elif osm_from_env in ("0", "false", "no", "off"):
            self._use_osm = False
        else:
            # Fallback to parameter if env not set
            self._use_osm = use_osm if use_osm is not None else False
        
        self._prefer_osm_first = prefer_osm_first
        self._osm_timeout_sec = max(0.5, _env_float("ORP_BERT_OSM_TIMEOUT_SEC", 3.0))
        self._osm_prefetch_budget_sec = max(0.0, _env_float("ORP_BERT_OSM_PREFETCH_BUDGET_SEC", 1.0))
        self._osm_prefetch_max_queries = max(1, _env_int("ORP_BERT_OSM_PREFETCH_MAX_QUERIES", 3))
        # {normalized_query: {"added_count": int, "expires_at": float}}
        self._osm_query_cache = {}

        if seed_dynamic_cache:
            self._seed_dynamic_cache()

        if seed_local_places:
            # local_places tablosundan yalnızca seed kayıtları çekilir.
            # Dinamik OSM cache ayrı bir adımda yönetilir.
            self._seed_local_places(include_dynamic=False)

        if seed_user_locations:
            self._seed_user_locations()

        if seed_static_places:
            self._seed_turkish_places()

    def _seed_dynamic_cache(self):
        """Kalıcı OSM cache içindeki dinamik yer adlarını yükler."""
        try:
            cached_places = get_dynamic_place_names()
            for place in cached_places:
                self.add_place(place)
            if cached_places:
                print(f"[PlaceDB] Dinamik OSM cache yüklendi: {len(cached_places)} yer")
        except Exception as e:
            print(f"[PlaceDB] Dinamik OSM cache yüklenemedi: {e}")

    def _seed_user_locations(self):
        """Kullanıcı lokasyonlarını ekler."""
        try:
            user_locations = get_all_locations()
            user_loc_count = 0
            for loc in user_locations:
                name = loc.get("name", "").strip()
                if name:
                    self.add_place(name)
                    user_loc_count += 1
            if user_loc_count > 0:
                print(f"[PlaceDB] {user_loc_count} özel kullanıcı lokasyonu eklendi.")
        except Exception as e:
            print(f"[PlaceDB] Kullanıcı lokasyonları yüklenemedi: {e}")

    def _seed_local_places(self, include_dynamic: bool = True):
        """local_places tablosundaki kayıtları ekler."""
        try:
            local_places = get_all_local_place_names(limit=2000, include_dynamic=include_dynamic)
            added = 0
            for place in local_places:
                if place not in self._places:
                    self.add_place(place)
                    added += 1
            if added > 0:
                print(f"[PlaceDB] local_places kaynagi eklendi: {added} yer")
        except Exception as e:
            print(f"[PlaceDB] local_places yuklenemedi: {e}")

    def _seed_turkish_places(self):
        """Türkiye'nin tüm yer isimlerini yükler."""
        try:
            if get_all_turkey_places:
                all_places = get_all_turkey_places()
                for place in all_places:
                    self.add_place(place)
                print(f"[PlaceDB] Türkiye veritabanı yüklendi: Toplam {len(self._place_names)} yer")
        except Exception as e:
            print(f"[PlaceDB] Türkiye verisi yüklenemedi: {e}")
            print("[PlaceDB] Yedek popüler yerler yükleniyor...")
            self._seed_fallback_places()

    def _seed_fallback_places(self):
        """Yedek popüler yer isimleri."""
        popular_places = [
            # İstanbul
            "Kadıköy", "Beşiktaş", "Taksim", "Taksim Meydanı", "Mecidiyeköy",
            "Şişli", "Levent", "Maslak", "Sarıyer", "Eminönü",
            "Sultanahmet", "Fatih", "Üsküdar", "Kartal", "Maltepe",
            "Bostancı", "Kozyatağı", "Bebek", "Ortaköy", "Karaköy",
            "Moda", "Bağdat Caddesi", "İstiklal Caddesi", "Galata",

            # Ankara
            "Ankara", "Kızılay", "Çankaya", "Keçiören", "Yenimahalle",
            "Sıhhiye", "Ulus", "AŞTİ", "Gar",

            # İzmir
            "İzmir", "Konak", "Alsancak", "Bornova", "Buca",
            "Karşıyaka", "Balçova", "Gaziemir",

            # Diğer
            "Bursa", "Antalya", "Adana", "Mersin", "Gaziantep",
            "Konya", "Kayseri", "Eskişehir", "Samsun", "Trabzon",
        ]

        for place in popular_places:
            self.add_place(place)

    def add_place(self, place_name: str, embedding: Optional[np.ndarray] = None):
        """
        Yer ismini veritabanına ekle.

        Args:
            place_name: Yer ismi
            embedding: BERT embedding (None ise hesaplanır)
        """
        if place_name in self._places:
            return

        emb_array = None
        if embedding is not None:
            emb_array = np.array(embedding)

        self._places[place_name] = emb_array
        self._place_names.append(place_name)
        self._place_name_to_index[place_name] = len(self._place_names) - 1
        normalized_key = normalize_place_key(place_name)
        if normalized_key and normalized_key not in self._normalized_place_lookup:
            self._normalized_place_lookup[normalized_key] = place_name
        folded_key = normalized_key.translate(_TR_FOLD_TABLE) if normalized_key else ""
        if folded_key and folded_key not in self._normalized_place_lookup:
            self._normalized_place_lookup[folded_key] = place_name

        if emb_array is None:
            self._embedding_matrix_dirty = True
            return

        if self._embeddings is None:
            self._embedding_matrix_dirty = True
            return

        if self._embedding_matrix_dirty:
            return

        if self._embeddings.ndim != 2:
            self._embedding_matrix_dirty = True
            return

        emb_row = np.array(emb_array).reshape(1, -1)
        if emb_row.shape[1] != self._embeddings.shape[1]:
            self._embedding_matrix_dirty = True
            return

        self._embeddings = np.vstack([self._embeddings, emb_row])
        self._embedding_matrix_dirty = False

    def get_embedding_matrix(self, bert_engine) -> np.ndarray:
        """
        Tüm yer isimlerinin embedding matrisini döner.

        Lazy: İlk çağırmada hesaplar ve cache'ler.
        """
        if self._embeddings is not None and not self._embedding_matrix_dirty:
            return self._embeddings

        if not self._place_names:
            self._embeddings = np.array([])
            self._embedding_matrix_dirty = False
            return self._embeddings

        # Tüm yer isimleri için embedding hesapla
        embeddings = bert_engine.encode_batch(self._place_names)
        self._embeddings = np.array(embeddings)

        # Cache'le
        for name, emb in zip(self._place_names, embeddings):
            self._places[name] = emb

        self._embedding_matrix_dirty = False
        return self._embeddings

    def resolve_lookup(self, query: str) -> Optional[str]:
        """
        Normalize lookup tabloları üzerinden canonical yer adını döner.
        """
        for lookup_key in build_place_lookup_keys(query):
            canonical_name = self._normalized_place_lookup.get(lookup_key)
            if canonical_name:
                return canonical_name
        return None

    def find_best_match(
        self,
        query: str,
        query_embedding: np.ndarray,
        threshold: float = 0.75,
        bert_engine = None,
        allow_below_threshold: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Sorguya en yakın yer ismini bulur.

        Hibrit: Cache + OSM API

        Args:
            query: Arama sorgusu
            query_embedding: Sorgu embedding'i
            threshold: Minimum benzerlik eşiği

        Returns:
            En yakın eşleşme veya None
        """
        if not self._place_names and self._use_osm and self._prefer_osm_first:
            self.cache_osm_results(query)

        if not self._place_names:
            return None

        canonical_name = self.resolve_lookup(query)
        if canonical_name:
            return {
                "place": canonical_name,
                "similarity": 1.0,
                "index": self._place_name_to_index.get(canonical_name, -1),
                "source": "lookup-exact",
            }

        def score_embeddings(embedding_matrix: np.ndarray) -> Optional[Dict[str, Any]]:
            similarities = np.dot(embedding_matrix, query_embedding)
            norms = np.linalg.norm(embedding_matrix, axis=1) * np.linalg.norm(query_embedding)

            if np.all(norms == 0):
                return None

            similarities = np.divide(
                similarities,
                norms,
                out=np.zeros_like(similarities),
                where=norms != 0
            )

            best_idx = int(np.argmax(similarities))
            return {
                "place": self._place_names[best_idx],
                "similarity": float(similarities[best_idx]),
                "index": best_idx,
                "source": "embedding-cache",
            }

        embeddings = self._embeddings
        if embeddings is None and bert_engine is not None:
            embeddings = self.get_embedding_matrix(bert_engine)

        best_match = score_embeddings(embeddings) if embeddings is not None else None
        if best_match and best_match["similarity"] >= threshold:
            return best_match

        # OSM-first modunda OSM adayları önce beslenmiş olur; burada ise son fallback çalışır.
        refreshed_match = None
        if self._use_osm and (best_match is None or best_match["similarity"] < 0.50):
            print(f"[OSM API] '{query}' aranıyor...")
            added = self.cache_osm_results(query, bert_engine=bert_engine)

            if added > 0:
                print(f"[OSM API] {added} yeni yer eklendi!")
                if bert_engine is not None:
                    refreshed_embeddings = self.get_embedding_matrix(bert_engine)
                    refreshed_match = score_embeddings(refreshed_embeddings)
                    if refreshed_match and refreshed_match["similarity"] >= threshold:
                        refreshed_match["source"] = "embedding-osm-refresh"
                        return refreshed_match

        if allow_below_threshold:
            fallback_match = refreshed_match or best_match
            if fallback_match:
                return fallback_match

        return None

    def search_osm_api(self, query: str, limit: int = 5) -> List[str]:
        """
        OpenStreetMap API'den yer arama.

        Args:
            query: Arama sorgusu
            limit: Max sonuç sayısı

        Returns:
            Bulunan yer isimleri listesi
        """
        if not self._use_osm:
            return []

        try:
            params = {
                "q": f"{query}, Turkey",
                "format": "json",
                "countrycodes": "tr",
                "limit": limit
            }

            response = _osm_retry_request(
                self.OSM_API_URL,
                params=params,
                headers={"User-Agent": "OpenRoutePlanner/1.0"},
                timeout=self._osm_timeout_sec
            )

            if response.status_code == 200:
                data = response.json()
                places = []

                for item in data:
                    place_name = item.get("display_name", item.get("name", ""))
                    # Kısa ismi al
                    short_name = place_name.split(",")[0].strip()
                    if short_name and short_name not in places:
                        places.append(short_name)

                # Rate limiting bekle
                time.sleep(self.OSM_RATE_LIMIT)

                return places

        except Exception as e:
            print(f"[OSM API] Hata: {e}")

        return []

    def add_places_from_osm(self, query: str) -> int:
        """
        OSM API'den yer çek ve veritabanına ekle.

        Args:
            query: Arama sorgusu

        Returns:
            Eklenen yer sayısı
        """
        return self.cache_osm_results(query, bert_engine=None)

    def cache_osm_results(
        self,
        query: str,
        limit: int = 5,
        deadline_ts: Optional[float] = None,
        bert_engine=None,
    ) -> int:
        """
        OSM'den yer arar, sonuçları memory + local_places cache'e yazar.
        deadline_ts verildiyse bu zamanı aşan çağrılar atlanır.
        """
        if not self._use_osm:
            return 0

        if deadline_ts is not None and time.monotonic() >= deadline_ts:
            return 0

        normalized_query = tr_lower((query or "").strip())
        if len(normalized_query) < 2:
            return 0

        now = time.time()
        cache_entry = self._osm_query_cache.get(normalized_query)
        if cache_entry and cache_entry.get("expires_at", 0) > now:
            return int(cache_entry.get("added_count", 0))

        added_count = 0
        request_succeeded = False

        try:
            if deadline_ts is not None and time.monotonic() >= deadline_ts:
                return 0

            params = {
                "q": f"{query}, Turkey",
                "format": "json",
                "countrycodes": "tr",
                "limit": limit
            }

            response = _osm_retry_request(
                self.OSM_API_URL,
                params=params,
                headers={"User-Agent": "OpenRoutePlanner/1.0"},
                timeout=self._osm_timeout_sec
            )

            if response.status_code == 200:
                request_succeeded = True
                data = response.json()
                new_place_names: List[str] = []
                seen_new_places = set()

                for item in data:
                    display_name = item.get("display_name", item.get("name", "")).strip()
                    short_name = display_name.split(",")[0].strip()
                    if not short_name:
                        continue

                    lat = item.get("lat")
                    lon = item.get("lon")
                    if lat is None or lon is None:
                        continue

                    if short_name not in self._places and short_name not in seen_new_places:
                        seen_new_places.add(short_name)
                        new_place_names.append(short_name)

                    save_dynamic_place(
                        name=short_name,
                        display_name=display_name,
                        lat=float(lat),
                        lon=float(lon),
                        search_terms=f"{tr_lower(short_name)} {tr_lower(display_name)}",
                    )

                if new_place_names:
                    if bert_engine is not None:
                        try:
                            new_embeddings = bert_engine.encode_batch(new_place_names)
                            for place_name, embedding in zip(new_place_names, new_embeddings):
                                self.add_place(place_name, embedding=np.array(embedding))
                        except Exception:
                            for place_name in new_place_names:
                                self.add_place(place_name)
                    else:
                        for place_name in new_place_names:
                            self.add_place(place_name)
                    added_count += len(new_place_names)

                time.sleep(self.OSM_RATE_LIMIT)
            else:
                print(f"[OSM API] Beklenmeyen status: {response.status_code}")

        except Exception as e:
            print(f"[OSM API] Hata: {e}")

        # Ağ/HTTP hatalarında cache yazma; böylece sonraki denemede tekrar sorgulanır.
        if request_succeeded:
            ttl_seconds = 3600 if added_count > 0 else 300
            self._osm_query_cache[normalized_query] = {
                "added_count": added_count,
                "expires_at": time.time() + ttl_seconds,
            }
        else:
            self._osm_query_cache.pop(normalized_query, None)

        return added_count

    def _build_osm_prefetch_queries(self, query: str, max_queries: int = 3) -> List[str]:
        """
        Kullanıcı sorgusundan OSM için daha anlamlı aday arama parçaları üretir.
        """
        phrases = []
        spans = extract_candidate_spans(query, max_ngram=3)

        for span in sorted(spans, key=lambda item: (-item["token_count"], item["start"])):
            phrase = span["normalized"]
            if len(phrase) < 2 or phrase in phrases:
                continue
            phrases.append(phrase)

        return phrases[:max_queries]

    def prefetch_osm_candidates(self, query: str, bert_engine=None, max_queries: int = 3) -> int:
        """
        Tek parse akışında kontrollü sayıda OSM sorgusu yaparak aday havuzunu büyütür.
        """
        if not self._use_osm or not self._prefer_osm_first:
            return 0

        effective_max_queries = min(max_queries, self._osm_prefetch_max_queries)
        if self._osm_prefetch_budget_sec <= 0:
            return 0

        deadline_ts = time.monotonic() + self._osm_prefetch_budget_sec

        added_total = 0
        for candidate_query in self._build_osm_prefetch_queries(query, max_queries=effective_max_queries):
            if time.monotonic() >= deadline_ts:
                break
            added_total += self.cache_osm_results(
                candidate_query,
                limit=5,
                deadline_ts=deadline_ts,
                bert_engine=bert_engine,
            )

        if added_total > 0 and bert_engine is not None and self._embedding_matrix_dirty:
            self.get_embedding_matrix(bert_engine)

        return added_total

    def find_all_matches(
        self,
        query: str,
        query_embedding: np.ndarray,
        threshold: float = 0.70,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Sorguya benzeyen tüm yer isimlerini bulur.

        Returns:
            Eşleşme listesi (en yüksek skordan düşüğe)
        """
        if not self._place_names or self._embeddings is None:
            return []

        # Tüm similarities
        similarities = np.dot(self._embeddings, query_embedding)
        norms = np.linalg.norm(self._embeddings, axis=1) * np.linalg.norm(query_embedding)
        # Sıfıra bölünme koruması
        similarities = np.divide(similarities, norms, out=np.zeros_like(similarities), where=norms!=0)

        # Threshold üstünü al
        results = []
        for idx, score in enumerate(similarities):
            if score >= threshold:
                results.append({
                    "place": self._place_names[idx],
                    "similarity": float(score)
                })

        # Sort by similarity descending
        results.sort(key=lambda x: x["similarity"], reverse=True)

        return results[:max_results]


# =============================================================================
# INTENT RESCUE HELPER
# =============================================================================

def should_rescue_poi_intent(
    *,
    query_type: str,
    has_poi_cue: bool,
    poi_question_cue: bool,
    route_intent_cue: bool,
    direction_hints: bool,
    role_hints: set,
    unique_place_count: int,
) -> bool:
    """
    Lokasyon yakalansa bile kaybolan POI niyetini geri kazanmak icin son adim guard'i.
    """
    if query_type == "poi":
        return False
    if not has_poi_cue and not poi_question_cue:
        return False
    if route_intent_cue and direction_hints and unique_place_count >= 2:
        return False

    has_loc_role = "loc" in role_hints

    if has_poi_cue and not direction_hints and unique_place_count <= 1 and has_loc_role:
        return True
    if poi_question_cue and not direction_hints and unique_place_count <= 1 and not route_intent_cue:
        return True
    return False


def should_prefetch_osm_for_query(query: str, candidate_spans: List[Dict[str, Any]]) -> bool:
    """
    OSM prefetch'i sadece lokasyon/POI sinyali gucluyken ac.
    """
    normalized = normalize_query_text(query or "")
    if not normalized:
        return False

    has_loc_role = any((span.get("role_hint") in {"from", "to", "loc"}) for span in (candidate_spans or []))
    has_multi_span = len(candidate_spans or []) >= 2
    has_route_cue = bool(re.search(r"\b(rota|yol|guzergah|güzergah|git|giderim|ulasim|ulaşım)\b", normalized))
    has_poi_cue = bool(
        re.search(
            r"\b(kafe|cafe|restoran|restaurant|eczane|hastane|müze|muze|park|avm|otel|cami|durak)\b",
            normalized,
        )
    )
    return bool(has_loc_role or has_multi_span or has_route_cue or has_poi_cue)


# =============================================================================
# BERT NLP ENGINE - ANA SINIF
# =============================================================================

class BertNLPEngine:
    """
    Tam BERT tabanlı NLP motoru.

    Regex yok! Her şey embedding ve semantic search.
    """

    def __init__(self):
        """BERT engine'i başlat."""
        if not is_bert_available():
            raise RuntimeError(
                "BERT kütüphaneleri kurulu değil!\n"
                "Çalıştır: pip install transformers torch"
            )

        # BERT engine'i al (singleton)
        self.bert = get_bert_engine()

        # Konfigürasyon: ENV ile runtime davranışı kontrol edilebilir.
        # ORP_BERT_USE_OSM=1/0
        # ORP_BERT_PREFER_OSM_FIRST=1/0
        # ORP_BERT_SEED_STATIC=1/0
        # ORP_BERT_SEED_USER_LOCATIONS=1/0
        # Konfigurasyon tamamen ENV tabanli:
        # ayni kodla farkli ortamlarda farkli NLP davranisi acilip kapanabilir.
        use_osm = _env_flag("ORP_BERT_USE_OSM", True)
        prefer_osm_first = _env_flag("ORP_BERT_PREFER_OSM_FIRST", False)
        seed_dynamic_cache = _env_flag("ORP_BERT_SEED_DYNAMIC", use_osm)
        seed_local_places = _env_flag("ORP_BERT_SEED_LOCAL", True)
        seed_static_places = _env_flag("ORP_BERT_SEED_STATIC", True)
        seed_user_locations = _env_flag("ORP_BERT_SEED_USER_LOCATIONS", True)

        # Yer ismi veritabanı (OSM API desteği ile)
        # PlaceDatabase hibrit kaynakla calisir:
        # static + local cache + opsiyonel OSM prefetch.
        self.places = PlaceDatabase(
            use_osm=use_osm,
            prefer_osm_first=prefer_osm_first,
            seed_dynamic_cache=seed_dynamic_cache,
            seed_local_places=seed_local_places,
            seed_static_places=seed_static_places,
            seed_user_locations=seed_user_locations,
        )
        self._max_candidate_spans = max(
            4,
            _env_int(
                "NLP_MAX_CANDIDATE_SPANS",
                _env_int("ORP_NLP_MAX_CANDIDATE_SPANS", 24),
            ),
        )

        # Yer isimleri için embedding matrix'i HESAPLA
        print("[BERT NLP] Yer isimleri için embedding hesaplanıyor...")
        self.places.get_embedding_matrix(self.bert)
        print(f"[BERT NLP] {len(self.places._place_names)} yer ismi indexlendi!")

        # Query template/hard-negative embedding cache
        self._template_embeddings = None
        self._template_centroids = None
        self._hard_negative_embeddings = None

        print("[BERT NLP] Engine hazır!")

    def _get_template_embeddings(self) -> Dict[str, List[np.ndarray]]:
        """
        Query template'lerinin embedding'lerini döner.

        Lazy: İlk çağırmada hesaplar.
        """
        if self._template_embeddings is not None:
            return self._template_embeddings

        embeddings: Dict[str, List[np.ndarray]] = {}
        centroids: Dict[str, np.ndarray] = {}
        for query_type, templates in QUERY_TEMPLATES.items():
            encoded = self.bert.encode_batch(templates)
            embeddings[query_type] = encoded
            if encoded:
                centroids[query_type] = np.mean(np.asarray(encoded), axis=0)

        self._template_embeddings = embeddings
        self._template_centroids = centroids
        return embeddings

    def _get_hard_negative_embeddings(self) -> List[np.ndarray]:
        """Hard negative template embedding'lerini lazy olarak döner."""
        if self._hard_negative_embeddings is not None:
            return self._hard_negative_embeddings
        self._hard_negative_embeddings = self.bert.encode_batch(HARD_NEGATIVE_TEMPLATES)
        return self._hard_negative_embeddings

    def classify_query_type_with_scores(self, query: str) -> Tuple[str, float, Dict[str, float]]:
        """
        Sorgunun tipini sınıflandırır.

        Args:
            query: Kullanıcı sorgusu

        Returns:
            (query_type, confidence, score_map)
        """
        # Intent siniflandirma template benzerligi uzerinden yapilir.
        query_embedding = self.bert.encode(query)
        template_embeddings = self._get_template_embeddings()

        best_type = "unknown"
        best_score = 0.0
        score_map: Dict[str, float] = {}

        # Her query type için ortalama similarity hesapla
        for query_type, template_embs in template_embeddings.items():
            scores = []
            for template_emb in template_embs:
                scores.append(cosine_similarity(query_embedding, template_emb))

            avg_score = np.mean(scores) if scores else 0.0
            centroid_score = 0.0
            centroid = (self._template_centroids or {}).get(query_type)
            if centroid is not None:
                centroid_score = cosine_similarity(query_embedding, centroid)

            # Template ortalamasını centroid ile birleştir.
            final_score = (0.65 * float(avg_score)) + (0.35 * float(centroid_score))
            score_map[query_type] = float(final_score)

            if final_score > best_score:
                best_score = final_score
                best_type = query_type

        # Hard-negative kontrolü: selamlaşma/yardım vb. sorguları yanlış intent'e çekmeyi azalt.
        # Hard-negative seti chitchat metinlerinin route/poi'ye kaymasini azaltir.
        hard_negative_embs = self._get_hard_negative_embeddings()
        hard_negative_score = 0.0
        for neg_emb in hard_negative_embs:
            hard_negative_score = max(hard_negative_score, cosine_similarity(query_embedding, neg_emb))

        sorted_scores = sorted(score_map.values(), reverse=True)
        second_best = float(sorted_scores[1]) if len(sorted_scores) > 1 else 0.0

        if should_force_unknown_with_hard_negative(best_score, second_best, hard_negative_score):
            return "unknown", float(best_score), score_map

        if hard_negative_score >= HARD_NEGATIVE_PENALTY_THRESHOLD:
            best_score = max(0.0, best_score - 0.05)

        # Threshold altındaysa unknown
        if best_score < 0.5:
            return "unknown", float(best_score), score_map

        return best_type, float(best_score), score_map

    def classify_query_type(self, query: str) -> Tuple[str, float]:
        """
        Sorgunun tipini sınıflandırır.
        """
        query_type, confidence, _ = self.classify_query_type_with_scores(query)
        return query_type, confidence

    def _is_location_like_match(self, span: Dict[str, Any], match: Dict[str, Any]) -> Tuple[bool, str]:
        """
        False-positive azaltmak için aday span'in gerçekten lokasyon olup olmadığını kontrol eder.
        """
        normalized = (span.get("normalized") or "").strip()
        if not normalized:
            return False, "empty-span"

        role_hint = span.get("role_hint")
        token_count = int(span.get("token_count", 1))
        similarity = float(match.get("similarity", 0.0))
        source = str(match.get("source", ""))

        if source == "lookup-exact":
            return True, "lookup-exact"

        tokens = [t for t in normalized.split() if t]
        has_poi_concept = any(is_poi_concept_term(token) for token in tokens)
        if any(token in NON_LOCATION_STOP_TOKENS for token in tokens):
            return False, "contains-stop-token"

        # Yön ekleri olan span'leri daha toleranslı kabul et.
        if role_hint in {"from", "to"}:
            return (similarity >= 0.72), ("direction-accepted" if similarity >= 0.72 else "direction-low-similarity")

        if role_hint == "loc":
            # "maltepe'de cami" gibi karışık span'lerde POI konsepti varsa reddet.
            if token_count > 1 and has_poi_concept:
                has_lookup_token = any(self.places.resolve_lookup(token) for token in tokens)
                if not has_lookup_token:
                    return False, "loc-span-has-poi-concept"
            return (similarity >= 0.76), ("loc-accepted" if similarity >= 0.76 else "loc-low-similarity")

        # Role hint yoksa daha sıkı filtre uygula.
        if token_count == 1:
            token = tokens[0] if tokens else normalized
            if is_likely_action_token(token):
                return False, "action-token"
            if is_poi_concept_term(token):
                return False, "poi-concept-token"
            if similarity < 0.90:
                return False, "single-low-similarity"
            return True, "single-accepted"

        # Multi-token role_hint yoksa POI konsept içeren span'leri dışarıda bırak.
        if has_poi_concept:
            return False, "multi-has-poi-concept"
        lookup_token_count = sum(1 for token in tokens if self.places.resolve_lookup(token))
        if lookup_token_count >= 2:
            return False, "multi-location-span"
        if similarity < 0.84:
            return False, "multi-low-similarity"
        return True, "multi-accepted"

    def extract_places(self, query: str, trace: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Sorgudan yer isimlerini çıkarır.

        Gelişmiş algoritma:
        1. Tek kelimeler + N-gramler (2-3 kelime grupları)
        2. Score-based filtering (yüksek skor öncelikli)
        3. Context-aware matching

        Args:
            query: Kullanıcı sorgusu

        Returns:
            Bulunan yer isimleri listesi
        """
        best_matches = {}
        candidate_spans = extract_candidate_spans(query, max_ngram=3)
        span_trace_rows = [] if trace is not None else None
        if len(candidate_spans) > self._max_candidate_spans:
            # Uzun sorgularda GPU yukunu sinirlamak icin aday span sayisini cap'le.
            candidate_spans = sorted(
                candidate_spans,
                key=lambda item: (-int(item.get("token_count", 1)), int(item.get("start", 0))),
            )[: self._max_candidate_spans]
            candidate_spans.sort(key=lambda item: (int(item.get("start", 0)), -int(item.get("token_count", 1))))

        # OSM-first: Lokasyon/POI sinyali gucluyse aday havuzunu kontrollu genislet.
        if should_prefetch_osm_for_query(query, candidate_spans):
            self.places.prefetch_osm_candidates(
                query,
                bert_engine=self.bert,
                max_queries=self.places._osm_prefetch_max_queries,
            )

        span_texts = [span["normalized"] for span in candidate_spans]
        span_embeddings = self.bert.encode_batch(span_texts) if span_texts else []

        for span, span_embedding in zip(candidate_spans, span_embeddings):
            threshold = 0.78 if span["token_count"] == 1 else 0.70
            match = self.places.find_best_match(
                query=span["normalized"],
                query_embedding=span_embedding,
                threshold=threshold,
                bert_engine=self.bert,
                allow_below_threshold=(trace is not None),
            )

            if not match:
                if span_trace_rows is not None:
                    span_trace_rows.append({
                        "surface": span["surface"],
                        "normalized": span["normalized"],
                        "role_hint": span["role_hint"],
                        "token_count": span["token_count"],
                        "threshold": float(threshold),
                        "best_place": None,
                        "best_similarity": None,
                        "best_similarity_percent": None,
                        "accepted": False,
                        "reason": "no-match",
                    })
                continue

            threshold_accepted = float(match.get("similarity", 0.0)) >= float(threshold)
            location_like, location_reason = self._is_location_like_match(span, match)
            accepted = threshold_accepted and location_like
            reason = "accepted"
            if not threshold_accepted:
                reason = "below-threshold"
            elif not location_like:
                reason = location_reason

            if span_trace_rows is not None:
                span_trace_rows.append({
                    "surface": span["surface"],
                    "normalized": span["normalized"],
                    "role_hint": span["role_hint"],
                    "token_count": span["token_count"],
                    "threshold": float(threshold),
                    "best_place": match.get("place"),
                    "best_similarity": float(match.get("similarity", 0.0)),
                    "best_similarity_percent": round(float(match.get("similarity", 0.0)) * 100.0, 2),
                    "accepted": accepted,
                    "match_source": match.get("source"),
                    "reason": reason,
                })

            if not accepted:
                continue

            candidate = {
                "place": match["place"],
                "similarity": min(
                    float(match["similarity"]) + (0.03 if span["token_count"] > 1 else 0.0),
                    1.0,
                ),
                "index": int(match["index"]) if "index" in match else None,
                "surface": span["surface"],
                "normalized": span["normalized"],
                "start": span["start"],
                "end": span["end"],
                "role_hint": span["role_hint"],
                "token_count": span["token_count"],
                "match_source": match.get("source"),
                "match_reason": reason,
            }

            existing = best_matches.get(candidate["place"])
            if not existing:
                best_matches[candidate["place"]] = candidate
                continue

            if (
                candidate["similarity"] > existing["similarity"]
                or (
                    candidate["similarity"] == existing["similarity"]
                    and (
                        candidate["token_count"] > existing["token_count"]
                        or candidate["start"] < existing["start"]
                    )
                )
            ):
                best_matches[candidate["place"]] = candidate

        found_places = [
            item for item in best_matches.values()
            if item["similarity"] >= 0.72
        ]

        # Ayni yerin daha genel/detayli varyantlari birlikte geldiyse
        # daha guvenilir ve daha dogrudan span ile uyusan adayi tercih et.
        collapsed_by_signature: Dict[Tuple[int, int, str], Dict[str, Any]] = {}
        for item in found_places:
            signature = (
                int(item.get("start", 0)),
                int(item.get("end", 0)),
                normalize_place_key(item.get("normalized") or item.get("surface") or ""),
            )
            existing = collapsed_by_signature.get(signature)
            if existing is None:
                collapsed_by_signature[signature] = item
                continue

            item_exact = str(item.get("match_source", "")) == "lookup-exact"
            existing_exact = str(existing.get("match_source", "")) == "lookup-exact"
            if item_exact and not existing_exact:
                collapsed_by_signature[signature] = item
                continue
            if item_exact == existing_exact and float(item.get("similarity", 0.0)) > float(existing.get("similarity", 0.0)):
                collapsed_by_signature[signature] = item

        found_places = list(collapsed_by_signature.values())

        if len(found_places) > 5:
            found_places.sort(key=lambda item: (-item["similarity"], item["start"]))
            found_places = found_places[:5]

        found_places.sort(key=lambda item: (item["start"], -item["token_count"], -item["similarity"]))

        if trace is not None:
            trace["candidate_spans"] = span_trace_rows or []
            trace["span_count"] = len(candidate_spans)
            trace["accepted_span_count"] = sum(1 for row in (span_trace_rows or []) if row.get("accepted"))

        return found_places

    def detect_route_direction(self, query: str, detected_places: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
        """
        "X'den Y'ye" tarzı sorgularda yönü tespit eder.

        Args:
            query: Kullanıcı sorgusu
            detected_places: Bulunan yerlerin span bazlı listesi

        Returns:
            {"origin": str | None, "destination": str | None}
        """
        if len(detected_places) < 2:
            return {"origin": None, "destination": None}

        ordered_places = sorted(
            detected_places,
            key=lambda item: (item.get("start", 0), -item.get("token_count", 1), -item.get("similarity", 0.0))
        )
        direct_single_places = [
            item for item in ordered_places
            if int(item.get("token_count", 1)) == 1 and is_route_candidate_confident(item)
        ]

        normalized_query = tr_lower(normalize_query_text(query or ""))
        if re.search(r"\b(arası|arasi)\b", normalized_query) and len(direct_single_places) >= 2:
            return {
                "origin": direct_single_places[0]["place"],
                "destination": direct_single_places[1]["place"],
            }

        def select_best(items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
            if not items:
                return None
            return sorted(
                items,
                key=lambda item: (
                    -float(item.get("similarity", 0.0)),
                    item.get("token_count", 1),
                    item.get("start", 0),
                ),
            )[0]

        origin = None
        destination = None
        origin_item = None
        destination_item = None

        from_candidates = [item for item in ordered_places if item.get("role_hint") == "from"]
        to_candidates = [item for item in ordered_places if item.get("role_hint") == "to"]

        origin_item = select_best(from_candidates)
        if origin_item:
            origin = origin_item["place"]

        destination_item = select_best([item for item in to_candidates if item["place"] != origin])
        if destination_item:
            destination = destination_item["place"]

        if origin_item and not destination:
            for item in direct_single_places or ordered_places:
                if item["start"] > origin_item["start"] and item["place"] != origin:
                    destination_item = item
                    destination = item["place"]
                    break

        if destination_item and not origin:
            for item in direct_single_places or ordered_places:
                if item["start"] < destination_item["start"] and item["place"] != destination:
                    origin_item = item
                    origin = item["place"]
                    break

        if not origin and not destination and len(direct_single_places) >= 2:
            return {
                "origin": direct_single_places[0]["place"],
                "destination": direct_single_places[1]["place"],
            }

        if not origin:
            origin = (direct_single_places or ordered_places)[0]["place"]

        if not destination:
            pool = direct_single_places[1:] if direct_single_places else ordered_places[1:]
            for item in pool:
                if item["place"] != origin:
                    destination = item["place"]
                    break

        return {"origin": origin, "destination": destination}

    def _choose_best_poi_location(self, ordered_places: List[Dict[str, Any]]) -> Optional[str]:
        """POI sorgularında en güvenilir lokasyon adayını seçer."""
        if not ordered_places:
            return None

        exact_candidates = [p for p in ordered_places if float(p.get("similarity", 0.0)) >= 0.999]
        if exact_candidates:
            exact_candidates.sort(key=lambda p: (p.get("token_count", 1), p.get("start", 0)))
            return exact_candidates[0]["place"]

        role_loc_candidates = [p for p in ordered_places if p.get("role_hint") == "loc"]
        if role_loc_candidates:
            role_loc_candidates.sort(
                key=lambda p: (
                    p.get("token_count", 1),
                    -float(p.get("similarity", 0.0)),
                    p.get("start", 0),
                )
            )
            return role_loc_candidates[0]["place"]

        best = sorted(
            ordered_places,
            key=lambda p: (
                -float(p.get("similarity", 0.0)),
                p.get("token_count", 1),
                p.get("start", 0),
            ),
        )[0]
        return best["place"]

    def parse(self, query: str, include_trace: bool = False) -> Dict[str, Any]:
        """
        Ana parse fonksiyonu.

        Args:
            query: Kullanıcı sorgusu

        Returns:
            {
                "type": "route" | "poi" | "multi" | "single" | "unknown",
                "confidence": float,
                "origin": str | None,
                "destination": str | None,
                "locations": list[str] | None,
                "place": str | None,  # POI için
                "raw_query": str,
                "detected_places": list[dict],
                "error": str | None
            }
        """
        start_time = time.time()

        if not query or not isinstance(query, str):
            return {
                "type": "unknown",
                "confidence": 0.0,
                "raw_query": query,
                "error": "Geçersiz sorgu",
                "detected_places": []
            }

        normalized_query_for_guard = normalize_query_text(query)
        if re.search(r"\b(merhaba|selam|nasılsın|nasilsin|iyi\s*misin)\b", normalized_query_for_guard):
            return {
                "type": "unknown",
                "confidence": 0.95,
                "raw_query": query,
                "detected_places": [],
                "error": None,
                "parse_time": time.time() - start_time,
            }

        trace_data: Optional[Dict[str, Any]] = {} if include_trace else None

        # 1. Sorgu tipini sınıflandır
        # 1) Intent siniflandirma (route/poi/multi/single/unknown)
        query_type, type_confidence, type_scores = self.classify_query_type_with_scores(query)
        initial_query_type = query_type
        initial_type_confidence = float(type_confidence)

        # 2. Yer isimlerini çıkar
        # 2) Span cikarma + semantic place eslestirme
        detected_places = self.extract_places(query, trace=trace_data)
        ordered_places = sorted(
            detected_places,
            key=lambda item: (item.get("start", 0), -item.get("token_count", 1), -item.get("similarity", 0.0))
        )
        place_names = [p["place"] for p in ordered_places]
        unique_place_names = list(dict.fromkeys(place_names))
        role_hints = {p.get("role_hint") for p in ordered_places if p.get("role_hint")}
        direction_hints = bool({"from", "to"} & role_hints)
        normalized_query = normalize_query_text(query)
        normalized_query_lower = tr_lower(normalized_query)
        route_intent_cue = bool(
            re.search(r"\b(" + "|".join(re.escape(term) for term in ROUTE_INTENT_TERMS) + r"|arası|arasi)\b", normalized_query_lower)
        )
        route_pattern_cue = has_explicit_route_pattern(query, ordered_places)
        multi_action_cue = bool(
            re.search(r"\b(gezi|gezisi|gez|turu|planı|plani|dolaş|dolas)\b", normalized_query_lower)
        )
        explicit_multi_delimiter = bool(re.search(r",|\bve\b", normalized_query_lower))
        explicit_multi_places = _extract_explicit_multi_places(query)
        plain_multi_places = _extract_plain_multi_places(query)
        strong_single_place_count = sum(
            1
            for p in ordered_places
            if int(p.get("token_count", 1)) == 1 and float(p.get("similarity", 0.0)) >= 0.82
        )
        max_place_similarity = max((float(p.get("similarity", 0.0)) for p in ordered_places), default=0.0)
        score_ranking = sorted(type_scores.items(), key=lambda item: item[1], reverse=True)
        score_margin = (
            float(score_ranking[0][1] - score_ranking[1][1])
            if len(score_ranking) >= 2
            else float(score_ranking[0][1]) if score_ranking else 0.0
        )
        low_margin = score_margin < INTENT_MARGIN_MIN
        strong_route_pair = has_confident_route_pair(ordered_places)
        direct_place_candidates = [
            p for p in ordered_places
            if str(p.get("match_source", "")) == "lookup-exact"
            or (
                p.get("role_hint") in {"from", "to", "loc"}
                and int(p.get("token_count", 1)) == 1
                and float(p.get("similarity", 0.0)) >= 0.95
            )
        ]
        direct_place_count = len({p.get("place") for p in direct_place_candidates if p.get("place")})
        has_direct_place_signal = direct_place_count > 0
        poi_resolution = extract_poi_concept_with_meta(query, ordered_places)
        poi_concept = (poi_resolution.get("concept") or "").strip()
        poi_osm_queries = poi_resolution.get("osm_queries") or []
        has_poi_cue = bool(poi_concept)
        generic_poi_browse_cue = any(
            re.search(r"\b" + re.escape(term) + r"\b", normalized_query_lower)
            for term in GENERIC_POI_BROWSE_TERMS
        )
        has_multi_cue = (
            (explicit_multi_delimiter and len(unique_place_names) >= 2 and not direction_hints)
            or (
                multi_action_cue
                and not direction_hints
                and (
                    strong_single_place_count >= 2
                    or len(explicit_multi_places) >= 2
                    or len(plain_multi_places) >= 3
                )
            )
        )

        # 3) Cakisma matrisi: intent sinyalleri celisirse son karari dengeler.
        query_type, type_confidence, intent_matrix_meta = apply_intent_conflict_matrix(
            query_type,
            float(type_confidence),
            has_poi_cue=has_poi_cue,
            has_multi_cue=has_multi_cue,
            direction_hints=direction_hints,
            unique_place_count=len(unique_place_names),
            low_margin=low_margin,
            route_intent_cue=(route_intent_cue or route_pattern_cue),
            strong_route_pair=strong_route_pair,
        )

        # Chitchat/non-location guard: zayıf lokasyon sinyallerinde POI'ye düşme.
        poi_question_cue = bool(
            re.search(
                r"\b(neler|nereler|ne var|yakında|civarında|civarinda|çevresinde|cevresinde|gezilecek|yemek|müze|muze|kafe|restoran|cami|eczane)\b",
                normalized_query_lower,
            )
        ) or generic_poi_browse_cue
        mixed_poi_place_conflict = has_poi_cue and direct_place_count >= 2 and not has_multi_cue
        ambiguous_loc_to_route = (
            route_intent_cue
            and "loc" in role_hints
            and "to" in role_hints
            and "from" not in role_hints
        )
        force_unknown_intent = False

        if not has_direct_place_signal and query_type in {"route", "poi", "single", "multi"}:
            query_type = "unknown"
            type_confidence = min(float(type_confidence), 0.45)
            intent_matrix_meta["final_type"] = "unknown"
            intent_matrix_meta["reason"] = "no-direct-place-signal=>unknown"

        if mixed_poi_place_conflict or ambiguous_loc_to_route:
            query_type = "unknown"
            type_confidence = min(float(type_confidence), 0.45)
            intent_matrix_meta["final_type"] = "unknown"
            intent_matrix_meta["reason"] = "mixed-intent=>unknown"
            force_unknown_intent = True

        if query_type == "route" and has_multi_cue and not direction_hints and len(plain_multi_places) >= 3:
            query_type = "multi"
            type_confidence = min(max(float(type_confidence), 0.78), 0.90)
            intent_matrix_meta["final_type"] = "multi"
            intent_matrix_meta["reason"] = "route-plan-list=>multi"

        if query_type == "poi" and multi_action_cue and len(plain_multi_places) >= 3 and not direction_hints:
            query_type = "multi"
            type_confidence = min(max(float(type_confidence), 0.80), 0.92)
            intent_matrix_meta["final_type"] = "multi"
            intent_matrix_meta["reason"] = "strong-plain-multi-pattern=>multi"

        if query_type == "route" and poi_question_cue and not route_intent_cue:
            query_type = "poi"
            type_confidence = min(max(float(type_confidence), 0.70), 0.86)
            intent_matrix_meta["final_type"] = "poi"
            intent_matrix_meta["reason"] = "poi-question-cue=>poi"

        if query_type == "poi" and not has_poi_cue and not poi_question_cue and not any(h == "loc" for h in role_hints):
            query_type = "unknown"
            type_confidence = min(float(type_confidence), 0.45)
            intent_matrix_meta["final_type"] = "unknown"
            intent_matrix_meta["reason"] = "weak-poi-signal=>unknown"

        if (
            query_type == "multi"
            and multi_action_cue
            and not has_multi_cue
            and not direction_hints
            and not has_poi_cue
            and not poi_question_cue
            and len(unique_place_names) == 1
            and len(plain_multi_places) == 1
            and normalize_place_key(plain_multi_places[0]) == normalize_place_key(unique_place_names[0])
            and direct_place_count == 1
        ):
            query_type = "single"
            type_confidence = min(max(float(type_confidence), 0.72), 0.88)
            intent_matrix_meta["final_type"] = "single"
            intent_matrix_meta["reason"] = "single-action-rescue=>single"

        # Lokasyon yakalansa da POI niyeti kaybolduysa son adimda geri kazan.
        if should_rescue_poi_intent(
            query_type=query_type,
            has_poi_cue=has_poi_cue,
            poi_question_cue=poi_question_cue,
            route_intent_cue=route_intent_cue,
            direction_hints=direction_hints,
            role_hints=role_hints,
            unique_place_count=len(unique_place_names),
        ):
            query_type = "poi"
            type_confidence = max(float(type_confidence), 0.72)
            intent_matrix_meta["final_type"] = "poi"
            intent_matrix_meta["reason"] = "poi-intent-rescue=>poi"

        if trace_data is not None:
            trace_data["query"] = query
            trace_data["query_type_initial"] = initial_query_type
            trace_data["confidence_initial"] = initial_type_confidence
            trace_data["query_type_final"] = query_type
            trace_data["confidence_final"] = float(type_confidence)
            trace_data["type_scores"] = {k: float(v) for k, v in type_scores.items()}
            trace_data["intent_signals"] = {
                "has_poi_cue": has_poi_cue,
                "has_multi_cue": has_multi_cue,
                "direction_hints": direction_hints,
                "route_intent_cue": route_intent_cue,
                "route_pattern_cue": route_pattern_cue,
                "strong_route_pair": strong_route_pair,
                "multi_action_cue": multi_action_cue,
                "generic_poi_browse_cue": generic_poi_browse_cue,
                "explicit_multi_delimiter": explicit_multi_delimiter,
                "explicit_multi_places": explicit_multi_places,
                "plain_multi_places": plain_multi_places,
                "strong_single_place_count": strong_single_place_count,
                "direct_place_count": direct_place_count,
                "max_place_similarity": round(float(max_place_similarity), 4),
                "score_margin": round(float(score_margin), 4),
                "role_hints": sorted(role_hints),
                "detected_place_names": place_names,
                "poi_concept": poi_concept,
                "poi_resolution_source": poi_resolution.get("source"),
                "poi_resolution_confidence": round(float(poi_resolution.get("confidence", 0.0)), 4),
                "poi_resolution_status": poi_resolution.get("status"),
                "poi_token_candidates": poi_resolution.get("tokens", []),
                "poi_candidate_count": len(poi_resolution.get("candidates", []) or []),
                "poi_osm_queries_count": len(poi_osm_queries),
            }
            trace_data["poi_resolution_plan"] = poi_resolution.get("debug_plan", {})
            trace_data["intent_conflict_matrix"] = intent_matrix_meta

        # 3. Numpy değerlerini Python native türlere çevir (JSON için)
        detected_places_json = [
            {
                "place": p["place"],
                "similarity": float(p["similarity"]),  # numpy.float32 -> float
                "index": int(p["index"]) if "index" in p else None,
                "surface": p.get("surface"),
                "normalized": p.get("normalized"),
                "start": p.get("start"),
                "end": p.get("end"),
                "role_hint": p.get("role_hint"),
            }
            for p in ordered_places
        ]

        # 4. Yere göre sonuç oluştur
        result = {
            "type": query_type,
            "confidence": float(type_confidence),  # numpy.float32 -> float
            "raw_query": query,
            "detected_places": detected_places_json,
            "error": None
        }

        if query_type == "route":
            # Origin ve destination tespit et
            direction = self.detect_route_direction(query, ordered_places)
            result["origin"] = direction["origin"]
            result["destination"] = direction["destination"]

            # Eğer direction bulunamazsa place_names kullan
            if not result["origin"] and len(place_names) >= 2:
                result["origin"] = place_names[0]
                result["destination"] = place_names[1]

        elif query_type == "poi":
            result["location"] = self._choose_best_poi_location(ordered_places)
            result["poi_concept"] = poi_concept or None
            result["poi_resolution_source"] = poi_resolution.get("source")
            result["poi_resolution_confidence"] = float(poi_resolution.get("confidence", 0.0))
            result["poi_resolution_status"] = poi_resolution.get("status")
            result["poi_token_candidates"] = poi_resolution.get("tokens", [])
            result["poi_resolution_plan"] = poi_resolution.get("debug_plan", {})
            result["poi_osm_queries"] = poi_osm_queries
            concept_key = normalize_place_key(poi_concept) if poi_concept else ""
            if concept_key and concept_key in NORMALIZED_POI_MAPPING:
                result["poi_tags_hint"] = dict(NORMALIZED_POI_MAPPING[concept_key])
            elif poi_osm_queries:
                first_query = poi_osm_queries[0]
                if isinstance(first_query, dict):
                    result["poi_tags_hint"] = dict(first_query)
            result["query_type"] = "search"

            # Lokasyon sinyali çok zayıfsa POI'den unknown'a düş.
            has_loc_role = any(p.get("role_hint") == "loc" for p in ordered_places)
            generic_browse_query = bool(
                re.search(
                    r"\b(neler var|nereler var|ne var|ne yapabilirim|yakında|civarında|civarinda|çevresinde|cevresinde|gezilecek)\b",
                    normalized_query_lower,
                )
            ) or poi_question_cue or generic_poi_browse_cue

            # "kadikoyde cami ariyorum" gibi sorgularda lokasyon+mekan birlikte zorunlu.
            # Sadece lokasyon varsa (ve generic browse da degilse) sonucu unknown'a indir.
            has_structured_poi_target = (
                bool(result.get("poi_concept"))
                or bool(result.get("poi_tags_hint"))
                or poi_question_cue
                or generic_poi_browse_cue
            )
            if result.get("location") and (not has_structured_poi_target) and (not generic_browse_query):
                result["type"] = "unknown"
                result["error"] = "Mekan tipi anlasilamadi"
            elif (not has_poi_cue) and (not has_loc_role) and max_place_similarity < 0.82:
                result["type"] = "unknown"
                result["error"] = "Sorgu anlaşılamadı"
            elif not result["location"]:
                result["type"] = "unknown"
                result["error"] = "Sorgu anlaşılamadı"

        elif query_type == "multi":
            # Çoklu sorguda tekil span'ler (token_count=1) genelde daha güvenilir.
            strong_single_places = []
            seen_places = set()
            for item in ordered_places:
                if int(item.get("token_count", 1)) != 1:
                    continue
                if float(item.get("similarity", 0.0)) < 0.78:
                    continue
                place = item.get("place")
                if not place or place in seen_places:
                    continue
                seen_places.add(place)
                strong_single_places.append(place)

            allow_multi = (
                (explicit_multi_delimiter and len(strong_single_places) >= 2)
                or (multi_action_cue and len(strong_single_places) >= 2)
                or (len(explicit_multi_places) >= 2)
                or (multi_action_cue and len(plain_multi_places) >= 3)
            )

            if direction_hints and strong_route_pair and not has_multi_cue:
                result["type"] = "route"
                direction = self.detect_route_direction(query, ordered_places)
                result["origin"] = direction["origin"]
                result["destination"] = direction["destination"]
                if trace_data is not None:
                    intent_matrix_meta["final_type"] = "route"
                    intent_matrix_meta["reason"] = "multi-to-route-rescue"
            elif allow_multi:
                if len(explicit_multi_places) >= 2:
                    result["locations"] = explicit_multi_places
                elif multi_action_cue and len(plain_multi_places) >= 3:
                    result["locations"] = plain_multi_places[:4]
                else:
                    result["locations"] = strong_single_places
            else:
                # Multi sinyali zayıfsa yanlış pozitiften kaçın.
                if has_poi_cue:
                    result["type"] = "poi"
                    result["location"] = self._choose_best_poi_location(ordered_places)
                    result["poi_concept"] = poi_concept or None
                    result["poi_resolution_source"] = poi_resolution.get("source")
                    result["poi_resolution_confidence"] = float(poi_resolution.get("confidence", 0.0))
                    result["poi_resolution_status"] = poi_resolution.get("status")
                    result["poi_token_candidates"] = poi_resolution.get("tokens", [])
                    result["poi_resolution_plan"] = poi_resolution.get("debug_plan", {})
                    result["poi_osm_queries"] = poi_osm_queries
                    concept_key = normalize_place_key(poi_concept) if poi_concept else ""
                    if concept_key and concept_key in NORMALIZED_POI_MAPPING:
                        result["poi_tags_hint"] = dict(NORMALIZED_POI_MAPPING[concept_key])
                    elif poi_osm_queries:
                        first_query = poi_osm_queries[0]
                        if isinstance(first_query, dict):
                            result["poi_tags_hint"] = dict(first_query)
                    result["query_type"] = "search"
                else:
                    result["type"] = "unknown"
                    result["error"] = "Sorgu anlaşılamadı"

        elif query_type == "single":
            # Tek hedefte önce "to" rol ipucunu, yoksa ilk yeri kullan
            destination_match = next((p for p in ordered_places if p.get("role_hint") == "to"), None)
            if destination_match is None:
                single_token_candidates = [p for p in ordered_places if int(p.get("token_count", 1)) == 1]
                candidate_pool = single_token_candidates if single_token_candidates else ordered_places
                if candidate_pool:
                    destination_match = sorted(
                        candidate_pool,
                        key=lambda p: (
                            -float(p.get("similarity", 0.0)),
                            int(p.get("token_count", 1)),
                            int(p.get("start", 0)),
                        ),
                    )[0]

            result["destination"] = destination_match["place"] if destination_match else (place_names[0] if place_names else None)

        elif query_type == "unknown":
            # Bilinmeyen tip - yer isimlerine göre karar ver
            if force_unknown_intent:
                result["error"] = "Sorgu anlaşılamadı"
            elif direction_hints and strong_route_pair:
                result["type"] = "route"
                direction = self.detect_route_direction(query, ordered_places)
                result["origin"] = direction["origin"]
                result["destination"] = direction["destination"]
                if trace_data is not None:
                    intent_matrix_meta["final_type"] = "route"
                    intent_matrix_meta["reason"] = "route-pattern"
            elif has_multi_cue and len(place_names) >= 2:
                result["type"] = "multi"
                if len(explicit_multi_places) >= 2:
                    result["locations"] = explicit_multi_places
                elif multi_action_cue and len(plain_multi_places) >= 3:
                    result["locations"] = plain_multi_places[:4]
                else:
                    result["locations"] = place_names
            elif len(place_names) == 2:
                strong_match = all(is_route_candidate_confident(p) for p in ordered_places[:2])
                has_direction_hint = bool({"from", "to"} & role_hints)
                if strong_match and has_direction_hint:
                    result["type"] = "route"
                    direction = self.detect_route_direction(query, ordered_places)
                    result["origin"] = direction["origin"] or place_names[0]
                    result["destination"] = direction["destination"] or place_names[1]
                    if trace_data is not None:
                        intent_matrix_meta["final_type"] = "route"
                        intent_matrix_meta["reason"] = "candidate-dedup"
                else:
                    result["error"] = "Sorgu anlaşılamadı"
            elif len(place_names) == 1:
                single_candidate = ordered_places[0]
                single_action_cue = (
                    multi_action_cue
                    and len(plain_multi_places) == 1
                    and normalize_place_key(plain_multi_places[0]) == normalize_place_key(place_names[0])
                )
                single_is_direct = (
                    str(single_candidate.get("match_source", "")) == "lookup-exact"
                    or single_candidate.get("role_hint") == "to"
                )
                if (
                    single_candidate.get("similarity", 0.0) >= 0.82
                    and (
                        single_candidate.get("role_hint") == "to"
                        or (single_is_direct and single_action_cue)
                    )
                ):
                    result["type"] = "single"
                    result["destination"] = place_names[0]
                    if trace_data is not None:
                        intent_matrix_meta["final_type"] = "single"
                        intent_matrix_meta["reason"] = "single-action-rescue"
                else:
                    result["error"] = "Sorgu anlaşılamadı"
            else:
                result["error"] = "Sorgu anlaşılamadı"

        # Parse süresi
        result["parse_time"] = time.time() - start_time
        if trace_data is not None:
            trace_data["parse_time_ms"] = round(float(result["parse_time"]) * 1000.0, 2)
            trace_data["selected"] = {
                "type": result.get("type"),
                "origin": result.get("origin"),
                "destination": result.get("destination"),
                "location": result.get("location"),
                "locations": result.get("locations"),
                "poi_concept": result.get("poi_concept"),
                "poi_resolution_source": result.get("poi_resolution_source"),
                "poi_resolution_confidence": result.get("poi_resolution_confidence"),
                "poi_resolution_status": result.get("poi_resolution_status"),
                "poi_tags_hint": result.get("poi_tags_hint"),
                "poi_osm_queries": result.get("poi_osm_queries"),
            }
            result["trace"] = trace_data

        return result


# =============================================================================
# SINGLETON
# =============================================================================

_bert_nlp_engine = None
_bert_nlp_engine_lock = threading.Lock()

def get_bert_nlp_engine() -> BertNLPEngine:
    """
    Global BERT NLP engine singleton'ını döner.
    """
    global _bert_nlp_engine

    if _bert_nlp_engine is None:
        with _bert_nlp_engine_lock:
            if _bert_nlp_engine is None:
                _bert_nlp_engine = BertNLPEngine()

    return _bert_nlp_engine


# =============================================================================
# TEST
# =============================================================================

def test_bert_nlp():
    """BERT NLP engine test."""
    print("=" * 60)
    print("BERT NLP ENGINE TEST")
    print("=" * 60)

    if not is_bert_available():
        print("[HATA] BERT kütüphaneleri yok!")
        return

    try:
        engine = get_bert_nlp_engine()

        # Test sorguları
        test_queries = [
            "Kadıköy'den Beşiktaş'a rota",
            "Kadıköy'de neler var",
            "Kadikoy, Taksim ve Beşiktasi gez",  # Typo ile!
            "Taksim'e git",
            "Boğaz turu yap",  # Bilinmeyen
        ]

        for query in test_queries:
            print(f"\n[SORGU]: {query}")
            print("-" * 40)

            result = engine.parse(query)

            print(f"Tip: {result['type']} | Confidence: {result['confidence']:.2f}")
            print(f"Süre: {result.get('parse_time', 0):.3f}s")

            if result.get('origin'):
                print(f"  [BASLANGIC]: {result['origin']}")
            if result.get('destination'):
                print(f"  [VARIS]: {result['destination']}")
            if result.get('location'):
                print(f"  [KONUM]: {result['location']}")
            if result.get('locations'):
                print(f"  [YERLER]: {result['locations']}")

            print(f"  [TESPIT EDILEN]: {[p['place'] for p in result['detected_places']]}")

        print("\n" + "=" * 60)
        print("[TAMAMLANDI]")

    except Exception as e:
        print(f"[HATA] {e}")


if __name__ == "__main__":
    test_bert_nlp()
