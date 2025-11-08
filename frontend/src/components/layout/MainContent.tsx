
import { DevTeamSection } from '@/components/dev-team';
import { CinematicMetrics } from '@/components/CinematicMetrics';
import { EvidenceUploadZone } from '@/components/evidence/EvidenceUploadZone';
import { GraphExplorerPanel } from '@/components/graph-explorer/GraphExplorerPanel';
import { TrialUniversityPanel } from '@/components/trial-university/TrialUniversityPanel';
import { MockTrialArenaPanel } from '@/components/mock-trial/MockTrialArenaPanel';
import { CinematicDesignSystemDemo } from '@/components/CinematicDesignSystemDemo';
import { SectionId } from './Sidebar';

type MainContentProps = {
  activeSection: SectionId;
  panelId: string;
  tabsId: string;
};

export function MainContent({ activeSection, panelId, tabsId }: MainContentProps): JSX.Element {
  return (
    <main id="main" className="cinematic-main ds-main-cinematic" role="main">
      <CinematicMetrics />
      <section
        id={`${panelId}-chat`}
        role="tabpanel"
        aria-labelledby={`${tabsId}-chat`}
        hidden={activeSection !== 'chat'}
      >
        <div className="panel-shell ds-card-cinematic p-6">
          <header>
            <h2>Co-Counsel Chat</h2>
            <p>AI-powered legal assistant with real-time collaboration.</p>
          </header>
          <div className="mt-4 p-4 bg-background-panel rounded-lg border border-border-subtle">
            <p className="text-text-secondary">Chat interface would be implemented here...</p>
          </div>
        </div>
      </section>
      <section
        id={`${panelId}-timeline`}
        role="tabpanel"
        aria-labelledby={`${tabsId}-timeline`}
        hidden={activeSection !== 'timeline'}
      >
        <div className="panel-shell ds-card-cinematic p-6">
          <header>
            <h2>Timeline Pulse</h2>
            <p>Adaptive chronology with neon event markers and deposition overlays.</p>
          </header>
          <div className="mt-4 p-4 bg-background-panel rounded-lg border border-border-subtle">
            <p className="text-text-secondary">Timeline view would be implemented here...</p>
          </div>
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
        <div className="panel-shell ds-card-cinematic p-6">
          <header>
            <h2>Evidence Citations</h2>
            <p>Source-grounded references with privilege posture indicators.</p>
          </header>
          <div className="mt-4 p-4 bg-background-panel rounded-lg border border-border-subtle">
            <p className="text-text-secondary">Citation panel would be implemented here...</p>
          </div>
        </div>
      </section>
      <section
        id={`${panelId}-trial-university`}
        role="tabpanel"
        aria-labelledby={`${tabsId}-trial-university`}
        hidden={activeSection !== 'trial-university'}
      >
        <TrialUniversityPanel />
        <div className="panel-shell ds-card-cinematic p-6">
          <header>
            <h2>Knowledge Hub</h2>
            <p>Cinematic dossiers, briefs, and AI explainers ready for court.</p>
          </header>
          <div className="mt-4 p-4 bg-background-panel rounded-lg border border-border-subtle">
            <p className="text-text-secondary">Knowledge hub would be implemented here...</p>
          </div>
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
        id={`${panelId}-design-system`}
        role="tabpanel"
        aria-labelledby={`${tabsId}-design-system`}
        hidden={activeSection !== 'design-system'}
      >
        <div className="panel-shell ds-card-cinematic p-6">
          <header>
            <h2>Cinematic Design System</h2>
            <p>Premium dark-mode UI components and design guidelines.</p>
          </header>
          <CinematicDesignSystemDemo />
        </div>
      </section>
      <section
        id={`${panelId}-dev-team`}
        role="tabpanel"
        aria-labelledby={`${tabsId}-dev-team`}
        hidden={activeSection !== 'dev-team'}
      >
        <div className="panel-shell ds-card-cinematic p-6">
          <header>
            <h2>Dev Team Workspace</h2>
            <p>Velocity dashboards, backlog intelligence, and agent orchestration.</p>
          </header>
          <DevTeamSection />
        </div>
      </section>
    </main>
  );
}
