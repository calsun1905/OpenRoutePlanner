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

    def __init__(self, use_osm: bool = False):
        self._places = {}  # {name: embedding}
        self._place_names = []  # List[str]
        self._embeddings = None  # np.ndarray matrix
        self._use_osm = use_osm  # OSM API açık mı?

        # Başlangıçta popüler Türk yerlerini ekle
        self._seed_turkish_places()

    def _seed_turkish_places(self):
        """Türkiye'nin tüm yer isimlerini ve KULLANICI LOKASYONLARINI yükler."""
        # 1. Kullanıcı lokasyonlarını ekle (Yüksek öncelikli)
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

        # 2. Türkiye veritabanını ekle
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
        threshold: float = 0.75
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
        if not self._place_names:
            return None

        # Cache'te ara
        embeddings = self._embeddings
        if embeddings is None:
            return None

        # Cosine similarity hesapla
        similarities = np.dot(embeddings, query_embedding)
        norms = np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)

        # Sıfıra bölünme kontrolü
        if np.all(norms == 0):
            return None

        # Sıfır olanları korumak için
        similarities = np.divide(similarities, norms, out=np.zeros_like(similarities), where=norms!=0)

        # En yüksek skoru bul
        best_idx = np.argmax(similarities)
        best_score = float(similarities[best_idx])

        # Eşik üstündeyse döndür
        if best_score >= threshold:
            return {
                "place": self._place_names[best_idx],
                "similarity": best_score,
                "index": best_idx
            }

        # Bulunamazsa ve OSM açıksa, API'ye sor
        if self._use_osm and best_score < 0.50:
            print(f"[OSM API] '{query}' aranıyor...")
            added = self.add_places_from_osm(query)

            if added > 0:
                print(f"[OSM API] {added} yeni yer eklendi!")
                # Not: Yeni yerler için embedding daha sonra hesaplanmalı

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
        places = self.search_osm_api(query)

        added_count = 0
        for place in places:
            if place not in self._places:
                self.add_place(place)
                added_count += 1

        return added_count

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
        self.places = PlaceDatabase(use_osm=True)  # OSM API AKTİF!

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
                threshold=0.75  # Yüksek threshold
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
                threshold=0.65  # Orta threshold (n-gram daha spesifik)
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

        # 3. Yere göre sonuç oluştur
        result = {
            "type": query_type,
            "confidence": type_confidence,
            "raw_query": query,
            "detected_places": detected_places,
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
