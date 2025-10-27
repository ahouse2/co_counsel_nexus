# Onboarding Guide — NinthOctopusMitten

## 1) Project Overview
- Purpose: Integrate reference agent frameworks to build an AI legal discovery co-counsel (GraphRAG + multi-agent orchestration) with strong documentation and validation via PRPs.
- Stack: Python (agents/backends), Neo4j, Qdrant/Chroma, React (UI), Whisper/Coqui (voice), Microsoft Agents Framework SDK, LlamaIndex + LlamaHub, Swarms. LLM Provider default: Google Gemini‑2.5‑Flash; optional OpenAI GPT‑5.0.
- Architecture: Service-style backend + agent workflow graph; vector + graph storage; web UI. PRP-driven development.

## 2) Repository Structure
- `AgentsMD_PRPs_and_AgentMemory/` — PRPs, guides, and agent process docs
- `AgentsMD_PRPs_and_AgentMemory/PRPs/templates/` — canonical templates for drafting base, planning, spec, and tasks packets
- `AgentsMD_PRPs_and_AgentMemory/.codex/commands/` — declarative automation manifests (sync, validation, rapid-development experiments)
- `Reference Code/` — automation + catalog for downloading upstream SDKs (`vendor/` is populated locally)
- `swarms-master/` — swarms orchestration library (reference)
- `.gitattributes` — LFS rules for media (note: currently contains junk bytes to clean later)

## 3) Getting Started
Prerequisites
- Python 3.11+, Node 18+, Docker + Docker Compose, Neo4j 5.x (container), optional Qdrant/Chroma

Environment
- Create `.env` with: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `VECTOR_DIR=./storage/vector`

Install (suggested commands)
- Python: create venv, install backend deps (to be defined in project setup)
- Node: install UI deps when UI folder is added

Reference SDK acquisition
1. Ensure Git and Python 3.11+ are installed; install PyYAML for catalog parsing:
   ```bash
   pip install --upgrade pyyaml
   ```
2. Synchronise all catalogued upstream repositories into `Reference Code/vendor/`:
   ```bash
   python Reference\ Code/sync_reference_code.py --dest "Reference Code/vendor"
   ```
3. (Optional) Clone a single dependency manually if the automation cannot reach GitHub:
   ```bash
   git clone --depth 1 --branch v0.2.27 https://github.com/microsoft/autogen.git "Reference Code/vendor/agent-framework-main"
   git clone --depth 1 https://github.com/run-llama/llama-hub.git "Reference Code/vendor/llama-hub"
   git clone --depth 1 https://github.com/kyegomez/swarms.git "Reference Code/vendor/swarms-master"
   ```
4. Confirm `Reference Code/vendor/` is excluded from Git (see `Reference Code/.gitignore`).

Run
- Use Docker Compose (to be added) to bring up api, Neo4j, and vector DB
- Forensics artifacts output to `./storage/forensics/{fileId}/` once implemented

## 4) Key Components
- PRPs: see `AgentsMD_PRPs_and_AgentMemory/PRPs/*` — base, planning, spec, tasks
- Rebuilt TRD/PRP: `AgentsMD_PRPs_and_AgentMemory/PRPs/ai_docs/TRD-PRP_legal_tech_2_rebuilt_msagents_llamaindex_swarms.md`
- Reference SDKs: `Reference Code/agent-framework-main`, `Reference Code/llama-hub`, `swarms-master/`

## 5) Dev Workflow
- Draft/refine PRPs; implement minimal diffs; validate via gates
- Conventional commits; small PRs; OTel traces in agents workflow

## 6) Architecture Decisions
- Local-first RAG; GraphRAG via Neo4j; MS Agents for workflow; Swarms for roles
- Cite-or-silence policy; persistent telemetry

## 7) Common Tasks
- Add loader: register LlamaHub reader, update ingestion config
- Add graph relation: extend ontology + Cypher upserts
- Add endpoint: extend API spec under PRP Spec doc

## 8) Gotchas
- `.gitattributes` corruption — clean before committing media changes
- Large reference repos — commit selectively; use LFS for assets

## 9) Docs & Resources
- PRP templates under `AgentsMD_PRPs_and_AgentMemory/PRPs/templates/`
- Process commands under `AgentsMD_PRPs_and_AgentMemory/.codex/commands/` (e.g., `validate-doc-links`, `sync-reference-assets`; see `rapid-development/experimental/prp-analyze-run.md` for the analysis log template)

## 10) Next Steps Checklist
1. Read PRP base/spec/planning/tasks
2. Configure `.env`, start services via compose
3. Implement ingestion + graph upserts on sample corpus
4. Validate retrieval with citations; log traces
5. Add minimal UI for chat + timeline
