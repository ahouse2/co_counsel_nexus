
import { useId } from 'react';

export const sections = [
  { id: 'chat', label: 'Co-Counsel' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'documents', label: 'Evidence' },
  { id: 'trial-university', label: 'Trial University' },
  { id: 'mock-court', label: 'Mock Trial' },
  { id: 'design-system', label: 'Design System' },
  { id: 'dev-team', label: 'Dev Team' },
] as const;

export type SectionId = (typeof sections)[number]['id'];

type SidebarProps = {
  activeSection: SectionId;
  setActiveSection: (section: SectionId) => void;
  panelId: string;
};

export function Sidebar({ activeSection, setActiveSection, panelId }: SidebarProps): JSX.Element {
  const tabsId = useId();

  return (
    <aside className="cinematic-nav ds-nav-cinematic" role="navigation" aria-labelledby={tabsId}>
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
              className={`ds-btn-accent ${activeSection === section.id ? 'active' : ''}`}
              onClick={() => setActiveSection(section.id)}
            >
              <span className="tab-glow" aria-hidden />
              {section.label}
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
