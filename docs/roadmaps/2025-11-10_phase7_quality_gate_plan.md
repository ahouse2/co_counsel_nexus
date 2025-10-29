# Phase 7 — QA & Validation Execution Blueprint (2025-11-10)

## 1. Orientation & Intent
- ### 1.1 Mission Definition
  - #### 1.1.a Extend PRP Phase 7 scope by codifying an automated quality gate enforcing ≥85% backend coverage alongside full test execution.
  - #### 1.1.b Ensure tooling integrates with existing stewardship cadence (build logs, ACE memory, Chain of Stewardship log).
- ### 1.2 Current State Recon
  - #### 1.2.a Backend pytest suite currently green (12 tests) but lacks explicit coverage measurement.
  - #### 1.2.b No centralised QA command orchestrates regression + coverage thresholds; manual runs required.

## 2. Decision Tree Exploration
- ### 2.1 Coverage Mechanism Selection
  - #### 2.1.a **Option A:** Rely on `pytest-cov` plugin — introduces dependency sprawl; harder to unit test CLI.
  - #### 2.1.b **Option B:** Use `coverage.py` API directly with bespoke orchestration — grants deterministic control + testability.
  - #### 2.1.c **Decision:** Choose Option B; pin `coverage==7.6.4` for Python 3.11 compatibility and branch metrics readiness.
- ### 2.2 Invocation Strategy
  - #### 2.2.a Wrap pytest execution via programmable runner enabling dependency injection for unit tests.
  - #### 2.2.b Default arguments should target `backend/tests -q`, while allowing overrides via CLI `--` remainder handling.
- ### 2.3 Reporting Surfaces
  - #### 2.3.a Emit concise stdout summary (tests result + coverage percentage + threshold evaluation).
  - #### 2.3.b Optionally persist JSON summary for CI ingestion; align schema with existing logging practices.
- ### 2.4 Failure Semantics
  - #### 2.4.a Non-zero pytest exit should fail gate irrespective of coverage.
  - #### 2.4.b Coverage below threshold triggers failure with exit code `2` (distinct from pytest code `1`).
  - #### 2.4.c Exceptions during pytest run must still finalise coverage session before bubbling error.

## 3. Implementation Breakdown
- ### 3.1 Tooling Surface (`tools/qa/quality_gate.py`)
  - #### 3.1.a Implement `QualityGate` class encapsulating coverage lifecycle + pytest runner.
  - #### 3.1.b Provide `QualityGateResult` dataclass with derived flags (`tests_passed`, `coverage_passed`, `passed`).
  - #### 3.1.c Build CLI parser supporting `--threshold`, `--json-output`, `--source`, `--omit`, and remainder pytest args.
  - #### 3.1.d Ensure CLI defaults to backend coverage; pretty-print summary and write JSON when requested.
- ### 3.2 Automated Tests (`tools/tests/test_quality_gate.py`)
  - #### 3.2.a Mock coverage object to assert lifecycle calls and evaluate pass/fail semantics.
  - #### 3.2.b Cover error path ensuring coverage stop/save invoked when pytest runner raises.
  - #### 3.2.c Validate argument parsing normalises remainder semantics (strip leading `--`, apply defaults).
- ### 3.3 Dependency Governance
  - #### 3.3.a Add `coverage==7.6.4` to `backend/requirements.txt`, keeping alphabetical grouping.
- ### 3.4 Documentation & Task Alignment
  - #### 3.4.a Update `docs/AgentsMD_PRPs_and_AgentMemory/PRPs/PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_tasks.md` Phase 7 checklist to reflect automated unit coverage gate progress (mark Unit Coverage item complete, add note referencing new tool).
  - #### 3.4.b Author validation memo `docs/validation/2025-11-10_quality_gate_run.md` capturing metrics + usage instructions.
- ### 3.5 Stewardship Artefacts
  - #### 3.5.a Record execution narrative in `build_logs/2025-11-10.md` (inputs, commands, outcomes).
  - #### 3.5.b Append ACE memory entry summarising retriever/planner/critic cycle for QA gate.
  - #### 3.5.c Extend `AGENTS.md` Chain of Stewardship log with contribution details + rubric snapshot.

## 4. Validation Plan
- ### 4.1 Automated Commands
  - #### 4.1.a `pytest tools/tests -q` — ensure new unit tests pass.
  - #### 4.1.b `pytest backend/tests -q` — regression safety net.
  - #### 4.1.c `python -m tools.qa.quality_gate --threshold 85 -- backend/tests -q` verifying exit 0.
- ### 4.2 Manual Checklist
  - #### 4.2.a Confirm JSON summary (when generated) matches expected schema fields.
  - #### 4.2.b Double-check tasks doc renders correct checkboxes + references to tool.
  - #### 4.2.c Review requirements file ordering.

## 5. Contingencies & Follow-ups
- ### 5.1 Future Enhancements
  - #### 5.1.a Integrate CLI into CI workflows (`qa-suite`) once pipeline definitions land.
  - #### 5.1.b Extend quality gate to accept component-specific thresholds (agents vs. backend vs. tools).
- ### 5.2 Risk Mitigation
  - #### 5.2.a If coverage dips below threshold due to new modules, ensure gate outputs actionable diff (per-file soon).
  - #### 5.2.b Provide fallback to disable JSON output gracefully when path unwritable (raise descriptive error).
