# 2025-11-23 — Voice Interface Implementation

## Summary
- Added Whisper STT + Coqui TTS services with sentiment-aware pacing and persisted session metadata.
- Exposed FastAPI endpoints for persona discovery, session creation, and audio streaming tied to agent threads.
- Delivered React voice console with recording controls, waveform visualisation, persona selector, and Vitest coverage.
- Updated deployment artefacts to preload audio dependencies and document GPU/CPU requirements.

## Verification
- `pytest backend/tests/test_voice_service.py backend/tests/test_voice_api.py -q`
- `npm run test -- --run useVoiceSession`
