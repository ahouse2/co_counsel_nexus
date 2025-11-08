# 2025-11-21 — Ingestion Metrics Enhancements

## Commands Executed
- `PYTHONPATH=. pytest backend/tests/test_ingestion_async.py -q`

## Outcomes
- ✅ Extended OpenTelemetry counters for queue events and job status transitions.
- ✅ Patched `IngestionService` to emit metrics for enqueue/claim/transition flows without altering business logic.
- ✅ Added regression test ensuring queue + status metrics fire during ingestion job lifecycle.

## Notes
- Pytest emits FastAPI `on_event` deprecation warnings; backlog already tracking migration to lifespan handlers.
- No additional dependencies introduced; OpenTelemetry API already provisioned via backend requirements.
