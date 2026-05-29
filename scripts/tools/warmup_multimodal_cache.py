"""
Multimodal cache warmup runner.

Runs origin/destination pairs from a pool file one-by-one against
/api/multimodal/compare to fill route/segment/OSRM caches.

Usage examples:
  python scripts/tools/warmup_multimodal_cache.py
  python scripts/tools/warmup_multimodal_cache.py --max-cases 10
  python scripts/tools/warmup_multimodal_cache.py --reset-progress
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def _default_pool_file(project_root: Path) -> Path:
    return project_root / "backend" / "data" / "warmup_pool_crossshore_v1.json"


def _default_progress_file(pool_file: Path) -> Path:
    return pool_file.with_suffix(".progress.json")


def _init_progress(pool_data: dict[str, Any], pool_file: Path) -> dict[str, Any]:
    return {
        "version": "warmup_progress_v1",
        "pool_file": str(pool_file),
        "pool_version": pool_data.get("version", "unknown"),
        "started_at_utc": _utc_now(),
        "updated_at_utc": _utc_now(),
        "total_cases": int(pool_data.get("case_count", 0)),
        "completed_ids": [],
        "failed_cases": {},
        "stats": {
            "sent": 0,
            "success": 0,
            "failed": 0,
            "http_429": 0,
            "http_5xx": 0,
            "other_http": 0,
            "network_errors": 0,
        },
    }


def _upsert_failure(progress: dict[str, Any], case_id: str, message: str) -> None:
    failed = progress.setdefault("failed_cases", {})
    row = failed.get(case_id) or {"count": 0, "last_error": ""}
    row["count"] = int(row.get("count", 0)) + 1
    row["last_error"] = message
    row["updated_at_utc"] = _utc_now()
    failed[case_id] = row


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Warm up multimodal cache using OD pool")
    parser.add_argument(
        "--pool-file",
        default="",
        help="Path to warmup pool JSON. Default: backend/data/warmup_pool_crossshore_v1.json",
    )
    parser.add_argument(
        "--progress-file",
        default="",
        help="Path to progress file. Default: <pool-file>.progress.json",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:5000",
        help="Backend base URL",
    )
    parser.add_argument(
        "--endpoint",
        default="/api/multimodal/compare",
        help="Warmup endpoint path",
    )
    parser.add_argument(
        "--sleep-sec",
        type=float,
        default=1.2,
        help="Sleep between successful requests",
    )
    parser.add_argument(
        "--timeout-sec",
        type=float,
        default=90.0,
        help="HTTP timeout seconds",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Retry count on non-200/network errors",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=0,
        help="Run only first N pending cases (0 = all pending)",
    )
    parser.add_argument(
        "--stats-every",
        type=int,
        default=5,
        help="Print periodic stats every N successful cases",
    )
    parser.add_argument(
        "--reset-progress",
        action="store_true",
        help="Reset progress file and start from scratch",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not send requests; only print what would run",
    )
    return parser


def _normalize_url(base_url: str, endpoint: str) -> str:
    return base_url.rstrip("/") + "/" + endpoint.lstrip("/")


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    pool_file = Path(args.pool_file) if args.pool_file else _default_pool_file(project_root)
    progress_file = Path(args.progress_file) if args.progress_file else _default_progress_file(pool_file)
    url = _normalize_url(args.base_url, args.endpoint)

    if not pool_file.exists():
        print(f"[warmup] pool file missing: {pool_file}")
        return 1

    pool_data = _load_json(pool_file)
    cases = list(pool_data.get("cases") or [])
    if not cases:
        print(f"[warmup] no cases in pool: {pool_file}")
        return 1

    if args.reset_progress or not progress_file.exists():
        progress = _init_progress(pool_data, pool_file)
        _save_json(progress_file, progress)
    else:
        progress = _load_json(progress_file)
        progress.setdefault("completed_ids", [])
        progress.setdefault("failed_cases", {})
        progress.setdefault("stats", {})
        progress["updated_at_utc"] = _utc_now()

    completed_ids = set(progress.get("completed_ids") or [])
    pending = [c for c in cases if str(c.get("id")) not in completed_ids]
    if args.max_cases > 0:
        pending = pending[: args.max_cases]

    print(f"[warmup] pool: {pool_file}")
    print(f"[warmup] progress: {progress_file}")
    print(f"[warmup] endpoint: {url}")
    print(f"[warmup] pending cases: {len(pending)}")

    if args.dry_run:
        for idx, case in enumerate(pending, start=1):
            case_id = str(case.get("id"))
            print(f"[dry-run] {idx:03d} {case_id} {case.get('origin')} -> {case.get('destination')}")
        print("[warmup] dry-run complete")
        return 0

    session = requests.Session()
    success_since_log = 0

    for idx, case in enumerate(pending, start=1):
        case_id = str(case.get("id", f"row_{idx}"))
        payload = {
            "origin": case.get("origin"),
            "destination": case.get("destination"),
            "allowed_modes": case.get("allowed_modes", ["bus", "metro", "metrobus", "ferry"]),
        }

        print(f"[warmup] {idx:03d}/{len(pending):03d} -> {case_id}")
        ok = False
        last_error = ""

        for attempt in range(1, max(1, args.retries) + 2):
            progress["stats"]["sent"] = int(progress["stats"].get("sent", 0)) + 1
            try:
                resp = session.post(url, json=payload, timeout=float(args.timeout_sec))
            except Exception as exc:
                progress["stats"]["network_errors"] = int(progress["stats"].get("network_errors", 0)) + 1
                last_error = f"network error: {exc}"
                print(f"  [retry {attempt}] {last_error}")
                time.sleep(min(3.0, 0.5 * attempt))
                continue

            if resp.status_code == 200:
                completed_ids.add(case_id)
                progress["completed_ids"] = sorted(completed_ids)
                progress["stats"]["success"] = int(progress["stats"].get("success", 0)) + 1
                progress["failed_cases"].pop(case_id, None)
                ok = True
                print("  [ok] cached")
                break

            if resp.status_code == 429:
                progress["stats"]["http_429"] = int(progress["stats"].get("http_429", 0)) + 1
            elif 500 <= resp.status_code <= 599:
                progress["stats"]["http_5xx"] = int(progress["stats"].get("http_5xx", 0)) + 1
            else:
                progress["stats"]["other_http"] = int(progress["stats"].get("other_http", 0)) + 1

            short_body = (resp.text or "").strip().replace("\n", " ")
            if len(short_body) > 200:
                short_body = short_body[:200] + "..."
            last_error = f"http {resp.status_code}: {short_body}"
            print(f"  [retry {attempt}] {last_error}")
            time.sleep(min(3.0, 0.6 * attempt))

        if not ok:
            progress["stats"]["failed"] = int(progress["stats"].get("failed", 0)) + 1
            _upsert_failure(progress, case_id, last_error or "unknown failure")
            print(f"  [fail] {case_id}")
        else:
            success_since_log += 1
            if args.stats_every > 0 and success_since_log >= args.stats_every:
                success_since_log = 0
                stats = progress.get("stats", {})
                print(
                    "[warmup] stats sent={sent} success={success} failed={failed} "
                    "429={http_429} 5xx={http_5xx} net={network_errors}".format(
                        sent=stats.get("sent", 0),
                        success=stats.get("success", 0),
                        failed=stats.get("failed", 0),
                        http_429=stats.get("http_429", 0),
                        http_5xx=stats.get("http_5xx", 0),
                        network_errors=stats.get("network_errors", 0),
                    )
                )
            time.sleep(max(0.0, float(args.sleep_sec)))

        progress["updated_at_utc"] = _utc_now()
        _save_json(progress_file, progress)

    print("[warmup] done")
    print(json.dumps(progress.get("stats", {}), ensure_ascii=True, indent=2))
    print(f"[warmup] completed ids: {len(progress.get('completed_ids', []))}/{len(cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
