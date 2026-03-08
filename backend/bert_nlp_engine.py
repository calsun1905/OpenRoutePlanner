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

import re
import time
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
    from local_places import save_dynamic_place, get_dynamic_place_names
except ImportError:
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        from local_places import save_dynamic_place, get_dynamic_place_names
    except ImportError:
        def save_dynamic_place(*args, **kwargs): return None
        def get_dynamic_place_names(limit=500): return []



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
    "yer", "nokta", "için", "yakında", "yakın", "istiyorum"
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
                if lowered.endswith(suffix) and len(lowered) > len(suffix) + 2:
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
        seed_static_places: bool = True,
        seed_user_locations: bool = True,
    ):
        self._places = {}  # {name: embedding}
        self._place_names = []  # List[str]
        self._embeddings = None  # np.ndarray matrix
        self._use_osm = use_osm  # OSM API açık mı?
        self._prefer_osm_first = prefer_osm_first
        self._osm_query_cache = {}

        self._seed_dynamic_cache()

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

    def find_best_match(
        self,
        query: str,
        query_embedding: np.ndarray,
        threshold: float = 0.75,
        bert_engine = None
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
                "index": best_idx
            }

        embeddings = self._embeddings
        if embeddings is None and bert_engine is not None:
            embeddings = self.get_embedding_matrix(bert_engine)

        best_match = score_embeddings(embeddings) if embeddings is not None else None
        if best_match and best_match["similarity"] >= threshold:
            return best_match

        # OSM-first modunda OSM adayları önce beslenmiş olur; burada ise son fallback çalışır.
        if self._use_osm and (best_match is None or best_match["similarity"] < 0.50):
            print(f"[OSM API] '{query}' aranıyor...")
            added = self.cache_osm_results(query)

            if added > 0:
                print(f"[OSM API] {added} yeni yer eklendi!")
                if bert_engine is not None:
                    refreshed_embeddings = self.get_embedding_matrix(bert_engine)
                    refreshed_match = score_embeddings(refreshed_embeddings)
                    if refreshed_match and refreshed_match["similarity"] >= threshold:
                        return refreshed_match

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

        if normalized_query in self._osm_query_cache:
            return self._osm_query_cache[normalized_query]

        added_count = 0

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

        except Exception as e:
            print(f"[OSM API] Hata: {e}")

        self._osm_query_cache[normalized_query] = added_count
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

        # Yer ismi veritabanı (OSM API desteği ile)
        self.places = PlaceDatabase(
            use_osm=True,
            prefer_osm_first=True,
            seed_static_places=False,
            seed_user_locations=True,
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

    def classify_query_type(self, query: str) -> Tuple[str, float]:
        """
        Sorgunun tipini sınıflandırır.

        Args:
            query: Kullanıcı sorgusu

        Returns:
            (query_type, confidence): "route", "poi", "multi", "single", "unknown"
        """
        query_embedding = self.bert.encode(query)
        template_embeddings = self._get_template_embeddings()

        best_type = "unknown"
        best_score = 0.0

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

            if avg_score > best_score:
                best_score = avg_score
                best_type = query_type

        # Threshold altındaysa unknown
        if best_score < 0.5:
            return "unknown", best_score

        return best_type, best_score

    def extract_places(self, query: str) -> List[Dict[str, Any]]:
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
        found_places = []
        seen_places = set()

        # OSM-first: Önce sorgudan canlı adaylar çekip aday havuzunu besle.
        self.places.prefetch_osm_candidates(query, bert_engine=self.bert, max_queries=6)

        # 1. KELİME SEViYE: Tek kelimeler için yüksek threshold
        words = re.findall(r'\b[\wğüşıöçĞÜŞİÖÇ]+\b', query)

        for word in words:
            if len(word) < 3:
                continue

            word_embedding = self.bert.encode(word)

            # Yüksek threshold - sadece kesin eşleşmeler
            match = self.places.find_best_match(
                query=word,
                query_embedding=word_embedding,
                threshold=0.75,  # Yüksek threshold
                bert_engine=self.bert
            )

            if match and match["place"] not in seen_places:
                found_places.append(match)
                seen_places.add(match["place"])

        # 2. N-GRAM SEViYE: 2-3 kelime grupları (daha spesifik)
        # Örnek: "Kadıköy'den", "Taksim Meydanı"
        ngrams = []

        # 2-gramler (komşu kelime çiftleri)
        for i in range(len(words) - 1):
            ngram = f"{words[i]} {words[i+1]}"
            if len(ngram) >= 5:  # En az 5 karakter
                ngrams.append(ngram)

        # 3-gramler
        for i in range(len(words) - 2):
            ngram = f"{words[i]} {words[i+1]} {words[i+2]}"
            if len(ngram) >= 7:
                ngrams.append(ngram)

        # N-gramleri dene (daha düşük threshold ile)
        for ngram in ngrams:
            ngram_embedding = self.bert.encode(ngram)

            match = self.places.find_best_match(
                query=ngram,
                query_embedding=ngram_embedding,
                threshold=0.65,  # Orta threshold (n-gram daha spesifik)
                bert_engine=self.bert
            )

            if match and match["place"] not in seen_places:
                # N-gram bulduysa, skorunu biraz artır (daha güvenilir)
                match["similarity"] = min(match["similarity"] * 1.05, 1.0)
                found_places.append(match)
                seen_places.add(match["place"])

        # 3. FiLTERiNG: Çok fazla sonuç varsa, en iyilerini al
        if len(found_places) > 5:
            # Skorlara göre sırala ve sadece en iyi 5'i al
            found_places.sort(key=lambda x: x["similarity"], reverse=True)

            # Ayrıca düşük skoru olanları at (0.70 altı)
            found_places = [p for p in found_places if p["similarity"] >= 0.70][:5]

        # Final sort
        found_places.sort(key=lambda x: x["similarity"], reverse=True)

        return found_places

    def detect_route_direction(self, query: str, places: List[str]) -> Dict[str, Optional[str]]:
        """
        "X'den Y'ye" tarzı sorgularda yönü tespit eder.

        Args:
            query: Kullanıcı sorgusu
            places: Bulunan yer isimleri

        Returns:
            {"origin": str | None, "destination": str | None}
        """
        if len(places) < 2:
            return {"origin": None, "destination": None}

        # "dan/den/ten/tan" edatlarını ara
        from_patterns = [
            r'(\w+)(?:den|dan|ten|tan)',
            r'(\w+)\s+van\b',
        ]

        # "ye/e/a/ya" edatlarını ara
        to_patterns = [
            r'(?:ye|a|e|ya|na)\s*.*?(\w+)$',
            r'(?:ye|a|e|ya|na)\s+(\w+)',
        ]

        origin = None
        destination = None

        # Origin ara
        for pattern in from_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                candidate = match.group(1)
                # Yer ismi ile eşleştir
                for place in places:
                    if candidate.lower() in place.lower() or place.lower() in candidate.lower():
                        origin = place
                        break
                if origin:
                    break

        # Destination ara
        for pattern in to_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                candidate = match.group(1)
                for place in places:
                    if place != origin:  # Origin ile aynı olmasın
                        if candidate.lower() in place.lower() or place.lower() in candidate.lower():
                            destination = place
                            break
                if destination:
                    break

        # Bulunamazsa ilk ikisini origin/destination yap
        if not origin and len(places) >= 2:
            origin = places[0]
            destination = places[1]
        elif not destination and len(places) >= 2:
            destination = places[1] if places[1] != origin else places[0]

        return {"origin": origin, "destination": destination}

    def parse(self, query: str) -> Dict[str, Any]:
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

        # 1. Sorgu tipini sınıflandır
        query_type, type_confidence = self.classify_query_type(query)

        # 2. Yer isimlerini çıkar
        detected_places = self.extract_places(query)
        place_names = [p["place"] for p in detected_places]

        # 3. Numpy değerlerini Python native türlere çevir (JSON için)
        detected_places_json = [
            {
                "place": p["place"],
                "similarity": float(p["similarity"]),  # numpy.float32 -> float
                "index": int(p["index"]) if "index" in p else None
            }
            for p in detected_places
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
            direction = self.detect_route_direction(query, place_names)
            result["origin"] = direction["origin"]
            result["destination"] = direction["destination"]

            # Eğer direction bulunamazsa place_names kullan
            if not result["origin"] and len(place_names) >= 2:
                result["origin"] = place_names[0]
                result["destination"] = place_names[1]

        elif query_type == "poi":
            # İlk yer ismi location olarak kullan
            result["location"] = place_names[0] if place_names else None
            result["query_type"] = "search"

        elif query_type == "multi":
            # Tüm yer isimlerini locations'a ekle
            result["locations"] = place_names if len(place_names) >= 2 else place_names

        elif query_type == "single":
            # Tek hedef
            result["destination"] = place_names[0] if place_names else None

        elif query_type == "unknown":
            # Bilinmeyen tip - yer isimlerine göre karar ver
            if len(place_names) >= 3:
                result["type"] = "multi"
                result["locations"] = place_names
            elif len(place_names) == 2:
                result["type"] = "route"
                result["origin"] = place_names[0]
                result["destination"] = place_names[1]
            elif len(place_names) == 1:
                result["type"] = "single"
                result["destination"] = place_names[0]
            else:
                result["error"] = "Sorgu anlaşılamadı"

        # Parse süresi
        result["parse_time"] = time.time() - start_time

        return result


# =============================================================================
# SINGLETON
# =============================================================================

_bert_nlp_engine = None

def get_bert_nlp_engine() -> BertNLPEngine:
    """
    Global BERT NLP engine singleton'ını döner.
    """
    global _bert_nlp_engine

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
