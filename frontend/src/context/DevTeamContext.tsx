import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  applyDevAgentProposal,
  fetchDevAgentBacklog,
  HttpError,
} from '@/utils/apiClient';
import {
  DevAgentProposal,
  DevAgentTask,
  SandboxCommandResult,
  SandboxExecution,
  DevAgentMetrics,
} from '@/types';

const POLL_INTERVAL_MS = 30000;

type DevTeamContextValue = {
  backlog: DevAgentTask[];
  loading: boolean;
  isApplying: boolean;
  error: string | null;
  hasPrivilege: boolean | null;
  lastExecution: SandboxExecution | null;
  lastExecutionProposalId: string | null;
  lastUpdated: number | null;
  metrics: DevAgentMetrics | null;
  selectedTask: DevAgentTask | null;
  selectedProposal: DevAgentProposal | null;
  selectTask: (taskId: string) => void;
  selectProposal: (proposalId: string) => void;
  refresh: () => Promise<void>;
  clearError: () => void;
  applyProposal: (proposalId: string) => Promise<SandboxExecution | null>;
};

const DevTeamContext = createContext<DevTeamContextValue | undefined>(undefined);

function normaliseExecution(detail: unknown): SandboxExecution {
  if (detail && typeof detail === 'object') {
    const record = detail as { workspace_id?: string; commands?: SandboxCommandResult[] };
    const commands = Array.isArray(record.commands)
      ? record.commands.map((command) => ({
          command: Array.isArray(command.command)
            ? command.command.map((value) => String(value))
            : [],
          return_code: Number(command.return_code ?? 1),
          stdout: typeof command.stdout === 'string' ? command.stdout : '',
          stderr: typeof command.stderr === 'string' ? command.stderr : '',
          duration_ms: Number(command.duration_ms ?? 0),
        }))
      : [];
    return {
      success: false,
      workspace_id: typeof record.workspace_id === 'string' ? record.workspace_id : 'sandbox',
      commands,
    };
  }
  return {
    success: false,
    workspace_id: 'sandbox',
    commands: [],
  };
}

