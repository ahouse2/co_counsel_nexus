# Dev Agent Delivery Plan — Planner's Ledger

## Phase 0 · Orientation (Book: Context)
- ### Chapter 0.1 · Stakeholder Intent
  - Feature requests triaged by Dev Team agent must materialise as backlog records with improvement tasks.
  - Secure admin operators require visibility into proposals and a guarded apply flow with audit trails.
  - Generated diffs must survive linting and tests inside an isolated sandbox before admission.
- ### Chapter 0.2 · Constraints & Guardrails
  - RBAC enforced via Oso policies and mTLS/OAuth bindings already in place for the API.
  - Storage primitives currently back agent threads only; improvement tasks must co-exist without regression.
  - Audit trail integrity is sacrosanct; every administrative action must hash-chain correctly.

## Phase 1 · Data Foundations (Book: Memory Ledger)
- ### Chapter 1.1 · Schema Augmentation
  - Paragraph · Introduce dataclasses for `ImprovementTaskRecord` and `PatchProposalRecord` with ISO-8601 timestamps and status enums.
  - Paragraph · Serialise into dedicated `improvement_tasks/` namespace under the agent memory store to avoid thread collisions.
- ### Chapter 1.2 · Persistence APIs
  - Paragraph · Implement CRUD helpers: `write_task`, `append_proposal`, `update_task_status`, `read_task`, `list_tasks`, `find_task_by_feature`.
  - Paragraph · Guarantee atomic writes via existing `atomic_write_json` helper and safe path handling for untrusted IDs.

## Phase 2 · Dev Team Agents (Book: Orchestration)
- ### Chapter 2.1 · Planner Persona
  - Paragraph · Encode `DevTeamPlanner` to transform a `FeatureRequest` into an `ImprovementTaskRecord`, deduping by feature request ID and capturing planner notes + risk tags.
- ### Chapter 2.2 · Executor Persona
  - Paragraph · Implement `DevTeamExecutor` to craft `PatchProposalRecord` instances, invoking sandbox harness validation previews and persisting telemetry.
  - Paragraph · Embed Microsoft Agents semantics via planner/executor naming, telemetry hooks, and actor metadata propagation.

## Phase 3 · Sandbox Harness (Book: Validation)
- ### Chapter 3.1 · Workspace Fabrication
  - Paragraph · Copy repository into a temp directory, respecting `.git` for diff application fidelity, and apply diffs via `git apply --whitespace=nowarn`.
- ### Chapter 3.2 · Command Orchestration
  - Paragraph · Run configured lint/test commands sequentially with streaming capture, short-circuiting on failure, returning structured `SandboxExecutionResult` + per-command metrics.
- ### Chapter 3.3 · Error Semantics
  - Paragraph · Surface `SandboxExecutionError` when diff application or command execution fails catastrophically, packaging stdout/stderr for operator review.

## Phase 4 · Service & API Surface (Book: Interfaces)
- ### Chapter 4.1 · Service Layer
  - Paragraph · Create `DevAgentService` wiring planner/executor/store/harness, exposing `record_feature_request`, `list_proposals`, `apply_proposal` with audit logging.
- ### Chapter 4.2 · RBAC & Config
  - Paragraph · Extend settings for dev-agent audience, scopes, roles, and validation command defaults.
  - Paragraph · Add `authorize_dev_agent_admin` dependency plus Oso policy alignment; ensure audit metadata flows through security dependency instrumentation.
- ### Chapter 4.3 · FastAPI Endpoints
  - Paragraph · Implement `/dev-agent/proposals` (GET) and `/dev-agent/apply` (POST) using new Pydantic models, returning sandbox telemetry and backlog context.

## Phase 5 · Quality Net (Book: Assurance)
- ### Chapter 5.1 · Unit Tests
  - Paragraph · Simulate end-to-end proposal lifecycle in `agents/tests/test_dev_agent.py`, stubbing sandbox command runner, ensuring audit ledger entries exist and statuses transition correctly.
- ### Chapter 5.2 · Documentation
  - Paragraph · Author `docs/AgentsMD_PRPs_and_AgentMemory/PRPs/RUNBOOK_Dev_Agent.md` detailing governance, approval gates, rollback, and audit expectations.
- ### Chapter 5.3 · Stewardship Update
  - Paragraph · Append Chain-of-Stewardship log entry summarising changes, tests, rubric self-assessment.

## Phase 6 · Verification & Polish (Book: Finale)
- ### Chapter 6.1 · Self-Review Loops
  - Paragraph · Walk the diff twice, verifying typing, error handling, audit coverage, and doc coherence.
- ### Chapter 6.2 · Automated Checks
  - Paragraph · Execute targeted pytest suites for agents/back-end to confirm the new harness and service contract.
- ### Chapter 6.3 · Delivery Capsule
  - Paragraph · Prepare PR narrative capturing planner/executor integration, RBAC, sandbox harness, and governance doc.
