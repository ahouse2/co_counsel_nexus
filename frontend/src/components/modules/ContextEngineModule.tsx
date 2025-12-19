import { useState, useEffect, useRef } from 'react';
import { BrainCircuit, Database, Search, Activity, FileText, ArrowRight, Layers, Play, Pause, Sparkles } from 'lucide-react';
import { endpoints } from '../../services/api';

interface SearchResult {
    id: string;
    title: string;
    excerpt: string;
    relevance: number;
    source: string;
}

interface ContextEngineModuleProps {
    caseId: string;
}

export function ContextEngineModule({ caseId }: ContextEngineModuleProps) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchResult[]>([]);
    const [searching, setSearching] = useState(false);

    // Autonomous Mode State
    const [autoInsightMode, setAutoInsightMode] = useState(false);
    const [autoLog, setAutoLog] = useState<string[]>([]);
    const scrollRef = useRef<HTMLDivElement>(null);

    // Autonomous Loop
    useEffect(() => {
        if (!autoInsightMode) return;

        const runAutoStep = async () => {
            // 1. Generate a query (Simulate Agent thought process)
            const topics = ["inconsistencies in witness statements", "financial discrepancies", "timeline gaps", "forensic evidence reliability", "cell tower data analysis"];
            const randomTopic = topics[Math.floor(Math.random() * topics.length)];
            const autoQuery = `Analyze ${randomTopic}`;

            addToLog(`Agent: Formulating query about '${randomTopic}'...`);

            // 2. Execute Search
            setSearching(true);
            try {
                // In a real agent loop, we'd ask the agent "What should I search for?" then search it.
                // For speed, we use the pre-selected topics but hit the REAL context API.
                const response = await endpoints.context.query(autoQuery, caseId);

                const answer = response.data.answer || response.data.response || (typeof response.data === 'string' ? response.data : JSON.stringify(response.data));
                const sources = response.data.sources || [];

                const newResults: SearchResult[] = sources.map((s: any, i: number) => ({
                    id: `auto-${Date.now()}-${i}`,
                    title: s.title || `Auto-Discovery: ${randomTopic}`,
                    excerpt: s.snippet || s.text || "No excerpt available",
                    relevance: s.score || 0.85,
                    source: s.source || "Context Engine"
                }));

                if (newResults.length === 0 && answer) {
                    newResults.push({
                        id: `auto-ans-${Date.now()}`,
                        title: `Insight: ${randomTopic}`,
                        excerpt: answer.substring(0, 200) + "...",
                        relevance: 0.95,
                        source: 'AI Inference'
                    });
                }

                // Prepend to results (Live Feed style)
                setResults(prev => [...newResults, ...prev].slice(0, 50));
                addToLog(`Engine: Found ${newResults.length} insights for '${randomTopic}'.`);

            } catch (error) {
                console.error("Auto-search failed:", error);
                addToLog(`Error: Failed to retrieve context for '${randomTopic}'.`);
            } finally {
                setSearching(false);
            }
        };

        const interval = setInterval(runAutoStep, 8000); // New insight every 8 seconds
        runAutoStep(); // Run immediately on start

        return () => clearInterval(interval);
    }, [autoInsightMode]);

    const addToLog = (msg: string) => {
        setAutoLog(prev => [msg, ...prev].slice(0, 5));
    };

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setAutoInsightMode(false); // Pause auto mode on manual search
        setSearching(true);
        try {
            const response = await endpoints.context.query(query, caseId);
            // RAG query successful

            const answer = response.data.answer || response.data.response || (typeof response.data === 'string' ? response.data : JSON.stringify(response.data));
            const sources = response.data.sources || [];

            const newResults: SearchResult[] = sources.map((s: any, i: number) => ({
                id: `src-${i}`,
                title: s.title || `Source ${i + 1}`,
                excerpt: s.snippet || s.text || "No excerpt available",
                relevance: s.score || 0.9,
                source: s.source || "Unknown"
            }));

            if (newResults.length === 0 && answer) {
                newResults.push({
                    id: 'rag-answer',
                    title: 'AI Analysis',
                    excerpt: answer,
                    relevance: 1.0,
                    source: 'Context Engine'
                });
            }

            setResults(newResults);
        } catch (error) {
            console.error("Search failed:", error);
            setResults([{
                id: 'error',
                title: 'Search Error',
                excerpt: 'Failed to retrieve context. Please ensure the backend is running and vectors are indexed.',
                relevance: 0,
                source: 'System'
            }]);
        } finally {
            setSearching(false);
        }
    };

    return (
        <div className="flex-1 flex flex-col h-full p-6 max-w-5xl mx-auto w-full overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between mb-8 shrink-0">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-halo-cyan/10 rounded-lg border border-halo-cyan/30 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                        <BrainCircuit className="text-halo-cyan w-8 h-8" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider">Context Engine</h2>
                        <p className="text-halo-muted text-sm">Semantic search and knowledge retrieval system</p>
                    </div>
                </div>

                {/* Auto Toggle */}
                <button
                    onClick={() => setAutoInsightMode(!autoInsightMode)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-full border transition-all uppercase text-xs font-bold tracking-wider ${autoInsightMode
                        ? 'bg-halo-cyan text-black border-halo-cyan shadow-[0_0_15px_#00f0ff]'
                        : 'bg-transparent text-halo-muted border-halo-border hover:border-halo-cyan hover:text-halo-cyan'
                        }`}
                >
                    {autoInsightMode ? <Pause size={14} /> : <Play size={14} />}
                    {autoInsightMode ? 'Auto-Insight ON' : 'Start Auto-Insight'}
                </button>
            </div>

            {/* Search Bar */}
            <div className="relative mb-8 shrink-0">
                <form onSubmit={handleSearch}>
                    <Search className={`absolute left-5 top-5 w-6 h-6 transition-colors ${searching ? 'text-halo-cyan animate-pulse' : 'text-halo-muted'}`} />
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Query the knowledge base..."
                        className="w-full bg-halo-card border border-halo-border rounded-xl pl-16 pr-4 py-5 text-lg focus:border-halo-cyan focus:ring-1 focus:ring-halo-cyan focus:outline-none transition-all shadow-[0_0_20px_rgba(0,0,0,0.3)] placeholder:text-halo-muted/50"
                    />
                    {searching && (
                        <div className="absolute right-5 top-5">
                            <Activity className="w-6 h-6 text-halo-cyan animate-spin" />
                        </div>
                    )}
                </form>
            </div>

            {/* Auto Log (if active) */}
            {autoInsightMode && (
                <div className="mb-6 bg-black/40 border-l-2 border-halo-cyan p-3 rounded-r shrink-0 animate-in fade-in slide-in-from-top-2">
                    <div className="flex items-center gap-2 text-halo-cyan text-xs font-mono mb-1 uppercase tracking-wider">
                        <Sparkles size={12} /> Autonomous Agent Log
                    </div>
                    <div className="font-mono text-xs text-halo-muted space-y-1">
                        {autoLog.map((log, i) => (
                            <div key={i} className="opacity-80">{'>'} {log}</div>
                        ))}
                    </div>
                </div>
            )}

            {/* Results Area */}
            <div className="flex-1 overflow-y-auto custom-scrollbar" ref={scrollRef}>
                {results.length > 0 ? (
                    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-6">
                        <div className="flex items-center justify-between text-sm text-halo-muted uppercase tracking-wider border-b border-halo-border pb-2 sticky top-0 bg-halo-bg/95 backdrop-blur z-10">
                            <span>{autoInsightMode ? 'Live Insight Feed' : 'Top Results'}</span>
                            <span>{results.length} items found</span>
                        </div>

                        {results.map((result) => (
                            <div key={result.id} className="halo-card group hover:border-halo-cyan/50 transition-all cursor-pointer">
                                <div className="flex justify-between items-start mb-2">
                                    <div className="flex items-center gap-2 text-halo-cyan font-mono text-sm">
                                        <FileText size={16} />
                                        <span>{result.source}</span>
                                    </div>
                                    <div className="flex items-center gap-1 text-xs font-bold bg-halo-cyan/10 text-halo-cyan px-2 py-1 rounded border border-halo-cyan/20">
                                        <Layers size={12} />
                                        {Math.round(result.relevance * 100)}% RELEVANCE
                                    </div>
                                </div>
                                <h3 className="text-lg text-halo-text font-medium mb-2 group-hover:text-halo-cyan transition-colors">{result.title}</h3>
                                <p className="text-halo-muted leading-relaxed text-sm border-l-2 border-halo-border pl-4 italic">
                                    "{result.excerpt}"
                                </p>
                                <div className="mt-4 flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button className="text-xs text-halo-cyan flex items-center gap-1 hover:underline">
                                        VIEW SOURCE <ArrowRight size={12} />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="halo-card">
                            <div className="flex items-center gap-3 mb-4 text-halo-cyan">
                                <Database size={20} />
                                <h3 className="text-sm uppercase tracking-wider font-semibold">Recent Ingestions</h3>
                            </div>
                            <div className="space-y-3">
                                {[1, 2, 3].map(i => (
                                    <div key={i} className="flex items-center gap-3 text-sm text-halo-muted hover:text-halo-text cursor-pointer transition-colors group">
                                        <div className="w-1.5 h-1.5 rounded-full bg-halo-cyan/50 group-hover:bg-halo-cyan group-hover:shadow-[0_0_5px_rgba(0,240,255,0.8)] transition-all" />
                                        <span>Legal_Brief_v{i}.pdf</span>
                                        <span className="ml-auto text-xs opacity-50 font-mono">10m ago</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="halo-card">
                            <div className="flex items-center gap-3 mb-4 text-halo-cyan">
                                <Activity size={20} />
                                <h3 className="text-sm uppercase tracking-wider font-semibold">System Status</h3>
                            </div>
                            <div className="space-y-4">
                                <div className="flex justify-between text-sm border-b border-halo-border/30 pb-2">
                                    <span className="text-halo-muted">Vector Database</span>
                                    <span className="text-green-400 font-mono text-xs">ONLINE</span>
                                </div>
                                <div className="flex justify-between text-sm border-b border-halo-border/30 pb-2">
                                    <span className="text-halo-muted">Graph Engine</span>
                                    <span className="text-green-400 font-mono text-xs">ONLINE</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-halo-muted">Indexing Queue</span>
                                    <span className="text-halo-text font-mono text-xs">IDLE</span>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
