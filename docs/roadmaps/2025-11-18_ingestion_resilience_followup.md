# 2025-11-18 Ingestion Resilience Follow-Up Roadmap

## Phase I — Context Reconnaissance
- ### Objective A — Inventory Code Surfaces
  - #### Step 1 — Catalogue service entry points
    - ##### Action a — Trace `backend/app/services/ingestion.py` async workflow to identify undefined symbols.
    - ##### Action b — Map actor derivation helpers (`_actor_from_principal`, `_job_actor`, `_system_actor`).
  - #### Step 2 — Align stewardship artefacts
    - ##### Action a — Review prior AGENTS.md entries for resilience notes.
    - ##### Action b — Extract pending TODOs from `build_logs/2025-11-18.md` once updated post-fix.
- ### Objective B — Confirm Reproducibility Steps
  - #### Step 1 — Enumerate mandatory regressions
    - ##### Action a — `pytest agents/tests/test_toolkit.py -q`
    - ##### Action b — `pytest backend/tests -q`
  - #### Step 2 — Establish diagnostic checkpoints
    - ##### Action a — Capture failing stack traces pre-fix for comparison.

## Phase II — Implementation Blueprint
- ### Objective A — Restore Actor Context in `_run_job`
  - #### Step 1 — Select actor source of truth
    - ##### Action a — Prefer `_job_actor(job_record)` to leverage persisted principal metadata.
  - #### Step 2 — Refactor method signature safely
    - ##### Action a — Introduce `actor = self._job_actor(job_record)` at method start.
    - ##### Action b — Ensure audit calls reuse local `actor`.
    - ##### Action c — Verify no redundant writes occur to `job_record` before actor initialisation.
- ### Objective B — Validate Downstream Behaviour
  - #### Step 1 — Execute asynchronous workflow tests
    - ##### Action a — Run regression suite commands enumerated above.
  - #### Step 2 — Inspect test artefacts
    - ##### Action a — Confirm ingestion citations populated in `backend/tests/test_agents.py`.
    - ##### Action b — Resolve any residual connector import errors (e.g., `msal`, `reference`).

## Phase III — Stewardship Consolidation
- ### Objective A — Document Execution Trail
  - #### Step 1 — Update `build_logs/2025-11-18.md`
    - ##### Action a — Append executed commands with outcomes.
  - #### Step 2 — Extend `memory/ace_state.jsonl`
    - ##### Action a — Record retriever/planner/critic summary for this intervention.
- ### Objective B — Chain of Stewardship Entry
  - #### Step 1 — Append AGENTS.md log entry with rubric ratings ≥9.
  - #### Step 2 — Highlight remaining follow-ups if connector issues persist.

## Phase IV — Quality Assurance Loops
- ### Objective A — Personal Code Review Passes
  - #### Step 1 — Perform tri-pass diff inspection ensuring no latent TODOs.
  - #### Step 2 — Cross-verify audit event payload consistency post-change.
- ### Objective B — Final Sign-Off Criteria
  - #### Step 1 — Green suites for agents + backend tests.
  - #### Step 2 — Updated documentation and memory assets committed.
  - #### Step 3 — PR message synthesised via `make_pr` after commit.
