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

### Role Definitions & Authentication Stack
- **Authentication**: Agents communicate via mTLS (certs issued by LegalOps PKI) and exchange OAuth 2.0 workload tokens from the
  Platform Identity Service (`aud=co-counsel.agents`). Tokens expire after 5 minutes; rotation is orchestrated by the
  Coordinator agent.
- **Authorization Engine**: Oso policies embedded in the Orchestrator enforce RBAC + ABAC (attributes: `case_id`, `tenant_id`,
  `artifact_scope`, `run_id`). Break-glass tokens require `PlatformEngineer` approval and expire after 30 minutes.
- **Canonical Roles**:
  - `CaseCoordinator` — Owns orchestration decisions and can instruct all downstream agents.
  - `ResearchAnalyst` — Consumes query outputs, limited to read operations on Research and Timeline agents.
  - `ForensicsOperator` — Executes and reruns forensic tools.
  - `ComplianceAuditor` — Observes all agent transitions; read-only.
  - `PlatformEngineer` — Maintains infrastructure; may assume other roles under incident command.
  - `AutomationService` — Scheduled or CI-driven workflows with scoped permissions.
- **Audit Hooks**: Every cross-agent invocation emits `agent.authz` events with callsite span IDs and the resolved policy rule.

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
- **Security & Access Control**:
  - Authentication: Requires mTLS cert + OAuth token with `agents:coordinate` scope.
  - Role Matrix:

    | Role | Invoke Runs | Modify Policy Graph | Notes |
    | --- | --- | --- | --- |
    | `CaseCoordinator` | ✅ | ✅ | Default owning role; must attach `case_id` to each run. |
    | `PlatformEngineer` | ✅ (break-glass) | ✅ | Requires incident ticket; changes mirrored to audit queue. |
    | `ComplianceAuditor` | 🔍 Observe only | ❌ | Read-only; receives signed event stream. |
    | `AutomationService` | ✅ | ❌ | Limited to scheduled maintenance tasks enumerated in policy. |
    | `ResearchAnalyst` | ❌ | ❌ | Cannot orchestrate runs. |
    | `ForensicsOperator` | ❌ | ❌ | Access denied to avoid circular control. |

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
- **Security & Access Control**:
  - Authentication: Requires `agents:ingest` scope; connector plugins fetch credentials via signed short-lived tokens stored in
    Azure Key Vault access policies scoped to `CaseCoordinator` contexts.
  - Role Matrix:

    | Role | Launch Jobs | Override Credentials | Notes |
    | --- | --- | --- | --- |
    | `CaseCoordinator` | ✅ | ❌ | May enqueue ingestion per case manifest. |
    | `PlatformEngineer` | ✅ (break-glass) | ✅ | Overrides require change ticket + peer approval logged via audit sink. |
    | `AutomationService` | ✅ | ❌ | Limited to scheduled sync jobs defined in policy. |
    | `ForensicsOperator` | 🔍 Observe | ❌ | Can view status via telemetry only. |
    | `ComplianceAuditor` | 🔍 Observe | ❌ | Receives signed status stream; no execution rights. |
    | `ResearchAnalyst` | ❌ | ❌ | No ingestion permissions. |

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
- **Security & Access Control**:
  - Authentication: Requires `agents:graph` scope and ABAC attribute `ontology_version` matching manifest.
  - Role Matrix:

    | Role | Execute Upserts | Modify Ontology | Notes |
    | --- | --- | --- | --- |
    | `CaseCoordinator` | ✅ | ❌ | Runs upserts for orchestrated cases only. |
    | `PlatformEngineer` | ✅ (break-glass) | ✅ | Ontology mutations require dual approval (`PlatformEngineer` + `ComplianceAuditor`). |
    | `AutomationService` | ✅ | ❌ | Limited to nightly reconciliation jobs. |
    | `ResearchAnalyst` | 🔍 Observe | ❌ | Access limited to read-only trace metrics. |
    | `ForensicsOperator` | ❌ | ❌ | Not authorized to mutate graph. |
    | `ComplianceAuditor` | 🔍 Observe | ✅ (with ticket) | May view ontology diffs; modifications require change advisory board sign-off. |

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
- **Security & Access Control**:
  - Authentication: Requires `agents:research` scope; LLM provider calls use delegated signed JWT stored in Vault transit engine.
  - Role Matrix:

    | Role | Execute Queries | Adjust Guardrails | Notes |
    | --- | --- | --- | --- |
    | `ResearchAnalyst` | ✅ | 🔍 Propose only | Guardrail modifications require `PlatformEngineer` approval. |
    | `CaseCoordinator` | ✅ | ❌ | May replay queries for case wrap-ups. |
    | `ComplianceAuditor` | 🔍 Observe | ✅ (with ticket) | Can adjust guardrails during audit simulation windows. |
    | `PlatformEngineer` | ✅ | ✅ | Can hotfix guardrails; actions mirrored to audit log. |
    | `ForensicsOperator` | 🔍 Observe | ❌ | Access limited to queries referencing forensic signals. |
    | `AutomationService` | ❌ | ❌ | Automatic research invocations blocked. |

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
- **Security & Access Control**:
  - Authentication: Requires `agents:timeline` scope with ABAC `case_id` alignment.
  - Role Matrix:

    | Role | Build Timeline | Publish to Clients | Notes |
    | --- | --- | --- | --- |
    | `CaseCoordinator` | ✅ | ✅ | Controls publication windows and redaction filters. |
    | `ResearchAnalyst` | ✅ | 🔍 Review only | Can request edits but cannot publish. |
    | `ComplianceAuditor` | 🔍 Observe | ✅ (with ticket) | May publish redacted compliance views. |
    | `PlatformEngineer` | ✅ (break-glass) | ✅ | Publication requires incident justification. |
    | `ForensicsOperator` | 🔍 Observe | ❌ | Receives forensics-tagged timeline slices only. |
    | `AutomationService` | ✅ | ❌ | Generates scheduled exports to archives. |

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
- **Security & Access Control**:
  - Authentication: Requires `agents:forensics-document` scope with artifact-level ABAC on `artifact_scope` and `case_id`.
  - Role Matrix:

    | Role | Execute Analyzer | Approve Rerun | Notes |
    | --- | --- | --- | --- |
    | `ForensicsOperator` | ✅ | ✅ | Must log ticket ID for each rerun; evidence chain updated automatically. |
    | `CaseCoordinator` | ✅ (summary mode) | ❌ | Access restricted to review mode; no rerun authority. |
    | `ComplianceAuditor` | 🔍 Observe | ✅ (with ticket) | Reruns limited to audit verification. |
    | `PlatformEngineer` | ✅ (break-glass) | ✅ | Only during incident; actions mirrored to `forensics_chain.jsonl`. |
    | `ResearchAnalyst` | 🔍 Observe | ❌ | Read-only sanitized outputs. |
    | `AutomationService` | ❌ | ❌ | Automated reruns prohibited. |

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
- **Security & Access Control**:
  - Authentication: Requires `agents:forensics-image` scope; GPU scheduling honors `tenant_id` quotas enforced by Kubernetes
    PodSecurity policies.
  - Role Matrix:

    | Role | Execute Analyzer | GPU Override | Notes |
    | --- | --- | --- | --- |
    | `ForensicsOperator` | ✅ | ✅ | Overrides require `gpu_override` flag and approval from PlatformEngineer. |
    | `PlatformEngineer` | ✅ (break-glass) | ✅ | Incident-driven; logs include GPU pool + timebox. |
    | `ComplianceAuditor` | 🔍 Observe | ❌ | Can replay jobs against archived images without GPU override. |
    | `CaseCoordinator` | 🔍 Observe | ❌ | Receives summarized authenticity metrics. |
    | `ResearchAnalyst` | 🔍 Observe | ❌ | Access limited to sanitized EXIF and anomaly flags. |
    | `AutomationService` | ❌ | ❌ | Automated image forensics blocked. |

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
- **Security & Access Control**:
  - Authentication: Requires `agents:forensics-financial` scope; ABAC enforces `ledger_scope` and `jurisdiction` claims per
    compliance requirements.
  - Role Matrix:

    | Role | Execute Analyzer | Override Thresholds | Notes |
    | --- | --- | --- | --- |
    | `ForensicsOperator` | ✅ | ✅ | Overrides require documented rationale and ComplianceAuditor approval. |
    | `ComplianceAuditor` | 🔍 Observe | ✅ (with ticket) | Adjustments limited to audit simulations with rollback plan. |
    | `CaseCoordinator` | 🔍 Observe | ❌ | Receives summary anomalies only. |
    | `PlatformEngineer` | ✅ (break-glass) | ✅ | For emergency remediation; logs include incident ID. |
    | `ResearchAnalyst` | 🔍 Observe | ❌ | Access sanitized to aggregated metrics. |
    | `AutomationService` | ❌ | ❌ | Automated ledger analysis disabled pending risk review. |

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

