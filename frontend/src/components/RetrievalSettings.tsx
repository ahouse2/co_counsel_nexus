import { useMemo } from 'react';
import { useQueryContext } from '@/context/QueryContext';

const MODE_OPTIONS: Record<
  'precision' | 'economy',
  {
    label: string;
    description: string;
    embedding: string;
    reranker: string;
    mode: 'precision' | 'recall';
  }
> = {
  precision: {
    label: 'Precision',
    description: 'Max quality answers using hybrid fusion with cross-encoder reranking.',
    embedding: 'OpenAI text-embedding-3-large',
    reranker: 'Cross-encoder reranker enabled',
    mode: 'precision',
  },
  economy: {
    label: 'Economy',
    description: 'Lower cost responses via distilled MiniLM embeddings and lexical fusion.',
    embedding: 'Local MiniLM-L6 embeddings',
    reranker: 'Cross-encoder disabled (lexical fallback)',
    mode: 'recall',
  },
};

export function RetrievalSettings(): JSX.Element {
  const { retrievalMode, setRetrievalMode } = useQueryContext();
  const activeProfile = useMemo<'precision' | 'economy'>(() => {
    return retrievalMode === 'precision' ? 'precision' : 'economy';
  }, [retrievalMode]);

  return (
    <section className="retrieval-settings" aria-label="Retrieval mode settings">
      <header>
        <span className="retrieval-label">Answer mode</span>
      </header>
      <div role="radiogroup" aria-label="Answer operating mode" className="retrieval-mode-toggle">
        {Object.entries(MODE_OPTIONS).map(([key, option]) => {
          const profileKey = key as 'precision' | 'economy';
          const checked = activeProfile === profileKey;
          return (
            <label key={profileKey} className={checked ? 'active' : ''}>
              <input
                type="radio"
                name="retrieval-mode"
                value={profileKey}
                checked={checked}
                onChange={() => setRetrievalMode(option.mode)}
              />
              <span className="mode-label">{option.label}</span>
            </label>
          );
        })}
      </div>
      <dl className="retrieval-details">
        <dt>Embedding</dt>
        <dd>{MODE_OPTIONS[activeProfile].embedding}</dd>
        <dt>Model pipeline</dt>
        <dd>{MODE_OPTIONS[activeProfile].reranker}</dd>
        <dt>Notes</dt>
        <dd>{MODE_OPTIONS[activeProfile].description}</dd>
      </dl>
    </section>
  );
}

export default RetrievalSettings;
