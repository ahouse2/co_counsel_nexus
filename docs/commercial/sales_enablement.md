# Sales Enablement Cheat Sheet

## Positioning Statements
- **Community** — Rapid evaluation for litigation teams exploring AI-assisted review; emphasise zero-cost entry with full provenance tracking.
- **Professional** — Production-ready deployment with telemetry, premium connectors, and success program; highlight 58% cycle-time reductions (see `case_study_legal_ops.md`).
- **Enterprise** — Global compliance, 24x7 support, Grafana dashboards; focus on security posture (mTLS, OAuth, audit ledger) and executive reporting.

## Discovery Questions
1. How many matters per month require document review or investigations?
2. What is the baseline review time and team composition (seats)?
3. Which departments must be involved in rollout (Litigation, Investigations, Compliance)?
4. What support expectations or SLAs are mandated by procurement?
5. How is success measured (hours saved, privilege accuracy, turnaround time)?

## Objection Handling
| Objection | Recommended Response |
| --------- | -------------------- |
| "We already have review tooling." | Differentiate with integrated telemetry + billing dashboard, automated privilege detector, and Graph timeline context. |
| "Telemetry is optional in regulated environments." | Community tier ships without OTLP; pro/enterprise use OTLP with configurable endpoints and storage under customer control. |
| "Budget uncertainty." | Leverage ROI calculator (`roi_calculator.md`) to tie automation targets to projected monthly value; highlight overage controls via customer health dashboard. |

## Key Collateral
- Demo the onboarding flow (`frontend/src/components/OnboardingFlow.tsx`) to capture ROI live during discovery.
- Share Grafana customer health snapshots for transparency in renewals.
- Provide the case study PDF derived from `case_study_legal_ops.md` for proof points.

## Operational Hooks
- Coordinate with Customer Success using `/billing/usage` exports for renewal forecasting.
- Align Finance on projected overages using `projected_monthly_cost` telemetry.
- Update this cheat sheet as new collateral or plan adjustments are shipped (append change log below).

### Change Log
- 2025-11-18 — Initial enablement package delivered with tier packaging, onboarding flow, and dashboards.
