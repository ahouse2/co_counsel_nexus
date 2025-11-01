import { DevAgentMetrics } from '@/types';

type MetricsDashboardProps = {
  metrics: DevAgentMetrics | null;
};

function formatPercent(value: number): string {
  if (!Number.isFinite(value)) {
    return '0%';
  }
  return `${Math.round(value * 100)}%`;
}

function formatVelocity(value: number): string {
  if (!Number.isFinite(value)) {
    return '0.0/day';
  }
  return `${value.toFixed(2)}/day`;
}

export function MetricsDashboard({ metrics }: MetricsDashboardProps): JSX.Element {
  if (!metrics) {
    return (
      <section className="dev-team-metrics" aria-live="polite">
        <h2>Dev-agent health</h2>
        <p className="dev-team-hint">Metrics will appear once the backlog loads.</p>
      </section>
    );
  }

  const weeklyVelocity = metrics.velocity_per_day * 7;

  return (
    <section className="dev-team-metrics" aria-live="polite">
      <header>
        <h2>Dev-agent health</h2>
        <span className="dev-team-timestamp" aria-label="metrics generated timestamp">
          Updated {new Date(metrics.generated_at).toLocaleString()}
        </span>
      </header>
      <div className="dev-team-metrics-grid">
        <article>
          <h3>Velocity</h3>
          <p className="dev-team-metric-value">{formatVelocity(metrics.velocity_per_day)}</p>
          <p className="dev-team-metric-subtext">{weeklyVelocity.toFixed(2)} per week</p>
        </article>
        <article>
          <h3>Quality gate pass rate</h3>
          <p className="dev-team-metric-value">{formatPercent(metrics.quality_gate_pass_rate)}</p>
          <p className="dev-team-metric-subtext">{metrics.validated_proposals} validated proposals</p>
        </article>
        <article>
          <h3>Rollouts</h3>
          <p className="dev-team-metric-value">{metrics.active_rollouts}</p>
          <p className="dev-team-metric-subtext">{metrics.rollout_pending} awaiting launch</p>
        </article>
        <article>
          <h3>Backlog</h3>
          <p className="dev-team-metric-value">{metrics.total_tasks}</p>
          <p className="dev-team-metric-subtext">{metrics.triaged_tasks} triaged tasks</p>
        </article>
      </div>
      {metrics.feature_toggles.length ? (
        <div className="dev-team-metrics-toggles">
          <h3>Active feature toggles</h3>
          <ul>
            {metrics.feature_toggles.map((toggle) => (
              <li key={`${toggle.toggle}-${toggle.status}`}>
                <code>{toggle.toggle}</code>
                <span className="dev-team-metric-subtext" aria-label="toggle stage">
                  {toggle.stage ?? 'stage'} · {toggle.status}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="dev-team-metrics-workflows">
        <h3>Regression CI workflows</h3>
        <ul>
          {metrics.ci_workflows.map((workflow) => (
            <li key={workflow}>{workflow}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
