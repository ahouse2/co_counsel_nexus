import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  ReactNode,
} from 'react';
import {
  AppearanceSettingsUpdatePayload,
  ProviderCatalogEntry,
  ProviderModelInfo,
  SettingsSnapshot,
  SettingsUpdatePayload,
  ThemePreference,
} from '@/types';
import {
  fetchModelCatalog,
  fetchSettingsSnapshot,
  updateSettingsSnapshot,
} from '@/utils/apiClient';

const THEME_STORAGE_KEY = 'cocounsel-theme';

type ResolvedModel = {
  providerId: string;
  model: ProviderModelInfo;
};

type ResolvedModels = {
  chat?: ResolvedModel;
  embeddings?: ResolvedModel;
  vision?: ResolvedModel;
};

type SettingsContextValue = {
  loading: boolean;
  saving: boolean;
  error?: string;
  settings: SettingsSnapshot | null;
  catalog: ProviderCatalogEntry[];
  resolvedModels: ResolvedModels;
  themePreference: ThemePreference;
  refresh: () => Promise<void>;
  updateSettings: (payload: SettingsUpdatePayload) => Promise<void>;
  setThemePreference: (theme: ThemePreference) => Promise<void>;
};

const SettingsContext = createContext<SettingsContextValue | undefined>(undefined);

function getInitialTheme(): ThemePreference {
  if (typeof window === 'undefined') {
    return 'system';
  }
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY) as ThemePreference | null;
  return stored ?? 'system';
}

function applyTheme(preference: ThemePreference): void {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  let effective = preference;
  if (preference === 'system') {
    if (typeof window !== 'undefined') {
      effective = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    } else {
      effective = 'light';
    }
  }
  root.setAttribute('data-theme', effective);
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(THEME_STORAGE_KEY, preference);
  }
}

function formatError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  try {
    return JSON.stringify(error);
  } catch {
    return 'Unknown error.';
  }
}

export function SettingsProvider({ children }: { children: ReactNode }): JSX.Element {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [settings, setSettings] = useState<SettingsSnapshot | null>(null);
  const [catalog, setCatalog] = useState<ProviderCatalogEntry[]>([]);
  const [themePreference, setThemePreferenceState] = useState<ThemePreference>(getInitialTheme);

  useEffect(() => {
    applyTheme(themePreference);
  }, [themePreference]);

  useEffect(() => {
    if (!settings) return;
    const serverTheme = settings.appearance.theme;
    if (serverTheme && serverTheme !== themePreference) {
      setThemePreferenceState(serverTheme);
    }
  }, [settings, themePreference]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const listener = () => {
      if (themePreference === 'system') {
        applyTheme('system');
      }
    };
    media.addEventListener('change', listener);
    return () => media.removeEventListener('change', listener);
  }, [themePreference]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [snapshot, catalogEntries] = await Promise.all([
        fetchSettingsSnapshot(),
        fetchModelCatalog().catch(() => null),
      ]);
      setSettings(snapshot);
      if (catalogEntries && catalogEntries.length > 0) {
        setCatalog(catalogEntries);
      } else {
        setCatalog(snapshot.providers.available ?? []);
      }
      setError(undefined);
    } catch (err) {
      setError(formatError(err));
      setSettings(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const updateSettings = useCallback(
    async (payload: SettingsUpdatePayload) => {
      setSaving(true);
      try {
        const snapshot = await updateSettingsSnapshot(payload);
        setSettings(snapshot);
        setCatalog((entries) => {
          if (entries.length === 0) {
            return snapshot.providers.available ?? [];
          }
          return entries;
        });
        setError(undefined);
      } catch (err) {
        setError(formatError(err));
        throw err;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  const setThemePreference = useCallback(
    async (theme: ThemePreference) => {
      const previous = themePreference;
      setThemePreferenceState(theme);
      const payload: SettingsUpdatePayload = { appearance: { theme } as AppearanceSettingsUpdatePayload };
      try {
        const snapshot = await updateSettingsSnapshot(payload);
        setSettings(snapshot);
        setError(undefined);
      } catch (err) {
        setThemePreferenceState(previous);
        setError(formatError(err));
        throw err;
      }
    },
    [themePreference]
  );

  const catalogSource = catalog.length > 0 ? catalog : settings?.providers.available ?? [];

  const resolvedModels: ResolvedModels = useMemo(() => {
    const resolve = (modelId?: string): ResolvedModel | undefined => {
      if (!modelId) return undefined;
      for (const entry of catalogSource) {
        const model = entry.models.find((item) => item.id === modelId);
        if (model) {
          return { providerId: entry.id, model };
        }
      }
      return undefined;
    };
    const defaults = settings?.providers.defaults ?? {};
    return {
      chat: resolve(defaults.chat),
      embeddings: resolve(defaults.embeddings),
      vision: resolve(defaults.vision),
    };
  }, [catalogSource, settings?.providers.defaults]);

  const value: SettingsContextValue = {
    loading,
    saving,
    error,
    settings,
    catalog: catalogSource,
    resolvedModels,
    themePreference,
    refresh,
    updateSettings,
    setThemePreference,
  };

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettingsContext(): SettingsContextValue {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettingsContext must be used within SettingsProvider');
  }
  return context;
}

