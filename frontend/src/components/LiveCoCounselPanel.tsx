import { ChatView } from '@/components/ChatView';

const highlights = [
  {
    id: 'callout-1',
    title: 'Transcript Flag: Witness 04',
    excerpt: 'Potential contradiction with email archive – highlight added to timeline.',
  },
  {
    id: 'callout-2',
    title: 'AI Strategy Pulse',
    excerpt: 'Recommend revisiting damages narrative: new graph insight surfaced.',
  },
];

export function LiveCoCounselPanel(): JSX.Element {
  return (
    <section className="co-counsel" aria-labelledby="co-counsel-title">
      <header>
        <div>
          <h2 id="co-counsel-title">Live Co-Counsel Chat</h2>
          <p>Streaming captions, transcript playback, and AI partner callouts in a neon holoscreen.</p>
        </div>
        <div className="co-counsel-actions">
          <button type="button">Filter transcript</button>
          <button type="button" className="accent">
            Export annotated PDF
          </button>
        </div>
      </header>
      <div className="co-counsel-body">
        <div className="co-counsel-chat">
          <ChatView />
        </div>
        <aside className="co-counsel-highlights" aria-label="Highlights">
          <h3>Highlights</h3>
          <ul>
            {highlights.map((highlight) => (
              <li key={highlight.id}>
                <strong>{highlight.title}</strong>
                <p>{highlight.excerpt}</p>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </section>
  );
}
