import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { OnboardingFlow } from '@/components/OnboardingFlow';

const mockPlans = {
  generated_at: new Date().toISOString(),
  plans: [
    {
      plan_id: 'community',
      label: 'Community',
      monthly_price_usd: 0,
      included_queries: 500,
      included_ingest_gb: 5,
      included_seats: 5,
      support_tier: 'Community',
      support_response_sla_hours: 48,
      support_contact: 'email',
      overage_per_query_usd: 0.02,
      overage_per_gb_usd: 3,
      onboarding_sla_hours: 72,
      description: 'Entry tier',
    },
    {
      plan_id: 'professional',
      label: 'Professional',
      monthly_price_usd: 3499,
      included_queries: 5000,
      included_ingest_gb: 60,
      included_seats: 25,
      support_tier: 'Standard',
      support_response_sla_hours: 12,
      support_contact: 'zendesk',
      overage_per_query_usd: 0.015,
      overage_per_gb_usd: 2.4,
      onboarding_sla_hours: 24,
      description: 'Production tier',
    },
    {
      plan_id: 'enterprise',
      label: 'Enterprise',
      monthly_price_usd: 8999,
      included_queries: 20000,
      included_ingest_gb: 250,
      included_seats: 100,
      support_tier: 'Premium',
      support_response_sla_hours: 2,
      support_contact: 'slack',
      overage_per_query_usd: 0.01,
      overage_per_gb_usd: 1.6,
      onboarding_sla_hours: 4,
      description: 'Global roll-out',
    },
  ],
};

vi.mock('@/utils/apiClient', () => ({
  fetchBillingPlans: vi.fn(async () => mockPlans),
  submitOnboarding: vi.fn(async () => ({
    tenant_id: 'tenant-x',
    recommended_plan: 'professional',
    message: 'Onboarding submission recorded',
    received_at: new Date().toISOString(),
  })),
}));

describe('OnboardingFlow', () => {
  it('walks through steps and submits onboarding payload', async () => {
    render(<OnboardingFlow />);

    await waitFor(() => expect(screen.getByText(/Plan comparison/)).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText(/Tenant ID/i), { target: { value: 'tenant-x' } });
    fireEvent.change(screen.getByLabelText(/Organisation/i), { target: { value: 'Acme Legal' } });
    fireEvent.change(screen.getByLabelText(/Primary contact name/i), { target: { value: 'Jane Counsel' } });
    fireEvent.change(screen.getByLabelText(/Primary contact email/i), { target: { value: 'jane@acme.com' } });
    fireEvent.change(screen.getByLabelText(/Seats required/i), { target: { value: 15 } });

    fireEvent.click(screen.getByRole('button', { name: /Next/i }));

    await waitFor(() => expect(screen.getByText(/Use case assumptions/i)).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText(/Primary use case/i), { target: { value: 'Investigations' } });
    fireEvent.change(screen.getByLabelText(/Matters per month/i), { target: { value: 30 } });
    fireEvent.click(screen.getByRole('button', { name: /Next/i }));

    await waitFor(() => expect(screen.getByText(/Commercial review/i)).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /Submit onboarding/i }));

    await waitFor(() => expect(screen.getByText(/Submission received/i)).toBeInTheDocument());
    expect(screen.getByText(/tenant-x/i)).toBeInTheDocument();
  });
});
