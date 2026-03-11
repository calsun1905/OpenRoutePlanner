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
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

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



# =============================================================================
# SORGU TİPLERİ İÇİN BERT EMBEDding TEMPLATES
# =============================================================================
# Her sorgu tipi için "örnek cümle embedding'leri" tutuyoruz
# Kullanıcı sorgusunu bu template'lerle karşılaştıracağız

QUERY_TEMPLATES = {
    "route": [
        "Kadıköy'den Beşiktaş'a rota",
        "Taksim'den Kadıköy'e gitmek istiyorum",
        "Ankara'dan İstanbul'a nasıl giderim",
        "Başlangıçtan varışa yol tarifi",
        "İki nokta arası güzergah",
    ],
    "poi": [
        "Kadıköy'de neler var",
        "Taksim'de ne yapabilirim",
        "Beşiktaş'ta nereler var",
        "Bu bölgede mekan arıyorum",
        "Yakında neleri gezebilirim",
    ],
    "multi": [
        "Kadıköy, Taksim ve Beşiktaş'ı gez",
        "Üç yer birden rota yap",
        "Birden fazla nokta ziyaret",
        "Çoklu duraklı gezi",
    ],
    "single": [
        "Taksim'e git",
        "Kadıköy'e nasıl giderim",
        "Bu yere varmak istiyorum",
        "Tek bir hedef belirle",
    ]
}

QUERY_NOISE_WORDS = {
    "rota", "rotası", "yol", "güzergah", "git", "gidilir", "giderim",
    "nasıl", "neler", "nereler", "var", "ne", "yapabilirim", "gez",
    "gezdir", "göster", "çiz", "hesapla", "bir", "ve", "ile", "bu",
    "yer", "nokta", "için", "yakında", "yakın", "istiyorum",
    "gitmek", "gidelim", "gideyim", "gidelım",
    "dolaş", "dolas", "dolaşalım", "dolasalim", "dolaşmak", "dolasmak",
    "gezelim", "plani", "planı", "turu", "turu",
    "merhaba", "selam", "nasılsın", "nasilsin", "bugün", "yarın", "yarin",
    "hava", "durumu", "mı", "mi", "mu", "mü"
}

POI_CUE_WORDS = {
    "neler", "nereler", "nerede", "civar", "civarinda", "çevre", "cevre",
    "yakın", "yakin", "var", "kahve", "yemek", "müze", "muze",
    "gezilecek", "göster", "goster", "mekan",
}

