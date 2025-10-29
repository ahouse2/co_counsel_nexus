import { useEffect, useState } from 'react';

const STORAGE_KEY = 'cocounsel-theme';

type Theme = 'light' | 'dark';

export function ThemeToggle(): JSX.Element {
  const [theme, setTheme] = useState<Theme>(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY) as Theme | null;
    if (stored) return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', theme);
    window.localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  return (
    <button
      type="button"
      className="theme-toggle"
      aria-pressed={theme === 'dark'}
      onClick={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))}
    >
      {theme === 'dark' ? '🌙 Dark' : '☀️ Light'}
    </button>
  );
}
