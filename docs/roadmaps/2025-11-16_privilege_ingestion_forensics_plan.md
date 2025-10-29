# 2025-11-16 — CourtListener/Web Search Async Connectors, Privilege Classifier, and Forensics Chain Ledger

## Phase I — Async Ingestion Sources Expansion
- ### Objective: Extend ingestion connectors with CourtListener and federated web search capabilities leveraging async workflows and digest caching.
  - #### Step 1 — Source Capability Definition
    - ##### Task A — Map `IngestionSource` semantics for remote connectors (query via `path`, credentials for auth, pagination defaults).
    - ##### Task B — Specify digest caching strategy (shared `_cache/<connector>` workspace keyed by SHA-256).
  - #### Step 2 — CourtListener Connector Implementation
    - ##### Task A — Introduce `CourtListenerSourceConnector` with async pagination + detail fetch (`httpx.AsyncClient`).
    - ##### Task B — Implement credential requirements (token optional, override endpoint, max pages/page size bounds).
    - ##### Task C — Persist opinion payloads as JSON text files plus digest cache reuse.
    - ##### Task D — Harden error handling (HTTP status mapping, empty result logging, credential validation).
    - ##### Task E — Unit tests covering fetch, caching, and credential validation using async client stubs.
  - #### Step 3 — Web Search Connector Implementation
    - ##### Task A — Implement configurable endpoint connector with API-key headers from registry.
    - ##### Task B — Support concurrent page fetch + per-result content summarisation.
    - ##### Task C — Apply digest cache for snippet reuse keyed by canonical URL.
    - ##### Task D — Validate query presence, handle API throttling/backoff, and log metrics.
    - ##### Task E — Regression tests for result materialisation and caching semantics.

## Phase II — Privilege Classifier Service Integration
- ### Objective: Provide trained privilege classifier with query trace + agent telemetry integration.
  - #### Step 1 — Service Foundations
    - ##### Task A — Add `privilege.py` service with TF-IDF + logistic regression training on curated samples.
    - ##### Task B — Expose dataclasses for `PrivilegeDecision` + aggregator, `get_privilege_classifier_service()` factory, settings knobs (threshold, model cache path optional).
  - #### Step 2 — Retrieval Layer Enhancements
    - ##### Task A — Extend `Trace`/`TraceModel` to include privilege section.
    - ##### Task B — Integrate classifier evaluation across filtered results, produce aggregate verdict & per-doc scores.
    - ##### Task C — Surface privilege data in metrics + `QueryResult.to_dict()`.
  - #### Step 3 — Agent Workflow Alignment
    - ##### Task A — Propagate privilege summary into research turn metrics + telemetry.
    - ##### Task B — Update QA agent heuristics to factor privilege alerts (e.g., compliance scoring adjustments).
    - ##### Task C — Add regression coverage ensuring privilege signals propagate through `/query` output and agent run pipeline.

## Phase III — Forensics Chain-of-Custody Ledger
- ### Objective: Build tamper-evident ledger with verification tooling + regression coverage.
  - #### Step 1 — Ledger Storage Module
    - ##### Task A — Implement `ForensicsChainLedger` with append-only JSONL, SHA-256 chaining, UTC timestamps.
    - ##### Task B — Provide `verify()` returning issues list, `iter_entries()`, and context manager safe writes (fsync flush).
    - ##### Task C — Integrate ledger appends into `ForensicsService` artifact persistence.
  - #### Step 2 — Nightly Verification Tooling
    - ##### Task A — Create CLI `backend/tools/verify_forensics_chain.py` invoking ledger verification (exit 0/1/2 semantics).
    - ##### Task B — Document usage in docstring + align with ACE instrumentation logging (stdout JSON summary).
  - #### Step 3 — Regression Tests
    - ##### Task A — Write `backend/tests/test_forensics_chain.py` covering append, tamper detection, verification CLI.
    - ##### Task B — Ensure ledger path respects `FORENSICS_CHAIN_PATH` override and plays nicely with settings prep.
    - ##### Task C — Add ingestion/forensics tests verifying ledger entries appended per artifact.

## Phase IV — Stewardship + Validation
- ### Objective: Ensure repository hygiene, tests, and stewardship artefacts updated.
  - #### Step 1 — Update stewardship log in root `AGENTS.md` with contributions + rubric.
  - #### Step 2 — Add build log entry summarising validation commands (pytest targets) under `build_logs/` dated 2025-11-16.
  - #### Step 3 — Re-run targeted pytest suites (`backend/tests/test_ingestion_connectors.py`, `backend/tests/test_agents.py`, `backend/tests/test_forensics_chain.py`, `backend/tests/test_forensics.py` if impacted).
  - #### Step 4 — Prepare PR narrative emphasising async connectors, privilege classifier integration, and chain ledger verification.

## Phase V — Iterative Review Loop
- ### Objective: Conduct multi-pass self-review for each module.
  - #### Pass 1 — Static analysis of new modules (naming, docstrings, typing, error handling).
  - #### Pass 2 — Runtime verification via pytest + targeted scenario replays.
  - #### Pass 3 — Final audit ensuring doc updates, stewardship logs, and caching directories created.
