import { Link, useLocation } from 'react-router-dom';
import { OfflineIndicator } from '@/components/OfflineIndicator';
import { ThemeToggle } from '@/components/ThemeToggle';
import { SettingsPanel } from '@/components/SettingsPanel';
import { useQueryContext } from '@/context/QueryContext'; // Assuming this context is still needed here

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const { queryMode, setQueryMode } = useQueryContext(); // Assuming this context is still needed here

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="cinematic-app">
      <div className="cinematic-backdrop" />
      <header className="cinematic-header">
        <div className="header-brand">
          <div className="brand-emblem">
            <i className="fa-solid fa-gavel" />
          </div>
          <div>
            <p className="eyebrow">Co-Counsel</p>
            <h1>AI Legal Discovery</h1>
          </div>
        </div>
        <div className="header-actions">
          <ThemeToggle />
          <SettingsPanel />
        </div>
      </header>

      <div className="cinematic-body">
        <nav className="cinematic-nav">
          <ul>
            <li>
              <Link
                to="/dashboard"
                className={isActive('/dashboard') || isActive('/') ? 'active' : ''}
              >
                <i className="fa-solid fa-house" />
                <span>Dashboard</span>
                <span className="tab-glow" />
              </Link>
            </li>
            <li>
              <Link
                to="/upload"
                className={isActive('/upload') ? 'active' : ''}
              >
                <i className="fa-solid fa-cloud-arrow-up" />
                <span>Upload Evidence</span>
                <span className="tab-glow" />
              </Link>
            </li>
            <li>
              <Link
                to="/graph"
                className={isActive('/graph') ? 'active' : ''}
              >
                <i className="fa-solid fa-diagram-project" />
                <span>Graph Explorer</span>
                <span className="tab-glow" />
              </Link>
            </li>
            <li>
              <Link
                to="/trial-university"
                className={isActive('/trial-university') ? 'active' : ''}
              >
                <i className="fa-solid fa-graduation-cap" />
                <span>Trial University</span>
                <span className="tab-glow" />
              </Link>
            </li>
            <li>
              <Link
                to="/mock-trial"
                className={isActive('/mock-trial') ? 'active' : ''}
              >
                <i className="fa-solid fa-gavel" />
                <span>Mock Trial Arena</span>
                <span className="tab-glow" />
              </Link>
            </li>
            <li>
              <Link
                to="/live-chat"
                className={isActive('/live-chat') ? 'active' : ''}
              >
                <i className="fa-solid fa-comments" />
                <span>Live Co-Counsel Chat</span>
                <span className="tab-glow" />
              </Link>
            </li>
            <li>
              <Link
                to="/design-system"
                className={isActive('/design-system') ? 'active' : ''}
              >
                <i className="fa-solid fa-palette" />
                <span>Design System</span>
                <span className="tab-glow" />
              </Link>
            </li>
            <li>
              <Link
                to="/dev-team"
                className={isActive('/dev-team') ? 'active' : ''}
              >
                <i className="fa-solid fa-users-gear" />
                <span>Dev Team</span>
                <span className="tab-glow" />
              </Link>
            </li>
            {/* Add a link for Forensics Report - this will likely be dynamic, so a placeholder for now */}
            <li>
              <Link
                to="/forensics/exampleCase/opposition_documents/exampleDoc" // Placeholder link
                className={location.pathname.startsWith('/forensics') ? 'active' : ''}
              >
                <i className="fa-solid fa-magnifying-glass-chart" />
                <span>Forensics Report</span>
                <span className="tab-glow" />
              </Link>
            </li>
          </ul>
        </nav>

        <main className="cinematic-main">
          {children}
        </main>
      </div>

      <footer className="cinematic-footer">
        <p>
          Co-Counsel AI &copy; 2025 | Powered by{' '}
          <kbd>Google Gemini & Project Veritas</kbd>
        </p>
      </footer>
      <OfflineIndicator />
    </div>
  );
}