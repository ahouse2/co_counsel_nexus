# Automated Legal Discovery Co-Counsel — TRD/PRP (Rebuilt)

Purpose: Rebuild “TRD-PRP_legal_tech_2.txt” using the following components and reference implementations:
- Orchestration: Microsoft Agents Framework SDK (graph workflows, memory, telemetry)
- Knowledge/RAG: LlamaIndex core + LlamaHub connectors; GraphRAG with Neo4j
- Domain roles: Swarms (specialized multi-agent roles/patterns)
- Vector store: Qdrant or Chroma (local-first), pluggable
- Frontend: React (neon theme), streaming chat/voice, timeline + graph views
- Voice: Whisper STT, Coqui TTS

## 1) Overview and Objectives
- End-to-end discovery ingestion (PDFs, emails, chats, drives) with continuous updates
- Contextual legal reasoning with citations (hybrid vector + graph retrieval)
- Interactive timeline and knowledge graph exploration with deep links to sources
- Voice co-counsel with sentiment/tone awareness and long-term case memory
- Deployable via Docker Compose; strong observability, audit, and security

Success criteria
- Answer queries with cited passages and graph paths; “cite or silence” policy
- Construct correct event timelines from corpus with high coverage
- Maintain reproducible pipelines and telemetry across agent workflow nodes

## 2) System Architecture
Frontend
- React UI (chat/voice console, timeline, evidence browser, mock court sim)
- WebSocket streaming, token display, citations w/ deep links

Agents Orchestration (Microsoft Agents Framework)
- Workflow graph connecting agents + tools, deterministic edges, checkpoints
- Memory: case threads + vector memory via LlamaIndex; optional Redis
- Telemetry: OpenTelemetry spans per node, request IDs, structured logs

Knowledge & Retrieval (LlamaIndex + LlamaHub)
- Loaders: local files, SharePoint/OneDrive/Outlook/Gmail/Slack/Confluence/Jira/GitHub/Google Drive/S3
- Indexes: vector (Qdrant/Chroma) + graph (Neo4j via Cypher)
- GraphRAG: entity/relation extraction, graph neighborhoods + semantic chunks

Swarms role schemas
- LeadCounsel, Paralegal, Researcher, SWE, PM; delegation + review loops

## 3) Core Agents (illustrative)
- IngestionAgent: runs LlamaHub loaders, chunking, embeddings, metadata, persistence
- GraphBuilderAgent: triples extraction, ontology mapping, Cypher upserts to Neo4j
- ResearchAgent: hybrid retrieval (vector + graph neighborhood), citations
- DraftingAgent: memos/briefs with citations and graph references
- TimelineAgent: derives events from KG; exposes API for UI timeline
- VoiceAgent: STT, TTS, conversation state, sentiment/tone modulation
- QAAgent: rubric checks, coverage metrics, regression scripts

## 4) Data Flow (Happy Path)
1. User links/uploads sources
2. Ingestion -> LlamaHub loaders -> chunk+embed -> vector store
3. GraphBuilder -> extract entities/relations -> Neo4j writes
4. Research/Drafting -> hybrid retrieval -> answer with citations and graph paths
5. TimelineAgent -> KG-derived events -> UI timeline

## 5) Security & Compliance
- Data residency and isolation; secrets via env/KeyVault
- PII/PHI redaction tools; role-based tool access; audit logs of evidence access
- Model governance via provider abstraction + safety middleware

## 6) Observability
- OTel tracing across nodes; log retrieval contexts, prompt templates, token usage
- Per-answer citation coverage metrics; retriever scores; graph traversal summaries

## 7) Deployment
- Docker Compose: api (agents), vector DB (Qdrant/Chroma), Neo4j, UI, Redis, optional STT/TTS
- One-click `.env` driven setup; health endpoints; seed scripts for sample corpus

## 8) Risks & Mitigations
- Hallucinations: strict RAG; “cite or silence”; adversarial prompts in QA
- Extraction errors: human review panel for low-confidence triples
- Cost/perf: on-prem embeddings, batching, incremental indexing, selective re-ingest

## 9) Validation Gates
- Unit: loaders, chunkers, embedding adapters, graph upserts
- Integration: ingest sample corpus; precision/recall of hybrid retrieval; timeline correctness
- E2E: scripted voice+chat journeys; snapshot citations and graph paths

## 10) Roadmap (Phases)
- P1: Core ingestion + vector search + basic Q/A w/ citations
- P2: GraphRAG + timeline + research improvements
- P3: Voice agent + UI polish + observability
- P4: Forensics tools + enterprise hardening

## 11) Reference Code in repo
- Microsoft Agents Framework SDK: `Reference Code/agent-framework-main` (Python)
- LlamaHub connectors: `Reference Code/llama-hub`
- Swarms library: `swarms-master/`

This TRD/PRP supersedes framework choices in older drafts and aligns implementation to MS Agents + LlamaIndex/LlamaHub + Swarms.

