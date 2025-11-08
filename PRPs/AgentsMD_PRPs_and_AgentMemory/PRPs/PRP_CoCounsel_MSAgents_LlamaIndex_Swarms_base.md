name: "Co-Counsel Legal Discovery — PRP Base"
version: 1.0
owners:
  - "Product/Eng: andrew house"
status: draft

> **PRP Navigation:** [Base](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_base.md) · [Planning](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_planning.md) · [Spec](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_spec.md) · [Tasks](PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_tasks.md) · [Pre-PRP Plan](PRE_PRP_PLAN.md) · [ACE Execution Guide](EXECUTION_GUIDE_ACE.md) · [Task List Master](TASK_LIST_MASTER.md) · [PRP Templates](templates/README.md)

## Goal / Why / What
- Goal: Ship a vertical slice of an AI legal co-counsel capable of ingesting documents, building vector + graph indexes, and answering questions with citations via a multi-agent system.
- Why: Enable reliable, explainable legal discovery assistance that scales to enterprise needs with strong observability and low-cost, local-first options.
- What: Backend services for ingestion, retrieval, graph building; a workflow graph (Microsoft Agents Framework); a minimal UI for chat + timeline; and validation gates.

## Scope
- In-scope: ingestion pipeline (folder uploads, OCR + Vision‑LLM agent), vector + graph stores, hybrid retrieval, core agents (ingest, graph, research, drafting, timeline), forensics core (hashing, metadata, structure, authenticity, basic financial checks), minimal React UI, voice plumbing stubs, Trial University + Mock Trial baseline.
- Out-of-scope (this slice): enterprise SSO; advanced forensics techniques beyond core; full mock court polish (MVP includes functional baseline).

## Context
- Reference code:
  - MS Agents Framework SDK: `Reference Code/agent-framework-main`
  - LlamaHub connectors: `Reference Code/llama-hub`
  - Swarms library: `swarms-master/`
- Prior PRPs/Docs: see `AgentsMD_PRPs_and_AgentMemory/PRPs/ai_docs/` including rebuilt TRD/PRP.
- Tech:
  - Python 3.11+, Neo4j 5.x, Qdrant/Chroma, React 18
  - Whisper (STT), Coqui (TTS) optional containers
  - LLM Provider: default Google Gemini‑2.5‑Flash; optional OpenAI GPT‑5.0; provider abstraction layer

## Implementation Blueprint
1) Data layer
   - Vector store driver (Qdrant/Chroma) via LlamaIndex Settings
   - Graph store driver (Neo4j) + Cypher upsert utils
2) Ingestion
   - LlamaHub loaders registry; chunking; embeddings; metadata; persistence
3) GraphRAG
   - Triples extraction prompt + mapper; ontology; idempotent upserts
4) Retrieval
   - Hybrid retriever fusing vector + graph neighborhood
5) Agents Orchestration
   - MS Agents workflow: nodes (Ingestion, GraphBuilder, Research, Timeline)
   - Memory threads; OTel spans; run context IDs
6) API
   - POST /ingest, GET /query?q=, GET /timeline, GET /graph/neighbor?id=
7) UI (minimal)
   - Chat panel (streaming); citations; collapsible timeline; basic graph view placeholder

## Validation Gates
- Unit tests: loaders, embeddings adapter, graph upserts, hybrid retriever
- Integration: sample corpus ingest; query answers include citations + paths
- E2E: scripted journey covering ingest->ask->timeline

## Risks & Mitigations
- Hallucinations: enforce cite-or-silence, retrieval traces, QA prompts
- Extract accuracy: low-confidence review queue; user corrections
- Cost/perf: on-prem embeddings; batch jobs; incremental updates

## Deliverables
- Running compose stack with API + stores + sample UI
- PRD/Spec/Tasks docs; ONBOARDING.md and QUICKSTART.md
