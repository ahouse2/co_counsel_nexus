# 2025-11-09 Bug Review and Remediation Plan

## Phase 0: Orientation
- ### P0.1 Establish scope and success criteria
  - #### P0.1.a Catalogue directives from AGENTS.md (root scope applies repository-wide).
  - #### P0.1.b Confirm requirement to produce stewardship artefacts (ACE state, build log, root log entry).
- ### P0.2 Identify validation surfaces
  - #### P0.2.a Enumerate automated test suites (backend, tools) for regression detection.
  - #### P0.2.b Note prior failure reports in Chain of Stewardship (e.g., dependency gaps, ACE workflow regressions).

## Phase 1: Reconnaissance
- ### P1.1 Execute regression probes
  - #### P1.1.a Run `pytest backend/tests -q` to validate service stack.
  - #### P1.1.b Run `pytest tools/tests -q` to surface ACE tooling defects.
- ### P1.2 Record observed failures
  - #### P1.2.a Capture missing dependency exception (`ModuleNotFoundError: jsonschema`).
  - #### P1.2.b Cross-check previous build logs for similar dependency regressions to confirm unresolved status.

## Phase 2: Root Cause Analysis
- ### P2.1 Trace import graph
  - #### P2.1.a Inspect `tools/ace/schema.py` for external library usage.
  - #### P2.1.b Verify absence of `jsonschema` declaration in managed dependency manifests.
- ### P2.2 Assess blast radius
  - #### P2.2.a Determine whether backend runtime indirectly exercises ACE schema validators.
  - #### P2.2.b Evaluate impact on CI workflows relying on `tools/tests/test_ace_pipeline.py`.

## Phase 3: Remediation Design
- ### P3.1 Dependency governance
  - #### P3.1.a Select authoritative requirements file (current shared environment: `backend/requirements.txt`).
  - #### P3.1.b Specify pinned version for `jsonschema` aligning with Draft7 validator usage.
- ### P3.2 Stewardship artefacts
  - #### P3.2.a Plan additions to `build_logs/2025-11-09.md` capturing context, actions, validations.
  - #### P3.2.b Outline ACE memory append with retriever/planner/critic narrative for this remediation.
  - #### P3.2.c Prepare Chain of Stewardship log entry summarizing effort and results.

## Phase 4: Implementation Steps
- ### P4.1 Modify dependency manifest
  - #### P4.1.a Insert `jsonschema==4.23.0` (latest stable Draft7 support) into `backend/requirements.txt` maintaining sorted grouping.
- ### P4.2 Update documentation/logs
  - #### P4.2.a Author `build_logs/2025-11-09.md` reflecting execution chronology.
  - #### P4.2.b Append ACE state entry capturing artefacts, checks, and follow-ups.
  - #### P4.2.c Extend root `AGENTS.md` Chain of Stewardship log with final metrics.

## Phase 5: Validation & Quality Gate
- ### P5.1 Environment preparation
  - #### P5.1.a Install updated dependencies via `pip install -r backend/requirements.txt` (ensure `jsonschema` available for tests).
- ### P5.2 Regression testing
  - #### P5.2.a Re-run `pytest tools/tests -q` (expect pass after dependency resolution).
  - #### P5.2.b Spot-check backend suite (`pytest backend/tests -q`) to guard against collateral regressions.
- ### P5.3 Final review
  - #### P5.3.a Diff inspection ensuring no unintended files modified.
  - #### P5.3.b Commit changes with descriptive message; invoke PR generator per instructions.
  - #### P5.3.c Conduct final self-review ensuring zero TODOs remain for this scope.
