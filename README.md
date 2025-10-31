# NinthOctopusMitten — Multi-Provider Co-Counsel Platform

NinthOctopusMitten delivers an end-to-end litigation co-counsel experience that blends document ingestion, knowledge graph reasoning, retrieval-augmented generation, multi-agent orchestration, and forensic tooling. The stack now ships with a provider-aware runtime, encrypted operator settings, and a production-ready neon UI for configuring model providers, credentials, and appearance.

## Highlights
- **Provider registry & catalog** — Gemini 2.5 Flash is the default chat/vision model with optional OpenAI, Azure OpenAI, Hugging Face Inference, Ollama, llama.cpp, and GGUF-local adapters. A machine-readable catalog (`/settings/models`) is current to 2025-10-30.
- **Encrypted settings service** — `/settings` endpoints persist provider choices, API keys, CourtListener tokens, and research browser credentials using AES-GCM encryption behind `PlatformEngineer` scopes.
- **Frontend settings panel** — The React app exposes tabs for Providers, Credentials, Research tools, and Appearance (system/dark/light) powered by the new `SettingsContext`.
- **Observability & auditability** — Retrieval responses stream provider/model metadata, and all changes flow through FastAPI routes secured with mTLS + OAuth.
- **Deployment matrix** — Docker Compose, Helm, and Terraform overlays support community, pro, and enterprise profiles with optional GPU acceleration and cloud-native backups.

## Quick Start
1. **Install prerequisites**
   - Docker (Compose v2), Python 3.11+, Node.js 20+
   - Optional: [`uv`](https://github.com/astral-sh/uv) for Python dependency management

2. **Bootstrap with provider defaults**
   ```bash
   ./scripts/bootstrap_full_stack.sh \
     --profile community \
     --provider gemini \
     --secondary-provider openai \
     --model gemini-2.5-flash \
     --embedding-model text-embedding-004
   ```
   Add `--vision-model` to override the default vision model and `--with-gpu` when running on CUDA-enabled hosts.

3. **Launch the stack**
   ```bash
   docker compose --project-directory infra --env-file infra/profiles/community.env \
     --env-file infra/profiles/.runtime-provider.env up -d
   ```

4. **Access services**
   - Web UI / API: <http://localhost:8000>
   - Neo4j Browser: <http://localhost:7474>
   - Qdrant Console: <http://localhost:6333/dashboard>
   - Grafana (enterprise profile): <http://localhost:3000>

5. **Run validations**
   ```bash
   python -m pytest backend/tests -q
   npm --prefix frontend run lint
   npm --prefix frontend run test -- --run
   pytest tests/e2e -q           # optional full-stack smoke tests
   ```

## Configuring Providers & Credentials
### Backend environment
The API container honours the following environment variables (automatically populated by `bootstrap_full_stack.sh` and the Compose/Helm overlays):

| Setting | Description | Default |
| --- | --- | --- |
| `MODEL_PROVIDERS_PRIMARY` | Primary provider ID (`gemini`, `openai`, `huggingface`, `ollama`, etc.) | `gemini` |
| `MODEL_PROVIDERS_SECONDARY` | Optional fallback provider | `openai` |
| `DEFAULT_CHAT_MODEL` | Default chat/completions model ID | `gemini-2.5-flash` |
| `DEFAULT_EMBEDDING_MODEL` | Default embedding model ID | `text-embedding-004` |
| `DEFAULT_VISION_MODEL` | Default vision model ID | `gemini-2.5-flash` |

These values can be customised in:

- `infra/docker-compose.yml` via the environment block, or
- Helm overrides (`infra/helm/full-stack/values.yaml`), or
- `./scripts/bootstrap_full_stack.sh` flags (`--provider`, `--secondary-provider`, `--model`, `--embedding-model`, `--vision-model`).

### Settings API & panel
- `GET /settings` / `PUT /settings` surface encrypted state for providers, credentials, research tools, and appearance. Requests require the `settings:read` or `settings:write` scope and the `PlatformEngineer` role.
- `GET /settings/models` exposes the curated model catalog (provider IDs, capabilities, display names, context windows, availability).
- The frontend’s **Settings** button (⚙) opens a four-tab panel powered by `SettingsContext`, allowing non-technical operators to select providers/models, upload API keys, manage CourtListener/research tokens, and toggle theme preferences. Changes persist to the encrypted backend store and immediately update the chat/query runtime.

## Deployment Matrix
A detailed comparison of community vs. pro vs. enterprise capabilities—covering observability, backups, RBAC, and GPU profiles—is maintained in [`docs/roadmaps/2025-11-23_deployment_matrix.md`](docs/roadmaps/2025-11-23_deployment_matrix.md). Highlights:

| Capability | Community | Enterprise |
| --- | --- | --- |
| Runtime | Docker Compose (single node) | Helm chart with HPA |
| Observability | Optional OTLP | Required OTLP + Grafana |
| Backups | Local tar rotation | Terraform-managed S3 buckets |
| Secrets | `.env` profiles | AWS Secrets Manager |
| CI Coverage | Smoke tests | Compose + enterprise overlays |

### Docker Compose
- `infra/docker-compose.yml` builds the backend API locally, provisions Neo4j, Qdrant, Whisper (STT), Larynx (TTS), optional OTEL collector, and Grafana.
- Provider env overrides are injected through `infra/profiles/.runtime-provider.env` (auto-generated by the bootstrap script).
- Storage volumes live in `var/` with automated nightly backups via `storage-backup`.

### Helm & Terraform
- Helm chart (`infra/helm/full-stack`) mirrors the Compose topology with configurable PVCs, secret handling, CronJobs for backups, and optional GPU tolerations.
- Terraform module (`infra/terraform/modules/platform`) provisions S3 buckets, IAM roles, and Secrets Manager entries for production deployments. Example environment wiring is located under `infra/terraform/environments/enterprise`.

## Archived Reference Assets
Legacy vendor experiments and snapshots now reside under [`archive/2025-10-30_reference-assets/`](archive/2025-10-30_reference-assets/). These files are retained for historical context; new work should reference the production backend/frontend code paths.

## Contributing
1. Bootstrap the backend (`./scripts/bootstrap_backend.sh`) to install Python dependencies (`qdrant-client`, `neo4j`, etc.).
2. Run linting/tests (`ruff`, `mypy`, `python -m pytest backend/tests -q`, `npm --prefix frontend run lint`, `npm --prefix frontend run test -- --run`).
3. Document substantive changes in `AGENTS.md`, including validation evidence and rubric outcomes.
4. For provider catalog edits, update both `backend/app/providers/catalog.py` and the generated `backend/app/providers/catalog.json`.

Please follow the project governance docs (`docs/DRIFT_GUARDRAILS.md`, `docs/MODEL_PROVIDER_POLICY.md`) when introducing new providers, credentials, or infrastructure profiles.
