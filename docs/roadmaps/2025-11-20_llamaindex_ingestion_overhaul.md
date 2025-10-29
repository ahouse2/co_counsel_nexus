# LlamaIndex Ingestion Overhaul — Execution Roadmap

## 0 · Orientation / Decision Tree Roots
- ### 0.1 · Mission Statement
  - deliver production-grade LlamaIndex ingestion orchestrations covering multimodal capture, OCR, embeddings, and graph persistence without placeholders.
- ### 0.2 · Guardrails & Constraints
  - honour TRD cost-modes (community / pro / enterprise) with adaptive embedding + OCR choices.
  - integrate with existing Qdrant/Chroma + Neo4j stores, asynchronous worker, telemetry, and tests.
  - maintain audit, security, and ACE instrumentation expectations from repo AGENTS.

## 1 · Repository Cartography (“Book” Level)
- ### 1.1 · Backend Ingestion Package (`backend/ingestion/`)
  - housing llama-index configuration, loader registries, pipeline orchestrators.
- ### 1.2 · Service Integrations (`backend/app/services/*.py`)
  - updating ingestion service, worker, graph + vector coordination, metrics.
- ### 1.3 · Persistence & Storage (`backend/app/storage/**`)
  - ensuring new metadata persistence surfaces exist / are extended.
- ### 1.4 · Tests (`backend/tests/test_ingestion_*.py`)
  - regression coverage for OCR, connectors, incremental reindex.
- ### 1.5 · Observability (`backend/app/telemetry/**`)
  - metrics + status transitions.
- ### 1.6 · Documentation & Stewardship (AGENTS log, roadmap)
  - append stewardship entry, record rationale.

## 2 · Chapter Breakdown per Book
- ### 2.1 · Backend Ingestion Package
  - #### 2.1.1 · `settings.py`
    - define Pydantic models for cost-mode dependent embedding & OCR providers.
  - #### 2.1.2 · `llama_index_factory.py`
    - build `LlamaIndexConfig`, global registry for embeddings, LLMs, node/post processors.
  - #### 2.1.3 · `loader_registry.py`
    - map source descriptors -> LlamaHub loaders (PDF, Email, SharePoint, OneDrive, S3, CourtListener).
  - #### 2.1.4 · `pipeline.py`
    - orchestrate load → preprocess → chunk → index; expose `run_ingestion_pipeline`.
  - #### 2.1.5 · `ocr.py`
    - integrate Tesseract (local) and vision model (remote) options with auto selection.
  - #### 2.1.6 · `metrics.py`
    - emit ingest metrics (duration, bytes, nodes) via telemetry interface.
  - #### 2.1.7 · `__init__.py`
    - export high-level orchestrator + settings dataclasses.

- ### 2.2 · Service Integrations
  - #### 2.2.1 · `backend/app/config.py`
    - embed ingestion settings: cost mode enum, provider API keys, toggles.
  - #### 2.2.2 · `backend/app/services/ingestion.py`
    - enqueue pipeline tasks, persist results, handle OCR/embedding config.
  - #### 2.2.3 · `backend/app/services/ingestion_worker.py`
    - track job states, dedupe via checksum, incremental reindex scheduling, recovery.
  - #### 2.2.4 · `backend/app/services/graph.py`
    - expose graph persistence helper for LlamaIndex graph builder output.
  - #### 2.2.5 · `backend/app/services/vector.py`
    - accept externally generated embeddings metadata for Qdrant/Chroma.
  - #### 2.2.6 · `backend/app/services/__init__.py`
    - wire ingestion orchestrator imports if required.

- ### 2.3 · Storage Adjustments
  - #### 2.3.1 · Node/vector persistence updates (Qdrant, Chroma fallback).
  - #### 2.3.2 · Document store metadata (checksums, OCR traces).
  - #### 2.3.3 · Graph service: entity/relation persistence to Neo4j.

- ### 2.4 · Telemetry & Metrics
  - #### 2.4.1 · Add ingestion metrics to telemetry exporters.
  - #### 2.4.2 · Capture state transitions for dashboards.