MULTI_CUE_WORDS = {
    "ve", "gezi", "tur", "turu", "plan", "plani", "dolaş", "dolas", ",",
}

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9ÇĞİÖŞÜçğıöşü]+(?:['’`][A-Za-z0-9ÇĞİÖŞÜçğıöşü]+)?")
FROM_SUFFIXES = ("den", "dan", "ten", "tan", "nden", "ndan")
TO_SUFFIXES_APOSTROPHE = ("ye", "ya", "e", "a", "na", "ne")
TO_SUFFIXES_PLAIN = ("ye", "ya", "na", "ne")
LOC_SUFFIXES = ("de", "da", "te", "ta")
COMMON_ALIASES = {
    "kadikoy": "kadıköy",
    "besiktas": "beşiktaş",
    "uskudar": "üsküdar",
    "sisli": "şişli",
    "cankaya": "çankaya",
    "kizilay": "kızılay",
    "goztepe": "göztepe",
    "ortakoy": "ortaköy",
    "bakirkoy": "bakırköy",
}

ACTION_WORD_SUFFIXES = (
    "yorum", "iyorum", "ıyorum", "uyorum",
    "yoruz", "iyoruz", "ıyoruz", "uyoruz",
    "mek", "mak",
)


def _env_flag(name: str, default: bool) -> bool:
    """ENV'den bool değer okur."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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
    text = re.sub(r"\s+", " ", text).strip().casefold()
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
    if normalized in QUERY_NOISE_WORDS:
        return True
    return len(normalized) >= 5 and normalized.endswith(ACTION_WORD_SUFFIXES)


def _singularize_tr_token(token: str) -> str:
    """Basit çoğul eklerini budar (mekanlar -> mekan)."""
    lowered = normalize_place_key(token)
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
    return any(_singularize_tr_token(token) in POI_CONCEPT_TOKENS for token in normalized.split())


def extract_poi_concept(query: str, detected_places: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    POI sorgusundan lokasyon dışı kavramı çıkarır.
    Örnek: "maltepe'de cami arıyorum" -> "cami"
    """
    normalized_query = normalize_query_text(query or "")
    if not normalized_query:
        return ""

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
        if in_occupied_range(match.start(), match.end()):
            continue

        token_surface = match.group(0)
        token_normalized, role_hint = normalize_token_with_role(token_surface)
        token_normalized = _singularize_tr_token(token_normalized)

        if len(token_normalized) < 2:
            continue
        if role_hint in {"from", "to", "loc"}:
            continue
        if token_normalized in QUERY_NOISE_WORDS:
            continue
        if is_likely_action_token(token_normalized):
            continue
        if token_normalized in seen:
            continue
        seen.add(token_normalized)
        concept_tokens.append(token_normalized)

    # Önce sözlükteki kavram token'larını önceliklendir.
    prioritized = [t for t in concept_tokens if is_poi_concept_term(t)]
    remaining = [t for t in concept_tokens if t not in prioritized]
    ordered = prioritized + remaining
    return " ".join(ordered[:4]).strip()


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
    cleaned = normalize_query_text(token).strip(".,;:!?()[]{}\"")
    lowered = cleaned.casefold()

    if not lowered:
        return "", None

    role_hint = None
    stem = lowered

    if "'" in lowered:
        base, suffix = lowered.rsplit("'", 1)
        if suffix in FROM_SUFFIXES:
            stem, role_hint = base, "from"
        elif suffix in TO_SUFFIXES_APOSTROPHE:
            stem, role_hint = base, "to"
        elif suffix in LOC_SUFFIXES:
            stem, role_hint = base, "loc"
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
            for suffix in LOC_SUFFIXES:
                # "-da/-de/-ta/-te" plain ek soyma kuralı çok agresif olursa
                # "Galata" gibi gerçek yer adlarını yanlış kırpar.
                # Bu yüzden daha uzun tokenlarda uygula.
                if lowered.endswith(suffix) and len(lowered) > len(suffix) + 4:
                    stem, role_hint = lowered[:-len(suffix)], "loc"
                    break

    stem = stem.strip(".,;:!?()[]{}\"'")
    stem = COMMON_ALIASES.get(stem, stem)
    return stem, role_hint


def extract_candidate_spans(query: str, max_ngram: int = 3) -> List[Dict[str, Any]]:
    """
    Sorgudan Türkçe ekleri soyulmuş, metin pozisyonu korunmuş aday span'ler çıkarır.
    """
    normalized_query = normalize_query_text(query)
    token_matches = []

    for match in TOKEN_PATTERN.finditer(normalized_query):
        surface = match.group(0)
        normalized, role_hint = normalize_token_with_role(surface)

        if len(normalized) < 2 or normalized in QUERY_NOISE_WORDS:
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
        use_osm: bool = False,
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
        self._use_osm = use_osm  # OSM API açık mı?
        self._prefer_osm_first = prefer_osm_first
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
        if place_name not in self._places:
            if embedding is None:
                # Embedding daha sonra hesaplanacak (lazy loading)
                self._places[place_name] = None
            else:
                self._places[place_name] = embedding
            self._place_names.append(place_name)
            self._place_name_to_index[place_name] = len(self._place_names) - 1
            normalized_key = normalize_place_key(place_name)
            if normalized_key and normalized_key not in self._normalized_place_lookup:
                self._normalized_place_lookup[normalized_key] = place_name
            folded_key = normalized_key.translate(_TR_FOLD_TABLE) if normalized_key else ""
            if folded_key and folded_key not in self._normalized_place_lookup:
                self._normalized_place_lookup[folded_key] = place_name
            self._embeddings = None  # Reset matrix

    def get_embedding_matrix(self, bert_engine) -> np.ndarray:
        """
        Tüm yer isimlerinin embedding matrisini döner.

        Lazy: İlk çağırmada hesaplar ve cache'ler.
        """
        if self._embeddings is not None:
            return self._embeddings

        # Tüm yer isimleri için embedding hesapla
        embeddings = bert_engine.encode_batch(self._place_names)
        self._embeddings = np.array(embeddings)

        # Cache'le
        for name, emb in zip(self._place_names, embeddings):
            self._places[name] = emb

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
            added = self.cache_osm_results(query)

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

            response = requests.get(
                self.OSM_API_URL,
                params=params,
                headers={"User-Agent": "OpenRoutePlanner/1.0"},
                timeout=5
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
        return self.cache_osm_results(query)

    def cache_osm_results(self, query: str, limit: int = 5) -> int:
        """
        OSM'den yer arar, sonuçları memory + local_places cache'e yazar.
        """
        if not self._use_osm:
            return 0

        normalized_query = (query or "").strip().lower()
        if len(normalized_query) < 2:
            return 0

        now = time.time()
        cache_entry = self._osm_query_cache.get(normalized_query)
        if cache_entry and cache_entry.get("expires_at", 0) > now:
            return int(cache_entry.get("added_count", 0))

        added_count = 0
        request_succeeded = False

        try:
            params = {
                "q": f"{query}, Turkey",
                "format": "json",
                "countrycodes": "tr",
                "limit": limit
            }

            response = requests.get(
                self.OSM_API_URL,
                params=params,
                headers={"User-Agent": "OpenRoutePlanner/1.0"},
                timeout=5
            )

            if response.status_code == 200:
                request_succeeded = True
                data = response.json()

                for item in data:
                    display_name = item.get("display_name", item.get("name", "")).strip()
                    short_name = display_name.split(",")[0].strip()
                    if not short_name:
                        continue

                    lat = item.get("lat")
                    lon = item.get("lon")
                    if lat is None or lon is None:
                        continue

                    if short_name not in self._places:
                        self.add_place(short_name)
                        added_count += 1

                    save_dynamic_place(
                        name=short_name,
                        display_name=display_name,
                        lat=float(lat),
                        lon=float(lon),
                        search_terms=f"{short_name.lower()} {display_name.lower()}",
                    )

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

    def _build_osm_prefetch_queries(self, query: str, max_queries: int = 6) -> List[str]:
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

    def prefetch_osm_candidates(self, query: str, bert_engine=None, max_queries: int = 6) -> int:
        """
        Tek parse akışında kontrollü sayıda OSM sorgusu yaparak aday havuzunu büyütür.
        """
        if not self._use_osm or not self._prefer_osm_first:
            return 0

        added_total = 0
        for candidate_query in self._build_osm_prefetch_queries(query, max_queries=max_queries):
            added_total += self.cache_osm_results(candidate_query, limit=5)

        if added_total > 0 and bert_engine is not None:
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
        use_osm = _env_flag("ORP_BERT_USE_OSM", True)
        prefer_osm_first = _env_flag("ORP_BERT_PREFER_OSM_FIRST", False)
        seed_dynamic_cache = _env_flag("ORP_BERT_SEED_DYNAMIC", use_osm)
        seed_local_places = _env_flag("ORP_BERT_SEED_LOCAL", True)
        seed_static_places = _env_flag("ORP_BERT_SEED_STATIC", True)
        seed_user_locations = _env_flag("ORP_BERT_SEED_USER_LOCATIONS", True)

        # Yer ismi veritabanı (OSM API desteği ile)
        self.places = PlaceDatabase(
            use_osm=use_osm,
            prefer_osm_first=prefer_osm_first,
            seed_dynamic_cache=seed_dynamic_cache,
            seed_local_places=seed_local_places,
            seed_static_places=seed_static_places,
            seed_user_locations=seed_user_locations,
        )

        # Yer isimleri için embedding matrix'i HESAPLA
        print("[BERT NLP] Yer isimleri için embedding hesaplanıyor...")
        self.places.get_embedding_matrix(self.bert)
        print(f"[BERT NLP] {len(self.places._place_names)} yer ismi indexlendi!")

        # Query template'leri için embedding cache
        self._template_embeddings = None

        print("[BERT NLP] Engine hazır!")

    def _get_template_embeddings(self) -> Dict[str, List[np.ndarray]]:
        """
        Query template'lerinin embedding'lerini döner.

        Lazy: İlk çağırmada hesaplar.
        """
        if self._template_embeddings is not None:
            return self._template_embeddings

        embeddings = {}
        for query_type, templates in QUERY_TEMPLATES.items():
            embeddings[query_type] = self.bert.encode_batch(templates)

        self._template_embeddings = embeddings
        return embeddings

    def classify_query_type_with_scores(self, query: str) -> Tuple[str, float, Dict[str, float]]:
        """
        Sorgunun tipini sınıflandırır.

        Args:
            query: Kullanıcı sorgusu

        Returns:
            (query_type, confidence, score_map)
        """
        query_embedding = self.bert.encode(query)
        template_embeddings = self._get_template_embeddings()

        best_type = "unknown"
        best_score = 0.0
        score_map: Dict[str, float] = {}

        # Her query type için ortalama similarity hesapla
        for query_type, template_embs in template_embeddings.items():
            scores = []
            for template_emb in template_embs:
                # Cosine similarity
                dot = np.dot(query_embedding, template_emb)
                norm = np.linalg.norm(query_embedding) * np.linalg.norm(template_emb)
                if norm > 0:
                    scores.append(dot / norm)

            # Ortalama similarity
            avg_score = np.mean(scores) if scores else 0.0
            score_map[query_type] = float(avg_score)

            if avg_score > best_score:
                best_score = avg_score
                best_type = query_type

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

        # OSM-first: Önce sorgudan canlı adaylar çekip aday havuzunu besle.
        self.places.prefetch_osm_candidates(query, bert_engine=self.bert, max_queries=6)

        for span in candidate_spans:
            span_embedding = self.bert.encode(span["normalized"])
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
            for item in ordered_places:
                if item["start"] > origin_item["start"] and item["place"] != origin:
                    destination_item = item
                    destination = item["place"]
                    break

        if destination_item and not origin:
            for item in ordered_places:
                if item["start"] < destination_item["start"] and item["place"] != destination:
                    origin_item = item
                    origin = item["place"]
                    break

        if not origin:
            origin = ordered_places[0]["place"]

        if not destination:
            for item in ordered_places[1:]:
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

        trace_data: Optional[Dict[str, Any]] = {} if include_trace else None

        # 1. Sorgu tipini sınıflandır
        query_type, type_confidence, type_scores = self.classify_query_type_with_scores(query)
        initial_query_type = query_type
        initial_type_confidence = float(type_confidence)

        # 2. Yer isimlerini çıkar
        detected_places = self.extract_places(query, trace=trace_data)
        ordered_places = sorted(
            detected_places,
            key=lambda item: (item.get("start", 0), -item.get("token_count", 1), -item.get("similarity", 0.0))
        )
        place_names = [p["place"] for p in ordered_places]
        role_hints = {p.get("role_hint") for p in ordered_places if p.get("role_hint")}
        normalized_query = normalize_place_key(query)
        query_tokens = set(normalized_query.split())
        has_poi_cue = bool(query_tokens & POI_CUE_WORDS)
        has_multi_cue = bool(query_tokens & MULTI_CUE_WORDS) or ("," in query)

        # Intent'i span tabanlı sinyallerle rafine et.
        if (
            len(place_names) >= 3
            and ("from" not in role_hints and "to" not in role_hints)
            and has_multi_cue
            and not has_poi_cue
        ):
            query_type = "multi"
            type_confidence = max(float(type_confidence), 0.78)
        elif query_type == "route" and has_poi_cue and ("from" not in role_hints and "to" not in role_hints):
            query_type = "poi"
            type_confidence = max(float(type_confidence), 0.75)
        if len(place_names) >= 2 and ("from" in role_hints):
            query_type = "route"
            type_confidence = max(float(type_confidence), 0.80)
        elif len(place_names) >= 2 and {"from", "to"}.issubset(role_hints):
            query_type = "route"
            type_confidence = max(float(type_confidence), 0.78)

        poi_concept = ""
        if query_type == "poi" or has_poi_cue:
            poi_concept = extract_poi_concept(query, ordered_places)

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
                "role_hints": sorted(role_hints),
                "detected_place_names": place_names,
                "poi_concept": poi_concept,
            }

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
            concept_key = normalize_place_key(poi_concept) if poi_concept else ""
            if concept_key and concept_key in NORMALIZED_POI_MAPPING:
                result["poi_tags_hint"] = dict(NORMALIZED_POI_MAPPING[concept_key])
            result["query_type"] = "search"
            if not result["location"]:
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

            if len(strong_single_places) >= 2:
                result["locations"] = strong_single_places
            else:
                result["locations"] = place_names if len(place_names) >= 2 else place_names

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
            if len(place_names) >= 3:
                result["type"] = "multi"
                result["locations"] = place_names
            elif len(place_names) == 2:
                strong_match = all(p.get("similarity", 0.0) >= 0.78 for p in ordered_places[:2])
                has_direction_hint = bool({"from", "to"} & role_hints)
                if strong_match or has_direction_hint:
                    result["type"] = "route"
                    direction = self.detect_route_direction(query, ordered_places)
                    result["origin"] = direction["origin"] or place_names[0]
                    result["destination"] = direction["destination"] or place_names[1]
                else:
                    result["error"] = "Sorgu anlaşılamadı"
            elif len(place_names) == 1:
                single_candidate = ordered_places[0]
                if single_candidate.get("similarity", 0.0) >= 0.82 and single_candidate.get("role_hint") == "to":
                    result["type"] = "single"
                    result["destination"] = place_names[0]
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
                "poi_tags_hint": result.get("poi_tags_hint"),
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
