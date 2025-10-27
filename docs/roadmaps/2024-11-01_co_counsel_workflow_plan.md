# Co-Counsel Workflow Implementation Roadmap

## Vision
- Deliver fully operational FastAPI service that honors the PRP contracts and persists knowledge artifacts across Neo4j, Qdrant, and filesystem storage.
- Embed deterministic, locally runnable analytics to support ingestion, retrieval, timeline, graph, and forensics workflows end-to-end.

## Phase 1 — Foundations
- ### Configuration Architecture
  - #### Settings Source
    - ##### Environment variables override sensible defaults for service URLs and storage paths.
    - ##### Support in-memory fallbacks for local testing (Neo4j `memory://`, Qdrant `:memory:`).
  - #### Resource Bootstrapping
    - ##### Ensure directories for vectors, forensics, timelines, and job metadata exist on load.
    - ##### Create schema management helpers for Neo4j constraints and Qdrant collections.
- ### Data Model Definitions
  - #### Document Model
    - ##### Fields

      | Field | Type | Nullable | Notes |
      | --- | --- | --- | --- |
      | `document_id` | `UUID4` (`str`) | No | Primary key shared across APIs, Neo4j, and Qdrant payloads. |
      | `external_id` | `str` | Yes | Upstream system reference (SharePoint item id, email message id, etc.). |
      | `source_type` | `Literal["upload", "email", "sharepoint", "s3", "database"]` | No | Enumerates provenance channels supported by ingestion. |
      | `source_uri` | `AnyUrl` | Yes | Direct locator for retrieval or audit when available. |
      | `title` | `str` | Yes | Preferred display name for UI surfaces; defaults to filename. |
      | `mime_type` | `str` | Yes | Detected content type (`application/pdf`, `text/plain`, ...). |
      | `sha256` | `str` | Yes | Cryptographic hash captured during ingestion/forensics. |
      | `size_bytes` | `PositiveInt` | Yes | Raw byte size of the primary artifact. |
      | `language` | `str` | Yes | ISO 639-1 language code derived during processing. |
      | `ingested_at` | `datetime` | No | UTC timestamp for when the document entered the pipeline. |
      | `created_at` | `datetime` | Yes | Source-authored timestamp if known. |
      | `tags` | `List[str]` | Yes | User/system assigned labels used for filtering. |
      | `metadata` | `Dict[str, Any]` | Yes | Flexible bag for modality-specific values (e.g., email headers). |

  - #### Chunk Model
    - ##### Fields

      | Field | Type | Nullable | Notes |
      | --- | --- | --- | --- |
      | `chunk_id` | `UUID4` (`str`) | No | Unique identifier for vector store payloads and trace responses. |
      | `document_id` | `UUID4` (`str`) | No | Foreign key to `Document`. |
      | `ordinal` | `NonNegativeInt` | No | Stable ordering of chunks within a document. |
      | `text` | `constr(min_length=1)` | No | Raw textual window post-normalization. |
      | `start_offset` | `NonNegativeInt` | Yes | Character offset of the chunk start in the original text. |
      | `end_offset` | `NonNegativeInt` | Yes | Character offset of the chunk end (exclusive). |
      | `embedding` | `conlist(float, min_items=128, max_items=128)` | No | Deterministic 128-dim vector stored in Qdrant. |
      | `score` | `float` | Yes | Optional relevance score populated on retrieval responses. |

  - #### Entity Model
    - ##### Fields

      | Field | Type | Nullable | Notes |
      | --- | --- | --- | --- |
      | `entity_id` | `UUID4` (`str`) | No | Primary key for graph nodes. |
      | `canonical_name` | `str` | No | Normalized, case-folded name used for deduplication. |
      | `type` | `Literal["PERSON", "ORG", "LOCATION", "DATE", "AMOUNT", "OTHER"]` | No | Coarse-grained category powering downstream analytics. |
      | `aliases` | `List[str]` | Yes | Alternate spellings gathered during extraction. |
      | `salience` | `float` | Yes | Optional importance score (0–1) surfaced by NER pipeline. |
      | `properties` | `Dict[str, Union[str, float, int]]` | Yes | Structured attributes such as titles or account numbers. |

  - #### Relation Model
    - ##### Fields

      | Field | Type | Nullable | Notes |
      | --- | --- | --- | --- |
      | `relation_id` | `UUID4` (`str`) | No | Unique identifier for provenance tracking. |
      | `subject_entity_id` | `UUID4` (`str`) | No | Source entity in the relation. |
      | `object_entity_id` | `UUID4` (`str`) | No | Target entity in the relation. |
      | `predicate` | `str` | No | Normalized verb/connector (e.g., `OWNS`, `TRANSFERRED_TO`). |
      | `confidence` | `float` | Yes | Extraction confidence between 0 and 1. |
      | `source_document_id` | `UUID4` (`str`) | No | Document grounding the relation. |
      | `source_chunk_id` | `UUID4` (`str`) | Yes | Chunk grounding the relation; optional for document-level facts. |
      | `qualifiers` | `Dict[str, Any]` | Yes | Temporal or quantitative qualifiers (`amount`, `timestamp`). |

  - #### ForensicsArtifact Model
    - ##### Fields

      | Field | Type | Nullable | Notes |
      | --- | --- | --- | --- |
      | `artifact_id` | `UUID4` (`str`) | No | Identifier for individual forensic derivative. |
      | `document_id` | `UUID4` (`str`) | No | Links artifact back to its source document. |
      | `artifact_type` | `Literal["hash", "metadata", "structure", "authenticity", "financial"]` | No | Enumerates supported analyzer outputs. |
      | `path` | `FilePath` | No | Relative filesystem path under the forensics storage root. |
      | `media_type` | `str` | Yes | MIME type for JSON, images (ELA heatmaps), CSV summaries, etc. |
      | `generated_at` | `datetime` | No | Timestamp recorded when analyzer finished writing the artifact. |
      | `checksum` | `str` | Yes | Optional SHA-256 of the artifact file for tamper detection. |
      | `summary` | `str` | Yes | Human-readable synopsis (anomaly counts, alerts). |
      | `payload` | `Dict[str, Any]` | Yes | Embedded metadata for quick API access without re-reading disk. |

  - #### Persistence Mapping
    - ##### Neo4j Graph Layer
      - `Document` nodes carry the fields above with `document_id` uniqueness and supporting indexes on `source_type`, `ingested_at`.
      - `Chunk` nodes store `chunk_id`, `ordinal`, `start_offset`, `end_offset` and maintain `(:Document)-[:HAS_CHUNK]->(:Chunk)` relationships.
      - `Entity` nodes expose `entity_id`, `canonical_name`, `type`, `salience`, and `properties` with uniqueness on `entity_id` and optional composite index on `(canonical_name, type)`.
      - `Relation` relationships materialize as `(:Entity)-[:RELATION {relation_id, predicate, confidence, qualifiers, source_document_id, source_chunk_id}]->(:Entity)` with uniqueness on `relation_id` enforced via relationship property constraint.
      - `ForensicsArtifact` nodes attach to documents through `(:Document)-[:HAS_ARTIFACT]->(:ForensicsArtifact)` storing `artifact_id`, `artifact_type`, `path`, `media_type`, `generated_at`, and `checksum`.
    - ##### Vector Store (Qdrant)
      - Collection `chunk_embeddings` holds 128-dimension cosine vectors keyed by `chunk_id`; payload replicates `document_id`, `ordinal`, `source_type`, `tags`, and `metadata` slices for filtering.
      - Document-level payloads mirror into a light `documents` collection that stores a 1-dim zero vector placeholder while focusing on payload attributes (`document_id`, `title`, `source_uri`) for join-free metadata fetches.
    - ##### Filesystem Layout
      - Raw uploads persist under `storage/documents/{document_id}/source.ext` with metadata manifest at `storage/documents/{document_id}/manifest.json`.
      - Forensics outputs live at `storage/forensics/{document_id}/{artifact_type}/{artifact_id}.json|png`, matching the `path` attribute captured in the model.
      - Chunk cache (optional) can store serialized text at `storage/chunks/{document_id}/{ordinal}.txt` for re-hydration during re-embedding jobs.

  - #### Initialization & Migration Guidance
    - ##### Neo4j
      - Execute the Cypher bundle in `infra/migrations/neo4j/2025-10-28_data_model_constraints.cql` on deployment or via startup hook to guarantee constraints and indexes.
    - ##### Qdrant
      - Run the Python bootstrap in `infra/migrations/qdrant/2025-10-28_chunk_collection.py` (idempotent) to create/update vector collections with the schema above.
    - ##### Filesystem
      - Provision directories with `mkdir -p storage/{documents,forensics,chunks}` and ensure service accounts have read/write permissions; manifests are generated automatically during ingestion jobs.

