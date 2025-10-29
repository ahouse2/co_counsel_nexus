# Scenario Simulation Execution Plan — 2025-11-24

## 0. Orientation
- **Objective**: deliver a courtroom simulation experience spanning backend scripted exchanges, WebGL front-end, optional TTS, configuration UI, asset pipeline, automated tests, and authoring documentation.
- **Constraints**:
  - Integrate with existing Microsoft Agents orchestrator without regressing current workflows.
  - No placeholder logic; all features production-grade.
  - Maintain CI parity (pytest + vitest) and update stewardship artefacts (ACE log, build log, memory state).
- **Success Metrics**:
  - Deterministic scenario engine with ≥90% unit coverage.
  - Canvas animation renders at 60fps on mid-tier hardware (baseline: MacBook Pro 14).
  - TTS toggle defaults to off; enabling streams synthesized audio via existing Larynx stack within 2s.
  - Configuration UI persists selection and cross-links to evidence manifests.

## 1. Workstream Breakdown
- **1.1 Backend Scenario Engine**
  - 1.1.1 Define scenario schema (metadata, participants, scripted beats, dynamic prompt slots, evidence references).
  - 1.1.2 Implement registry loader (YAML backed with hot reload guard) under `backend/app/scenarios`.
  - 1.1.3 Build `ScenarioEngine` service integrating `AgentsService` for dynamic prompts; ensure deterministic seed support for tests.
  - 1.1.4 Extend FastAPI with `/scenarios` (list), `/scenarios/{id}` (detail), `/scenarios/run` (generate exchange transcripts + TTS presigned URLs placeholder replaced by actual audio handshake).
  - 1.1.5 Persist scenario runs to agent memory store (thread reuse) for auditability.

- **1.2 Voice/TTS Integration**
  - 1.2.1 Add settings for TTS endpoint/voice catalogue; expose `/tts/speak` streaming endpoint bridging to Larynx server with caching under `var/audio`.
  - 1.2.2 Extend scenario engine to request per-character voice synthesis when toggle enabled; asynchronous job with immediate signed URL response referencing audio artifact.
  - 1.2.3 Add retry/backoff + health check for TTS service.

- **1.3 Frontend Simulation Workspace**
  - 1.3.1 Introduce simulation context store (React) for scenario metadata, configuration state, run results, TTS preferences.
  - 1.3.2 Build configuration panel (scenario selector, participant toggles, evidence attachments) with accessible form controls.
  - 1.3.3 Implement Pixi.js canvas scene: stage layout, animated sprites per participant, speech bubble captions syncing with backend transcript; integrate Web Audio for TTS playback.
  - 1.3.4 Provide playback controls (play/pause, step, replay) and progress timeline.
  - 1.3.5 Wire into App navigation with dedicated section.

- **1.4 Asset Pipeline**
  - 1.4.1 Curate simulation spritesheets/backgrounds in `frontend/public/simulations` with hashed filenames.
  - 1.4.2 Update Vite build to copy assets + generate manifest for dynamic loading.
  - 1.4.3 Add npm script to validate asset integrity (dimensions, metadata) at build time.

- **1.5 Automated Tests**
  - 1.5.1 Backend pytest suite: scenario engine unit tests, API contract tests (FastAPI TestClient), TTS integration tests with httpx mock.
  - 1.5.2 Frontend vitest: component tests for config UI + store, snapshot tests for dialog captions.
  - 1.5.3 Visual regression harness using `@testing-library/react` + `pixelmatch` for canvas snapshot.

- **1.6 Documentation & Stewardship**
  - 1.6.1 Author `docs/simulations/authoring.md` detailing scenario schema, asset guidelines, TTS voice configuration.
  - 1.6.2 Append build log entry summarising work and tests executed.
  - 1.6.3 Update `memory/ace_state.jsonl` with ACE trio summary.
  - 1.6.4 Extend `AGENTS.md` stewardship log with contribution entry.

