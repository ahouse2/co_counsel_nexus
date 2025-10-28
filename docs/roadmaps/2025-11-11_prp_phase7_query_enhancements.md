# Roadmap — PRP Phase 7 Retrieval Enhancements (2025-11-11)

## 0. Orientation
- ### 0.1 Objectives
  - #### 0.1.1 Align backend `/query` implementation with PRP spec pagination/filtering/rerank requirements.
    - ##### 0.1.1.1 Ensure new query parameters (`page`, `page_size`, `filters[source]`, `filters[entity]`, `rerank`) are validated and wired through FastAPI.
    - ##### 0.1.1.2 Persist provenance metadata (`source_type`, entity descriptors) during ingestion to unlock filtering and scoring logic.
    - ##### 0.1.1.3 Extend retrieval service with deterministic reranking + response metadata (`meta.page`, `meta.page_size`, `meta.total_items`, `meta.has_next`).
  - #### 0.1.2 Deliver regression coverage for new behaviours (pagination windowing, entity/source filters, rerank boost path, 204 guardrail).

- ### 0.2 Inputs
  - #### 0.2.1 Specs: `docs/AgentsMD_PRPs_and_AgentMemory/PRPs/PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_spec.md` (§GET /query).
  - #### 0.2.2 Existing implementations: `backend/app/services/ingestion.py`, `backend/app/services/retrieval.py`, `backend/app/main.py`, `backend/app/models/api.py`, `backend/tests/test_api.py`.
  - #### 0.2.3 Tooling baseline: Qdrant in-memory index, GraphService memory path, ForensicsService artifacts.

## 1. Data Foundation Adjustments (Ingestion Path)
- ### 1.1 Payload Metadata Expansion
  - #### 1.1.1 Update `_ingest_materialized_source` to derive `source_type = materialized.source.type.lower()` once per source.
    - ##### 1.1.1.1 Pass `source_type` into `_ingest_text`, image, and financial registration pathways.
  - #### 1.1.2 Refactor `_register_document` signature to accept `source_type: str` plus optional `extra_metadata`.
    - ##### 1.1.2.1 Add `source_type` to metadata stored in DocumentStore and GraphService document nodes.
    - ##### 1.1.2.2 Preserve compatibility for non-text artifacts (image/financial) by passing empty `extra_metadata`.
  - #### 1.1.3 Introduce helper `_update_document_metadata(doc_id, metadata_updates)` to merge derived fields (entity sets, chunk counts).
    - ##### 1.1.3.1 After entity extraction in `_ingest_text`, call helper to persist `entity_ids`, `entity_labels`, `chunk_count`.

- ### 1.2 Vector Payload Enrichment
  - #### 1.2.1 When building chunk payloads, attach `source_type`, `doc_type`, `entity_ids`, `entity_labels`, and `origin`.
    - ##### 1.2.1.1 Ensure entity label collection deduplicates and preserves deterministic ordering.
  - #### 1.2.2 Maintain hashed embeddings + chunk indexes unchanged.

## 2. Retrieval Service Evolution
- ### 2.1 Configuration Support
  - #### 2.1.1 Extend `Settings` with `retrieval_max_search_window: int = 60` and `retrieval_graph_hop_window: int = 12`.
    - ##### 2.1.1.1 Ensure directories prep unaffected; update tests that rely on settings defaults.

- ### 2.2 Data Structures
  - #### 2.2.1 Introduce dataclasses `QueryMeta` and `QueryResult` with `to_dict()` helpers (mirroring `Trace`/`Citation`).
    - ##### 2.2.1.1 Add boolean `has_evidence` flag for 204 routing decision.

