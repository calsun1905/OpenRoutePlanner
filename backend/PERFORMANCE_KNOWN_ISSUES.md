# Performance Known Issues (May 27, 2026)

This document tracks unresolved performance risks observed during current routing and NLP validation.

## 1) GPU Overuse Risk (NLP/BERT Side)

### Symptom
- GPU usage can stay unnecessarily high during long-lived backend sessions.
- Warmup/startup flows and repeated heavy inference calls may keep memory pressure elevated.

### Likely Triggers
- Eager model load/warmup in backend startup path.
- Missing adaptive idle policy for GPU-backed NLP engine.
- Concurrent requests hitting large model paths without bounded queueing.

### Impact
- Reduced system responsiveness under mixed traffic.
- Thermal/power cost increase on development and production hosts.
- Higher risk of OOM on machines with smaller VRAM.

### Planned Mitigations
1. Add runtime switch for delayed model warmup (on first request).
2. Add max-concurrency guard for NLP inference path.
3. Add optional CPU fallback policy when GPU memory threshold is exceeded.
4. Add telemetry fields: model load time, inference queue depth, VRAM watermark.

## 2) Slow Route Computation Risk (Routing Side)

### Symptom
- Some multimodal scenarios take significantly longer than expected.
- End-to-end compare call latency can grow when candidate combinations expand.

### Likely Triggers
- Broad candidate search radius expansion and combinatorial transfer evaluation.
- Multiple external road routing requests (OSRM) in the same compare cycle.
- Heavy mixed-option diversification when many near-equivalent routes exist.

### Impact
- Delayed UI feedback while route cards are being prepared.
- Timeouts in stress scenarios and large route spaces.

### Planned Mitigations
1. Introduce stricter per-stage time budgets and early-stop thresholds.
2. Reduce candidate fan-out with adaptive pruning by geodesic heuristics.
3. Cache transfer-walk and route-segment computations more aggressively.
4. Add structured timing logs per stage:
   - candidate discovery
   - graph shortest path
   - mixed-option assembly
   - OSRM geometry enrichment

## 3) Acceptance Targets for Next Performance Patch

- P95 `/api/multimodal/compare` latency: reduce by at least 25% from current baseline.
- GPU VRAM idle watermark: reduce by at least 30% in steady state.
- Timeout rate in stress tests: < 1%.

## 4) Status

- Status: Open (tracked)
- Priority: High
- Owner: Routing/NLP performance pass in next cycle

## 5) Implemented MVP Mitigations (2026-05-27)

- BERT eager warmup on startup is now disabled by default (`ORP_BERT_PRELOAD_ON_STARTUP` default `False`).
- NLP parse endpoint now has bounded concurrency guard (`ORP_NLP_PARSE_MAX_CONCURRENCY`) and returns controlled busy response when saturated.
- `/api/multimodal/compare` now emits stage-level API timing telemetry and applies a simple allowed-modes fan-out cap.
- `/api/multimodal/compare` now has bounded concurrency guard (`ORP_MULTIMODAL_COMPARE_MAX_CONCURRENCY`) and returns `MULTIMODAL_BUSY` when saturated.
- Multimodal engine now emits internal stage telemetry and uses config-driven transit fan-out cap (`MULTIMODAL_MAX_TRANSIT_OPTIONS`).
- Cache observability endpoint added: `GET /api/cache/stats` (graph/poi/multimodal compare cache metrics).
