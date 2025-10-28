# Phase 6 — Timeline Orchestration Roadmap

## 1. Mission Profile
- Deliver a resilient `/timeline` service that synthesises graph-derived events, persists deterministic histories, and exposes filterable, paginated APIs for agents and UI clients.
- Harden supporting systems (stores, graph queries, agents) so that multi-agent workflows can depend on timeline accuracy and availability.

## 2. Decision Tree Overview
- **2.1 Data Provenance**
  - 2.1.1 Use ingestion-produced events as authoritative records; enrich via graph entity lookups for filtering.
  - 2.1.2 Reject ad-hoc timeline synthesis without citations — maintains forensic traceability.
- **2.2 Delivery Mechanics**
  - 2.2.1 Cursor-based pagination vs. offset pagination → choose opaque cursor to guarantee deterministic ordering across app restarts.
  - 2.2.2 Filter semantics: timestamp range (from/to), entity scoping, and page sizing.
  - 2.2.3 Error handling: malformed cursors → 400; missing entity mappings → exclude silently to avoid leaking data scope.
- **2.3 Agent Integration**
  - 2.3.1 TimelineAgent consumes `/timeline` endpoint for case threads.
  - 2.3.2 ResearchAgent cross-checks timeline events with graph neighbors before drafting answers.
  - 2.3.3 QAAgent validates pagination metadata to ensure coverage.
- **2.4 Observability + Resilience**
  - 2.4.1 Emit telemetry counters for events served; log cursor transitions for replay.
  - 2.4.2 Guard against corrupt JSONL lines with defensive parsing.

## 3. Implementation Phases (Nested)
- **3.1 Storage Enhancements**
  - 3.1.1 Keep JSONL format; ensure append path exists (already satisfied).
  - 3.1.2 Provide deterministic sorting and filtering purely in service layer to avoid format churn.
- **3.2 Graph Service Augmentation**
  - 3.2.1 Add `document_entities(doc_ids)` method for Neo4j + in-memory modes.
  - 3.2.2 Normalise entity identifiers and surface labels for downstream summaries.
- **3.3 Timeline Service Logic**
  - 3.3.1 Introduce query DTO capturing cursor, limit, timestamp bounds, entity filter.
  - 3.3.2 Implement base64 cursor encode/decode using `(ts, id)` tuple.
  - 3.3.3 Filter pipeline order: time range → entity scope → cursor → slicing.
  - 3.3.4 Return structured result containing events + pagination metadata.
- **3.4 API Surface**
  - 3.4.1 Extend FastAPI route to accept query parameters with validation bounds (limit 1–100).
  - 3.4.2 Map query result into `TimelineResponse` with `meta` payload.
  - 3.4.3 Translate service `ValueError` into `400 Bad Request`.
- **3.5 Agent + Task Alignment**
  - 3.5.1 Update master task list with detailed agent coding steps (QA coverage, telemetry, fallback flows).
  - 3.5.2 Document new responsibilities for TimelineAgent within task list and roadmap.
- **3.6 Verification**
  - 3.6.1 Extend API tests for pagination, timestamp filters, entity scoping, cursor validation.
  - 3.6.2 Ensure regression coverage for ingestion -> timeline count remains.

## 4. Validation Checklist
- ✅ `pytest backend/tests/test_api.py -q`
- ✅ `pytest backend/tests/test_agents.py -q`
- ✅ `pytest backend/tests/test_triples.py -q`
- ✅ Manual spot-check of timeline JSONL after ingestion for sorted order.

## 5. Notes & Contingencies
- If Neo4j backend becomes primary, reuse same query method; ensure session pooling.
- Future work: introduce caching layer (Redis) keyed by `(case_id, entity, cursor)` once throughput demands increase.
- Maintain compatibility with existing agents by keeping event schema stable; new pagination metadata is additive.
