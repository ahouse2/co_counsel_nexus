name: "Tasks — Co-Counsel MVP"
status: draft

> **PRP Navigation:** [Base](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_base.md) · [Planning](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_planning.md) · [Spec](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_spec.md) · [Tasks](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_tasks.md) · [Pre-PRP Plan](PRE_PRP_PLAN.md) · [ACE Execution Guide](EXECUTION_GUIDE_ACE.md) · [Task List Master](TASK_LIST_MASTER.md) · [PRP Templates](templates/README.md)

## Phase 1 — Foundation
**Owner:** Platform Core Guild — Priya Raman  
**Duration Estimate:** 8 engineer-days  
**Prerequisites:** Baseline repo scaffolding complete (Roadmap Phase 0)  
**Roadmap Milestone Alignment:** Roadmap Phase 1 — Data Foundations  
**CI/CD Checkpoint:** `foundation-smoke` workflow (lint, type-check, config bootstrap)  
**Exit Criteria:** Service boots with configuration + logging, storage clients pingable, placeholder APIs returning 501, telemetry exported to collector stub.

- [ ] **Environment & Telemetry Wiring** — Materialize `.env.example`, settings objects, logging, and OpenTelemetry exporters per Spec §APIs (service contracts demand structured logs for `/ingest`, `/query`, `/timeline`).
- [ ] **Storage Driver Shims** — Instantiate Qdrant (vector) and Neo4j (graph) connectors with readiness checks, aligning with Spec §APIs.GET /query trace payload expectations.
- [ ] **API Skeleton** — Scaffold FastAPI routers for `/ingest`, `/ingest/{job_id}`, `/query`, `/timeline` mirroring Spec §§APIs.POST /ingest, GET /ingest/{job_id}, GET /query, GET /timeline schemas with stub implementations.

## Phase 2 — Ingestion
**Owner:** Data Pipelines Squad — Mateo Alvarez  
**Duration Estimate:** 12 engineer-days  
**Prerequisites:** Phase 1 exit criteria; document fixtures available  
**Roadmap Milestone Alignment:** Roadmap Phase 2 — Ingestion MVP  
**CI/CD Checkpoint:** `ingestion-e2e` workflow (loader unit tests + `/ingest` contract tests)  
**Exit Criteria:** `/ingest` end-to-end flow populates storage, OCR + classification metadata persists, embeddings stored with schema-compliant metadata, retry + error codes match spec.

- [ ] **Source Connectors (Spec §APIs.POST /ingest → IngestionSource)**
  - [ ] Implement local folder ingest honoring mount validations.
  - [ ] Wire SharePoint/S3 credential lookups respecting `credRef` constraints.
- [ ] **Submission Lifecycle (Spec §APIs.POST /ingest & GET /ingest/{job_id})**
  - [ ] Queue jobs, persist `job_id`, emit lifecycle timestamps.
  - [ ] Provide polling endpoint that surfaces `status`, `errors`, and timestamps exactly as defined.
- [ ] **Document Normalization (Spec §APIs.POST /ingest → Request Schema)**
  - [ ] Canonicalize filenames, MIME detection, and store `metadata` entries for downstream pipelines.
- [ ] **OCR & Vision Classification (Spec §Forensics Toolbox Execution Blueprint prerequisites)**
  - [ ] Integrate Tesseract-based OCR for scanned PDFs/images.
  - [ ] Invoke Vision-LLM tagging agent to pre-label artifacts (`status_details.ingestion.tags`).
- [ ] **Chunking & Embeddings (Spec §APIs.GET /query → traces.vector)**
  - [ ] Segment documents using HF BGE-small default, persisting chunk IDs.
  - [ ] Store embedding vectors in Qdrant with metadata fields required by trace responses.
- [ ] **Vector Persistence (Spec §APIs.GET /query → TraceModel)**
  - [ ] Ensure metadata includes `docId`, `score` placeholders, and ingestion timestamps for retrieval audit.

## Phase 3 — GraphRAG
**Owner:** Knowledge Graph Team — Dr. Eun-Ji Park  
**Duration Estimate:** 10 engineer-days  
**Prerequisites:** Phase 2 exit criteria; Neo4j cluster credentials provisioned  
**Roadmap Milestone Alignment:** Roadmap Phase 3 — Context Engine  
**CI/CD Checkpoint:** `graph-rag` workflow (Cypher unit tests + ontology snapshot checks)  
**Exit Criteria:** Triples extracted into Neo4j, ontology seeding complete, ID normalization consistent, hybrid retriever returns combined vector/graph traces.

