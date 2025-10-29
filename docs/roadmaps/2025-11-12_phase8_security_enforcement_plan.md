# Phase 8 — Security Enforcement Roadmap (2025-11-12)

## 0. Orientation
- ### 0.1 Mission
  - #### 0.1.1 Enforce mutual TLS for all protected endpoints using a central certificate registry and CA chain validation.
  - #### 0.1.2 Layer OAuth2 bearer verification with JWKS-backed signature checks and tenant-aligned claims.
  - #### 0.1.3 Apply RBAC/ABAC policies through Oso so that scopes + roles govern endpoint behaviour per PRP spec.
- ### 0.2 Inputs
  - #### 0.2.1 Specs: `PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_spec.md` §§APIs `/ingest`, `/query`, `/timeline`, `/graph`, `/forensics`.
  - #### 0.2.2 Validation backlog: `docs/validation/2025-11-07_prp_status_review_tasks.md` security items (mTLS, OAuth2, RBAC).
  - #### 0.2.3 Existing runtime: FastAPI app (`backend/app/main.py`), settings (`backend/app/config.py`), services/tests under `backend/`.

## 1. Certificate Trust & mTLS (Book → Chapter → Paragraph)
- ### 1.1 Config Surfaces
  - #### 1.1.1 Extend `Settings` with CA path, client registry path, certificate header names, and exempt path list.
  - #### 1.1.2 Ensure env var overrides exist (`SECURITY_MTLS_CA_PATH`, `SECURITY_MTLS_CLIENT_REGISTRY_PATH`, ...).
- ### 1.2 Middleware Implementation
  - #### 1.2.1 Create `security/mtls.py` defining `MTLSConfig`, `ClientIdentity`, and `MTLSMiddleware`.
    - ##### 1.2.1.1 Load CA cert + registry at startup; convert registry fingerprints into lookup map.
    - ##### 1.2.1.2 Parse base64-encoded PEM from header; validate signature (RSA PKCS#1 v1.5), issuer match, validity window.
    - ##### 1.2.1.3 Match fingerprint + subject to registry, populate `ClientIdentity` (client_id, tenant_id, roles) on `request.state`.
  - #### 1.2.2 Handle bypass paths (e.g., `/health`) while still supporting optional telemetry for audit events (log on denial).
- ### 1.3 Tests
  - #### 1.3.1 Author `test_security_mtls.py` generating CA/client certs at runtime, covering success + invalid signature + unknown fingerprint + expired cert cases.

## 2. OAuth2 Token Validation (Next Book)
- ### 2.1 JWKS Handling
  - #### 2.1.1 Add settings for JWKS file path, issuer, default leeway.
  - #### 2.1.2 Implement `OAuthValidator` (module `security/oauth.py`) to cache JWKS, resolve key by `kid`, and decode tokens per audience.
- ### 2.2 Claims Normalisation
  - #### 2.2.1 Produce `TokenClaims` dataclass capturing `sub`, `tenant_id`, `roles`, `scopes`, `case_admin`, `attributes`.
  - #### 2.2.2 Normalise `scope` (space-delimited -> set) and `roles` (array or comma string -> set).
- ### 2.3 Tests
  - #### 2.3.1 Extend security test suite to assert missing scope → 403, issuer/audience mismatch → 401/403, and tenant mismatch with certificate → 403.

## 3. Authorization via Oso (Another Book)
- ### 3.1 Policy & Types
  - #### 3.1.1 Create `security/authz.py` with `Principal`, `ResourceDescriptor`, `AuthorizationService` plus helper methods.
  - #### 3.1.2 Register classes with Oso and load `policy.polar` (include recursion helpers `has_all_scopes` / `has_any_role`).
  - #### 3.1.3 Ensure `policy.polar` enforces action match, scope inclusion, role intersection, and optional tenant equality.
- ### 3.2 FastAPI Integration
  - #### 3.2.1 Build dependency factory `require_authorization(action, audience, scopes, roles, *, attributes=None)` returning validated `Principal`.
  - #### 3.2.2 Inject dependency into each route (`/ingest`, `/ingest/{job_id}`, `/query`, `/timeline`, `/graph/neighbor`, `/forensics/*`, `/agents/*`).
  - #### 3.2.3 Enforce nuanced behaviour:
    - ##### 3.2.3.1 `/ingest/{job_id}` denies `ResearchAnalyst` until status `succeeded`.
    - ##### 3.2.3.2 `/query` redacts traces for `CaseCoordinator` lacking `query:trace` scope; denies `AutomationService` regardless of scopes.
    - ##### 3.2.3.3 `/forensics/*` require type-specific scope (document/image/financial) in addition to `forensics:read`.
- ### 3.3 Tests
  - #### 3.3.1 Add `test_security_roles.py` verifying role/scope combos (e.g., CaseCoordinator with missing scope fails, ResearchAnalyst + succeeded job passes, AutomationService denied).
  - #### 3.3.2 Update integration tests (`test_api.py`) to supply valid security headers/tokens and assert redaction behaviour.

## 4. Shared Test Fixtures & Utilities
- ### 4.1 Create `backend/tests/conftest.py`
  - #### 4.1.1 Provide `security_materials` fixture generating CA, client cert, JWKS, and helper `issue_token(scopes, roles, audience_override=None)`.
  - #### 4.1.2 Expose helper `auth_headers` merging cert + bearer token for requests.
- ### 4.2 Update existing fixtures to depend on security materials and reload settings/services accordingly.

## 5. Documentation & Stewardship
- ### 5.1 Update Validation Backlog
  - #### 5.1.1 Mark completed tasks in `docs/validation/2025-11-07_prp_status_review_tasks.md` with implementation notes/tests.
- ### 5.2 Task List Updates
  - #### 5.2.1 Reflect Phase 8 security milestone progress in `PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_tasks.md` and master task list if applicable.
- ### 5.3 Logs & Memory
  - #### 5.3.1 Append build log entry (`build_logs/2025-11-12.md`) capturing ACE cycle + tests.
  - #### 5.3.2 Record ACE state update in `memory/ace_state.jsonl` summarising retriever/planner/critic decisions.
  - #### 5.3.3 Extend `AGENTS.md` stewardship log with timestamp, files, tests, rubric assessment.

## 6. Validation & Release
- ### 6.1 Automated Verification
  - #### 6.1.1 Reinstall backend dependencies post-update (`pip install -r backend/requirements.txt`).
  - #### 6.1.2 Execute `pytest backend/tests -q` ensuring security suites and legacy regressions remain green.
- ### 6.2 PR Preparation
  - #### 6.2.1 Prepare PR summary referencing security enforcement + tests.
  - #### 6.2.2 Capture citations for modified files and test outputs.
