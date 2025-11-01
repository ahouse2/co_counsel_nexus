# Backend API & Component Map

This document enumerates the backend surface area that the front-end consumes so that the UI can be revamped without breaking server-side behaviour. It organises REST and GraphQL endpoints alongside the core service classes, storage layers, and cross-cutting concerns that power them.

## Platform Overview
- The FastAPI application is defined in `backend/app/main.py`, where telemetry is initialised, the app metadata is populated, mutual TLS middleware is installed, and the GraphQL application is mounted for both HTTP and WebSocket access.【F:backend/app/main.py†L25-L142】
- Startup initialises long-running dependencies such as the ingestion worker and agent orchestrator; shutdown drains the ingestion worker before exit.【F:backend/app/main.py†L207-L216】
- All endpoints return pydantic response models housed in `backend/app/models/api.py`, ensuring typed responses for the UI.【F:backend/app/main.py†L34-L89】

## Security & Observability
- Every route enforces bearer-token + mTLS dual auth via dependency functions (e.g., `authorize_agents_run`) that validate certificates, decode JWTs, enforce scopes/roles, and append security audit events.【F:backend/app/main.py†L116-L133】【F:backend/app/security/dependencies.py†L20-L198】
- Billing telemetry is emitted across endpoints using `record_billing_event`, while domain services push OpenTelemetry metrics and traces (e.g., voice, ingestion, retrieval) for latency, throughput, and fallback tracking.【F:backend/app/main.py†L271-L390】【F:backend/app/services/voice/service.py†L11-L340】【F:backend/app/services/ingestion.py†L14-L82】【F:backend/app/services/retrieval.py†L20-L82】

## REST Domain Map

### Voice conversations
- **GET `/voice/personas`** – Lists configured personas, filtering unavailable speakers through `VoiceService.list_personas`; requires the same principal scope as running agents.【F:backend/app/main.py†L262-L269】【F:backend/app/services/voice/service.py†L200-L231】
- **POST `/voice/sessions`** – Accepts multipart audio, runs STT → sentiment → agent query → TTS via `VoiceService.create_session`, records GPU usage, persists the session, and returns metadata plus a signed streaming URL.【F:backend/app/main.py†L271-L360】【F:backend/app/services/voice/service.py†L233-L360】
- **GET `/voice/sessions/{session_id}`** – Hydrates a prior session, augmenting it with any agent memory stored in `AgentMemoryStore` threads.【F:backend/app/main.py†L304-L343】【F:backend/app/services/voice/service.py†L200-L209】
- **GET `/voice/sessions/{session_id}/response`** – Streams synthesised audio directly from the session store as a WAV attachment.【F:backend/app/main.py†L346-L360】【F:backend/app/services/voice/service.py†L233-L360】

### Ingestion pipeline
- **POST `/ingest`** – Queues an ingestion job, stores it in `JobStore`, and emits billing metrics proportional to the number of sources.【F:backend/app/main.py†L363-L390】【F:backend/app/services/ingestion.py†L38-L82】
- **GET `/ingest/{job_id}`** – Returns job status from the job store with role-aware restrictions; also sets HTTP 202 for in-flight jobs.【F:backend/app/main.py†L393-L423】【F:backend/app/services/ingestion.py†L38-L82】

### Knowledge hub
- **POST `/knowledge/search`** – Executes semantic search across curated playbooks via `KnowledgeService`, including optional graph-derived filters.【F:backend/app/main.py†L426-L443】【F:backend/app/services/knowledge.py†L30-L176】
- **GET `/knowledge/lessons`** – Lists lessons sourced from the catalog and cached in the knowledge profile store.【F:backend/app/main.py†L446-L456】【F:backend/app/services/knowledge.py†L96-L176】
- **GET `/knowledge/lessons/{lesson_id}`** – Returns full lesson content, raising 404 when the catalog entry is missing.【F:backend/app/main.py†L459-L473】【F:backend/app/services/knowledge.py†L121-L176】
- **POST `/knowledge/lessons/{lesson_id}/progress`** – Records completion progress per section within `KnowledgeProfileStore` and increments telemetry counters.【F:backend/app/main.py†L476-L496】【F:backend/app/services/knowledge.py†L30-L54】【F:backend/app/services/knowledge.py†L96-L176】
- **POST `/knowledge/lessons/{lesson_id}/bookmark`** – Toggles bookmarks for the current principal, persisting the flag in the profile store and logging metrics.【F:backend/app/main.py†L499-L514】【F:backend/app/services/knowledge.py†L30-L54】【F:backend/app/services/knowledge.py†L96-L176】

### Retrieval & query
- **GET `/query`** – Serves the hybrid retrieval stack, allowing filters, reranking, and streaming responses while tracking billing and suppressing traces for certain roles.【F:backend/app/main.py†L517-L597】【F:backend/app/services/retrieval.py†L20-L344】

### Timeline intelligence
- **GET `/timeline`** – Provides paginated, filterable events enriched with graph highlights, while emitting billing telemetry and raising workflow errors on invalid ranges.【F:backend/app/main.py†L599-L675】【F:backend/app/services/timeline.py†L10-L140】

