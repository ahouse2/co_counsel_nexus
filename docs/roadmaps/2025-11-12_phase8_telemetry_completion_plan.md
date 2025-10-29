# Phase 8 Telemetry Completion Plan

## 1. Mission Overview
- Objective: finish telemetry instrumentation rollout for retrieval and forensics services with deterministic unit tests.
- Constraints:
  - Tests must avoid external exporters; rely on in-process stubs.
  - Maintain compatibility with existing telemetry bootstrap design.
- Success Criteria:
  - `pytest backend/tests -q` passes on clean environment.
  - Telemetry tests assert spans/metrics via stubbed providers.

## 2. Execution Tree
- ### 2.1 Environment Priming
  - #### 2.1.1 Settings Hygiene
    - Confirm telemetry env vars toggled via helper.
    - Ensure caches reset between tests.
  - #### 2.1.2 Telemetry Bootstrap Isolation
    - Monkeypatch exporter factory to stubbed variant.
    - Guard against accidental network/exporter usage.
- ### 2.2 Test Harness Refactor
  - #### 2.2.1 Stub Architecture
    - Reuse `RecordingTracer`, `RecordingSpan`, `RecordingCounter`, `RecordingHistogram` structures.
    - Provide container struct for grouped instruments per service under test.
  - #### 2.2.2 Retrieval Assertions
    - Patch `_tracer` and metric instruments in `backend.app.services.retrieval`.
    - Validate span attributes for query/vector spans.
    - Assert metric counters/histograms record expected values.
  - #### 2.2.3 Forensics Assertions
    - Patch `_tracer` and metric instruments in `backend.app.services.forensics`.
    - Validate pipeline + stage spans capture duration attributes and fallback status.
    - Confirm counters/histograms record increments with correct attributes.
  - #### 2.2.4 Helper Simplification
    - Replace exporter-centric `_bootstrap_telemetry` with stub-first bootstrap returning fixtures.
- ### 2.3 Regression Sweep
  - #### 2.3.1 Pytest Suite
    - Execute `pytest backend/tests -q`.
    - If failures appear, iterate until suite is green.
  - #### 2.3.2 Stewardship Artefacts
    - Update AGENTS chain log with activity summary.
    - Record build log entry referencing telemetry completion.

## 3. Validation Notes
- Expectation: retrieval query result includes spans `retrieval.query`, `retrieval.vector_search`.
- Metrics: counters/histograms invoked once per query/pipeline run.
- Stage metrics should capture at least canonicalise/metadata/analyse stages.

## 4. Post-Execution Checklist
- ✅ Telemetry tests deterministic with stubs.
- ✅ Repository metadata updated (AGENTS log + build log).
- ✅ Final PR message summarises refactor + passing tests.
