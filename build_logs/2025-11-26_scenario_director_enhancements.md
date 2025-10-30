# 2025-11-26 — Scenario director enhancements

## Summary
- Hardened scenario director manifest plumbing and ensured runtime cues are persisted alongside transcripts for downstream consumers.
- Synced simulation canvas real-time rendering with director-provided motion, lighting, and persona cues for both Pixi and fallback renderers.
- Added beat authoring controls for counsel to tweak emotional tone, motion, lighting, and counter-arguments prior to simulation playback.
- Seeded end-to-end health checks with deterministic randomness to stabilise orchestration smoke tests.

## Validation
- Targeted lint/tests not executed (backend pytest currently blocked on missing `jwt` dependency in shared environment).
- Manual inspection of scenario transcript payloads and front-end rendering against existing fixtures.

## Follow-ups
- Backfill `jwt` dependency for backend test harness to restore full suite coverage.
- Expand automated UI coverage for beat authoring interactions once deterministic seeds are available in Vitest harness.
