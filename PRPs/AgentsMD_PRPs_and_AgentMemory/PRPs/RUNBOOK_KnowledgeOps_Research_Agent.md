# KnowledgeOps Runbook — Research Agent Onboarding

## 1. Mission Profile
- **Objective:** Deliver timeline-centric, evidence-backed answers for corporate investigations under the KnowledgeOps programme.
- **Personas:** Research analysts, discovery engineers, PRP implementers.
- **Tooling:** `agents/toolkit/packs/research_baseline.yaml`, `agents/toolkit/fixtures/research_baseline.json`, backend agents service (`/agents/run`).

## 2. Prerequisites
- Complete ingestion of the target workspace (see `docs/roadmaps/2025-11-04_prp_execution_phase2.md`).
- Verify graph enrichment and forensics artefacts are present (`pytest backend/tests/test_api.py -k timeline`).
- Install KnowledgeOps toolkit dependencies (PyYAML available via repo bootstrap).

## 3. Prompt & Fixture Alignment
1. Load the prompt pack:
   ```bash
   python -c "from agents.toolkit import PromptPack; print(PromptPack.load('agents/toolkit/packs/research_baseline.yaml').checksum)"
   ```
2. Inspect fixtures for scenario coverage:
   ```bash
   python -c "from agents.toolkit import FixtureSet; fs = FixtureSet.load('agents/toolkit/fixtures/research_baseline.json'); print([c.case_id for c in fs.cases])"
   ```
3. Confirm checksums match the runbook baseline:
   - `research_baseline.yaml` checksum → record in deployment log.
   - `research_baseline.json` checksum → append to ACE memory capsule.

## 4. Orchestration Procedure
1. **Warm the retrieval stack:** execute `/query` smoke test with `rerank=false` to ensure vector index readiness.
2. **Execute research harness locally:**
   ```bash
   python - <<'PY'
   from agents.toolkit import EvaluationHarness, FixtureSet, PromptPack

   pack = PromptPack.load('agents/toolkit/packs/research_baseline.yaml')
   fixtures = FixtureSet.load('agents/toolkit/fixtures/research_baseline.json')
   harness = EvaluationHarness(pack, fixtures, template_id='case_synthesis')

   # Replace with actual orchestrator invocation
   def orchestrator(case, template):
       messages = template.render(question=case.question, context=case.context, references='\n\n'.join(d.title for d in case.documents))
       # call backend /agents/run or direct service here
       raise NotImplementedError('wire orchestrator')

   harness.run(orchestrator)
   PY
   ```
3. **Deploy agent service:** use `/agents/run` endpoint with new prompt pack selection (if multiple templates exposed via orchestrator configuration).
4. **Capture artefacts:** store prompt pack checksum, fixture checksum, evaluation summary, and `/agents/run` telemetry in build logs and memory (`memory/ace_state.jsonl`).

## 5. Evaluation Gates
- Minimum success rate: **≥ 0.9** across research fixture suite.
- Each case must satisfy:
  - `assert_contains_terms`, `assert_minimum_citations`, `assert_required_documents`, `assert_privileged_within_bounds`.
  - Latency under configured `max_latency_ms` (defaults to 1.6s in baseline fixtures).
- Telemetry checks:
  - `telemetry.errors` must be empty for successful runs.
  - `telemetry.retries` should be empty in steady-state; investigate non-empty results.

## 6. Escalation Protocol
- **Privilege alerts:** escalate to Compliance runbook if `telemetry.privileged_docs > 0` or QA notes include privilege warnings.
- **Regulatory gaps:** open ticket in regulatory gap tracker (`docs/AgentsMD_PRPs_and_AgentMemory/PRPs/TASK_LIST_MASTER.md`) referencing affected documents.
- **Circuit breaker trips:** review backend logs; reset via `backend.app.services.agents.reset_agents_service()` after remediating root cause.

## 7. Artefact References
- Prompt pack: `agents/toolkit/packs/research_baseline.yaml`
- Fixtures: `agents/toolkit/fixtures/research_baseline.json`
- Backend service: `backend/app/services/agents.py`
- Evaluation harness: `agents/toolkit/evaluation.py`
- Timeline error taxonomy reference: `backend/app/services/timeline.py`
