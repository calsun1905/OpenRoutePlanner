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
from typing import List, Optional, Dict, Any
import numpy as np


# =============================================================================
# GLOBAL CACHE (Model tek seferde yüklenir)
# =============================================================================

_bert_model = None
_tokenizer = None


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

            # GPU varsa kullan, yoksa CPU
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
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

    def encode(self, text: str) -> np.ndarray:
        """
        Metni BERT embedding'ine çevirir.

        Args:
            text: Embedding'e çevrilecek metin

        Returns:
            np.ndarray: 768 boyutlu embedding vektörü
        """
        import torch

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

        # [CLS] token'ın embedding'ini al (sentence representation)
        # outputs.last_hidden_state: [batch_size, seq_len, hidden_size]
        cls_embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()

        return cls_embedding[0]  # (768,) vektörü

    def encode_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Birden fazla metni embedding'e çevirir.

        Args:
            texts: Metin listesi

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

            cls_embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
            all_embeddings.extend(cls_embeddings)

        return all_embeddings

    def similarity(self, text1: str, text2: str) -> float:
        """
        İki metin arasındaki cosine similarity'yi hesaplar.

        Args:
            text1: İlk metin
            text2: İkinci metin

        Returns:
            float: 0-1 arası benzerlik skoru (1 = tam aynı)
        """
        emb1 = self.encode(text1)
        emb2 = self.encode(text2)

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
        threshold: float = 0.75
    ) -> Optional[Dict[str, Any]]:
        """
        Sorguya en yakın adayı bulur.

        Args:
            query: Arama sorgusu
            candidates: Aday metin listesi
            threshold: Minimum benzerik eşiği

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

        query_emb = self.encode(query)

        best_match = None
        best_score = 0.0
        best_idx = -1

        for i, candidate in enumerate(candidates):
            candidate_emb = self.encode(candidate)

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
                "similarity": best_score,
                "index": best_idx
            }

        return None


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

        print("\n" + "=" * 60)
        print("[TAMAMLANDI] Test basariyla tamamlandi!")

    except Exception as e:
        print(f"[HATA] {e}")


if __name__ == "__main__":
    test_bert_engine()
