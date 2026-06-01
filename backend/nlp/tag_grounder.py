"""
tag_grounder.py - Dinamik OSM Tag Grounding

Kullanıcının POI sorgusundaki konsepti (ör. "cami", "hamburgerci", "stadyum")
lokasyondaki GERÇEK OSM tag dağılımıyla eşleştirir.

Algoritma:
  1. Overpass API ile bölgedeki POI'lerin tag'lerini çek
  2. Her tag key=value grubu için metin temsili oluştur
     (ör. "amenity place_of_worship: Cami Fatih, Büyük Cami, ...")
  3. Konsept + tag temsillerini BERT ile embedding'e çevir
  4. Cosine similarity × frekans ağırlığı ile sırala
  5. En iyi eşleşen OSM tag filtresini döndür

Hiçbir hardcoded kelime listesi / sözlük gerektirmez.
"""

import math
import time
import threading
from typing import List, Dict, Optional, Tuple, Any

import requests

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
CACHE_TTL_SECONDS = 30 * 60          # 30 dakika area cache
REQUEST_TIMEOUT = 25                  # Overpass max bekleme süresi (sn)
MAX_ELEMENTS = 2000                   # Overpass yanıtından maksimum eleman
MAX_PROFILES = 60                     # Kaç farklı tag tipi saklansın
MIN_EMBEDDING_SIMILARITY = 0.50      # Bu altı sonuç döndürme

# Anlamlı POI kategorik tag anahtarları (meta / adres tag'leri değil)
_POI_TAG_KEYS = frozenset({
    "amenity", "shop", "tourism", "leisure", "sport", "historic",
    "office", "craft", "healthcare", "religion", "natural",
    "club", "emergency", "landuse",
})

# Bu key'lerin genel (bilgi içermeyen) değerleri → atla
_GENERIC_VALUES = frozenset({"yes", "no", "1", "0", "true", "false", "building"})


# ---------------------------------------------------------------------------
# TagProfile: Tek bir OSM tag grubu
# ---------------------------------------------------------------------------

class TagProfile:
    """Bir tag key=value için profil (count + örnek isimler + embedding)."""

    __slots__ = (
        "tag_key", "tag_value", "osm_filter",
        "count", "example_names", "representation",
        "embedding", "idf_weight",
    )

    def __init__(self, tag_key: str, tag_value: str, count: int, example_names: List[str]):
        self.tag_key = tag_key
        self.tag_value = tag_value
        self.osm_filter: Dict[str, str] = {tag_key: tag_value}
        self.count = count
        self.example_names: List[str] = example_names[:15]

        # Metin temsili: "amenity place of worship: Fatih Camii, Büyük Cami ..."
        readable_value = tag_value.replace("_", " ")
        names_text = " ".join(self.example_names[:8])
        self.representation = f"{tag_key} {readable_value} {names_text}".strip()

        self.embedding = None  # TagGrounder._compute_embeddings() tarafından doldurulur

        # IDF benzeri ağırlık: 1-200 arası frekans için log normalleşme
        # Çok nadir (count=1) veya çok yaygın (count>500) eşit derecede baskılanır
        clamped = max(1, min(self.count, 200))
        self.idf_weight: float = math.log(1 + clamped) / math.log(201)


# ---------------------------------------------------------------------------
# TagGrounder
# ---------------------------------------------------------------------------

