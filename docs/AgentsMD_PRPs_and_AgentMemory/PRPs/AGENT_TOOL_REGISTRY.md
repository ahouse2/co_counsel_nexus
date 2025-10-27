# Agent & Tool Registry (Enhanced — 2025-10-29)

Purpose: Central map of agents, tools, state transitions, and observability contracts governing the MS Agents + Swarms workflow.

## Canonical State Glossary
- `idle` → agent awaiting work.
- `pending` → validation/config pre-flight executing.
- `active` → primary workload running.
- `waiting` → blocked on upstream signals or rate limits.
- `succeeded` → job complete; downstream notified.
- `soft_failed` → transient fault; retries allowed within budget.
- `hard_failed` → unrecoverable error; escalate to human review.
- `cancelled` → request aborted intentionally; compensating actions executed.

## Agent Registry

### Coordinator / Co-Counsel Agent
- **Purpose**: Orchestrates run lifecycle; sequences node execution; aggregates telemetry.
- **State Machine**
  | From | Event | To | Notes |
  | --- | --- | --- | --- |
  | `idle` | Case assignment received | `pending` | Initialize `run_id`, allocate agents |
  | `pending` | All prerequisites satisfied | `active` | Issue ingest command |
  | `active` | All downstream nodes `succeeded` | `succeeded` | Compile final dossier |
  | `active` | Any node `hard_failed` | `waiting` | Pause flow; await human decision |
  | `waiting` | Human approves resume | `active` | Continue with rerouted plan |
  | `waiting` | Human cancels run | `cancelled` | Emit `case_handoff_required` |
- **Failure & Retry**: Coordinator does not auto-retry; instead remediates by re-scheduling nodes with adjusted parameters. Hard failure triggers escalation to operations team.
- **Inputs/Outputs**: Inputs `case_id`, scope constraints, policy flags. Outputs consolidated status report, final deliverables manifest.
- **Telemetry**: Emits `coordinator.lifecycle` span with child spans referencing node states; metrics `cases_inflight`, `handoffs_triggered`.
- **Memory**: Persists orchestration context (YAML) ≤ 50 MB in run metadata store.

### IngestionAgent
- **Purpose**: Normalize sources, chunk, embed, persist to blob/vector stores.
- **State Machine**: Mirrors spec table (§ Agents Workflow).
  | From | Event | To | Failure Handling | Retry |
  | --- | --- | --- | --- | --- |
  | `idle` | Job dequeued | `pending` | Validate manifest | n/a |
  | `pending` | Credentials resolved | `active` | Missing credential → `soft_failed` | 3 attempts, exp backoff (2^n·15s + jitter) |
  | `pending` | Schema validation error | `hard_failed` | Emit `ingestion.validation_error` | No retry |
  | `active` | Connectors succeed | `succeeded` | Emit `ingestion.completed` | n/a |
  | `active` | Timeout/throttle | `soft_failed` | Log `ingestion.transient_failure` | consume retry budget |
  | `soft_failed` | Retry budget exhausted | `hard_failed` | Emit `case_handoff_required` | No further attempts |
  | any | Cancel request | `cancelled` | Cleanup partial writes | n/a |
- **Inputs/Outputs**: Inputs manifest entries, credential refs, run context. Outputs chunk ids, embedding vectors, success event.
- **Telemetry**: Spans `ingestion.queue`, `ingestion.load`; metrics `ingested_bytes`, `chunks_written`; logs include connector latency + retry counts.
- **Memory**: Ephemeral staging buffer ≤ 2 GB; persists final assets to blob/Qdrant.

### GraphBuilderAgent
- **Purpose**: Convert chunks to entities/relations; update Neo4j ontology.
- **State Machine**
  | From | Event | To | Failure Handling | Retry |
  | --- | --- | --- | --- | --- |
  | `idle` | Receive `ingestion.completed` | `pending` | Check manifest presence | n/a |
  | `pending` | Neo4j session ready | `active` | Ontology cache miss → `soft_failed` | 2 retries (30s, 60s) |
  | `pending` | Manifest missing/corrupt | `hard_failed` | Emit `graphbuilder.artifact_missing` | Manual re-ingest |
  | `active` | Triples committed | `succeeded` | Emit `graphbuilder.completed` | n/a |
  | `active` | Commit failure/deadlock | `soft_failed` | Rollback transaction | Retry with 20–45s randomized delay |
  | `active` | Schema mismatch | `hard_failed` | Emit `graphbuilder.schema_violation` | Manual migration |
  | any | Cancel request | `cancelled` | Run compensating Cypher cleanup | n/a |
