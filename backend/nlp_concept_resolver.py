"""
nlp_concept_resolver.py - POI konsept çözümleyici (faz-1)

Amaç:
- Türkçe yüzey formlardan (ekli/çoğul) POI kökünü çıkarmak
- Sözlük doğrulama + rollback
- Opsiyonel semantik fallback kancası
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import get_close_matches
import re
from typing import Callable, Dict, List, Optional, Tuple

from osm_poi_dictionary import POI_MAPPING


@dataclass
class PoiResolution:
    concept: Optional[str]
    source: str
    confidence: float
    status: str  # success | unknown | ambiguous
    candidates: List[str]


_TR_FOLD_TABLE = str.maketrans({
    "ç": "c",
    "ğ": "g",
    "ı": "i",
    "ö": "o",
    "ş": "s",
    "ü": "u",
})

# Türkçe ek soyma için basit suffix listeleri (faz-1)
_CASE_SUFFIXES = (
    "lardan", "lerden", "dan", "den", "tan", "ten",
    "daki", "deki", "taki", "teki",
    "daki", "deki",
    "nın", "nin", "nun", "nün",
    "na", "ne", "ya", "ye",
    "da", "de", "ta", "te",
    "ı", "i", "u", "ü", "yı", "yi", "yu", "yü",
)

_PLURAL_SUFFIXES = ("lar", "ler")

# Over-stemming riskli alanlar için korunan ifadeler
_PROTECTED_FULL_FORMS = {
    "dondurma", "kokoreç", "lahmacun", "çiğköfte", "çiğ köfte", "baklava"
}


def normalize_text(value: str) -> str:
    text = (value or "").replace("’", "'").replace("`", "'")
    text = text.casefold()
    text = re.sub(r"[^a-z0-9çğıöşü\s']+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tr_fold(value: str) -> str:
    return normalize_text(value).translate(_TR_FOLD_TABLE)


def singularize_token(token: str) -> str:
    t = normalize_text(token)
    for suf in _PLURAL_SUFFIXES:
        if t.endswith(suf) and len(t) > len(suf) + 2:
            return t[:-len(suf)]
    return t


def strip_case_suffix(token: str) -> str:
    t = normalize_text(token)
    if t in _PROTECTED_FULL_FORMS:
        return t

    # apostrof ile gelen ekler: malatya'da
    if "'" in t:
        base, suffix = t.rsplit("'", 1)
        if suffix and suffix in _CASE_SUFFIXES and len(base) >= 2:
            return base

    for suf in _CASE_SUFFIXES:
        if t.endswith(suf) and len(t) > len(suf) + 2:
            candidate = t[:-len(suf)]
            if candidate and candidate not in _PROTECTED_FULL_FORMS:
                return candidate

    return t


def morph_candidates(surface: str) -> List[str]:
    """Katman-1: morfolojik adaylar (top-k)."""
    s = normalize_text(surface)
    if not s:
        return []

    cands: List[str] = []

    def push(v: str) -> None:
        v = normalize_text(v)
        if v and v not in cands:
            cands.append(v)

    push(s)
    push(strip_case_suffix(s))
    push(singularize_token(s))
    push(singularize_token(strip_case_suffix(s)))

    # çok kelimeli ifade ise son token'a da bak
    parts = s.split()
    if len(parts) > 1:
        tail = parts[-1]
        push(tail)
        push(strip_case_suffix(tail))
        push(singularize_token(tail))
        push(singularize_token(strip_case_suffix(tail)))

    return cands


def _build_index(mapping: Dict[str, Dict[str, str]]) -> Tuple[Dict[str, str], List[str]]:
    """Canonical/synonym index oluşturur."""
    idx: Dict[str, str] = {}
    canonicals: List[str] = []

    for key in mapping.keys():
        canonical = normalize_text(key)
        if not canonical:
            continue

        if canonical not in canonicals:
            canonicals.append(canonical)

        variants = {
            canonical,
            tr_fold(canonical),
            singularize_token(canonical),
            singularize_token(strip_case_suffix(canonical)),
        }

        for v in variants:
            if v:
                idx.setdefault(v, canonical)

    return idx, canonicals


_POI_INDEX, _POI_CANONICALS = _build_index(POI_MAPPING)


def _dict_lookup(candidate: str) -> Optional[str]:
    c = normalize_text(candidate)
    if not c:
        return None
    return _POI_INDEX.get(c) or _POI_INDEX.get(tr_fold(c))


def resolve_poi_concept(
    surface: str,
    bert_matcher: Optional[Callable[[str], Optional[Tuple[str, float]]]] = None,
    bert_threshold: float = 0.80,
) -> PoiResolution:
    """
    Faz-1 çözümleyici:
    1) morph_candidates
    2) sözlük doğrulama
    3) basit rule+dict yakın eşleşme
    4) opsiyonel bert fallback
    """
    cands = morph_candidates(surface)

    # Katman-1 + Katman-2
    for c in cands:
        canonical = _dict_lookup(c)
        if canonical:
            return PoiResolution(
                concept=canonical,
                source="morph+dict",
                confidence=0.95,
                status="success",
                candidates=cands,
            )

    # Katman-2b: rule+dict (yakın string)
    normalized = normalize_text(surface)
    if normalized:
        pool = list(_POI_INDEX.keys())
        near = get_close_matches(normalized, pool, n=1, cutoff=0.90)
        if near:
            canonical = _dict_lookup(near[0])
            if canonical:
                return PoiResolution(
                    concept=canonical,
                    source="rule+dict",
                    confidence=0.88,
                    status="success",
                    candidates=cands,
                )

    # Katman-3: opsiyonel BERT fallback
    if bert_matcher is not None and normalized and len(normalized) >= 4:
        try:
            matched = bert_matcher(normalized)
        except Exception:
            matched = None

        if matched:
            term, score = matched
            canonical = _dict_lookup(term)
            if canonical and float(score) >= bert_threshold:
                return PoiResolution(
                    concept=canonical,
                    source="bert",
                    confidence=float(score),
                    status="success",
                    candidates=cands,
                )

    return PoiResolution(
        concept=None,
        source="unknown",
        confidence=0.0,
        status="unknown",
        candidates=cands,
    )


def build_poi_ngrams(tokens: List[str], max_ngram: int = 3) -> List[str]:
    """3->2->1 ngram adayları üretir."""
    items: List[str] = []
    n = len(tokens)
    for size in range(max_ngram, 0, -1):
        for i in range(0, n - size + 1):
            gram = " ".join(tokens[i:i + size]).strip()
            if gram and gram not in items:
                items.append(gram)
    return items


def resolve_poi_from_tokens(
    tokens: List[str],
    bert_matcher: Optional[Callable[[str], Optional[Tuple[str, float]]]] = None,
) -> PoiResolution:
    """Token listesinden en iyi POI konseptini döndürür."""
    ngrams = build_poi_ngrams(tokens, max_ngram=3)
    best = PoiResolution(None, "unknown", 0.0, "unknown", [])

    for gram in ngrams:
        res = resolve_poi_concept(gram, bert_matcher=bert_matcher)
        if res.status == "success" and res.confidence > best.confidence:
            best = res
            # yüksek güvenli bulduysak erken çık
            if res.source == "morph+dict":
                return best

    return best


def extract_candidates(query: str) -> List[str]:
    """Sorgudan resolver için aday token/ngram listesi çıkarır."""
    normalized = normalize_text(query)
    if not normalized:
        return []

    tokens = [t for t in normalized.split() if len(t) >= 2]
    grams = build_poi_ngrams(tokens, max_ngram=3)
    out: List[str] = []

    for gram in grams:
        for cand in morph_candidates(gram):
            if cand and cand not in out:
                out.append(cand)

    return out


def normalize_poi_concept(surface: str) -> Optional[str]:
    """Yüzey formu canonical POI konseptine normalize eder."""
    res = resolve_poi_concept(surface)
    return res.concept if res.status == "success" else None


def map_concept_to_osm_queries(concept: str) -> List[Dict[str, str]]:
    """
    Canonical konsepti OSM tag sorgularına map eder.

    Dönüş birden fazla query verebilir (faz-1: şimdilik tek kayıt + fallback amenity).
    """
    canonical = normalize_text(concept)
    if not canonical:
        return []

    tags = POI_MAPPING.get(canonical)
    if tags:
        return [dict(tags)]

    # basit fallback: bilinmeyen konsepti amenity name aramasına bırak
    return [{"name": canonical}]


def resolve_query(query: str) -> Dict[str, object]:
    """Sorguyu konsept adaylarıyla çözümleyip OSM query planı döndürür."""
    candidates = extract_candidates(query)
    best = PoiResolution(None, "unknown", 0.0, "unknown", [])

    for cand in candidates:
        res = resolve_poi_concept(cand)
        if res.status == "success" and res.confidence >= best.confidence:
            best = res

    concept = best.concept
    return {
        "query": query,
        "concept": concept,
        "source": best.source,
        "confidence": float(best.confidence),
        "status": best.status,
        "candidates": candidates,
        "osm_queries": map_concept_to_osm_queries(concept) if concept else [],
    }
