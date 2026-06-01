"""
RAG servis yardimcilari (ChromaDB + sentence-transformers).

Bu modul, yerel Chroma index'ten ilgili baglami cekip LLM prompt'una
eklemek icin tek noktadan kullanilir.
"""

from __future__ import annotations

import os
import threading
from typing import Any

try:
    import chromadb
except Exception:  # pragma: no cover
    chromadb = None  # type: ignore[assignment]

_SENTENCE_TRANSFORMER_CLS = None


_LOCK = threading.Lock()
_CLIENT = None
_EMBEDDER = None


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return default


def _enabled() -> bool:
    return _env_flag("ORP_RAG_ENABLED", True)


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _db_path() -> str:
    raw = (os.getenv("ORP_RAG_DB_PATH", "").strip() or "")
    if raw:
        return raw
    return os.path.join(_repo_root(), "chroma_db")


def _collection_name() -> str:
    return (os.getenv("ORP_RAG_COLLECTION", "istanbul_rag_core").strip()
            or "istanbul_rag_core")


def _embed_model_name() -> str:
    return (os.getenv("ORP_RAG_EMBED_MODEL", "BAAI/bge-m3").strip()
            or "BAAI/bge-m3")


def _top_k_default() -> int:
    return max(1, _env_int("ORP_RAG_TOP_K_DEFAULT", 5))


def _max_context_chars() -> int:
    return max(500, _env_int("ORP_RAG_MAX_CONTEXT_CHARS", 4000))


def is_rag_available() -> bool:
    # sentence-transformers/torch importu agir olabilir; startup'ta zorlamiyoruz.
    return _enabled() and chromadb is not None


def rag_status() -> dict[str, Any]:
    return {
        "enabled": _enabled(),
        "available": is_rag_available(),
        "db_path": _db_path(),
        "collection": _collection_name(),
        "embed_model": _embed_model_name(),
        "top_k_default": _top_k_default(),
        "max_context_chars": _max_context_chars(),
    }


def _get_client():
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    if chromadb is None:
        raise RuntimeError("chromadb kurulumu eksik")
    with _LOCK:
        if _CLIENT is None:
            _CLIENT = chromadb.PersistentClient(path=_db_path())
    return _CLIENT


def _get_embedder():
    global _SENTENCE_TRANSFORMER_CLS
    global _EMBEDDER
    if _EMBEDDER is not None:
        return _EMBEDDER
    if _SENTENCE_TRANSFORMER_CLS is None:
        try:
            from sentence_transformers import SentenceTransformer as _SentenceTransformer
            _SENTENCE_TRANSFORMER_CLS = _SentenceTransformer
        except Exception as exc:
            raise RuntimeError(f"sentence-transformers/torch import hatasi: {exc}") from exc
    with _LOCK:
        if _EMBEDDER is None:
            _EMBEDDER = _SENTENCE_TRANSFORMER_CLS(_embed_model_name())
    return _EMBEDDER


def rag_list_collections() -> list[str]:
    client = _get_client()
    out: list[str] = []
    for item in client.list_collections() or []:
        name = str(getattr(item, "name", "") or "").strip()
        if name:
            out.append(name)
    out.sort()
    return out


def rag_query(question: str, *, top_k: int | None = None, collection: str | None = None) -> dict[str, Any]:
    if not is_rag_available():
        raise RuntimeError("RAG aktif degil veya bagimliliklar eksik")

    user_q = str(question or "").strip()
    if not user_q:
        raise ValueError("Soru bos olamaz")

    coll_name = str(collection or "").strip() or _collection_name()
    k = max(1, int(top_k or _top_k_default()))

    client = _get_client()
    col = client.get_collection(coll_name)
    embedder = _get_embedder()

    q_emb = embedder.encode([user_q], normalize_embeddings=True).tolist()
    res = col.query(query_embeddings=q_emb, n_results=k)

    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]

    chunks: list[dict[str, Any]] = []
    sources: list[str] = []
    source_seen: set[str] = set()

    for idx, doc in enumerate(docs):
        text = str(doc or "").strip()
        meta = metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {}
        src = str(meta.get("source_url", "") or "").strip()
        if src and src not in source_seen:
            source_seen.add(src)
            sources.append(src)
        chunks.append({
            "rank": idx + 1,
            "text": text,
            "source_url": src,
            "record_type": str(meta.get("record_type", "") or ""),
            "id": str(meta.get("id", "") or ""),
            "meta": meta,
        })

    context_parts: list[str] = []
    for c in chunks:
        if not c["text"]:
            continue
        context_parts.append(f"[{c['rank']}] {c['text']}")

    context = "\n\n".join(context_parts)
    max_chars = _max_context_chars()
    if len(context) > max_chars:
        context = context[:max_chars].rstrip() + "\n\n[...baglam kisaltildi...]"

    return {
        "question": user_q,
        "collection": coll_name,
        "top_k": k,
        "chunks": chunks,
        "context": context,
        "sources": sources,
        "count": len(chunks),
    }

