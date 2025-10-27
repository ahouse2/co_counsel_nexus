name: "Spec — Co-Counsel (MVP)"
version: 0.2

## APIs

### POST /ingest
**Summary**: Queue document sources for processing. Implemented via `backend.app.models.api.IngestionRequest` ➜ `IngestionResponse`.

| Aspect | Value |
| --- | --- |
| Method | POST |
| Path | `/ingest` |
| Authentication | TBD (service token) |
| Synchronous Response | `202 Accepted` with `IngestionResponse` payload |
| Long-running Behaviour | Jobs processed asynchronously; clients poll `/ingest/{job_id}` |

#### Request Schema — `IngestionRequest`
| Field | Type | Required | Validation Rules | Notes |
| --- | --- | --- | --- | --- |
| `sources` | array of [`IngestionSource`](#ingestionsource) | yes | `minItems=1` | Source definitions processed sequentially |

##### `IngestionSource`
| Field | Type | Required | Validation Rules | Notes |
| --- | --- | --- | --- | --- |
| `type` | string | yes | Enum: `local`, `sharepoint`, `s3`, `onedrive`, `web` | Drives downstream connector selection |
| `path` | string | conditional | Required when `type == "local"`; must resolve under configured mount | Absolute or relative path |
| `credRef` | string | conditional | Required when `type` is not `local`; must match credentials registry key | Secrets fetched server-side |

```json
{
  "sources": [
    {"type": "local", "path": "./data/case-512"},
    {"type": "sharepoint", "credRef": "sharepoint/corp-legal"}
  ]
}
```

#### Response Schema — `IngestionResponse`
| Field | Type | Validation Rules | Notes |
| --- | --- | --- | --- |
| `job_id` | string | RFC 4122 UUID | Stable identifier for lifecycle polling |
| `status` | string | Enum: `queued`, `running`, `succeeded`, `failed` | Reflects current job state at time of response |

```json
{
  "job_id": "0f6f7bc4-322b-4e61-a4f7-4b9a61d1adbe",
  "status": "queued"
}
```

#### Error Envelope — `HTTPValidationError`
| Code | Body |
| --- | --- |
| 400 | `{"detail": "At least one source must be provided"}` |
| 404 | `{"detail": "Source path ./data/case-512 not found"}` |
| 422 | `{"detail": "Unsupported ingestion source type"}` |

### GET /ingest/{job_id}
**Summary**: Poll ingestion status for asynchronous lifecycle. Response model to be introduced as `backend.app.models.api.IngestionStatusResponse`.

| Aspect | Value |
| --- | --- |
| Method | GET |
| Path | `/ingest/{job_id}` |
| Path Parameters | `job_id` (UUID) |
| Success Codes | `200 OK` when terminal state reached, `202 Accepted` when still processing |
| Error Codes | `404 Not Found` if job unknown, `410 Gone` if history expired |

#### Response Schema — `IngestionStatusResponse` (planned)
| Field | Type | Validation Rules | Notes |
| --- | --- | --- | --- |
| `job_id` | string | RFC 4122 UUID | Echoes request identifier |
| `status` | string | Enum: `queued`, `running`, `succeeded`, `failed`, `cancelled` | `succeeded` indicates downstream graph, timeline, and forensics pipelines triggered |
| `submitted_at` | string (ISO 8601 UTC) | `format=date-time` | Original enqueue timestamp |
| `updated_at` | string (ISO 8601 UTC) | `format=date-time` | Last state change |
| `errors` | array of objects | Each entry `{ "code": string, "message": string, "source": string }`; optional | Populated when `status` is `failed` |

```json
{
  "job_id": "0f6f7bc4-322b-4e61-a4f7-4b9a61d1adbe",
  "status": "running",
  "submitted_at": "2025-10-27T07:59:41Z",
  "updated_at": "2025-10-27T08:04:12Z",
  "errors": []
}
```

#### Lifecycle Semantics
| Stage | Description |
| --- | --- |
| Initial Response | `202 Accepted` with `status="queued"`; clients persist `job_id` for polling. |
| Polling Loop | Continue requests until `status` is `succeeded` (all downstream artifacts materialized) or `failed` (see `errors`). |
| Caching | Clients MAY send `If-None-Match`; service SHOULD return `304 Not Modified` when status unchanged. |

### GET /query
**Summary**: Retrieve synthesized answer with citations. Implemented via `backend.app.models.api.QueryResponse`. Pagination metadata will be attached using forthcoming `QueryPagination` Pydantic model.

| Aspect | Value |
| --- | --- |
| Method | GET |
| Path | `/query` |
| Required Query Parameters | `q` (string, minLength=3) |
| Optional Query Parameters | `page` (integer ≥ 1, default 1), `page_size` (integer 1–50, default 10), `filters[source]` (string enum matching ingestion source types), `filters[entity]` (string), `rerank` (boolean) |
| Success Codes | `200 OK` |
| Error Codes | `204 No Content` when no supporting evidence, `500 Internal Server Error` when retrieval pipeline fails |

#### Response Schema — `QueryResponse`
| Field | Type | Validation Rules | Notes |
| --- | --- | --- | --- |
| `answer` | string | Non-empty | Primary synthesized response |
| `citations` | array of `CitationModel` | `minItems=0` | Aligns with `backend.app.models.api.CitationModel` |
| `traces` | `TraceModel` | Contains vector and graph diagnostics | Aligns with `backend.app.models.api.TraceModel` |

##### Pagination Metadata (planned `QueryPagination`)
| Field | Type | Validation | Notes |
| --- | --- | --- | --- |
| `page` | integer | ≥ 1 | Current page |
| `page_size` | integer | 1–50 | Items per page |
| `total_items` | integer | ≥ 0 | Count of trace vector hits |
| `has_next` | boolean | | Indicates if `Link` header for next page present |

```json
{
  "answer": "Acme entered into the supply agreement on 2024-05-12 and breached the exclusivity clause in Q3.",
  "citations": [
    {"docId": "doc-492", "span": "Paragraph 4", "uri": "https://dms.example.com/doc-492"}
  ],
  "traces": {
    "vector": [
      {"id": "vec-01", "score": 0.87, "docId": "doc-492"},
      {"id": "vec-02", "score": 0.81, "docId": "doc-771"}
    ],
    "graph": {
      "nodes": [
        {"id": "entity::Acme", "type": "Entity", "properties": {"label": "Acme Corp"}}
      ],
      "edges": [
        {"source": "doc-492", "target": "entity::Acme", "type": "MENTIONS", "properties": {"evidence": "Acme"}}
      ]
    }
  },
  "meta": {
    "page": 1,
    "page_size": 10,
    "total_items": 24,
    "has_next": true
  }
}
```

### GET /timeline
**Summary**: Return chronological events. Implemented via `backend.app.models.api.TimelineResponse` and `TimelineEventModel`. Pagination extension will reuse planned `TimelinePagination` model.

| Aspect | Value |
| --- | --- |
| Method | GET |
| Path | `/timeline` |
| Optional Query Parameters | `cursor` (opaque string), `limit` (integer 1–100, default 20), `from_ts` & `to_ts` (ISO 8601 timestamps), `entity` (string) |
| Success Codes | `200 OK` |
| Empty Result Handling | Returns `events: []` with corresponding pagination metadata |

#### Response Schema — `TimelineResponse`
| Field | Type | Validation Rules | Notes |
| --- | --- | --- | --- |
| `events` | array of `TimelineEventModel` | Items sorted ascending by `ts` | Mirrors `backend.app.models.api.TimelineResponse` |

##### `TimelineEventModel`
| Field | Type | Validation Rules | Notes |
| --- | --- | --- | --- |
| `id` | string | Unique per event | Stable identifier (document::event::<n>) |
| `ts` | string (ISO 8601 UTC) | `format=date-time` | Ingestion time or document timestamp |
| `title` | string | Non-empty | Short label |
| `summary` | string | Non-empty | Narrative summary |
| `citations` | array of string | Contains document identifiers | Links back to sources |

##### Pagination Metadata (planned `TimelinePagination`)
| Field | Type | Validation | Notes |
| --- | --- | --- | --- |
| `cursor` | string | Optional; opaque | Use for next page requests |
| `limit` | integer | 1–100 | Reflects request limit |
| `has_more` | boolean | | Indicates additional events exist |

```json
{
  "events": [
    {
      "id": "doc::event::0",
      "ts": "2024-10-26T00:00:00Z",
      "title": "Initial Contract Execution",
      "summary": "Acme and Contoso executed the master supply agreement.",
      "citations": ["doc-492"]
    }
  ],
  "meta": {
    "cursor": "g2wAAAAB",
    "limit": 20,
    "has_more": false
  }
}
```

### GET /graph/neighbor
**Summary**: Retrieve neighboring nodes around an entity. Implemented via `backend.app.models.api.GraphNeighborResponse`.

| Aspect | Value |
| --- | --- |
| Method | GET |
| Path | `/graph/neighbor` |
| Required Query Parameters | `id` (string) |
| Success Codes | `200 OK` |
| Error Codes | `404 Not Found` when node absent |

#### Response Schema — `GraphNeighborResponse`
| Field | Type | Validation Rules | Notes |
| --- | --- | --- | --- |
| `nodes` | array of `GraphNodeModel` | Non-empty | Each node includes `id`, `type`, `properties` |
| `edges` | array of `GraphEdgeModel` | Non-empty | Each edge includes `source`, `target`, `type`, `properties` |

```json
{
  "nodes": [
    {"id": "entity::Acme", "type": "Entity", "properties": {"label": "Acme"}}
  ],
  "edges": [
    {
      "source": "doc-492",
      "target": "entity::Acme",
      "type": "MENTIONS",
      "properties": {"evidence": "Acme"}
    }
  ]
}
```

### GET /forensics/document | /forensics/image | /forensics/financial
**Summary**: Fetch artifact-specific forensic analysis. Implemented via `backend.app.models.api.ForensicsResponse`.

| Aspect | Value |
| --- | --- |
| Methods | GET |
| Paths | `/forensics/document`, `/forensics/image`, `/forensics/financial` |
| Required Query Parameters | `id` (string) |
| Success Codes | `200 OK` |
| Error Codes | `404 Not Found` when artifact missing, `415 Unsupported Media Type` when no fallback available |

#### Response Schema — `ForensicsResponse`
| Field | Type | Validation Rules | Notes |
| --- | --- | --- | --- |
| `artifact_id` | string | Matches ingestion asset identifier | Primary lookup key |
| `artifact_type` | string | Enum: `document`, `image`, `financial` | Mirrors endpoint |
| `pipeline_version` | string | SemVer | Communicates toolbox release |
| `summary` | object | Required keys: `risk_level`, `headline`, `confidence` | One-line executive readout |
| `hashes` | object | Contains `sha256` + optional `md5`, `tlsh` | Always populated |
| `metadata` | object | Non-empty | Canonicalized metadata map |
| `signals` | array | Each entry `{ "category": string, "name": string, "value": any, "evidence": string }` | Detailed detections |
| `fallback_applied` | boolean | | `true` when toolbox used downgrade path |
| `raw` | object | Optional | Type-specific payload (`structure`, `authenticity`, `anomalies`, etc.) |

```json
{
  "artifact_id": "doc-492",
  "artifact_type": "document",
  "pipeline_version": "1.2.0",
  "summary": {"risk_level": "medium", "headline": "PDF metadata edited post-signature", "confidence": 0.71},
  "hashes": {"sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "tlsh": "T10293BD123AB4F1E3"},
  "metadata": {"mime": "application/pdf", "pages": 12, "producer": "Acrobat Pro 2024"},
  "signals": [
    {"category": "authenticity", "name": "xmp_modification_after_signature", "value": true, "evidence": "xmp:ModifyDate 2024-10-19"}
  ],
  "fallback_applied": false,
  "raw": {
    "structure": {"toc": ["Summary", "Findings"]},
    "authenticity": {"ela": {"score": 0.96}, "clone": {"matches": []}}
  }
}
```

### Forensics Toolbox Execution Blueprint
1. **Canonicalization Pass** — normalize path/URI, stream bytes, and compute hashes (`sha256`, optional `md5`, `tlsh`) using `hashlib`/`tlsh`.
2. **Metadata Probing** — determine MIME via `python-magic`, harvest core metadata with `hachoir`, and capture file size + timestamps.
3. **Type Routing** — select analyzer based on MIME/extension: `DocumentAnalyzer`, `ImageAnalyzer`, or `FinancialAnalyzer` (see below). Unknown types branch to the fallback routine.
4. **Analyzer Execution Order**:
   - `DocumentAnalyzer`:
     1. Parse containers via `pypdf` (PDF), `python-docx` (DOCX), `extract-msg` (MSG/EML); fallback to `pdfminer.six`/`textract` for text-only extraction.
     2. Run structure modeling (TOC, outlines) and semantic segmentation with `unstructured`.
     3. Perform authenticity checks: signature inspection (`pikepdf`), revision diffing, header consistency (`mailparser` for emails).
   - `ImageAnalyzer`:
     1. Extract EXIF via `piexif` and `Pillow`.
     2. Execute Error Level Analysis with `opencv-python` + `numpy`.
     3. Perform clone/PRNU heuristics using `imagededup` (SSIM) and `pyprnu`; degrade to EXIF-only when dimensions < 128px or unsupported color model.
   - `FinancialAnalyzer`:
     1. Load ledger/tabular sources into `pandas` with `pyarrow` acceleration.
     2. Validate accounting identities using `decimal` totals and cross-sheet reconciliation.
     3. Detect anomalies via `scikit-learn` Isolation Forest (default) and rule-based thresholds; fallback to z-score heuristics when dataset < 32 rows.
5. **Signal Aggregation** — map analyzer outputs into normalized `signals` array and populate `summary` risk classification (low/medium/high) using scoring rubric.
6. **Persistence & API Surfacing** — emit JSON to `./storage/forensics/{fileId}/report.json`, register pointer in vector metadata, and mark ingestion job stage `forensics_complete` when all analyzers succeed.

### Fallback & Unsupported Format Strategy
| Scenario | Behaviour |
| --- | --- |
| Unknown MIME or analyzer failure | Record `fallback_applied=true`, capture hashes + base metadata, emit `signals` entry `{ "category": "coverage", "name": "unsupported_format", "value": "{mime}" }`, respond with HTTP `415` if client requests type-specific endpoint without fallback allowance. |
| Password-protected PDFs | Attempt decryption via configured credential vault; on failure, capture `signals` entry `pdf_password_protected` and expose partial metadata only. |
| Corrupted images | Use `Pillow` to attempt load; if exception persists, store best-effort EXIF (if accessible) and mark `signals` `image_decode_error`. |
| Financial sheets without headers | Apply schema inference using `pandas.read_csv` with `header=None`; require manual mapping queued in `forensics_requeue` table, respond with `202 Accepted` until remediation. |

### Compute & Performance Expectations
| Dimension | Baseline | Notes |
| --- | --- | --- |
| CPU | 8 vCPU minimum for production worker pool | Document + image analyzers CPU-bound; Isolation Forest parallelized via joblib |
| Memory | 16 GiB RAM | Required for multi-page PDF parsing and tabular joins |
| GPU | Optional RTX A2000+ for vision accelerations | Enables PRNU FFT optimizations when available |
| Per-artifact SLA | ≤ 45s for 200-page PDF, ≤ 15s for 25MP image, ≤ 30s for 50k-row ledger | Includes hashing + analyzer stack |
| Throughput | 4 concurrent artifacts per worker | Achieved via asyncio task group with bounded semaphore |
| Storage | Reports capped at 2 MiB each | Enforced via compression and dropping large intermediate matrices |

### API Surfacing of Forensics Artifacts
- `/ingest/{job_id}` → `status_details.forensics` block lists remaining artifacts and timestamps for `canonicalized_at`, `analysis_started_at`, `analysis_completed_at`.
- `/query` → `traces.forensics` contains array of `{ "artifact_id", "summary", "signals" }` to explain answers referencing forensic evidence.
- `/timeline` → Events referencing forensic anomalies include `event.type = "forensics"` with pointer to `/forensics/{type}?id=...`.
- `/forensics/*` → Returns full toolbox payload (`ForensicsResponse`). Clients MUST respect `fallback_applied` to warn on downgraded coverage.

## Domain Models
| Model | Module | Purpose |
| --- | --- | --- |
| `IngestionRequest` | `backend.app.models.api` | Validates ingestion payloads |
| `IngestionResponse` | `backend.app.models.api` | Returns job handle and state |
| `QueryResponse` | `backend.app.models.api` | Encapsulates synthesized answer & traces |
| `TimelineResponse` | `backend.app.models.api` | Wraps ordered event timeline |
| `GraphNeighborResponse` | `backend.app.models.api` | Packages graph neighborhood |
| `ForensicsResponse` | `backend.app.models.api` | Delivers forensic artifacts |
| `IngestionStatusResponse` | **planned** | Will expose job status polling contract |
| `QueryPagination`, `TimelinePagination` | **planned** | Will supply pagination metadata envelopes |

## Constraints
| Constraint | Requirement |
| --- | --- |
| Neo4j Entity IDs | Must be unique per node; relationship types use `UPPER_SNAKE_CASE` |
| Vector Store Path | Default `./storage/vector`; override via configuration |
| Forensics Storage | Artifacts persist under `./storage/forensics/{fileId}/report.json` |
| Forensics Pipeline Order | Canonicalization → Metadata → Analyzer (document/image/financial) → Aggregation → Persistence |
| Toolbox Dependencies | `hashlib`, `tlsh`, `python-magic`, `hachoir`, `pypdf`, `python-docx`, `extract-msg`, `textract`, `pikepdf`, `unstructured`, `Pillow`, `piexif`, `opencv-python`, `numpy`, `imagededup`, `pyprnu`, `pandas`, `pyarrow`, `decimal`, `scikit-learn` |

## Agents Workflow (MS Agents)
| Sequence | Node | Responsibility |
| --- | --- | --- |
| 1 | Ingestion | Normalize and enqueue sources |
| 2 | GraphBuilder | Materialize entities and relationships |
| 3 | Research | Execute retrieval augmented generation |
| 4 | Timeline | Curate chronological narrative |
| 5 | DocumentForensicsAgent / ImageForensicsAgent / FinancialForensicsAgent | Post-ingest forensic enrichment (respect toolbox execution order) |

Context propagation: each node receives `case_id`, `run_id`, and `user_id`, persisting to shared memory. Telemetry: OTel spans emitted per node; logs must capture retrieval context and token usage.

### Canonical Agent States
- `idle`: awaiting work; resources may be warm.
- `pending`: job accepted, prerequisites (credentials, routing) validating.
- `active`: executing primary workload.
- `waiting`: blocked on upstream artifact or external callback; timer guards enforced.
- `succeeded`: work finished; downstream notifications emitted.
- `soft_failed`: transient issue encountered; eligible for retry budget.
- `hard_failed`: unrecoverable error; pipeline halts or reroutes to human review.
- `cancelled`: run intentionally aborted; emit compensating actions if needed.

### State Transitions, Failure Handling, and Retry Logic

#### Ingestion Node
| From State | Event / Condition | To State | Failure Handling | Retry Logic |
| --- | --- | --- | --- | --- |
| `idle` | Job dequeued | `pending` | Validate source schema; emit `ingestion.accepted` span event | n/a |
| `pending` | Connectors resolved & credentials fetched | `active` | Missing credential ➜ mark `soft_failed` | Retry up to 3 times, exp backoff (2^n * 15s) with jitter |
| `pending` | Validation error (schema, path) | `hard_failed` | Emit `ingestion.validation_error`; publish to human review queue | No retry; requires payload correction |
| `active` | All sources loaded, chunks persisted | `succeeded` | Emit `ingestion.completed` metric; notify GraphBuilder | n/a |
| `active` | Connector timeout / throttling | `soft_failed` | Record `ingestion.transient_failure` with connector id | Retry remaining budget with exponential backoff |
| `soft_failed` | Retry budget exhausted | `hard_failed` | Emit `case_handoff_required` signal | No further attempts |
| any | Cancellation request | `cancelled` | Issue delete for partially persisted artifacts | No retry |

#### GraphBuilder Node
| From State | Event / Condition | To State | Failure Handling | Retry Logic |
| --- | --- | --- | --- | --- |
| `idle` | Receives `ingestion.completed` event | `pending` | Validate artifact manifest presence | n/a |
| `pending` | Neo4j session established, ontology cached | `active` | Missing ontology ➜ `soft_failed` with cache refresh | 2 retries, backoff 30s then 60s |
| `pending` | Manifest missing / corrupt | `hard_failed` | Emit `graphbuilder.artifact_missing`; request re-ingest | Requires upstream remediation |
| `active` | Triples committed & indexes refreshed | `succeeded` | Emit `graphbuilder.completed`; trigger Research | n/a |
| `active` | Neo4j commit failure / deadlock | `soft_failed` | Rollback transaction; log `graphbuilder.retry` | Retry with randomized delay 20–45s |
| `active` | Schema mismatch (fatal) | `hard_failed` | Raise `graphbuilder.schema_violation`; stop downstream | Manual migration required |
| any | Cancellation request | `cancelled` | Abort session; delete partial nodes via compensating Cypher | No retry |

#### Research Node
| From State | Event / Condition | To State | Failure Handling | Retry Logic |
| --- | --- | --- | --- | --- |
| `idle` | Receives `graphbuilder.completed` | `pending` | Load retrieval context; warm LLM session | n/a |
| `pending` | Vector + graph context ready | `active` | Missing vector context ➜ `soft_failed` and request replay | 3 retries, 10s base backoff |
| `pending` | Prompt safety policy violation | `hard_failed` | Emit `research.policy_blocked`; escalate | Manual override only |
| `active` | LLM response received, citations validated | `succeeded` | Emit `research.answer_ready`; notify Timeline | n/a |
| `active` | LLM timeout / provider outage | `soft_failed` | Record `research.provider_timeout`; rotate model if configured | Retry with provider failover list |
| `active` | Citation validation fails repeatedly | `hard_failed` | Emit `research.citation_failure`; trigger curator intervention | No further retries |
| any | Cancellation request | `cancelled` | Drop conversation memory; release tokens | No retry |

#### Timeline Node
| From State | Event / Condition | To State | Failure Handling | Retry Logic |
| --- | --- | --- | --- | --- |
| `idle` | Receives `research.answer_ready` | `pending` | Fetch structured events & embeddings | n/a |
| `pending` | Event store reachable | `active` | Event store lag ➜ `soft_failed` | Retry twice, 20s base backoff |
| `pending` | Event store unreachable > 5 min | `hard_failed` | Emit `timeline.store_unavailable`; raise alert | Manual recovery |
| `active` | Timeline assembled, pagination metadata computed | `succeeded` | Emit `timeline.published`; fan-out to subscribers | n/a |
| `active` | Ordering conflict (timestamp gaps) | `soft_failed` | Apply clock skew correction; re-run build | Retry remaining budget |
| `active` | Data corruption detected | `hard_failed` | Emit `timeline.data_corruption`; freeze run | Requires upstream fix |
| any | Cancellation request | `cancelled` | Remove partial timeline artifacts | No retry |

#### Forensics Nodes
| Node | From State | Event / Condition | To State | Failure Handling | Retry Logic |
| --- | --- | --- | --- | --- | --- |
| DocumentForensicsAgent | `idle` | Receives `timeline.published` | `pending` | Validate document manifest | n/a |
| DocumentForensicsAgent | `pending` | Storage accessible | `active` | Storage throttle ➜ `soft_failed` | Retry 3x, 25s base backoff |
| DocumentForensicsAgent | `active` | Hashing + structure extraction done | `succeeded` | Emit `forensics.document_ready` | n/a |
| DocumentForensicsAgent | `active` | Parser fatal error | `hard_failed` | Emit `forensics.document_error`; attach stack trace | Manual tool patch |
| ImageForensicsAgent | `idle` | Receives `timeline.published` | `pending` | Locate media set | n/a |
| ImageForensicsAgent | `pending` | Media available | `active` | Missing media ➜ `soft_failed` | Retry twice, 30s base backoff |
| ImageForensicsAgent | `active` | Analysis complete (EXIF/ELA/PRNU) | `succeeded` | Emit `forensics.image_ready` | n/a |
| ImageForensicsAgent | `active` | GPU accelerator unavailable | `soft_failed` | Queue on CPU fallback | Retry with degraded profile once |
| ImageForensicsAgent | `soft_failed` | Fallback exhausted | `hard_failed` | Emit `forensics.image_unavailable`; escalate | n/a |
| FinancialForensicsAgent | `idle` | Receives `timeline.published` | `pending` | Load ledger extracts | n/a |
| FinancialForensicsAgent | `pending` | Schema validated | `active` | Schema mismatch ➜ `soft_failed` | Retry once after schema refresh |
| FinancialForensicsAgent | `active` | Metrics computed & anomalies tagged | `succeeded` | Emit `forensics.financial_ready` | n/a |
| FinancialForensicsAgent | `active` | Ledger schema mismatch persists | `hard_failed` | Emit `forensics.financial_blocked`; notify finance SME | No retry |
| any Forensics Node | Cancellation request | `cancelled` | Cleanup temp artifacts; record cancellation reason | No retry |

### Failure Escalation Principles
- Transient issues (`soft_failed`) must emit structured telemetry events with `error.class = transient` and attach retry count.
- Hard failures trigger `case_handoff_required` events with enriched context (agent, run_id, diagnostics URI) for human triage.
- Cancellation produces compensating actions: remove scratch artifacts, release locks, and log audit trail for compliance.

### Agent Contracts (Inputs • Outputs • Telemetry • Memory)
| Agent | Required Inputs | Outputs / Side Effects | Telemetry & Metrics | Memory Footprint |
| --- | --- | --- | --- | --- |
| Ingestion | `case_id`, source manifest, credential refs, `run_id` | Persisted chunks (blob store), vector embeddings queued, `ingestion.completed` event | Spans: `ingestion.queue`, `ingestion.load`<br>Metrics: processed bytes, chunk count<br>Logs: connector latency | Ephemeral staging buffers ≤ 2 GB<br>Persistent storage lives in blob/Qdrant |
| GraphBuilder | `case_id`, chunk handles, ontology version, `run_id` | Neo4j nodes/edges, `graphbuilder.completed` event, updated ontology cache timestamp | Spans: `graphbuilder.extract`, `graphbuilder.commit`<br>Metrics: nodes/edges upserted, Cypher latency<br>Logs: ontology drift events | In-memory graph batch window ≤ 1 GB<br>Persistent layer: Neo4j cluster |
| Research | Query intents, vector hits, graph triples, guardrail config | Synthesized answer, citation bundle, `research.answer_ready` event | Spans: `research.retrieve`, `research.generate`<br>Metrics: token usage, model latency<br>Logs: safety filters applied | Conversation scratchpad ≤ 256 MB<br>Ephemeral vector cache only |
| Timeline | Event candidates, answer context, pagination policy | Ordered timeline payload, `timeline.published` event | Spans: `timeline.assemble`<br>Metrics: events emitted, time normalization adjustments<br>Logs: conflict resolution actions | Working set ≤ 512 MB for event sorting<br>Persistent timeline cache (Redis/Postgres) |
| DocumentForensicsAgent | Document manifest, blob handles, checksum policy | Hash digests, structural metadata, `forensics.document_ready` event | Spans: `forensics.document.hash`<br>Metrics: documents processed, average parse time<br>Logs: integrity anomalies | Temp disk ≤ 1 GB for PDF/image conversions<br>Artifacts stored in forensics vault |
| ImageForensicsAgent | Media manifest, GPU/CPU profile, anomaly thresholds | EXIF payload, ELA/PRNU scores, `forensics.image_ready` event | Spans: `forensics.image.analysis`<br>Metrics: GPU utilization, anomalies flagged<br>Logs: model confidence summaries | GPU VRAM ≤ 2 GB<br>CPU buffers ≤ 512 MB<br>Artifacts persisted to vault |
| FinancialForensicsAgent | Ledger extracts, currency config, anomaly rules | Trend charts, anomaly list, `forensics.financial_ready` event | Spans: `forensics.financial.evaluate`<br>Metrics: transactions processed, anomaly rate<br>Logs: rule triggers | Memory pool ≤ 768 MB for ledger aggregation<br>Metrics persisted to warehouse |

### Sequence Diagrams — Handoff Visibility
```mermaid
sequenceDiagram
    participant Client
    participant Ingestion
    participant GraphBuilder
    participant Research

    Client->>Ingestion: submit sources (case_id, run_id)
    activate Ingestion
    Ingestion-->>Client: job accepted (job_id)
    Ingestion->>GraphBuilder: emit ingestion.completed
    deactivate Ingestion
    activate GraphBuilder
    GraphBuilder->>GraphBuilder: upsert entities/relations
    GraphBuilder->>Research: emit graphbuilder.completed
    deactivate GraphBuilder
    activate Research
    Research->>Research: retrieve & synthesize answer
    Research-->>Client: answer (via /query)
    deactivate Research
```

```mermaid
sequenceDiagram
    participant Research
    participant Timeline
    participant Subscriber

    Research->>Timeline: emit research.answer_ready
    activate Timeline
    Timeline->>Timeline: assemble chronological events
    Timeline-->>Research: ack timeline.published
    Timeline-->>Subscriber: deliver timeline payload
    deactivate Timeline
```

```mermaid
sequenceDiagram
    participant Timeline
    participant DocumentForensics
    participant ImageForensics
    participant FinancialForensics
    participant Ops

    Timeline->>DocumentForensics: fan-out timeline.published
    Timeline->>ImageForensics: fan-out timeline.published
    Timeline->>FinancialForensics: fan-out timeline.published
    activate DocumentForensics
    activate ImageForensics
    activate FinancialForensics
    DocumentForensics-->>Timeline: forensics.document_ready
    ImageForensics-->>Timeline: forensics.image_ready
    FinancialForensics-->>Timeline: forensics.financial_ready
    DocumentForensics-->>Ops: emit case_handoff_required (on hard_fail)
    ImageForensics-->>Ops: emit case_handoff_required (on hard_fail)
    FinancialForensics-->>Ops: emit case_handoff_required (on hard_fail)
    deactivate DocumentForensics
    deactivate ImageForensics
    deactivate FinancialForensics
```

## Retrieval Logic
| Step | Operation |
| --- | --- |
| 1 | `vector_results = VectorSearch(q, top_k=8)` |
| 2 | `graph_context = GraphNeighborhood(entities_from(vector_results), radius=2)` |
| 3 | Prompt LLM with query, vector snippets, and graph triples |
| 4 | Enforce cite-or-silence guardrails and emit structured answer |

## Non-Functional Requirements
| Category | SLO | Validation |
| --- | --- | --- |
| Availability & Offline Continuity | \>=99.5% API uptime measured monthly; ingest queue must buffer 12 hours of backlog at 150 documents/hour (1,800 documents) without data loss. | Continuous health polling via `tools/monitoring/uptime_probe.py` and offline drain rehearsal documented in [docs/validation/nfr_validation_matrix.md#offline-tolerance](../../validation/nfr_validation_matrix.md#offline-tolerance). |
| Reproducibility | \<=0.5% drift tolerance across job manifests, timeline events, and forensics hashes when replaying the same workspace three times; cryptographic hashes must match exactly. | Deterministic replay harness `tools/perf/reproducibility_check.py`. |
| Performance | `/query` p95 latency \<=1,800 ms under Baseline Query load profile; sustained ingest throughput \>=150 documents/hour for three-file workspaces on reference hardware. | Synthetic workload driver `tools/perf/query_latency_probe.py` executed with the Baseline Query and Batch Ingest profiles in [docs/validation/nfr_validation_matrix.md#load-profiles](../../validation/nfr_validation_matrix.md#load-profiles). |
| Provider Policy | \>=95% of LLM calls routed to `gemini-2.5-flash`; fallback providers collectively \<=1% error rate over any rolling 7-day window. | Invocation ledger audit using `tools/monitoring/provider_mix_check.py` against the `build_logs/llm_invocations.jsonl` export. |

### Validation Hardware & Load Profiles
- Reference hardware: 8 vCPU (3.0 GHz Ryzen 7840HS class), 32 GB RAM, NVMe SSD (3.2 GB/s sequential read), no discrete GPU required.
- Network: \<=40 ms RTT to vector and graph stores during validation, 1 Gbps LAN.
- Detailed load profiles and execution guidance are catalogued in [docs/validation/nfr_validation_matrix.md](../../validation/nfr_validation_matrix.md).
