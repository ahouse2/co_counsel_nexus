# 2025-11-23 Voice Interface Execution Blueprint

## 0. North Star Narrative
- Design the end-to-end real-time voice experience that fuses multimodal Co-Counsel reasoning with seamless audio interaction.
  - Guarantee deterministic speech-to-text (STT) ingestion using Whisper with resilient CPU/GPU fallbacks.
    - Provision caching and model asset management scoped to the existing storage canon.
    - Encode compliance by persisting sentiment scores and transcripts inside the agent memory ledger.
  - Deliver expressive text-to-speech (TTS) synthesis powered by Coqui with persona-aware timbre selection.
    - Synchronise speaking tempo with per-turn sentiment analytics to keep delivery empathetic.
    - Stream audio responses efficiently to the React SPA via FastAPI streaming endpoints.
  - Extend the React surface with ergonomic voice controls, waveform telemetry, and persona selectors without regressing accessibility.
    - Maintain parity with keyboard interaction patterns and ARIA semantics.
    - Validate behaviour with Vitest to preserve deterministic recordings and playback.

## 1. Backend Architecture Phase
- 1.1 Voice settings + asset management
  - 1.1.1 Extend `backend/app/config.py` with Whisper/TTS/sentiment settings, device fallbacks, persona map, and storage roots.
    - 1.1.1.1 Ensure directories materialise in `Settings.prepare_directories` for session audio + caches.
    - 1.1.1.2 Add typed defaults for persona registry and GPU preference toggles.
  - 1.1.2 Document GPU/CPU fallback semantics in settings docstrings and config comments.
- 1.2 Voice service module scaffolding (no placeholders, production-grade implementations)
  - 1.2.1 Create `backend/app/services/voice/__init__.py` exporting dependency factory + exceptions.
  - 1.2.2 Build `adapters.py` with concrete `WhisperTranscriber` and `CoquiSynthesizer` classes.
    - 1.2.2.1 Resolve lazy model loading with caching keyed by persona/model id.
    - 1.2.2.2 Auto-detect CUDA availability; fall back to CPU compute if GPU is absent or misconfigured.
    - 1.2.2.3 Normalise incoming audio to target sample rate leveraging `soundfile` to avoid quantisation errors.
  - 1.2.3 Implement `sentiment.py` with transformer-driven sentiment scoring + pace recommendation heuristic.
    - 1.2.3.1 Cache pipeline per process and expose deterministic API returning compound sentiment metadata.
  - 1.2.4 Author `session.py` to persist session metadata/audio artefacts atomically under `voice_sessions_dir`.
    - 1.2.4.1 Encode `VoiceSession` dataclass, JSON serialisation, and guard rails for identifier sanitisation.
  - 1.2.5 Compose `service.py` orchestrating STT -> AgentsService -> sentiment -> TTS.
    - 1.2.5.1 Support session creation + follow-up turns bound to Microsoft Agents conversation state.
    - 1.2.5.2 Persist transcripts + sentiment inside thread memory and session store.
    - 1.2.5.3 Emit structured telemetry for pacing + persona usage.

## 2. FastAPI Endpoint Integration Phase
- 2.1 API models
  - 2.1.1 Extend `backend/app/models/api.py` with Pydantic schemas for personas, session creation payload/response, streaming manifest.
- 2.2 Route wiring in `backend/app/main.py`
  - 2.2.1 Register dependency injection for `VoiceService` + persona listing endpoint (`GET /voice/personas`).
  - 2.2.2 Implement `POST /voice/sessions` accepting `UploadFile` audio + metadata (case_id, persona_id, optional thread_id).
    - 2.2.2.1 Handle streaming request body -> bytes transformation without loading entire file into memory when avoidable.
    - 2.2.2.2 Attach authenticated principal context using new `authorize_agents_run` scope (reuse existing roles).
  - 2.2.3 Provide `GET /voice/sessions/{session_id}/response` returning streamed audio bytes with proper headers + caching semantics.
  - 2.2.4 Deliver `GET /voice/sessions/{session_id}` for polling transcript/sentiment metadata.
  - 2.2.5 Ensure error handling maps to existing `WorkflowException` taxonomy and surfaces `Retry-After` where relevant.
