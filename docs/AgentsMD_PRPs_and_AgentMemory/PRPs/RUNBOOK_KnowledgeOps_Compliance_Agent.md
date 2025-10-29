# KnowledgeOps Runbook — Compliance Agent Operations

## 1. Mission Profile
- **Objective:** Detect privilege leakage, regulatory exposure, and remediation gaps before disclosures.
- **Personas:** Compliance reviewers, privacy counsel, regulatory programme managers.
- **Tooling:** `agents/toolkit/packs/compliance_baseline.yaml`, `agents/toolkit/fixtures/compliance_baseline.json`, backend agents service (`/agents/run`).

## 2. Prerequisites
- Research agent must pass baseline evaluation (see Research Runbook) to ensure shared traces are available.
- Compliance policies referenced: attorney-client privilege matrix, SEC disclosure checklist, GDPR DPIA workflow.
- Backend security checks: mutual TLS enabled (`pytest backend/tests/test_security_mtls.py`).

## 3. Prompt & Fixture Validation
1. Validate prompt pack integrity:
   ```bash
   python -c "from agents.toolkit import PromptPack; print(PromptPack.load('agents/toolkit/packs/compliance_baseline.yaml').checksum)"
   ```
2. Review fixture expectations to align reviewers on escalation thresholds:
   ```bash
   python -c "from agents.toolkit import FixtureSet; fs = FixtureSet.load('agents/toolkit/fixtures/compliance_baseline.json');\nprint({case.case_id: case.expected['max_privileged_documents'] for case in fs.cases})"
   ```
3. Confirm telemetry expectations (latency budgets, required documents) are documented in the deployment ticket.

## 4. Operational Steps
1. **Sandbox evaluation:** run the evaluation harness locally using an orchestrator stub or staging endpoint.
2. **Calibrate privilege heuristics:** ensure the orchestrator surfaces `telemetry.privileged_docs` and per-document privilege labels.
3. **Deploy compliance prompts:** update orchestration configuration to point to `privilege_review` and `regulatory_gap_analysis` templates.
4. **Execute smoke tests:**
   ```bash
   curl -s -X POST http://localhost:8000/agents/run \
     -H "Authorization: Bearer <token>" \
     -d '{"case_id": "sandbox", "question": "Privileged content sweep?"}' | jq '.errors'
   ```
5. **Document outcomes:** capture evaluation summary, telemetry snapshots, and any escalations in build logs and compliance tracking systems.

## 5. Evaluation Criteria
- Success rate target: **≥ 0.85** across compliance fixture suite.
- Each case must satisfy:
  - `assert_contains_terms` (ensures escalation language present).
  - `assert_minimum_citations` and `assert_required_documents`.
  - `assert_privileged_within_bounds` (hotlist must not exceed allowed privileged documents).
- Telemetry expectations:
  - `telemetry.errors` empty on successful runs; non-empty results trigger incident review.
  - `telemetry.retries` indicates backend resilience was exercised; review backend logs for root cause.

## 6. Escalation Matrix
- **Privilege breach:** immediate notification to legal operations with document IDs and recommended actions.
- **Regulatory gap:** create remediation task with owner and due date; update `docs/AgentsMD_PRPs_and_AgentMemory/PRPs/TASK_LIST_MASTER.md`.
- **Circuit breaker open:** coordinate with platform engineering; reference `backend/app/services/agents.py` circuit breaker settings and adjust thresholds if sustained load occurs.

## 7. Artefact References
- Prompt pack: `agents/toolkit/packs/compliance_baseline.yaml`
- Fixtures: `agents/toolkit/fixtures/compliance_baseline.json`
- Evaluation harness: `agents/toolkit/evaluation.py`
- Backend resilience implementation: `backend/app/services/agents.py`
- Timeline error taxonomy (for cross-team alignment): `backend/app/services/timeline.py`
