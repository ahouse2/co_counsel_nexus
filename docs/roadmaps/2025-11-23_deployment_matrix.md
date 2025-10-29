# Deployment Matrix — Community vs Enterprise

| Capability | Community | Enterprise |
| --- | --- | --- |
| API, Retrieval, Graph services | ✅ Single-node Docker Compose | ✅ Helm-managed replicas with HPA |
| Neo4j graph store | ✅ Ephemeral volume | ✅ StatefulSet with dedicated PVC & backups |
| Qdrant vector store | ✅ Local volume | ✅ Dedicated PVC + lifecycle policies |
| Speech-to-text (Whisper) | ✅ CPU-only container | ✅ GPU-optional deployment |
| Text-to-speech (Larynx) | ✅ CPU-only container | ✅ GPU-optional deployment |
| Telemetry (OTel + Grafana) | Optional | ✅ Required with dashboards |
| Backup & retention | Local tarball rotation | S3 versioned buckets (Terraform) |
| Secrets management | `.env` profiles | AWS Secrets Manager (Terraform output) |
| RBAC | Local API roles | Kubernetes RBAC (Helm templates) |
| CI coverage | Smoke tests | Smoke + enterprise overrides (values-enterprise) |

## Environment Profiles Overview
- **Community** — lowest resource footprint, ideal for evaluation and feature demos.
- **Pro** — extends community with telemetry; optional GPU acceleration toggles.
- **Enterprise** — production-grade, includes Grafana dashboards, enforced telemetry, cloud backups, and Terraform-provisioned storage.

## Next Steps
1. Use `scripts/bootstrap_full_stack.sh --profile community` for local bring-up.
2. For enterprise deployments, apply Terraform module outputs as Helm values overrides and configure backup credentials.
3. Keep Grafana admin credentials rotated via Secrets Manager integrations.
