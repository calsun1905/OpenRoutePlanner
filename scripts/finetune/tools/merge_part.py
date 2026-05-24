from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_existing(path: Path) -> set[str]:
    if not path.exists():
        return set()
    out: set[str] = set()
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            s = line.strip()
            if s:
                out.add(s)
    return out


def extract_blocks(text: str, start: str, end: str) -> list[str]:
    rows: list[str] = []
    active = False
    for raw in text.splitlines():
        line = raw.strip()
        if line == start:
            active = True
            continue
        if line == end:
            active = False
            continue
        if active and line:
            rows.append(line)
    return rows


def normalize_json_line(line: str) -> str:
    obj: Any = json.loads(line)
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))


def append_unique(target: Path, rows: list[str]) -> tuple[int, int, int]:
    existing = read_existing(target)
    added = 0
    invalid = 0
    dup = 0
    with target.open('a', encoding='utf-8') as f:
        for line in rows:
            try:
                norm = normalize_json_line(line)
            except Exception:
                invalid += 1
                continue
            if norm in existing:
                dup += 1
                continue
            existing.add(norm)
            f.write(norm + '\n')
            added += 1
    return added, dup, invalid


def main() -> None:
    p = argparse.ArgumentParser(description='Merge pasted SFT/DPO parts into cumulative jsonl files.')
    p.add_argument('--input-file', required=True, help='Path to a txt/md file containing SFT_JSONL_START/END and DPO_JSONL_START/END blocks')
    p.add_argument('--sft-out', default='artifacts/finetune/input/sft_raw.jsonl')
    p.add_argument('--dpo-out', default='artifacts/finetune/input/dpo_raw.jsonl')
    args = p.parse_args()

    text = Path(args.input_file).read_text(encoding='utf-8')
    sft_rows = extract_blocks(text, 'SFT_JSONL_START', 'SFT_JSONL_END')
    dpo_rows = extract_blocks(text, 'DPO_JSONL_START', 'DPO_JSONL_END')

    sft_out = Path(args.sft_out)
    dpo_out = Path(args.dpo_out)
    sft_out.parent.mkdir(parents=True, exist_ok=True)
    dpo_out.parent.mkdir(parents=True, exist_ok=True)

    sft_added, sft_dup, sft_invalid = append_unique(sft_out, sft_rows)
    dpo_added, dpo_dup, dpo_invalid = append_unique(dpo_out, dpo_rows)

    summary = {
        'sft': {
            'found_in_part': len(sft_rows),
            'added': sft_added,
            'duplicate': sft_dup,
            'invalid': sft_invalid,
        },
        'dpo': {
            'found_in_part': len(dpo_rows),
            'added': dpo_added,
            'duplicate': dpo_dup,
            'invalid': dpo_invalid,
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