export function DevTeamProvider({ children }: { children: ReactNode }): JSX.Element {
  const [backlog, setBacklog] = useState<DevAgentTask[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [isApplying, setIsApplying] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [hasPrivilege, setHasPrivilege] = useState<boolean | null>(null);
  const [lastExecution, setLastExecution] = useState<SandboxExecution | null>(null);
  const [lastExecutionProposalId, setLastExecutionProposalId] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  const [metrics, setMetrics] = useState<DevAgentMetrics | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedProposalId, setSelectedProposalId] = useState<string | null>(null);
  const pollHandle = useRef<number | null>(null);

  const synchroniseSelection = useCallback(
    (tasks: DevAgentTask[]) => {
      if (!tasks.length) {
        setSelectedTaskId(null);
        setSelectedProposalId(null);
        return;
      }
      const taskMap = new Map(tasks.map((task) => [task.task_id, task]));
      const preferredTaskId = selectedTaskId && taskMap.has(selectedTaskId)
        ? selectedTaskId
        : tasks[0].task_id;
      setSelectedTaskId(preferredTaskId);
      const task = taskMap.get(preferredTaskId);
      if (!task) {
        setSelectedProposalId(null);
        return;
      }
      if (!task.proposals.length) {
        setSelectedProposalId(null);
        return;
      }
      const hasSelectedProposal = selectedProposalId
        ? task.proposals.some((proposal) => proposal.proposal_id === selectedProposalId)
        : false;
      setSelectedProposalId(hasSelectedProposal ? selectedProposalId : task.proposals[0].proposal_id);
    },
    [selectedProposalId, selectedTaskId]
  );

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetchDevAgentBacklog();
      setBacklog(response.backlog);
      setMetrics(response.metrics);
      synchroniseSelection(response.backlog);
      setHasPrivilege(true);
      setError(null);
      setLastUpdated(Date.now());
    } catch (cause) {
      if (cause instanceof HttpError) {
        if (cause.status === 401 || cause.status === 403) {
          setHasPrivilege(false);
          setError('You do not have permission to view the Dev Team backlog.');
          setMetrics(null);
        } else {
          setError(cause.message);
        }
      } else {
        setError(cause instanceof Error ? cause.message : 'Unable to load Dev Team backlog.');
        setMetrics(null);
      }
    } finally {
      setLoading(false);
    }
  }, [synchroniseSelection]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (pollHandle.current) {
      window.clearInterval(pollHandle.current);
      pollHandle.current = null;
    }
    if (hasPrivilege === false) {
      return;
    }
    pollHandle.current = window.setInterval(() => {
      void refresh();
    }, POLL_INTERVAL_MS);
    return () => {
      if (pollHandle.current) {
        window.clearInterval(pollHandle.current);
        pollHandle.current = null;
      }
    };
  }, [hasPrivilege, refresh]);

  const selectedTask = useMemo(() => backlog.find((task) => task.task_id === selectedTaskId) ?? null, [
    backlog,
    selectedTaskId,
  ]);

  const selectedProposal = useMemo(
    () =>
      selectedTask?.proposals.find((proposal) => proposal.proposal_id === selectedProposalId) ?? null,
    [selectedTask, selectedProposalId]
  );

  useEffect(() => {
    if (!selectedProposalId) {
      if (lastExecution || lastExecutionProposalId) {
        setLastExecution(null);
        setLastExecutionProposalId(null);
      }
      return;
    }
    if (lastExecutionProposalId && lastExecutionProposalId !== selectedProposalId) {
      setLastExecution(null);
      setLastExecutionProposalId(null);
    }
  }, [lastExecution, lastExecutionProposalId, selectedProposalId]);

  const selectTask = useCallback(
    (taskId: string) => {
      setSelectedTaskId(taskId);
      const task = backlog.find((item) => item.task_id === taskId);
      if (task) {
        if (task.proposals.length) {
          const defaultProposal = task.proposals[0]?.proposal_id ?? null;
          setSelectedProposalId((current) => {
            if (!current) {
              return defaultProposal;
            }
            return task.proposals.some((proposal) => proposal.proposal_id === current)
              ? current
              : defaultProposal;
          });
        } else {
          setSelectedProposalId(null);
        }
      } else {
        setSelectedProposalId(null);
      }
    },
    [backlog]
  );

  const selectProposal = useCallback((proposalId: string) => {
    setSelectedProposalId(proposalId);
  }, []);

  const applyProposal = useCallback(
    async (proposalId: string) => {
      setIsApplying(true);
      try {
        const response = await applyDevAgentProposal(proposalId);
        setHasPrivilege(true);
        setError(null);
        setLastExecution(response.execution);
        setLastExecutionProposalId(response.proposal.proposal_id);
        setBacklog((previous) => {
          const next = previous.map((task) =>
            task.task_id === response.task.task_id ? response.task : task
          );
          if (!next.some((task) => task.task_id === response.task.task_id)) {
            next.push(response.task);
          }
          return next;
        });
        setSelectedTaskId(response.task.task_id);
        setSelectedProposalId(response.proposal.proposal_id);
        setLastUpdated(Date.now());
        setMetrics(response.metrics);
        return response.execution;
      } catch (cause) {
        if (cause instanceof HttpError) {
          if (cause.status === 401 || cause.status === 403) {
            setHasPrivilege(false);
            setError('You do not have permission to approve proposals.');
          } else if (cause.status === 422) {
            const execution = normaliseExecution((cause as HttpError & { detail?: unknown }).detail);
            setLastExecution(execution);
            setLastExecutionProposalId(proposalId);
            setError('Sandbox validation failed. Review the command outputs.');
            return execution;
          } else {
            setError(cause.message);
          }
        } else {
          setError(cause instanceof Error ? cause.message : 'Unable to approve the proposal.');
        }
        return null;
      } finally {
        setIsApplying(false);
      }
    },
    []
  );

  const clearError = useCallback(() => setError(null), []);

  const value = useMemo<DevTeamContextValue>(
    () => ({
      backlog,
      loading,
      isApplying,
      error,
      hasPrivilege,
      lastExecution,
      lastExecutionProposalId,
      lastUpdated,
      metrics,
      selectedTask,
      selectedProposal,
      selectTask,
      selectProposal,
      refresh,
      clearError,
      applyProposal,
    }),
    [
      applyProposal,
      backlog,
      clearError,
      error,
      hasPrivilege,
      isApplying,
      lastExecution,
      lastExecutionProposalId,
      lastUpdated,
      loading,
      refresh,
      selectProposal,
      selectTask,
      selectedProposal,
      selectedTask,
      metrics,
    ]
  );

  return <DevTeamContext.Provider value={value}>{children}</DevTeamContext.Provider>;
}

export function useDevTeamContext(): DevTeamContextValue {
  const context = useContext(DevTeamContext);
  if (!context) {
    throw new Error('useDevTeamContext must be used within a DevTeamProvider');
  }
  return context;
}
