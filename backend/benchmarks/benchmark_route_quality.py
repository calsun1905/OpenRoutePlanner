"""
Offline route quality benchmark for bridge/snap improvements.

Usage (from repo root):
    venv_test\\Scripts\\python.exe backend\\benchmark_route_quality.py
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from pathlib import Path

import graph_manager
import networkx as nx
import route_engine_impl as route_engine
from route_config import ROUTE_CONFIG


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "benchmark_results.json"
DEFAULT_USER_CASES = ROOT / "benchmark_user_cases.json"
BUCKET_PROFILES = {
    "coastline": {"center": (41.03, 29.02), "radius_m": 7000, "cache_graphml": "kadikoy_istanbul_turkey.graphml"},
    "bridge_sensitive": {"center": (41.01, 29.03), "radius_m": 7000, "cache_graphml": "besiktas_istanbul_turkey.graphml"},
    "long_edge_snap": {"center": (40.99, 29.07), "radius_m": 7500, "cache_graphml": "kadikoy_istanbul_turkey.graphml"},
    "low_connectivity": {"center": (41.08, 29.05), "radius_m": 8000, "cache_graphml": "maslak_istanbul_turkey.graphml"},
    "alternatives": {"center": (41.00, 29.00), "radius_m": 7000, "cache_graphml": "kadikoy_istanbul_turkey.graphml"},
    "user_real_case": {"center": (41.01, 29.02), "radius_m": 8000, "cache_graphml": "kadikoy_istanbul_turkey.graphml"},
}


def _generate_point_pair(rng: random.Random, center_lat: float, center_lon: float, span: float):
    lat1 = center_lat + rng.uniform(-span, span)
    lon1 = center_lon + rng.uniform(-span, span)
    lat2 = center_lat + rng.uniform(-span, span)
    lon2 = center_lon + rng.uniform(-span, span)
    return [[round(lat1, 6), round(lon1, 6)], [round(lat2, 6), round(lon2, 6)]]


def build_hybrid_scenarios(total: int, user_cases_path: Path) -> list[dict]:
    rng = random.Random(20260525)
    scenarios: list[dict] = []

    user_cases: list[dict] = []
    if user_cases_path.exists():
        try:
            raw = json.loads(user_cases_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                for item in raw:
                    if isinstance(item, dict) and isinstance(item.get("points"), list):
                        user_cases.append(item)
        except (OSError, ValueError):
            user_cases = []

    for idx, item in enumerate(user_cases[:100]):
        item = dict(item)
        item.setdefault("id", f"user_case_{idx+1:03d}")
        item.setdefault("category", "user_real_case")
        item.setdefault("bucket", item.get("category", "user_real_case"))
        scenarios.append(item)

    core_categories = [
        ("coastline", 41.03, 29.02, 0.03),
        ("bridge_sensitive", 41.01, 29.03, 0.025),
        ("long_edge_snap", 40.99, 29.07, 0.035),
        ("low_connectivity", 41.08, 29.05, 0.04),
        ("alternatives", 41.00, 29.00, 0.03),
    ]

    # Guarantee at least 150 core-like scenarios.
    while len(scenarios) < 150:
        category, lat, lon, span = core_categories[len(scenarios) % len(core_categories)]
        scenarios.append(
            {
                "id": f"core_{len(scenarios)+1:03d}",
                "category": category,
                "bucket": category,
                "points": _generate_point_pair(rng, lat, lon, span),
                "avoid_bridge_preference": category in {"coastline", "bridge_sensitive"},
            }
        )

    # Fill to requested total (default 250) with deterministic synthetic cases.
    while len(scenarios) < total:
        category, lat, lon, span = rng.choice(core_categories)
        scenarios.append(
            {
                "id": f"synthetic_{len(scenarios)+1:03d}",
                "category": category,
                "bucket": category,
                "points": _generate_point_pair(rng, lat, lon, span),
                "avoid_bridge_preference": category in {"coastline", "bridge_sensitive"},
            }
        )

    return scenarios[:total]


def _count_bridge_edges(G, route_nodes: list[int]) -> int:
    count = 0
    for i in range(len(route_nodes) - 1):
        _, best = route_engine._best_edge_data(G, route_nodes[i], route_nodes[i + 1])  # noqa: SLF001
        if best and graph_manager._is_bridge_edge(best):  # noqa: SLF001
            count += 1
    return count


def _get_bucket_graph(bucket: str, graph_cache: dict[str, nx.MultiDiGraph]):
    if bucket in graph_cache:
        return graph_cache[bucket]

    profile = BUCKET_PROFILES.get(bucket, BUCKET_PROFILES["user_real_case"])
    center_lat, center_lon = profile["center"]
    radius_m = int(profile["radius_m"])
    predefined_name = str(profile.get("cache_graphml", "")).strip()

    if predefined_name:
        predefined_path = ROOT / "data" / predefined_name
        if predefined_path.exists():
            G = graph_manager.ox.load_graphml(predefined_path)
            G = graph_manager._prepare_graph_for_routing(G)  # noqa: SLF001
            graph_cache[bucket] = G
            return G

    cache_file = ROOT / "data" / f"benchmark_bucket_{bucket}_{radius_m}_all.graphml"

    if cache_file.exists():
        G = graph_manager.ox.load_graphml(cache_file)
    else:
        G = graph_manager.ox.graph_from_point(
            (center_lat, center_lon),
            dist=radius_m,
            network_type="walk",
            retain_all=True,
        )
        graph_manager.ox.save_graphml(G, cache_file)

    G = graph_manager._prepare_graph_for_routing(G)  # noqa: SLF001
    graph_cache[bucket] = G
    return G


def _run_single_scenario(scenario: dict, graph_cache: dict[str, nx.MultiDiGraph]) -> dict:
    points = [(float(p[0]), float(p[1])) for p in scenario["points"]]
    started = time.perf_counter()
    bucket = str(scenario.get("bucket", scenario.get("category", "user_real_case")))
    G = _get_bucket_graph(bucket, graph_cache)

    snap_infos = []
    for lat, lon in points:
        node_id, edge_dist_m = graph_manager.find_nearest_node_with_distance(G, lat, lon)
        node_dist_m = graph_manager._distance_to_node_m(G, node_id, lat, lon)  # noqa: SLF001
        snap_infos.append(
            {
                "node": int(node_id),
                "edge_dist_m": float(edge_dist_m),
                "node_dist_m": float(node_dist_m),
                "gap_m": float(node_dist_m - edge_dist_m),
            }
        )

    if len(points) > 2:
        order = route_engine.solve_tsp(G, points)
    else:
        order = list(range(len(points)))
    ordered_points = [points[i] for i in order]

    route_nodes = route_engine.build_alternative_routes(G, ordered_points, route_index=0)
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    if not route_nodes:
        return {
            "id": scenario.get("id", "unknown"),
            "ok": False,
            "latency_ms": elapsed_ms,
            "bridge_edges": 0,
            "snap_infos": snap_infos,
            "category": scenario.get("category", "unknown"),
        }

    bridge_edges = _count_bridge_edges(G, route_nodes)
    return {
        "id": scenario.get("id", "unknown"),
        "ok": True,
        "latency_ms": elapsed_ms,
        "bridge_edges": bridge_edges,
        "route_node_count": len(route_nodes),
        "snap_infos": snap_infos,
        "category": scenario.get("category", "unknown"),
    }


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    idx = max(0, int(0.95 * len(values_sorted)) - 1)
    return values_sorted[idx]


def run_benchmark(total: int, factors: list[float], user_cases: Path) -> dict:
    scenarios = build_hybrid_scenarios(total=total, user_cases_path=user_cases)
    outputs = []

    for factor in factors:
        ROUTE_CONFIG["BRIDGE_PENALTY_FACTOR"] = float(factor)
        graph_cache: dict[str, nx.MultiDiGraph] = {}
        per_case = []
        for scenario in scenarios:
            try:
                per_case.append(_run_single_scenario(scenario, graph_cache=graph_cache))
            except Exception as exc:  # Keep benchmark running and record failures.
                per_case.append(
                    {
                        "id": scenario.get("id", "unknown"),
                        "ok": False,
                        "latency_ms": 0.0,
                        "bridge_edges": 0,
                        "snap_infos": [],
                        "category": scenario.get("category", "unknown"),
                        "error": str(exc),
                    }
                )

        ok_cases = [c for c in per_case if c["ok"]]
        latencies = [c["latency_ms"] for c in per_case]
        bridge_counts = [c["bridge_edges"] for c in ok_cases]
        snap_gaps = [s["gap_m"] for c in per_case for s in c["snap_infos"]]

        outputs.append(
            {
                "bridge_penalty_factor": factor,
                "scenario_count": len(per_case),
                "success_count": len(ok_cases),
                "success_rate": (len(ok_cases) / len(per_case)) if per_case else 0.0,
                "error_rate": ((len(per_case) - len(ok_cases)) / len(per_case)) if per_case else 0.0,
                "latency_ms_p50": statistics.median(latencies) if latencies else 0.0,
                "latency_ms_p95": _p95(latencies),
                "bridge_edges_avg": statistics.mean(bridge_counts) if bridge_counts else 0.0,
                "snap_gap_avg_m": statistics.mean(snap_gaps) if snap_gaps else 0.0,
                "cases": per_case,
            }
        )

    baseline = next((row for row in outputs if abs(row["bridge_penalty_factor"] - 1.0) < 1e-9), None)
    if baseline:
        base_avg = baseline["bridge_edges_avg"]
        for row in outputs:
            if base_avg > 0:
                row["bridge_reduction_vs_baseline"] = (base_avg - row["bridge_edges_avg"]) / base_avg
            else:
                row["bridge_reduction_vs_baseline"] = 0.0

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scenario_total": len(scenarios),
        "factors": factors,
        "results": outputs,
    }


def main():
    parser = argparse.ArgumentParser(description="Offline route quality benchmark")
    parser.add_argument("--total", type=int, default=250, help="Total scenario count")
    parser.add_argument(
        "--factors",
        type=float,
        nargs="+",
        default=[1.0, 1.4, 1.6, 1.8, 2.0],
        help="Bridge penalty factors to evaluate",
    )
    parser.add_argument("--user-cases", type=Path, default=DEFAULT_USER_CASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    report = run_benchmark(total=args.total, factors=args.factors, user_cases=args.user_cases)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Benchmark] Rapor yazildi: {args.output}")


if __name__ == "__main__":
    main()
