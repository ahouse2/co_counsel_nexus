name: "Tasks — Co-Counsel MVP"
status: draft

## Phase 1 — Foundation
- [ ] Repo wiring: env, settings, logging, OTel stubs
- [ ] Data stores: Qdrant/Chroma driver; Neo4j driver; config
- [ ] API skeleton: FastAPI/Flask with endpoints stubs

## Phase 2 — Ingestion
- [ ] Folder uploads; LlamaHub loader registry + local file loader
- [ ] OCR (Tesseract or equivalent) + Vision‑LLM agent for classification/tagging/scanned docs
- [ ] Chunking + embeddings (HF BGE small by default)
- [ ] Persist vector index; metadata schema

## Phase 3 — GraphRAG
- [ ] Triples extraction prompt and parser
- [ ] Cypher upsert utils; constraints
- [ ] Ontology seed; id normalization

## Phase 4 — Forensics Core (Non‑Negotiable)
### 4.1 Toolbox Orchestration & Storage
- [ ] Implement canonicalization → metadata → analyzer orchestration respecting spec execution order.  
  **Deliverable**: `tests/forensics/test_pipeline_order.py` validates stage sequencing via deterministic fixtures.
- [ ] Persist reports to `./storage/forensics/{fileId}/report.json` with versioned schema.
  **Deliverable**: CLI `python -m backend.tools.forensics dump --id sample-doc` emits JSON matching spec contract.

### 4.2 Document Forensics
- [ ] Hashing (SHA‑256 + TLSH) and PDF/DOCX/MSG metadata extraction using `hashlib`, `tlsh`, `python-magic`, `pypdf`, `python-docx`, `extract-msg`.
  **Deliverable**: Unit tests cover PDF, DOCX, and MSG fixtures with expected hashes + metadata snapshots.
- [ ] Structure + authenticity analysis (TOC, signatures, header diffs) via `unstructured`, `pikepdf`, `mailparser`.
  **Deliverable**: Golden JSON in `build_logs/forensics/document/sample_report.json` demonstrating populated `signals` and `summary`.

### 4.3 Image Forensics
- [ ] EXIF harvesting with `Pillow`/`piexif` plus ELA and clone detection via `opencv-python`, `numpy`, `imagededup`, `pyprnu`.
  **Deliverable**: Regression notebook `notebooks/forensics/image_qa.ipynb` (executed to HTML) evidences detection of tampered sample.
- [ ] Implement fallback path for unsupported/low-resolution imagery, surfacing `fallback_applied` + coverage signal.
  **Deliverable**: Integration test triggers fallback and asserts API returns HTTP `415` when analyzer unavailable.

### 4.4 Financial Forensics
- [ ] Tabular ingestion with `pandas`/`pyarrow`, totals reconciliation using `decimal`.
  **Deliverable**: Automated check verifying accounting identities on synthetic ledger fixture.
- [ ] Isolation Forest anomaly detection with `scikit-learn` and z-score fallback for small datasets.
  **Deliverable**: Stored artifact `build_logs/forensics/financial/anomaly_run.json` summarizing flagged transactions.

### 4.5 API & Telemetry Wiring
- [ ] Enrich `/ingest/{job_id}` status with `status_details.forensics` timestamps.
  **Deliverable**: FastAPI contract test asserting presence of timestamps after mocked run.
- [ ] Expose `/forensics/{type}` responses with summary, signals, raw payload + fallback flag as defined in spec.
  **Deliverable**: OpenAPI schema diff captured in `build_logs/forensics/api_contract.md` documenting additions.
- [ ] Publish `traces.forensics` hook within `/query` responses linking to artifacts.
  **Deliverable**: Retrieval integration test verifying trace snippet references stored forensic report.

## Phase 5 — Retrieval
- [ ] Hybrid retriever; citation extraction
- [ ] Tracing of retrieval contexts
- [ ] “Cite or silence” guardrails

## Phase 6 — UI
- [ ] Chat panel with streaming
- [ ] Citations panel w/ deep links
- [ ] Timeline list bound to KG
- [ ] Forensics report views (document/image/financial)

## Phase 7 — QA & Validation
- [ ] Unit tests for loaders, graph upserts, retriever
- [ ] Integration flow on sample corpus
- [ ] E2E scripted journey