- **Inputs/Outputs**: Inputs chunk handles, ontology version, extraction rules. Outputs Neo4j nodes/edges, completion event, ontology revision id.
- **Telemetry**: Spans `graphbuilder.extract`, `graphbuilder.commit`; metrics `nodes_upserted`, `edges_upserted`, `cypher_latency`; logs capture schema diffs.
- **Memory**: ≤ 1 GB working set for batch graph assembly; persistent store is Neo4j.

### ResearchAgent
- **Purpose**: Perform hybrid retrieval, reasoning, and citation validation.
- **State Machine**
  | From | Event | To | Failure Handling | Retry |
  | --- | --- | --- | --- | --- |
  | `idle` | Receive `graphbuilder.completed` | `pending` | Preload retrieval context | n/a |
  | `pending` | Context ready | `active` | Missing vector hits → `soft_failed` | 3 attempts, 10s base backoff |
  | `pending` | Safety violation | `hard_failed` | Emit `research.policy_blocked` | Manual override only |
  | `active` | Answer + citations validated | `succeeded` | Emit `research.answer_ready` | n/a |
  | `active` | LLM timeout/provider outage | `soft_failed` | Emit `research.provider_timeout` | Retry with provider failover list |
  | `active` | Citation validation failure persistent | `hard_failed` | Emit `research.citation_failure` | Human curator |
  | any | Cancel request | `cancelled` | Drop conversation memory | n/a |
- **Inputs/Outputs**: Inputs query intents, vector/graph context, guardrail config. Outputs synthesized answer, citations, trace bundle.
- **Telemetry**: Spans `research.retrieve`, `research.generate`; metrics `token_usage`, `model_latency`, `citation_pass_rate`; logs include prompt + safety metadata hashes.
- **Memory**: 256 MB scratchpad for conversation context; ephemeral caches only.

### TimelineAgent
- **Purpose**: Build chronological event narrative from research + event store.
- **State Machine**
  | From | Event | To | Failure Handling | Retry |
  | --- | --- | --- | --- | --- |
  | `idle` | Receive `research.answer_ready` | `pending` | Fetch event candidates | n/a |
  | `pending` | Event store reachable | `active` | Store lag → `soft_failed` | 2 retries, 20s base backoff |
  | `pending` | Store outage >5 min | `hard_failed` | Emit `timeline.store_unavailable` | Alert ops |
  | `active` | Timeline assembled | `succeeded` | Emit `timeline.published` | n/a |
  | `active` | Ordering conflict | `soft_failed` | Apply skew correction | Consume remaining retries |
  | `active` | Data corruption | `hard_failed` | Emit `timeline.data_corruption` | Manual fix |
  | any | Cancel request | `cancelled` | Remove partial timeline artifacts | n/a |
- **Inputs/Outputs**: Inputs event candidates, answer context, pagination policy. Outputs ordered timeline payload, published event.
- **Telemetry**: Spans `timeline.assemble`; metrics `events_emitted`, `skew_adjustments`; logs capture ordering decisions.
- **Memory**: ≤ 512 MB working set; persistent cache (Redis/Postgres) for timeline snapshots.

### Forensics Agents

#### DocumentForensicsAgent
- **Purpose**: Hashing, structure extraction, metadata validation for documents/email.
- **State Machine**: Aligns with spec Forensics table.
  | From | Event | To | Failure Handling | Retry |
  | --- | --- | --- | --- | --- |
  | `idle` | Receive `timeline.published` | `pending` | Validate manifest | n/a |
  | `pending` | Storage accessible | `active` | Throttled → `soft_failed` | 3 retries, 25s backoff |
  | `active` | Extraction complete | `succeeded` | Emit `forensics.document_ready` | n/a |
  | `active` | Parser fatal error | `hard_failed` | Emit `forensics.document_error` | Manual remediation |
  | any | Cancel request | `cancelled` | Cleanup temp artifacts | n/a |
- **Inputs/Outputs**: Inputs document manifest, checksum policy. Outputs hash digests, metadata JSON, readiness event.
- **Telemetry**: Spans `forensics.document.hash`; metrics `documents_processed`, `avg_parse_time`; logs highlight integrity anomalies.
- **Memory**: Temp disk ≤ 1 GB; persistent artifacts stored in forensics vault.

