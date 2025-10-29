# Scenario Simulation Authoring Guide

## 1. Overview
- Deliver immersive courtroom walkthroughs by scripting exchanges in YAML, orchestrating dynamic beats through the Scenario Engine, and presenting playback with Pixi-powered animation plus optional voice synthesis.
- Assets, configuration, and documentation follow the roadmap defined in `docs/roadmaps/2025-11-24_scenario_simulation_execution_plan.md`.

## 2. Backend Authoring Workflow
### 2.1 Scenario Library
- Store scenario definitions under `backend/app/scenarios/library/` using `.yaml` files validated by `ScenarioDefinition`.
- Core fields:
  - `scenario_id`, `title`, `description`, `category`, `difficulty`, `tags`.
  - `participants`: id, name, role, description, sprite (relative path), accent_color, voice (Agents SDK voice id), default, optional.
  - `variables`: keyed map with name, description, required, default.
  - `evidence`: id, label, description, required, type, optional `document_id` default.
  - `beats`: sequence with `id`, `kind` (`scripted` | `dynamic`), `speaker`, optional `delegate`, `stage_direction`, `emphasis`, `duration_ms`, `fallback_text`, `top_k`.
- Use `${variable}` placeholders inside scripted beats; dynamic beats call Agents SDK delegates defined in the beat metadata.

### 2.2 Dynamic Prompts
- Dynamic beats supply `delegate` identifiers that map to Agents orchestrations. The Scenario Engine expands variables/evidence and invokes delegates through the Microsoft Agents SDK adapter, seeded by the `case_id` and participant roster.
- Provide deterministic seeds (set `seed` per beat if reproducibility required) and guard `top_k` for retrieval fan-out.

### 2.3 Persistence & Telemetry
- Runs persist through `ScenarioRunRecord` in `AgentMemoryStore`, tying `run_id` to `case_id`, participants, variables, evidence bindings, and transcript/telemetry payloads.
- Use `/scenarios/run` to trigger simulations and `/scenarios/{id}` for static definitions. TTS toggles synthesize audio for each beat when `enable_tts` is true.

## 3. Frontend Authoring Workflow
### 3.1 Asset Manifest
- Stage assets live under `frontend/public/simulations/`.
- Maintain `manifest.json` with:
  - `stage`: width, height, background image path, and per-character coordinates.
  - `characters`: sprite path and accent color keyed by participant id.
- Validate assets with `npm run validate:sim` (calls `scripts/validate-sim-assets.mjs`). The script checks file existence, dimensions, and manifest parity.

### 3.2 UI Integration
- `ScenarioProvider` fetches metadata, loads scenario definitions, validates required variables/evidence, and executes runs through `/scenarios/run` plus `/tts/speak` for previews.
- `SimulationWorkbench` composes:
  - `ScenarioConfigurator`: scenario selector, participant toggles, variable/evidence entry, case id capture, TTS toggle, and voice preview controls.
  - `SimulationCanvas`: Pixi-driven or fallback DOM stage with animated participants and captions.
  - Transcript timeline, progress controls, and telemetry inspector.
- Wrap the SPA with `ScenarioProvider` in `frontend/src/main.tsx`. The Simulation tab is exposed from `App.tsx` navigation.

### 3.3 Voice & Playback
- Voice previews call `/tts/speak` with sample text; scenario runs embed audio metadata that `SimulationWorkbench` streams with Web Audio.
- Playback controls (play/pause/step/restart) advance beats using `duration_ms` heuristics. When durations are omitted, the UI uses 320 ms/word minimum 2.5 seconds.
- Captions overlay the canvas for accessibility; transcript list mirrors the active beat for keyboard navigation.

## 4. Testing & Validation
- Backend: run `coverage run -m pytest backend/tests -q` to ensure Scenario Engine + API coverage.
- Frontend: run `npm run test -- --run` for vitest suites, including context logic, UI interaction, and deterministic visual snapshot (`simulationCanvas.snapshot.test.tsx`).
- Asset integrity enforced by `npm run validate:sim`; `npm run build` also invokes validation before Vite build.

## 5. Extending the Library
- Add new voices to `app/config.py` voice catalogue and ensure Larynx server exposes matching IDs.
- Publish new sprites/backgrounds with hashed filenames to avoid cache collisions; update the manifest accordingly.
- Document scenario nuances (e.g., evidence prerequisites, dynamic delegate expectations) within the YAML file `notes` fields to surface via UI tooltips in future iterations.
