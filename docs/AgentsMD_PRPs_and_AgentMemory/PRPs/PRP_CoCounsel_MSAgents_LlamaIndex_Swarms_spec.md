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
| Error Codes | `404 Not Found` when artifact missing |

#### Response Schema — `ForensicsResponse`
| Field | Type | Validation Rules | Notes |
| --- | --- | --- | --- |
| `data` | object | Arbitrary JSON validated per artifact type | Contains `hashes`, `metadata`, `structure`, `authenticity`, `anomalies`, etc. |

```json
{
  "data": {
    "hashes": {"sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
    "metadata": {"mime": "application/pdf", "pages": 12},
    "structure": {"toc": ["Summary", "Findings"]},
    "authenticity": {"score": 0.96, "signals": ["ela_uniform", "no_clone_match"]}
  }
}
```

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
| Forensics Storage | Artifacts persist under `./storage/forensics/{fileId}/` |

## Agents Workflow (MS Agents)
| Sequence | Node | Responsibility |
| --- | --- | --- |
| 1 | Ingestion | Normalize and enqueue sources |
| 2 | GraphBuilder | Materialize entities and relationships |
| 3 | Research | Execute retrieval augmented generation |
| 4 | Timeline | Curate chronological narrative |
| 5 | DocumentForensicsAgent / ImageForensicsAgent / FinancialForensicsAgent | Post-ingest forensic enrichment |

Context propagation: each node receives `case_id`, `run_id`, and `user_id`, persisting to shared memory. Telemetry: OTel spans emitted per node; logs must capture retrieval context and token usage.

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
