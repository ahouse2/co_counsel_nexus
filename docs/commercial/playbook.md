# Commercial Launch Playbook

## 1. Packaging & Deployment Profiles
- **Tier catalogue** — Community, Professional, Enterprise. Each tier extends the base stack defined in `infra/docker-compose.yml` with optional observability (`otel-collector`) and Grafana dashboards (`infra/grafana/**`).
- **Environment manifests** — `infra/profiles/*.env` capture default settings for telemetry, billing plans, and Grafana credentials.
- **Installer automation** — run `scripts/install_tier.sh <tier>` to copy the tier manifest, create required storage directories (including `storage/billing`), and start the compose project with the relevant profile. Use `--dry-run` to preview commands during security review.

## 2. Pricing, Usage Limits & Support SLAs
| Plan | Monthly Price (USD) | Included Queries | Ingest Quota (GB) | Seats | Support Tier | SLA (hrs) | Overage (Query / GB) |
| ---- | ------------------- | ---------------- | ----------------- | ----- | ------------ | --------- | ------------------- |
| Community | 0 | 500 | 5 | 5 | Community | 48 | $0.02 / $3.00 |
| Professional | 3,499 | 5,000 | 60 | 25 | Standard | 12 | $0.015 / $2.40 |
| Enterprise | 8,999 | 20,000 | 250 | 100 | Premium | 2 | $0.010 / $1.60 |

Support contact paths: community — asynchronous email/forum, standard — Zendesk queue + scheduled reviews, premium — 24x7 hotline and Slack Connect. Health thresholds: soft alert at 80% quota consumption, hard alert at 95%.

## 3. Onboarding Workflow
1. **Intake form** — `frontend/src/components/OnboardingFlow.tsx` collects tenant, contact, use case, automation assumptions, and success criteria. Plans auto-recommend via shared heuristics with the API (`backend/app/main.py::_recommend_plan`).
2. **Submission API** — `POST /onboarding` persists metadata via `backend/app/telemetry/billing.py` (billing registry) and returns the recommended plan, timestamp, and tenant identifier.
3. **Commercial artefacts** — Submission metadata (departments, ROI assumptions, go-live date) is persisted in `storage/billing/usage.json` for playbook follow-up and ingestion into CRM.
4. **Success handoff** — The UI provides ROI projections and plan comparison to brief Customer Success prior to kickoff.

## 4. Customer Health & Telemetry
- **Instrumentation** — Billing events recorded for ingestion, query, timeline, agents, and onboarding flows (`backend/app/main.py`) with metrics exported via OpenTelemetry (`backend/app/telemetry/billing.py`).
- **Persistence** — Usage ledger stored at `storage/billing/usage.json` with thread-safe writes and per-tenant snapshots (health score, usage ratio, projected cost).
- **Dashboard** — `/billing/usage` exposes RBAC-protected JSON (role `CustomerSuccessManager`, scope `billing:read`). `frontend/src/components/CustomerHealthDashboard.tsx` visualises metrics with bearer-token input.
- **Grafana** — Enterprise profile ships with provisioned dashboards under `infra/grafana/dashboards/customer_health.json` pointing to the OTLP collector Prometheus endpoint.

## 5. Billing API Surface
- `GET /billing/plans` — returns plan catalogue (pricing, quotas, support tiers).
- `GET /billing/usage` — returns customer health snapshots (requires billing audience token).
- `POST /onboarding` — writes onboarding intake, triggers billing telemetry event (`BillingEventType.SIGNUP`).

## 6. Sales Enablement Collateral
- **Case studies** — see `docs/commercial/case_study_legal_ops.md` for a litigation ops success story with quantified outcomes.
- **ROI calculator methodology** — `docs/commercial/roi_calculator.md` documents formulae aligned with onboarding inputs and telemetry.
- **Battlecards & objections** — `docs/commercial/sales_enablement.md` summarises positioning, objection handling, and key differentiators for each tier.

## 7. Operational Routines
- **Daily** — review Grafana dashboard (Customer Intelligence folder), triage tenants flagged with health < 0.75 or usage ratio > 0.95.
- **Weekly** — sync billing ledger into CRM, align with Finance on projected overages, verify support SLA adherence via `support_response_sla_hours` counters.
- **Monthly** — audit `storage/billing/usage.json` for retention, export anonymised KPIs for exec reporting, reconcile plan overrides in environment config.

## 8. Change Management Checklist
- Update `infra/profiles/*.env` when adjusting plan defaults or telemetry endpoints.
- Keep billing plan constants in `backend/app/telemetry/billing.py` in sync with published pricing.
- Document any new collateral or tier adjustments under `docs/commercial/` and cross-link here.
- Append actions and validation results to `AGENTS.md` Chain of Stewardship after each commercial release.
