"""
Evaluate BERT NLP output against Turkish gold dataset.

Usage:
    python scripts/tools/evaluate_bert_gold.py
    python scripts/tools/evaluate_bert_gold.py --dataset tests/data/bert_gold_tr_v1.jsonl --limit 10
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


CHAR_TRANSLIT = str.maketrans(
    {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
        "â": "a",
        "î": "i",
        "û": "u",
    }
)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).casefold().strip()
    text = text.translate(CHAR_TRANSLIT)
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fuzzy_match(expected: Any, predicted: Any) -> bool:
    exp = normalize_text(expected)
    pred = normalize_text(predicted)
    if not exp or not pred:
        return False
    if exp == pred:
        return True
    if len(exp) >= 4 and exp in pred:
        return True
    if len(pred) >= 4 and pred in exp:
        return True
    return False


def match_list(expected_items: List[Any], predicted_items: List[Any]) -> bool:
    if not isinstance(predicted_items, list):
        return False

    unmatched = list(predicted_items)
    for expected in expected_items:
        matched_idx = None
        for idx, predicted in enumerate(unmatched):
            if fuzzy_match(expected, predicted):
                matched_idx = idx
                break
        if matched_idx is None:
            return False
        unmatched.pop(matched_idx)

    return True


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    if pct <= 0:
        return min(values)
    if pct >= 100:
        return max(values)
    ordered = sorted(values)
    rank = (len(ordered) - 1) * (pct / 100.0)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    frac = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * frac


def load_dataset(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for lineno, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {lineno}: {exc}") from exc
            if "query" not in data or "expected" not in data:
                raise ValueError(f"Missing query/expected on line {lineno}")
            records.append(data)
    return records


def evaluate_case(case: Dict[str, Any], result: Dict[str, Any]) -> Tuple[bool, Dict[str, bool]]:
    expected = case.get("expected", {})
    field_status: Dict[str, bool] = {}

    for key, expected_value in expected.items():
        predicted_value = result.get(key)

        if key == "locations" and isinstance(expected_value, list):
            ok = match_list(expected_value, predicted_value if isinstance(predicted_value, list) else [])
        elif key == "mentions" and isinstance(expected_value, list):
            detected_places = [item.get("place") for item in result.get("detected_places", []) if item.get("place")]
            ok = match_list(expected_value, detected_places)
        elif key == "type":
            ok = normalize_text(expected_value) == normalize_text(predicted_value)
        else:
            ok = fuzzy_match(expected_value, predicted_value)

        field_status[key] = ok

    return all(field_status.values()), field_status


def append_confusion_cell(
    matrix: Dict[str, Dict[str, int]],
    expected_type: str,
    predicted_type: str,
) -> None:
    row = matrix.setdefault(expected_type, {})
    row[predicted_type] = row.get(predicted_type, 0) + 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate BERT NLP with Turkish gold dataset")
    parser.add_argument(
        "--dataset",
        default=str(ROOT_DIR / "tests" / "data" / "bert_gold_tr_v1.jsonl"),
        help="Path to JSONL dataset",
    )
    parser.add_argument("--limit", type=int, default=0, help="Evaluate only first N cases (0 = all)")
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write markdown report to docs/raporlar",
    )
    parser.add_argument(
        "--with-osm",
        action="store_true",
        help="Enable OSM lookup during evaluation (default: disabled for deterministic benchmark)",
    )
    parser.add_argument(
        "--osm-first",
        action="store_true",
        help="Enable OSM-first candidate prefetch (implies --with-osm)",
    )
    parser.add_argument(
        "--no-static",
        action="store_true",
        help="Disable static Turkey place seed (default: enabled)",
    )
    parser.add_argument(
        "--with-dynamic-cache",
        action="store_true",
        help="Load cached dynamic OSM places from local DB (default: disabled for clean benchmark)",
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.is_file():
        print(f"[ERROR] Dataset not found: {dataset_path}")
        return 1

    # Benchmark varsayılanı: deterministik ve tekrar üretilebilir.
    os.environ["ORP_BERT_USE_OSM"] = "1" if (args.with_osm or args.osm_first) else "0"
    os.environ["ORP_BERT_PREFER_OSM_FIRST"] = "1" if args.osm_first else "0"
    os.environ["ORP_BERT_SEED_DYNAMIC"] = "1" if args.with_dynamic_cache else "0"
    os.environ["ORP_BERT_SEED_STATIC"] = "0" if args.no_static else "1"
    os.environ["ORP_BERT_SEED_USER_LOCATIONS"] = "1"
    os.environ["ORP_BERT_SEED_LOCAL"] = "1"

    from bert_engine import is_bert_available
    if not is_bert_available():
        print("[ERROR] BERT dependencies are not installed (transformers + torch).")
        return 1

    from bert_nlp_engine import get_bert_nlp_engine

    records = load_dataset(dataset_path)
    if args.limit > 0:
        records = records[: args.limit]

    if not records:
        print("[ERROR] Dataset is empty.")
        return 1

    engine = get_bert_nlp_engine()

    cases_passed = 0
    field_totals: Dict[str, int] = {}
    field_passed: Dict[str, int] = {}
    latencies_ms: List[float] = []
    failures: List[Dict[str, Any]] = []
    type_confusion: Dict[str, Dict[str, int]] = {}

    for case in records:
        query = case["query"]
        started = time.perf_counter()
        result = engine.parse(query)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        latencies_ms.append(elapsed_ms)

        case_ok, fields = evaluate_case(case, result)
        if case_ok:
            cases_passed += 1
        else:
            failures.append(
                {
                    "id": case.get("id"),
                    "query": query,
                    "expected": case.get("expected", {}),
                    "predicted": {
                        "type": result.get("type"),
                        "origin": result.get("origin"),
                        "destination": result.get("destination"),
                        "location": result.get("location"),
                        "locations": result.get("locations"),
                    },
                    "field_status": fields,
                }
            )

        expected_type = normalize_text(case.get("expected", {}).get("type"))
        predicted_type = normalize_text(result.get("type"))
        if expected_type:
            append_confusion_cell(
                type_confusion,
                expected_type,
                predicted_type or "unknown",
            )

        for field_name, ok in fields.items():
            field_totals[field_name] = field_totals.get(field_name, 0) + 1
            field_passed[field_name] = field_passed.get(field_name, 0) + int(ok)

    total = len(records)
    case_accuracy = cases_passed / total if total else 0.0

    print("\n=== BERT GOLD EVALUATION (TR) ===")
    print(f"Dataset: {dataset_path}")
    print(f"Cases: {total}")
    print(
        "Mode: "
        f"OSM={'on' if os.environ.get('ORP_BERT_USE_OSM') == '1' else 'off'}, "
        f"OSM-first={'on' if os.environ.get('ORP_BERT_PREFER_OSM_FIRST') == '1' else 'off'}, "
        f"dynamic-cache={'on' if os.environ.get('ORP_BERT_SEED_DYNAMIC') == '1' else 'off'}, "
        f"static-seed={'on' if os.environ.get('ORP_BERT_SEED_STATIC') == '1' else 'off'}"
    )
    print(f"Case accuracy: {case_accuracy:.2%} ({cases_passed}/{total})")
    print(f"Latency p50: {percentile(latencies_ms, 50):.1f} ms")
    print(f"Latency p95: {percentile(latencies_ms, 95):.1f} ms")
    print("\nField accuracy:")
    for field_name in sorted(field_totals.keys()):
        passed = field_passed.get(field_name, 0)
        total_count = field_totals[field_name]
        score = passed / total_count if total_count else 0.0
        print(f"- {field_name}: {score:.2%} ({passed}/{total_count})")

    if type_confusion:
        labels = sorted(
            set(type_confusion.keys())
            | {pred for row in type_confusion.values() for pred in row.keys()}
        )
        print("\nType confusion matrix (expected -> predicted):")
        header = "expected\\pred".ljust(14) + " ".join(label.ljust(10) for label in labels)
        print(header)
        for expected in labels:
            row = type_confusion.get(expected, {})
            row_values = " ".join(str(row.get(predicted, 0)).ljust(10) for predicted in labels)
            print(expected.ljust(14) + row_values)

    if failures:
        print("\nTop failures:")
        for item in failures[:10]:
            print(f"- {item.get('id')}: {item.get('query')}")
            print(f"  expected={item.get('expected')}")
            print(f"  predicted={item.get('predicted')}")
            print(f"  fields={item.get('field_status')}")
    else:
        print("\nNo failures.")

    if args.write_report:
        report_dir = ROOT_DIR / "docs" / "raporlar"
        report_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"BERT_GOLD_EVAL_TR_{ts}.md"
        with report_path.open("w", encoding="utf-8") as handle:
            handle.write("# BERT Gold Evaluation (TR)\n\n")
            handle.write(f"- Dataset: `{dataset_path}`\n")
            handle.write(f"- Cases: {total}\n")
            handle.write(f"- Case accuracy: {case_accuracy:.2%} ({cases_passed}/{total})\n")
            handle.write(f"- Latency p50: {percentile(latencies_ms, 50):.1f} ms\n")
            handle.write(f"- Latency p95: {percentile(latencies_ms, 95):.1f} ms\n\n")
            handle.write("## Field Accuracy\n\n")
            for field_name in sorted(field_totals.keys()):
                passed = field_passed.get(field_name, 0)
                total_count = field_totals[field_name]
                score = passed / total_count if total_count else 0.0
                handle.write(f"- {field_name}: {score:.2%} ({passed}/{total_count})\n")
            if type_confusion:
                labels = sorted(
                    set(type_confusion.keys())
                    | {pred for row in type_confusion.values() for pred in row.keys()}
                )
                handle.write("\n## Type Confusion Matrix\n\n")
                handle.write("| expected \\ predicted | " + " | ".join(labels) + " |\n")
                handle.write("|---|" + "|".join(["---"] * len(labels)) + "|\n")
                for expected in labels:
                    row = type_confusion.get(expected, {})
                    cells = [str(row.get(predicted, 0)) for predicted in labels]
                    handle.write(f"| {expected} | " + " | ".join(cells) + " |\n")
            handle.write("\n## Failures (first 20)\n\n")
            if not failures:
                handle.write("- None\n")
            else:
                for item in failures[:20]:
                    handle.write(f"- `{item.get('id')}`: {item.get('query')}\n")
                    handle.write(f"  - expected: `{item.get('expected')}`\n")
                    handle.write(f"  - predicted: `{item.get('predicted')}`\n")
                    handle.write(f"  - fields: `{item.get('field_status')}`\n")
        print(f"\nReport written: {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
