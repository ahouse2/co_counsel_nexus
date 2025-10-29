# Master Roadmap — KnowledgeOps Toolkit & Resilience Expansion

## Volume I — KnowledgeOps Toolkit Codification
### Chapter 1 — Repository Cartography
- #### Section 1.1 — Baseline Reconnaissance
  - Document current `agents/` surface (only README).
  - Inspect existing PRP directives calling for KnowledgeOps tooling.
- #### Section 1.2 — Scope Definition Artifacts
  - Enumerate deliverables: prompt packs, deterministic fixtures, evaluation harness, documentation.
  - Capture interface requirements for research vs. compliance agents.

### Chapter 2 — Prompt Pack Architecture
- #### Section 2.1 — Schema Blueprint
  - Define dataclasses for prompt roles, metadata, and templating with validation constraints (system/user/critic turns).
  - Support serialization from YAML to guarantee reproducibility and versioning fields.
- #### Section 2.2 — Repository Layout
  - Create `agents/toolkit/packs/` with canonical research + compliance YAML packs, ensuring descriptive metadata.
  - Embed checksum/version headers for drift detection in evaluation harness.

### Chapter 3 — Deterministic Fixture System
- #### Section 3.1 — Fixture Specification
  - Draft JSON fixture schema covering question, corpus slice, expected assertions, rubric weights, and compliance controls.
  - Bake in PRP-aligned metadata (jurisdiction, privilege classification, doc set lineage).
- #### Section 3.2 — Loader Implementation
  - Implement fixture loader enforcing hash validation + RNG seeding for deterministic sampling.
  - Provide fixture selection APIs (by agent type, tag, or compliance posture).
- #### Section 3.3 — Storage Layout
  - Materialize `agents/toolkit/fixtures/` with curated research/compliance fixture sets.

### Chapter 4 — Evaluation Harness
- #### Section 4.1 — Metric Engine
  - Implement harness evaluating accuracy, citation coverage, latency, compliance leakage, privilege detection.
  - Support deterministic replay by capturing agent outputs + telemetry snapshot per fixture.
- #### Section 4.2 — Retry/Policy Hooks
  - Allow injection of scoring policies + failure handling for new agents.
  - Emit JSON + Markdown summary artifacts for onboarding.
- #### Section 4.3 — Toolkit API Surface
  - Publish entrypoints in `agents/toolkit/__init__.py` consolidating prompt packs, fixtures, harness.

### Chapter 5 — Documentation & Tests
- #### Section 5.1 — Contributor Guide
  - Author `agents/toolkit/README.md` detailing agent onboarding steps, pack format, fixture lifecycle, evaluation commands.
- #### Section 5.2 — Unit Verification
  - Add `agents/tests/test_toolkit.py` covering YAML/JSON parsing, deterministic fixture hashing, harness metrics, failure cases.

## Volume II — Agent & Timeline Resilience
### Chapter 6 — Error Taxonomy Design
- #### Section 6.1 — Classification Matrix
  - Define enums for component (`retrieval`, `forensics`, `qa`, `timeline`, `memory`, `telemetry`, `audit`).
  - Codify severity ladder (`info`, `warning`, `error`, `critical`) and retryability semantics.
- #### Section 6.2 — Data Model Integration
  - Extend `AgentThread` with `status` + `errors` payload, ensure persistence + API serialization.
  - Update timeline service to surface taxonomy-aware `WorkflowError` for malformed cursors/filters.

### Chapter 7 — Circuit Breakers & Retries
- #### Section 7.1 — Settings Augmentation
  - Introduce configurable retry attempts/backoff + circuit thresholds in `Settings` with environment overrides.
- #### Section 7.2 — Circuit Implementation
  - Create reusable `CircuitBreaker` with rolling failure window + cooldown.
  - Wrap retrieval/forensics/QA orchestration with retry loops + breaker gating.
- #### Section 7.3 — Telemetry & Audit
  - Record retry attempts + breaker transitions in telemetry + audit metadata.
  - Ensure audit trail receives taxonomy-coded failure events.

### Chapter 8 — Failure-Oriented Testing
- #### Section 8.1 — Unit Scenarios
  - Add tests simulating transient retrieval failure (ensuring retry then success) and hard failure (breaker trips, thread marked failed).
  - Validate timeline API returns taxonomy-coded errors on invalid cursor/time windows.
- #### Section 8.2 — Regression Safeguards
  - Update API contract tests for new `status`/`errors` fields + telemetry counters.

## Volume III — KnowledgeOps Runbooks & Stewardship
### Chapter 9 — Runbook Publication
- #### Section 9.1 — Draft Runbooks
  - Author KnowledgeOps Research Agent Runbook + Compliance Agent Runbook within `docs/AgentsMD_PRPs_and_AgentMemory/PRPs/`.
- #### Section 9.2 — Cross-Linking
  - Update onboarding + PRP references to point at new runbooks and toolkit docs.

### Chapter 10 — Stewardship Artefacts
- #### Section 10.1 — Build Log Entry
  - Append 2025-11-18 build log capturing scope, diff highlights, validation commands.
- #### Section 10.2 — ACE Memory Update
  - Add retriever/planner/critic capsule to `memory/ace_state.jsonl` reflecting execution + validations.
- #### Section 10.3 — Stewardship Ledger
  - Extend root `AGENTS.md` chain-of-stewardship entry with task summary + validation results.

