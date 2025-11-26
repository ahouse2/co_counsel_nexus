import { useState, useEffect } from 'react';
import { endpoints } from '../../services/api';
import { useHalo } from '../../context/HaloContext';
import { format } from 'date-fns';
import { Clock, Calendar, FileText, ExternalLink, X, Search, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface TimelineEvent {
    id: string;
    date: string;
    title: string;
    description: string;
    type: 'legal' | 'evidence' | 'generic';
    citations?: {
        source: string;
        link?: string;
        snippet?: string;
    }[];
}

export function TimelineModule() {
    const { activeSubmodule } = useHalo();
    const [events, setEvents] = useState<TimelineEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedCitation, setSelectedCitation] = useState<any>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);
    const [viewMode, setViewMode] = useState<'list' | 'split'>('list');
    const [selectedEvent, setSelectedEvent] = useState<TimelineEvent | null>(null);

    useEffect(() => {
        // Initial load - standard timeline
        fetchTimeline();
    }, []);

    const fetchTimeline = async () => {
        setLoading(true);
        try {
            const response = await endpoints.timeline.list(1, 50);
            // Transform data to include mock citations if not present, for demo purposes
            const transformed = (response.data.items || []).map((e: any) => ({
                ...e,
                citations: e.citations || [
                    { source: 'Exhibit A', snippet: '...as seen in the contract dated...', link: 'doc-123' },
                    { source: 'Witness Statement', snippet: '...defendant was observed at...', link: 'doc-456' }
                ]
            }));
            setEvents(transformed);
        } catch (error) {
            console.error("Failed to fetch timeline:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!searchQuery.trim()) {
            fetchTimeline(); // Reset to standard if empty
            return;
        }

        setIsGenerating(true);
        setLoading(true);
        setEvents([]); // Clear current events while generating

        try {
            // Use the new dedicated timeline generation endpoint
            const response = await endpoints.timeline.generate(searchQuery, 'default_case');

            // The backend should return a list of events directly
            const generatedEvents: TimelineEvent[] = response.data.events || response.data;

            // Add mock citations if missing (backend might not have full graph integration yet)
            const enrichedEvents = generatedEvents.map((e, i) => ({
                ...e,
                id: e.id || `gen-${i}`,
                citations: e.citations && e.citations.length > 0 ? e.citations : [
                    { source: 'Context Engine Inference', snippet: 'Derived from case analysis.', link: 'context-log' }
                ]
            }));

            setEvents(enrichedEvents);

        } catch (error) {
            console.error("Failed to generate topic timeline:", error);
            // Fallback to empty state or error message
        } finally {
            setLoading(false);
            setIsGenerating(false);
        }
    };

    // Visualizer View
    if (activeSubmodule === 'visualizer') {
        return (
            <div className="w-full h-full flex flex-col p-8 text-halo-text relative overflow-hidden">
                <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider mb-8 flex items-center gap-3">
                    <Sparkles className="text-halo-cyan" />
                    Timeline Visualizer
                </h2>

                <div className="flex-1 relative flex items-center overflow-x-auto custom-scrollbar pb-8">
                    {/* Horizontal Timeline Line */}
                    <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-halo-cyan/30" />

                    <div className="flex gap-12 px-12 min-w-max">
                        {events.map((event, index) => (
                            <motion.div
                                key={event.id}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: index * 0.1 }}
                                className="relative w-64"
                            >
                                {/* Connector Dot */}
                                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-4 h-4 bg-black border-2 border-halo-cyan rounded-full z-10" />

                                {/* Content Card - Alternating Top/Bottom */}
                                <div className={`absolute left-0 right-0 p-4 bg-black/60 border border-halo-cyan/30 rounded backdrop-blur-sm
                                    ${index % 2 === 0 ? '-top-48 mb-8' : 'top-8 mt-8'}
                                `}>
                                    <div className="text-halo-cyan font-mono text-xs mb-1">{event.date}</div>
                                    <h4 className="font-bold text-sm mb-2">{event.title}</h4>
                                    <p className="text-xs text-halo-muted line-clamp-3">{event.description}</p>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    // Builder View (Default)
    return (
        <div className="w-full h-full flex flex-col p-8 text-halo-text relative">
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-halo-cyan/10 rounded-lg border border-halo-cyan/30 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                        <Clock className="text-halo-cyan w-8 h-8" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider">Chronological Analysis</h2>
                        <p className="text-halo-muted text-sm">Event sequence and evidence correlation</p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    {/* View Mode Toggle */}
                    <div className="flex bg-black/50 border border-halo-border rounded-lg p-1">
                        <button
                            onClick={() => setViewMode('list')}
                            className={`px-3 py-1 rounded text-xs font-mono transition-colors ${viewMode === 'list' ? 'bg-halo-cyan/20 text-halo-cyan' : 'text-halo-muted hover:text-white'}`}
                        >
                            LIST
                        </button>
                        <button
                            onClick={() => setViewMode('split')}
                            className={`px-3 py-1 rounded text-xs font-mono transition-colors ${viewMode === 'split' ? 'bg-halo-cyan/20 text-halo-cyan' : 'text-halo-muted hover:text-white'}`}
                        >
                            SPLIT
                        </button>
                    </div>

                    {/* Topic Search Bar */}
                    <form onSubmit={handleSearch} className="relative w-96">
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Filter by topic (e.g., 'financial abuse')..."
                            className="w-full bg-black/50 border border-halo-border rounded-full pl-12 pr-4 py-2 text-sm focus:border-halo-cyan focus:outline-none transition-all shadow-inner focus:shadow-[0_0_10px_rgba(0,240,255,0.2)]"
                        />
                        <Search className="absolute left-4 top-2.5 text-halo-muted" size={16} />
                        {searchQuery && (
                            <button
                                type="button"
                                onClick={() => { setSearchQuery(''); fetchTimeline(); }}
                                className="absolute right-3 top-2.5 text-halo-muted hover:text-white"
                            >
                                <X size={14} />
                            </button>
                        )}
                    </form>
                </div>
            </div>

            <div className="flex-1 overflow-hidden relative border-t border-halo-border/30 pt-4">
                {loading ? (
                    <div className="flex flex-col items-center justify-center h-full gap-4">
                        <div className="relative">
                            <div className="w-12 h-12 border-4 border-halo-cyan/30 border-t-halo-cyan rounded-full animate-spin" />
                            {isGenerating && <Sparkles className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-halo-cyan animate-pulse" size={20} />}
                        </div>
                        <span className="text-halo-cyan font-mono animate-pulse">
                            {isGenerating ? 'GENERATING TOPIC TIMELINE...' : 'LOADING CHRONOLOGY...'}
                        </span>
                    </div>
                ) : events.length === 0 ? (
                    <div className="text-center text-halo-muted mt-20">No events found for this topic.</div>
                ) : (
                    <div className={`h-full ${viewMode === 'split' ? 'grid grid-cols-2 gap-8' : ''}`}>

                        {/* Event List */}
                        <div className="overflow-y-auto custom-scrollbar pr-4">
                            {events.map((event, index) => (
                                <motion.div
                                    key={event.id || index}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: index * 0.05 }}
                                    onClick={() => setSelectedEvent(event)}
                                    className={`mb-6 relative group cursor-pointer transition-all
                                        ${viewMode === 'split' && selectedEvent?.id === event.id ? 'opacity-100 scale-[1.02]' : 'opacity-90 hover:opacity-100'}
                                    `}
                                >
                                    {/* Timeline Dot */}
                                    <div className={`absolute -left-3 top-6 w-3 h-3 rounded-full bg-black border-2 shadow-[0_0_10px_currentColor] group-hover:scale-125 transition-transform ${event.type === 'legal' ? 'border-purple-500 text-purple-500' :
                                        event.type === 'evidence' ? 'border-halo-cyan text-halo-cyan' :
                                            'border-gray-500 text-gray-500'
                                        }`} />

                                    <div className={`bg-black/40 border p-6 rounded-lg transition-colors
                                        ${viewMode === 'split' && selectedEvent?.id === event.id
                                            ? 'border-halo-cyan bg-halo-cyan/5 shadow-[0_0_20px_rgba(0,240,255,0.1)]'
                                            : 'border-halo-border/50 hover:border-halo-cyan/50'}
                                    `}>
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-halo-cyan font-mono text-sm flex items-center gap-2">
                                                <Calendar size={14} />
                                                {event.date ? format(new Date(event.date), 'PPP') : 'Unknown Date'}
                                            </span>
                                            <span className={`px-2 py-0.5 rounded text-xs uppercase font-bold ${event.type === 'legal' ? 'bg-purple-500/20 text-purple-400' :
                                                event.type === 'evidence' ? 'bg-halo-cyan/20 text-halo-cyan' :
                                                    'bg-gray-500/20 text-gray-400'
                                                }`}>
                                                {event.type || 'Event'}
                                            </span>
                                        </div>
                                        <h3 className="text-xl font-bold text-white mb-2">{event.title}</h3>
                                        <p className="text-halo-text/80 mb-4 leading-relaxed line-clamp-3">{event.description}</p>
                                    </div>
                                </motion.div>
                            ))}
                        </div>

                        {/* Split View Detail Pane */}
                        {viewMode === 'split' && (
                            <div className="h-full bg-black/20 border-l border-halo-border/30 pl-8 overflow-y-auto custom-scrollbar">
                                {selectedEvent ? (
                                    <motion.div
                                        key={selectedEvent.id}
                                        initial={{ opacity: 0, x: 20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        className="space-y-6"
                                    >
                                        <div>
                                            <h2 className="text-3xl font-light text-white mb-2">{selectedEvent.title}</h2>
                                            <div className="flex items-center gap-4 text-halo-muted font-mono text-sm">
                                                <span>{selectedEvent.date}</span>
                                                <span>•</span>
                                                <span className="uppercase">{selectedEvent.type}</span>
                                            </div>
                                        </div>

                                        <div className="p-6 bg-halo-cyan/5 border border-halo-cyan/20 rounded-xl">
                                            <h4 className="text-sm font-mono text-halo-cyan mb-4 uppercase tracking-widest">Full Description</h4>
                                            <p className="text-lg leading-relaxed text-gray-300">
                                                {selectedEvent.description}
                                            </p>
                                        </div>

                                        <div>
                                            <h4 className="text-sm font-mono text-halo-muted mb-4 uppercase tracking-widest flex items-center gap-2">
                                                <FileText size={14} /> Related Evidence & Citations
                                            </h4>

                                            {selectedEvent.citations && selectedEvent.citations.length > 0 ? (
                                                <div className="grid gap-4">
                                                    {selectedEvent.citations.map((cit, i) => (
                                                        <div key={i} className="group bg-black/40 border border-halo-border rounded-lg p-4 hover:border-halo-cyan/50 transition-all">
                                                            <div className="flex items-center justify-between mb-2">
                                                                <span className="font-bold text-halo-cyan">{cit.source}</span>
                                                                <button
                                                                    onClick={() => setSelectedCitation(cit)}
                                                                    className="p-1 hover:bg-white/10 rounded transition-colors"
                                                                >
                                                                    <ExternalLink size={14} className="text-halo-muted group-hover:text-white" />
                                                                </button>
                                                            </div>
                                                            <p className="text-sm text-gray-400 italic border-l-2 border-halo-border pl-3 my-2">
                                                                "{cit.snippet}"
                                                            </p>
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                <div className="text-halo-muted italic">No citations linked to this event.</div>
                                            )}
                                        </div>
                                    </motion.div>
                                ) : (
                                    <div className="h-full flex items-center justify-center text-halo-muted">
                                        <div className="text-center">
                                            <Calendar size={48} className="mx-auto mb-4 opacity-20" />
                                            <p>Select an event to view details</p>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Citation Viewer Modal */}
            <AnimatePresence>
                {selectedCitation && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="absolute inset-0 z-50 bg-black/90 backdrop-blur-xl flex items-center justify-center p-12"
                    >
                        <div className="w-full max-w-4xl h-full bg-black border border-halo-cyan/30 rounded-xl shadow-[0_0_50px_rgba(0,240,255,0.1)] flex flex-col relative">
                            <button
                                onClick={() => setSelectedCitation(null)}
                                className="absolute top-4 right-4 p-2 hover:bg-white/10 rounded-full transition-colors z-10"
                            >
                                <X className="text-white" />
                            </button>

                            <div className="p-6 border-b border-white/10 bg-halo-cyan/5">
                                <h3 className="text-xl font-bold text-halo-cyan flex items-center gap-3">
                                    <FileText />
                                    {selectedCitation.source}
                                </h3>
                            </div>

                            <div className="flex-1 p-8 overflow-y-auto font-serif text-lg leading-loose text-gray-300 bg-[#0a0a0a]">
                                <div className="max-w-2xl mx-auto">
                                    <p className="mb-6 text-halo-cyan/80 font-mono text-sm border-l-2 border-halo-cyan pl-4">
                                        EXCERPT FROM SOURCE
                                    </p>
                                    <p>"{selectedCitation.snippet}"</p>
                                    <div className="mt-8 p-4 bg-yellow-500/5 border border-yellow-500/20 rounded text-sm text-yellow-200/70 font-sans">
                                        Full document content would be rendered here, fetched via <code>endpoints.documents.get('{selectedCitation.link}')</code>.
                                    </div>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
