# Phase 8 Security Enforcement Execution Roadmap

## Volume I — Stabilising the Security Runtime
### Chapter 1 — Shared Test Infrastructure
- Paragraph 1 — Fixture consolidation
  - Sentence 1 — Promote the sample workspace fixture to `backend/tests/conftest.py` so every suite consumes identical evidence.
  - Sentence 2 — Delete duplicate fixtures in legacy modules (`test_api.py`, `test_agents.py`) to prevent divergence.

### Chapter 2 — Policy Engine Reliability
- Paragraph 1 — Policy hygiene
  - Sentence 1 — Normalise Polar policy rules to eliminate resource-block warnings while preserving scope/role gating.
  - Sentence 2 — Replace deprecated loader APIs in the authorization service and extend diagnostics.
- Paragraph 2 — Access heuristics
  - Sentence 1 — Enforce scope and role pre-flight checks in dependency layer with expressive failures.
  - Sentence 2 — Preserve case administrator escape hatch with observable telemetry.

## Volume II — Edge Handling & Redaction Guarantees
### Chapter 3 — mTLS Middleware Refinement
- Paragraph 1 — Temporal accuracy
  - Sentence 1 — Adopt timezone-aware certificate validity helpers to silence deprecation and ensure precision.
- Paragraph 2 — Structured responses
  - Sentence 1 — Confirm middleware surfaces JSON responses for certificate issues without bubbling raw exceptions.

### Chapter 4 — Research Analyst Guardrails
- Paragraph 1 — Endpoint outcomes
  - Sentence 1 — Verify ingestion status endpoint returns 403 rather than 500 when policy denies Research Analyst access.
  - Sentence 2 — Ensure failure modes cascade into tests that assert business semantics.

## Volume III — Verification & Stewardship
### Chapter 5 — Test Orchestration
- Paragraph 1 — Security suite validation
  - Sentence 1 — Execute `pytest backend/tests -q` ensuring all security scenarios now pass with descriptive responses.

### Chapter 6 — Stewardship Artifacts
- Paragraph 1 — Repository hygiene
  - Sentence 1 — Append stewardship log entry capturing tests and rubric alignment.
  - Sentence 2 — Prepare PR narrative summarising security enforcement maturation.
