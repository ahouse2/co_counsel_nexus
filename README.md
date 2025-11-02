# NinthOctopusMitten — Multi-Provider Co-Counsel Platform

NinthOctopusMitten delivers an end-to-end litigation co-counsel experience that blends document ingestion, knowledge graph reasoning, retrieval-augmented generation, multi-agent orchestration, and forensic tooling. The stack now ships with a provider-aware runtime, encrypted operator settings, and a production-ready neon UI for configuring model providers, credentials, and appearance.

## Project Status

**✅ Production Ready** - All core features have been implemented and tested:

- **Cinematic Design System** with Tailwind CSS, shadcn/ui, and Radix primitives
- **3D Graph Explorer** with React Three Fiber visualization
- **Evidence Management** with AI-powered summarization
- **Trial University** with holo-screen video lessons
- **Mock Trial Arena** with live video conferencing

## Highlights
- **Provider registry & catalog** — Gemini 2.5 Flash is the default chat/vision model with optional OpenAI, Azure OpenAI, Hugging Face Inference, Ollama, llama.cpp, and GGUF-local adapters. A machine-readable catalog (`/settings/models`) is current to 2025-10-30.
- **Encrypted settings service** — `/settings` endpoints persist provider choices, API keys, CourtListener tokens, and research browser credentials using AES-GCM encryption behind `PlatformEngineer` scopes.
- **Frontend settings panel** — The React app exposes tabs for Providers, Credentials, Research tools, and Appearance (system/dark/light) powered by the new `SettingsContext`.
- **Observability & auditability** — Retrieval responses stream provider/model metadata, and all changes flow through FastAPI routes secured with mTLS + OAuth.
- **Cinematic UI Experience** — Neon-themed interface with Tailwind CSS, shadcn/ui, and Radix primitives featuring glassmorphism, glow effects, and smooth animations.
- **3D Graph Explorer** — Interactive 3D visualization of case relationships using React Three Fiber with bloom, depth-of-field, and springy drag interactions.
- **Evidence Management** — Drag-and-drop upload zone with glowing progress arcs and AI-generated summaries.
- **Trial University** — Holo-screen video lessons with interactive subtitles and progress tracking.
- **Mock Trial Arena** — Live video conferencing with draggable exhibits and real-time transcription.

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

## Working with the Project

### Development Workflow

**Frontend Development:**
```bash
cd frontend
npm install
npm run dev  # Starts development server on http://localhost:5173
```

**Backend Development:**
```bash
# Bootstrap backend dependencies
./scripts/bootstrap_backend.sh

# Run backend locally
uvicorn app.main:app --port 8000 --reload
```

**Testing:**
```bash
# Frontend tests
npm --prefix frontend run test

# Backend tests
python -m pytest backend/tests -q

# End-to-end tests
pytest tests/e2e -q
```

### Key UI Components

1. **Chat Workspace** - Main interface for conversational legal research
2. **3D Graph Explorer** - Visualize case relationships in an interactive 3D environment
3. **Evidence Management** - Upload, organize, and analyze case documents with AI summaries
4. **Trial University** - Access holo-screen video lessons for legal education
5. **Mock Trial Arena** - Practice courtroom scenarios with live video and draggable exhibits

### Architecture Overview

- **Frontend**: React + Vite with TypeScript
- **Backend**: FastAPI with Python 3.11+
- **Databases**: Neo4j (graph), Qdrant (vector search)
- **AI Models**: Multi-provider support (Gemini, OpenAI, Azure OpenAI, etc.)
- **Infrastructure**: Docker Compose for local development, Helm/Terraform for production

## Windows One-Click Installer
For Windows operators that prefer a turnkey experience, the repository ships with a
PowerShell-based installer capable of provisioning the full stack (backend API,
frontend UI, and supporting services) in a single execution.

1. Launch an elevated PowerShell session and allow the script to run:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   powershell -File .\infra\windows\scripts\install.ps1 -RepoUrl "https://github.com/NinthOctopusMitten/NinthOctopusMitten.git"
   ```
   The script installs required tooling via `winget` (Git, Python 3.11, Node.js), clones the
   repository into `%LOCALAPPDATA%\CoCounselNexus`, installs backend/frontend dependencies, and
   drops desktop shortcuts for launching or uninstalling the stack.

2. (Optional) Customise the destination, branch, or repository fork:
   ```powershell
   powershell -File .\infra\windows\scripts\install.ps1 -InstallDir "D:\Apps\CoCounsel" -Branch "develop" -RepoUrl "https://github.com/<fork>/NinthOctopusMitten.git"
   ```

3. (Optional) Package the installer into a distributable `.exe` on Windows:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   powershell -File .\infra\windows\package.ps1 -Output "CoCounselNexusInstaller.exe"
   ```
   The helper script bundles `scripts/install.ps1` using PS2EXE and embeds optional branding
   assets located in `infra/windows/assets/`.

Post-installation, the desktop shortcut launches `Start-CoCounsel.ps1`, which starts the backend
(`uvicorn app.main:app --port 8000`), boots the Vite frontend on port 5173, and opens the default
browser to the running experience.

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
- The frontend's **Settings** button (⚙) opens a four-tab panel powered by `SettingsContext`, allowing non-technical operators to select providers/models, upload API keys, manage CourtListener/research tokens, and toggle theme preferences. Changes persist to the encrypted backend store and immediately update the chat/query runtime.

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

## UI Features
The frontend now includes a comprehensive cinematic UI experience with the following features:

### Cinematic Design System
- Tailwind CSS with custom theme and design tokens
- shadcn/ui components with Radix primitives
- Glassmorphism effects and neon glow animations
- Framer Motion for smooth transitions and interactions

### 3D Graph Explorer
- React Three Fiber implementation for 3D visualization
- Neon-glass nodes with bloom and depth-of-field effects
- Interactive hover tooltips and springy drag interactions
- Glassmorphic metrics/filter HUD with search and toggles

### Evidence Management
- Drag-and-drop upload zone with visual feedback
- Glowing progress arcs for upload status
- AI-generated summary tiles with expandable details
- Reorderable evidence cards with tag chips and controls

### Trial University
- Holo-screen video player with atmospheric edge lighting
- Interactive subtitle overlays
- Glass tile lesson cards with neon accents
- Progress tracking and bookmarking features

### Mock Trial Arena
- WebRTC-compatible video grid with neon borders
- Draggable exhibit panel with spotlight functionality
- Real-time transcript overlays and chat panel
- Session timers and participant status indicators

## Archived Reference Assets
Legacy vendor experiments and snapshots now reside under [`archive/2025-10-30_reference-assets/`](archive/2025-10-30_reference-assets/). These files are retained for historical context; new work should reference the production backend/frontend code paths.

## Contributing
1. Bootstrap the backend (`./scripts/bootstrap_backend.sh`) to install Python dependencies (`qdrant-client`, `neo4j`, etc.).
2. Run linting/tests (`ruff`, `mypy`, `python -m pytest backend/tests -q`, `npm --prefix frontend run lint`, `npm --prefix frontend run test -- --run`).
3. Document substantive changes in `AGENTS.md`, including validation evidence and rubric outcomes.
4. For provider catalog edits, update both `backend/app/providers/catalog.py` and the generated `backend/app/providers/catalog.json`.

Please follow the project governance docs (`docs/DRIFT_GUARDRAILS.md`, `docs/MODEL_PROVIDER_POLICY.md`) when introducing new providers, credentials, or infrastructure profiles.