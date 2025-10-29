import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

import { CustomerHealthDashboard } from '@/components/CustomerHealthDashboard';

const mockUsage = {
  generated_at: new Date().toISOString(),
  tenants: [
    {
      tenant_id: 'tenant-a',
      plan_id: 'community',
      plan_label: 'Community',
      support_tier: 'Community',
      support_sla_hours: 48,
      support_channel: 'email',
      total_events: 10,
      success_rate: 0.9,
      usage_ratio: 0.45,
      health_score: 0.92,
      ingestion_jobs: 3,
      ingestion_gb: 1.2,
      query_count: 9,
      average_query_latency_ms: 420,
      timeline_requests: 4,
      agent_runs: 1,
      projected_monthly_cost: 0,
      seats_requested: 5,
      onboarding_completed: true,
      last_event_at: new Date().toISOString(),
      metadata: {},
    },
    {
      tenant_id: 'tenant-b',
      plan_id: 'professional',
      plan_label: 'Professional',
      support_tier: 'Standard',
      support_sla_hours: 12,
      support_channel: 'zendesk',
      total_events: 200,
      success_rate: 0.62,
      usage_ratio: 0.97,
      health_score: 0.58,
      ingestion_jobs: 35,
      ingestion_gb: 45,
      query_count: 180,
      average_query_latency_ms: 380,
      timeline_requests: 60,
      agent_runs: 12,
      projected_monthly_cost: 4200,
      seats_requested: 40,
      onboarding_completed: true,
      last_event_at: new Date().toISOString(),
      metadata: {},
    },
  ],
};

vi.mock('@/utils/apiClient', () => ({
  fetchBillingUsage: vi.fn(async () => mockUsage),
}));

describe('CustomerHealthDashboard', () => {
  it('renders health summary and highlights at-risk tenants', async () => {
    render(<CustomerHealthDashboard />);

    await waitFor(() => expect(screen.getByText(/Customer Health/)).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText(/tenant-b/)).toBeInTheDocument());

    expect(screen.getByText(/At-risk tenants/i)).toBeInTheDocument();
    const riskCell = screen.getByText(/tenant-b/i);
    const riskRow = riskCell.closest('tr');
    expect(riskRow).not.toBeNull();
    expect(riskRow).toHaveAttribute('data-health', 'at-risk');
  });
});