- 2.3 Conversation state integration
  - 2.3.1 Update `AgentsService` to expose helper for resuming threads from persisted memory payloads.
    - 2.3.1.1 Implement payload -> `AgentThread` reconstruction utilities (turns, timestamps, telemetry).
    - 2.3.1.2 Reconcile audit trail semantics for resumed voice turns (e.g., `agents.thread.voice_turn`).

## 3. Frontend Experience Phase
- 3.1 Type + API client extensions
  - 3.1.1 Update `frontend/src/types.ts` with `VoicePersona`, `VoiceSession`, `VoiceTurn` definitions.
  - 3.1.2 Extend `frontend/src/utils/apiClient.ts` with persona fetch + session create/poll endpoints (multipart POST + streaming GET).
- 3.2 Hooks + utilities
  - 3.2.1 Implement `useMicrophone` hook managing MediaStream lifecycle, permission prompts, and PCM buffer capture.
    - 3.2.1.1 Derive waveform samples using `AudioContext` analyser for visualisation.
    - 3.2.1.2 Encode PCM buffers to WAV (16-bit) before upload.
  - 3.2.2 Implement `useVoiceSession` orchestrating persona selection, backend requests, audio playback, and error states.
    - 3.2.2.1 Stream backend audio via `Audio` element + Blob URLs with clean-up.
    - 3.2.2.2 Surface status updates for UI (recording, processing, playing).
  - 3.2.3 Add `frontend/src/utils/audio.ts` for reusable PCM -> WAV encoding + amplitude normalisation.
- 3.3 UI components
  - 3.3.1 Create `VoiceConsole` component embedding microphone controls, persona selector, waveform canvas, status text, playback UI.
    - 3.3.1.1 Guarantee accessible labels, keyboard shortcuts, and focus states.
    - 3.3.1.2 Display sentiment-driven pacing hints per completed session.
  - 3.3.2 Integrate `VoiceConsole` into `ChatView` layout without disrupting existing chat controls.
    - 3.3.2.1 Ensure responsive design on smaller breakpoints.
  - 3.3.3 Expand stylesheet with voice console theming.

## 4. Testing & Quality Phase
- 4.1 Backend tests
  - 4.1.1 Add `backend/tests/test_voice_service.py` verifying STT→Agents→TTS pipeline using deterministic stub adapters.
    - 4.1.1.1 Assert agent memory store persists voice transcript + sentiment metadata.
  - 4.1.2 Add `backend/tests/test_voice_api.py` covering persona listing, session creation, response streaming with `TestClient`.
    - 4.1.2.1 Validate audio bytes content-type + waveform metadata.
- 4.2 Frontend tests
  - 4.2.1 Author Vitest suite `frontend/tests/useVoiceSession.test.ts` verifying hook state transitions + API interactions via mocked fetch/Media APIs.
- 4.3 Lint/format review
  - 4.3.1 Run backend pytest subset (voice) and targeted `npm test -- voice` to ensure deterministic results.

## 5. Deployment & Documentation Phase
- 5.1 Containerisation updates
  - 5.1.1 Expand `backend/Dockerfile` to install system deps (ffmpeg/libsndfile) and prime Whisper/TTS models under `/models`.
  - 5.1.2 Update `infra/docker-compose.yml` with bind mounts/volumes for `voice_models` + optional GPU runtime flags.
- 5.2 Artefact caching guidance
  - 5.2.1 Document caching strategy in `docs/voice/hardware_requirements.md`, covering GPU (RTX 4090) vs CPU fallback (AVX2) envelopes.
  - 5.2.2 Outline environment variables for persona selection + compute preference.
- 5.3 Stewardship updates
  - 5.3.1 Append build log entry summarising execution + validations.
  - 5.3.2 Record ACE memory capsule + AGENTS chain-of-stewardship entry.

