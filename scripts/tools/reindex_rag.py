#!/usr/bin/env python3
"""
reindex_rag.py - JSONL dosyasindan ChromaDB RAG indeksini sifirdan olusturur.

Kullanim:
    cd OpenRoutePlanner
    python scripts/tools/reindex_rag.py
    python scripts/tools/reindex_rag.py --jsonl path/to/file.jsonl
    python scripts/tools/reindex_rag.py --collection my_collection
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _default_jsonl() -> str:
    return os.path.join(_repo_root(), "backend", "data", "rag_retrieval_ready.jsonl")


def _default_db_path() -> str:
    env = (os.getenv("ORP_RAG_DB_PATH", "") or "").strip()
    if env:
        return env
    return os.path.join(_repo_root(), "chroma_db")


def _default_collection() -> str:
    return (os.getenv("ORP_RAG_COLLECTION", "istanbul_rag_core").strip()
            or "istanbul_rag_core")


def _default_embed_model() -> str:
    return (os.getenv("ORP_RAG_EMBED_MODEL", "BAAI/bge-m3").strip()
            or "BAAI/bge-m3")


# ---------------------------------------------------------------------------
# JSONL okuyucu
# ---------------------------------------------------------------------------

def read_jsonl(path: str) -> list[dict]:
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"  [WARN] Satir {lineno} JSON parse hatasi: {exc}")
                continue
            rows.append(obj)
    return rows


# ---------------------------------------------------------------------------
# Ana islem
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="JSONL'den ChromaDB RAG indeksini sifirdan olusturur."
    )
    parser.add_argument(
        "--jsonl", default=_default_jsonl(),
        help="Kaynak JSONL dosyasi (varsayilan: rag_retrieval_ready.jsonl)",
    )
    parser.add_argument(
        "--db-path", default=_default_db_path(),
        help="ChromaDB dizin yolu",
    )
    parser.add_argument(
        "--collection", default=_default_collection(),
        help="ChromaDB koleksiyon adi",
    )
    parser.add_argument(
        "--embed-model", default=_default_embed_model(),
        help="Embedding modeli (sentence-transformers uyumlu)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=32,
        help="Embedding batch boyutu",
    )
    args = parser.parse_args()

    jsonl_path = os.path.abspath(args.jsonl)
    db_path = os.path.abspath(args.db_path)
    coll_name = args.collection
    embed_model_name = args.embed_model
    batch_size = max(1, args.batch_size)

    print("=" * 60)
    print("RAG Reindex - rag_retrieval_ready.jsonl -> ChromaDB")
    print("=" * 60)
    print(f"  JSONL       : {jsonl_path}")
    print(f"  DB path     : {db_path}")
    print(f"  Collection  : {coll_name}")
    print(f"  Embed model : {embed_model_name}")
    print(f"  Batch size  : {batch_size}")
    print()

    # ----- 1. JSONL oku -----
    if not os.path.isfile(jsonl_path):
        print(f"HATA: JSONL dosyasi bulunamadi: {jsonl_path}")
        sys.exit(1)

    print("[1/4] JSONL dosyasi okunuyor...")
    rows = read_jsonl(jsonl_path)
    print(f"       {len(rows)} kayit okundu.")
    if not rows:
        print("HATA: JSONL dosyasinda kayit bulunamadi.")
        sys.exit(1)

    # ----- 2. Embedding modeli yukle -----
    print(f"[2/4] Embedding modeli yukleniyor: {embed_model_name}")
    t0 = time.time()
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("HATA: sentence-transformers kurulu degil. pip install sentence-transformers")
        sys.exit(1)

    embedder = SentenceTransformer(embed_model_name)
    print(f"       Model yuklendi ({time.time() - t0:.1f}s)")

    # ----- 3. Embedding'leri hesapla -----
    print("[3/4] Embedding'ler hesaplaniyor...")
    t0 = time.time()

    # Her satirdan embedding_text alanini al, yoksa text alanini kullan
    texts: list[str] = []
    for row in rows:
        emb_text = str(row.get("embedding_text") or row.get("text") or "").strip()
        if not emb_text:
            emb_text = str(row.get("ad", "")).strip()
        texts.append(emb_text)

    embeddings = embedder.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=batch_size,
    ).tolist()

    print(f"       {len(embeddings)} embedding hesaplandi ({time.time() - t0:.1f}s)")

    # ----- 4. ChromaDB'ye yaz -----
    print(f"[4/4] ChromaDB'ye yaziliyor: {coll_name}")
    t0 = time.time()

    try:
        import chromadb
    except ImportError:
        print("HATA: chromadb kurulu degil. pip install chromadb")
        sys.exit(1)

    os.makedirs(db_path, exist_ok=True)
    client = chromadb.PersistentClient(path=db_path)

    # Eski koleksiyonu sil ve yenisini olustur
    try:
        client.delete_collection(coll_name)
        print(f"       Eski '{coll_name}' koleksiyonu silindi.")
    except Exception:
        print(f"       Eski '{coll_name}' koleksiyonu bulunamadi (yeni olusturulacak).")

    collection = client.create_collection(
        name=coll_name,
        metadata={"hnsw:space": "cosine"},
    )

    # Batch halinde ekle
    total = len(rows)
    added = 0
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch_rows = rows[start:end]
        batch_embeddings = embeddings[start:end]

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []

        for i, row in enumerate(batch_rows):
            chunk_id = str(row.get("chunk_id", f"chunk_{start + i}")).strip()
            ids.append(chunk_id)

            # Document olarak ana text alani
            doc_text = str(row.get("text") or "").strip()
            documents.append(doc_text)

            # Zengin metadata
            meta: dict = {}
            for key in (
                "ad", "chunk_kind", "entity_id", "freshness", "confidence",
            ):
                val = row.get(key)
                if val is not None:
                    meta[key] = str(val).strip()

            # Liste alanlari virgullu string'e cevir (ChromaDB dict value olarak
            # sadece str/int/float/bool destekler)
            for list_key in (
                "aliases", "kategoriler", "semtler", "hat_kodlari",
                "operatorler", "source_urls", "record_types",
            ):
                val = row.get(list_key)
                if isinstance(val, list) and val:
                    meta[list_key] = ", ".join(str(v) for v in val)

            # source_url (ilk url'yi ayri tut - eski uyumluluk)
            urls = row.get("source_urls")
            if isinstance(urls, list) and urls:
                meta["source_url"] = str(urls[0])

            # record_type (ilk tipi ayri tut - eski uyumluluk)
            rtypes = row.get("record_types")
            if isinstance(rtypes, list) and rtypes:
                meta["record_type"] = str(rtypes[0])

            metadatas.append(meta)

        collection.add(
            ids=ids,
            documents=documents,
            embeddings=batch_embeddings,
            metadatas=metadatas,
        )
        added += len(batch_rows)
        pct = (added / total) * 100
        print(f"       [{added}/{total}] ({pct:.0f}%)", end="\r")

    print()
    print(f"       {added} kayit ChromaDB'ye yazildi ({time.time() - t0:.1f}s)")

    # ----- Dogrulama -----
    count = collection.count()
    print()
    print("=" * 60)
    print(f"TAMAMLANDI! Koleksiyon '{coll_name}' -> {count} dokuman")
    print("=" * 60)

    # Hizli dogrulama: M5 aramas?
    print()
    print("--- Hizli Dogrulama: 'M5 duraklar?' aramas? ---")
    q_emb = embedder.encode(["M5 metro duraklar? nelerdir"], normalize_embeddings=True).tolist()
    result = collection.query(query_embeddings=q_emb, n_results=3)
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    for idx, doc in enumerate(docs):
        ad = metas[idx].get("ad", "-") if idx < len(metas) else "-"
        hat = metas[idx].get("hat_kodlari", "-") if idx < len(metas) else "-"
        print(f"  [{idx+1}] ad={ad} | hat={hat}")
        print(f"      {doc[:150]}...")
    print()
    print("Reindex islemi basariyla tamamlandi!")


if __name__ == "__main__":
    main()
