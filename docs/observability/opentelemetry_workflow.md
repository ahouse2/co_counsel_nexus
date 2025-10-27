# OpenTelemetry Workflow Instrumentation Guide

## Purpose
This guide documents the required spans, metrics, log fields, and context propagation rules for the Co-Counsel workflow. It captures the acceptance criteria that ensure observability is consistent across local development and continuous integration environments.

## Workflow Spans, Metrics, and Logs
| Workflow node | Span name & hierarchy | Required span attributes | Metrics to emit | Structured log fields |
| --- | --- | --- | --- | --- |
| FastAPI ingress | Parent span `http.server.request` | `http.method`, `http.route`, `http.status_code`, `case_id`, `run_id`, `user_id` | Histogram `http.server.duration` | Access log payload containing `case_id`, `run_id`, `user_id`, `endpoint`, `status`, `latency_ms` |
| Ingestion | Child span `workflow.ingestion` with nested handler/chunk/embedding/persistence spans | `case_id`, `run_id`, `user_id`, `job_id`, `source_type`, `document_id`, `ingested_at`, `chunk_count` | Timer `ingestion.duration`, counters `ingestion.documents`, `ingestion.chunks_indexed`, `ingestion.forensics_artifacts` | `event="ingestion.persist.document"`, `document_id`, `source_type`, `qdrant_collection`, `neo4j_nodes_written`, `timeline_events_added`, `artifact_ids` |
| GraphBuilder | `workflow.graph_builder` with child span `graph.upsert` | `case_id`, `run_id`, `user_id`, `document_id`, `entity_count`, `relation_count` | Counters `graph.entities_upserted`, `graph.relations_upserted`, timer `graph.duration` | `event="graph.upsert"`, `document_id`, `entity_ids`, `relation_ids`, `neo4j_query_ms` |
| Research (hybrid retrieval + answer synthesis) | `workflow.research` with nested spans `retrieval.vector_search`, `retrieval.graph_expand`, `llm.prompt` | `case_id`, `run_id`, `user_id`, `question`, `top_k`, `model`, `token_count_prompt`, `token_count_completion` | Gauges `retrieval.vector_latency`, `retrieval.graph_latency`; counters `llm.completions`, timer `llm.latency`, counter `answer.citations` | `event="retrieval.trace"`, `question`, `vector_hits`, `graph_nodes`, `graph_edges`, `citations` |
| Timeline | `workflow.timeline` with child span `timeline.build` | `case_id`, `run_id`, `user_id`, `event_count`, `filter_range` | Counter `timeline.events_returned`, timer `timeline.duration` | `event="timeline.result"`, `event_ids`, `from_ts`, `to_ts`, `filters_applied` |
| Forensics agents | `workflow.forensics` with modality spans `forensics.document`, `forensics.image`, `forensics.financial` | `case_id`, `run_id`, `user_id`, `document_id`, `artifact_type`, `artifact_id`, `generated_at` | Counters `forensics.artifacts_generated`, `forensics.anomalies_detected`, timer `forensics.duration` | `event="forensics.artifact"`, `artifact_id`, `artifact_type`, `checksum`, `summary`, `media_type` |

## Context Propagation Strategy
1. **FastAPI layer**
   - Accept `case_id`, `run_id`, and `user_id` via headers or request body.
   - Attach identifiers to the incoming span and store them in the FastAPI dependency container so every endpoint (e.g., `/ingest`, `/query`, `/timeline`, `/graph/neighbor`, `/forensics/*`) retrieves the same context object.
   - Include identifiers in response metadata (`IngestionResponse`, `QueryResponse`, `TimelineResponse`, `GraphNeighborResponse`, `ForensicsResponse`) for downstream replay/correlation.
2. **Agent graph**
   - Inject the context object into shared memory before invoking each node.
   - Require each span to read the identifiers and append node-specific state (chunk counts, entity IDs, artifact references) to logs or span attributes.
3. **Neo4j writes**
   - Persist identifiers on `Document`, `Entity`, `Relation`, and `ForensicsArtifact` nodes/edges as properties (e.g., `case_id`, `run_id`, `user_id`).
   - Ensure graph queries can trace back to the originating workflow run without additional joins.
4. **Qdrant interactions**
   - Include identifiers in point payload metadata during upsert (`payload["case_id"]`, etc.).
   - Surface the same metadata when returning retrieval results so telemetry matches API responses.
5. **Propagation flow**
   - Flow identifiers from HTTP ingress → FastAPI dependency → agent graph memory → storage layers → response payloads.
   - Every span/log emission must reference the shared context to avoid orphaned telemetry records.

## Acceptance Criteria and Sample Artifacts
1. **Local verification**
   - Use Docker Compose to start services and confirm the FastAPI health check (`docker compose -f infra/docker-compose.yml up -d --build api`, `curl http://localhost:8000/health`).
   - Execute representative ingestion and research requests; verify the OpenTelemetry collector receives spans `http.server.request`, `workflow.ingestion`, `workflow.research`, etc., each populated with the identifiers and attributes listed above.
2. **CI verification**
   - Run smoke scenarios in the pipeline with exporters targeting the CI telemetry backend.
   - Fail the build if spans or structured logs omit `case_id`, `run_id`, or `user_id`, or if required metrics counters remain zero after workflow execution. Automated assertions can parse in-memory exporter JSON during pytest runs.
3. **Sample trace artifact**
   ```json
   {
     "span": "workflow.research",
     "attributes": {
       "case_id": "CASE-2025-0001",
       "run_id": "RUN-12345",
       "user_id": "user-42",
       "question": "What agreements reference Project Atlas?",
       "top_k": 5
     },
     "events": [
       {
         "name": "retrieval.trace",
         "attributes": {
           "traces": {
             "vector": [
               {"id": "point-1", "score": 0.88, "docId": "doc-492"},
               {"id": "point-2", "score": 0.77, "docId": "doc-318"}
             ],
             "graph": {
               "nodes": [{"id": "entity::Atlas", "type": "ORG", "properties": {"salience": 0.9}}],
               "edges": [{"source": "entity::Atlas", "target": "entity::Acme", "type": "RELATION"}]
             }
           }
         }
       }
     ]
   }
   ```
4. **Structured log example**
   ```json
   {
     "event": "ingestion.persist.document",
     "case_id": "CASE-2025-0001",
     "run_id": "RUN-12345",
     "user_id": "user-42",
     "job_id": "JOB-6789",
     "document_id": "doc-492",
     "source_type": "upload",
     "chunk_count": 18,
     "neo4j_nodes_written": {"Document": 1, "Entity": 6, "Relation": 4},
     "qdrant_collection": "chunk_embeddings",
     "timeline_events_added": 3,
     "artifact_ids": ["artifact-hash", "artifact-metadata"]
   }
   ```
5. **Metric expectations**
   - After a successful ingestion and research run, counters `ingestion.documents`, `ingestion.chunks_indexed`, `graph.entities_upserted`, `retrieval.vector_latency`, and `forensics.artifacts_generated` must report non-zero samples, reflecting the mandatory workflow steps.

