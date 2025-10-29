import { useMemo } from 'react';
import { useQueryContext } from '@/context/QueryContext';
import { TimelineEvent } from '@/types';

export function DocumentViewerPanel(): JSX.Element {
  const { activeCitation, setActiveCitation, timelineEvents } = useQueryContext();

  const relatedEvents = useMemo((): TimelineEvent[] => {
    if (!activeCitation) return [];
    return timelineEvents.filter((event) => event.citations.includes(activeCitation.docId));
  }, [activeCitation, timelineEvents]);

  if (!activeCitation) {
    return (
      <section className="document-viewer" aria-label="Document viewer">
        <div className="document-viewer__empty" role="status">
          <h3>Select a citation to preview evidence</h3>
          <p>Choose any cited source from the chat, timeline, or documents list to open it here.</p>
        </div>
      </section>
    );
  }

  const { title, docId, span, uri, entities } = activeCitation;

  return (
    <section className="document-viewer" aria-label="Document viewer" aria-live="polite">
      <header className="document-viewer__header">
        <div>
          <p className="document-viewer__label">Document</p>
          <h3>{title ?? docId}</h3>
        </div>
        <div className="document-viewer__actions">
          <button type="button" onClick={() => setActiveCitation(null)}>
            Clear
          </button>
          {uri && (
            <a href={uri} target="_blank" rel="noopener noreferrer">
              Open Original
            </a>
          )}
        </div>
      </header>
      <article className="document-viewer__body">
        <p className="document-viewer__excerpt">{span}</p>
        {entities && entities.length > 0 && (
          <section className="document-viewer__entities">
            <h4>Entities</h4>
            <ul>
              {entities.map((entity) => (
                <li key={entity.id}>
                  <span>{entity.label}</span>
                  <span className="entity-type">{entity.type}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
        {relatedEvents.length > 0 && (
          <section className="document-viewer__timeline">
            <h4>Appears In Timeline</h4>
            <ul>
              {relatedEvents.map((event) => (
                <li key={event.id}>
                  <a href="#timeline" onClick={() => window.dispatchEvent(new CustomEvent('focus-timeline-event', { detail: event.id }))}>
                    {event.title}
                  </a>
                  <time dateTime={event.ts}>{new Date(event.ts).toLocaleString()}</time>
                </li>
              ))}
            </ul>
          </section>
        )}
      </article>
    </section>
  );
}
