# Dev Agent Runbook — Feature Backlog Stewardship

## 1. Mission Profile
- **Objective:** Continuously triage feature requests, translate them into improvement tasks, and deliver validated patch proposals through Microsoft Agents Planner/Executor personas.
- **Data Stores:** `AgentMemoryStore` namespaces `threads/` and `improvement_tasks/` with ISO-8601 timestamps and hash-chained audit events.
- **Execution Harness:** `agents.toolkit.sandbox.SandboxExecutionHarness` clones the repo, applies diffs via `git apply --whitespace=nowarn`, and runs configurable lint/test commands.

## 2. Governance & Approval Gates
1. **Triage Gate** – Planner ingests a feature request, dedupes by `feature_request_id`, annotates risk, and marks task `triaged`.
2. **Proposal Gate** – Executor publishes a patch proposal with rationale and diff reference; status remains `pending` until sandbox validation is executed.
3. **Validation Gate** – `/dev-agent/apply` triggers sandbox execution. Commands must exit `0` or the proposal is stamped `failed` and the task flips to `needs_revision`.
4. **Approval Gate** – Successful validation upgrades proposal status to `validated`, appends an approval entry with actor metadata, and moves task status to `approved`.
5. **Audit Gate** – Every gate interaction appends to the audit ledger (`category=dev_agent`, action `dev_agent.proposal.applied`) to satisfy compliance reviews.

## 3. Access Controls
- **Endpoint Surface:**
  - `GET /dev-agent/proposals` → list backlog tasks + proposals.
  - `POST /dev-agent/apply` → execute sandbox validation for a proposal.
- **RBAC:** `authorize_dev_agent_admin` enforces scope `dev-agent:admin` and roles `PlatformEngineer` or `AutomationService`. Case administrators bypass role checks per Oso policy.
- **mTLS/OAuth:** Requests must present a trusted client certificate and bearer token; audit metadata captures fingerprint, roles, and scopes for investigations.

## 4. Sandbox Workflow
1. **Workspace Fabrication:** Copy repo (including `.git`) into an ephemeral directory under `/tmp/dev-agent-*/workspace`.
2. **Diff Application:** Apply provided diff via `git apply --whitespace=nowarn`; failures raise `SandboxExecutionError` with captured stdout/stderr.
3. **Command Orchestration:** Execute `settings.dev_agent_validation_commands` sequentially. Results capture command, exit code, stdout/stderr, and duration.
4. **Result Envelope:** Validation results stored on the proposal (`validation`) and surfaced through API responses for operator review.

## 5. Rollback & Remediation
- **Failed Validation:** Proposal remains `failed`; planner revises diff or splits work. Task remains in `needs_revision` until a succeeding proposal validates.
- **Manual Rollback:** Operators may purge proposals via filesystem (`improvement_tasks/<task_id>.json`) using `AgentMemoryStore.purge` semantics or craft a superseding proposal.
- **Audit Repair:** Use `backend/app/utils/audit.py:AuditTrail.verify()` to confirm chain integrity post-incident. Append corrective events referencing the failed hash if tampering detected.
- **Sandbox Diagnostics:** Retry validation locally by exporting proposal diff and rerunning `SandboxExecutionHarness.validate()` with verbose commands. Store outputs alongside incident ticket.

## 6. Operational Tips
- Keep validation command lists lean but comprehensive (`ruff`, `python -m tools.qa.quality_gate`, targeted pytest shards).
- Tag planner notes with `[risk:<level>]` to accelerate triage in `/dev-agent/proposals`.
- Update `settings.dev_agent_validation_commands` in environment for branch-specific workflows (e.g., hotfix pipelines).

## 7. References
- `backend/app/agents/dev_team.py`
- `backend/app/services/dev_agent.py`
- `backend/app/storage/agent_memory_store.py`
- `agents/toolkit/sandbox.py`
- `agents/tests/test_dev_agent.py`
- `backend/app/security/dependencies.py`
