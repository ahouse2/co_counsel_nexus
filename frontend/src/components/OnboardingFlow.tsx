import { useEffect, useMemo, useState } from 'react';
import type {
  BillingPlan,
  OnboardingSubmissionPayload,
  OnboardingSubmissionResponse,
} from '@/types';
import { fetchBillingPlans, submitOnboarding } from '@/utils/apiClient';

const steps = ['Profile', 'Use Case', 'Review'];

interface FormState {
  tenant_id: string;
  organization: string;
  contact_name: string;
  contact_email: string;
  seats: number;
  primary_use_case: string;
  departmentsText: string;
  estimated_matters_per_month: number;
  roi_baseline_hours_per_matter: number;
  automation_target_percent: number;
  hourly_rate: number;
  go_live_date: string;
  notes: string;
  successCriteriaText: string;
}

function normaliseList(input: string): string[] {
  return input
    .split(/\r?\n|,/)
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0);
}

function recommendPlan(form: FormState, plans: BillingPlan[]): string {
  if (!plans.length) {
    return 'community';
  }
  const seats = form.seats;
  const matters = form.estimated_matters_per_month;
  const automation = Math.max(0.1, form.automation_target_percent);
  const projectedQueries = Math.max(500, seats * Math.max(5, matters) * automation * 4);
  const community = plans.find((plan) => plan.plan_id === 'community');
  const professional = plans.find((plan) => plan.plan_id === 'professional');
  if (community && seats <= community.included_seats && projectedQueries <= community.included_queries) {
    return 'community';
  }
  if (
    professional &&
    seats <= professional.included_seats + 15 &&
    projectedQueries <= professional.included_queries * 1.15
  ) {
    return 'professional';
  }
  return 'enterprise';
}

