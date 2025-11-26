import { useState } from 'react';
import { Library, Search, BookOpen, Scale, Loader2, ExternalLink } from 'lucide-react';
import { endpoints } from '../../services/api';

interface CaseLawResult {
    id: string;
    citation: string;
    summary: string;
    relevance: number;
}

export function LegalResearchModule() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<CaseLawResult[]>([]);
    const [searching, setSearching] = useState(false);

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setSearching(true);
        try {
            // Prepend instruction to focus on case law
            const specializedQuery = `Search for legal precedents and case law citations relevant to: ${query}. Return a list of cases with citations and brief summaries.`;
            const response = await endpoints.context.query(specializedQuery);

            // Parse response (assuming text or structured)
            const answer = response.data.response || response.data.answer || (typeof response.data === 'string' ? response.data : JSON.stringify(response.data));

            // If the backend returns a single text block, we wrap it. 
            // Ideally, we'd parse it into a list if the LLM follows instructions well.
            // For now, we'll show the "AI Analysis" as the primary result.
            setResults([{
                id: 'res-1',
                citation: 'AI Legal Analysis',
                summary: answer,
                relevance: 1.0
            }]);

        } catch (error) {
            console.error("Legal research failed:", error);
        } finally {
            setSearching(false);
        }
    };

    return (
        <div className="w-full h-full flex flex-col p-8 text-halo-text overflow-y-auto custom-scrollbar">
            <div className="flex items-center gap-4 mb-8">
                <div className="p-3 bg-halo-cyan/10 rounded-lg border border-halo-cyan/30 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                    <Library className="text-halo-cyan w-8 h-8" />
                </div>
                <div>
                    <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider">Legal Research</h2>
                    <p className="text-halo-muted text-sm">Case law engine and precedent retrieval</p>
                </div>
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

            {/* Results */}
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
                            <div className="mt-4 flex justify-end">
                                <button className="text-xs text-halo-muted hover:text-halo-cyan flex items-center gap-1 transition-colors">
                                    FULL TEXT <ExternalLink size={12} />
                                </button>
                            </div>
                        </div>
                    ))
                ) : (
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

