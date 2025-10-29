# Monitoring Playbook & Alert Thresholds

This playbook consolidates the instrumentation introduced across ingestion, agents, voice, simulation, knowledge, and cost tracking services. It establishes the alerting contracts surfaced on the new Grafana dashboards under `infra/grafana/dashboards/` and enumerates the minimum signals SREs must wire into PagerDuty or OpsGenie.

## Dashboards

| Dashboard | Purpose | Primary Metrics |
|-----------|---------|-----------------|
| **Pipeline Latency Overview** (`pipeline-latency`) | End-to-end latency SLIs for ingestion, knowledge search, voice sessions, and scenario runs. | `ingestion_job_duration_ms`, `knowledge_search_duration_ms`, `voice_session_duration_ms`, `scenario_run_duration_ms` |
| **Agent Run Outcomes** (`agent-success`) | Success ratio and failure diagnostics for orchestration threads. | `agents_runs_total`, `agents_run_duration_ms`, `agents_failures_total` |
| **Cost & Utilization** (`cost-observability`) | Cost attribution rollups for API usage, model loads, and GPU occupancy. | `cost_api_calls_total`, `cost_model_loads_total`, `cost_gpu_duration_ms_sum` |
| **Customer Health Overview** (`customer-health`) | Commercial telemetry retained for CSMs. | Billing health metrics |

Dashboards are automatically provisioned via `infra/grafana/provisioning/dashboards/dashboard.yaml` which points Grafana at `/var/lib/grafana/dashboards`. Drop-in JSON files in that directory are deployed on restart.

## Alert Thresholds

| Service | Signal | Warning | Critical | Notes |
|---------|--------|---------|----------|-------|
| Ingestion | P90 `ingestion_job_duration_ms` | > 12m for 2 samples | > 20m for 2 samples | Check upstream connectors and OCR throughput. |
| Knowledge | P95 `knowledge_search_duration_ms` | > 3s for 5m | > 5s for 5m | Validate vector index health and embedding service. |
| Voice | P90 `voice_session_duration_ms` | > 8s for 5m | > 12s for 5m | GPU under-provisioning or Whisper download failure. |
| Scenarios | P90 `scenario_run_duration_ms` | > 15s for 10m | > 25s for 10m | Inspect agent latency and TTS workloads. |
| Agents | Success rate (`agents_runs_total` excluding `status="failed"`) | < 90% for 10m | < 80% for 5m | Trigger triage of orchestrator logs with correlation IDs. |
| Cost | `cost_gpu_duration_ms_sum` | +50% vs 24h baseline | +100% vs 24h baseline | Helps identify runaway GPU jobs. |
| Cost | `cost_api_calls_total` | +50% vs plan quota | +100% vs plan quota | Correlate with billing events and throttles. |

## Runbooks

### Ingestion Latency
1. Confirm metric spike on `pipeline-latency` dashboard.
2. Inspect agent retry counters (`ingestion_job_errors_total`).
3. Tail ingestion worker logs for connector-specific errors.
4. If latency isolated to OCR-heavy sources, provision additional workers (`INGESTION_WORKER_CONCURRENCY`).
5. Record impact + mitigation in incident log.

### Agent Failures
1. Review failure table in `agent-success` dashboard (component dimension).
2. Fetch corresponding trace IDs from the agent service logs (search by thread id).
3. If failures cluster on a tool, disable the tool in orchestrator configuration and open P1 ticket.
4. Once resolved, ensure success rate > 95% for 30 minutes before closing.

### Cost Anomalies
1. Use `cost-observability` dashboard to identify offending endpoints/devices.
2. Drill into `/costs/events` API with tenant filter for supporting detail.
3. Coordinate with Finance to validate impact, then
   - throttle offending endpoint, or
   - migrate to `economy` retrieval mode (documented below) to reduce spend.
4. Backfill cost tracking data store from snapshot if corruption suspected.

## Economy vs Precision Mode

The header settings now expose **Precision** and **Economy** profiles:

- **Precision** – OpenAI `text-embedding-3-large` + cross-encoder reranker. Default for accuracy-first matters.
- **Economy** – Local MiniLM embeddings + lexical fusion (maps to retrieval mode `recall`). Ideal for cost-sensitive review or offline workloads.

Switching modes updates WebSocket and REST query calls, allowing downstream telemetry (`retrieval.mode` attribute) to differentiate the spend profile in traces and metrics.

## Alert Wiring Checklist

- [ ] Export the metrics above to Prometheus via OTLP (verify scrape job `cocounsel-backend`).
- [ ] Configure alert rules in Grafana/Alertmanager using thresholds from this document.
- [ ] Route ingestion & agent alerts to the Incident Response rotation, cost anomalies to Finance on-call.
- [ ] Update PagerDuty runbook links to point at this file.
