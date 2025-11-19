import { useState, useEffect } from 'react';
import type { JSX, ReactNode } from 'react';
import { OfflineIndicator } from '@/components/OfflineIndicator';
import { SettingsPanel } from '@/components/SettingsPanel';
import { SlideOutMenu } from '@/components/SlideOutMenu';
import { LoginModal } from '@/components/LoginModal';
import { CaseSelection } from '@/components/CaseSelection';
import { useCaseContext } from '@/context/CaseContext';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps): JSX.Element {
  const [menuOpen, setMenuOpen] = useState(false);
  const [showLogin, setShowLogin] = useState(false);
  const [showCaseSelect, setShowCaseSelect] = useState(false);
  const { caseId, setCaseId } = useCaseContext();

  useEffect(() => {
    const token = localStorage.getItem('cc_token');
    if (!token) {
      setShowLogin(true);
    }
  }, []);

  const handleLogin = (token: string) => {
    localStorage.setItem('cc_token', token);
    setShowLogin(false);
    if (!caseId) {
      setShowCaseSelect(true);
    }
  };

  return (
    <div className="halo-shell">
      <div className="halo-gradient" aria-hidden />
      <div className="halo-noise" aria-hidden />
      <SlideOutMenu open={menuOpen} onClose={() => setMenuOpen(false)} />

      <LoginModal open={showLogin} onLogin={handleLogin} />
      <CaseSelection open={showCaseSelect} onSelect={(id) => {
        setCaseId(id);
        setShowCaseSelect(false);
      }} />

      <header className="halo-top-bar">
        <button
          type="button"
          className="menu-trigger"
          onClick={() => setMenuOpen(true)}
        >
          <span className="menu-symbol" aria-hidden>
            <span />
            <span />
            <span />
          </span>
          <span>Menu</span>
        </button>
        <div className="halo-topline">
          <p className="eyebrow">AI-Driven Legal Discovery</p>
          <h1>Neuro-SAN Litigation OS</h1>
        </div>
        <div className="halo-case-meta">
          <button onClick={() => setShowCaseSelect(true)} className="text-right hover:text-cyan-400 transition-colors">
            <span className="block text-xs text-zinc-500">Active Matter</span>
            <strong className="block">{caseId ? `Case ${caseId}` : 'Select Case...'}</strong>
          </button>
        </div>
      </header>

      <main className="halo-stage cinematic-main">{children}</main>

      <footer className="halo-bottom-bar">
        <div className="halo-links">
          <button type="button">Contact Us</button>
          <button type="button">Diagnostics</button>
          <button type="button">System Logs</button>
        </div>
      </footer>

      <div className="halo-settings">
        <SettingsPanel triggerVariant="icon" triggerLabel="Open settings" />
      </div>

      <OfflineIndicator />
    </div>
  );
}