- ### 2.3 Query Pipeline Enhancements
  - #### 2.3.1 Adjust `RetrievalService.query` signature to accept keyword-only args: `page`, `page_size`, `filters`, `rerank`.
    - ##### 2.3.1.1 Validate `page_size` vs settings window (raise `ValueError` for oversize or zero results windows).
    - ##### 2.3.1.2 Normalise filter inputs (`source` lower-case, trimmed; `entity` stripped).
  - #### 2.3.2 Fetch vector results using `search_window = min(max_window, page * page_size * 2)` to provide cushion for filtering.
    - ##### 2.3.2.1 Rerank path: compute deterministic boost factoring entity matches, entity count, forensics availability.
    - ##### 2.3.2.2 Non-rerank path: maintain original score ordering.
  - #### 2.3.3 Filtering logic
    - ##### 2.3.3.1 Source filter: require payload `source_type` match; fallback to DocumentStore metadata when missing.
    - ##### 2.3.3.2 Entity filter: match case-insensitive substring against payload `entity_labels` or normalized `entity_ids`; fallback to GraphService `document_entities` if payload absent.
  - #### 2.3.4 Pagination slicing
    - ##### 2.3.4.1 Compute `start = (page-1)*page_size`, `end = start + page_size`; derive `page_results` & `has_next`.
    - ##### 2.3.4.2 When `filtered` empty → construct `QueryResult` with `has_evidence=False`.
    - ##### 2.3.4.3 When `page_results` empty but `filtered` non-empty → return informational answer + empty traces but `has_evidence=True`.
  - #### 2.3.5 Trace + Answer composition
    - ##### 2.3.5.1 Build citations/traces using `page_results` (vector, graph, forensics) while computing answer from `filtered[:page_size]`.
    - ##### 2.3.5.2 Ensure meta uses total filtered size.

## 3. API Surface + Models
- ### 3.1 Pydantic Model Updates
  - #### 3.1.1 Create `QueryPaginationModel` with validation constraints (page ≥1, page_size 1–50, total_items ≥0, has_next bool).
  - #### 3.1.2 Add `meta: QueryPaginationModel` to `QueryResponse`.
  - #### 3.1.3 Update `TraceModel.vector`/`graph` definitions if necessary to accept defaults consistent with new usage.

- ### 3.2 FastAPI Endpoint Wiring
  - #### 3.2.1 Update `/query` handler signature to include `page`, `page_size`, `filters[source]`, `filters[entity]`, `rerank` parameters with validation (`min_length=3` for `q`).
  - #### 3.2.2 Invoke `RetrievalService.query` with constructed filters dict; catch `ValueError` for 400 conversion.
  - #### 3.2.3 Return HTTP 204 (empty body) when `QueryResult.has_evidence` false; otherwise respond with JSON (including meta).
  - #### 3.2.4 Ensure response_model matches new schema.

## 4. Regression Coverage
- ### 4.1 Test Augmentation (`backend/tests/test_api.py`)
  - #### 4.1.1 Enhance `test_ingestion_and_retrieval` assertions for `meta` structure (`page=1`, `page_size=10`, `total_items>=1`, `has_next` bool).
  - #### 4.1.2 Add dedicated `test_query_filters_and_pagination` verifying:
    - ##### 4.1.2.1 `page_size=1` yields correct slicing + `has_next` true.
    - ##### 4.1.2.2 `filters[source]=local` retains evidence; `filters[source]=s3` triggers 204.
    - ##### 4.1.2.3 `filters[entity]` matches `Acme` and excludes mismatched label.
    - ##### 4.1.2.4 Rerank toggles reorder results deterministically (assert top citation doc ID equality across rerank).
    - ##### 4.1.2.5 Requesting page beyond range returns 200 with informative answer + `meta.has_next=False` and empty vector trace.
  - #### 4.1.3 Add 204 expectation check via `rerank` or `filters` when evidence missing.

## 5. Documentation & Stewardship
- ### 5.1 Update `docs/AgentsMD_PRPs_and_AgentMemory/PRPs/PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_tasks.md`
  - #### 5.1.1 Mark `/query Enhancements` checklist item as complete with note referencing files/tests.

- ### 5.2 Build Log Entry
  - #### 5.2.1 Append `build_logs/2025-11-11.md` summarizing work, ACE loop, and tests run.

- ### 5.3 ACE Memory Update
  - #### 5.3.1 Append JSONL record to `memory/ace_state.jsonl` capturing retriever/planner/critic highlights & CI results.

- ### 5.4 Chain of Stewardship
  - #### 5.4.1 Add entry to repository `AGENTS.md` log with timestamp, tasks, files, tests, rubric notes.

## 6. Validation & Review
- ### 6.1 Automated Tests
  - #### 6.1.1 Run `pytest backend/tests -q` ensuring new scenarios covered.
- ### 6.2 Manual Audit
  - #### 6.2.1 Inspect diff for metadata persistence/regression safety.
  - #### 6.2.2 Verify new query responses via unit tests reflect rerank/pagination semantics.

## 7. Finalisation
- ### 7.1 Prepare PR summary referencing spec alignment & tests.
- ### 7.2 Ensure citations ready for final response (key files + tests output chunk IDs).
- ### 7.3 Commit changes, update PR, deliver final report.