class TagGrounder:
    """
    Dinamik OSM Tag Grounding engine.

    Kullanım:
        grounder = TagGrounder(bert_engine_instance)
        results = grounder.ground("cami", lat=40.99, lon=29.03)
        # → [{"tags": {"amenity": "place_of_worship"}, "score": 0.91, ...}, ...]
    """

    def __init__(self, bert_engine):
        """
        Args:
            bert_engine: BERTEngine instance'ı (encode / encode_batch metotları olmalı)
        """
        self._bert = bert_engine
        # {cache_key: (timestamp, List[TagProfile])}
        self._area_cache: Dict[str, Tuple[float, List[TagProfile]]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ground(
        self,
        concept: str,
        lat: float,
        lon: float,
        radius: int = 3000,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Konsepti bölgedeki OSM tag'lerine eşleştirir.

        Args:
            concept : "cami", "hamburgerci", "stadyum" vb. (Türkçe serbest metin)
            lat, lon: Merkez koordinat
            radius  : Arama yarıçapı (metre), default 3000
            top_k   : Döndürülecek en yüksek skorlu sonuç sayısı

        Returns:
            [
                {
                    "tags"      : {"amenity": "place_of_worship"},
                    "score"     : 0.91,        # idf-ağırlıklı skor
                    "similarity": 0.94,        # ham cosine benzerliği
                    "count"     : 47,          # bölgedeki bu tag'li POI sayısı
                    "examples"  : ["Fatih Camii", "Merkez Cami", ...],
                    "label"     : "amenity=place_of_worship",
                },
                ...
            ]
        """
        concept = concept.strip()
        if not concept:
            return []

        profiles = self._get_area_profiles(lat, lon, radius)
        if not profiles:
            return []

        # Concept embedding (tek metin, hızlı)
        try:
            concept_emb = self._bert.encode(concept)
        except Exception as e:
            print(f"[TagGrounder] Concept embedding hatası: {e}")
            return []

        # Her profille benzerlik
        scored: List[Dict[str, Any]] = []
        for profile in profiles:
            if profile.embedding is None:
                continue
            sim = float(self._cosine_sim(concept_emb, profile.embedding))
            score = sim * profile.idf_weight
            scored.append({
                "tags"      : profile.osm_filter,
                "score"     : round(score, 4),
                "similarity": round(sim, 4),
                "count"     : profile.count,
                "examples"  : profile.example_names[:5],
                "label"     : f"{profile.tag_key}={profile.tag_value}",
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        # Minimum benzerlik filtresi
        results = [r for r in scored if r["similarity"] >= MIN_EMBEDDING_SIMILARITY][:top_k]
        return results

    # ------------------------------------------------------------------
    # Dahili: Cache & Profil yönetimi
    # ------------------------------------------------------------------

    def _get_area_profiles(self, lat: float, lon: float, radius: int) -> List[TagProfile]:
        """Cache'den veya Overpass'tan area profilleri döndürür."""
        # 2 ondalık koordinat ≈ ~1.1 km hassasiyet (cache granülaritesi için yeterli)
        cache_key = f"{lat:.2f}_{lon:.2f}_{radius}"

        with self._lock:
            if cache_key in self._area_cache:
                ts, profiles = self._area_cache[cache_key]
                if time.time() - ts < CACHE_TTL_SECONDS:
                    return profiles

        # Cache miss → Overpass
        try:
            elements = self._fetch_overpass(lat, lon, radius)
        except Exception as e:
            print(f"[TagGrounder] Overpass hatası: {e}")
            return []

        if not elements:
            return []

        profiles = self._build_profiles(elements)
        self._compute_embeddings(profiles)

        with self._lock:
            self._area_cache[cache_key] = (time.time(), profiles)

        return profiles

    def _fetch_overpass(self, lat: float, lon: float, radius: int) -> List[Dict]:
        """Overpass API'den bölgedeki POI elementlerini çeker."""
        key_filter = "|".join(sorted(_POI_TAG_KEYS))
        query = f"""[out:json][timeout:{REQUEST_TIMEOUT}];
(
  node(around:{radius},{lat},{lon})[~"^({key_filter})$"~"."];
  way(around:{radius},{lat},{lon})[~"^({key_filter})$"~"."];
  relation(around:{radius},{lat},{lon})[~"^({key_filter})$"~"."];
);
out tags center {MAX_ELEMENTS};"""

        resp = requests.post(
            OVERPASS_URL,
            data={"data": query},
            timeout=REQUEST_TIMEOUT + 5,
            headers={"User-Agent": "OpenRoutePlanner/1.0 (tag-grounding)"},
        )
        resp.raise_for_status()
        return resp.json().get("elements", [])

    def _build_profiles(self, elements: List[Dict]) -> List[TagProfile]:
        """Element listesinden TagProfile listesi oluşturur."""
        from collections import defaultdict

        # group_key → {"count": int, "names": List[str]}
        groups: Dict[str, Dict] = defaultdict(lambda: {"count": 0, "names": []})

        for elem in elements:
            tags = elem.get("tags", {})
            name = tags.get("name") or tags.get("name:tr") or tags.get("name:en")

            for key in _POI_TAG_KEYS:
                value = tags.get(key)
                if not value or value in _GENERIC_VALUES:
                    continue

                gk = f"{key}={value}"
                groups[gk]["count"] += 1
                if name and isinstance(name, str) and len(groups[gk]["names"]) < 20:
                    if name not in groups[gk]["names"]:
                        groups[gk]["names"].append(name)

        profiles = []
        for gk, data in groups.items():
            if data["count"] < 1:
                continue
            key, value = gk.split("=", 1)
            profiles.append(TagProfile(
                tag_key=key,
                tag_value=value,
                count=data["count"],
                example_names=data["names"],
            ))

        # Frekansa göre sırala, en fazla MAX_PROFILES tane tut
        profiles.sort(key=lambda p: p.count, reverse=True)
        return profiles[:MAX_PROFILES]

    def _compute_embeddings(self, profiles: List[TagProfile]) -> None:
        """Tüm tag profilleri için toplu embedding hesaplar."""
        texts = [p.representation for p in profiles]
        if not texts:
            return
        try:
            embeddings = self._bert.encode_batch(texts)
            for profile, emb in zip(profiles, embeddings):
                profile.embedding = emb
        except Exception as e:
            print(f"[TagGrounder] Batch embedding hatası: {e}")

    # ------------------------------------------------------------------
    # Yardımcı
    # ------------------------------------------------------------------

    @staticmethod
    def _cosine_sim(a, b) -> float:
        import numpy as np
        a = np.asarray(a, dtype=np.float32)
        b = np.asarray(b, dtype=np.float32)
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        if denom < 1e-9:
            return 0.0
        return float(np.dot(a, b) / denom)


# ---------------------------------------------------------------------------
# Singleton yönetimi (app başlatıldığında tek instance)
# ---------------------------------------------------------------------------

_grounder_instance: Optional[TagGrounder] = None
_grounder_lock = threading.Lock()


def get_tag_grounder(bert_engine=None) -> Optional[TagGrounder]:
    """
    Singleton TagGrounder döndürür.
    İlk çağrıda bert_engine gereklidir.
    """
    global _grounder_instance
    with _grounder_lock:
        if _grounder_instance is None:
            if bert_engine is None:
                return None
            _grounder_instance = TagGrounder(bert_engine)
        return _grounder_instance
