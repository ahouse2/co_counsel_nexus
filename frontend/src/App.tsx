import { useEffect, useId, useState } from 'react';
import { ChatView } from '@/components/ChatView';
import { CitationPanel } from '@/components/CitationPanel';
import { TimelineView } from '@/components/TimelineView';
import { KnowledgeHub } from '@/components/KnowledgeHub';
import { OfflineIndicator } from '@/components/OfflineIndicator';
import { ThemeToggle } from '@/components/ThemeToggle';
import { RetrievalSettings } from '@/components/RetrievalSettings';
import { SimulationWorkbench } from '@/components/simulation/SimulationWorkbench';
import { DevTeamSection } from '@/components/dev-team';
import { useQueryContext } from '@/context/QueryContext';

const sections = [
  { id: 'chat', label: 'Chat' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'documents', label: 'Documents' },
  { id: 'trial-university', label: 'Trial University' },
  { id: 'mock-court', label: 'Mock Court' },
  { id: 'dev-team', label: 'Dev Team' },
] as const;

type SectionId = (typeof sections)[number]['id'];

function App(): JSX.Element {
  const [activeSection, setActiveSection] = useState<SectionId>('chat');
  const tabsId = useId();
  const panelId = useId();
  const { refreshTimelineOnDemand } = useQueryContext();

  useEffect((): (() => void) => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const listener = (): void => setActiveSection((current) => current);
    media.addEventListener('change', listener);
    return () => {
      media.removeEventListener('change', listener);
    };
  }, []);

  useEffect((): void => {
    if (activeSection === 'timeline') {
      refreshTimelineOnDemand();
    }
  }, [activeSection, refreshTimelineOnDemand]);

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent): void => {
      const target = event.target as HTMLElement | null;
      if (target) {
        const tagName = target.tagName;
        if (
          target.isContentEditable ||
          tagName === 'INPUT' ||
          tagName === 'TEXTAREA' ||
          tagName === 'SELECT' ||
          target.closest('input, textarea, select, [contenteditable]:not([contenteditable="false"])')
        ) {
          return;
        }
      }
      if (event.altKey || event.metaKey || event.ctrlKey) return;
      if (event.key.toLowerCase() === 'g') {
        event.preventDefault();
        setActiveSection('timeline');
      }
      if (event.key.toLowerCase() === 'd') {
        event.preventDefault();
        setActiveSection('documents');
      }
    };
    window.addEventListener('keydown', handleShortcut);
    return () => {
      window.removeEventListener('keydown', handleShortcut);
    };
  }, []);

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
            <p className="subtitle">Cinematic discovery with verified provenance</p>
          </div>
        </div>
        <div className="header-controls">
          <RetrievalSettings />
          <ThemeToggle />
          <OfflineIndicator />
        </div>
      </header>
      <div className="app-body">
        <nav className="app-sidebar" role="navigation" aria-labelledby={tabsId}>
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
            id={`${panelId}-documents`}
            role="tabpanel"
            aria-labelledby={`${tabsId}-documents`}
            hidden={activeSection !== 'documents'}
          >
            <CitationPanel />
          </section>
          <section
            id={`${panelId}-trial-university`}
            role="tabpanel"
            aria-labelledby={`${tabsId}-trial-university`}
            hidden={activeSection !== 'trial-university'}
          >
            <KnowledgeHub />
          </section>
          <section
            id={`${panelId}-mock-court`}
            role="tabpanel"
            aria-labelledby={`${tabsId}-mock-court`}
            hidden={activeSection !== 'mock-court'}
          >
            <SimulationWorkbench />
          </section>
          <section
            id={`${panelId}-dev-team`}
            role="tabpanel"
            aria-labelledby={`${tabsId}-dev-team`}
            hidden={activeSection !== 'dev-team'}
          >
            <DevTeamSection />
          </section>
        </main>
      </div>
      <footer className="app-footer" role="contentinfo">
        <p>
          Streaming answers powered by Co-Counsel telemetry. Shortcuts: <kbd>Ctrl</kbd> + <kbd>Enter</kbd> to send, <kbd>g</kbd> for
          timeline, <kbd>d</kbd> for documents, <kbd>n</kbd>/<kbd>p</kbd> to step through events.
        </p>
      </footer>
    </div>
  );
}

export default App;
