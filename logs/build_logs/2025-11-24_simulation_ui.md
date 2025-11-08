# 2025-11-24 — Simulation UI Stabilisation

## Summary
- Resolved Pixi `TextStyle` typing conflicts by aligning imports with `@pixi/text` and caching placeholder styles.
- Finalised simulation canvas rendering path and ensured manifest provider feeds non-null data when Pixi is active.
- Adjusted scenario workbench tests to use strongly typed Vitest mocks and revalidated manifest hook.
- Pinned `llama-hub` to 0.0.45 to restore compatibility with Python 3.12 and regenerated `uv.lock`.
- Confirmed asset validation, TypeScript build, and Vitest suite succeed end-to-end.

## Commands Executed
- `npm run build`
- `npm run test -- --run`
- `pip install llama-hub==0.0.45 --no-deps`

## Follow-ups
- Full backend dependency install remains heavy; consider prebuilt cache for CI.
- Monitor bundle size warning for simulation chunk during future optimisation passes.