### Tool Access Controls
| Tool | Authentication Mechanism | Authorized Roles | Notes |
| --- | --- | --- | --- |
| LlamaHub Loaders (SharePoint/OneDrive/S3/etc.) | mTLS + short-lived Azure AD workload tokens scoped to connector; secrets pulled from Key Vault | `CaseCoordinator`, `PlatformEngineer`, `AutomationService` | Operators require `ingest:connector` scope; actions logged per connector. |
| OCR (Tesseract wrapper) | Signed job token issued by IngestionAgent with `ocr:run` claim | `IngestionAgent`, `PlatformEngineer` | PlatformEngineer access restricted to diagnostics mode. |
| Embeddings (HF BGE small) | API key stored in Vault Transit; delegated via `research:embed` scope | `ResearchAgent`, `PlatformEngineer` | PlatformEngineer use requires incident justification. |
| Vector Stores (Qdrant/Chroma) | gRPC mTLS cert pinned to `co-counsel-vector` role; OAuth optional for hosted variant | `IngestionAgent`, `ResearchAgent`, `PlatformEngineer` | Write permissions limited to ingestion contexts. |
| Graph Store (Neo4j) | Bolt+TLS with client cert; OAuth bearer for Aura fallback | `GraphBuilderAgent`, `PlatformEngineer`, `ComplianceAuditor` (read) | `ComplianceAuditor` read tokens minted with `graph:readonly`. |
| Case Law Adapters | HTTPS signed requests with API-specific keys stored in Vault | `ResearchAgent`, `AutomationService` (throttled) | Usage capped at 30 RPM per principal; compliance monitors provider terms. |
| Security — Redaction & Privilege Detector | Local execution with signed WASM modules validated via SHA-256 | `ResearchAgent`, `ComplianceAuditor` | Privilege detector emits `privilege.alert` events consumed by compliance checklist. |
| Forensics Core Tooling | mTLS + signed artifact manifest; requires `forensics:tool` scope | `DocumentForensicsAgent`, `ImageForensicsAgent`, `FinancialForensicsAgent`, `PlatformEngineer` | PlatformEngineer limited to maintenance windows; actions appended to chain-of-custody ledger. |

Notes
- Source references under `agents and tools/` (autogen, prior agents); integrate incrementally.
- Every tool must define schema, security scope, observability fields, retry envelope, and test strategy.
