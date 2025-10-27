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

## Retrieval Logic
| Step | Operation |
| --- | --- |
| 1 | `vector_results = VectorSearch(q, top_k=8)` |
| 2 | `graph_context = GraphNeighborhood(entities_from(vector_results), radius=2)` |
| 3 | Prompt LLM with query, vector snippets, and graph triples |
| 4 | Enforce cite-or-silence guardrails and emit structured answer |

## Non-Functional Requirements
| Category | Expectation |
| --- | --- |
| Availability | Core flows operate offline-first |
| Reproducibility | Deterministic seeds for repeatable runs |
| Performance | Responsive on laptop-scale corpora |
| Provider Policy | Default `Gemini-2.5-Flash`; configurable `GPT-5.0` option |