export function OnboardingFlow(): JSX.Element {
  const [plans, setPlans] = useState<BillingPlan[]>([]);
  const [loadingPlans, setLoadingPlans] = useState(true);
  const [planError, setPlanError] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<FormState>({
    tenant_id: '',
    organization: '',
    contact_name: '',
    contact_email: '',
    seats: 10,
    primary_use_case: '',
    departmentsText: '',
    estimated_matters_per_month: 25,
    roi_baseline_hours_per_matter: 6,
    automation_target_percent: 0.35,
    hourly_rate: 285,
    go_live_date: '',
    notes: '',
    successCriteriaText: '',
  });
  const [submission, setSubmission] = useState<OnboardingSubmissionResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadPlans(): Promise<void> {
      try {
        setLoadingPlans(true);
        setPlanError(null);
        const response = await fetchBillingPlans();
        if (!cancelled) {
          setPlans(response.plans);
        }
      } catch (error) {
        if (!cancelled) {
          setPlanError(error instanceof Error ? error.message : 'Failed to load pricing plans');
        }
      } finally {
        if (!cancelled) {
          setLoadingPlans(false);
        }
      }
    }
    loadPlans();
    return () => {
      cancelled = true;
    };
  }, []);

  const recommendation = useMemo(() => recommendPlan(form, plans), [form, plans]);

  const roi = useMemo(() => {
    const hoursSaved =
      form.estimated_matters_per_month * form.roi_baseline_hours_per_matter * form.automation_target_percent;
    const annualValue = hoursSaved * form.hourly_rate * 12;
    return {
      hoursSaved: Number.isFinite(hoursSaved) ? hoursSaved : 0,
      annualValue: Number.isFinite(annualValue) ? annualValue : 0,
    };
  }, [form]);

  const recommendedPlan = plans.find((plan) => plan.plan_id === recommendation);

  const canProceedStep = (currentStep: number): boolean => {
    if (currentStep === 0) {
      return (
        form.tenant_id.trim().length >= 3 &&
        form.organization.trim().length >= 3 &&
        form.contact_name.trim().length >= 3 &&
        form.contact_email.includes('@') &&
        form.seats > 0
      );
    }
    if (currentStep === 1) {
      return form.primary_use_case.trim().length > 3 && form.estimated_matters_per_month >= 0;
    }
    return true;
  };

  const handleChange = (field: keyof FormState, value: string | number): void => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = async (): Promise<void> => {
    setSubmitting(true);
    setSubmissionError(null);
    try {
      const payload: OnboardingSubmissionPayload = {
        tenant_id: form.tenant_id.trim(),
        organization: form.organization.trim(),
        contact_name: form.contact_name.trim(),
        contact_email: form.contact_email.trim(),
        seats: form.seats,
        primary_use_case: form.primary_use_case.trim(),
        departments: normaliseList(form.departmentsText),
        estimated_matters_per_month: form.estimated_matters_per_month,
        roi_baseline_hours_per_matter: form.roi_baseline_hours_per_matter,
        automation_target_percent: form.automation_target_percent,
        go_live_date: form.go_live_date ? new Date(form.go_live_date).toISOString() : null,
        notes: form.notes.trim() || null,
        success_criteria: normaliseList(form.successCriteriaText),
      };
      const response = await submitOnboarding(payload);
      setSubmission(response);
      setStep(2);
    } catch (error) {
      setSubmissionError(error instanceof Error ? error.message : 'Onboarding submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  const resetForm = (): void => {
    setSubmission(null);
    setSubmissionError(null);
    setForm({
      tenant_id: '',
      organization: '',
      contact_name: '',
      contact_email: '',
      seats: 10,
      primary_use_case: '',
      departmentsText: '',
      estimated_matters_per_month: 25,
      roi_baseline_hours_per_matter: 6,
      automation_target_percent: 0.35,
      hourly_rate: 285,
      go_live_date: '',
      notes: '',
      successCriteriaText: '',
    });
    setStep(0);
  };

  return (
    <div className="onboarding-flow" aria-live="polite">
      <header className="onboarding-header">
        <h2>Commercial Onboarding</h2>
        <p>
          Launch playbooks, assess ROI, and capture implementation details for every prospect. Plans auto-adapt based on the
          seats, matter volume, and automation targets you provide.
        </p>
      </header>

      <ol className="onboarding-steps" aria-label="Onboarding steps">
        {steps.map((label, index) => (
          <li key={label} data-active={index === step}>
            <span className="step-index">{index + 1}</span>
            <span>{label}</span>
          </li>
        ))}
      </ol>

      {planError && <div role="alert" className="onboarding-error">{planError}</div>}

      {submission ? (
        <section className="onboarding-review">
          <h3>Submission received</h3>
          <p>
            {submission.message} — recommended plan <strong>{submission.recommended_plan.toUpperCase()}</strong>.
          </p>
          <dl className="onboarding-summary">
            <div>
              <dt>Tenant</dt>
              <dd>{submission.tenant_id}</dd>
            </div>
            <div>
              <dt>Received at</dt>
              <dd>{new Date(submission.received_at).toLocaleString()}</dd>
            </div>
            {recommendedPlan && (
              <div>
                <dt>Plan price</dt>
                <dd>${recommendedPlan.monthly_price_usd.toLocaleString()} / month</dd>
              </div>
            )}
            <div>
              <dt>Projected annual value</dt>
              <dd>${roi.annualValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}</dd>
            </div>
          </dl>
          <div className="onboarding-actions">
            <button type="button" onClick={resetForm}>
              Capture another submission
            </button>
          </div>
        </section>
      ) : (
        <form
          className="onboarding-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (step < steps.length - 1) {
              setStep((current) => current + 1);
            } else {
              void handleSubmit();
            }
          }}
        >
          {step === 0 && (
            <section className="onboarding-panel">
              <h3>Organisation profile</h3>
              <div className="field-grid">
                <label>
                  Tenant ID
                  <input
                    type="text"
                    value={form.tenant_id}
                    onChange={(event) => handleChange('tenant_id', event.target.value)}
                    required
                  />
                </label>
                <label>
                  Organisation
                  <input
                    type="text"
                    value={form.organization}
                    onChange={(event) => handleChange('organization', event.target.value)}
                    required
                  />
                </label>
                <label>
                  Primary contact name
                  <input
                    type="text"
                    value={form.contact_name}
                    onChange={(event) => handleChange('contact_name', event.target.value)}
                    required
                  />
                </label>
                <label>
                  Primary contact email
                  <input
                    type="email"
                    value={form.contact_email}
                    onChange={(event) => handleChange('contact_email', event.target.value)}
                    required
                  />
                </label>
                <label>
                  Seats required
                  <input
                    type="number"
                    min={1}
                    value={form.seats}
                    onChange={(event) => handleChange('seats', Number(event.target.value))}
                    required
                  />
                </label>
                <label>
                  Target go-live
                  <input
                    type="date"
                    value={form.go_live_date}
                    onChange={(event) => handleChange('go_live_date', event.target.value)}
                  />
                </label>
              </div>
            </section>
          )}

          {step === 1 && (
            <section className="onboarding-panel">
              <h3>Use case assumptions</h3>
              <div className="field-grid">
                <label>
                  Primary use case
                  <input
                    type="text"
                    value={form.primary_use_case}
                    onChange={(event) => handleChange('primary_use_case', event.target.value)}
                    required
                  />
                </label>
                <label>
                  Departments (comma or newline separated)
                  <textarea
                    value={form.departmentsText}
                    onChange={(event) => handleChange('departmentsText', event.target.value)}
                    rows={3}
                    placeholder="Litigation, Investigations"
                  />
                </label>
                <label>
                  Matters per month
                  <input
                    type="number"
                    min={0}
                    value={form.estimated_matters_per_month}
                    onChange={(event) => handleChange('estimated_matters_per_month', Number(event.target.value))}
                  />
                </label>
                <label>
                  Baseline hours per matter
                  <input
                    type="number"
                    min={0}
                    value={form.roi_baseline_hours_per_matter}
                    onChange={(event) => handleChange('roi_baseline_hours_per_matter', Number(event.target.value))}
                  />
                </label>
                <label>
                  Automation target (%)
                  <input
                    type="number"
                    min={0}
                    max={1}
                    step={0.05}
                    value={form.automation_target_percent}
                    onChange={(event) => handleChange('automation_target_percent', Number(event.target.value))}
                  />
                </label>
                <label>
                  Blended hourly rate ($)
                  <input
                    type="number"
                    min={0}
                    value={form.hourly_rate}
                    onChange={(event) => handleChange('hourly_rate', Number(event.target.value))}
                  />
                </label>
                <label>
                  Success criteria (one per line)
                  <textarea
                    value={form.successCriteriaText}
                    onChange={(event) => handleChange('successCriteriaText', event.target.value)}
                    rows={4}
                    placeholder={'Reduce review turnaround time\nImprove privilege call accuracy'}
                  />
                </label>
                <label className="full-width">
                  Notes
                  <textarea
                    value={form.notes}
                    onChange={(event) => handleChange('notes', event.target.value)}
                    rows={4}
                    placeholder="Integration constraints, security considerations, or bespoke training data."
                  />
                </label>
              </div>
            </section>
          )}

          {step === 2 && (
            <section className="onboarding-panel">
              <h3>Commercial review</h3>
              <div className="review-grid">
                <article className="roi-card">
                  <h4>ROI projection</h4>
                  <p>
                    Estimated monthly hours saved: <strong>{roi.hoursSaved.toFixed(1)} hrs</strong>
                  </p>
                  <p>
                    Annualised business value: <strong>${roi.annualValue.toLocaleString()}</strong>
                  </p>
                  <p className="hint">
                    Adjust automation targets or hourly rate to explore upside. These metrics populate the commercial playbook
                    automatically.
                  </p>
                </article>
                <article className="plan-card" data-recommended>
                  <header>
                    <h4>Recommended plan</h4>
                    <span className="badge">{recommendation}</span>
                  </header>
                  {recommendedPlan ? (
                    <ul>
                      <li>
                        <strong>${recommendedPlan.monthly_price_usd.toLocaleString()}</strong> per month
                      </li>
                      <li>{recommendedPlan.included_queries.toLocaleString()} queries included</li>
                      <li>{recommendedPlan.included_ingest_gb} GB ingestion allocation</li>
                      <li>{recommendedPlan.included_seats} seats bundled</li>
                      <li>Support: {recommendedPlan.support_tier}</li>
                      <li>Onboarding SLA: {recommendedPlan.onboarding_sla_hours} hours</li>
                    </ul>
                  ) : (
                    <p>Loading plan recommendation…</p>
                  )}
                </article>
              </div>
              <p className="hint">
                When submitted, deployment engineering receives the seat counts, environments, and goals for this tenant. The
                billing ledger tracks quota consumption automatically.
              </p>
            </section>
          )}

          {submissionError && (
            <div role="alert" className="onboarding-error">
              {submissionError}
            </div>
          )}

          <div className="onboarding-actions">
            {step > 0 && (
              <button type="button" onClick={() => setStep((current) => current - 1)}>
                Back
              </button>
            )}
            <span className="spacer" />
            {step < steps.length - 1 ? (
              <button type="submit" disabled={!canProceedStep(step)}>
                Next
              </button>
            ) : (
              <button type="submit" disabled={submitting}>
                {submitting ? 'Submitting…' : 'Submit onboarding'}
              </button>
            )}
          </div>
        </form>
      )}

      <section className="plan-grid" aria-live="polite">
        <header>
          <h3>Plan comparison</h3>
          <p>
            {loadingPlans
              ? 'Loading plan catalogue…'
              : 'Contextual pricing ensures legal teams scale from proof-of-concept to enterprise roll-out with predictable economics.'}
          </p>
        </header>
        <div className="plan-grid-cards">
          {plans.map((plan) => (
            <article key={plan.plan_id} className="plan-card" data-highlight={plan.plan_id === recommendation}>
              <header>
                <h4>{plan.label}</h4>
                <span className="badge">{plan.plan_id}</span>
              </header>
              <p className="price">${plan.monthly_price_usd.toLocaleString()} / month</p>
              <ul>
                <li>{plan.included_queries.toLocaleString()} queries included</li>
                <li>{plan.included_ingest_gb} GB ingestion allowance</li>
                <li>{plan.included_seats} seats</li>
                <li>Support tier: {plan.support_tier}</li>
                <li>Response SLA: {plan.support_response_sla_hours}h</li>
                <li>Overage: ${plan.overage_per_query_usd} / query · ${plan.overage_per_gb_usd} / GB</li>
              </ul>
              <p className="description">{plan.description}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
