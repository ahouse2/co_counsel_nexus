# Provider Configuration & Settings Expansion Plan

## Baseline (2025-10-30)
- **Backend defaults:** `backend/app/config.py` hardcodes legacy OpenAI defaults; runtime services call OpenAI-centric factories and ignore the provider registry shipped in the repo.
- **Provider metadata:** `backend/app/providers/` includes `catalog.py` and `registry.py`, but only unit tests exercise them; Gemini remains a secondary adapter.
- **Credentials:** `backend/app/utils/credentials.py` is a read-only JSON loader; there is no encrypted persistence or API for provider keys, CourtListener tokens, or research browser credentials.
- **Frontend UX:** `frontend/src/components/RetrievalSettings.tsx` exposes only a precision/economy toggle with static OpenAI copy; there is no settings surface for provider selection, API keys, or theme preferences.
- **Deployment:** Scripts (`scripts/bootstrap_full_stack.sh`, `infra/docker-compose.yml`) lack provider/model parameters, local runtime toggles, and secret wiring for multiple vendors; CI/e2e suites exercise only the OpenAI path.
- **Documentation:** README and policy docs mention Gemini priority, but there is no user-facing guide for multi-provider configuration or settings management.

## Target Architecture
1. **Provider Registry Layer** – expand adapters covering Google Gemini (default), OpenAI, Azure OpenAI, Hugging Face, Ollama, Llama.cpp, and GGUF-local; ship a canonical catalog current to 2025-10-30 and expose it via `/settings/models`. Settings must persist primary/secondary providers, capability defaults, API bases, and local runtime paths.
2. **Runtime Integration** – route retrieval, agent orchestration, timeline, and ingestion services through the registry so provider selection and fallbacks honour governance policy and telemetry.
3. **Settings & Credential Persistence** – add an encrypted store plus `/settings` APIs for provider choices, API keys, CourtListener tokens, and research browser credentials with role-scoped security and validation.
4. **Frontend Settings Experience** – deliver a multi-tab settings panel (Providers, Credentials, Appearance, Research tools) backed by the new APIs and context, wiring chat/timeline clients to propagate provider metadata.
5. **Deployment & Tooling** – parameterise bootstrap scripts, Compose/Helm/Terraform overlays, and CI matrices to cover cloud + local providers (e.g., Gemini + Ollama).
6. **Documentation & UX Readiness** – rewrite README and governance docs with provider selection walkthroughs, settings panel instructions, deployment recipes, and troubleshooting for credentials/rate limits/offline fallbacks.

## Workstreams
1. Provider registry hardening (catalog refresh, config defaults, unit tests).
2. Runtime wiring for retrieval/agents/timeline, plus `/settings/models`.
3. Credential storage and `/settings` APIs with encrypted persistence and tests.
4. Frontend settings context/panel, provider-aware clients, and Vitest coverage.
5. Deployment/CI updates and repo cleanup (archive legacy assets).
6. Documentation refresh (README, governance links, screenshots/asciinema).

Each workstream gates on green backend/frontend/e2e suites with lint/type checks (`ruff`, `mypy`, `npm lint`). Feature flags protect incremental UI roll-out so production flows stay stable while multi-provider support lands.

## Risks & Mitigations
- **Provider drift:** enforce Gemini defaults via tests, emit telemetry on provider mix, and document override policy.
- **Credential leakage:** use envelope encryption with manifest key, redact secrets in responses/logs, and add regression tests for storage sanitisation.
- **UI regressions:** deliver settings panel under feature flag, keep current retrieval toggle until end-to-end testing passes, and expand Vitest coverage.
- **Deployment drift:** update bootstrap/infra assets with provider parameters and add CI profiles to exercise non-default providers.
