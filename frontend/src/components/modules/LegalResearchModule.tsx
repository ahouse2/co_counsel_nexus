import { useState, useEffect } from 'react';
import { Library, Search, BookOpen, Scale, Loader2, Lightbulb, ListChecks, ShieldAlert, Globe, Clock, Plus, Trash2, Play, CheckCircle, FileText, AlertTriangle } from 'lucide-react';
import { endpoints } from '../../services/api';


interface LegalTheory {
    cause: string;
    score: number;
    elements: { name: string; description: string }[];
    defenses: string[];
    indicators: string[];
    missing_elements: string[];
}

interface Monitor {
    monitor_id: string;
    monitor_type: 'keyword' | 'citation';
    value: string;
    check_interval_hours: number;
    last_check: string | null;
    last_results_count: number;
    enabled: boolean;
}

interface Trigger {
    trigger_id: string;
    source: string;
    query: string;
    frequency: 'daily' | 'on-demand';
    last_run: string | null;
    enabled: boolean;
}

interface LegalResearchModuleProps {
    caseId: string;
}

export function LegalResearchModule({ caseId }: LegalResearchModuleProps) {
    const [activeTab, setActiveTab] = useState<'research' | 'docket' | 'scraper' | 'advanced'>('research');

    // Legacy Research State
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<any[]>([]);
    const [theories, setTheories] = useState<LegalTheory[]>([]);
    const [searching, setSearching] = useState(false);
    const [generating, setGenerating] = useState(false);

    // New Research State
    const [monitors, setMonitors] = useState<Monitor[]>([]);
    const [triggers, setTriggers] = useState<Trigger[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Form States
    const [newMonitorType, setNewMonitorType] = useState<'keyword' | 'citation'>('keyword');
    const [newMonitorValue, setNewMonitorValue] = useState('');
    const [newScraperSource, setNewScraperSource] = useState('california_codes');
    const [newScraperQuery, setNewScraperQuery] = useState('');

    useEffect(() => {
        if (activeTab !== 'research') {
            fetchData();
        }
    }, [activeTab]);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            if (activeTab === 'docket') {
                const res = await endpoints.research.listMonitors();
                setMonitors(res.data);
            } else if (activeTab === 'scraper') {
                const res = await endpoints.research.listTriggers();
                setTriggers(res.data);
            }
        } catch (err: any) {
            setError(err.message || 'Failed to fetch data');
        } finally {
            setLoading(false);
        }
    };

    // --- Legacy Handlers ---
    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;
        setSearching(true);
        try {
            const response = await endpoints.agents.run(`Research: ${query}`, caseId);
            setResults([{
                id: 'res-1',
                citation: 'Agent Research Report',
                summary: response.data.result,
                relevance: 1.0
            }]);
        } catch (error) {
            console.error("Legal research failed:", error);
        } finally {
            setSearching(false);
        }
    };

    const handleGenerateTheories = async () => {
        setGenerating(true);
        try {
            const response = await endpoints.legalTheory.suggestions(caseId);
            setTheories(response.data);
        } catch (error) {
            console.error("Failed to generate theories:", error);
        } finally {
            setGenerating(false);
        }
    };

    // --- New Handlers ---
    const handleAddMonitor = async () => {
        if (!newMonitorValue) return;
        try {
            await endpoints.research.addMonitor({
                monitor_type: newMonitorType,
                value: newMonitorValue,
                requested_by: 'user',
                check_interval_hours: 6
            });
            setNewMonitorValue('');
            fetchData();
        } catch (err: any) {
            setError(err.message || 'Failed to add monitor');
        }
    };

    const handleDeleteMonitor = async (id: string) => {
        try {
            await endpoints.research.removeMonitor(id);
            fetchData();
        } catch (err: any) {
            setError(err.message || 'Failed to delete monitor');
        }
    };

    const handleExecuteMonitor = async (id: string) => {
        try {
            await endpoints.research.executeMonitor(id);
            fetchData();
        } catch (err: any) {
            setError(err.message || 'Failed to execute monitor');
        }
    };

    const handleAddTrigger = async () => {
        if (!newScraperQuery) return;
        try {
            await endpoints.research.addTrigger({
                source: newScraperSource,
                query: newScraperQuery,
                frequency: 'on-demand',
                requested_by: 'user'
            });
            setNewScraperQuery('');
            fetchData();
        } catch (err: any) {
            setError(err.message || 'Failed to add trigger');
        }
    };

    const handleDeleteTrigger = async (id: string) => {
        try {
            await endpoints.research.removeTrigger(id);
            fetchData();
        } catch (err: any) {
            setError(err.message || 'Failed to delete trigger');
        }
    };

    const handleExecuteTrigger = async (id: string) => {
        try {
            await endpoints.research.executeTrigger(id);
            fetchData();
        } catch (err: any) {
            setError(err.message || 'Failed to execute trigger');
        }
    };

    const handleManualScrape = async () => {
        if (!newScraperQuery) return;
        setLoading(true);
        try {
            await endpoints.research.manualScrape(newScraperSource, newScraperQuery);
            alert('Scrape completed and ingested!');
        } catch (err: any) {
            setError(err.message || 'Scrape failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full h-full flex flex-col p-8 text-halo-text overflow-y-auto custom-scrollbar bg-black/50">
            {/* Header & Tabs */}
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-halo-cyan/10 rounded-lg border border-halo-cyan/30 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                        <Library className="text-halo-cyan w-8 h-8" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider">Research Center</h2>
                        <p className="text-halo-muted text-sm">Autonomous Legal Research & Docket Watch</p>
                    </div>
                </div>

                <div className="flex bg-halo-card rounded-lg p-1 border border-halo-border">
                    <button
                        onClick={() => setActiveTab('research')}
                        className={`px-4 py-2 rounded-md flex items-center gap-2 transition-colors ${activeTab === 'research' ? 'bg-halo-cyan/20 text-halo-cyan border border-halo-cyan/30' : 'text-halo-muted hover:text-halo-text'
                            }`}
                    >
                        <Lightbulb className="w-4 h-4" />
                        Agent Research
                    </button>
                    <button
                        onClick={() => setActiveTab('docket')}
                        className={`px-4 py-2 rounded-md flex items-center gap-2 transition-colors ${activeTab === 'docket' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' : 'text-halo-muted hover:text-halo-text'
                            }`}
                    >
                        <Scale className="w-4 h-4" />
                        Docket Watch
                    </button>
                    <button
                        onClick={() => setActiveTab('scraper')}
                        className={`px-4 py-2 rounded-md flex items-center gap-2 transition-colors ${activeTab === 'scraper' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'text-halo-muted hover:text-halo-text'
                            }`}
                    >
                        <Globe className="w-4 h-4" />
                        Scraper
                    </button>
                    <button
                        onClick={() => setActiveTab('advanced')}
                        className={`px-4 py-2 rounded-md flex items-center gap-2 transition-colors ${activeTab === 'advanced' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'text-halo-muted hover:text-halo-text'
                            }`}
                    >
                        <ShieldAlert className="w-4 h-4" />
                        Advanced
                    </button>
                </div>
            </div>

            {/* Error Banner */}
            {error && (
                <div className="bg-red-900/20 border border-red-500/50 text-red-200 p-4 rounded-lg mb-6 flex items-center gap-3">
                    <AlertTriangle className="w-5 h-5" />
                    {error}
                </div>
            )}

            {/* --- TAB CONTENT --- */}

            {/* 1. AGENT RESEARCH (Legacy) */}
            {activeTab === 'research' && (
                <div className="animate-in fade-in duration-300">
                    <div className="flex justify-end mb-6">
                        <button
                            onClick={handleGenerateTheories}
                            disabled={generating}
                            className="flex items-center gap-2 px-4 py-2 bg-purple-500/10 border border-purple-500/30 rounded hover:bg-purple-500/20 text-purple-400 transition-colors disabled:opacity-50"
                        >
                            {generating ? <Loader2 className="animate-spin" size={16} /> : <Lightbulb size={16} />}
                            GENERATE THEORIES
                        </button>
                    </div>

                    {/* Search Bar */}
                    <div className="relative mb-12">
                        <form onSubmit={handleSearch}>
                            <Search className={`absolute left-5 top-5 w-6 h-6 transition-colors ${searching ? 'text-halo-cyan animate-pulse' : 'text-halo-muted'}`} />
                            <input
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Enter legal issue or fact pattern to find precedents..."
                                className="w-full bg-halo-card border border-halo-border rounded-xl pl-16 pr-4 py-5 text-lg focus:border-halo-cyan focus:ring-1 focus:ring-halo-cyan focus:outline-none transition-all shadow-[0_0_20px_rgba(0,0,0,0.3)] placeholder:text-halo-muted/50 text-halo-text"
                            />
                            {searching && (
                                <div className="absolute right-5 top-5">
                                    <Loader2 className="w-6 h-6 text-halo-cyan animate-spin" />
                                </div>
                            )}
                        </form>
                    </div>

                    {/* Theories Section */}
                    {theories.length > 0 && (
                        <div className="mb-12 space-y-6">
                            <h3 className="text-lg font-mono uppercase tracking-wide text-purple-400 flex items-center gap-2">
                                <Lightbulb size={20} /> Suggested Legal Theories
                            </h3>
                            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                                {theories.map((theory, idx) => (
                                    <div key={idx} className="halo-card border-purple-500/20 bg-purple-500/5 p-6 rounded-xl border">
                                        <div className="flex justify-between items-start mb-4">
                                            <h4 className="text-xl font-bold text-purple-300">{theory.cause}</h4>
                                            <div className="flex items-center gap-1 text-xs font-mono bg-purple-500/20 px-2 py-1 rounded border border-purple-500/30">
                                                <span>CONFIDENCE:</span>
                                                <span className="text-white">{(theory.score * 100).toFixed(0)}%</span>
                                            </div>
                                        </div>

                                        <div className="space-y-4 text-sm">
                                            <div>
                                                <div className="flex items-center gap-2 text-halo-muted mb-2 uppercase text-xs font-bold">
                                                    <ListChecks size={14} /> Elements
                                                </div>
                                                <ul className="space-y-2 pl-4 border-l border-purple-500/20">
                                                    {theory.elements.map((el, i) => (
                                                        <li key={i}>
                                                            <span className="text-purple-200 font-medium">{el.name}:</span> <span className="text-halo-muted">{el.description}</span>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>

                                            {theory.missing_elements && theory.missing_elements.length > 0 && (
                                                <div>
                                                    <div className="flex items-center gap-2 text-red-400 mb-2 uppercase text-xs font-bold">
                                                        <ShieldAlert size={14} /> Missing Elements
                                                    </div>
                                                    <ul className="list-disc list-inside text-red-300/80 pl-2">
                                                        {theory.missing_elements.map((m, i) => (
                                                            <li key={i}>{m}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Search Results */}
                    <div className="space-y-6">
                        {results.length > 0 ? (
                            results.map((result) => (
                                <div key={result.id} className="halo-card group hover:border-halo-cyan/50 transition-all p-6 rounded-xl border border-halo-border bg-halo-card">
                                    <div className="flex items-center gap-2 mb-3 text-halo-cyan">
                                        <Scale size={18} />
                                        <span className="font-mono text-sm font-bold uppercase tracking-wider">{result.citation}</span>
                                    </div>
                                    <div className="prose prose-invert prose-sm max-w-none">
                                        <div className="whitespace-pre-wrap leading-relaxed text-halo-text/90">{result.summary}</div>
                                    </div>
                                </div>
                            ))
                        ) : !theories.length && (
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 opacity-50">
                                <div className="halo-card flex flex-col items-center text-center p-6 border border-halo-border rounded-xl">
                                    <BookOpen size={32} className="text-halo-muted mb-4" />
                                    <h3 className="text-sm font-bold text-halo-text mb-2">Federal Cases</h3>
                                    <p className="text-xs text-halo-muted">Search across all federal circuits and Supreme Court rulings.</p>
                                </div>
                                <div className="halo-card flex flex-col items-center text-center p-6 border border-halo-border rounded-xl">
                                    <Scale size={32} className="text-halo-muted mb-4" />
                                    <h3 className="text-sm font-bold text-halo-text mb-2">State Statutes</h3>
                                    <p className="text-xs text-halo-muted">Access codified laws and regulatory frameworks.</p>
                                </div>
                                <div className="halo-card flex flex-col items-center text-center p-6 border border-halo-border rounded-xl">
                                    <Library size={32} className="text-halo-muted mb-4" />
                                    <h3 className="text-sm font-bold text-halo-text mb-2">Secondary Sources</h3>
                                    <p className="text-xs text-halo-muted">Law reviews, treatises, and expert commentary.</p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* 2. DOCKET WATCH */}
            {activeTab === 'docket' && (
                <div className="space-y-6 animate-in fade-in duration-300">
                    <div className="halo-card border-blue-500/20 bg-blue-500/5 p-6 rounded-xl border">
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-blue-400">
                            <Plus className="w-5 h-5" />
                            Add New Monitor
                        </h3>
                        <div className="flex gap-4 items-end">
                            <div className="w-48">
                                <label className="block text-sm text-halo-muted mb-1">Type</label>
                                <select
                                    value={newMonitorType}
                                    onChange={(e) => setNewMonitorType(e.target.value as any)}
                                    className="w-full bg-black border border-halo-border rounded-lg px-3 py-2 focus:ring-1 focus:ring-blue-500 outline-none text-halo-text"
                                    aria-label="Monitor Type"
                                >
                                    <option value="keyword">Keyword Search</option>
                                    <option value="citation">Citation Tracker</option>
                                </select>
                            </div>
                            <div className="flex-1">
                                <label className="block text-sm text-halo-muted mb-1">
                                    {newMonitorType === 'keyword' ? 'Keywords (e.g., "Google v. Oracle")' : 'Citation (e.g., "550 U.S. 544")'}
                                </label>
                                <input
                                    type="text"
                                    value={newMonitorValue}
                                    onChange={(e) => setNewMonitorValue(e.target.value)}
                                    placeholder={newMonitorType === 'keyword' ? "Enter search terms..." : "Enter case citation..."}
                                    className="w-full bg-black border border-halo-border rounded-lg px-3 py-2 focus:ring-1 focus:ring-blue-500 outline-none text-halo-text"
                                />
                            </div>
                            <button
                                onClick={handleAddMonitor}
                                disabled={!newMonitorValue || loading}
                                className="bg-blue-600/20 hover:bg-blue-600/40 border border-blue-500/50 text-blue-400 px-4 py-2 rounded-lg flex items-center gap-2 disabled:opacity-50 transition-colors"
                            >
                                <Plus className="w-4 h-4" />
                                Add Monitor
                            </button>
                        </div>
                    </div>

                    <div className="grid gap-4">
                        {monitors.map(m => (
                            <div key={m.monitor_id} className="halo-card border-halo-border bg-halo-card p-4 rounded-xl flex items-center justify-between hover:border-blue-500/30 transition-colors">
                                <div className="flex items-center gap-4">
                                    <div className={`p-3 rounded-lg ${m.monitor_type === 'keyword' ? 'bg-blue-900/20 text-blue-400' : 'bg-purple-900/20 text-purple-400'}`}>
                                        {m.monitor_type === 'keyword' ? <Search className="w-6 h-6" /> : <BookOpen className="w-6 h-6" />}
                                    </div>
                                    <div>
                                        <h4 className="font-medium text-lg text-halo-text">{m.value}</h4>
                                        <div className="flex items-center gap-4 text-sm text-halo-muted mt-1">
                                            <span className="flex items-center gap-1">
                                                <Clock className="w-3 h-3" />
                                                Every {m.check_interval_hours}h
                                            </span>
                                            {m.last_check && (
                                                <span className="flex items-center gap-1">
                                                    <CheckCircle className="w-3 h-3 text-emerald-500" />
                                                    Last check: {new Date(m.last_check).toLocaleString()}
                                                </span>
                                            )}
                                            {m.last_results_count > 0 && (
                                                <span className="text-emerald-400 font-medium">
                                                    {m.last_results_count} new opinions
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => handleExecuteMonitor(m.monitor_id)}
                                        className="p-2 hover:bg-halo-cyan/10 rounded-lg text-halo-muted hover:text-halo-cyan transition-colors"
                                        title="Run Now"
                                    >
                                        <Play className="w-5 h-5" />
                                    </button>
                                    <button
                                        onClick={() => handleDeleteMonitor(m.monitor_id)}
                                        className="p-2 hover:bg-red-900/20 rounded-lg text-halo-muted hover:text-red-400 transition-colors"
                                        title="Delete"
                                    >
                                        <Trash2 className="w-5 h-5" />
                                    </button>
                                </div>
                            </div>
                        ))}
                        {monitors.length === 0 && !loading && (
                            <div className="text-center py-12 text-halo-muted">
                                No active monitors. Add one above to start tracking cases.
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* 3. SCRAPER */}
            {activeTab === 'scraper' && (
                <div className="space-y-6 animate-in fade-in duration-300">
                    <div className="halo-card border-emerald-500/20 bg-emerald-500/5 p-6 rounded-xl border">
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-emerald-400">
                            <Globe className="w-5 h-5" />
                            Autonomous Scraper
                        </h3>
                        <div className="flex gap-4 items-end">
                            <div className="w-48">
                                <label className="block text-sm text-halo-muted mb-1">Source</label>
                                <select
                                    value={newScraperSource}
                                    onChange={(e) => setNewScraperSource(e.target.value)}
                                    className="w-full bg-black border border-halo-border rounded-lg px-3 py-2 focus:ring-1 focus:ring-emerald-500 outline-none text-halo-text"
                                    aria-label="Scraper Source"
                                >
                                    <option value="california_codes">California Codes</option>
                                    <option value="ecfr">eCFR (Federal Regs)</option>
                                </select>
                            </div>
                            <div className="flex-1">
                                <label className="block text-sm text-halo-muted mb-1">
                                    Query (e.g., "PEN 187" or "Title 12 Part 205")
                                </label>
                                <input
                                    type="text"
                                    value={newScraperQuery}
                                    onChange={(e) => setNewScraperQuery(e.target.value)}
                                    placeholder="Enter code section or search term..."
                                    className="w-full bg-black border border-halo-border rounded-lg px-3 py-2 focus:ring-1 focus:ring-emerald-500 outline-none text-halo-text"
                                />
                            </div>
                            <button
                                onClick={handleManualScrape}
                                disabled={!newScraperQuery || loading}
                                className="bg-emerald-600/20 hover:bg-emerald-600/40 border border-emerald-500/50 text-emerald-400 px-4 py-2 rounded-lg flex items-center gap-2 disabled:opacity-50 transition-colors"
                            >
                                <Play className="w-4 h-4" />
                                Scrape Now
                            </button>
                            <button
                                onClick={handleAddTrigger}
                                disabled={!newScraperQuery || loading}
                                className="bg-halo-card hover:bg-halo-border border border-halo-border text-halo-text px-4 py-2 rounded-lg flex items-center gap-2 disabled:opacity-50 transition-colors"
                            >
                                <Plus className="w-4 h-4" />
                                Save Trigger
                            </button>
                        </div>
                    </div>

                    <div className="grid gap-4">
                        {triggers.map(t => (
                            <div key={t.trigger_id} className="halo-card border-halo-border bg-halo-card p-4 rounded-xl flex items-center justify-between hover:border-emerald-500/30 transition-colors">
                                <div className="flex items-center gap-4">
                                    <div className="p-3 rounded-lg bg-emerald-900/20 text-emerald-400">
                                        <FileText className="w-6 h-6" />
                                    </div>
                                    <div>
                                        <h4 className="font-medium text-lg text-halo-text">{t.query}</h4>
                                        <div className="flex items-center gap-4 text-sm text-halo-muted mt-1">
                                            <span className="uppercase text-xs font-bold bg-halo-border px-2 py-0.5 rounded text-halo-text">
                                                {t.source.replace('_', ' ')}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Clock className="w-3 h-3" />
                                                {t.frequency}
                                            </span>
                                            {t.last_run && (
                                                <span className="flex items-center gap-1">
                                                    <CheckCircle className="w-3 h-3 text-emerald-500" />
                                                    Last run: {new Date(t.last_run).toLocaleString()}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => handleExecuteTrigger(t.trigger_id)}
                                        className="p-2 hover:bg-halo-cyan/10 rounded-lg text-halo-muted hover:text-halo-cyan transition-colors"
                                        title="Run Now"
                                    >
                                        <Play className="w-5 h-5" />
                                    </button>
                                    <button
                                        onClick={() => handleDeleteTrigger(t.trigger_id)}
                                        className="p-2 hover:bg-red-900/20 rounded-lg text-halo-muted hover:text-red-400 transition-colors"
                                        title="Delete"
                                    >
                                        <Trash2 className="w-5 h-5" />
                                    </button>
                                </div>
                            </div>
                        ))}
                        {triggers.length === 0 && !loading && (
                            <div className="text-center py-12 text-halo-muted">
                                No saved scraping triggers. Use "Scrape Now" for one-off tasks.
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* 4. ADVANCED TOOLS */}
            {activeTab === 'advanced' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 animate-in fade-in duration-300">
                    {/* Shepardizing Agent */}
                    <div className="halo-card border-halo-border bg-halo-card p-6 rounded-xl border">
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-amber-400">
                            <ShieldAlert className="w-5 h-5" />
                            Shepardizing Agent
                        </h3>
                        <p className="text-sm text-halo-muted mb-4">Check if a case citation is still good law.</p>
                        <div className="space-y-4">
                            <input
                                type="text"
                                placeholder="Enter citation (e.g., 347 U.S. 483)"
                                className="w-full bg-black border border-halo-border rounded-lg px-3 py-2 focus:ring-1 focus:ring-amber-500 outline-none text-halo-text"
                                id="shep-input"
                            />
                            <button
                                onClick={async () => {
                                    const input = (document.getElementById('shep-input') as HTMLInputElement).value;
                                    if (!input) return;
                                    setLoading(true);
                                    try {
                                        const res = await endpoints.research.shepardizeCase(input);
                                        alert(`Status: ${res.data.status}\nReasoning: ${res.data.reasoning}`);
                                    } catch (e: any) {
                                        setError(e.message);
                                    } finally {
                                        setLoading(false);
                                    }
                                }}
                                disabled={loading}
                                className="w-full bg-amber-600/20 hover:bg-amber-600/40 border border-amber-500/50 text-amber-400 px-4 py-2 rounded-lg flex items-center justify-center gap-2 disabled:opacity-50 transition-colors"
                            >
                                {loading ? <Loader2 className="animate-spin w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
                                Check Citation
                            </button>
                        </div>
                    </div>

                    {/* Judge Profiler */}
                    <div className="halo-card border-halo-border bg-halo-card p-6 rounded-xl border">
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-pink-400">
                            <Scale className="w-5 h-5" />
                            Judge Profiler
                        </h3>
                        <p className="text-sm text-halo-muted mb-4">Analyze ruling tendencies and judicial philosophy.</p>
                        <div className="space-y-4">
                            <input
                                type="text"
                                placeholder="Judge Name"
                                className="w-full bg-black border border-halo-border rounded-lg px-3 py-2 focus:ring-1 focus:ring-pink-500 outline-none text-halo-text"
                                id="judge-name"
                            />
                            <input
                                type="text"
                                placeholder="Jurisdiction"
                                className="w-full bg-black border border-halo-border rounded-lg px-3 py-2 focus:ring-1 focus:ring-pink-500 outline-none text-halo-text"
                                id="judge-jur"
                            />
                            <button
                                onClick={async () => {
                                    const name = (document.getElementById('judge-name') as HTMLInputElement).value;
                                    const jur = (document.getElementById('judge-jur') as HTMLInputElement).value;
                                    if (!name || !jur) return;
                                    setLoading(true);
                                    try {
                                        const res = await endpoints.research.profileJudge(name, jur);
                                        alert(`Judge: ${res.data.judge_name}\nBio: ${res.data.biography}`);
                                    } catch (e: any) {
                                        setError(e.message);
                                    } finally {
                                        setLoading(false);
                                    }
                                }}
                                disabled={loading}
                                className="w-full bg-pink-600/20 hover:bg-pink-600/40 border border-pink-500/50 text-pink-400 px-4 py-2 rounded-lg flex items-center justify-center gap-2 disabled:opacity-50 transition-colors"
                            >
                                {loading ? <Loader2 className="animate-spin w-4 h-4" /> : <Search className="w-4 h-4" />}
                                Generate Profile
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}


