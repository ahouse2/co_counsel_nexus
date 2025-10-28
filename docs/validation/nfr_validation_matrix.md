# Non-Functional Validation Matrix

This playbook codifies the hardware assumptions, synthetic load profiles, and validation artifacts that back the SLOs defined in the main Co-Counsel specification.

## Hardware Baseline
- **CPU**: 8 vCPU @ 3.0 GHz (Ryzen 7 7840HS or Intel i7-13700H class)
- **Memory**: 32 GB DDR5
- **Storage**: 1 TB NVMe SSD (\>=3.2 GB/s sequential read)
- **Network**: 1 Gbps LAN with \<=40 ms round-trip latency to Neo4j and Qdrant services
- **GPU**: Not required for validation (LLM invocations hosted)

## Load Profiles
| Profile | Target | Shape | Command |
| --- | --- | --- | --- |
| Baseline Query | `/query` latency SLO | 20 sequential queries using `tools/perf/query_latency_probe.py --runs 20` after seeding the reference workspace. | `python tools/perf/query_latency_probe.py --runs 20` |
| Batch Ingest | Ingest throughput SLO | 10 sequential ingests of the reference three-file workspace; measure total elapsed time and extrapolate hourly throughput. | `python tools/perf/query_latency_probe.py --runs 1` (ingest step) repeated via wrapper script or CI job. |
| Offline Tolerance | Queue durability | Disconnect Neo4j/Qdrant for up to 12 hours while `docker compose` keeps API and storage volumes available; replay queued ingests post-reconnect and verify no job loss. | Procedure in [#offline-tolerance](#offline-tolerance). |

## Validation Matrix
| NFR | Metric | Target | Validation Artifact | Execution |
| --- | --- | --- | --- | --- |
| Availability & Offline Continuity | Uptime ratio | \>=99.5% monthly | `tools/monitoring/uptime_probe.py` | `python tools/monitoring/uptime_probe.py --interval 60 --duration 86400 --csv build_logs/uptime_probe.csv` |
| Availability & Offline Continuity | Offline backlog capacity | 1,800 documents minimum | Manual simulation documented in [#offline-tolerance](#offline-tolerance) | Follow procedural checklist |
| Reproducibility | Drift across replays | \<=0.5% (exact match expected) | `tools/perf/reproducibility_check.py` | `python tools/perf/reproducibility_check.py` |
| Performance | `/query` p95 latency | \<=1,800 ms | `tools/perf/query_latency_probe.py` | `python tools/perf/query_latency_probe.py --runs 20` |
| Performance | Ingest throughput | \>=150 documents/hour | `tools/perf/query_latency_probe.py --skip-ingest` paired with manual duration tracking for 10 ingests | Capture elapsed wall-clock and compute throughput |
| Provider Policy | Preferred provider ratio | \>=95% of calls | `tools/monitoring/provider_mix_check.py` | `python tools/monitoring/provider_mix_check.py build_logs/llm_invocations.jsonl` |
| Provider Policy | Fallback error rate | \<=1% | `tools/monitoring/provider_mix_check.py` (inspect non-success entries) | Same as above |
| Observability | Retrieval telemetry coverage | Spans + metrics exported (`retrieval_query_duration_ms`, `retrieval_results_returned`, `retrieval_queries_total`) | OTLP dashboard `retrieval-latency` | Enable telemetry env vars then `pytest backend/tests/test_telemetry.py -q` |
| Observability | Forensics telemetry coverage | Stage spans + metrics (`forensics_pipeline_duration_ms`, `forensics_stage_duration_ms`, `forensics_reports_total`) | OTLP dashboard `forensics-pipeline` | Enable telemetry env vars then `pytest backend/tests/test_telemetry.py -q` |

## Offline Tolerance
1. Start the stack: `docker compose -f infra/docker-compose.yml up -d`.
2. Begin an ingest run that produces at least 150 documents/hour (repeat ingestion of the reference workspace via API).
3. Stop Neo4j and Qdrant containers: `docker compose -f infra/docker-compose.yml stop neo4j qdrant` while continuing to enqueue ingest requests (they should persist on disk).
4. Maintain the outage window for up to 12 hours, ensuring API writes manifests to `JOB_STORE_DIR` without errors.
5. Restart dependencies: `docker compose -f infra/docker-compose.yml start neo4j qdrant` and reprocess queued jobs via the normal ingestion retry mechanism.
6. Validate job manifests and document store contents for continuity. Any data loss invalidates the SLO.

## Notes
- Persist raw metrics (CSV/JSON) in `build_logs/` for auditability.
- When collecting provider metrics, standardize the JSONL schema to `{ "timestamp": "ISO", "provider": "gemini-2.5-flash", "status": "success" }`.
- Telemetry bootstrap variables: set `TELEMETRY_ENABLED=true`, `TELEMETRY_OTLP_ENDPOINT=grpc://otel-collector:4317`, `TELEMETRY_SERVICE_NAME=cocounsel-backend`, and `TELEMETRY_CONSOLE_FALLBACK=false` in production.
- Dashboards ingest the following OTel instruments: retrieval (`retrieval_query_duration_ms`, `retrieval_queries_total`, `retrieval_results_returned`) and forensics (`forensics_pipeline_duration_ms`, `forensics_stage_duration_ms`, `forensics_reports_total`, `forensics_pipeline_fallbacks_total`).
