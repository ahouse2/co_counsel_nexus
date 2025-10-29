import { useEffect, useMemo, useState } from 'react';
import { EvidenceModal } from '@/components/EvidenceModal';
import { useQueryContext } from '@/context/QueryContext';
import { Citation, EntityHighlight, RelationTag, TimelineEvent } from '@/types';

export function TimelineView(): JSX.Element {
  const {
    timelineEvents,
    timelineMeta,
    timelineLoading,
    loadMoreTimeline,
    timelineEntityFilter,
    setTimelineEntityFilter,
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
            </header>
            <p>{expandedEvent.summary}</p>
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
