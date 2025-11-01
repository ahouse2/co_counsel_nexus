import { useMemo } from 'react';
import { useSettingsContext } from '@/context/SettingsContext';

function resolveTheme(preference: string): 'light' | 'dark' {
  if (preference === 'system') {
    if (typeof window !== 'undefined') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'light';
  }
  return preference === 'dark' ? 'dark' : 'light';
}

export function ThemeToggle(): JSX.Element {
  const { themePreference, setThemePreference, saving } = useSettingsContext();
  const resolved = useMemo(() => resolveTheme(themePreference), [themePreference]);

  const handleToggle = (): void => {
    const next = resolved === 'dark' ? 'light' : 'dark';
    void setThemePreference(next);
  };

  return (
    <button
      type="button"
      className="theme-toggle"
      aria-pressed={resolved === 'dark'}
      onClick={handleToggle}
      disabled={saving}
    >
      {resolved === 'dark' ? '🌙 Dark' : '☀️ Light'}
    </button>
  );
}
