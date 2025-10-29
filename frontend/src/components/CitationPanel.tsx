import { useMemo, useState } from 'react';
import { EvidenceModal } from '@/components/EvidenceModal';
import { useQueryContext } from '@/context/QueryContext';
import { Citation, EntityHighlight } from '@/types';

export function CitationPanel(): JSX.Element {
  const { citations, activeCitation, setActiveCitation } = useQueryContext();
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);

  const filtered = useMemo<Citation[]>(() => {
    const query = search.trim().toLowerCase();
    if (!query) return citations;
    return citations.filter((citation) => {
      const terms = [citation.docId, citation.span, citation.title].filter(
        (value): value is string => Boolean(value)
      );
      return terms.some((value) => value.toLowerCase().includes(query));
    });
  }, [citations, search]);

  const openCitation = (citation: Citation): void => {
    setActiveCitation(citation);
    setShowModal(true);
  };

  return (
    <div className="citation-panel">
      <header>
        <h2>Cited Evidence</h2>
        <p className="panel-subtitle">Traceable provenance for the latest assistant answer.</p>
        <label htmlFor="citation-search" className="sr-only">
          Search citations
        </label>
        <input
          id="citation-search"
          type="search"
          placeholder="Search by document, snippet, or entity"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </header>
      <ul className="citation-grid" role="list">
        {filtered.map((citation) => (
          <li key={citation.docId}>
            <article className="citation-card">
              <header>
                <h3>{citation.title ?? citation.docId}</h3>
                {citation.confidence !== undefined && citation.confidence !== null && (
                  <span className="confidence">Confidence {(citation.confidence * 100).toFixed(0)}%</span>
                )}
              </header>
              <p>{citation.span}</p>
              {citation.entities && citation.entities.length > 0 && (
                <ul className="entity-tags">
                  {citation.entities.map((entity: EntityHighlight) => (
                    <li key={`${citation.docId}-${entity.id}`}>{entity.label}</li>
                  ))}
                </ul>
              )}
              <div className="citation-actions">
                {citation.uri && (
                  <a href={citation.uri} target="_blank" rel="noopener noreferrer">
                    Open Source
                  </a>
                )}
                <button type="button" onClick={() => openCitation(citation)}>
                  Pop-out Panel
                </button>
              </div>
            </article>
          </li>
        ))}
        {filtered.length === 0 && <p role="status">No citations found.</p>}
      </ul>
      {showModal && activeCitation && (
        <EvidenceModal
          title={`Evidence for ${activeCitation.docId}`}
          onClose={() => {
            setShowModal(false);
            setActiveCitation(null);
          }}
        >
          <article>
            <h3>{activeCitation.title ?? activeCitation.docId}</h3>
            <p>{activeCitation.span}</p>
            {activeCitation.entities && activeCitation.entities.length > 0 && (
              <section>
                <h4>Entities</h4>
                <ul>
                  {activeCitation.entities.map((entity: EntityHighlight) => (
                    <li key={entity.id}>
                      {entity.label} <span className="entity-type">{entity.type}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
            {activeCitation.uri && (
              <p>
                <a href={activeCitation.uri} target="_blank" rel="noopener noreferrer">
                  Open original document
                </a>
              </p>
            )}
          </article>
        </EvidenceModal>
      )}
    </div>
  );
}
