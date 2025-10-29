# Execution Plan — Microsoft Agents SDK Orchestration Refresh

- Phase 1 — Discovery & Alignment
  - Chapter 1.1 — Repository Audit
    - Paragraph 1.1.1 — Catalogue existing agents runtime (`backend/app/agents/*`).
      - Sentence 1.1.1.a — Verify tool abstractions map to TRD personas.
      - Sentence 1.1.1.b — Inspect telemetry pathways from `/agents/run` to storage.
    - Paragraph 1.1.2 — Inspect persistence stack (`AgentMemoryStore`).
      - Sentence 1.1.2.a — Confirm thread snapshots include memory & telemetry.
      - Sentence 1.1.2.b — Identify extension points for per-turn persistence counters.
  - Chapter 1.2 — Requirements Trace
    - Paragraph 1.2.1 — Map instructions 1–7 to concrete code artefacts.
      - Sentence 1.2.1.a — Highlight docs needing refresh for telemetry schema change.
      - Sentence 1.2.1.b — Enumerate tests covering hand-offs, retries, telemetry.

- Phase 2 — Design Decisions
  - Chapter 2.1 — Telemetry Schema Evolution
    - Paragraph 2.1.1 — Adopt structured `hand_offs` payload with `from`/`to` fields.
      - Sentence 2.1.1.a — Update orchestrator to emit dictionaries instead of tuples.
      - Sentence 2.1.1.b — Adjust service defaults/tests/docs accordingly.
  - Chapter 2.2 — Memory Persistence Instrumentation
    - Paragraph 2.2.1 — Craft stub memory store capturing write cadence.
      - Sentence 2.2.1.a — Ensure orchestrator triggers writes on each turn + final persist.
      - Sentence 2.2.1.b — Validate via regression test assertions.

- Phase 3 — Implementation Sequence
  - Chapter 3.1 — Code Updates
    - Paragraph 3.1.1 — Modify `MicrosoftAgentsOrchestrator.run` telemetry handling.
      - Sentence 3.1.1.a — Replace tuple appends with dict payloads including `via` tool name.
      - Sentence 3.1.1.b — Preserve audit/circuit-breaker hooks by keeping executor signature unchanged.
    - Paragraph 3.1.2 — Clean redundant imports in `agents/types.py`.
      - Sentence 3.1.2.a — Remove duplicate `from __future__ import annotations` line.
  - Chapter 3.2 — Test Enhancements
    - Paragraph 3.2.1 — Extend `backend/tests/test_agents.py` coverage.
      - Sentence 3.2.1.a — Assert new `hand_offs` schema in API response.
      - Sentence 3.2.1.b — Add `test_agents_service_persists_memory_each_turn` using stub store.
  - Chapter 3.3 — Documentation Refresh
    - Paragraph 3.3.1 — Update PRP session graph doc telemetry section.
      - Sentence 3.3.1.a — Reflect new `hand_offs` structure & per-turn persistence note.

- Phase 4 — Verification & Stewardship
  - Chapter 4.1 — Automated Validation
    - Paragraph 4.1.1 — Run `pytest backend/tests/test_agents.py -q` to ensure regression coverage.
  - Chapter 4.2 — Documentation & Log Updates
    - Paragraph 4.2.1 — Append AGENTS.md stewardship entry summarising work/tests.
      - Sentence 4.2.1.a — Capture rubric targets and validation results.

