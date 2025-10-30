import { useEffect, useMemo, useState } from 'react';
import { EvidenceModal } from '@/components/EvidenceModal';
import { useQueryContext } from '@/context/QueryContext';
import {
  Citation,
  EntityHighlight,
  OutcomeProbability,
  RelationTag,
  TimelineEvent,
} from '@/types';

export function TimelineView(): JSX.Element {
  const {
    timelineEvents,
    timelineMeta,
    timelineLoading,
    loadMoreTimeline,
    timelineEntityFilter,
    setTimelineEntityFilter,
    timelineRiskBand,
    setTimelineRiskBand,
    timelineDeadline,
    setTimelineDeadline,
    citations,
    setActiveCitation,
  } = useQueryContext();
  const [activeIndex, setActiveIndex] = useState(0);
  const [expandedEvent, setExpandedEvent] = useState<TimelineEvent | null>(null);
  const grouped = useMemo(() => groupByDay(timelineEvents), [timelineEvents]);

  useEffect((): (() => void) => {
    const handler = (event: KeyboardEvent): void => {
      if (event.key === 'n') {
        event.preventDefault();
        setActiveIndex((index) => Math.min(index + 1, timelineEvents.length - 1));
      }
      if (event.key === 'p') {
        event.preventDefault();
        setActiveIndex((index) => Math.max(index - 1, 0));
      }
    };
    window.addEventListener('keydown', handler);
    return () => {
      window.removeEventListener('keydown', handler);
    };
  }, [timelineEvents.length]);

  useEffect((): void => {
    if (activeIndex >= timelineEvents.length) {
      setActiveIndex(Math.max(timelineEvents.length - 1, 0));
    }
  }, [timelineEvents, activeIndex]);

  useEffect(() => {
    const handler = (event: Event): void => {
      const detail = (event as CustomEvent<string>).detail;
      if (!detail) return;
      const index = timelineEvents.findIndex((item) => item.id === detail);
      if (index >= 0) {
        setActiveIndex(index);
        requestAnimationFrame(() => {
          const target = document.querySelector<HTMLElement>(`[data-timeline-id="${detail}"]`);
          target?.focus({ preventScroll: false });
        });
      }
    };
    window.addEventListener('focus-timeline-event', handler as EventListener);
    return () => {
      window.removeEventListener('focus-timeline-event', handler as EventListener);
    };
  }, [timelineEvents]);

  const handleCitationLink = (docId: string): void => {
    const match = citations.find((citation) => citation.docId === docId);
    if (match) {
      setActiveCitation(match);
    } else {
      const fallback: Citation = {
        docId,
        span: 'Details not yet available for this document. Check the source repository.',
      };
      setActiveCitation(fallback);
    }
  };

  return (
    <div className="timeline-view">
      <header>
        <h2>Timeline</h2>
        <p className="panel-subtitle">Graph-enriched events aligned with evidence citations.</p>
        <label htmlFor="timeline-entity" className="sr-only">
          Filter by entity
        </label>
        <input
          id="timeline-entity"
          type="search"
          placeholder="Filter by entity or label"
          value={timelineEntityFilter ?? ''}
          onChange={(event) => setTimelineEntityFilter(event.target.value || null)}
        />
        <div className="timeline-filters" role="group" aria-label="Advanced timeline filters">
          <label htmlFor="timeline-risk" className="sr-only">
            Filter by risk band
          </label>
          <select
            id="timeline-risk"
            value={timelineRiskBand ?? ''}
            onChange={(event) =>
              setTimelineRiskBand(event.target.value ? (event.target.value as 'low' | 'medium' | 'high') : null)
            }
          >
            <option value="">All risk levels</option>
            <option value="high">High risk</option>
            <option value="medium">Medium risk</option>
            <option value="low">Low risk</option>
          </select>
          <label htmlFor="timeline-deadline" className="sr-only">
            Filter by motion deadline
          </label>
          <input
            id="timeline-deadline"
            type="date"
            value={timelineDeadline?.slice(0, 10) ?? ''}
            onChange={(event) => {
              const value = event.target.value;
              setTimelineDeadline(value ? `${value}T23:59:59` : null);
            }}
          />
          {timelineDeadline && (
            <button
              type="button"
              className="timeline-filter-clear"
              onClick={() => setTimelineDeadline(null)}
            >
              Clear deadline
            </button>
          )}
        </div>
      </header>
      <div className="timeline-summary" role="status" aria-live="polite">
        Rendering {timelineEvents.length} events {timelineMeta?.has_more ? 'with more available' : ''}
      </div>
      <ol className="timeline-groups" aria-live="polite" id="timeline">
        {grouped.map(({ day, events }) => (
          <li key={day}>
            <h3>{day}</h3>
            <ul>
              {events.map((event) => (
                <TimelineCard
                  key={event.id}
                  event={event}
                  active={timelineEvents.indexOf(event) === activeIndex}
                  onFocus={() => setActiveIndex(timelineEvents.indexOf(event))}
                  onExpand={() => setExpandedEvent(event)}
                  onCitationLink={handleCitationLink}
                />
              ))}
            </ul>
          </li>
        ))}
      </ol>
      <div className="timeline-actions">
        <button type="button" onClick={() => void loadMoreTimeline()} disabled={!timelineMeta?.has_more || timelineLoading}>
          {timelineLoading ? 'Loading…' : timelineMeta?.has_more ? 'Load more events' : 'No more events'}
        </button>
      </div>
      {expandedEvent && (
        <EvidenceModal
          title={`Timeline event ${expandedEvent.title}`}
          onClose={() => setExpandedEvent(null)}
        >
          <article className="timeline-popout">
            <header>
              <time dateTime={expandedEvent.ts}>{new Date(expandedEvent.ts).toLocaleString()}</time>
              {typeof expandedEvent.confidence === 'number' && (
                <span className="confidence">Confidence {(expandedEvent.confidence * 100).toFixed(0)}%</span>
              )}
              {expandedEvent.risk_band && (
                <span className={`risk-chip risk-chip--${expandedEvent.risk_band}`}>
                  {expandedEvent.risk_band.toUpperCase()} risk
                </span>
              )}
            </header>
            <p>{expandedEvent.summary}</p>
            <ProbabilityOverview event={expandedEvent} />
            {expandedEvent.citations.length > 0 && (
              <section>
                <h4>Linked Citations</h4>
                <ul>
                  {expandedEvent.citations.map((docId) => (
                    <li key={`${expandedEvent.id}-${docId}`}>
                      <button type="button" onClick={() => handleCitationLink(docId)}>
                        {citations.find((citation) => citation.docId === docId)?.title ?? docId}
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </article>
        </EvidenceModal>
      )}
    </div>
  );
}

function TimelineCard({
  event,
  active,
  onFocus,
  onExpand,
  onCitationLink,
}: {
  event: TimelineEvent;
  active: boolean;
  onFocus: () => void;
  onExpand: () => void;
  onCitationLink: (docId: string) => void;
}): JSX.Element {
  const deadlineLabel = useMemo(() => {
    if (!event.motion_deadline) return null;
    return new Date(event.motion_deadline).toLocaleDateString();
  }, [event.motion_deadline]);

  return (
    <li>
      <article
        tabIndex={0}
        onFocus={onFocus}
        className={`timeline-card${active ? ' active' : ''}`}
        data-timeline-id={event.id}
        aria-current={active ? 'true' : undefined}
      >
        <header>
          <time dateTime={event.ts}>{new Date(event.ts).toLocaleString()}</time>
          <h4>{event.title}</h4>
          {typeof event.confidence === 'number' && (
            <span className="confidence">Confidence {(event.confidence * 100).toFixed(0)}%</span>
          )}
          {event.risk_band && (
            <span className={`risk-chip risk-chip--${event.risk_band}`}>
              {event.risk_band.toUpperCase()} risk
            </span>
          )}
        </header>
        <p>{event.summary}</p>
        <ProbabilityOverview event={event} compact />
        {event.entity_highlights.length > 0 && (
          <section>
            <h5>Entities</h5>
            <ul className="entity-tags">
              {event.entity_highlights.map((entity: EntityHighlight) => (
                <li key={`${event.id}-${entity.id}`}>{entity.label}</li>
              ))}
            </ul>
          </section>
        )}
        {event.relation_tags.length > 0 && (
          <section>
            <h5>Relations</h5>
            <ul className="relation-tags">
              {event.relation_tags.map((relation: RelationTag, index: number) => (
                <li key={`${event.id}-rel-${index}`}>
                  {relation.label} <span className="relation-detail">{relation.type}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
        {deadlineLabel && (
          <section className="timeline-deadline">
            <h5>Motion deadline</h5>
            <p>{deadlineLabel}</p>
          </section>
        )}
        <footer>
          <div className="timeline-card__footer">
            <div className="timeline-card__citations" aria-label="Citations">
              {event.citations.map((docId) => (
                <button
                  key={`${event.id}-${docId}`}
                  type="button"
                  onClick={() => onCitationLink(docId)}
                >
                  {docId}
                </button>
              ))}
            </div>
            <button type="button" onClick={onExpand} className="timeline-card__expand">
              View Details
            </button>
          </div>
        </footer>
      </article>
    </li>
  );
}

function groupByDay(events: TimelineEvent[]): { day: string; events: TimelineEvent[] }[] {
  const groups = new Map<string, TimelineEvent[]>();
  events.forEach((event) => {
    const day = event.ts.slice(0, 10);
    const bucket = groups.get(day) ?? [];
    bucket.push(event);
    groups.set(day, bucket);
  });
  return Array.from(groups.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, dayEvents]) => ({
      day: new Date(day).toLocaleDateString(),
      events: dayEvents.sort((left, right) => new Date(left.ts).getTime() - new Date(right.ts).getTime()),
    }));
}

function ProbabilityOverview({ event, compact }: { event: TimelineEvent; compact?: boolean }): JSX.Element | null {
  if (!event.outcome_probabilities?.length && !event.recommended_actions?.length && !event.risk_score)
    return null;

  const probabilities = event.outcome_probabilities ?? [];
  const actions = event.recommended_actions ?? [];

  return (
    <section className={`timeline-probability${compact ? ' timeline-probability--compact' : ''}`}>
      {probabilities.length > 0 && (
        <div className="timeline-probability__chart" aria-label="Outcome probability arcs">
          <ProbabilityArcs probabilities={probabilities} />
          <ul className="timeline-probability__legend">
            {probabilities.map((item) => (
              <li key={`${event.id}-${item.label}`}>
                <span className="legend-label">{item.label}</span>
                <span className="legend-value">{Math.round(item.probability * 100)}%</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {actions.length > 0 && (
        <div className="timeline-probability__actions">
          <h5>Recommended actions</h5>
          <ul>
            {actions.map((action, index) => (
              <li key={`${event.id}-action-${index}`}>{action}</li>
            ))}
          </ul>
        </div>
      )}
      {typeof event.risk_score === 'number' && (
        <p className="timeline-probability__score">Predicted risk score {(event.risk_score * 100).toFixed(0)}%</p>
      )}
    </section>
  );
}

function ProbabilityArcs({ probabilities }: { probabilities: OutcomeProbability[] }): JSX.Element {
  const radius = 32;
  const center = 40;
  const circumference = 2 * Math.PI * radius;
  let cumulative = 0;
  const palette = ['#ff6b6b', '#4dabf7', '#ffd43b'];

  return (
    <svg viewBox="0 0 80 80" className="probability-arcs" role="presentation">
      <circle className="probability-arcs__background" cx={center} cy={center} r={radius} />
      {probabilities.map((item, index) => {
        const value = Math.max(0, Math.min(item.probability, 1));
        const length = value * circumference;
        const dasharray = `${length} ${circumference - length}`;
        const rotation = (cumulative / circumference) * 360;
        cumulative += length;
        return (
          <circle
            key={`${item.label}-${index}`}
            className="probability-arcs__segment"
            cx={center}
            cy={center}
            r={radius}
            strokeDasharray={dasharray}
            transform={`rotate(${rotation - 90} ${center} ${center})`}
            data-index={index}
            style={{ stroke: palette[index % palette.length] }}
          />
        );
      })}
    </svg>
  );
}
