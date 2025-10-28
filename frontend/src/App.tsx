import { useEffect, useId, useState } from 'react';
import { ChatView } from '@/components/ChatView';
import { CitationPanel } from '@/components/CitationPanel';
import { TimelineView } from '@/components/TimelineView';
import { OfflineIndicator } from '@/components/OfflineIndicator';
import { ThemeToggle } from '@/components/ThemeToggle';
import { useQueryContext } from '@/context/QueryContext';

const sections = [
  { id: 'chat', label: 'Chat' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'citations', label: 'Citations' },
] as const;

type SectionId = (typeof sections)[number]['id'];

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

function App(): JSX.Element {
  const [activeSection, setActiveSection] = useState<SectionId>('chat');
  const tabsId = useId();
  const panelId = useId();
  const { refreshTimelineOnDemand } = useQueryContext();

  useEffect((): (() => void) => {
    const listener = (): void => setActiveSection((current) => current);
    prefersReducedMotion.addEventListener('change', listener);
    return () => {
      prefersReducedMotion.removeEventListener('change', listener);
    };
  }, []);

  useEffect((): void => {
    if (activeSection === 'timeline') {
      refreshTimelineOnDemand();
    }
  }, [activeSection, refreshTimelineOnDemand]);

  return (
    <div className="app-shell" data-section={activeSection}>
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <header className="app-header" role="banner">
        <div className="brand">
          <span aria-hidden="true" className="brand-mark">
            ⚖️
          </span>
          <div>
            <h1>Co-Counsel Workspace</h1>
            <p className="subtitle">Conversational intelligence with provenance</p>
          </div>
        </div>
        <div className="header-controls">
          <ThemeToggle />
          <OfflineIndicator />
        </div>
      </header>
      <nav className="app-nav" role="navigation" aria-labelledby={tabsId}>
        <h2 id={tabsId} className="sr-only">
          Workspace sections
        </h2>
        <ul role="tablist" aria-controls={panelId}>
          {sections.map((section) => (
            <li key={section.id} role="presentation">
              <button
                type="button"
                role="tab"
                id={`${tabsId}-${section.id}`}
                aria-controls={`${panelId}-${section.id}`}
                aria-selected={activeSection === section.id}
                className={activeSection === section.id ? 'active' : ''}
                onClick={() => setActiveSection(section.id)}
              >
                {section.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>
      <main id="main" className="app-main" role="main">
        <section
          id={`${panelId}-chat`}
          role="tabpanel"
          aria-labelledby={`${tabsId}-chat`}
          hidden={activeSection !== 'chat'}
        >
          <ChatView />
        </section>
        <section
          id={`${panelId}-timeline`}
          role="tabpanel"
          aria-labelledby={`${tabsId}-timeline`}
          hidden={activeSection !== 'timeline'}
        >
          <TimelineView />
        </section>
        <section
          id={`${panelId}-citations`}
          role="tabpanel"
          aria-labelledby={`${tabsId}-citations`}
          hidden={activeSection !== 'citations'}
        >
          <CitationPanel />
        </section>
      </main>
      <footer className="app-footer" role="contentinfo">
        <p>
          Streaming answers powered by Co-Counsel telemetry. Keyboard shortcuts: <kbd>Ctrl</kbd> + <kbd>Enter</kbd> to send,{' '}
          <kbd>g</kbd> to toggle timeline, <kbd>n</kbd>/<kbd>p</kbd> to step through events.
        </p>
      </footer>
    </div>
  );
}

export default App;
