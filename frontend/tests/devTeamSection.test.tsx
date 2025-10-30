import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DevTeamSection } from '@/components/dev-team/DevTeamSection';
import { SandboxExecution } from '@/types';

type MockContext = ReturnType<typeof buildMockContext>;

function buildMockContext() {
  const execution: SandboxExecution = {
    success: true,
    workspace_id: 'ws-test',
    commands: [
      {
        command: ['pytest', '-q'],
        return_code: 0,
        stdout: '1 passed',
        stderr: '',
        duration_ms: 12.5,
      },
    ],
  };
  const proposal = {
    proposal_id: 'proposal-1',
    task_id: 'task-1',
    feature_request_id: 'FR-1',
    title: 'Add smoke tests',
    summary: 'Introduce sandbox smoke tests for diffs.',
    diff: 'diff --git a/foo b/foo',
    status: 'pending',
    created_at: new Date().toISOString(),
    created_by: { subject: 'dev-bot' },
    validation: { status: 'pending' },
    approvals: [],
    rationale: ['Reduces regressions'],
  };
  const task = {
    task_id: 'task-1',
    feature_request_id: 'FR-1',
    title: 'Enable smoke tests',
    description: 'Ensure dev agent validations run smoke tests.',
    priority: 'high',
    status: 'triaged',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    planner_notes: ['Verify command idempotency'],
    risk_score: 0.5,
    metadata: { tags: ['quality', 'automation'] },
    proposals: [proposal],
  };
  return {
    backlog: [task],
    loading: false,
    selectedTask: task,
    selectedProposal: proposal,
    selectTask: vi.fn(),
    selectProposal: vi.fn(),
    isApplying: false,
    hasPrivilege: true,
    lastExecution: execution,
    lastExecutionProposalId: proposal.proposal_id,
    lastUpdated: Date.now(),
    applyProposal: vi.fn(async () => execution),
    error: null,
    refresh: vi.fn(async () => undefined),
    clearError: vi.fn(),
  };
}

const mockContext: MockContext = buildMockContext();

vi.mock('@/context/DevTeamContext', () => ({
  useDevTeamContext: () => mockContext,
}));

describe('DevTeamSection', () => {
  it('renders backlog and proposal information', () => {
    render(<DevTeamSection />);
    expect(screen.getByRole('heading', { name: /backlog/i })).toBeInTheDocument();
    expect(screen.getByText(/Enable smoke tests/i)).toBeInTheDocument();
    expect(screen.getByText(/Diff preview/i)).toBeInTheDocument();
    expect(screen.getByText(/Workspace ws-test/i)).toBeInTheDocument();
  });
});
