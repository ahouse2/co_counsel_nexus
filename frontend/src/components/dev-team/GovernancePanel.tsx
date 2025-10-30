import { DevAgentProposal } from '@/types';

type GovernancePanelProps = {
  proposal: DevAgentProposal | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object') {
    return null;
  }
  return value as Record<string, unknown>;
}

export function GovernancePanel({ proposal }: GovernancePanelProps): JSX.Element {
  if (!proposal) {
    return (
      <div>
        <h3>Governance</h3>
        <p className="dev-team-hint">Select a proposal to view rollouts and policy gates.</p>
      </div>
    );
  }

  const governance = asRecord(proposal.governance) ?? {};
  const regression = asRecord(governance.regression_gate) ?? {};
  const rollout = asRecord(governance.rollout) ?? {};
  const stages = Array.isArray(rollout.stages) ? rollout.stages : [];

  return (
    <div>
      <h3>Governance</h3>
      <section className="dev-team-governance-block">
        <h4>Regression gate</h4>
        <p className={`dev-team-governance-status status-${String(regression.status ?? 'pending')}`}>
          Status: {String(regression.status ?? 'pending')}
        </p>
        {Array.isArray(regression.ci_workflows) ? (
          <ul className="dev-team-governance-list">
            {(regression.ci_workflows as unknown[]).map((item, index) => {
              const entry = asRecord(item) ?? {};
              return (
                <li key={`${entry.workflow ?? index}`}>
                  <span>{String(entry.workflow ?? 'workflow')}</span>
                  <span className="dev-team-metric-subtext">{String(entry.status ?? 'pending')}</span>
                </li>
              );
            })}
          </ul>
        ) : null}
        {Array.isArray(regression.failed_commands) && regression.failed_commands.length ? (
          <details className="dev-team-governance-failures">
            <summary>Failed commands</summary>
            <ul>
              {(regression.failed_commands as unknown[]).map((command, index) => {
                const record = asRecord(command) ?? {};
                const commandLine = Array.isArray(record.command)
                  ? (record.command as unknown[]).map((item) => String(item)).join(' ')
                  : 'command';
                return (
                  <li key={`${commandLine}-${index}`}>
                    <code>{commandLine}</code>
                    <span className="dev-team-metric-subtext">exit {String(record.return_code ?? '')}</span>
                  </li>
                );
              })}
            </ul>
          </details>
        ) : null}
      </section>
      {stages.length ? (
        <section className="dev-team-governance-block">
          <h4>Staged rollout toggles</h4>
          <ul className="dev-team-governance-list">
            {stages.map((stage, index) => {
              const record = asRecord(stage) ?? {};
              return (
                <li key={`${record.toggle ?? index}`}>
                  <code>{String(record.toggle ?? 'toggle')}</code>
                  <span className="dev-team-metric-subtext">
                    {String(record.name ?? record.stage ?? 'stage')} · {String(record.status ?? 'pending')}
                  </span>
                </li>
              );
            })}
          </ul>
        </section>
      ) : (
        <p className="dev-team-hint">No rollout stages scheduled.</p>
      )}
    </div>
  );
}
