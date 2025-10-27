# Pre‑PRP Plan — Co‑Counsel Commercial Build

> **PRP Navigation:** [Base](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_base.md) · [Planning](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_planning.md) · [Spec](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_spec.md) · [Tasks](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_tasks.md) · [Pre-PRP Plan](PRE_PRP_PLAN.md) · [ACE Execution Guide](EXECUTION_GUIDE_ACE.md) · [Task List Master](TASK_LIST_MASTER.md) · [PRP Templates](templates/README.md) · [Rapid Dev Commands](../.codex/commands/README.md)

Purpose: Establish shared context and an execution playbook before coding. Aligns prior blueprints (previous builds/docs) with the target stack: Microsoft Agents Framework SDK, LlamaIndex + LlamaHub, Swarms, Neo4j, Qdrant/Chroma, React UI, Whisper/Coqui.

## Vision & Bar
- One‑pass attempt at commercial, production‑ready quality (worth $1000/mo).
- Enterprise‑grade reliability, security, observability, and auditability.
- Explainable outputs with citations and graph paths (cite‑or‑silence policy).

## Folder Canon (repo alignment)
- apps/ — thin CLI/UX wrappers
- backend/ — API, agents, workers (MS Agents workflow graph)
- services/ — long‑running jobs, ingestion workers
- agents/ — agent registry + ACE loop
- tools/ — callable tools
- frontend/ — React/Vite UI
- infra/ — Docker Compose, Helm, packaging
- docs/ — specs, PRDs, runbooks
- runbooks/ — operations/incident guides
- build_logs/ — daily logs + automation.jsonl
- memory/ — ace_state.jsonl + handoffs/
- scripts/ — dev utilities

## Phases (high‑level)
0) Repo & Guardrails — compose up green; CI basic; logging bootstrapped
1) Data Foundations — Neo4j + Qdrant/Chroma + health checks
2) Ingestion MVP — loaders, OCR, chunk, embed, index; jobs & retries
3) Context Engine — hybrid retrieval (vector+graph), ContextPacket JSON
4) Multi‑Agent + ACE — Coordinator, Retriever, Planner, Critic, LegalResearch, TimelineBuilder, Forensics stubs
5) Timeline — event graph; UI timeline with citations pop‑outs
6) Forensics — doc/media/financial; privilege & chain‑of‑custody
7–8) API + Frontend — chat/ingest/search/graph/timeline; neon UI
9) Testing/Hardening — unit/integration/e2e/load; security
10) Installers/Packaging — optional platform installers

## ACE Loop (Agentic Context Engineering)
- Roles: Retriever → Planner → Critic (default 3 cycles) then Orchestrator merges
- Logs: append to memory/ace_state.jsonl; unfinished write memory/handoffs/<feature>.md
- Required for every non‑trivial change; must include citations to sources/context IDs

## Security & Compliance Guardrails
- RBAC and tool allow‑lists per agent
- Encryption in transit/at rest; secrets via env/KeyVault
- Audit evidence access; chain‑of‑custody logs; ethical walls

## Observability
- OpenTelemetry spans on each workflow node/edge
- Retrieval traces including vector scores and graph paths
- SLO dashboards (latency, error rates, citation coverage)

## Dependencies (initial)
- Python 3.11+, Neo4j 5.x, Qdrant/Chroma, Node 18+
- Microsoft Agents Framework SDK (Python), LlamaIndex + LlamaHub, Swarms, Whisper/Coqui

## Validation Gates (global)
- Unit: loaders, embeddings, graph upserts, retriever composition
- Integration: ingest sample corpus; query eval (precision/recall); timeline correctness
- E2E: scripted journeys (chat/voice) with snapshot citations