- ### 2.5 · Tests & Fixtures
  - #### 2.5.1 · Expand fixtures for SharePoint/OneDrive mocks using recorded transcripts.
  - #### 2.5.2 · Add OCR edge-case sample images + expected text.
  - #### 2.5.3 · Validate incremental reindex & checksum dedupe.
  - #### 2.5.4 · Assert graph entities/relations stored.

## 3 · Paragraph-Level Tasks
- ### 3.1 · Implement ingestion settings models
  - encode TRD cost modes mapping to embedding + OCR provider choices.
  - support environment overrides for provider keys / endpoints.
- ### 3.2 · Build OCR abstraction (local/remote)
  - integrate pytesseract for PDFs/images; fallback to remote vision via HTTP.
  - expose structured output with confidences for telemetry.
- ### 3.3 · Loader registry integration
  - register LlamaHub loaders (PDF, Email, SharePoint, OneDrive, IMAP, Google Drive etc.).
  - wrap connectors with workspace materialisation from existing `ingestion_sources`.
- ### 3.4 · Pipeline orchestration
  - instantiate LlamaIndex `IngestionPipeline` with chunking per settings.
  - ensure nodes + metadata persisted via vector + document stores.
  - graph builder extraction -> GraphService (Neo4j) persistence.
- ### 3.5 · Queue integration
  - update worker to accept structured payload referencing pipeline config + materialised paths.
  - implement checksum dedupe using stored document metadata.
  - include retry/backoff with failure journal.
- ### 3.6 · Metrics & state transitions
  - integrate with telemetry counters/histograms; update job records.
- ### 3.7 · Tests
  - create synthetic docs/emails/pdfs and OCR images to exercise pipeline.
  - mock LlamaHub connectors for remote sources; ensure fixtures align with TRD connectors.

## 4 · Sentence-Level Steps (Detailed Execution Order)
1. Extend configuration (`config.py`) with cost mode enums + provider secrets, update settings tests if present.
2. Scaffold `backend/ingestion/` package modules per sections 2.1 & 3, implementing full functionality using llama_index APIs.
3. Update ingestion sources/materialisation to interact with loader registry.
4. Refactor `IngestionService` to hand off to new pipeline orchestrator, ensuring queue payload contains job_id, sources, and resolved connectors; persist nodes/vectors to Qdrant/Chroma via vector service.
5. Enhance `IngestionWorker` for incremental reindex, dedupe, failure recovery (persist resume tokens to job store).
6. Implement GraphService extensions for entity/relation persistence (Neo4j writes with MERGE semantics) using pipeline outputs.
7. Integrate OCR + embeddings selection; ensure TRD cost modes map to HuggingFace vs OpenAI embeddings.
8. Emit telemetry metrics + job status transitions.
9. Refresh backend tests with new fixtures covering OCR, SharePoint/OneDrive, pipeline flows.
10. Update stewardship log and ensure ACE/memory artefacts if required.

## 5 · Word-Level Notes (Implementation Nuances)
- use llama_index `download_loader` from LlamaHub with caching in workspace.
- adopt `SentenceSplitter` chunking aligning with settings chunk size/overlap.
- encode OCR results into document metadata for dedupe + auditing.
- compute SHA256 digests of raw bytes pre/post OCR for incremental detection.
- when embeddings provider is OpenAI, respect rate limiting via async pipeline; for HuggingFace use `HuggingFaceEmbedding` with offline model path support.
- graph persistence: leverage `GraphService.upsert_entities_relations` (implement if missing) to persist nodes/edges and store triple counts.
- instrumentation: record metrics via telemetry module (histograms for duration, counters for ingested nodes, gauge for queue depth).

## 6 · Character-Level Checklists
- [ ] New package modules fully typed with docstrings.
- [ ] No placeholders; all connectors implemented with actual logic or deterministic fakes for tests.
- [ ] Tests deterministic; use local assets under `backend/tests/data/`.
- [ ] Telemetry integration respects existing OpenTelemetry wrappers.
- [ ] Update `backend/requirements.txt` with llama-index, pytesseract, OCR dependencies.
- [ ] Document plan execution in stewardship log entry upon completion.

