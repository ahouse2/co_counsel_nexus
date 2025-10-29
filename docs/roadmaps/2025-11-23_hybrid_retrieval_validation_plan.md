# 2025-11-23 — Hybrid Retrieval Validation Reinforcement Roadmap

## 1. Vision
- **Objective:** Cement confidence in hybrid retrieval stack by codifying deterministic behaviours for fusion, streaming, and telemetry pathways.
- **Success Criteria:**
  - Tests assert fusion provenance metadata, streaming cadence sequencing, and deterministic citation envelopes.
  - Documentation maps validation lattice to operational telemetry counters for dashboard parity.

## 2. Strategic Pillars
### 2.1 Retrieval Fusion Analytics
- Validate reciprocal-rank fusion ordering and retriever provenance stamps.
- Simulate cross-encoder guard rails to guarantee graceful fallback semantics.
- Instrument regression hooks for future scorer plug-ins (placeholder-free; enforce concrete assertions).

### 2.2 Streaming Determinism
- Extend stream event expectations (meta → partial deltas → final) with strict sequencing assertions.
- Calibrate chunk sizing knobs for predictable replay in load tests.

### 2.3 Telemetry Correlation
- Map counter/histogram emissions to QA checkpoints ensuring latency + chunk counters stay monotonic.
- Prepare harness notes for synthetic OpenTelemetry exporters (implementation deferred until dedicated observability sprint).

## 3. Execution Lattice
### 3.1 Phase A — Test Harness Augmentation
- Draft adapter doubles for vector/graph/keyword retrievers to assert fusion provenance.
- Encode regression verifying per-result `retrievers` payload and `fusion_score` ordering.
- Simulate cross-encoder absence with deterministic fallback assertions.

### 3.2 Phase B — Streaming Envelope Assertions
- Tighten API streaming test to assert ordered JSONL frames and inclusion of at least one partial delta.
- Guarantee final frame replays citation payload verbatim.

### 3.3 Phase C — Telemetry Hooks Audit
- Trace current histogram/counter invocations, noting metric names + attribute cartography.
- Outline shadow exporter scaffolding for subsequent observability work.

## 4. Quality Gates
- **Automated:** `pytest backend/tests/test_retrieval.py -q`, `pytest backend/tests/test_api.py -q`, `pytest backend/tests/test_retrieval_engine.py -q`.
- **Manual:**
  - Inspect OpenTelemetry counter wiring for naming drift.
  - Review streaming payload transcripts for JSON schema adherence.

## 5. Decision Ledger
- Cross-encoder reranking remains optional; fall back to RRF when dependency absent.
- Streaming remains JSONL-first to align with pop-out UI expectations; SSE deferment documented.

## 6. Handoff Notes
- Future work: integrate synthetic exporter harness once observability sprint scheduled.
- Maintain deterministic local embeddings for CI; no remote model downloads permitted.
