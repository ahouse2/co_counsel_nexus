import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Settings, Key, Cpu, Sliders, X, Check, AlertCircle, Loader2 } from 'lucide-react';
import { endpoints } from '../services/api';

interface SettingsPanelProps {
    isOpen: boolean;
    onClose: () => void;
}

type TabId = 'api-keys' | 'llm-config' | 'system' | 'advanced';

interface ProviderModel {
    model_id: string;
    display_name: string;
    context_window: number;
    capabilities: string[];
}

interface ProviderCatalogEntry {
    provider_id: string;
    display_name: string;
    capabilities: string[];
    models: ProviderModel[];
}

interface SettingsState {
    providers: {
        primary: string;
        secondary: string | null;
        defaults: Record<string, string>;
        available: ProviderCatalogEntry[];
    };
    credentials: {
        providers: Array<{ provider_id: string; has_api_key: boolean }>;
        services: Record<string, boolean>;
    };
    appearance: {
        theme: string;
    };
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({ isOpen, onClose }) => {
    const [activeTab, setActiveTab] = useState<TabId>('api-keys');
    const [settings, setSettings] = useState<SettingsState | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    // Form state
    const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
    const [primaryProvider, setPrimaryProvider] = useState('gemini');
    const [secondaryProvider, setSecondaryProvider] = useState<string | null>(null);
    const [defaultModels, setDefaultModels] = useState<Record<string, string>>({});
    const [theme, setTheme] = useState('system');
    const [courtlistenerToken, setCourtlistenerToken] = useState('');

    // Fetch settings on mount
    useEffect(() => {
        if (isOpen) {
            fetchSettings();
        }
    }, [isOpen]);

    const fetchSettings = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await endpoints.settings.get();
            const data = response.data;
            setSettings(data);

            // Populate form state
            setPrimaryProvider(data.providers?.primary || 'gemini');
            setSecondaryProvider(data.providers?.secondary || null);
            setDefaultModels(data.providers?.defaults || {});
            setTheme(data.appearance?.theme || 'system');

            // Initialize API keys state (empty - we don't receive actual keys)
            const keysState: Record<string, string> = {};
            data.credentials?.providers?.forEach((p: { provider_id: string }) => {
                keysState[p.provider_id] = '';
            });
            setApiKeys(keysState);
        } catch (err) {
            console.error('Failed to fetch settings:', err);
            setError('Failed to load settings. Using defaults.');
            // Set some defaults
            setSettings(null);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        setError(null);
        setSuccessMessage(null);

        try {
            // Build update payload
            const payload: any = {
                providers: {
                    primary: primaryProvider,
                    secondary: secondaryProvider,
                    defaults: defaultModels,
                },
                appearance: {
                    theme,
                },
                credentials: {
                    provider_api_keys: {},
                    courtlistener_token: courtlistenerToken || undefined,
                },
            };

            // Only include API keys that have been entered
            Object.entries(apiKeys).forEach(([provider, key]) => {
                if (key && key.trim()) {
                    payload.credentials.provider_api_keys[provider] = key;
                }
            });

            await endpoints.settings.update(payload);
            setSuccessMessage('Settings saved successfully!');
            setTimeout(() => setSuccessMessage(null), 3000);
        } catch (err) {
            console.error('Failed to save settings:', err);
            setError('Failed to save settings. Please try again.');
        } finally {
            setSaving(false);
        }
    };

    if (!isOpen) return null;

