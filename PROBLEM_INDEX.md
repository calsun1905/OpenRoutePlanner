# OpenRoutePlanner - Problem Index (Updated)

**Date:** 2026-05-27  
**Status legend:** `open` | `partially-fixed` | `closed`

## 1) Current Matrix (16 Items)

| # | Problem | Status | Notes |
|---|---|---|---|
| 1 | TSP infinite value risk | `closed` | No-path handling uses large finite penalty + explicit unreachable contract path. |
| 2 | Edge overlap asymmetry/direction | `closed` | Overlap is direction-sensitive: `(u,v)` and `(v,u)` are different. |
| 3 | MultiDiGraph edge key missing | `closed` | Penalty logic tracks `(u,v,key)`; regression test added. |
| 4 | Unreachable nodes in TSP | `closed` | API returns `400` with `UNREACHABLE_WAYPOINTS` and `details.unreachable_pairs`. |
| 5 | Via-node missing node attributes | `closed` | Missing `x/y` nodes are skipped safely; insufficient route coords guarded. |
| 6 | TSP same-node mapping issue | `closed` | `node_to_indices` keeps all original point indices mapped to same node. |
| 7 | GPU overuse risk | `partially-fixed` | Startup eager warmup default disabled; full runtime policy still future work. |
| 8 | Slow route computation | `closed` | Added API+engine stage telemetry, concurrency guard, allowed-modes cap, and transit fan-out cap (MVP). |
| 9 | Fixed via-node sample count | `closed` | Dynamic sample count added with min/max + per-km config. |
| 10 | Coordinate tolerance fixed at `1e-6` | `closed` | Alternative-route dedup now uses distance-aware dynamic tolerance. |
| 11 | Overly broad exception capture | `closed` | Route-generation catch-all narrowed; unexpected errors are no longer silently masked there. |
| 12 | Test failures | `closed` | Full suite green: `96 passed, 0 failed`. |
| 13 | BERT POI parsing loss | `partially-fixed` | Added POI-intent rescue heuristic + tests; semantic edge-cases still backlog. |
| 14 | Weather UI missing in frontend | `closed` | Weather widget/banner/simulator actively fetch backend endpoints. |
| 15 | SQLite vs PostgreSQL decision | `closed` | SQLite strategy fixed; PostgreSQL migration is explicitly out of current scope. |
| 16 | Cache policy monitoring | `partially-fixed` | `/api/cache/stats` now includes policy evaluation/warnings; external alerting still backlog. |

## 2) Public API Changes Applied

For multi-point optimize flow, unreachable waypoint pairs now return:

- HTTP `400`
- `error_code: "UNREACHABLE_WAYPOINTS"`
- `details.unreachable_pairs: [[i,j], ...]`

This is now exercised by API tests.

Multimodal and cache observability additions:

- HTTP `429` on multimodal concurrency saturation:
  - `error_code: "MULTIMODAL_BUSY"`
  - `max_concurrency`
- `GET /api/cache/stats` endpoint for graph/poi/multimodal cache metrics + policy warnings.

## 3) Test Snapshot (2026-05-27)

Command:

```bash
.\venv_test\Scripts\python.exe -m pytest -q
```

Result:

- 96 collected
- 96 passed
- 0 failed

## 4) Remaining Backlog (Focused)

1. GPU/runtime policy hardening for NLP (queueing + memory thresholds + fallback policy).
2. Deeper multimodal performance optimization beyond current MVP telemetry/cap.
3. POI parse quality iteration for difficult Turkish query patterns.
4. SQLite strategy korunacak; DB migration planning bu kapsamda yok.
