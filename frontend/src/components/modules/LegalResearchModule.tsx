import { useState } from 'react';
import { Library, Search, BookOpen, Scale, Loader2, Lightbulb, ListChecks, ShieldAlert } from 'lucide-react';
import { endpoints } from '../../services/api';

interface LegalTheory {
    cause: string;
    score: number;
    elements: { name: string; description: string }[];
    defenses: string[];
    indicators: string[];
    missing_elements: string[];
}

export function LegalResearchModule() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<any[]>([]);
    const [theories, setTheories] = useState<LegalTheory[]>([]);
    const [searching, setSearching] = useState(false);
    const [generating, setGenerating] = useState(false);

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setSearching(true);
        try {
            // Use the new Swarms Agent Runner for research
            const response = await endpoints.agents.run(`Research: ${query}`, 'default_case');

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
            // @ts-ignore
            const response = await endpoints.legalTheory.suggestions('default_case');
            setTheories(response.data);
        } catch (error) {
            console.error("Failed to generate theories:", error);
        } finally {
            setGenerating(false);
        }
    };

    return (
        <div className="w-full h-full flex flex-col p-8 text-halo-text overflow-y-auto custom-scrollbar">
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-halo-cyan/10 rounded-lg border border-halo-cyan/30 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                        <Library className="text-halo-cyan w-8 h-8" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider">Legal Research</h2>
                        <p className="text-halo-muted text-sm">Case law engine and precedent retrieval</p>
                    </div>
                </div>
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
                        className="w-full bg-halo-card border border-halo-border rounded-xl pl-16 pr-4 py-5 text-lg focus:border-halo-cyan focus:ring-1 focus:ring-halo-cyan focus:outline-none transition-all shadow-[0_0_20px_rgba(0,0,0,0.3)] placeholder:text-halo-muted/50"
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
                            <div key={idx} className="halo-card border-purple-500/20 bg-purple-500/5">
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
                        <div key={result.id} className="halo-card group hover:border-halo-cyan/50 transition-all">
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
                        <div className="halo-card flex flex-col items-center text-center p-6">
                            <BookOpen size={32} className="text-halo-muted mb-4" />
                            <h3 className="text-sm font-bold text-halo-text mb-2">Federal Cases</h3>
                            <p className="text-xs text-halo-muted">Search across all federal circuits and Supreme Court rulings.</p>
                        </div>
                        <div className="halo-card flex flex-col items-center text-center p-6">
                            <Scale size={32} className="text-halo-muted mb-4" />
                            <h3 className="text-sm font-bold text-halo-text mb-2">State Statutes</h3>
                            <p className="text-xs text-halo-muted">Access codified laws and regulatory frameworks.</p>
                        </div>
                        <div className="halo-card flex flex-col items-center text-center p-6">
                            <Library size={32} className="text-halo-muted mb-4" />
                            <h3 className="text-sm font-bold text-halo-text mb-2">Secondary Sources</h3>
                            <p className="text-xs text-halo-muted">Law reviews, treatises, and expert commentary.</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

