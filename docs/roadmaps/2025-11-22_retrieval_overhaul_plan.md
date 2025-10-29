# Retrieval Overhaul Execution Log — 2025-11-22

## Volume I — Strategic Overview
- **Chapter 1: Objectives**
  - §1.1 Establish configurable embedding providers (HuggingFace local + OpenAI) for ingestion and retrieval parity.
  - §1.2 Replace legacy hashed embedding consumption with LlamaIndex-native retriever stack.
  - §1.3 Deliver hybrid retrieval orchestration (vector + graph + keyword) with rerankers (RRF + cross-encoder fallback).
  - §1.4 Guarantee deterministic citation packaging (doc/page context) aligned to TRD pop-out guidelines.
  - §1.5 Extend `/query` API with streaming partial answers and precision/recall operating modes.
  - §1.6 Expand regression suite for citations, pagination, reranking, filters, and streaming behaviours.
  - §1.7 Instrument telemetry for hit counts + latency suitable for dashboard ingestion.

## Volume II — Architectural Blueprint
- **Chapter 2: Embedding Provider Refactor**
  - §2.1 Retire `hashed_embedding` from runtime factories; preserve unit tests under feature flag.
  - §2.2 Extend `EmbeddingConfig` plumbing to surface provider overrides for retrieval.
  - §2.3 Implement provider bridge: HuggingFace (local inference) + OpenAI/Azure (API) with lazy dependency guards.
  - §2.4 Inject bridge into both ingestion pipeline + retrieval service initialisation (single authority module).
  - §2.5 Document deterministic fallback and environment variable controls.
- **Chapter 3: LlamaIndex Hybrid Query Engine**
  - §3.1 Design module `backend/app/retrieval/engine.py` hosting query-engine builder.
  - §3.2 Implement retriever adapters inheriting from `BaseRetriever`:
    - ¶3.2.a `VectorRetrieverAdapter` wrapping `VectorService.search` → `NodeWithScore` conversion.
    - ¶3.2.b `GraphRetrieverAdapter` emitting relation-centric nodes based on `GraphService.subgraph` + `document_store` spans.
    - ¶3.2.c `KeywordRetrieverAdapter` performing BM25-style scoring over `DocumentStore` metadata/text caches.
  - §3.3 Construct `HybridRetriever` aggregator employing Reciprocal Rank Fusion (deterministic weights).
  - §3.4 Integrate optional cross-encoder reranker (sentence-transformers) with safe fallback when dependency absent.
  - §3.5 Surface trace hooks to capture raw retriever outputs for audit + telemetry.
- **Chapter 4: Citation Packaging & Evidence Windows**
  - §4.1 Define `CitationBundle` dataclass carrying `doc_id`, `page_label`, `snippet`, `uri`, `chunk_index`.
  - §4.2 Map vector payload metadata to `page_label` (prefers explicit metadata → fallback `chunk_index + 1`).
  - §4.3 Normalise snippet extraction: highlight window ±200 chars, sentence aware when available.
  - §4.4 Ensure page-scoped grouping for timeline/graph overlays.
  - §4.5 Update serialization contract + OpenAPI models.
- **Chapter 5: `/query` API Evolution**
  - §5.1 Introduce `mode` query param (`precision`, `recall`) influencing retriever window + reranker choice.
  - §5.2 Accept `stream` flag returning `StreamingResponse` (JSONL chunks) while preserving existing 204 semantics.
  - §5.3 Emit initial metadata event → incremental answer fragments → final summary event (citations/meta).
  - §5.4 Preserve non-streaming path via shared execution core.
  - §5.5 Authorize streaming path with same guard rails + telemetry tagging.
- **Chapter 6: Telemetry Enhancements**
  - §6.1 Add counters: `retrieval_stream_chunks_total`, `retrieval_mode_queries_total` (labelled by mode/reranker).
  - §6.2 Histogram: `retrieval_partial_latency_ms` capturing time to first chunk.
  - §6.3 Propagate metrics through `/query` endpoint instrumentation (including HTTP 204 cases).
  - §6.4 Ensure metrics exported via existing OpenTelemetry setup.

## Volume III — Implementation Playbook
- **Chapter 7: Code Execution Order (Atomic Tasks)**
  - ¶7.1 Scaffold provider bridge module + adjust imports.
  - ¶7.2 Update ingestion pipeline + tests to consume new provider factory.
  - ¶7.3 Author hybrid engine adapters + integrate into `RetrievalService`.
  - ¶7.4 Refactor `RetrievalService.query` to utilise hybrid engine results; compute citations via `CitationBundle`.
  - ¶7.5 Embed reranker selection logic (RRF default, cross-encoder optional) with deterministic ordering.
  - ¶7.6 Implement streaming helpers (generator returning JSON events) + integrate into FastAPI route.
  - ¶7.7 Extend Pydantic models for citations/meta + update serialization.
  - ¶7.8 Instrument telemetry counters/histograms + register attributes.
  - ¶7.9 Update tests: `backend/tests/test_retrieval.py` (citations, pagination, reranking, filters) + `backend/tests/test_api.py` (API streaming, precision/recall, citations packaging, filters).
  - ¶7.10 Regenerate fixtures/mocks as required (vector search stubs, document store writes).
  - ¶7.11 Append stewardship log entry + ensure lint/tests executed.
- **Chapter 8: Risk & Contingency Ledger**
  - §8.1 Dependency availability — guard huggingface/cross-encoder imports with informative runtime errors + test doubles.
  - §8.2 Streaming output size — enforce chunk size limit + fallback to buffered response on failure.
  - §8.3 Telemetry cardinality — cap label permutations (mode ∈ {precision, recall}, reranker ∈ {rrf, cross_encoder}).
  - §8.4 Performance — reuse embedding/query engine per service instantiation; avoid per-request rebuild.
  - §8.5 Backwards compatibility — maintain existing JSON schema for non-streaming queries; version gating for new fields.
- **Chapter 9: Verification Matrix**
  - §9.1 Unit tests covering citation bundling + RRF determinism.
  - §9.2 API tests verifying streaming chunk order + metadata completeness.
  - §9.3 Telemetry tests ensuring counters increment under stubbed meter.
  - §9.4 Manual sanity script for hybrid retriever (optional, documented but not executed here).

## Volume IV — Documentation & Hand-off
- **Chapter 10: Repo Hygiene Actions**
  - §10.1 Update `AGENTS.md` stewardship log post-implementation.
  - §10.2 Document new `/query` params + streaming contract within `docs/` (follow-up ticket if scope exceeds current window).
  - §10.3 Summarise telemetry metrics in `build_logs/` entry aligned with execution date.

