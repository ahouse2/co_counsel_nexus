# Dev Agent Refinement Plan — Sandbox Reliability & Governance

## Phase 1 · Context Reconnaissance
- ### Inventory
  - #### Agents Toolkit
    - Inspect `agents/toolkit/sandbox.py` for diff application and workspace metadata semantics.
    - Confirm exception pathways and success envelopes align with Planner/Executor expectations.
  - #### Services & Security
    - Trace `DevAgentService.apply_proposal` to audit handling, proposal status transitions, and RBAC side effects.
    - Map endpoint models in `backend/app/models/api.py` to ensure schema coverage for validation outputs.
- ### Knowledge Capture
  - #### Constraints
    - Ensure sandbox maintains deterministic workspace identifiers for audit reproducibility without leaking host paths.
    - Preserve `SandboxExecutionResult` contract consumed by API models and persistence layers.

## Phase 2 · Design the Remediation
- ### Workspace Telemetry Enhancement
  - #### Objective
    - Emit unique workspace identifiers (per tempdir) and capture `git apply` outcomes as first-class command results.
  - #### Decision Matrix
    - Prefer structured `SandboxCommandResult` records over raising exceptions so downstream services can persist failure traces.
- ### Service-Level Failure Semantics
  - #### Objective
    - Guarantee proposal/application lifecycle marks tasks `needs_revision` on validation failure with serialized command output.
  - #### Decision Matrix
    - Continue surfacing HTTP 422 with detailed validation payload while appending audit trail entries.

## Phase 3 · Implementation Steps
- ### Toolkit Refactor
  - #### Tasks
    - Refactor `_apply_diff` to return `SandboxCommandResult`; short-circuit validation on non-zero return codes.
    - Ensure `validate()` records diff application attempts before running configured lint/test commands.
    - Normalize `workspace_id` to derive from the ephemeral directory root for uniqueness.
- ### Service & Tests
  - #### Tasks
    - Adjust `DevAgentService.apply_proposal` to consume the updated sandbox responses without relying on exceptions.
    - Expand `agents/tests/test_dev_agent.py` with success + failure scenarios, asserting persisted statuses and audit entries.
- ### Documentation Update
  - #### Tasks
    - Update the runbook governance section to reflect the enriched failure telemetry.

## Phase 4 · Validation & Handoff
- ### Automated Verification
  - #### Tasks
    - Run `PYTHONPATH=. pytest agents/tests/test_dev_agent.py -q` to ensure lifecycle scenarios pass.
- ### Stewardship Artefacts
  - #### Tasks
    - Append stewardship entry in root `AGENTS.md` summarizing changes and validation results.
    - Prepare PR message referencing sandbox telemetry enhancement and validation coverage.
