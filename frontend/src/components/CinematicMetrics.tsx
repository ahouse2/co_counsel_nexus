import { useMemo } from 'react';

interface MetricCard {
  id: string;
  label: string;
  value: string;
  delta?: string;
  status?: 'positive' | 'negative' | 'neutral';
  description?: string;
}

const metricCopy: MetricCard[] = [
  {
    id: 'case-velocity',
    label: 'Case Velocity Index',
    value: '1.12x',
    delta: '+0.08',
    status: 'positive',
    description: 'Acceleration over last 72 hours across motions, filings, and hearings.',
  },
  {
    id: 'evidence-confidence',
    label: 'Evidence Confidence',
    value: '97.4%',
    delta: '+2.4%',
    status: 'positive',
    description: 'AI-verified provenance and privilege readiness for uploaded exhibits.',
  },
  {
    id: 'trial-readiness',
    label: 'Trial Readiness Pulse',
    value: '88%',
    delta: '-1%',
    status: 'neutral',
    description: 'Forecast from simulation arena factoring witness strength and motion backlog.',
  },
  {
    id: 'ai-co-counsel',
    label: 'AI Co-Counsel Sync',
    value: 'Live',
    status: 'positive',
    description: 'All co-counsel agents active with telemetry and legal hold monitoring engaged.',
  },
];

export function CinematicMetrics(): JSX.Element {
  const metrics = useMemo(() => metricCopy, []);

  return (
    <section className="cinematic-metrics" aria-label="Live case metrics">
      {metrics.map((metric) => (
        <article key={metric.id} className="metric-card" aria-live="polite">
          <header>
            <span className="metric-label">{metric.label}</span>
            {metric.delta ? (
              <span
                className={`metric-delta ${metric.status ?? 'neutral'}`}
                aria-label={metric.status === 'negative' ? 'decrease' : 'increase'}
              >
                {metric.delta}
              </span>
            ) : null}
          </header>
          <div className="metric-value">{metric.value}</div>
          {metric.description ? <p className="metric-description">{metric.description}</p> : null}
        </article>
      ))}
    </section>
  );
}
