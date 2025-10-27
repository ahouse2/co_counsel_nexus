# Task List — Master Plan (Phases 0–10)

> **PRP Navigation:** [Base](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_base.md) · [Planning](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_planning.md) · [Spec](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_spec.md) · [Tasks](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_tasks.md) · [Pre-PRP Plan](PRE_PRP_PLAN.md) · [ACE Execution Guide](EXECUTION_GUIDE_ACE.md) · [Task List Master](TASK_LIST_MASTER.md) · [PRP Templates](templates/README.md) · [PRP Analyze Run Template](../.codex/commands/rapid-development/experimental/prp-analyze-run.md)

Phase 0 — Repo & Guardrails
- [ ] Compose skeleton, health endpoints, pre-commit
- [ ] CI basic checks (lint/tests), orphan_scan script stub
- [ ] Build logs + memory folders initialized

Phase 1 — Data Foundations
- [ ] Neo4j container + constraints; Qdrant/Chroma local store
- [ ] Settings/env wiring; health checks; readiness gates

Phase 2 — Ingestion MVP
- [ ] Folder uploads; LlamaHub loader registry (local files + 1 cloud loader)
- [ ] OCR/parse (required), Vision‑LLM agent classification/tagging for images/scanned docs
- [ ] Chunking, embeddings, persist vector index + metadata schema

Phase 3 — Context Engine
- [ ] GraphRAG extract (triples prompt) + Cypher upserts
- [ ] Hybrid retriever (vector + graph neighborhood)
- [ ] ContextPacket JSON schema

Phase 4 — Forensics Core (Non‑Negotiable)
- [ ] Hashing + metadata + structure checks for all files
- [ ] Image authenticity pipeline; financial baseline analysis
- [ ] Forensics artifacts + API endpoints

Phase 5 — Multi‑Agent + ACE
- [ ] MS Agents workflow nodes; memory threads
- [ ] ACE trio orchestration; telemetry spans
- [ ] QAAgent with rubric scoring and citation audit

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
