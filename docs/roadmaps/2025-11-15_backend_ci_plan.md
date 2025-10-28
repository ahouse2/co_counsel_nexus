# Backend CI Hardening and Bootstrap Roadmap

## Phase 0 — Context Assimilation
- ### Inputs
  - #### Repository Baselines
    - ##### backend/requirements.txt pin set requiring lockfile translation to uv semantics.
    - ##### Existing backend test harness under `backend/tests/` with coverage expectations documented in validation notebooks.
  - #### Operational Directives
    - ##### Root AGENTS.md mandates stewardship log updates and ACE artefact maintenance.
    - ##### User request emphasises linting (ruff), typing (mypy), pytest with coverage, caching heavy wheels, onboarding parity, and documentation refresh.
- ### Outputs
  - #### Structured execution plan captured prior to implementation.

## Phase 1 — Dependency Governance Foundations
- ### Step 1.1 — Toolchain Selection
  - #### Evaluate `uv` for lockfile generation aligning with requirements pins.
  - #### Confirm compatibility of `scripts/bootstrap_backend.sh` with local developer workflows and CI usage.
- ### Step 1.2 — Lockfile Materialisation
  - #### Execute `uv pip compile backend/requirements.txt --output-file backend/uv.lock`.
  - #### Validate lock contents for deterministic transitive resolution.
- ### Step 1.3 — Bootstrap Script Authoring
  - #### Provide deterministic env creation, dependency sync (via uv or pip fallback), and invocation guidance for lint/type/test.

## Phase 2 — CI Workflow Authoring
- ### Step 2.1 — Workflow Skeleton
  - #### Create `.github/workflows/backend_ci.yml` triggered on pull_request and pushes touching backend/ or scripts/ changes.
  - #### Set permissions minimal read.
- ### Step 2.2 — Job Definition
  - #### Setup Python (3.12) with caching for uv and pip wheels.
  - #### Reuse `scripts/bootstrap_backend.sh` to install dependencies and tooling.
  - #### Run ruff, mypy, and pytest with coverage xml/html outputs.
- ### Step 2.3 — Artifact Publishing
  - #### Upload `coverage.xml`, `htmlcov/`, and junit/pytest logs if produced.
  - #### Expose coverage summary via step output for future gating.

## Phase 3 — Local Experience Alignment
- ### Step 3.1 — Documentation Updates
  - #### Expand `docs/ONBOARDING.md` with bootstrap guidance, CI parity, and troubleshooting for uv caches.
  - #### Document new workflow responsibilities in `build_logs/` entry.
- ### Step 3.2 — Stewardship Trail
  - #### Append AGENTS.md Chain-of-Stewardship entry summarising deliverables, files touched, and verification results.

## Phase 4 — Quality Gates Integration
- ### Step 4.1 — Ruff Compliance
  - #### Address lint issues through precise code edits or targeted `# noqa` annotations where module ordering is intentional.
- ### Step 4.2 — Mypy Configuration
  - #### Introduce `mypy.ini` capturing scoped enforcement with incremental adoption (ignore complex service modules while logging TODO for expansion).
- ### Step 4.3 — Test Validation
  - #### Run `pytest backend/tests -q --cov=backend/app --cov-report=xml --cov-report=html` locally to ensure green suite.

## Phase 5 — Artefact Publication and Logging
- ### Step 5.1 — Build Log Entry
  - #### Draft `build_logs/2025-11-15_backend_ci.md` covering summary, timeline, metrics, and notes referencing command outputs.
- ### Step 5.2 — Final Audit
  - #### Verify formatting, rerun lint/type/test commands post-modifications.
  - #### Prepare final summary with citations and update memory/ace_state if required.
