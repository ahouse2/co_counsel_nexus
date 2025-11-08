
import { OfflineIndicator } from '@/components/OfflineIndicator';
import { ThemeToggle } from '@/components/ThemeToggle';
import { SettingsPanel } from '@/components/SettingsPanel';

export function Header(): JSX.Element {
  return (
    <header className="cinematic-header ds-header-cinematic" role="banner">
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
  );
}
