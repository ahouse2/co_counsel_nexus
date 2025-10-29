# Phase 9 Remote Connector Execution Roadmap

## Volume I — Ingestion Connector Expansion
### Chapter 1 — Credential Plumbing
- Paragraph 1 — Registry scaffolding
  - Sentence 1 — Ensure test scaffolding writes credential registry fixtures for S3, SharePoint, and OneDrive to exercise integration pathways end to end.
  - Sentence 2 — Reset backend settings cache after priming environment variables so connectors hydrate workspace directories deterministically.
- Paragraph 2 — Validation matrix
  - Sentence 1 — Validate presence of `credRef` and required attributes per connector (buckets for S3, site/folder for SharePoint, drive/folder for OneDrive) before attempting network calls.
  - Sentence 2 — Raise FastAPI `HTTPException` with descriptive messages for missing inputs to align with PRP error contracts.

### Chapter 2 — OneDrive Materialisation
- Paragraph 1 — Token acquisition
  - Sentence 1 — Implement OAuth client-credential flow against Microsoft identity endpoints using `httpx` with bounded timeouts and structured logging.
  - Sentence 2 — Surface `503` if Graph access token retrieval fails or returns malformed payloads so ingestion jobs record actionable diagnostics.
- Paragraph 2 — Graph traversal
  - Sentence 1 — Resolve the target drive item (root or nested folder) and breadth-first traverse child folders honouring `@odata.nextLink` pagination for large collections.
  - Sentence 2 — Stream file content via `items/{id}/content`, writing to per-job workspaces while logging provenance metadata for downstream stores.
- Paragraph 3 — Resilience envelope
  - Sentence 1 — Apply limited retry with exponential backoff on `429`/`5xx` responses to satisfy reliability requirements without blocking unit tests.
  - Sentence 2 — Emit structured warnings when folders resolve to no files so status manifests capture empty materialisations explicitly.

## Volume II — Regression Coverage
### Chapter 3 — Remote Connector Tests
- Paragraph 1 — S3 regression
  - Sentence 1 — Monkeypatch boto3 paginator/client to simulate object downloads and assert file writes plus logging metadata.
  - Sentence 2 — Assert skipped results remain empty and workspace naming follows `job/index_label` convention.
- Paragraph 2 — SharePoint regression
  - Sentence 1 — Stub Office365 client context operations to validate recursive folder downloads and error propagation surfaces `502` on unexpected exceptions.
  - Sentence 2 — Confirm connectors respect `source.path` overrides in preference to credential defaults.
- Paragraph 3 — OneDrive regression
  - Sentence 1 — Provide fake `httpx.Client` injecting canned token, listing, and download responses covering pagination, nested folders, and binary content writes.
  - Sentence 2 — Exercise negative scenarios (missing credentials, token failure) to ensure HTTP errors propagate with correct status/detail payloads.

### Chapter 4 — API Contract Confirmation
- Paragraph 1 — `pytest` execution
  - Sentence 1 — Run focused `pytest backend/tests/test_ingestion_connectors.py -q` to validate new coverage in isolation.
  - Sentence 2 — Execute full backend regression `PYTHONPATH=. pytest backend/tests -q` verifying connectors integrate with existing suites under environment priming.

## Volume III — Stewardship & Reporting
### Chapter 5 — Documentation & Tasks
- Paragraph 1 — Task ledger
  - Sentence 1 — Update PRP status review task list marking remote connector work complete and referencing regression coverage additions.
  - Sentence 2 — Cross-link plan summary where applicable to maintain traceability between roadmap and execution artefacts.
- Paragraph 2 — Build log & ACE memory
  - Sentence 1 — Capture execution timeline, commands, and metrics in `build_logs/2025-11-13.md`.
  - Sentence 2 — Append ACE state entry documenting Retriever → Planner → Critic flow, including validation commands and resulting artefacts.

### Chapter 6 — Stewardship Log & PR Draft
- Paragraph 1 — Stewardship update
  - Sentence 1 — Extend root `AGENTS.md` log with timestamped summary, files touched, and validation outcomes.
- Paragraph 2 — Pull request brief
  - Sentence 1 — Prepare PR summary emphasising OneDrive connector delivery, regression coverage, and documentation/task updates ready for review.
