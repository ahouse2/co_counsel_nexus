import { useState, useEffect } from 'react';
import { endpoints } from '../../services/api';
import { format } from 'date-fns';
import { Calendar, Search, ZoomIn, ZoomOut, RefreshCw, ChevronRight, Download } from 'lucide-react';
import { ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts';
import { motion } from 'framer-motion';

interface TimelineEvent {
    id: string;
    date: string;
    title: string;
    description: string;
    significance: number; // 1-10, maps to Y-axis
    type: 'fact' | 'filing' | 'evidence' | 'testimony';
    source_id?: string;
}

export function TimelineModule() {
    const [events, setEvents] = useState<TimelineEvent[]>([]);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');

    const [selectedEvent, setSelectedEvent] = useState<TimelineEvent | null>(null);

    // Mock data generator
    const generateMockEvents = (): TimelineEvent[] => {

        const mockEvents: TimelineEvent[] = [
            { id: '1', date: '2023-01-15', title: 'Incident Occurred', description: 'Plaintiff injured at construction site.', significance: 10, type: 'fact' },
            { id: '2', date: '2023-01-16', title: 'Hospital Admission', description: 'Admitted to ER with compound fracture.', significance: 8, type: 'fact' },
            { id: '3', date: '2023-02-01', title: 'Internal Email', description: 'Supervisor discusses safety violation.', significance: 9, type: 'evidence' },
            { id: '4', date: '2023-03-10', title: 'Complaint Filed', description: 'Initial complaint filed in Superior Court.', significance: 7, type: 'filing' },
            { id: '5', date: '2023-04-05', title: 'Answer Filed', description: 'Defendant denies all allegations.', significance: 5, type: 'filing' },
            { id: '6', date: '2023-05-20', title: 'Witness Deposition', description: 'Foreman admits to cutting corners.', significance: 9, type: 'testimony' },
            { id: '7', date: '2023-06-15', title: 'Expert Report', description: 'Safety expert confirms protocol breach.', significance: 8, type: 'evidence' },
            { id: '8', date: '2023-08-01', title: 'Settlement Offer', description: 'Defendant offers $50k (Rejected).', significance: 4, type: 'fact' },
        ];
        return mockEvents;
    };

    useEffect(() => {
        fetchTimeline();
    }, []);

    const fetchTimeline = async () => {
        setLoading(true);
        try {
            // Try fetch real data
            const response = await endpoints.timeline.generate(searchQuery || "key events", 'default_case');
            if (response.data && Array.isArray(response.data.events)) {
                const mappedEvents = response.data.events.map((e: any) => ({
                    id: e.id,
                    date: e.ts,
                    title: e.title,
                    description: e.summary,
                    significance: Math.round((e.risk_score || 0.5) * 10),
                    type: e.type || 'fact',
                    source_id: e.citations?.[0]
                }));
                setEvents(mappedEvents);
            } else {
                setEvents(generateMockEvents());
            }
        } catch (error) {
            console.error("Failed to fetch timeline, using mock data:", error);
            setEvents(generateMockEvents());
        } finally {
            setLoading(false);
        }
    };

    const handleZoom = (direction: 'in' | 'out') => {
        // Simple zoom logic implementation
        // In a real app, this would manipulate the domain state more precisely
        console.log(`Zooming ${direction}`);
    };

    const exportToCSV = () => {
        if (events.length === 0) return;

        const headers = ['Date', 'Title', 'Description', 'Type', 'Significance'];
        const csvContent = [
            headers.join(','),
            ...events.map(e => [
                format(new Date(e.date), 'yyyy-MM-dd'),
                `"${e.title.replace(/"/g, '""')}"`,
                `"${e.description.replace(/"/g, '""')}"`,
                e.type,
                e.significance
            ].join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `timeline_export_${format(new Date(), 'yyyy-MM-dd')}.csv`;
        link.click();
    };

    const chartData = events.map(e => ({
        ...e,
        x: new Date(e.date).getTime(),
        y: e.significance,
        z: 1 // bubble size
    })).sort((a, b) => a.x - b.x);

    const CustomTooltip = ({ active, payload }: any) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
                <div className="bg-black/90 border border-halo-cyan/50 p-3 rounded shadow-xl backdrop-blur-md max-w-xs z-50">
                    <p className="text-halo-cyan font-bold text-sm mb-1">{format(new Date(data.date), 'MMM d, yyyy')}</p>
                    <p className="text-white font-medium mb-1">{data.title}</p>
                    <p className="text-gray-400 text-xs line-clamp-2">{data.description}</p>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="w-full h-full flex flex-col text-halo-text overflow-hidden bg-black/20">
            {/* Header */}
            <div className="p-6 border-b border-halo-border/30 flex justify-between items-center bg-halo-bg/50">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-halo-cyan/10 rounded-lg border border-halo-cyan/30 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                        <Calendar className="text-halo-cyan w-8 h-8" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider">Chronos Timeline</h2>
                        <p className="text-halo-muted text-sm">Interactive Event Visualization</p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <div className="relative">
                        <Search className="absolute left-3 top-2.5 text-halo-muted w-4 h-4" />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && fetchTimeline()}
                            placeholder="Filter events..."
                            className="bg-black/40 border border-halo-border rounded-lg pl-9 pr-4 py-2 text-sm focus:border-halo-cyan focus:outline-none w-64"
                            aria-label="Filter events"
                        />
                    </div>
                    <button onClick={fetchTimeline} className="p-2 bg-halo-card border border-halo-border rounded hover:bg-halo-cyan/10 hover:border-halo-cyan transition-colors" title="Refresh">
                        <RefreshCw size={20} className={loading ? "animate-spin" : ""} />
                    </button>
                    <button
                        onClick={exportToCSV}
                        disabled={events.length === 0}
                        className="p-2 bg-halo-card border border-halo-border rounded hover:bg-halo-cyan/10 hover:border-halo-cyan transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Export to CSV"
                    >
                        <Download size={20} />
                    </button>
                </div>
            </div>

            <div className="flex-1 flex overflow-hidden">
                {/* Chart Area */}
                <div className="flex-1 flex flex-col p-6 relative">
                    <div className="absolute top-6 right-6 z-10 flex gap-2">
                        <button onClick={() => handleZoom('in')} className="p-2 bg-black/60 border border-halo-border rounded hover:text-halo-cyan backdrop-blur-sm" title="Zoom in"><ZoomIn size={20} /></button>
                        <button onClick={() => handleZoom('out')} className="p-2 bg-black/60 border border-halo-border rounded hover:text-halo-cyan backdrop-blur-sm" title="Zoom out"><ZoomOut size={20} /></button>
                    </div>

                    <div className="flex-1 w-full min-h-0 bg-black/40 border border-halo-border/30 rounded-xl p-4">
                        <ResponsiveContainer width="100%" height="100%">
                            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                                <XAxis
                                    type="number"
                                    dataKey="x"
                                    name="Date"
                                    domain={['auto', 'auto']}
                                    tickFormatter={(unixTime) => format(new Date(unixTime), 'MMM yyyy')}
                                    stroke="#4b5563"
                                    tick={{ fill: '#9ca3af', fontSize: 12 }}
                                />
                                <YAxis
                                    type="number"
                                    dataKey="y"
                                    name="Significance"
                                    domain={[0, 12]}
                                    stroke="#4b5563"
                                    tick={{ fill: '#9ca3af', fontSize: 12 }}
                                    label={{ value: 'Impact', angle: -90, position: 'insideLeft', fill: '#6b7280' }}
                                />
                                <ZAxis type="number" dataKey="z" range={[100, 400]} />
                                <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                                <ReferenceLine y={5} stroke="#374151" strokeDasharray="3 3" />
                                <Scatter name="Events" data={chartData} onClick={(node) => setSelectedEvent(node)}>
                                    {chartData.map((entry, index) => (
                                        <Cell
                                            key={`cell-${index}`}
                                            fill={
                                                entry.type === 'evidence' ? '#00f0ff' :
                                                    entry.type === 'filing' ? '#a855f7' :
                                                        entry.type === 'testimony' ? '#eab308' :
                                                            '#ffffff'
                                            }
                                            className="cursor-pointer hover:opacity-80 transition-opacity"
                                        />
                                    ))}
                                </Scatter>
                            </ScatterChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Event List / Detail Sidebar */}
                <div className="w-96 bg-halo-card/20 border-l border-halo-border/30 flex flex-col">
                    <div className="p-4 border-b border-halo-border/30 bg-halo-bg/50">
                        <h3 className="font-mono text-sm uppercase tracking-wider text-halo-muted">Event Log</h3>
                    </div>

                    <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">
                        {selectedEvent && (
                            <motion.div
                                initial={{ opacity: 0, y: -20 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="mb-6 p-4 bg-halo-cyan/10 border border-halo-cyan/30 rounded-lg"
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <span className="text-xs font-bold text-halo-cyan uppercase">{selectedEvent.type}</span>
                                    <span className="text-xs text-halo-muted">{format(new Date(selectedEvent.date), 'MMM d, yyyy')}</span>
                                </div>
                                <h4 className="font-bold text-white text-lg mb-2">{selectedEvent.title}</h4>
                                <p className="text-sm text-gray-300 mb-4">{selectedEvent.description}</p>
                                <div className="flex gap-2">
                                    <button className="flex-1 py-2 bg-halo-cyan text-black text-xs font-bold rounded hover:bg-white transition-colors">
                                        VIEW SOURCE
                                    </button>
                                    <button
                                        onClick={() => setSelectedEvent(null)}
                                        className="px-3 py-2 border border-halo-border text-halo-muted text-xs font-bold rounded hover:text-white transition-colors"
                                    >
                                        CLOSE
                                    </button>
                                </div>
                            </motion.div>
                        )}

                        {chartData.map((event) => (
                            <div
                                key={event.id}
                                onClick={() => setSelectedEvent(event)}
                                className={`p-3 rounded border transition-all cursor-pointer group ${selectedEvent?.id === event.id
                                    ? 'bg-white/5 border-halo-cyan/50'
                                    : 'bg-black/20 border-halo-border/30 hover:bg-white/5 hover:border-halo-cyan/30'
                                    }`}
                            >
                                <div className="flex items-center gap-3">
                                    <div className={`w-2 h-2 rounded-full ${event.type === 'evidence' ? 'bg-cyan-400' :
                                        event.type === 'filing' ? 'bg-purple-400' :
                                            event.type === 'testimony' ? 'bg-yellow-400' :
                                                'bg-white'
                                        }`} />
                                    <div className="flex-1 min-w-0">
                                        <div className="flex justify-between items-baseline mb-1">
                                            <h5 className={`text-sm font-medium truncate ${selectedEvent?.id === event.id ? 'text-halo-cyan' : 'text-gray-300 group-hover:text-white'}`}>
                                                {event.title}
                                            </h5>
                                            <span className="text-xs text-gray-500 font-mono flex-shrink-0 ml-2">
                                                {format(new Date(event.date), 'MMM d')}
                                            </span>
                                        </div>
                                        <p className="text-xs text-gray-500 truncate">{event.description}</p>
                                    </div>
                                    <ChevronRight size={14} className="text-gray-600 group-hover:text-halo-cyan opacity-0 group-hover:opacity-100 transition-all" />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
