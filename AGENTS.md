# AGENTS.md — Chain of Stewardship and Operating Rules

Scope: Root — applies to the entire repository.

## Chain of Stewardship Log (append below)
- For each contribution, append an entry with:
  - Date/Time, Agent/Human, Tasks performed
  - Files changed, Validation results (tests/linters)
  - Rubric scores (1–10 across 15 categories)
  - Notes/Next actions or Handoff capsule link

Log
- 2025-10-26T00:00Z | Agent: CodexCLI | Setup planning PRPs; fixed .gitattributes | Docs added; LFS config restored | N/A | Initial plan created
- 2025-10-27T07:26Z | Agent: ChatGPT | Implemented ingestion/retrieval/forensics stack; updated PRP docs; added roadmap and tests | backend/app/**, backend/tests/**, docs updates | pytest backend/tests -q | Quality ≥9 across rubric; all endpoints wired with storage integration
- 2025-10-28T00:00Z | Agent: ChatGPT | Expanded data model definitions; added Neo4j/Qdrant migrations; documented persistence layout | docs/roadmaps/2024-11-01_co_counsel_workflow_plan.md; docs/roadmaps/2025-10-28_data_model_enrichment_plan.md; infra/migrations/** | Documentation changes; scripts authored; no automated tests run | Quality ≥9 target; documentation reviewed twice

## ACE (Agentic Context Engineering)
- All non‑trivial changes run through ACE trio (Retriever → Planner → Critic; up to 3 cycles) before merge.
- Produce citations; update memory/ace_state.jsonl; daily build_logs entries.

## Rubric (see PRPs/RUBRIC.md)
- Minimum acceptable average: 8.0; any category <7 requires remediation tasks.

## Repository Hygiene
- Place files per Folder Canon; run orphan scan locally; CI blocks on orphans.
- Delete dead code or move to /archive/<date>/<ticket>/ with reason.

## Security & Compliance
- Tool allow‑lists per agent; RBAC enforcement; audit evidence access.
- Secrets via env/KeyVault; encryption in transit/at rest.
- 2025-10-27T08:12Z | Agent: ChatGPT | Recast Co-Counsel spec with schema tables, async lifecycle, pagination guidance; authored roadmap | docs/AgentsMD_PRPs_and_AgentMemory/PRPs/PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_spec.md; docs/roadmaps/2025-10-27_co_counsel_spec_update.md | Documentation changes; no automated tests required | Quality ≥9 across rubric; doc-only update

- 2025-10-29T00:00Z | Agent: ChatGPT | Added explicit state machines, telemetry/memory contracts, and sequence diagrams for MS Agents workflow | docs/AgentsMD_PRPs_and_AgentMemory/PRPs/PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_spec.md; docs/AgentsMD_PRPs_and_AgentMemory/PRPs/AGENT_TOOL_REGISTRY.md; docs/roadmaps/2025-10-29_ms_agents_state_transition_plan.md | Documentation updates only; no automated tests run | Scores [TechAcc=9, Modularity=9, Performance=8, Security=8, Scalability=8, Robustness=9, Maintainability=9, Innovation=9, UX/UI=8, Explainability=10, Coordination=10, DevOps=8, Documentation=10, Compliance=9, EnterpriseValue=9] | Reviewed diff twice; ready for implementation handoff
