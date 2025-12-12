import { useState, useEffect } from 'react';
import { FolderOpen, Star, FileText, Plus, X, Search, Loader2, MoreVertical, Map, Calendar as CalendarIcon } from 'lucide-react';
import { endpoints } from '../../services/api';
import { playSound } from '../../utils/sounds';
import { motion, AnimatePresence } from 'framer-motion';

interface BinderDoc {
    id: string;
    filename: string;
    size: number;
    type: string;
}

export function TrialBinderModule() {
    const [binderDocs, setBinderDocs] = useState<BinderDoc[]>([]);
    const [allDocs, setAllDocs] = useState<BinderDoc[]>([]);
    const [loading, setLoading] = useState(false);
    const [isAdding, setIsAdding] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [activeMenu, setActiveMenu] = useState<string | null>(null);

    useEffect(() => {
        fetchDocuments();
    }, []);

    const fetchDocuments = async () => {
        setLoading(true);
        try {
            const response = await endpoints.documents.list('1');
            const docs = response.data.map((d: any) => ({
                id: d.id,
                filename: d.filename,
                size: d.size,
                type: d.content_type || 'application/pdf'
            }));
            setAllDocs(docs);

            // Load pinned IDs from localStorage
            const pinnedIds = JSON.parse(localStorage.getItem('halo_binder_pins') || '[]');
            const pinned = docs.filter((d: BinderDoc) => pinnedIds.includes(d.id));
            setBinderDocs(pinned);
        } catch (error) {
            console.error("Failed to fetch documents:", error);
        } finally {
            setLoading(false);
        }
    };

    const togglePin = (doc: BinderDoc) => {
        const isPinned = binderDocs.some(d => d.id === doc.id);
        let newPinned;

        if (isPinned) {
            newPinned = binderDocs.filter(d => d.id !== doc.id);
            playSound.error(); // Unpin sound
        } else {
            newPinned = [...binderDocs, doc];
            playSound.success(); // Pin sound
        }

        setBinderDocs(newPinned);
        localStorage.setItem('halo_binder_pins', JSON.stringify(newPinned.map(d => d.id)));
    };

    const handleAction = (action: string, doc: BinderDoc) => {
        playSound.notification();
        console.log(`[ACTION] ${action} on ${doc.filename}`);
        setActiveMenu(null);
        // In a real app, this would dispatch an event or update a global store
        // to notify the target module.
    };

    const filteredAllDocs = allDocs.filter(d =>
        d.filename.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !binderDocs.some(bd => bd.id === d.id)
    );

    return (
        <div className="w-full h-full flex flex-col p-8 text-halo-text overflow-hidden bg-black/20" onClick={() => setActiveMenu(null)}>
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-halo-cyan/10 rounded-lg border border-halo-cyan/30 shadow-[0_0_15px_rgba(0,240,255,0.2)] backdrop-blur-sm">
                        <FolderOpen className="text-halo-cyan w-8 h-8" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider text-shadow-glow">Trial Binder</h2>
                        <p className="text-halo-muted text-sm">Key evidence and organized exhibits</p>
                    </div>
                </div>
                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        setIsAdding(true);
                        playSound.click();
                    }}
                    className="flex items-center gap-2 px-4 py-2 bg-halo-cyan text-black rounded hover:bg-white transition-colors font-medium shadow-[0_0_10px_rgba(0,240,255,0.3)]"
                    onMouseEnter={() => playSound.hover()}
                >
                    <Plus size={18} />
                    ADD EXHIBIT
                </button>
            </div>

            {/* Binder Grid */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-2">
                {loading ? (
                    <div className="flex items-center justify-center h-64 text-halo-muted">
                        <Loader2 className="animate-spin mr-2" /> Loading binder...
                    </div>
                ) : binderDocs.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-64 text-halo-muted opacity-50 border-2 border-dashed border-halo-border rounded-xl bg-black/20">
                        <Star size={48} className="mb-4" />
                        <p>Trial Binder is empty.</p>
                        <p className="text-sm">Add exhibits to organize your case strategy.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                        <AnimatePresence>
                            {binderDocs.map(doc => (
                                <motion.div
                                    key={doc.id}
                                    layout
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.9 }}
                                    className="halo-card group relative hover:border-halo-cyan transition-all bg-black/40 backdrop-blur-sm border border-halo-border/50"
                                    onMouseEnter={() => playSound.hover()}
                                >
                                    <div className="flex items-start justify-between mb-4">
                                        <FileText size={32} className="text-halo-cyan opacity-80 group-hover:opacity-100 transition-opacity" />
                                        <div className="relative">
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setActiveMenu(activeMenu === doc.id ? null : doc.id);
                                                    playSound.click();
                                                }}
                                                className="text-halo-muted hover:text-white transition-colors p-1"
                                            >
                                                <MoreVertical size={18} />
                                            </button>

                                            {/* Context Menu */}
                                            {activeMenu === doc.id && (
                                                <motion.div
                                                    initial={{ opacity: 0, y: 10 }}
                                                    animate={{ opacity: 1, y: 0 }}
                                                    className="absolute right-0 top-8 w-48 bg-black/90 border border-halo-cyan/30 rounded-lg shadow-xl z-50 backdrop-blur-md overflow-hidden"
                                                >
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); handleAction('timeline', doc); }}
                                                        className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-halo-cyan/20 hover:text-white flex items-center gap-2 transition-colors"
                                                    >
                                                        <CalendarIcon size={14} /> Send to Timeline
                                                    </button>
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); handleAction('map', doc); }}
                                                        className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-halo-cyan/20 hover:text-white flex items-center gap-2 transition-colors"
                                                    >
                                                        <Map size={14} /> Send to Map
                                                    </button>
                                                    <div className="h-px bg-white/10 my-1" />
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); togglePin(doc); }}
                                                        className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-500/20 flex items-center gap-2 transition-colors"
                                                    >
                                                        <X size={14} /> Remove
                                                    </button>
                                                </motion.div>
                                            )}
                                        </div>
                                    </div>
                                    <h3 className="font-medium text-halo-text truncate mb-1" title={doc.filename}>{doc.filename}</h3>
                                    <p className="text-xs text-halo-muted">{(doc.size / 1024).toFixed(1)} KB</p>

                                    <div className="absolute inset-0 bg-halo-cyan/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none rounded-lg" />
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                )}
            </div>

            {/* Add Document Modal Overlay */}
            <AnimatePresence>
                {isAdding && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="absolute inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-8"
                        onClick={() => setIsAdding(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            className="bg-halo-bg border border-halo-cyan rounded-xl w-full max-w-2xl h-[80%] flex flex-col shadow-[0_0_50px_rgba(0,240,255,0.2)]"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="p-6 border-b border-halo-border flex justify-between items-center">
                                <h3 className="text-xl font-light text-halo-text">Add to Binder</h3>
                                <button onClick={() => setIsAdding(false)} className="text-halo-muted hover:text-white">
                                    <X size={24} />
                                </button>
                            </div>

                            <div className="p-4 border-b border-halo-border">
                                <div className="relative">
                                    <Search className="absolute left-3 top-3 text-halo-muted" size={18} />
                                    <input
                                        type="text"
                                        placeholder="Search available documents..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="w-full bg-black/50 border border-halo-border rounded-lg pl-10 pr-4 py-2 text-halo-text focus:border-halo-cyan focus:outline-none"
                                        autoFocus
                                    />
                                </div>
                            </div>

                            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar space-y-2">
                                {filteredAllDocs.map(doc => (
                                    <div
                                        key={doc.id}
                                        className="flex items-center justify-between p-3 rounded hover:bg-halo-cyan/10 border border-transparent hover:border-halo-cyan/30 transition-all group cursor-pointer"
                                        onClick={() => togglePin(doc)}
                                        onMouseEnter={() => playSound.hover()}
                                    >
                                        <div className="flex items-center gap-3 overflow-hidden">
                                            <FileText size={18} className="text-halo-muted group-hover:text-halo-cyan flex-shrink-0" />
                                            <span className="truncate text-sm text-halo-text group-hover:text-white">{doc.filename}</span>
                                        </div>
                                        <button
                                            className="px-3 py-1 bg-halo-cyan/20 text-halo-cyan text-xs rounded hover:bg-halo-cyan hover:text-black transition-colors"
                                        >
                                            ADD
                                        </button>
                                    </div>
                                ))}
                                {filteredAllDocs.length === 0 && (
                                    <div className="text-center text-halo-muted py-8">
                                        No matching documents found.
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
