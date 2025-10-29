# Commercial Enablement Rollout Plan — 2025-11-18

## Phase A — Packaging & Deployment Profiles
- ### A1 — Asset audit & prerequisites
  - Enumerate existing infra artifacts (docker-compose base file, bootstrap scripts).
  - Identify environment variables required for billing, telemetry, and customer success services.
- ### A2 — Tiered configuration architecture
  - Define community/pro/enterprise tiers with shared base compose file + override profiles.
  - Materialise environment manifests per tier capturing secrets, limits, feature flags.
- ### A3 — Installer automation
  - Implement `scripts/install_tier.sh` orchestrating env templating, directory prep, and compose profile selection.
  - Provide inline validation + dry-run preview for security review.
- ### A4 — Documentation integration
  - Update `docs/ROADMAP.md` to anchor packaging milestone to tiered deployment.
  - Draft commercial playbook referencing compose profiles and installer usage.

## Phase B — Billing Plans, Usage Limits & Telemetry
- ### B1 — Pricing model definition
  - Encode plan metadata (price, quotas, support tier, overages) in strongly typed models under telemetry/billing.
  - Extend settings for plan selection overrides and usage persistence path.
- ### B2 — Usage instrumentation
  - Create `backend/app/telemetry/billing.py` capturing ingestion/query/timeline/sign-up events with OpenTelemetry counters & histograms.
  - Persist per-tenant usage snapshots for dashboards and alert thresholds.
- ### B3 — API surface for commercial data
  - Add billing endpoints for plan catalogue and customer health dashboards with RBAC guardrail.
  - Introduce onboarding submission endpoint writing into usage ledger.
- ### B4 — Automated verification
  - Add focused unit tests covering plan resolution, usage accumulation, and API contract responses.

## Phase C — Frontend Onboarding & Customer Success Experience
- ### C1 — API client expansion
  - Implement typed fetch helpers for billing plans, usage dashboard, and onboarding submission.
- ### C2 — UI architecture
  - Add navigation sections for onboarding and customer success dashboards while preserving existing workspace.
  - Compose reusable components: plan selector, ROI estimator, health score visualisations.
- ### C3 — State management & flows
  - Build multi-step onboarding wizard with validation, success states, and telemetry submission.
  - Render customer health metrics using accessible tables/cards with auto-refresh.
- ### C4 — Frontend regression coverage
  - Author component tests verifying rendering, interaction, and API wiring for new flows.

## Phase D — Commercial Collateral & Documentation
- ### D1 — Commercial playbook structure
  - Create `docs/commercial/playbook.md` detailing GTM motions, tier positioning, and lifecycle checkpoints.
- ### D2 — Marketing & sales enablement assets
  - Draft case studies, ROI calculator methodology, objection handling one-pager.
- ### D3 — Documentation cross-linking
  - Embed references in roadmap and playbook for deployment scripts, billing dashboards, and onboarding flow.
  - Ensure citations align with stewardship log requirements.

## Phase E — Stewardship & Quality Gates
- ### E1 — Chain of stewardship update post-implementation.
- ### E2 — Execute backend + frontend test suites; capture telemetry/billing specific tests.
- ### E3 — Run lint/type-check as needed to preserve CI parity.
