import { useEffect, useId, useState } from 'react';
import { CitationPanel } from '@/components/CitationPanel';
import { TimelineView } from '@/components/TimelineView';
import { KnowledgeHub } from '@/components/KnowledgeHub';
import { OfflineIndicator } from '@/components/OfflineIndicator';
import { ThemeToggle } from '@/components/ThemeToggle';
import { SettingsPanel } from '@/components/SettingsPanel';
import { DevTeamSection } from '@/components/dev-team';
import { CinematicMetrics } from '@/components/CinematicMetrics';
import { EvidenceUploadZone } from '@/components/EvidenceUploadZone';
import { GraphExplorerPanel } from '@/components/GraphExplorerPanel';
import { TrialUniversityPanel } from '@/components/TrialUniversityPanel';
import { LiveCoCounselPanel } from '@/components/LiveCoCounselPanel';
import { MockTrialArenaPanel } from '@/components/MockTrialArenaPanel';
import { useQueryContext } from '@/context/QueryContext';

const sections = [
  { id: 'chat', label: 'Co-Counsel' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'documents', label: 'Evidence' },
  { id: 'trial-university', label: 'Trial University' },
  { id: 'mock-court', label: 'Mock Trial' },
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
    <div className="cinematic-app" data-section={activeSection}>
      <div className="cinematic-backdrop" aria-hidden />
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <header className="cinematic-header" role="banner">
        <div className="header-brand">
          <span aria-hidden className="brand-emblem">
            ⚖️
          </span>
          <div>
            <p className="eyebrow">F1-grade litigation command center</p>
            <h1>Co-Counsel Nexus</h1>
            <p className="hero-subtitle">AI-amplified discovery, trial prep, and evidence mastery.</p>
          </div>
        </div>
        <div className="header-actions">
          <SettingsPanel />
          <ThemeToggle />
          <OfflineIndicator />
        </div>
      </header>
      <div className="cinematic-body">
        <aside className="cinematic-nav" role="navigation" aria-labelledby={tabsId}>
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
                  <span className="tab-glow" aria-hidden />
                  {section.label}
                </button>
              </li>
            ))}
          </ul>
        </aside>
        <main id="main" className="cinematic-main" role="main">
          <CinematicMetrics />
          <section
            id={`${panelId}-chat`}
            role="tabpanel"
            aria-labelledby={`${tabsId}-chat`}
            hidden={activeSection !== 'chat'}
          >
            <LiveCoCounselPanel />
          </section>
          <section
            id={`${panelId}-timeline`}
            role="tabpanel"
            aria-labelledby={`${tabsId}-timeline`}
            hidden={activeSection !== 'timeline'}
          >
            <div className="panel-shell">
              <header>
                <h2>Timeline Pulse</h2>
                <p>Adaptive chronology with neon event markers and deposition overlays.</p>
              </header>
              <TimelineView />
            </div>
          </section>
          <section
            id={`${panelId}-documents`}
            role="tabpanel"
            aria-labelledby={`${tabsId}-documents`}
            hidden={activeSection !== 'documents'}
          >
            <EvidenceUploadZone />
            <GraphExplorerPanel />
            <div className="panel-shell">
              <header>
                <h2>Evidence Citations</h2>
                <p>Source-grounded references with privilege posture indicators.</p>
              </header>
              <CitationPanel />
            </div>
          </section>
          <section
            id={`${panelId}-trial-university`}
            role="tabpanel"
            aria-labelledby={`${tabsId}-trial-university`}
            hidden={activeSection !== 'trial-university'}
          >
            <TrialUniversityPanel />
            <div className="panel-shell">
              <header>
                <h2>Knowledge Hub</h2>
                <p>Cinematic dossiers, briefs, and AI explainers ready for court.</p>
              </header>
              <KnowledgeHub />
            </div>
          </section>
          <section
            id={`${panelId}-mock-court`}
            role="tabpanel"
            aria-labelledby={`${tabsId}-mock-court`}
            hidden={activeSection !== 'mock-court'}
          >
            <MockTrialArenaPanel />
          </section>
          <section
            id={`${panelId}-dev-team`}
            role="tabpanel"
            aria-labelledby={`${tabsId}-dev-team`}
            hidden={activeSection !== 'dev-team'}
          >
            <div className="panel-shell">
              <header>
                <h2>Dev Team Workspace</h2>
                <p>Velocity dashboards, backlog intelligence, and agent orchestration.</p>
              </header>
              <DevTeamSection />
            </div>
          </section>
        </main>
      </div>
      <footer className="cinematic-footer" role="contentinfo">
        <p>
          Streaming answers powered by Co-Counsel telemetry. Shortcuts: <kbd>Ctrl</kbd> + <kbd>Enter</kbd> to send, <kbd>g</kbd> for
          timeline, <kbd>d</kbd> for evidence, <kbd>n</kbd>/<kbd>p</kbd> to step through events.
        </p>
      </footer>
    </div>
  );
}

export default App;
