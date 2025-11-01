import { ReactNode } from 'react';
import { DevAgentProposal, DevAgentTask } from '@/types';

type ProposalDetailProps = {
  task: DevAgentTask | null;
  proposal: DevAgentProposal | null;
  isApplying: boolean;
  hasPrivilege: boolean | null;
  onApprove?: (() => void) | null;
  validation?: ReactNode;
  approvals?: ReactNode;
  governance?: ReactNode;
  error?: string | null;
};

function renderMetadata(metadata: Record<string, unknown> | undefined): ReactNode {
  if (!metadata || Object.keys(metadata).length === 0) {
    return <p className="dev-team-hint">No metadata recorded.</p>;
  }
  return (
    <dl className="dev-team-metadata">
      {Object.entries(metadata).map(([key, value]) => (
        <div key={key}>
          <dt>{key}</dt>
          <dd>{String(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

export function ProposalDetail({
  task,
  proposal,
  isApplying,
  hasPrivilege,
  onApprove,
  validation,
  approvals,
  governance,
  error,
}: ProposalDetailProps): JSX.Element {
  if (!task || !proposal) {
    return (
      <section className="dev-team-detail" aria-live="polite">
        <h2>Proposal details</h2>
        <p className="dev-team-hint">Select a proposal from the backlog to inspect its details.</p>
      </section>
    );
  }

  const disableApprove =
    !onApprove || isApplying || hasPrivilege === false || proposal.status === 'validated';
  const approveLabel = proposal.status === 'validated' ? 'Already approved' : 'Validate & approve';

  return (
    <section className="dev-team-detail" aria-live="polite">
      <header className="dev-team-detail-header">
        <div>
          <h2>{proposal.title}</h2>
          <p className="dev-team-detail-summary">{proposal.summary}</p>
        </div>
        <div className="dev-team-actions">
          {error ? (
            <div className="dev-team-error" role="alert">
              {error}
            </div>
          ) : null}
          <button
            type="button"
            onClick={() => onApprove?.()}
            disabled={disableApprove}
            className="dev-team-approve"
          >
            {isApplying ? 'Validating…' : approveLabel}
          </button>
          {hasPrivilege === false ? (
            <p className="dev-team-hint">Requires dev-agent:admin scope.</p>
          ) : null}
        </div>
      </header>
      <div className="dev-team-detail-body">
        <section>
          <h3>Feature request</h3>
          <p>{task.description}</p>
          <div className="dev-team-detail-meta">
            <span className="badge" data-priority={task.priority}>
              {task.priority} priority
            </span>
            <span className="badge" data-status={task.status}>
              {task.status}
            </span>
            {typeof task.risk_score === 'number' ? (
              <span className="badge">Risk {task.risk_score.toFixed(2)}</span>
            ) : null}
          </div>
          <section>
            <h4>Planner notes</h4>
            {task.planner_notes.length ? (
              <ul className="dev-team-notes">
                {task.planner_notes.map((note, index) => (
                  <li key={`${note}-${index}`}>{note}</li>
                ))}
              </ul>
            ) : (
              <p className="dev-team-hint">No planner notes.</p>
            )}
          </section>
        </section>
        <section>
          <h3>Diff preview</h3>
          <pre className="dev-team-diff" aria-label="proposed diff">
            {proposal.diff || 'No diff provided.'}
          </pre>
        </section>
        <section>
          <h3>Metadata</h3>
          {renderMetadata(task.metadata)}
        </section>
        <section>
          <h3>Created by</h3>
          <pre className="dev-team-created-by">{JSON.stringify(proposal.created_by, null, 2)}</pre>
        </section>
      </div>
      <div className="dev-team-detail-footer">
        <section>{validation}</section>
        <section>
          <h3>Approvals</h3>
          {approvals}
        </section>
        <section>{governance}</section>
      </div>
    </section>
  );
}
