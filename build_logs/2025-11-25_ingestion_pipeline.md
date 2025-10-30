# 2025-11-25 — LlamaIndex ingestion pipeline integration

## Summary
- Materialised `backend/ingestion/` package with runtime settings, OCR, loader registry, pipeline orchestration, and metrics glue.
- Updated `IngestionService` orchestration to queue LlamaIndex jobs, persist vector + metadata payloads, and push triples/entities into Neo4j via `GraphService`.
- Hardened async worker with checksum dedupe, retry backoff, and idempotent fingerprinting.
- Refreshed ingestion regression suite to cover local workspaces, SharePoint/OneDrive remote materialisation, OCR fallbacks, and metrics hooks.

## Testing
- `PYTHONPATH=. pytest backend/tests/test_ingestion_async.py backend/tests/test_ingestion_connectors.py -q` *(fails: ModuleNotFoundError: No module named 'jwt'; test harness missing dependency)*

## Follow-ups
- Provision `jwt` dependency within backend test environment to unblock ingestion suite execution in CI.
