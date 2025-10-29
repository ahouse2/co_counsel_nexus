# Full-Stack Deployment Enablement Plan — 2025-11-23

## Phase 0 — Context Alignment
- **Objective**: establish shared understanding of platform scope and deployment expectations before implementation begins.
  - Document baseline runtime topology for API, data stores, telemetry, and new audio services.
  - Confirm storage domains requiring rotation (documents, graphs, telemetry) and associated RPO/RTO targets.
  - Catalogue environment tiers (community, pro, enterprise) and GPU acceleration permutations to drive configuration matrices.

## Phase 1 — Local Orchestration Enhancements
- **1.1 Docker Compose Extensions**
  - Add speech-to-text (Whisper/faster-whisper) and text-to-speech (Larynx) services with configurable model caches.
  - Introduce dedicated volumes for documents/graphs/telemetry storage and Hugging Face model snapshots.
  - Embed optional GPU profiles using `deploy.resources`/`device_requests` anchors for containers that can leverage CUDA.
  - Configure scheduled volume backups with rotation policy targeting the three storage domains.
- **1.2 Environment Profiles**
  - Expand `infra/profiles/*.env` to surface audio endpoints, cache paths, and backup tunables per tier.
  - Ensure secrets may be overridden via user-provided environment variables without modifying committed files.

## Phase 2 — Bootstrap & Operational Tooling
- **2.1 Full-Stack Bootstrap Script**
  - Compose environment selection logic, `.env` generation, directory scaffolding, and optional Hugging Face downloads.
  - Reuse backend bootstrap to guarantee Python dependencies before running migrations or health probes.
  - Automate Neo4j and Qdrant migrations after containers become healthy.
- **2.2 Backup Tooling**
  - Provide manual backup script with retention policy aligned to Compose service defaults for parity between CI and operators.

## Phase 3 — Enterprise Deployment Artefacts
- **3.1 Helm Chart**
  - Scaffold chart packaging API, data stores, audio services, RBAC/ServiceAccount, Secrets, and PVC definitions.
  - Surface values overrides for GPU enablement, storage class selection, Grafana/OTel toggles, and backup CronJobs.
- **3.2 Terraform Module**
  - Deliver AWS-oriented module provisioning S3 buckets with lifecycle policies, Secrets Manager entries, and IAM roles for workload identities.
  - Provide environment wiring example (enterprise) referencing module outputs for Helm/Argo CD pipelines.

## Phase 4 — Continuous Verification
- **4.1 End-to-End Smoke Tests**
  - Author pytest-based API smoke hitting `/health` plus dependency probes.
  - Add GitHub Actions workflow that composes stack, runs API smoke, executes frontend Vitest suite, and tears down reliably.
- **4.2 Documentation Updates**
  - Refresh README with professional overview, quickstart, deployment matrix summary, and references to new tooling.
  - Author roadmap deployment matrix detailing feature coverage per tier (community vs enterprise).

## Phase 5 — Governance & Stewardship
- **5.1 Chain-of-Stewardship Entry**
  - Append AGENTS.md log entry capturing scope, validation, and rubric targeting ≥9 across categories.
- **5.2 Follow-up Signals**
  - Note future enhancements (e.g., secret rotation automation, GPU benchmarking) for subsequent iterations.
