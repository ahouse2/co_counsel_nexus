import { useCallback, useMemo } from 'react';
import { useDevTeamContext } from '@/context/DevTeamContext';
import { DevAgentProposal, SandboxExecution } from '@/types';
import { BacklogList } from './BacklogList';
import { ProposalDetail } from './ProposalDetail';
import { ValidationResults } from './ValidationResults';
import { ApprovalList } from './ApprovalList';

function normaliseProposalValidation(proposal: DevAgentProposal | null): SandboxExecution | null {
  if (!proposal) {
    return null;
  }
  const validation = proposal.validation as Record<string, unknown> | null;
  if (!validation || typeof validation !== 'object') {
    return null;
  }
  const commandsRaw = (validation as { commands?: unknown }).commands;
  if (!Array.isArray(commandsRaw)) {
    return null;
  }
  const commands = commandsRaw.map((command) => {
    const record = command as Record<string, unknown>;
    const commandLine = record.command;
    return {
      command: Array.isArray(commandLine) ? commandLine.map((item) => String(item)) : [],
      return_code: Number(record.return_code ?? 0),
      stdout: typeof record.stdout === 'string' ? record.stdout : '',
      stderr: typeof record.stderr === 'string' ? record.stderr : '',
      duration_ms: Number(record.duration_ms ?? 0),
    };
  });
  const success = (validation as { success?: unknown }).success;
  const workspace = (validation as { workspace_id?: unknown }).workspace_id;
  return {
    success: typeof success === 'boolean' ? success : proposal.status === 'validated',
    workspace_id: typeof workspace === 'string' ? workspace : 'sandbox',
    commands,
  };
}

export function DevTeamSection(): JSX.Element {
  const {
    backlog,
    loading,
    selectedTask,
    selectedProposal,
    selectTask,
    selectProposal,
    isApplying,
    hasPrivilege,
    lastExecution,
    lastExecutionProposalId,
    lastUpdated,
    applyProposal,
    error,
  } = useDevTeamContext();

  const execution = useMemo(() => {
    if (
      selectedProposal &&
      lastExecution &&
      lastExecutionProposalId &&
      lastExecutionProposalId === selectedProposal.proposal_id
    ) {
      return lastExecution;
    }
    return normaliseProposalValidation(selectedProposal);
  }, [lastExecution, lastExecutionProposalId, selectedProposal]);

  const validationStatus = useMemo(() => {
    if (
      selectedProposal &&
      lastExecution &&
      lastExecutionProposalId === selectedProposal.proposal_id
    ) {
      return lastExecution.success ? 'validated' : 'failed';
    }
    const validation = (selectedProposal?.validation ?? null) as { status?: unknown } | null;
    if (validation && typeof validation === 'object' && typeof validation.status === 'string') {
      return validation.status;
    }
    return selectedProposal?.status ?? 'pending';
  }, [lastExecution, lastExecutionProposalId, selectedProposal]);

  const handleApprove = useCallback(() => {
    if (!selectedProposal) {
      return;
    }
    void applyProposal(selectedProposal.proposal_id);
  }, [applyProposal, selectedProposal]);

  return (
    <div className="dev-team-section">
      <div className="dev-team-grid">
        <BacklogList
          tasks={backlog}
          loading={loading}
          selectedTaskId={selectedTask?.task_id ?? null}
          selectedProposalId={selectedProposal?.proposal_id ?? null}
          onSelectTask={selectTask}
          onSelectProposal={selectProposal}
          lastUpdated={lastUpdated}
        />
        <div className="dev-team-content">
          {hasPrivilege === false ? (
            <div className="dev-team-warning" role="alert">
              Dev-agent administrator scope required. Ask a platform engineer to grant access.
            </div>
          ) : null}
          <ProposalDetail
            task={selectedTask ?? null}
            proposal={selectedProposal ?? null}
            isApplying={isApplying}
            hasPrivilege={hasPrivilege}
            onApprove={selectedProposal ? handleApprove : null}
            validation={<ValidationResults execution={execution} status={validationStatus} />}
            approvals={<ApprovalList approvals={selectedProposal?.approvals ?? []} />}
            error={error}
          />
        </div>
      </div>
    </div>
  );
}
