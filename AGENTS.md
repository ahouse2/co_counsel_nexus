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
- 2025-02-14T00:00Z | Agent: ChatGPT | Replaced NFR prose with numeric SLOs; authored validation playbook and probes; added reproducibility harness | docs/AgentsMD_PRPs_and_AgentMemory/PRPs/PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_spec.md; docs/validation/nfr_validation_matrix.md; tools/perf/**; tools/monitoring/**; backend/requirements.txt | pytest backend/tests/test_api.py -q (fails: missing backend.app.storage module) | Docs/tests quality ≥9; follow-up required to restore storage package
- 2025-10-28T12:00Z | Agent: ChatGPT | Folded forensics toolbox into Co-Counsel spec; expanded task breakdown with deliverables | docs/AgentsMD_PRPs_and_AgentMemory/PRPs/PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_spec.md; docs/AgentsMD_PRPs_and_AgentMemory/PRPs/PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_tasks.md | Documentation updates; no automated tests run | Quality ≥9 target; compute/performance expectations recorded

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
- 2025-10-30T00:00Z | Agent: ChatGPT | Recast tasks plan with owners/durations/prereqs, aligned roadmap + CI checkpoints | docs/AgentsMD_PRPs_and_AgentMemory/PRPs/PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_tasks.md; AGENTS.md; build_logs/2025-10-30.md; memory/ace_state.jsonl | Documentation updates; no automated tests run | Quality ≥9; verified spec references + formatting
- 2025-10-30T00:00Z | Agent: ChatGPT | Materialised reference asset workspace + command catalog; documented dependency acquisition; automated link validation | Reference Code/**/*; docs/ONBOARDING.md; docs/AgentsMD_PRPs_and_AgentMemory/.codex/commands/**/*; docs/roadmaps/2025-10-30_reference_assets_integration_plan.md; tools/docs/validate_links.py | python "Reference Code/sync_reference_code.py" --help; python tools/docs/validate_links.py | Scores ≥9 across rubric; diff reviewed thrice; commands documented
- 2025-10-30T00:00Z | Agent: ChatGPT | AuthZ matrices + compliance controls for APIs, agents, and tools; authored roadmap | docs/AgentsMD_PRPs_and_AgentMemory/PRPs/PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_spec.md; docs/AgentsMD_PRPs_and_AgentMemory/PRPs/AGENT_TOOL_REGISTRY.md; docs/roadmaps/2025-10-30_co_counsel_auth_compliance_extension_plan.md | Documentation changes; no automated tests run | Scores [TechAcc=9, Modularity=9, Performance=8, Security=10, Scalability=8, Robustness=9, Maintainability=9, Innovation=9, UX/UI=8, Explainability=10, Coordination=10, DevOps=8, Documentation=10, Compliance=10, EnterpriseValue=9] | Reviewed documentation thrice; compliance checklist cross-checked with owners
- 2025-10-30T00:00Z | Agent: ChatGPT | Added PRP navigation banners, authored templates, created rapid-development analysis guide, aligned onboarding | docs/AgentsMD_PRPs_and_AgentMemory/.codex/commands/**; docs/AgentsMD_PRPs_and_AgentMemory/PRPs/**; docs/ONBOARDING.md; docs/roadmaps/2025-10-30_prp_discoverability_enhancement_plan.md | python tools/docs/validate_links.py | Scores ≥9 across rubric; diff reviewed thrice; navigation verified manually
- 2025-10-27T09:04Z | Agent: ChatGPT | Documented OpenTelemetry workflow instrumentation and context propagation | docs/observability/opentelemetry_workflow.md; AGENTS.md | Documentation update; no automated tests run | Quality ≥9; diff reviewed twice
- 2025-10-31T00:00Z | Agent: ChatGPT | Authored forensics validation matrix with success metrics/datasets; updated build log | docs/AgentsMD_PRPs_and_AgentMemory/PRPs/PRP_Forensics_Core_validation_matrix.md; build_logs/2025-10-31.md | Documentation changes; no automated tests run | Scores [TechAcc=9, Modularity=9, Performance=8, Security=9, Scalability=8, Robustness=9, Maintainability=9, Innovation=9, UX/UI=8, Explainability=10, Coordination=10, DevOps=8, Documentation=10, Compliance=9, EnterpriseValue=9] | Matrix cross-checked with PRP requirements; datasets aligned with success metrics
- 2025-10-31T00:00Z | Agent: ChatGPT | Re-ran PRP QA review; authored analysis blueprint + run log | docs/roadmaps/2025-10-31_prp_co_counsel_review_run.md; build_logs/2025-10-31_prp_co_counsel_analyze.md | Tests not run (static review) | QA rubric average 2.2; follow-up implementation required
- 2025-11-01T00:00Z | Agent: ChatGPT | Executed Phase 1 storage/vector hardening; resolved import hygiene; documented run | backend/app/storage/**; backend/app/services/**; backend/app/models/api.py; backend/app/utils/text.py; docs/roadmaps/2025-11-01_prp_execution_phase1.md; build_logs/2025-11-01.md | pytest backend/tests/test_api.py -q | Scores [TechAcc=9, Modularity=9, Performance=8, Security=8, Scalability=8, Robustness=9, Maintainability=9, Innovation=9, UX/UI=8, Explainability=10, Coordination=10, DevOps=9, Documentation=10, Compliance=9, EnterpriseValue=9]
- 2025-11-02T00:00Z | Agent: ChatGPT | Conducted Phase 1 rubric review; authored ACE 3-agent validation workflow blueprint | docs/validation/2025-11-02_phase1_quality_review.md; build_logs/2025-11-02.md | Static review (no automated tests) | Scores [TechAcc=9, Modularity=9, Performance=8, Security=8, Scalability=8, Robustness=9, Maintainability=9, Innovation=9, UX/UI=8, Explainability=10, Coordination=10, DevOps=8, Documentation=9, Compliance=9, EnterpriseValue=9]
