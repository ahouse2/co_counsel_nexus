# Frontend Simulation Phase Notes — 2025-11-24

## 0. Phase Orientation
- Objective: finish simulation UI/UX, integrate ScenarioProvider, deliver testing + docs.
- Constraints: no placeholder UI, deterministic tests, respect asset manifest pipeline.

## 1. Work Breakdown
- 1.0 Scenario Context Completion
  - 1.0.1 Add case id handling + evidence typing.
  - 1.0.2 Ensure configuration validation enforces case id + required inputs.
  - 1.0.3 Wire TTS preview error handling.
- 1.1 Simulation Components
  - 1.1.1 Build `SimulationCanvas` (Pixi + fallback) with caption overlay.
  - 1.1.2 Build `ScenarioConfigurator` with scenario selector, participants, variables, evidence, TTS toggle, voice preview.
  - 1.1.3 Build `SimulationWorkbench` layout + playback controls + transcript timeline.
- 1.2 Integration
  - 1.2.1 Wrap app with `ScenarioProvider`.
  - 1.2.2 Add Simulation tab to `App.tsx` navigation.
  - 1.2.3 Update styles for new layout.
- 1.3 Testing
  - 1.3.1 Vitest coverage for ScenarioContext + SimulationWorkbench interactions.
  - 1.3.2 Visual fallback snapshot for SimulationCanvas.
- 1.4 Documentation
  - 1.4.1 Author simulation authoring guide.
  - 1.4.2 Update stewardship logs (AGENTS.md, ACE, build log).

## 2. Decision Notes
- Pixi fallback is mandatory for SSR/tests → `forceFallback` prop + DOM overlay snapshot.
- Playback heuristics: fallback to 320ms/word (min 2.5s) when duration missing.
- Audio playback uses Web Audio (HTMLAudioElement) with test stub to avoid jsdom gaps.

## 3. Validation Gates
- ✅ `npm run test -- --run`
- ✅ `npm run build`
- ✅ `coverage run -m pytest backend/tests -q`
- ✅ Docs + logs appended.