## 2. Decision Tree — Backend Scenario Engine
- **Schema Source Options**
  - YAML (human authoring) vs JSON (faster parse) vs Python module.
  - **Chosen**: YAML with pydantic validation.
    - Pros: editors comfortable, future designers can update without code release.
    - Cons: parse overhead negligible for <20 scenarios.
- **Dynamic Prompt Execution**
  - Option A: direct orchestrator run per dynamic beat.
  - Option B: embed into initial run with branches.
  - **Chosen**: orchestrator per beat with seeded question -> ensures reuse of retrieval/forensics.
- **Thread Persistence Strategy**
  - Option A: ephemeral thread per run.
  - Option B: reuse case thread to keep telemetry.
  - **Chosen**: new `ScenarioThreadRecord` persisted alongside, referencing base thread ID for audit.

## 3. Decision Tree — TTS Strategy
- **Synthesis Approach**
  - Option A: Real-time streaming via websocket.
  - Option B: HTTP chunked streaming via requests.
  - **Chosen**: HTTP streaming (requests iter_content) for simplicity; convert to base64 WAV.
- **Caching**
  - Option A: Always regenerate.
  - Option B: Cache by hash(question+voice+text).
  - **Chosen**: Cache by SHA256 -> ensures dedupe and reuse.
- **Failure Handling**
  - Circuit breaker shared with Agents? -> reuse existing pattern with new component `WorkflowComponent.TTS`.

## 4. Decision Tree — Frontend Rendering
- **Rendering Library**
  - Option A: Pixi.js (2D, easier).
  - Option B: Three.js (3D, heavier).
  - **Chosen**: Pixi.js + @pixi/react for React integration.
- **State Management**
  - Option A: Context + reducer.
  - Option B: Zustand/external store.
  - **Chosen**: Context + reducer (no new dependency besides Pixi ecosystem).
- **Caption Layout**
  - Option A: DOM overlay.
  - Option B: Canvas text.
  - **Chosen**: DOM overlay for accessibility + snapshot testing.

## 5. Execution Checklist (Atomic Tasks)
1. Scaffold backend `scenarios` package with schema + registry + sample YAML.
2. Implement `ScenarioEngine` with deterministic random + orchestrator integration.
3. Extend `WorkflowComponent` enum with `SCENARIO`/`TTS` if needed.
4. Add FastAPI routers for scenarios & tts.
5. Update models with pydantic classes for requests/responses.
6. Write pytest coverage for scenario service + API.
7. Implement TTS client bridging to Larynx.
8. Frontend: install Pixi dependencies, create Simulation context.
9. Build configuration panel component.
10. Build Pixi canvas component with animations + TTS playback.
11. Integrate scenario UI into App navigation.
12. Add vitest unit + snapshot tests.
13. Add visual regression harness (canvas to image via `@testing-library/react` + `toMatchImageSnapshot`).
14. Add assets + update Vite to include.
15. Update npm scripts & build pipeline for assets.
16. Document authoring workflow.
17. Update build log, memory, AGENTS log.
18. Run tests: `coverage run -m pytest backend/tests -q`; `npm run test -- --run`; `npm run build` for asset validation.

## 6. Risk Register
- **R1**: Orchestrator call per beat could be slow.
  - Mitigation: allow `max_turns` limit + ability to stub in tests.
- **R2**: Pixi snapshots may be flaky.
  - Mitigation: deterministic animation tick (advance by manual `app.ticker.update`).
- **R3**: Larynx may be unavailable in CI.
  - Mitigation: degrade gracefully; tests mock HTTP responses.

## 7. Validation Gates
- ✅ Unit tests (backend/frontend) green.
- ✅ Visual snapshots stable (CI baseline stored under `frontend/tests/__snapshots__`).
- ✅ Scenario list endpoint returns sample data.
- ✅ Simulation UI loads assets w/out network.
- ✅ Documentation cross-links to scenario YAML.