    const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
        { id: 'api-keys', label: 'API Keys', icon: <Key size={16} /> },
        { id: 'llm-config', label: 'LLM Config', icon: <Cpu size={16} /> },
        { id: 'system', label: 'System', icon: <Settings size={16} /> },
        { id: 'advanced', label: 'Advanced', icon: <Sliders size={16} /> },
    ];

    const availableProviders = settings?.providers?.available || [];

    const getModelsForProvider = (providerId: string): ProviderModel[] => {
        const provider = availableProviders.find(p => p.provider_id === providerId);
        return provider?.models || [];
    };

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-md flex items-center justify-center p-4"
                onClick={onClose}
            >
                <motion.div
                    initial={{ scale: 0.95, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.95, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="bg-slate-950 border border-cyan-500/30 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden shadow-[0_0_60px_rgba(0,240,255,0.15)]"
                    onClick={(e) => e.stopPropagation()}
                >
                    {/* Header */}
                    <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-cyan-500/10 rounded-lg">
                                <Settings className="w-5 h-5 text-cyan-400" />
                            </div>
                            <h2 className="text-xl font-semibold text-white">System Configuration</h2>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
                            title="Close settings"
                        >
                            <X className="w-5 h-5 text-slate-400" />
                        </button>
                    </div>

                    {/* Tab Bar */}
                    <div className="flex gap-1 px-6 py-3 border-b border-slate-800 bg-slate-900/50">
                        {tabs.map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === tab.id
                                    ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                                    : 'text-slate-400 hover:text-white hover:bg-slate-800'
                                    }`}
                            >
                                {tab.icon}
                                {tab.label}
                            </button>
                        ))}
                    </div>

                    {/* Content */}
                    <div className="p-6 overflow-y-auto max-h-[calc(90vh-180px)]">
                        {loading ? (
                            <div className="flex items-center justify-center py-12">
                                <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
                            </div>
                        ) : (
                            <>
                                {/* API Keys Tab */}
                                {activeTab === 'api-keys' && (
                                    <div className="space-y-6">
                                        <p className="text-slate-400 text-sm">
                                            Configure API keys for LLM providers and external services. Keys are encrypted and stored securely.
                                        </p>

                                        <div className="grid gap-4">
                                            {/* Gemini */}
                                            <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800">
                                                <div className="flex items-center justify-between mb-3">
                                                    <label className="text-sm font-medium text-white">Google Gemini API Key</label>
                                                    {settings?.credentials?.providers?.find(p => p.provider_id === 'gemini')?.has_api_key && (
                                                        <span className="flex items-center gap-1 text-xs text-green-400">
                                                            <Check size={12} /> Configured
                                                        </span>
                                                    )}
                                                </div>
                                                <input
                                                    type="password"
                                                    value={apiKeys['gemini'] || ''}
                                                    onChange={(e) => setApiKeys({ ...apiKeys, gemini: e.target.value })}
                                                    placeholder="Enter new key to update..."
                                                    className="w-full bg-black/50 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                                                />
                                            </div>

                                            {/* OpenAI */}
                                            <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800">
                                                <div className="flex items-center justify-between mb-3">
                                                    <label className="text-sm font-medium text-white">OpenAI API Key</label>
                                                    {settings?.credentials?.providers?.find(p => p.provider_id === 'openai')?.has_api_key && (
                                                        <span className="flex items-center gap-1 text-xs text-green-400">
                                                            <Check size={12} /> Configured
                                                        </span>
                                                    )}
                                                </div>
                                                <input
                                                    type="password"
                                                    value={apiKeys['openai'] || ''}
                                                    onChange={(e) => setApiKeys({ ...apiKeys, openai: e.target.value })}
                                                    placeholder="sk-..."
                                                    className="w-full bg-black/50 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                                                />
                                            </div>

                                            {/* Azure OpenAI */}
                                            <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800">
                                                <div className="flex items-center justify-between mb-3">
                                                    <label className="text-sm font-medium text-white">Azure OpenAI API Key</label>
                                                    {settings?.credentials?.providers?.find(p => p.provider_id === 'azure-openai')?.has_api_key && (
                                                        <span className="flex items-center gap-1 text-xs text-green-400">
                                                            <Check size={12} /> Configured
                                                        </span>
                                                    )}
                                                </div>
                                                <input
                                                    type="password"
                                                    value={apiKeys['azure-openai'] || ''}
                                                    onChange={(e) => setApiKeys({ ...apiKeys, 'azure-openai': e.target.value })}
                                                    placeholder="Enter Azure OpenAI key..."
                                                    className="w-full bg-black/50 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                                                />
                                            </div>

                                            {/* CourtListener */}
                                            <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800">
                                                <div className="flex items-center justify-between mb-3">
                                                    <label className="text-sm font-medium text-white">CourtListener API Token</label>
                                                    {settings?.credentials?.services?.courtlistener && (
                                                        <span className="flex items-center gap-1 text-xs text-green-400">
                                                            <Check size={12} /> Configured
                                                        </span>
                                                    )}
                                                </div>
                                                <input
                                                    type="password"
                                                    value={courtlistenerToken}
                                                    onChange={(e) => setCourtlistenerToken(e.target.value)}
                                                    placeholder="Enter CourtListener token..."
                                                    className="w-full bg-black/50 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                                                />
                                                <p className="mt-2 text-xs text-slate-500">Used for legal research and case law queries</p>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* LLM Config Tab */}
                                {activeTab === 'llm-config' && (
                                    <div className="space-y-6">
                                        <p className="text-slate-400 text-sm">
                                            Configure which LLM providers and models to use for different tasks.
                                        </p>

                                        <div className="grid gap-6">
                                            {/* Primary Provider */}
                                            <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800">
                                                <label className="block text-sm font-medium text-white mb-3">Primary Provider</label>
                                                <select
                                                    value={primaryProvider}
                                                    onChange={(e) => setPrimaryProvider(e.target.value)}
                                                    className="w-full bg-black/50 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white focus:border-cyan-500 focus:outline-none"
                                                    title="Select primary LLM provider"
                                                >
                                                    {availableProviders.map((provider) => (
                                                        <option key={provider.provider_id} value={provider.provider_id}>
                                                            {provider.display_name}
                                                        </option>
                                                    ))}
                                                </select>
                                            </div>

                                            {/* Secondary Provider */}
                                            <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800">
                                                <label className="block text-sm font-medium text-white mb-3">Secondary Provider (Fallback)</label>
                                                <select
                                                    value={secondaryProvider || ''}
                                                    onChange={(e) => setSecondaryProvider(e.target.value || null)}
                                                    className="w-full bg-black/50 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white focus:border-cyan-500 focus:outline-none"
                                                    title="Select secondary LLM provider"
                                                >
                                                    <option value="">None</option>
                                                    {availableProviders.map((provider) => (
                                                        <option key={provider.provider_id} value={provider.provider_id}>
                                                            {provider.display_name}
                                                        </option>
                                                    ))}
                                                </select>
                                            </div>

                                            {/* Default Chat Model */}
                                            <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800">
                                                <label className="block text-sm font-medium text-white mb-3">Default Chat Model</label>
                                                <select
                                                    value={defaultModels['chat'] || ''}
                                                    onChange={(e) => setDefaultModels({ ...defaultModels, chat: e.target.value })}
                                                    className="w-full bg-black/50 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white focus:border-cyan-500 focus:outline-none"
                                                    title="Select default chat model"
                                                >
                                                    {getModelsForProvider(primaryProvider)
                                                        .filter(m => m.capabilities.includes('chat'))
                                                        .map((model) => (
                                                            <option key={model.model_id} value={model.model_id}>
                                                                {model.display_name}
                                                            </option>
                                                        ))}
                                                </select>
                                            </div>

                                            {/* Default Embedding Model */}
                                            <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800">
                                                <label className="block text-sm font-medium text-white mb-3">Default Embedding Model</label>
                                                <select
                                                    value={defaultModels['embeddings'] || ''}
                                                    onChange={(e) => setDefaultModels({ ...defaultModels, embeddings: e.target.value })}
                                                    className="w-full bg-black/50 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white focus:border-cyan-500 focus:outline-none"
                                                    title="Select default embedding model"
                                                >
                                                    {getModelsForProvider(primaryProvider)
                                                        .filter(m => m.capabilities.includes('embeddings'))
                                                        .map((model) => (
                                                            <option key={model.model_id} value={model.model_id}>
                                                                {model.display_name}
                                                            </option>
                                                        ))}
                                                </select>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* System Tab */}
                                {activeTab === 'system' && (
                                    <div className="space-y-6">
                                        <p className="text-slate-400 text-sm">
                                            General system settings and preferences.
                                        </p>

                                        <div className="grid gap-4">
                                            {/* Theme */}
                                            <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800">
                                                <label className="block text-sm font-medium text-white mb-3">Interface Theme</label>
                                                <select
                                                    value={theme}
                                                    onChange={(e) => setTheme(e.target.value)}
                                                    className="w-full bg-black/50 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white focus:border-cyan-500 focus:outline-none"
                                                    title="Select interface theme"
                                                >
                                                    <option value="system">System (Auto)</option>
                                                    <option value="dark">Dark</option>
                                                    <option value="light">Light</option>
                                                </select>
                                            </div>

                                            {/* Telemetry Toggle */}
                                            <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800 flex items-center justify-between">
                                                <div>
                                                    <label className="block text-sm font-medium text-white">Telemetry</label>
                                                    <p className="text-xs text-slate-500 mt-1">Send anonymous usage data to improve the product</p>
                                                </div>
                                                <div className="w-12 h-6 bg-slate-700 rounded-full relative cursor-pointer opacity-50">
                                                    <div className="w-4 h-4 bg-slate-500 rounded-full absolute top-1 left-1" />
                                                </div>
                                            </div>

                                            {/* Voice Toggle */}
                                            <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800 flex items-center justify-between">
                                                <div>
                                                    <label className="block text-sm font-medium text-white">Voice Interface</label>
                                                    <p className="text-xs text-slate-500 mt-1">Enable voice commands and TTS responses</p>
                                                </div>
                                                <div className="w-12 h-6 bg-cyan-500/30 rounded-full relative cursor-pointer">
                                                    <div className="w-4 h-4 bg-cyan-400 rounded-full absolute top-1 right-1" />
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Advanced Tab */}
                                {activeTab === 'advanced' && (
                                    <div className="space-y-6">
                                        <p className="text-slate-400 text-sm">
                                            Advanced configuration for developers and power users.
                                        </p>

                                        <div className="grid gap-4">
                                            {/* Neo4j URI */}
                                            <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800">
                                                <label className="block text-sm font-medium text-white mb-3">Neo4j URI</label>
                                                <input
                                                    type="text"
                                                    defaultValue="neo4j://neo4j:7687"
                                                    className="w-full bg-black/50 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none font-mono"
                                                    disabled
                                                    title="Neo4j connection URI (read-only)"
                                                    aria-label="Neo4j URI"
                                                />
                                                <p className="mt-2 text-xs text-slate-500">Set via environment variables</p>
                                            </div>

                                            {/* Qdrant URL */}
                                            <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800">
                                                <label className="block text-sm font-medium text-white mb-3">Qdrant URL</label>
                                                <input
                                                    type="text"
                                                    defaultValue="http://qdrant:6333"
                                                    className="w-full bg-black/50 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none font-mono"
                                                    disabled
                                                    title="Qdrant connection URL (read-only)"
                                                    aria-label="Qdrant URL"
                                                />
                                                <p className="mt-2 text-xs text-slate-500">Set via environment variables</p>
                                            </div>

                                            {/* Info Box */}
                                            <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl">
                                                <div className="flex items-start gap-3">
                                                    <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                                                    <div>
                                                        <h4 className="text-sm font-medium text-amber-400">Environment Configuration</h4>
                                                        <p className="text-xs text-amber-200/70 mt-1">
                                                            Database connections and system paths are configured via environment variables in docker-compose.yml.
                                                            Restart containers after making changes.
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </>
                        )}
                    </div>

                    {/* Footer */}
                    <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-900/30">
                        <div className="text-sm">
                            {error && (
                                <span className="text-red-400 flex items-center gap-2">
                                    <AlertCircle size={14} /> {error}
                                </span>
                            )}
                            {successMessage && (
                                <span className="text-green-400 flex items-center gap-2">
                                    <Check size={14} /> {successMessage}
                                </span>
                            )}
                        </div>
                        <div className="flex gap-3">
                            <button
                                onClick={onClose}
                                className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSave}
                                disabled={saving}
                                className="px-6 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/50 text-cyan-400 rounded-lg text-sm font-medium transition-all disabled:opacity-50 flex items-center gap-2"
                            >
                                {saving && <Loader2 size={14} className="animate-spin" />}
                                Save Configuration
                            </button>
                        </div>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
};