## Phase 2 — Workflow Engines
- ### Ingestion Pipeline
  - #### Source Handlers
    - ##### Local filesystem enumerator with recursive traversal + MIME detection.
    - ##### SharePoint placeholder rejection with actionable error (explicitly unsupported until credentials provided).
  - #### Text Processing
    - ##### UTF-8 normalization + fallback decoding.
    - ##### Semantic chunker (400 char windows with overlap) with metadata propagation.
  - #### Embedding Strategy
    - ##### Deterministic hashed term-frequency vectorizer (dimension 128) using SHA-256.
    - ##### Unit-length normalization for cosine-friendly similarity.
  - #### Persistence
    - ##### Upsert Qdrant points with document + chunk metadata.
    - ##### Create/update Neo4j nodes: `Document`, `Entity`, `MENTIONS` relationships.
    - ##### Extract simple events (date regex) and append to timeline store.
    - ##### Generate forensics artifacts per modality and save under storage tree.
    - ##### Record ingestion job manifest with completion timestamp + artifacts.

- ### Retrieval Engine
  - #### Vector Search
    - ##### Query embedding using same hashing vectorizer.
    - ##### Top-k search against Qdrant with payload fetch.
  - #### Graph Expansion
    - ##### Identify entity ids from retrieved payloads.
    - ##### Pull two-hop neighborhood via GraphService abstraction.
  - #### Response Composer
    - ##### Construct concise answer summary from highest-score chunk(s).
    - ##### Attach citations (doc id, span excerpt, optional file URI).
    - ##### Provide trace data for vectors (scores, chunk ids) and graph (nodes/edges).

