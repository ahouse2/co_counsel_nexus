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

Phase 6 — Timeline
- [ ] Event extraction from KG; API: GET /timeline
- [ ] UI timeline with pop‑outs and citations

Phase 7 — Legal Research & Extended Forensics
- [ ] CourtListener/web search; privilege detector; chain‑of‑custody

Phase 8–9 — API + Frontend
- [ ] Endpoints: /ingest, /query, /timeline, /graph/neighbor
- [ ] Neon UI chat stream; citations; basic graph view

Phase 10 — Testing & Hardening
- [ ] Unit/integration/e2e/load; security posture review
- [ ] Orphan scan CI; repo hygiene rules

Phase 11 — Packaging
- [ ] Installer/packaging targets (as needed)
