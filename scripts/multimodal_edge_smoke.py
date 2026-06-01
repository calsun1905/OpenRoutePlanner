#!/usr/bin/env python3
"""
Multimodal edge/smoke tester for /api/multimodal/compare.

Usage examples:
  python scripts/multimodal_edge_smoke.py
  python scripts/multimodal_edge_smoke.py --base-url http://127.0.0.1:5000 --timeout 120
  python scripts/multimodal_edge_smoke.py --only 4 5 14a
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Scenario:
    sid: str
    name: str
    origin: Tuple[float, float]
    destination: Tuple[float, float]
    modes: Tuple[str, ...]
    expect_transit: bool


SCENARIOS: List[Scenario] = [
    Scenario("1", "ferry_direct", (41.0169, 28.9700), (40.9909, 29.0246), ("ferry",), True),
    Scenario("2", "ferry_uskudar_line", (41.0265, 29.0142), (41.0410, 29.0053), ("ferry",), True),
    Scenario("3", "ferry_bus_mixed", (41.0520, 29.0200), (40.9700, 29.1000), ("ferry", "bus"), True),
    Scenario("4", "metrobus_long", (41.0120, 28.6506), (40.9920, 29.0372), ("metrobus",), True),
    Scenario("5", "metrobus_far_origin", (41.0300, 28.9200), (40.9920, 29.0372), ("metrobus",), False),
    Scenario("6", "bus_only_multi_transfer", (41.0237, 28.9431), (40.9825, 29.0552), ("bus",), True),
    Scenario("7", "bus_metrobus_mixed", (41.0000, 28.8200), (41.0700, 29.0100), ("bus", "metrobus"), True),
    Scenario("8", "metro_m4_corridor", (40.9926, 29.0234), (40.8822, 29.2473), ("metro",), True),
    Scenario("9", "metro_cross", (41.0369, 28.9851), (41.0801, 29.0116), ("metro",), False),
    Scenario("10", "all_modes_far", (41.1674, 29.0578), (40.8164, 29.3002), ("bus", "metro", "metrobus", "ferry"), True),
    Scenario("11", "ferry_same_side", (41.0400, 29.0000), (41.0600, 29.0200), ("ferry",), False),
    Scenario("14a", "water_point_metrobus", (41.0200, 28.9600), (40.9909, 29.0246), ("metrobus",), False),
    Scenario("14b", "water_point_ferry", (41.0200, 28.9600), (40.9909, 29.0246), ("ferry",), False),
]


def segment_user_mode(seg: Dict) -> Optional[str]:
    mode = str(seg.get("mode") or "").lower()
    if not mode or mode == "walk":
        return None
    if mode == "ferry":
        return "ferry"
    if mode == "rail":
        return "metro"
    if mode == "bus":
        route_code = str(seg.get("route_code") or "").upper().strip()
        if route_code.startswith("34"):
            return "metrobus"
        return "bus"
    return None


def option_has_mode_leak(option: Dict, allowed_modes: Sequence[str]) -> bool:
    allowed = {m.lower() for m in allowed_modes}
    for seg in option.get("segments") or []:
        u_mode = segment_user_mode(seg)
        if u_mode and u_mode not in allowed:
            return True
    return False


def post_json(base_url: str, path: str, payload: Dict, timeout_sec: int) -> Dict:
    url = base_url.rstrip("/") + path
    body = json.dumps(payload).encode("utf-8")
    req = Request(url=url, data=body, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    with urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def run_scenario(base_url: str, timeout_sec: int, sc: Scenario) -> Dict:
    t0 = time.perf_counter()
    payload = {
        "origin": [sc.origin[0], sc.origin[1]],
        "destination": [sc.destination[0], sc.destination[1]],
        "allowed_modes": list(sc.modes),
    }
    data = post_json(base_url, "/api/multimodal/compare", payload, timeout_sec)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    options = data.get("options") or []
    transit = [o for o in options if str(o.get("type")) == "transit"]
    leak_count = sum(1 for o in transit if option_has_mode_leak(o, sc.modes))

    ok = True
    reason = "pass"
    if leak_count > 0:
        ok = False
        reason = "mode_leak"
    elif sc.expect_transit and not transit:
        ok = False
        reason = "no_transit"

    first_name = "-"
    first_modes = "-"
    if transit:
        first_name = str(transit[0].get("name") or "-")
        first_modes = " -> ".join(str(s.get("mode") or "") for s in (transit[0].get("segments") or []))

    return {
        "id": sc.sid,
        "name": sc.name,
        "ok": ok,
        "result_reason": reason,
        "elapsed_ms": elapsed_ms,
        "recommended": data.get("recommended"),
        "recommendation_reason": data.get("recommendation_reason"),
        "transit_count": len(transit),
        "mode_leak_count": leak_count,
        "strict_snap": ((data.get("telemetry") or {}).get("fallback_strict_mode_snap_applied")),
        "first_transit": first_name,
        "first_modes": first_modes,
    }


def run_cache_repeat(base_url: str, timeout_sec: int, repeats: int = 3) -> List[Dict]:
    sc = Scenario("15", "cache_repeat_metrobus_long", (41.0120, 28.6506), (40.9920, 29.0372), ("metrobus",), True)
    rows: List[Dict] = []
    for idx in range(1, repeats + 1):
        try:
            result = run_scenario(base_url, timeout_sec, sc)
            result["run"] = idx
            rows.append(result)
        except Exception as exc:  # noqa: BLE001
            rows.append(
                {
                    "run": idx,
                    "id": sc.sid,
                    "name": sc.name,
                    "ok": False,
                    "result_reason": f"error:{type(exc).__name__}",
                    "elapsed_ms": -1,
                    "recommended": "-",
                    "recommendation_reason": str(exc),
                    "transit_count": -1,
                    "mode_leak_count": -1,
                    "strict_snap": None,
                    "first_transit": "-",
                    "first_modes": "-",
                }
            )
    return rows


def print_table(rows: Iterable[Dict]) -> None:
    rows = list(rows)
    if not rows:
        print("No rows.")
        return
    cols = [
        "id",
        "name",
        "ok",
        "result_reason",
        "elapsed_ms",
        "transit_count",
        "mode_leak_count",
        "recommended",
        "strict_snap",
        "first_transit",
    ]
    widths = {c: len(c) for c in cols}
    for r in rows:
        for c in cols:
            widths[c] = max(widths[c], len(str(r.get(c, ""))))
    line = " | ".join(c.ljust(widths[c]) for c in cols)
    print(line)
    print("-+-".join("-" * widths[c] for c in cols))
    for r in rows:
        print(" | ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run multimodal edge smoke scenarios.")
    p.add_argument("--base-url", default="http://127.0.0.1:5000", help="Backend base URL.")
    p.add_argument("--timeout", type=int, default=120, help="Per-request timeout seconds.")
    p.add_argument("--only", nargs="*", default=None, help="Scenario IDs to run, e.g. --only 4 5 14a")
    p.add_argument("--skip-cache", action="store_true", help="Skip case 15 cache repeat.")
    p.add_argument("--json-out", default=None, help="Optional path to write JSON report.")
    return p.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    wanted = set(args.only or [])
    scenarios = [s for s in SCENARIOS if (not wanted or s.sid in wanted)]

    all_rows: List[Dict] = []
    for sc in scenarios:
        try:
            row = run_scenario(args.base_url, args.timeout, sc)
        except HTTPError as exc:
            row = {
                "id": sc.sid,
                "name": sc.name,
                "ok": False,
                "result_reason": f"http_{exc.code}",
                "elapsed_ms": -1,
                "transit_count": -1,
                "mode_leak_count": -1,
                "recommended": "-",
                "strict_snap": None,
                "first_transit": "-",
                "recommendation_reason": str(exc),
            }
        except URLError as exc:
            row = {
                "id": sc.sid,
                "name": sc.name,
                "ok": False,
                "result_reason": "url_error",
                "elapsed_ms": -1,
                "transit_count": -1,
                "mode_leak_count": -1,
                "recommended": "-",
                "strict_snap": None,
                "first_transit": "-",
                "recommendation_reason": str(exc),
            }
        except Exception as exc:  # noqa: BLE001
            row = {
                "id": sc.sid,
                "name": sc.name,
                "ok": False,
                "result_reason": f"error:{type(exc).__name__}",
                "elapsed_ms": -1,
                "transit_count": -1,
                "mode_leak_count": -1,
                "recommended": "-",
                "strict_snap": None,
                "first_transit": "-",
                "recommendation_reason": str(exc),
            }
        all_rows.append(row)

    if not args.skip_cache and (not wanted or "15" in wanted):
        all_rows.extend(run_cache_repeat(args.base_url, args.timeout, repeats=3))

    print_table(all_rows)

    summary_total = len(all_rows)
    summary_ok = sum(1 for r in all_rows if bool(r.get("ok")))
    summary_fail = summary_total - summary_ok
    print()
    print(f"Summary: total={summary_total} pass={summary_ok} fail={summary_fail}")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump({"rows": all_rows}, f, ensure_ascii=False, indent=2)
        print(f"JSON report written: {args.json_out}")

    return 0 if summary_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

