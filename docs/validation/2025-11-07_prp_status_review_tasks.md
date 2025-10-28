# Task List — Follow-ups from 2025-11-07 PRP Status Review

## Context
- Source: [PRP Status Review — Co-Counsel MVP (2025-11-07)](2025-11-07_prp_status_review.md)
- Purpose: Translate review recommendations into actionable engineering tasks with clear owners, dependencies, and validation steps.

## Security & Compliance
- [ ] **Mutual TLS Enforcement** — Terminate TLS certificates at FastAPI layer; validate client cert CN/SAN per tenant. *(Owners: Platform Security Guild)*
  - [ ] Implement ASGI middleware verifying client certs + mapping to tenant scopes. *(Code: `backend/app/main.py`, `backend/app/security/mtls.py`)*
  - [ ] Add integration tests simulating trusted/untrusted cert chains. *(Tests: `backend/tests/test_security_mtls.py`)*
- [ ] **OAuth2 + Oso RBAC Integration** — Enforce scopes and policies on `/ingest`, `/query`, `/agents/*`. *(Owners: Identity & Access Pod)*
  - [ ] Wire OAuth2 bearer validation with JWKS cache + signature checks. *(Code: `backend/app/security/oauth.py`)*
  - [ ] Configure Oso policies reflecting PRP role matrix; author regression tests for role coverage. *(Files: `backend/app/security/policy.polar`, `backend/tests/test_security_roles.py`)*
- [ ] **Audit & Break-Glass Logging** — Persist privileged access trails in tamper-evident store. *(Owners: Compliance Engineering)*
  - [ ] Emit structured audit events for every administrative override, including agent threads. *(Code: `backend/app/services/agents.py`, `backend/app/utils/audit.py`)*
  - [ ] Document retention + rotation policy in compliance runbook. *(Docs: `docs/compliance/audit_playbook.md`)*

## Testing & DevOps
- [ ] **Backend CI Workflow** — Add GitHub Actions pipeline covering lint, type-check, and full pytest suite. *(Owners: DevOps Enablement)*
  - [ ] Publish workflow file with caching for heavy deps (`pandas`, `scikit-learn`). *(File: `.github/workflows/backend_ci.yml`)*
  - [ ] Fail build on missing optional extras; upload coverage + artefacts. *(Tools: `coverage.xml`, `reports/pytest.html`)*
- [ ] **Dependency Bootstrap** — Provide deterministic installer for backend stack. *(Owners: Developer Productivity Guild)*
  - [ ] Author `uv.lock` or `poetry.lock` capturing pinned versions. *(File: `backend/uv.lock`)*
  - [ ] Update onboarding docs with setup instructions and smoke commands. *(Docs: `docs/ONBOARDING.md`)*

## Functional Coverage
- [x] **/query Enhancements** — Add pagination, filters, and rerank toggle per spec. *(Owners: Retrieval Engineering Pod — completed 2025-11-11; see backend/app/services/retrieval.py & backend/tests/test_api.py)*
  - [ ] Extend Pydantic models + service layer to accept pagination/filter args. *(Code: `backend/app/models/api.py`, `backend/app/services/retrieval.py`)*
  - [ ] Update FastAPI route + tests verifying behaviour. *(Files: `backend/app/main.py`, `backend/tests/test_api.py`)*
- [ ] **Remote Ingestion Connectors** — Implement SharePoint/S3/OneDrive connectors with credential registry integration. *(Owners: Data Pipelines Squad)*
  - [ ] Materialise connector classes with retries/backoff + secrets fetch. *(Code: `backend/app/services/ingestion_sources.py`)*
  - [ ] Add fixtures + tests covering remote ingestion flows. *(Files: `backend/tests/test_ingestion_connectors.py`)*

## Scalability & Observability
- [ ] **Background Ingestion Workers** — Move ingestion orchestration off request thread. *(Owners: Platform Core Guild)*
  - [ ] Introduce task queue abstraction (Celery/RQ) with idempotent job handling. *(Code: `backend/app/services/ingestion_worker.py`)*
  - [ ] Provide e2e test verifying async job lifecycle + status polling. *(Tests: `backend/tests/test_ingestion_async.py`)*
- [x] **Telemetry & Metrics Export** — Emit OpenTelemetry spans/metrics for retrieval + forensics pipelines. *(Owners: Observability Team)*
  - [x] Integrate OTLP exporter configuration + span instrumentation. *(Code: `backend/app/telemetry/__init__.py`)*
  - [x] Document dashboards + SLO probes in validation playbook. *(Docs: `docs/validation/nfr_validation_matrix.md`)*
  - [x] Stabilise instrumentation tests with recording stubs for spans/metrics. *(Tests: `backend/tests/test_telemetry.py`)*