### Graph exploration
- **GET `/graph/neighbor`** – Fetches nearby nodes and edges using `GraphService.neighbors`, which falls back to in-memory stores when Neo4j is unavailable.【F:backend/app/main.py†L677-L698】【F:backend/app/services/graph.py†L1-L178】

### Forensics analyzers
- **GET `/forensics/document|image|financial`** – Loads modality-specific reports generated by `ForensicsService`, enforcing media support checks and returning structured metadata, signals, and stages.【F:backend/app/main.py†L701-L753】【F:backend/app/services/forensics.py†L34-L159】

### Agent orchestration
- **POST `/agents/run`** – Executes the multi-agent case workflow with controllable autonomy/turn limits, records billing units, and returns the persisted thread transcript.【F:backend/app/main.py†L756-L788】【F:backend/app/services/agents.py†L1-L160】
- **GET `/agents/threads/{thread_id}`** – Retrieves a specific agent thread from `AgentMemoryStore`, surfacing the full run transcript and metadata.【F:backend/app/main.py†L791-L801】【F:backend/app/services/agents.py†L1-L160】
- **GET `/agents/threads`** – Lists all known threads for the tenant/principal, allowing the UI to render recent workspaces.【F:backend/app/main.py†L804-L812】【F:backend/app/services/agents.py†L1-L160】

### Scenario director
- **GET `/scenarios`** – Returns available scenario manifests for simulation tooling via the scenario engine.【F:backend/app/main.py†L813-L820】【F:backend/app/services/scenarios.py†L1-L160】
- **GET `/scenarios/{scenario_id}`** – Hydrates a full scenario definition along with the director manifest for UI scripting.【F:backend/app/main.py†L823-L837】【F:backend/app/services/scenarios.py†L1-L160】
- **POST `/scenarios/run`** – Executes a scripted/AI-driven run, delivering transcript turns and telemetry payloads for replay in the front end.【F:backend/app/main.py†L838-L859】【F:backend/app/services/scenarios.py†L1-L160】

### Text-to-speech
- **POST `/tts/speak`** – Synthesises speech via the optional `TextToSpeechService`, encoding audio as base64 when the service is configured.【F:backend/app/main.py†L862-L886】【F:backend/app/services/tts.py†L1-L160】

### Dev agent governance
- **GET `/dev-agent/proposals`** – Lists backlog tasks, proposals, and aggregated metrics from `DevAgentService`, providing velocity + rollout status for the developer console.【F:backend/app/main.py†L889-L910】【F:backend/app/services/dev_agent.py†L27-L160】
- **POST `/dev-agent/apply`** – Applies a proposal via sandbox execution, updates governance metadata, and returns execution transcripts alongside refreshed metrics.【F:backend/app/main.py†L912-L940】【F:backend/app/services/dev_agent.py†L107-L160】

### Billing & costs
- **GET `/billing/plans`** – Returns the static billing catalogue with generated timestamp for UI plan selectors.【F:backend/app/main.py†L943-L949】【F:backend/app/telemetry/billing.py†L1-L120】
- **GET `/billing/usage`** – Surfaces tenant health metrics for administrators via export functions in the billing telemetry module.【F:backend/app/main.py†L952-L960】【F:backend/app/telemetry/billing.py†L1-L120】
- **GET `/costs/summary`** – Summarises API/model/GPU spend over a sliding window using `CostTrackingService` aggregates.【F:backend/app/main.py†L964-L982】【F:backend/app/services/costs.py†L1-L198】
- **GET `/costs/events`** – Streams raw cost events with optional tenant/category filters backed by `CostStore` records.【F:backend/app/main.py†L984-L1014】【F:backend/app/services/costs.py†L80-L190】

### Onboarding funnel
- **POST `/onboarding`** – Records marketing/onboarding submissions, recommends a billing plan, and emits a signup billing event.【F:backend/app/main.py†L1017-L1060】【F:backend/app/telemetry/billing.py†L1-L120】

## GraphQL API
- `/graphql` is exposed over HTTP and WebSocket and currently implements the `timelineEvents` query, which proxies to `TimelineService.list_events` with identical filtering semantics.【F:backend/app/main.py†L139-L142】【F:backend/app/graphql/__init__.py†L1-L96】

## Storage & Background Components
- Voice sessions, agent threads, and developer backlog items are persisted under `AgentMemoryStore`, enabling cross-endpoint hydration of transcripts and governance history.【F:backend/app/main.py†L304-L343】【F:backend/app/services/voice/service.py†L205-L209】【F:backend/app/services/dev_agent.py†L40-L106】
- Ingestion relies on document, job, timeline, and forensics stores plus OCR, graph, and vector subsystems; connectors are registered via `LoaderRegistry` while the worker coordinates asynchronous execution.【F:backend/app/services/ingestion.py†L38-L82】
- Retrieval blends vector search, graph traversal, external case-law adapters, privilege enforcement, and streaming answer emission, all mediated by `HybridRetrievalBundle` adapters.【F:backend/app/main.py†L517-L597】【F:backend/app/services/retrieval.py†L20-L344】
- Timeline enrichment leverages graph metadata and maintains pagination cursors, ensuring consistent ordering for UI timeline widgets.【F:backend/app/services/timeline.py†L12-L140】

This map can be used as the source of truth when redesigning UI flows: each component section highlights the backing service, storage dependencies, and telemetry hooks the UI should continue to honour.
