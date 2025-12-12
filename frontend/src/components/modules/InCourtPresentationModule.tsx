import { useState, useEffect } from 'react';
import { Presentation, Plus, X, Play, FileText, ChevronRight, ChevronLeft, GripVertical, Search, LayoutTemplate, Minimize2, Loader2 } from 'lucide-react';
import { endpoints } from '../../services/api';
import { motion, AnimatePresence } from 'framer-motion';

interface Document {
    id: string;
    filename: string;
    content_type: string;
}

interface PlaylistItem {
    id: string;
    doc: Document;
    notes?: string;
}

export function InCourtPresentationModule() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [playlist, setPlaylist] = useState<PlaylistItem[]>([]);
    const [isPresenting, setIsPresenting] = useState(false);
    const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchDocuments();
    }, []);

    const fetchDocuments = async () => {
        setLoading(true);
        try {
            const response = await endpoints.documents.list('default_case');
            const docs = Array.isArray(response.data) ? response.data : (response.data.documents || []);
            setDocuments(docs);
        } catch (error) {
            console.error("Failed to fetch documents:", error);
        } finally {
            setLoading(false);
        }
    };

    const addToPlaylist = (doc: Document) => {
        if (playlist.some(item => item.doc.id === doc.id)) return;
        setPlaylist([...playlist, { id: `item-${Date.now()}`, doc }]);
    };

    const removeFromPlaylist = (id: string) => {
        setPlaylist(playlist.filter(item => item.id !== id));
    };

    const startPresentation = () => {
        if (playlist.length === 0) return;
        setCurrentSlideIndex(0);
        setIsPresenting(true);
    };

    const nextSlide = () => {
        if (currentSlideIndex < playlist.length - 1) {
            setCurrentSlideIndex(prev => prev + 1);
        }
    };

    const prevSlide = () => {
        if (currentSlideIndex > 0) {
            setCurrentSlideIndex(prev => prev - 1);
        }
    };

    const filteredDocs = documents.filter(d =>
        d.filename.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="w-full h-full flex flex-col text-halo-text overflow-hidden relative">
            {/* Main Interface */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left Sidebar: Document Library */}
                <div className="w-80 bg-black/20 border-r border-halo-border/30 flex flex-col">
                    <div className="p-4 border-b border-halo-border/30">
                        <h3 className="text-sm font-mono uppercase tracking-wider text-halo-muted mb-3 flex items-center gap-2">
                            <FileText size={16} /> Exhibit Library
                        </h3>
                        <div className="relative">
                            <Search className="absolute left-3 top-2.5 text-halo-muted w-4 h-4" />
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="Search exhibits..."
                                className="w-full bg-black/40 border border-halo-border rounded pl-9 py-2 text-sm focus:border-halo-cyan focus:outline-none"
                            />
                        </div>
                    </div>
                    <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1">
                        {loading ? (
                            <div className="flex items-center justify-center py-8">
                                <Loader2 className="w-6 h-6 text-halo-cyan animate-spin" />
                            </div>
                        ) : filteredDocs.length === 0 ? (
                            <div className="text-center py-8 text-halo-muted text-sm">
                                No documents found
                            </div>
                        ) : (
                            filteredDocs.map(doc => (
                                <div
                                    key={doc.id}
                                    className="flex items-center justify-between p-2 rounded hover:bg-halo-cyan/10 group transition-colors cursor-pointer"
                                    onClick={() => addToPlaylist(doc)}
                                >
                                    <div className="flex items-center gap-2 overflow-hidden">
                                        <FileText size={14} className="text-halo-muted group-hover:text-halo-cyan shrink-0" />
                                        <span className="text-sm truncate text-halo-text/80 group-hover:text-white">{doc.filename}</span>
                                    </div>
                                    <Plus size={14} className="text-halo-cyan opacity-0 group-hover:opacity-100 transition-opacity" />
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Center: Playlist Builder */}
                <div className="flex-1 flex flex-col bg-halo-bg/50">
                    <div className="p-6 border-b border-halo-border/30 flex items-center justify-between">
                        <div>
                            <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider flex items-center gap-3">
                                <Presentation className="text-halo-cyan" />
                                Trial Playlist
                            </h2>
                            <p className="text-halo-muted text-sm">Drag and drop exhibits to sequence your presentation</p>
                        </div>
                        <button
                            onClick={startPresentation}
                            disabled={playlist.length === 0}
                            className="px-6 py-2 bg-halo-cyan text-black font-bold rounded hover:bg-white transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <Play size={18} fill="currentColor" />
                            PRESENT
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto custom-scrollbar p-8">
                        {playlist.length === 0 ? (
                            <div className="h-full flex flex-col items-center justify-center border-2 border-dashed border-halo-border/30 rounded-xl bg-black/20 text-halo-muted">
                                <LayoutTemplate size={48} className="mb-4 opacity-50" />
                                <p>Playlist is empty.</p>
                                <p className="text-sm">Select documents from the library to add them here.</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {playlist.map((item, index) => (
                                    <motion.div
                                        key={item.id}
                                        layout
                                        initial={{ opacity: 0, scale: 0.9 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        className="bg-halo-card border border-halo-border rounded-lg p-4 relative group hover:border-halo-cyan/50 transition-colors"
                                    >
                                        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button
                                                onClick={() => removeFromPlaylist(item.id)}
                                                className="p-1 hover:bg-red-500/20 text-halo-muted hover:text-red-500 rounded"
                                            >
                                                <X size={16} />
                                            </button>
                                        </div>

                                        <div className="flex items-center gap-3 mb-3">
                                            <div className="w-8 h-8 bg-halo-cyan/10 rounded-full flex items-center justify-center text-halo-cyan font-mono font-bold text-sm border border-halo-cyan/30">
                                                {index + 1}
                                            </div>
                                            <GripVertical className="text-halo-muted cursor-grab" size={16} />
                                        </div>

                                        <div className="aspect-video bg-black/40 rounded border border-halo-border/30 mb-3 flex items-center justify-center">
                                            <FileText size={32} className="text-halo-muted" />
                                        </div>

                                        <h4 className="font-medium text-sm truncate mb-1" title={item.doc.filename}>{item.doc.filename}</h4>
                                        <p className="text-xs text-halo-muted uppercase">{item.doc.content_type.split('/')[1] || 'FILE'}</p>
                                    </motion.div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Presentation Mode Overlay */}
            <AnimatePresence>
                {isPresenting && playlist.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 bg-black flex flex-col"
                    >
                        {/* Toolbar */}
                        <div className="h-16 bg-gradient-to-b from-black/80 to-transparent absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-6 opacity-0 hover:opacity-100 transition-opacity duration-300">
                            <div className="text-white/80 font-mono text-sm">
                                EXHIBIT {currentSlideIndex + 1} / {playlist.length}
                            </div>
                            <div className="flex items-center gap-4">
                                <button onClick={() => setIsPresenting(false)} className="p-2 bg-white/10 hover:bg-white/20 rounded-full text-white backdrop-blur-sm transition-colors">
                                    <Minimize2 size={20} />
                                </button>
                            </div>
                        </div>

                        {/* Main Content */}
                        <div className="flex-1 flex items-center justify-center p-8 relative">
                            {/* Previous Button */}
                            <button
                                onClick={prevSlide}
                                disabled={currentSlideIndex === 0}
                                className="absolute left-4 p-4 text-white/50 hover:text-white disabled:opacity-0 transition-all hover:scale-110"
                            >
                                <ChevronLeft size={48} />
                            </button>

                            {/* Document Viewer (Placeholder for actual render) */}
                            <motion.div
                                key={currentSlideIndex}
                                initial={{ opacity: 0, x: 50 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -50 }}
                                className="w-full h-full max-w-6xl bg-white text-black rounded shadow-2xl overflow-hidden flex flex-col"
                            >
                                <div className="bg-gray-100 p-4 border-b flex justify-between items-center">
                                    <h2 className="font-bold text-lg truncate">{playlist[currentSlideIndex].doc.filename}</h2>
                                    <span className="text-xs text-gray-500 uppercase font-mono">{playlist[currentSlideIndex].doc.id}</span>
                                </div>
                                <div className="flex-1 flex items-center justify-center bg-gray-50">
                                    <div className="text-center">
                                        <FileText size={64} className="mx-auto text-gray-300 mb-4" />
                                        <p className="text-gray-500">Document Preview</p>
                                        <p className="text-xs text-gray-400 mt-2">Full rendering would occur here using PDF.js or similar.</p>
                                    </div>
                                </div>
                            </motion.div>

                            {/* Next Button */}
                            <button
                                onClick={nextSlide}
                                disabled={currentSlideIndex === playlist.length - 1}
                                className="absolute right-4 p-4 text-white/50 hover:text-white disabled:opacity-0 transition-all hover:scale-110"
                            >
                                <ChevronRight size={48} />
                            </button>
                        </div>

                        {/* Bottom Bar (Thumbnails) */}
                        <div className="h-24 bg-black/80 border-t border-white/10 flex items-center gap-4 px-8 overflow-x-auto custom-scrollbar">
                            {playlist.map((item, idx) => (
                                <button
                                    key={item.id}
                                    onClick={() => setCurrentSlideIndex(idx)}
                                    className={`h-16 aspect-video rounded border-2 transition-all overflow-hidden relative
                                        ${currentSlideIndex === idx ? 'border-halo-cyan scale-110' : 'border-white/20 hover:border-white/50 opacity-50 hover:opacity-100'}
                                    `}
                                >
                                    <div className="absolute inset-0 flex items-center justify-center bg-white/10">
                                        <span className="font-mono font-bold text-xs text-white">{idx + 1}</span>
                                    </div>
                                </button>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