- [ ] **Triple Extraction (Spec §Forensics Toolbox Execution Blueprint → prerequisite graph context)**
  - [ ] Author prompt templates + parsers generating `(subject, predicate, object)` from ingestion outputs.
- [ ] **Graph Upsert Utilities (Spec §APIs.GET /query → traces.graph)**
  - [ ] Implement Cypher upserts with constraint enforcement and deduplication.
- [ ] **Ontology Seeding (Spec §Forensics Nodes dependency)**
  - [ ] Bootstrap legal entity taxonomy and timeline relationships.
- [ ] **ID Normalization (Spec §APIs.GET /query → citations & nodes)**
  - [ ] Synchronize document IDs across vector + graph stores.
- [ ] **Hybrid Retriever (Spec §APIs.GET /query)**
  - [ ] Merge vector + graph results into unified `QueryResponse.traces` payloads.

## Phase 4 — Forensics Core (Non‑Negotiable)
**Owner:** Forensic Intelligence Guild — Naomi Okafor  
**Duration Estimate:** 20 engineer-days  
**Prerequisites:** Phase 3 exit criteria; forensic fixtures (documents, media, ledgers) curated  
**Roadmap Milestone Alignment:** Roadmap Phase 4 — Forensics Core  
**CI/CD Checkpoint:** `forensics-suite` workflow (pipeline order tests, modality-specific regression packs)  
**Exit Criteria:** Toolbox orchestrates per spec order, reports versioned under storage path, `/forensics/*` APIs return spec-compliant payloads, telemetry + trace hooks operational.

### 4.1 Toolbox Orchestration & Storage
- [ ] Implement canonicalization → metadata → analyzer orchestration respecting Spec §Forensics Toolbox Execution Blueprint stage order.  
  **Deliverable:** `tests/forensics/test_pipeline_order.py` validates sequencing fixtures.
- [ ] Persist reports to `./storage/forensics/{fileId}/report.json` with schema versioning mandated in Spec §Forensics Storage.  
  **Deliverable:** CLI `python -m backend.tools.forensics dump --id sample-doc` emits compliant JSON.

### 4.2 Document Forensics
- [ ] Hashing (SHA‑256 + TLSH) and PDF/DOCX/MSG metadata extraction using `hashlib`, `tlsh`, `python-magic`, `pypdf`, `python-docx`, `extract-msg` to satisfy Spec §Forensics Nodes → DocumentForensicsAgent outputs.  
  **Deliverable:** Unit tests cover PDF, DOCX, MSG fixtures with expected hashes + metadata snapshots.
- [ ] Structure + authenticity analysis (TOC, signatures, header diffs) via `unstructured`, `pikepdf`, `mailparser` to populate Spec §ForensicsResponse `signals`.  
  **Deliverable:** Golden JSON `build_logs/forensics/document/sample_report.json` showing populated `signals` + `summary`.

### 4.3 Image Forensics
- [ ] EXIF harvesting with `Pillow`/`piexif` plus ELA and clone detection via `opencv-python`, `numpy`, `imagededup`, `pyprnu` delivering Spec §Forensics Nodes → ImageForensicsAgent metrics.  
  **Deliverable:** Regression notebook `notebooks/forensics/image_qa.ipynb` (executed to HTML) evidencing tamper detection.
- [ ] Implement fallback path for unsupported/low-resolution imagery, surfacing `fallback_applied` + coverage signal required by Spec §ForensicsResponse.  
  **Deliverable:** Integration test triggers fallback and asserts API returns HTTP `415` when analyzer unavailable.

### 4.4 Financial Forensics
- [ ] Tabular ingestion with `pandas`/`pyarrow`, totals reconciliation using `decimal` to output Spec §Forensics Nodes → FinancialForensicsAgent metrics.  
  **Deliverable:** Automated check verifying accounting identities on synthetic ledger fixture.
- [ ] Isolation Forest anomaly detection with `scikit-learn` and z-score fallback for small datasets ensuring Spec §ForensicsResponse anomaly representation.  
  **Deliverable:** Store artifact `build_logs/forensics/financial/anomaly_run.json` summarizing flagged transactions.

