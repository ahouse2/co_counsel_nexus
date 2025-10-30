import { DevAgentApprovalRecord } from '@/types';

type ApprovalListProps = {
  approvals: DevAgentApprovalRecord[];
};

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  year: 'numeric',
  month: 'short',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
});

function formatTimestamp(timestamp: string): string {
  try {
    return dateFormatter.format(new Date(timestamp));
  } catch {
    return timestamp;
  }
}

export function ApprovalList({ approvals }: ApprovalListProps): JSX.Element {
  if (!approvals.length) {
    return <p className="dev-team-hint">No approvals recorded yet.</p>;
  }
  const sorted = [...approvals].sort((a, b) => (a.timestamp > b.timestamp ? -1 : 1));
  return (
    <ul className="dev-team-approvals">
      {sorted.map((approval, index) => {
        const actor = approval.actor ?? {};
        const roles = Array.isArray(actor.roles) ? (actor.roles as string[]).join(', ') : undefined;
        return (
          <li key={`${approval.timestamp}-${index}`}>
            <div className="dev-team-approval-meta">
              <span className="dev-team-approval-outcome" data-outcome={approval.outcome}>
                {approval.outcome}
              </span>
              <span className="dev-team-approval-time">{formatTimestamp(approval.timestamp)}</span>
            </div>
            <div className="dev-team-approval-actor">
              <span>{String(actor.subject ?? actor.client_id ?? 'Unknown actor')}</span>
              {roles ? <span className="dev-team-approval-roles">{roles}</span> : null}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
