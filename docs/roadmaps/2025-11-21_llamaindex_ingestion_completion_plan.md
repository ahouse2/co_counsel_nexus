# 2025-11-21 — LlamaIndex Ingestion Completion Plan

## 0. Meta
- ### 0.1. Objectives
  - #### 0.1.1. Restore optional LlamaIndex import resilience while keeping fallbacks deterministic.
  - #### 0.1.2. Complete ingestion orchestration (vector, graph, worker) per roadmap §4 items 2–10.
  - #### 0.1.3. Ship green ingestion test suite covering OCR/sharepoint/chroma fallbacks.
  - #### 0.1.4. Instrument pipeline metrics and append stewardship artefacts (AGENTS log, build log entry).
- ### 0.2. Constraints & Signals
  - #### 0.2.1. No placeholder implementations; each fallback must be feature-complete for offline mode.
  - #### 0.2.2. Preserve hashed embedding deterministic outputs for non-LlamaIndex environments.
  - #### 0.2.3. Maintain backward compatibility for existing ingestion API + worker queues.

## 1. Environment & Dependency Verification
- ### 1.1. Inspect current import failures
  - #### 1.1.1. Reproduce pytest import error; capture stack for plan validation (skip running until fixes ready to avoid noise).
- ### 1.2. Dependency guards
  - #### 1.2.1. Map modules requiring optional imports (llama_index, chromadb, pytesseract, docx).
  - #### 1.2.2. Decide lazy import vs. importlib guards for each module (Document, SentenceSplitter, embeddings, hub loaders).

## 2. Fallback Integration & Loader Registry Stabilisation
- ### 2.1. Harmonise fallback primitives
  - #### 2.1.1. Extend `fallback.py` exports if additional helpers (e.g., `MetadataModeEnum`) required downstream.
- ### 2.2. Loader registry refactor
  - #### 2.2.1. Replace direct `Document`/`MetadataMode` imports with optional import logic.
  - #### 2.2.2. Use fallback Document + metadata mode when llama_index unavailable.
  - #### 2.2.3. Ensure LlamaHub loaders gracefully degrade: skip if module missing, raise actionable error.
  - #### 2.2.4. Guarantee `LoadedDocument.document` type uniform via Protocol or duck typing for fallback.
- ### 2.3. PDF/email/image handlers
  - #### 2.3.1. Validate OCR metadata injection works for fallback Document.
  - #### 2.3.2. Ensure checksums computed identically for bytes/text (dedupe support).

## 3. Pipeline Orchestration & Embedding Factory
- ### 3.1. Sentence splitter abstraction
  - #### 3.1.1. Update factory to return fallback splitter when LlamaIndex absent.
  - #### 3.1.2. Guarantee returned splitter exposes `get_nodes_from_documents` for fallback documents.
- ### 3.2. Embedding model selection
  - #### 3.2.1. Wrap HuggingFace/OpenAI/Azure imports with availability guards + explicit error messages.
  - #### 3.2.2. Ensure deterministic hash embedding respects configured dimensions from runtime.
- ### 3.3. Pipeline chunk processing
  - #### 3.3.1. Swap `MetadataMode.ALL`/`TextNode` dependencies for fallback-friendly equivalents.
  - #### 3.3.2. Confirm entity/triple extraction uses raw text (no LlamaIndex dependency).
  - #### 3.3.3. Guarantee nodes produce metadata when fallback types used (attribute parity tests).

## 4. Service Wiring & Persistence
- ### 4.1. Ingestion service
  - #### 4.1.1. Inject updated loader/pipeline usage; verify checksum dedupe + job transitions unaffected.
  - #### 4.1.2. Confirm vector + graph persistence flows accept fallback node metadata.
- ### 4.2. Vector service
  - #### 4.2.1. Audit `_chroma_collection` creation for all execution paths; ensure attributes exist.
  - #### 4.2.2. Add explicit lazy import error messaging when chromadb missing but backend configured.
  - #### 4.2.3. Validate Chroma search returns deterministic `ScoredPoint` objects.
- ### 4.3. Graph service integration
  - #### 4.3.1. Ensure GraphService persists LlamaIndex graph builder output (entity/triple ingestion) with dedupe semantics.
  - #### 4.3.2. Map pipeline triple metadata to Neo4j persistence payloads.

## 5. Worker Hardening & Incremental Re-index
- ### 5.1. Ingestion worker adjustments
  - #### 5.1.1. Extend worker to handle incremental re-index (checksum comparison before enqueue).
  - #### 5.1.2. Implement retry/backoff behaviour with failure recovery metadata (status transitions).
  - #### 5.1.3. Add logging hooks for dedupe decisions + pipeline metrics.
- ### 5.2. Failure telemetry
  - #### 5.2.1. Persist failure causes to job store timeline for observability dashboards.

## 6. Metrics & Observability
- ### 6.1. Metrics instrumentation
  - #### 6.1.1. Verify `metrics.py` exposes OTEL counters/histograms for load/node counts.
  - #### 6.1.2. Add status transition events capturing worker stage durations.
- ### 6.2. Dashboards alignment
  - #### 6.2.1. Ensure metrics labels match dashboard expectations (source_type, job_id).

## 7. Test Suite Expansion
- ### 7.1. Fixture updates
  - #### 7.1.1. Update `backend/tests/conftest.py` for fallback embeddings + chroma temp dirs.
- ### 7.2. Test scenarios
  - #### 7.2.1. Validate local workspace ingestion with hashed embeddings + OCR fallback.
  - #### 7.2.2. Cover SharePoint/OneDrive connectors with mocked LlamaHub imports.
  - #### 7.2.3. Add OCR edge case tests ensuring patched pytesseract path aligns post-refactor.
  - #### 7.2.4. Include chroma backend tests verifying upsert/search flows.

## 8. Verification & Stewardship
- ### 8.1. Static quality pass
  - #### 8.1.1. Self-review diff thrice focusing on optional import paths.
  - #### 8.1.2. Run `ruff check backend` and `mypy --config-file mypy.ini backend` if feasible.
- ### 8.2. Test execution
  - #### 8.2.1. Run `PYTHONPATH=. pytest backend/tests/test_ingestion_async.py backend/tests/test_ingestion_connectors.py -q`.
  - #### 8.2.2. Run full backend suite if time permits.
- ### 8.3. Artefact updates
  - #### 8.3.1. Append stewardship entry to root `AGENTS.md` log.
  - #### 8.3.2. Update `build_logs/<date>.md` if required by instructions (review prior conventions).
  - #### 8.3.3. Prepare ACE trio notes (Retriever/Planner/Critic) if process artefact mandated.

## 9. Contingency Considerations
- ### 9.1. If LlamaHub unavailable
  - #### 9.1.1. Implement graceful error with actionable remediation steps.
- ### 9.2. If chromadb import fails
  - #### 9.2.1. Auto-fallback to in-memory with warning + metric flag (document in job status).
- ### 9.3. If Neo4j unreachable
  - #### 9.3.1. Queue graph mutations for retry via worker persistence (future enhancement note).

