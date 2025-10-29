# Forensics Workflow Playbook — LlamaIndex Node Intelligence & DFIR Connectors

## 1. Pipeline Overview
1. **Canonicalisation** — Each artifact is copied into the tamper-evident workspace before any processing begins.
2. **LlamaIndex Enrichment** — Document artifacts ingest LlamaIndex nodes (chunk IDs, embeddings, metadata) and compute:
   - Chunk statistics (count, length distribution, entropy) and embedding norm summaries.
   - Duplicate chunk detection (cosine ≥ 0.985) with structured alerts.
   - Embedding outlier detection (IsolationForest or z-score) to flag abnormal segments.
   - High-entropy chunk tracking for potential credential dumps or binary blobs.
3. **Metadata Extraction** — Hashes (MD5/SHA-256/TLSH), MIME, OCR provenance, and ingestion metadata are recorded.
4. **Modality Analysis** — PDF/DOCX/email/image-specific analyzers run alongside financial anomaly detection for ledgers.
5. **Persistence** — Reports are stored under `<FORENSICS_DIR>/<doc_id>/report.json`, appended to the hash-chain ledger for auditability.

## 2. Connector Activation via Agents SDK
- Strategy tool heuristics seed `directives` (e.g., `dfir`, `financial`) from the case question.
- Forensics tool consults directives and enriches the artifact bundle with connector outputs.
- DFIR connector aggregates:
  - LlamaIndex alerts, duplicate/outlier chunks, high-entropy nodes per document.
  - Privilege classifier aggregates for QA gating.
  - Remediation checklist (`quarantine evidence`, `correlate access logs`).
- Financial connector compiles ledger totals, anomaly counts, and remediation guidance sourced from forensics payloads.

## 3. Privilege & QA Gating
- Retrieval traces now surface chunk previews, norms, and privilege aggregates.
- QA agent marks `telemetry.gating.requires_privilege_review = True` when privileged evidence is detected.
- Orchestrator returns `status = needs_privilege_review` while preserving QA scores/notes.

## 4. Remediation Steps
### DFIR Incidents
1. Quarantine documents flagged by DFIR connector.
2. Cross-reference duplicate/outlier chunks with access logs for exfiltration confirmation.
3. Escalate to incident commander before disseminating any privileged content.

### Financial Ledgers
1. Validate approval trail for each anomaly (`report.data.remediation`).
2. Reconcile totals versus source system exports.
3. Escalate entities highlighted in remediation checklist for controller review.

## 5. Validation Checklist
- [ ] `pytest backend/tests/test_forensics.py backend/tests/test_forensics_connectors.py -q`
- [ ] Inspect `docs/validation/forensics_workflow_playbook.md` for alignment with current pipeline.
- [ ] Verify `FORENSICS_CHAIN_PATH` ledger integrity via `backend/tools/verify_forensics_chain.py`.

## 6. Telemetry & Audit
- LlamaIndex stage metrics emit `forensics_stage_duration_ms{stage="llama_index"}` and alerts recorded in the ledger payload.
- Connector executions record directive names inside agent telemetry for downstream analytics.
- Privilege gating is persisted in thread telemetry for follow-up QA review.
