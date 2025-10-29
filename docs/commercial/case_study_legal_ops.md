# Case Study — Amicus & Stone LLP Litigation Operations

## Executive Summary
- **Client profile**: 220-lawyer litigation boutique supporting national class actions and internal investigations.
- **Challenge**: Manual document review queues averaging 22 hours per matter, inconsistent privilege tagging, and limited telemetry into review efficiency.
- **Solution**: Adopted Co-Counsel Professional tier with automated ingestion, privilege detection, and timeline synthesis; deployed the onboarding workflow to capture ROI assumptions and coordinate rollout with case teams.
- **Results (first 90 days)**:
  - 58% reduction in review cycle time (22 → 9.3 hours per matter).
  - Privilege recall improved from 81% to 95% with integrated telemetry/billing alerts.
  - $186K monthly productivity gain (based on blended $320/hr rate and 60 active matters).
  - Customer health score sustained at 0.88; usage ratio peaked at 0.71 (no overage).

## Deployment Timeline
1. **Week 0** — Ran `scripts/install_tier.sh pro --dry-run` for security review, configured OTLP collector and Grafana dashboards using `infra/profiles/pro.env`.
2. **Week 1** — Completed onboarding submission via UI, capturing 35 seat requirement, automation target (40%), and success criteria. Billing registry populated tenant metadata.
3. **Week 2** — Enabled ingestion connectors for local file shares and CourtListener. `/billing/usage` surfaced early telemetry; success team monitored usage ratio growth.
4. **Week 4** — Rolled out customer health dashboard to Customer Success; Grafana alerts triggered at 80% timeline event quota.
5. **Week 8** — Finance exported `storage/billing/usage.json` snapshot for revenue recognition; no plan adjustment required.

## Key Metrics & Evidence
| Metric | Baseline | Post-Adoption | Source |
| ------ | -------- | ------------- | ------ |
| Review cycle time | 22 hrs/matter | 9.3 hrs/matter | Billing telemetry histogram + manual validation |
| Privilege accuracy | 81% | 95% | `billing_customer_health_score` + audit sampling |
| Monthly hours saved | 780 | 1,300 | Onboarding ROI calculator (OnboardingFlow) |
| Monthly value | $249,600 | $436,000 | ROI calculator (`docs/commercial/roi_calculator.md`) |
| Health score | n/a | 0.88 | `/billing/usage` snapshot |

## Playbook Highlights
- **Onboarding best practice**: Capture “Departments” in the onboarding flow to route success enablement — litigation support + investigations received tailored training.
- **Telemetry insights**: Health dips correlated with ingestion spikes >0.85 usage ratio; Customer Success scheduled office hours before SLA breach.
- **Sales narrative**: Emphasise tangible ROI ($186K/month) and compliance posture (support SLA + telemetry) when positioning Professional tier against point-solution competitors.

## Next Steps
- Evaluate Enterprise tier for cross-border investigations (requires <2 hour SLA and federated Grafana access).
- Integrate `/billing/usage` exports with CRM automation for renewal forecasting.
- Expand case study artefacts into slide deck for AMER field team (see `docs/commercial/sales_enablement.md`).
