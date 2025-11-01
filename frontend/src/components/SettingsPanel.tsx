import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { useSettingsContext } from '@/context/SettingsContext';
import { ProviderCatalogEntry, ThemePreference } from '@/types';

type TabId = 'providers' | 'credentials' | 'research' | 'appearance';

const TABS: { id: TabId; label: string }[] = [
  { id: 'providers', label: 'Providers' },
  { id: 'credentials', label: 'Credentials' },
  { id: 'research', label: 'Research Tools' },
  { id: 'appearance', label: 'Appearance' },
];

function capabilityModels(
  provider: ProviderCatalogEntry | undefined,
  capability: 'chat' | 'embeddings' | 'vision'
) {
  if (!provider) return [];
  return provider.models.filter((model) => model.capabilities.includes(capability));
}

export function SettingsPanel(): JSX.Element {
  const {
    settings,
    catalog,
    updateSettings,
    themePreference,
    setThemePreference,
    loading,
    saving,
    error,
  } = useSettingsContext();
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>('providers');
  const [primaryProvider, setPrimaryProvider] = useState('');
  const [secondaryProvider, setSecondaryProvider] = useState('');
  const [chatModel, setChatModel] = useState('');
  const [embeddingModel, setEmbeddingModel] = useState('');
  const [visionModel, setVisionModel] = useState('');
  const [providerKeys, setProviderKeys] = useState<Record<string, string>>({});
  const [keysToClear, setKeysToClear] = useState<Record<string, boolean>>({});
  const [courtListenerToken, setCourtListenerToken] = useState('');
  const [clearCourtListener, setClearCourtListener] = useState(false);
  const [researchToken, setResearchToken] = useState('');
  const [clearResearchToken, setClearResearchToken] = useState(false);

  const providerCatalog = catalog.length > 0 ? catalog : settings?.providers.available ?? [];

  useEffect(() => {
    if (!settings) return;
    setPrimaryProvider(settings.providers.primary ?? '');
    setSecondaryProvider(settings.providers.secondary ?? '');
    const defaults = settings.providers.defaults ?? {};
    setChatModel(defaults['chat'] ?? '');
    setEmbeddingModel(defaults['embeddings'] ?? '');
    setVisionModel(defaults['vision'] ?? '');
    setProviderKeys({});
    setKeysToClear({});
    setCourtListenerToken('');
    setClearCourtListener(false);
    setResearchToken('');
    setClearResearchToken(false);
  }, [settings]);

  useEffect(() => {
    if (!open) return;
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open]);

  const providerStatus = useMemo(() => {
    const map = new Map<string, boolean>();
    settings?.credentials.providers.forEach((entry) => {
      map.set(entry.provider_id, entry.has_api_key);
    });
    return map;
  }, [settings?.credentials.providers]);

  const serviceStatus = settings?.credentials.services ?? {};

  const selectedPrimary = providerCatalog.find((entry) => entry.id === primaryProvider);
  const selectedSecondary = providerCatalog.find((entry) => entry.id === secondaryProvider);

  const ensureModelSelection = useCallback(
    (provider: ProviderCatalogEntry | undefined, capability: 'chat' | 'embeddings' | 'vision', current: string) => {
      if (!provider) return current;
      const models = capabilityModels(provider, capability);
      if (models.length === 0) {
        return '';
      }
      if (current && models.some((model) => model.id === current)) {
        return current;
      }
      return models[0].id;
    },
    []
  );

  useEffect(() => {
    setChatModel((current) => ensureModelSelection(selectedPrimary, 'chat', current));
  }, [ensureModelSelection, selectedPrimary]);

  useEffect(() => {
    setEmbeddingModel((current) => ensureModelSelection(selectedPrimary, 'embeddings', current));
  }, [ensureModelSelection, selectedPrimary]);

  useEffect(() => {
    setVisionModel((current) => ensureModelSelection(selectedPrimary, 'vision', current));
  }, [ensureModelSelection, selectedPrimary]);

  const handleProvidersSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    if (!primaryProvider) {
      return;
    }
    await updateSettings({
      providers: {
        primary: primaryProvider,
        secondary: secondaryProvider ? secondaryProvider : null,
        defaults: {
          chat: chatModel || null,
          embeddings: embeddingModel || null,
          vision: visionModel || null,
        },
      },
    });
  };

  const handleCredentialsSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    const apiKeys: Record<string, string | null> = {};
    Object.entries(providerKeys).forEach(([id, value]) => {
      if (value && value.trim().length > 0) {
        apiKeys[id] = value.trim();
      }
    });
    Object.entries(keysToClear).forEach(([id, remove]) => {
      if (remove) {
        apiKeys[id] = null;
      }
    });
    if (Object.keys(apiKeys).length === 0) {
      return;
    }
    await updateSettings({
      credentials: {
        provider_api_keys: apiKeys,
      },
    });
    setProviderKeys({});
    setKeysToClear({});
  };

  const handleResearchSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    const credentials: Record<string, string | null> = {};
    let hasUpdate = false;
    if (clearCourtListener || courtListenerToken.trim().length > 0) {
      credentials.courtlistener_token = clearCourtListener ? null : courtListenerToken.trim();
      hasUpdate = true;
    }
    if (clearResearchToken || researchToken.trim().length > 0) {
      credentials.research_browser_api_key = clearResearchToken ? null : researchToken.trim();
      hasUpdate = true;
    }
    if (!hasUpdate) {
      return;
    }
    await updateSettings({
      credentials: credentials,
    });
    setCourtListenerToken('');
    setResearchToken('');
    setClearCourtListener(false);
    setClearResearchToken(false);
  };

  const handleThemeChange = (value: ThemePreference) => {
    void setThemePreference(value);
  };

  const providerTab = (
    <form className="settings-form" onSubmit={handleProvidersSubmit}>
      <fieldset disabled={saving || loading}>
        <legend className="sr-only">Provider selection</legend>
        <label>
          Primary provider
          <select value={primaryProvider} onChange={(event) => setPrimaryProvider(event.target.value)}>
            {providerCatalog.map((entry) => (
              <option key={entry.id} value={entry.id}>
                {entry.display_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Secondary provider
          <select value={secondaryProvider} onChange={(event) => setSecondaryProvider(event.target.value)}>
            <option value="">None</option>
            {providerCatalog
              .filter((entry) => entry.id !== primaryProvider)
              .map((entry) => (
                <option key={entry.id} value={entry.id}>
                  {entry.display_name}
                </option>
              ))}
          </select>
        </label>
        <label>
          Chat model
          <select value={chatModel} onChange={(event) => setChatModel(event.target.value)}>
            {capabilityModels(selectedPrimary, 'chat').map((model) => (
              <option key={model.id} value={model.id}>
                {model.display_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Embedding model
          <select value={embeddingModel} onChange={(event) => setEmbeddingModel(event.target.value)}>
            {capabilityModels(selectedPrimary, 'embeddings').map((model) => (
              <option key={model.id} value={model.id}>
                {model.display_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Vision model
          <select value={visionModel} onChange={(event) => setVisionModel(event.target.value)}>
            {capabilityModels(selectedPrimary, 'vision').map((model) => (
              <option key={model.id} value={model.id}>
                {model.display_name}
              </option>
            ))}
          </select>
        </label>
        <div className="form-actions">
          <button type="submit" disabled={saving}>
            Save provider preferences
          </button>
        </div>
      </fieldset>
    </form>
  );

  const credentialsTab = (
    <form className="settings-form" onSubmit={handleCredentialsSubmit}>
      <fieldset disabled={saving || loading}>
        <legend className="sr-only">Provider credentials</legend>
        {providerCatalog.map((entry) => (
          <div key={entry.id} className="credentials-field">
            <label>
              {entry.display_name} API key
              <input
                type="password"
                placeholder={providerStatus.get(entry.id) ? 'Stored' : 'Enter API key'}
                value={providerKeys[entry.id] ?? ''}
                onChange={(event) =>
                  setProviderKeys((current) => ({ ...current, [entry.id]: event.target.value }))
                }
              />
            </label>
            {providerStatus.get(entry.id) && (
              <button
                type="button"
                className="link-button"
                onClick={() =>
                  setKeysToClear((current) => ({ ...current, [entry.id]: !current[entry.id] }))
                }
              >
                {keysToClear[entry.id] ? 'Restore' : 'Remove stored key'}
              </button>
            )}
          </div>
        ))}
        <div className="form-actions">
          <button type="submit" disabled={saving}>
            Save credentials
          </button>
        </div>
      </fieldset>
    </form>
  );

  const researchTab = (
    <form className="settings-form" onSubmit={handleResearchSubmit}>
      <fieldset disabled={saving || loading}>
        <legend className="sr-only">Research integrations</legend>
        <label>
          CourtListener token
          <input
            type="password"
            placeholder={serviceStatus.courtlistener ? 'Stored' : 'Enter token'}
            value={courtListenerToken}
            onChange={(event) => setCourtListenerToken(event.target.value)}
          />
        </label>
        {serviceStatus.courtlistener && (
          <button
            type="button"
            className="link-button"
            onClick={() => setClearCourtListener((current) => !current)}
          >
            {clearCourtListener ? 'Keep stored token' : 'Remove stored token'}
          </button>
        )}
        <label>
          Research browser API key
          <input
            type="password"
            placeholder={serviceStatus.research_browser ? 'Stored' : 'Enter API key'}
            value={researchToken}
            onChange={(event) => setResearchToken(event.target.value)}
          />
        </label>
        {serviceStatus.research_browser && (
          <button
            type="button"
            className="link-button"
            onClick={() => setClearResearchToken((current) => !current)}
          >
            {clearResearchToken ? 'Keep stored key' : 'Remove stored key'}
          </button>
        )}
        <div className="form-actions">
          <button type="submit" disabled={saving}>
            Save research credentials
          </button>
        </div>
      </fieldset>
    </form>
  );

  const appearanceTab = (
    <form className="settings-form" onSubmit={(event) => event.preventDefault()}>
      <fieldset disabled={saving || loading}>
        <legend className="sr-only">Theme preference</legend>
        <div className="radio-group">
          {(['system', 'light', 'dark'] as ThemePreference[]).map((value) => (
            <label key={value} className={themePreference === value ? 'active' : ''}>
              <input
                type="radio"
                name="theme-preference"
                value={value}
                checked={themePreference === value}
                onChange={() => handleThemeChange(value)}
              />
              {value === 'system' ? 'Match system' : value === 'light' ? 'Light' : 'Dark'}
            </label>
          ))}
        </div>
      </fieldset>
    </form>
  );

  const renderTab = () => {
    switch (activeTab) {
      case 'providers':
        return providerTab;
      case 'credentials':
        return credentialsTab;
      case 'research':
        return researchTab;
      case 'appearance':
        return appearanceTab;
      default:
        return null;
    }
  };

  return (
    <div className="settings-panel">
      <button
        type="button"
        className="settings-trigger"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        ⚙ Settings
      </button>
      {open && (
        <div className="settings-surface" role="dialog" aria-modal="false">
          <header className="settings-header">
            <h2>Application settings</h2>
            {error ? <p className="settings-error">{error}</p> : null}
          </header>
          <div className="settings-body">
            <nav className="settings-tabs" aria-label="Settings categories">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  className={activeTab === tab.id ? 'active' : ''}
                  onClick={() => setActiveTab(tab.id)}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
            <div className="settings-content">{renderTab()}</div>
          </div>
        </div>
      )}
    </div>
  );
}