- ### Timeline Service
  - #### Storage Format
    - ##### JSONL backed by append-only writes, read with ordering by timestamp.
  - #### API Logic
    - ##### Filter/normalize timestamps, default ordering descending recency.

- ### Graph Service
  - #### Query Endpoint
    - ##### Validate requested id exists.
    - ##### Return typed nodes/edges with properties sanitized for JSON serialization.

- ### Forensics Services
  - #### Document Forensics
    - ##### Hash digests (SHA256, MD5), size, word/line counts, MIME detection.
  - #### Image Forensics
    - ##### Metadata via Pillow (dimensions, mode, EXIF if present).
    - ##### Error Level Analysis heatmap score (per-channel mean absolute diff).
    - ##### Clone detection heuristic via block hashing (avg hash) comparisons.
  - #### Financial Forensics
    - ##### CSV/Excel ingestion (pandas-free) using `csv` module.
    - ##### Column typing heuristics; totals for numeric columns; anomaly detection via z-score.

## Phase 3 — API Wiring & Contracts
- ### FastAPI Router Composition
  - #### Dependency Injection
    - ##### Provide service singletons (Settings, GraphService, VectorService, TimelineStore, ForensicsStore).
  - #### Endpoint Implementations
    - ##### `/ingest` returns 202 + job id, synchronous job execution for MVP.
    - ##### `/query` returns retrieval payloads with citations and traces.
    - ##### `/timeline` streams timeline events.
    - ##### `/graph/neighbor` surfaces neighbor graph.
    - ##### `/forensics/document|image|financial` loads saved artifacts and handles missing cases gracefully.

## Phase 4 — Testing & Quality Gates
- ### Unit Tests
  - #### Vectorizer, chunker, and timeline parsers with deterministic outputs.
- ### Integration Tests
  - #### FastAPI client covering happy paths and error scenarios for each endpoint.
  - #### Temporary storage + in-memory services to guarantee hermeticity.
- ### Documentation Traceability
  - #### Expand PRP doc with explicit payload/status references per endpoint.

## Phase 5 — Polish & Compliance
- ### Repository Hygiene
  - #### Update requirements, ensure dependency locking.
  - #### Append chain-of-stewardship entry.
- ### Validation
  - #### Run pytest suite; ensure zero lint/test failures.
  - #### Manual code inspection pass (two iterations minimum) before submission.

