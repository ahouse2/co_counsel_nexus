import { useEffect, useMemo, useState } from 'react';
import { useQueryContext } from '@/context/QueryContext';
import { EntityHighlight, RelationTag, TimelineEvent } from '@/types';

export function TimelineView(): JSX.Element {
  const {
    timelineEvents,
    timelineMeta,
    timelineLoading,
    loadMoreTimeline,
    timelineEntityFilter,
    setTimelineEntityFilter,
  } = useQueryContext();
  const [activeIndex, setActiveIndex] = useState(0);
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
      </header>
      <div className="timeline-summary" role="status" aria-live="polite">
        Rendering {timelineEvents.length} events {timelineMeta?.has_more ? 'with more available' : ''}
      </div>
      <ol className="timeline-groups" aria-live="polite">
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
    </div>
  );
}

function TimelineCard({ event, active, onFocus }: { event: TimelineEvent; active: boolean; onFocus: () => void }): JSX.Element {
  return (
    <li>
      <article
        tabIndex={0}
        onFocus={onFocus}
        className={`timeline-card${active ? ' active' : ''}`}
        aria-current={active ? 'true' : undefined}
      >
        <header>
          <time dateTime={event.ts}>{new Date(event.ts).toLocaleString()}</time>
          <h4>{event.title}</h4>
          {typeof event.confidence === 'number' && (
            <span className="confidence">Confidence {(event.confidence * 100).toFixed(0)}%</span>
          )}
        </header>
        <p>{event.summary}</p>
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
        <footer>
          <small>{event.citations.join(', ')}</small>
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