### 4.5 API & Telemetry Wiring
- [ ] Enrich `/ingest/{job_id}` status with `status_details.forensics` timestamps aligning with Spec §APIs.GET /ingest/{job_id}.  
  **Deliverable:** FastAPI contract test asserting timestamps after mocked run.
- [ ] Expose `/forensics/{type}` responses with summary, signals, raw payload + fallback flag per Spec §API Surfacing of Forensics Artifacts.  
  **Deliverable:** OpenAPI diff captured in `build_logs/forensics/api_contract.md` documenting additions.
- [ ] Publish `traces.forensics` hook within `/query` responses linking to artifacts mandated by Spec §APIs.GET /query traces.  
  **Deliverable:** Retrieval integration test verifying trace snippet references stored forensic report.

## Phase 5 — Retrieval
**Owner:** Retrieval Engineering Pod — Aiko Matsuda  
**Duration Estimate:** 9 engineer-days  
**Prerequisites:** Phase 3 hybrid retriever baseline shipped; vector + graph stores populated  
**Roadmap Milestone Alignment:** Roadmap Phase 3 — Context Engine (retrieval refinement)  
**CI/CD Checkpoint:** `retrieval-regression` workflow (hybrid scorer tests + citation contract checks)  
**Exit Criteria:** `/query` returns cited answers with trace coverage, guardrails enforced, telemetry captures retrieval contexts.

- [ ] **Hybrid Ranking Tuning (Spec §APIs.GET /query)** — Implement ensemble scoring with deterministic ordering for citations.
- [ ] **Citation Extraction (Spec §APIs.GET /query → citations)** — Map spans to document metadata with confidence thresholds.
- [ ] **Context Tracing (Spec §APIs.GET /query → traces.vector/graph)** — Persist path diagnostics for debugging + UI.
- [ ] **Cite-or-Silence Guardrail (Spec §APIs.GET /query → Error Codes)** — Return `204` when evidence absent; ensure guardrail policy instrumentation.

## Phase 6 — UI
**Owner:** Experience Engineering — Lila Chen  
**Duration Estimate:** 14 engineer-days  
**Prerequisites:** Phases 2–5 complete; design system tokens approved  
**Roadmap Milestone Alignment:** Roadmap Phase 8–9 — API + Frontend  
**CI/CD Checkpoint:** `frontend-e2e` workflow (Playwright chat + forensics views)  
**Exit Criteria:** Chat, citation, timeline, and forensics views wired to live APIs with loading/error states; accessibility AA compliance.

- [ ] **Chat Surface (Spec §APIs.GET /query)** — Streaming chat panel consuming query endpoint with typing indicators.
- [ ] **Citation Panel (Spec §APIs.GET /query → citations)** — Render inline citations with deep links to document viewer.
- [ ] **Timeline View (Spec §APIs.GET /timeline)** — Display chronological events with pagination + filters.
- [ ] **Forensics Dashboards (Spec §API Surfacing of Forensics Artifacts)** — Provide modality-specific report viewers with fallback banners.

## Phase 7 — QA & Validation
**Owner:** Reliability & Compliance Team — Omar Haddad  
**Duration Estimate:** 11 engineer-days  
**Prerequisites:** Phases 1–6 completed; infra stable  
**Roadmap Milestone Alignment:** Roadmap Phase 10 — Testing/Hardening  
**CI/CD Checkpoint:** `qa-suite` workflow (unit, integration, e2e, load-smoke)  
**Exit Criteria:** All automated suites green, coverage thresholds met, NFR validation matrix signed off, release candidate tagged.

- [x] **Unit Coverage (Spec §§APIs & Forensics Nodes)** — Ensure loaders, graph upserts, forensic analyzers, retriever components meet ≥85% coverage (enforced via `python -m tools.qa.quality_gate`).
- [ ] **Integration Journeys (Spec §Forensics Toolbox Execution Blueprint & §APIs)** — Validate end-to-end ingestion → query → forensics flows on sample corpus.
- [ ] **E2E Scripted Journey (Spec §APIs.GET /query & §API Surfacing)** — Execute user journey script verifying chat, citations, timeline, forensics UI.
- [ ] **Performance & Resilience (Spec §Forensics Nodes soft/hard fail paths)** — Run load and failover drills capturing metrics in NFR validation matrix.
