# 2025-10-30 Co-Counsel Auth & Compliance Extension Plan

## Phase I — Context Assimilation
- ### Objective A — Enumerate Integration Targets
  - #### Step 1 — Catalogue External-Facing HTTP APIs
    - ##### Task a — Inspect existing Co-Counsel PRP for `/ingest`, `/ingest/{job_id}`, `/query`, `/timeline`, `/forensics`, `/cases`, `/runs` endpoints.
    - ##### Task b — Map future endpoints tagged as "planned" to ensure forward-compatible matrices.
  - #### Step 2 — Catalogue Agent Tools & Interfaces
    - ##### Task a — Cross-reference Agent & Tool Registry entries for execution pathways.
    - ##### Task b — Align connectors (SharePoint, S3, OCR, Graph, Vector, Forensics) with principle-of-least-privilege posture.
- ### Objective B — Harvest Existing Security Guarantees
  - #### Step 1 — Extract baseline policies (encryption, retention, audit) from repo (PRPs, validation playbooks).
  - #### Step 2 — Note missing owner assignments and verification touchpoints for each policy.

## Phase II — Access Control Architecture
- ### Objective A — Define Authentication Schemes per Interface
  - #### Step 1 — Select primary credential models (Mutual TLS + OAuth2 service principals; short-lived workload identities).
  - #### Step 2 — Describe token audiences, issuance authorities, and rotation cadences tailored to API clusters.
- ### Objective B — Author Authorization Matrices
  - #### Step 1 — Establish canonical roles (CaseCoordinator, ResearchAnalyst, ForensicsOperator, ComplianceAuditor, PlatformEngineer).
  - #### Step 2 — Produce CRUD/verb matrix per API and agent tool; capture approval and emergency elevation flows.
  - #### Step 3 — Capture telemetry correlation IDs required for tamper-evident auditability.

## Phase III — Operational Safeguards
- ### Objective A — Secrets & Key Management Blueprint
  - #### Step 1 — Assign vault paths, access tiers, rotation SLAs, and owners for ingestion connectors, LLM providers, and forensic GPUs.
  - #### Step 2 — Codify encryption-in-transit/at-rest requirements (TLS 1.3, envelope encryption with KMS, field-level crypto for PII).
- ### Objective B — Data Lifecycle Controls
  - #### Step 1 — Document retention timelines per artifact class (raw ingest, embeddings, graph, audit logs) with purge verification scripts.
  - #### Step 2 — Bind each retention routine to implementation owners and acceptance criteria.
- ### Objective C — Audit Logging & Evidence Chain
  - #### Step 1 — Define minimal log fields for privilege detection and chain-of-custody attestations.
  - #### Step 2 — Draft compliance checklists with measurable verification (queries, dashboards, automated tests) and owners.

## Phase IV — Documentation Integration
- ### Objective A — Update Co-Counsel PRP Spec
  - #### Step 1 — Insert authentication/authorization tables within API sections.
  - #### Step 2 — Add security governance chapter covering secrets, encryption, retention, audit logging, and compliance checklists.
- ### Objective B — Update Agent & Tool Registry
  - #### Step 1 — Embed per-agent access control blocks with credential requirements and role gating.
  - #### Step 2 — Attach tool-level role matrices and security requirements.

## Phase V — Verification & Sign-off
- ### Objective A — Cross-Document Consistency Review
  - #### Step 1 — Ensure roles/owners identical across PRP and registry.
  - #### Step 2 — Validate terminology alignment with existing validation playbooks.
- ### Objective B — Repository Stewardship Updates
  - #### Step 1 — Append Chain of Stewardship entry with test evidence.
  - #### Step 2 — Stage, lint (markdown link/style), and commit.
  - #### Step 3 — Prepare PR summary referencing authentication, authorization, and compliance enhancements.
