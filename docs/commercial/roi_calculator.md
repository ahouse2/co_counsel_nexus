# ROI Calculator Methodology

## Inputs (captured via Onboarding Flow)
- **Seats (`seats`)** — number of active knowledge workers using Co-Counsel.
- **Matters per month (`estimated_matters_per_month`)** — expected volume of litigation/investigation matters.
- **Baseline hours per matter (`roi_baseline_hours_per_matter`)** — historic manual effort per matter.
- **Automation target (`automation_target_percent`)** — percentage of baseline hours that Co-Counsel will automate.
- **Blended hourly rate (`hourly_rate`)** — user-specified in UI (default $285, adjustable).
- **Success criteria** — qualitative checkpoints used by Customer Success; not used in numeric calculations but logged in usage metadata.

## Core Formulae
1. **Monthly hours saved**
   ```
   hours_saved = estimated_matters_per_month * roi_baseline_hours_per_matter * automation_target_percent
   ```
2. **Annualised business value**
   ```
   annual_value = hours_saved * hourly_rate * 12
   ```
3. **Projected query volume (plan recommendation heuristic)**
   ```
   projected_queries = max(500, seats * max(5, estimated_matters_per_month) * max(0.1, automation_target_percent) * 4)
   ```
   Used by frontend/backend to map to the optimal plan tier.

## Alignment with Telemetry
- **Billing registry** persists the onboarding payload, storing ROI assumptions alongside usage telemetry.
- **Customer health dashboard** combines success rate, usage ratio, and health score to flag whether projected ROI is at risk.
- **Overage tracking** leverages `projected_monthly_cost` from `backend/app/telemetry/billing.py` to compare actual spend vs. projected value.

## Usage in Sales Motions
- Surface `annual_value` in discovery recaps and proposals.
- Compare `projected_queries` with plan quotas to explain tier recommendations.
- Use `hours_saved` as leading indicator in QBRs, cross-referenced with billing telemetry to prove adoption.

## Maintaining Accuracy
- Adjust default hourly rate in `frontend/src/components/OnboardingFlow.tsx` if pricing assumptions change.
- Keep recommendation heuristic in sync across frontend and backend (`_recommend_plan`).
- Review ROI assumptions quarterly with Customer Success; update onboarding form placeholders to reflect latest industry benchmarks.
