import { DevAgentTask } from '@/types';

type BacklogListProps = {
  tasks: DevAgentTask[];
  selectedTaskId: string | null;
  selectedProposalId: string | null;
  onSelectTask: (taskId: string) => void;
  onSelectProposal: (proposalId: string) => void;
  loading?: boolean;
  lastUpdated?: number | null;
};

function formatTimestamp(timestamp: number | null | undefined): string | null {
  if (!timestamp) {
    return null;
  }
  try {
    return new Intl.DateTimeFormat(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(new Date(timestamp));
  } catch {
    return null;
  }
}

export function BacklogList({
  tasks,
  selectedTaskId,
  selectedProposalId,
  onSelectTask,
  onSelectProposal,
  loading = false,
  lastUpdated,
}: BacklogListProps): JSX.Element {
  const updatedLabel = formatTimestamp(lastUpdated);
  return (
    <aside className="dev-team-backlog" aria-label="Dev Team backlog">
      <header className="dev-team-backlog-header">
        <h2>Backlog</h2>
        {updatedLabel ? <span className="dev-team-timestamp">Synced {updatedLabel}</span> : null}
      </header>
      {loading ? (
        <p className="dev-team-hint" role="status">
          Loading backlog…
        </p>
      ) : null}
      {!loading && tasks.length === 0 ? (
        <p className="dev-team-hint">No feature requests have been triaged yet.</p>
      ) : null}
      <ul className="dev-team-task-list">
        {tasks.map((task) => {
          const isActiveTask = task.task_id === selectedTaskId;
          return (
            <li
              key={task.task_id}
              className={isActiveTask ? 'dev-team-task active' : 'dev-team-task'}
              data-status={task.status}
            >
              <button
                type="button"
                className="dev-team-task-button"
                aria-pressed={isActiveTask}
                onClick={() => onSelectTask(task.task_id)}
              >
                <div className="dev-team-task-meta">
                  <span className="dev-team-task-priority" data-priority={task.priority}>
                    {task.priority}
                  </span>
                  <span className="dev-team-task-status">{task.status}</span>
                  {typeof task.risk_score === 'number' ? (
                    <span className="dev-team-task-risk">Risk {task.risk_score.toFixed(2)}</span>
                  ) : null}
                </div>
                <h3>{task.title}</h3>
                <p className="dev-team-task-description">{task.description}</p>
                {task.planner_notes.length ? (
                  <p className="dev-team-task-notes" title={task.planner_notes.join('\n')}>
                    Planner notes: {task.planner_notes.length}
                  </p>
                ) : null}
                <p className="dev-team-task-tags">
                  {(task.metadata?.tags as string[] | undefined)?.join(', ') || 'No tags'}
                </p>
              </button>
              {isActiveTask ? (
                <ul className="dev-team-proposal-list" aria-label={`Proposals for ${task.title}`}>
                  {task.proposals.map((proposal) => {
                    const isActiveProposal = proposal.proposal_id === selectedProposalId;
                    return (
                      <li
                        key={proposal.proposal_id}
                        className={
                          isActiveProposal
                            ? 'dev-team-proposal active'
                            : 'dev-team-proposal'
                        }
                      >
                        <button
                          type="button"
                          onClick={() => onSelectProposal(proposal.proposal_id)}
                          aria-pressed={isActiveProposal}
                        >
                          <span className="dev-team-proposal-title">{proposal.title}</span>
                          <span className="dev-team-proposal-status" data-status={proposal.status}>
                            {proposal.status}
                          </span>
                          <span className="dev-team-proposal-rationale">
                            {proposal.rationale.length ? `${proposal.rationale.length} notes` : 'No notes'}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                  {task.proposals.length === 0 ? (
                    <li className="dev-team-empty-proposals">No proposals registered.</li>
                  ) : null}
                </ul>
              ) : null}
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
