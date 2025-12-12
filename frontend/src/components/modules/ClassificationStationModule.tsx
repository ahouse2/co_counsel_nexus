import { useState, useEffect } from 'react';
import { endpoints } from '../../services/api';
import { Tag, CheckCircle, Edit2, Save, FileText, RefreshCw, Loader2, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { playSound } from '../../utils/sounds';

interface ClassifiedDoc {
    id: string;
    filename: string;
    categories: string[];
    tags: string[];
    metadata: {
        summary?: string;
        key_entities?: string[];
        sentiment?: string;
    };
    status: 'pending_review' | 'reviewed';
}

export function ClassificationStationModule() {
    const [docs, setDocs] = useState<ClassifiedDoc[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedDoc, setSelectedDoc] = useState<ClassifiedDoc | null>(null);
    const [isEditing, setIsEditing] = useState(false);
    const [editForm, setEditForm] = useState<{ categories: string, tags: string }>({ categories: '', tags: '' });
    const [isSaving, setIsSaving] = useState(false);

    // Mock data for now until backend endpoint is ready
    const generateMockDocs = (): ClassifiedDoc[] => [
        {
            id: '1',
            filename: 'Settlement_Offer_v2.pdf',
            categories: ['Correspondence', 'Financial'],
            tags: ['Settlement', 'Urgent', 'Confidential'],
            metadata: {
                summary: 'Offer to settle for $50,000 with NDA clause.',
                key_entities: ['Doe Plaintiff', 'Smith Defendant', 'InsurCo'],
                sentiment: 'Conciliatory'
            },
            status: 'pending_review'
        },
        {
            id: '2',
            filename: 'Incident_Report_Final.docx',
            categories: ['Evidence', 'Internal'],
            tags: ['Safety Violation', 'Negligence'],
            metadata: {
                summary: 'Internal report admitting to safety protocol breach on day of incident.',
                sentiment: 'Negative'
            },
            status: 'pending_review'
        }
    ];

    const fetchDocs = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await endpoints.documents.pendingReview('default_case');
            if (response.data && Array.isArray(response.data) && response.data.length > 0) {
                const transformed: ClassifiedDoc[] = response.data.map((doc: any) => ({
                    id: doc.id,
                    filename: doc.filename || doc.id,
                    categories: doc.categories || doc.keywords || [],
                    tags: doc.tags || [],
                    metadata: {
                        summary: doc.summary || doc.forensic_metadata?.summary,
                        key_entities: doc.key_entities || [],
                        sentiment: doc.sentiment
                    },
                    status: 'pending_review' as const
                }));
                setDocs(transformed);
            } else {
                console.log("No pending documents found, showing demo data");
                setDocs(generateMockDocs());
            }
        } catch (err) {
            console.error("Failed to fetch pending documents:", err);
            setError("Failed to load documents. Showing demo data.");
            setDocs(generateMockDocs());
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDocs();
    }, []);

    const handleEdit = (doc: ClassifiedDoc) => {
        setEditForm({
            categories: doc.categories.join(', '),
            tags: doc.tags.join(', ')
        });
        setIsEditing(true);
    };

    const saveEdits = async () => {
        if (!selectedDoc) return;
        setIsSaving(true);
        const updatedCategories = editForm.categories.split(',').map(s => s.trim()).filter(Boolean);
        const updatedTags = editForm.tags.split(',').map(s => s.trim()).filter(Boolean);

        try {
            await endpoints.documents.updateMetadata(selectedDoc.id, {
                categories: updatedCategories,
                tags: updatedTags
            });
            const updatedDoc = { ...selectedDoc, categories: updatedCategories, tags: updatedTags };
            setDocs(docs.map(d => d.id === selectedDoc.id ? updatedDoc : d));
            setSelectedDoc(updatedDoc);
            setIsEditing(false);
            playSound.success();
        } catch (err) {
            console.error("Failed to save edits:", err);
            const updatedDoc = { ...selectedDoc, categories: updatedCategories, tags: updatedTags };
            setDocs(docs.map(d => d.id === selectedDoc.id ? updatedDoc : d));
            setSelectedDoc(updatedDoc);
            setIsEditing(false);
        } finally {
            setIsSaving(false);
        }
    };

    const handleApprove = async (doc: ClassifiedDoc) => {
        try {
            await endpoints.documents.approveClassification(doc.id);
            setDocs(docs.filter(d => d.id !== doc.id));
            setSelectedDoc(null);
            playSound.success();
        } catch (err) {
            console.error("Failed to approve document:", err);
            setDocs(docs.filter(d => d.id !== doc.id));
            setSelectedDoc(null);
        }
    };

    return (
        <div className="h-full flex flex-col gap-6 p-6">
            {/* Error Toast */}
            {error && (
                <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 bg-yellow-500/20 border border-yellow-500/50 rounded-lg px-4 py-2 flex items-center gap-2 backdrop-blur-sm">
                    <AlertCircle className="w-5 h-5 text-yellow-400" />
                    <span className="text-yellow-300 text-sm">{error}</span>
                </div>
            )}

            {/* Header */}
            <div className="flex justify-between items-center">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-halo-cyan/10 rounded-lg border border-halo-cyan/30 shadow-[0_0_15px_rgba(0,240,255,0.2)] backdrop-blur-sm">
                        <Tag className="text-halo-cyan w-8 h-8" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider text-shadow-glow">Classification Station</h2>
                        <p className="text-halo-muted text-sm">Review AI-assigned tags and metadata</p>
                    </div>
                </div>
                <button
                    onClick={fetchDocs}
                    disabled={loading}
                    className="p-2 bg-halo-card border border-halo-border rounded hover:bg-halo-cyan/10 hover:border-halo-cyan transition-colors disabled:opacity-50"
                >
                    {loading ? <Loader2 size={20} className="animate-spin" /> : <RefreshCw size={20} />}
                </button>
            </div>

            <div className="flex-1 flex gap-6 overflow-hidden">
                {/* List */}
                <div className="w-1/3 flex flex-col gap-3 overflow-y-auto custom-scrollbar pr-2">
                    {docs.length === 0 && !loading && (
                        <div className="text-center text-halo-muted py-10 border border-dashed border-halo-border rounded-xl">
                            <CheckCircle className="mx-auto mb-2 opacity-50" size={32} />
                            <p>All caught up!</p>
                        </div>
                    )}

                    {docs.map(doc => (
                        <motion.div
                            key={doc.id}
                            layoutId={doc.id}
                            onClick={() => { setSelectedDoc(doc); setIsEditing(false); playSound.click(); }}
                            className={`p-4 rounded-xl border cursor-pointer transition-all ${selectedDoc?.id === doc.id
                                ? 'bg-halo-cyan/10 border-halo-cyan shadow-[0_0_10px_rgba(0,240,255,0.1)]'
                                : 'bg-black/40 border-halo-border/30 hover:bg-white/5 hover:border-halo-cyan/30'
                                }`}
                        >
                            <div className="flex items-start gap-3">
                                <FileText className="text-halo-cyan mt-1" size={20} />
                                <div className="flex-1 min-w-0">
                                    <h4 className="font-medium text-white truncate">{doc.filename}</h4>
                                    <div className="flex flex-wrap gap-1 mt-2">
                                        {doc.categories.slice(0, 2).map(c => (
                                            <span key={c} className="px-2 py-0.5 text-[10px] uppercase bg-purple-500/20 text-purple-300 rounded border border-purple-500/30">
                                                {c}
                                            </span>
                                        ))}
                                        {doc.tags.slice(0, 2).map(t => (
                                            <span key={t} className="px-2 py-0.5 text-[10px] uppercase bg-blue-500/20 text-blue-300 rounded border border-blue-500/30">
                                                {t}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>

                {/* Detail / Review Panel */}
                <div className="flex-1 bg-black/40 border border-halo-border/30 rounded-xl p-6 backdrop-blur-md flex flex-col relative overflow-hidden">
                    {selectedDoc ? (
                        <AnimatePresence mode='wait'>
                            <motion.div
                                key={selectedDoc.id}
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                className="flex-1 flex flex-col"
                            >
                                <div className="flex justify-between items-start mb-6">
                                    <h3 className="text-xl font-bold text-white">{selectedDoc.filename}</h3>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleEdit(selectedDoc)}
                                            className="px-3 py-1.5 bg-gray-800 text-gray-300 rounded hover:bg-gray-700 flex items-center gap-2 text-sm"
                                        >
                                            <Edit2 size={14} /> Edit
                                        </button>
                                        <button
                                            onClick={() => handleApprove(selectedDoc)}
                                            className="px-3 py-1.5 bg-halo-cyan text-black font-bold rounded hover:bg-white flex items-center gap-2 text-sm shadow-[0_0_10px_rgba(0,240,255,0.3)]"
                                        >
                                            <CheckCircle size={14} /> Approve
                                        </button>
                                    </div>
                                </div>

                                {isEditing ? (
                                    <div className="space-y-4 flex-1">
                                        <div>
                                            <label className="block text-xs text-halo-muted uppercase mb-1">Categories (comma separated)</label>
                                            <input
                                                value={editForm.categories}
                                                onChange={e => setEditForm({ ...editForm, categories: e.target.value })}
                                                className="w-full bg-black/50 border border-halo-border rounded p-2 text-white focus:border-halo-cyan outline-none"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs text-halo-muted uppercase mb-1">Tags (comma separated)</label>
                                            <input
                                                value={editForm.tags}
                                                onChange={e => setEditForm({ ...editForm, tags: e.target.value })}
                                                className="w-full bg-black/50 border border-halo-border rounded p-2 text-white focus:border-halo-cyan outline-none"
                                            />
                                        </div>
                                        <button
                                            onClick={saveEdits}
                                            disabled={isSaving}
                                            className="w-full py-2 bg-green-600/20 text-green-400 border border-green-600/50 rounded hover:bg-green-600/30 flex items-center justify-center gap-2 disabled:opacity-50"
                                        >
                                            {isSaving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                                            {isSaving ? 'Saving...' : 'Save Changes'}
                                        </button>
                                    </div>
                                ) : (
                                    <div className="space-y-6 flex-1 overflow-y-auto custom-scrollbar">
                                        {/* AI Summary */}
                                        <div className="p-4 bg-halo-cyan/5 border border-halo-cyan/20 rounded-lg">
                                            <h4 className="text-xs font-bold text-halo-cyan uppercase mb-2 flex items-center gap-2">
                                                <RefreshCw size={12} className="animate-spin-slow" /> AI Analysis
                                            </h4>
                                            <p className="text-gray-300 text-sm leading-relaxed">
                                                {selectedDoc.metadata.summary || "No summary available."}
                                            </p>
                                        </div>

                                        {/* Metadata Grid */}
                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="p-4 bg-white/5 rounded-lg border border-white/10">
                                                <h5 className="text-xs text-gray-500 uppercase mb-2">Sentiment</h5>
                                                <span className={`text-sm font-bold ${selectedDoc.metadata.sentiment === 'Negative' ? 'text-red-400' :
                                                    selectedDoc.metadata.sentiment === 'Conciliatory' ? 'text-green-400' :
                                                        'text-gray-300'
                                                    }`}>
                                                    {selectedDoc.metadata.sentiment || "Neutral"}
                                                </span>
                                            </div>
                                            <div className="p-4 bg-white/5 rounded-lg border border-white/10">
                                                <h5 className="text-xs text-gray-500 uppercase mb-2">Key Entities</h5>
                                                <div className="flex flex-wrap gap-1">
                                                    {selectedDoc.metadata.key_entities?.map(e => (
                                                        <span key={e} className="px-2 py-0.5 bg-black/50 rounded text-xs text-gray-300 border border-white/10">{e}</span>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>

                                        {/* Tags & Categories */}
                                        <div>
                                            <h5 className="text-xs text-gray-500 uppercase mb-2">Categories</h5>
                                            <div className="flex flex-wrap gap-2 mb-4">
                                                {selectedDoc.categories.map(c => (
                                                    <span key={c} className="px-3 py-1 bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded-full text-sm">
                                                        {c}
                                                    </span>
                                                ))}
                                            </div>

                                            <h5 className="text-xs text-gray-500 uppercase mb-2">Contextual Tags</h5>
                                            <div className="flex flex-wrap gap-2">
                                                {selectedDoc.tags.map(t => (
                                                    <span key={t} className="px-3 py-1 bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded-full text-sm">
                                                        {t}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </motion.div>
                        </AnimatePresence>
                    ) : (
                        <div className="flex-1 flex flex-col items-center justify-center text-halo-muted opacity-50">
                            <Tag size={64} className="mb-4" />
                            <p>Select a document to review</p>
                        </div>
                    )}
                </div>
            </div>
        </div >
    );
}