#### ImageForensicsAgent
- **Purpose**: Perform EXIF, ELA, PRNU/clone detection on media.
- **State Machine**
  | From | Event | To | Failure Handling | Retry |
  | --- | --- | --- | --- | --- |
  | `idle` | Receive `timeline.published` | `pending` | Locate media set | n/a |
  | `pending` | Media available | `active` | Missing media → `soft_failed` | 2 retries, 30s base backoff |
  | `active` | Analysis complete | `succeeded` | Emit `forensics.image_ready` | n/a |
  | `active` | GPU unavailable | `soft_failed` | Queue CPU fallback | Single retry on fallback |
  | `soft_failed` | Fallback exhausted | `hard_failed` | Emit `forensics.image_unavailable` | Manual ops |
  | any | Cancel request | `cancelled` | Remove temporary frames | n/a |
- **Inputs/Outputs**: Inputs media manifest, GPU/CPU profile, anomaly thresholds. Outputs EXIF payload, forensic scores, readiness event.
- **Telemetry**: Spans `forensics.image.analysis`; metrics `gpu_utilization`, `anomalies_flagged`; logs summarise model confidence.
- **Memory**: GPU VRAM ≤ 2 GB; CPU buffers ≤ 512 MB; artifacts persisted to vault.

#### FinancialForensicsAgent
- **Purpose**: Evaluate ledgers for anomalies, totals, entity linkages.
- **State Machine**
  | From | Event | To | Failure Handling | Retry |
  | --- | --- | --- | --- | --- |
  | `idle` | Receive `timeline.published` | `pending` | Load ledger extracts | n/a |
  | `pending` | Schema validated | `active` | Schema mismatch → `soft_failed` | 1 retry after schema refresh |
  | `active` | Metrics computed | `succeeded` | Emit `forensics.financial_ready` | n/a |
  | `active` | Schema mismatch persists | `hard_failed` | Emit `forensics.financial_blocked` | Human finance SME |
  | any | Cancel request | `cancelled` | Purge temp aggregates | n/a |
- **Inputs/Outputs**: Inputs ledger extracts, currency config, anomaly rules. Outputs trend charts, anomaly list, readiness event.
- **Telemetry**: Spans `forensics.financial.evaluate`; metrics `transactions_processed`, `anomaly_rate`; logs capture triggered rules.
- **Memory**: Memory pool ≤ 768 MB for aggregation; metrics persisted to analytics warehouse.

### Supporting Agents (Drafting, QA, Voice)
- DraftingAgent — downstream consumer; inherits canonical states; outputs long-form briefs; telemetry `drafting.compose`, `drafting.review`.
- QAAgent — performs rubric scoring; emits `qa.validation_complete`; retries twice on retriever mismatch.
- VoiceAgent — handles Whisper STT/Coqui TTS; retries on audio decoding errors with jittered backoff (5s, 15s, 30s).

## Tool Registry (Seed)
- Loaders — LlamaHub connectors (local, SharePoint/OneDrive/Outlook/Gmail/Slack/Confluence/Jira/GitHub/Google Drive/S3) with circuit breaker + retry envelopes matching IngestionAgent budget.
- OCR — Tesseract wrapper with transient retry (3 attempts, 10s base) and telemetry `ocr.page_processed`.
- Embeddings — HF BGE small (default) pluggable; emits `embedding.encode` spans; memory limit 1 GB.
- Vector Stores — Qdrant/Chroma adapters with idempotent upsert; retries align with IngestionAgent soft failures.
- Graph Store — Neo4j driver + Cypher utils; integrates deadlock retry (20–45s randomized) as per GraphBuilderAgent.
- Case Law — CourtListener/Web search adapters (policy constrained) with 429 backoff policy (exp base 5s, max 5 tries).
- Security — Redaction + privilege detector; emits `security.scan` metrics.
- Forensics Core — sha256 hasher, EXIF extractor, PDF parser, ELA, clone detection, email header parser, financial parsers; each tool surfaces span events consumed by respective forensics agents.

Notes
- Source references under `agents and tools/` (autogen, prior agents); integrate incrementally.
- Every tool must define schema, security scope, observability fields, retry envelope, and test strategy.
