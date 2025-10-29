# NinthOctopusMitten — Full-Stack Co-Counsel Platform

NinthOctopusMitten delivers an end-to-end research and co-counsel workflow that blends document ingestion, graph reasoning, retrieval, multi-agent orchestration, and forensic analysis. This repository packages the full stack required for community evaluations through enterprise deployments with GPU-accelerated audio services, observability, and disaster recovery controls.

## Quick Start
1. **Install prerequisites** — Docker (with Compose v2), Python 3.11+, Node.js 20+, and optional `uv` for dependency management.
2. **Bootstrap the stack**
   ```bash
   ./scripts/bootstrap_full_stack.sh --profile community
   docker compose --project-directory infra --env-file infra/profiles/community.env up -d
   ```
   *GPU acceleration?* Append `--with-gpu` and include `--env-file infra/profiles/gpu.env` when starting Compose to request CUDA devices.
3. **Run smoke tests** — validate the platform end to end.
   ```bash
   pytest tests/e2e -q
   npm --prefix frontend run test -- --run
   ```
4. **Access services**
   - API: http://localhost:8000
   - Neo4j Browser: http://localhost:7474
   - Qdrant Console: http://localhost:6333/dashboard
   - Grafana (enterprise profile): http://localhost:3000

## Deployment Matrix
A detailed capability comparison between community and enterprise tiers lives in [`docs/roadmaps/2025-11-23_deployment_matrix.md`](docs/roadmaps/2025-11-23_deployment_matrix.md). The table below highlights key differences:

| Capability | Community | Enterprise |
| --- | --- | --- |
| Core API + services | Docker Compose, single instance | Helm chart with horizontal scaling |
| Audio (STT/TTS) | CPU profiles with local caches | GPU-optional deployments with node selectors |
| Observability | Optional OTLP collector | Mandatory OTLP + Grafana dashboards |
| Backups | Local tarball rotation via Compose + script | Terraform-provisioned S3 buckets with lifecycle policies |
| Secrets | `.env` profiles | AWS Secrets Manager via Terraform module |

## Infrastructure Layout
- **Docker Compose** (`infra/docker-compose.yml`)
  - API, Neo4j, Qdrant, OTEL collector, Grafana, Whisper (STT), and Larynx (TTS) services.
  - Model caches and storage volumes mounted under `var/` with automated backups using `ghcr.io/offen/docker-volume-backup`.
  - Optional GPU profiles exposed via Compose `profiles` for accelerated inference.
- **Helm Chart** (`infra/helm/full-stack`)
  - Deploys the complete stack with RBAC, Secrets, PVCs, configurable storage classes, and CronJobs for backups.
  - Values overlays provided for community and enterprise tiers, including GPU tolerations and telemetry settings.
- **Terraform Module** (`infra/terraform/modules/platform`)
  - Provisions AWS S3 buckets (documents/graphs/telemetry) with lifecycle + versioning, Secrets Manager entries, and IAM roles for Kubernetes service accounts.
  - Example environment wiring under `infra/terraform/environments/enterprise`.

## Operations Tooling
- `scripts/bootstrap_full_stack.sh` orchestrates environment setup, Hugging Face model downloads, Docker Compose bring-up, and datastore migrations.
- `scripts/backup_storage.sh` performs manual backups with retention aligned to Compose defaults, enabling on-demand disaster recovery validation.
- CI workflow `.github/workflows/full_stack_e2e.yml` spins up the Compose stack, runs API smoke tests, and executes frontend Vitest suites for regression coverage.

## Backup & Retention
Storage directories reside in `var/storage/{documents,graphs,telemetry}`. Nightly backups are executed by the Compose `storage-backup` service and can be triggered manually:
```bash
./scripts/backup_storage.sh --retention-days 7
```
Backups are written to `var/backups/` with timestamped archives and pruned according to the configured retention policy.

## Contributing
1. Run `./scripts/bootstrap_backend.sh` to prepare the Python environment when extending backend services.
2. Ensure linting and tests pass (`ruff`, `mypy`, `pytest`, `npm run test`).
3. Append an entry to the stewardship log in `AGENTS.md` summarizing your changes, validations, and rubric outcomes.

For roadmap visibility across active initiatives, consult the documents in [`docs/roadmaps/`](docs/roadmaps/).
