# Task List — Master Plan (Phases 0–10)

> **PRP Navigation:** [Base](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_base.md) · [Planning](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_planning.md) · [Spec](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_spec.md) · [Tasks](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_tasks.md) · [Pre-PRP Plan](PRE_PRP_PLAN.md) · [ACE Execution Guide](EXECUTION_GUIDE_ACE.md) · [Task List Master](TASK_LIST_MASTER.md) · [PRP Templates](templates/README.md) · [PRP Analyze Run Template](../.codex/commands/rapid-development/experimental/prp-analyze-run.md)

Phase 0 — Repo & Guardrails
- [x] Compose skeleton, health endpoints, pre-commit
- [x] CI basic checks (lint/tests), orphan_scan script stub
- [x] Build logs + memory folders initialized

Phase 1 — Data Foundations
- [x] Neo4j container + constraints; Qdrant/Chroma local store
- [x] Settings/env wiring; health checks; readiness gates

Phase 2 — Ingestion MVP
- [x] Folder uploads; LlamaHub loader registry (local files + 1 cloud loader)
- [x] OCR/parse (required), Vision‑LLM agent classification/tagging for images/scanned docs
- [x] Chunking, embeddings, persist vector index + metadata schema

Phase 3 — Context Engine
- [x] GraphRAG extract (triples prompt) + Cypher upserts
- [x] Hybrid retriever (vector + graph neighborhood)
- [x] ContextPacket JSON schema

Phase 4 — Forensics Core (Non‑Negotiable)
- [x] Hashing + metadata + structure checks for all files
- [x] Image authenticity pipeline; financial baseline analysis
- [x] Forensics artifacts + API endpoints

Phase 5 — Multi‑Agent + ACE
- [x] MS Agents workflow nodes; memory threads
- [x] ACE trio orchestration; telemetry spans
- [x] QAAgent with rubric scoring and citation audit
  - [ ] **Follow-on hardening** — extend TimelineAgent playbooks with retry/circuit breaker patterns, persist agent trace spans, and surface structured error taxonomy for downstream escalation.
  - [ ] **KnowledgeOps toolkit** — codify agent scaffolds (prompt packs, evaluation harness, deterministic fixtures) so new research or compliance agents can be added with <4h onboarding.

Phase 6 — Timeline
- [x] Event extraction from KG; API: GET /timeline
  - [x] Implement cursor-based pagination, `from_ts`/`to_ts` range filters, and entity scoping backed by graph lookups. (Implemented in `backend/app/services/timeline.py`; verifies naive timestamps + cursor sequencing.)
  - [ ] Emit telemetry counters/latency histograms; fail closed on malformed cursors with structured 400 responses.
    - Structured 400s landed; telemetry counters still pending once observability wiring arrives.
  - [x] Regression-suite coverage for timeline enrichment, pagination, and filter semantics. (`backend/tests/test_api.py::test_timeline_pagination_and_filters`.)
- [ ] UI timeline with pop‑outs and citations
  - [ ] Wire streaming data layer to `/timeline` endpoint with optimistic updates + offline cache.
  - [ ] Provide evidence pop-outs that hydrate citations + forensics deltas; add accessibility narration and keyboard traversal.

Phase 7 — Legal Research & Extended Forensics
- [ ] CourtListener/web search; privilege detector; chain‑of‑custody
  - [ ] Integrate external research connectors with rate-limited async agents and cached digests.
  - [ ] Automate privilege classification with explainable feature attributions + policy overrides.
  - [ ] Chain-of-custody ledger with cryptographic sealing + audit replay tooling.

Phase 8–9 — API + Frontend
- [ ] Endpoints: /ingest, /query, /timeline, /graph/neighbor
  - [ ] Harden authZ/ABAC matrix, enforce scope-aware response shaping, and introduce streaming query responses with back-pressure.
  - [ ] Graph diff + timeline delta webhooks for agent-triggered notifications.
- [ ] Neon UI chat stream; citations; basic graph view
  - [ ] Implement design tokens + dark-mode baseline; ensure WCAG AA contrast.
  - [ ] Embed timeline + graph canvases with shared selection state + real-time collaboration primitives.

Phase 10 — Testing & Hardening
- [ ] Unit/integration/e2e/load; security posture review
- [ ] Orphan scan CI; repo hygiene rules

Phase 11 — Packaging
- [ ] Installer/packaging targets (as needed)
