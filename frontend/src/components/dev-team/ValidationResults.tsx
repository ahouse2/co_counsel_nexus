import { SandboxExecution } from '@/types';

type ValidationResultsProps = {
  execution: SandboxExecution | null;
  status: string;
};

function statusLabel(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized.includes('fail')) return 'Validation failed';
  if (normalized.includes('validate') || normalized === 'approved') return 'Validation succeeded';
  if (normalized.includes('pending')) return 'Validation pending';
  return status;
}

export function ValidationResults({ execution, status }: ValidationResultsProps): JSX.Element {
  if (!execution || execution.commands.length === 0) {
    return (
      <div className="dev-team-validation" data-status={status}>
        <h3>Validation</h3>
        <p className="dev-team-hint">{statusLabel(status)}</p>
      </div>
    );
  }
  return (
    <div className="dev-team-validation" data-status={status}>
      <h3>Validation</h3>
      <p className="dev-team-hint">Workspace {execution.workspace_id}</p>
      <ul className="dev-team-validation-commands">
        {execution.commands.map((command, index) => {
          const success = command.return_code === 0;
          return (
            <li key={`${command.command.join(' ')}-${index}`} className={success ? 'success' : 'error'}>
              <div className="dev-team-command-header">
                <code>{command.command.join(' ') || 'git apply'}</code>
                <span className="dev-team-command-status">{success ? 'Passed' : 'Failed'}</span>
              </div>
              {command.stdout ? (
                <pre className="dev-team-command-output" aria-label="stdout">
                  {command.stdout.trim()}
                </pre>
              ) : null}
              {command.stderr ? (
                <pre className="dev-team-command-output error" aria-label="stderr">
                  {command.stderr.trim()}
                </pre>
              ) : null}
              <span className="dev-team-command-duration">{command.duration_ms.toFixed(2)} ms</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
