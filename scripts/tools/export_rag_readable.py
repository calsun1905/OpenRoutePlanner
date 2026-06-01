"""
Chroma RAG verisini okunabilir CSV ve Markdown formatina aktarir.

Kullanim:
    python scripts/tools/export_rag_readable.py
    python scripts/tools/export_rag_readable.py --limit 500
"""

from __future__ import annotations

import argparse
import csv
import os
import sqlite3
from collections import defaultdict
from datetime import datetime
from typing import Iterable


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _default_db_path() -> str:
    env_path = (os.getenv("ORP_RAG_DB_PATH", "") or "").strip()
    if env_path:
        return env_path
    return os.path.join(_repo_root(), "chroma_db", "chroma.sqlite3")


def _read_rows(db_path: str, limit: int | None = None) -> list[dict[str, str]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    sql = """
    SELECT
        c.id AS chunk_id,
        c.c0 AS text,
        MAX(CASE WHEN m.key = 'ad' THEN m.string_value END) AS ad,
        MAX(CASE WHEN m.key = 'kategori' THEN m.string_value END) AS kategori,
        MAX(CASE WHEN m.key = 'record_type' THEN m.string_value END) AS record_type,
        MAX(CASE WHEN m.key = 'source_url' THEN m.string_value END) AS source_url,
        MAX(CASE WHEN m.key = 'semt' THEN m.string_value END) AS semt,
        MAX(CASE WHEN m.key = 'hat_kodu' THEN m.string_value END) AS hat_kodu,
        MAX(CASE WHEN m.key = 'operator' THEN m.string_value END) AS operator,
        MAX(CASE WHEN m.key = 'son_guncelleme' THEN m.string_value END) AS son_guncelleme
    FROM embedding_fulltext_search_content c
    LEFT JOIN embedding_metadata m ON m.id = c.id
    GROUP BY c.id, c.c0
    ORDER BY c.id
    """
    if limit and limit > 0:
        sql += f" LIMIT {int(limit)}"

    rows = []
    for row in cur.execute(sql):
        ad = _repair_mojibake(str(row["ad"] or ""))
        kategori = _repair_mojibake(str(row["kategori"] or ""))
        record_type = _repair_mojibake(str(row["record_type"] or ""))
        source_url = str(row["source_url"] or "")
        semt = _repair_mojibake(str(row["semt"] or ""))
        hat_kodu = _repair_mojibake(str(row["hat_kodu"] or ""))
        operator = _repair_mojibake(str(row["operator"] or ""))
        son_guncelleme = _repair_mojibake(str(row["son_guncelleme"] or ""))
        text = _repair_mojibake(str(row["text"] or "").strip())

        rows.append(
            {
                "chunk_id": str(row["chunk_id"] or ""),
                "ad": ad,
                "kategori": kategori,
                "record_type": record_type,
                "semt": semt,
                "hat_kodu": hat_kodu,
                "operator": operator,
                "source_url": source_url,
                "son_guncelleme": son_guncelleme,
                "text": text,
            }
        )
    conn.close()
    return rows


def _repair_mojibake(value: str) -> str:
    """
    UTF-8 metnin yanlislikla latin-1/cp1252 gibi okunmasindan kaynakli
    tipik '�' vb. bozulmalari onarmaya calisir.
    """
    s = (value or "").strip()
    if not s:
        return s
    markers = ("ï¿½", "ï¿½", "ï¿½", "ï¿½", "??", "?", "?")
    if not any(m in s for m in markers):
        return s
    for enc in ("latin1", "cp1252"):
        try:
            fixed = s.encode(enc).decode("utf-8")
        except Exception:
            continue
        if fixed and fixed != s:
            return fixed
    return s


def _ensure_parent(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _write_csv(path: str, rows: Iterable[dict[str, str]]) -> None:
    _ensure_parent(path)
    fieldnames = [
        "chunk_id",
        "ad",
        "kategori",
        "record_type",
        "semt",
        "hat_kodu",
        "operator",
        "source_url",
        "son_guncelleme",
        "text",
    ]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _short_text(text: str, max_len: int = 220) -> str:
    val = (text or "").strip().replace("\r", " ").replace("\n", " ")
    if len(val) <= max_len:
        return val
    return val[: max_len - 3].rstrip() + "..."


def _write_markdown(path: str, rows: list[dict[str, str]]) -> None:
    _ensure_parent(path)

    by_record = defaultdict(int)
    by_category = defaultdict(int)
    for row in rows:
        by_record[row["record_type"] or "BILINMIYOR"] += 1
        by_category[row["kategori"] or "BILINMIYOR"] += 1

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# RAG Icerik Raporu (Okunabilir)\n\n")
        f.write(f"- Uretim zamani: {now}\n")
        f.write(f"- Toplam chunk: {len(rows)}\n\n")

        f.write("## Dagilim (record_type)\n\n")
        for key, val in sorted(by_record.items(), key=lambda x: (-x[1], x[0])):
            f.write(f"- {key}: {val}\n")
        f.write("\n")

        f.write("## Dagilim (kategori)\n\n")
        for key, val in sorted(by_category.items(), key=lambda x: (-x[1], x[0])):
            f.write(f"- {key}: {val}\n")
        f.write("\n")

        f.write("## Ilk 120 Kayit (Ozet)\n\n")
        f.write("| id | ad | record_type | kategori | semt | kaynak | metin |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for row in rows[:120]:
            source = row["source_url"]
            if source:
                source_md = f"[link]({source})"
            else:
                source_md = "-"
            line = (
                f"| {row['chunk_id']} "
                f"| {row['ad'] or '-'} "
                f"| {row['record_type'] or '-'} "
                f"| {row['kategori'] or '-'} "
                f"| {row['semt'] or '-'} "
                f"| {source_md} "
                f"| {_short_text(row['text']).replace('|', '\\|')} |\n"
            )
            f.write(line)

        f.write("\n## Tam Metinler\n\n")
        for row in rows:
            f.write(f"### Chunk {row['chunk_id']} - {row['ad'] or 'Adsiz'}\n\n")
            f.write(f"- record_type: {row['record_type'] or '-'}\n")
            f.write(f"- kategori: {row['kategori'] or '-'}\n")
            f.write(f"- semt: {row['semt'] or '-'}\n")
            f.write(f"- hat_kodu: {row['hat_kodu'] or '-'}\n")
            f.write(f"- operator: {row['operator'] or '-'}\n")
            f.write(f"- son_guncelleme: {row['son_guncelleme'] or '-'}\n")
            f.write(f"- source_url: {row['source_url'] or '-'}\n\n")
            f.write(f"{row['text'] or '-'}\n\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Chroma RAG verisini okunabilir disa aktarir.")
    parser.add_argument("--db-path", default=_default_db_path(), help="chroma.sqlite3 dosya yolu")
    parser.add_argument("--limit", type=int, default=0, help="Kayit limiti (0 = tumu)")
    parser.add_argument(
        "--out-dir",
        default=os.path.join(_repo_root(), "artifacts", "rag_readable"),
        help="Cikti klasoru",
    )
    args = parser.parse_args()

    db_path = os.path.abspath(args.db_path)
    if not os.path.exists(db_path):
        raise SystemExit(f"RAG DB bulunamadi: {db_path}")

    rows = _read_rows(db_path=db_path, limit=args.limit if args.limit and args.limit > 0 else None)
    if not rows:
        raise SystemExit("RAG DB icinde okunabilir chunk bulunamadi.")

    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    csv_path = os.path.join(out_dir, "rag_chunks_readable.csv")
    md_path = os.path.join(out_dir, "rag_chunks_readable.md")

    _write_csv(csv_path, rows)
    _write_markdown(md_path, rows)

    print(f"OK: {len(rows)} kayit disa aktarildi.")
    print(f"CSV: {csv_path}")
    print(f"MD : {md_path}")


if __name__ == "__main__":
    main()
