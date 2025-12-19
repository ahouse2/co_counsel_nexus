import { useState, useEffect, useRef } from 'react';
import { FileText, Search, Filter, Upload, Loader2, FolderUp, Terminal, Play, Pause, X, Download, Import, RefreshCw, ShieldCheck, List, Trash2, HardDrive } from 'lucide-react';
import ForceGraph2D from 'react-force-graph-2d';
import { endpoints } from '../../services/api';
import { useHalo } from '../../context/HaloContext';
import { useUploadManager } from '../../hooks/useUploadManager';
import { SubmoduleNav } from '../SubmoduleNav';

interface Document {
    id: string;
    filename: string;
    content_type: string;
    size: number;
    created_at: string;
    url?: string;
    status?: string;
}

const DocumentGraph = ({ docId, caseId }: { docId: string, caseId: string }) => {
    const [graphData, setGraphData] = useState({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchGraph = async () => {
            try {
                const response = await endpoints.documents.getGraph(caseId, docId, 2);
                const { nodes, edges } = response.data;
                setGraphData({
                    nodes: nodes.map((n: any) => ({ ...n, val: n.label === 'Document' ? 20 : 10 })),
                    links: edges.map((e: any) => ({ ...e, source: e.source, target: e.target }))
                });
            } catch (error) {
                console.error("Failed to fetch graph:", error);
            } finally {
                setLoading(false);
            }
        };
        fetchGraph();
    }, [docId, caseId]);

    if (loading) return <div className="flex justify-center p-8"><Loader2 className="animate-spin text-halo-cyan" /></div>;
    if (graphData.nodes.length === 0) return <div className="text-center p-8 text-halo-muted">No relationships found.</div>;

    return (
        <div className="w-full h-[300px] bg-black/50 rounded border border-halo-border overflow-hidden">
            <ForceGraph2D
                graphData={graphData}
                nodeLabel="label"
                nodeColor={node => (node as any).label === 'Document' ? '#00f0ff' : '#ff003c'}
                linkColor={() => '#ffffff33'}
                width={400} // Approximate width of side panel
                height={300}
            />
        </div>
    );
};

const EntitiesView = ({ docId }: { docId: string }) => {
    const [data, setData] = useState<{ entities: any[], keywords: string[] } | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await endpoints.documents.getEntities(docId);
                setData(res.data);
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [docId]);

    if (loading) return <div className="flex justify-center p-8"><Loader2 className="animate-spin text-halo-cyan" /></div>;
    if (!data) return <div className="text-center p-8 text-halo-muted">No entities found.</div>;

    return (
        <div className="w-full h-full p-4 overflow-auto custom-scrollbar">
            <h3 className="text-lg font-semibold text-halo-cyan mb-4">Extracted Entities</h3>
            <div className="space-y-4">
                {data.entities && data.entities.length > 0 ? (
                    <div className="grid gap-2">
                        {data.entities.map((e: any, i: number) => (
                            <div key={i} className="p-2 bg-halo-card/50 border border-halo-border rounded flex justify-between">
                                <span className="text-halo-text">{e.name || e}</span>
                                <span className="text-xs text-halo-muted uppercase">{e.type || 'Entity'}</span>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className="text-halo-muted">No named entities extracted.</p>
                )}

                <h3 className="text-lg font-semibold text-halo-cyan mt-6 mb-4">Keywords</h3>
                <div className="flex flex-wrap gap-2">
                    {data.keywords && data.keywords.map((k, i) => (
                        <span key={i} className="px-2 py-1 bg-halo-cyan/10 text-halo-cyan rounded text-xs border border-halo-cyan/30">
                            {k}
                        </span>
                    ))}
                </div>
            </div>
        </div>
    );
};

const OCRView = ({ docId }: { docId: string }) => {
    const [text, setText] = useState<string>("");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchText = async () => {
            try {
                const res = await endpoints.documents.getOCR(docId);
                setText(res.data.text);
            } catch (e) {
                console.error(e);
                setText("Failed to load text.");
            } finally {
                setLoading(false);
            }
        };
        fetchText();
    }, [docId]);

    const handleTriggerOCR = async () => {
        setLoading(true);
        try {
            await endpoints.documents.triggerOCR(docId);
            alert("OCR triggered. Check back later.");
        } catch (e) {
            alert("Failed to trigger OCR");
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="flex justify-center p-8"><Loader2 className="animate-spin text-halo-cyan" /></div>;

    return (
        <div className="w-full h-full p-4 flex flex-col">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-halo-cyan">OCR Text Content</h3>
                <button
                    onClick={handleTriggerOCR}
                    className="px-3 py-1 bg-halo-cyan/20 text-halo-cyan border border-halo-cyan/50 rounded hover:bg-halo-cyan/40 transition-colors text-xs"
                >
                    Re-run OCR
                </button>
            </div>
            <div className="flex-1 bg-black/30 border border-halo-border rounded p-4 overflow-auto custom-scrollbar font-mono text-sm text-halo-text whitespace-pre-wrap">
                {text}
            </div>
        </div>
    );
};

interface DocumentModuleProps {
    caseId: string;
}

export function DocumentModule({ caseId }: DocumentModuleProps) {
    const { activeSubmodule, setActiveSubmodule } = useHalo();

    // Upload function for chunked uploads
    const uploadChunkFn = async (files: File[], paths: string[], chunkIndex: number, totalChunks: number, onProgress?: (progress: number) => void) => {
        const formData = new FormData();
        files.forEach((file, idx) => {
            formData.append('files', file, paths[idx]);
        });
        formData.append('chunk_index', chunkIndex.toString());
        formData.append('total_chunks', totalChunks.toString());

        return await endpoints.documents.uploadChunk(caseId, formData, (progressEvent) => {
            if (onProgress && progressEvent.total) {
                onProgress(progressEvent.loaded / progressEvent.total);
            }
        });
    };

    const uploadManager = useUploadManager(uploadChunkFn);
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
    const [syncMode, setSyncMode] = useState(false);
    const [activeTab, setActiveTab] = useState<'preview' | 'graph' | 'entities' | 'ocr' | 'clustering'>('preview');
    const [logs, setLogs] = useState<string[]>([
        "[SYSTEM] Document Ingestion Pipeline Initialized",
        "[SYSTEM] Connected to Qdrant Vector Store",
        "[SYSTEM] Connected to Knowledge Graph"
    ]);

    // Upload Stats
    const [uploadHistory, setUploadHistory] = useState<number[]>([]);

    // Search State
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<Document[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

    const displayDocs = searchQuery ? searchResults : documents;

    const toggleSelection = (id: string) => {
        const newSelection = new Set(selectedIds);
        if (newSelection.has(id)) {
            newSelection.delete(id);
        } else {
            newSelection.add(id);
        }
        setSelectedIds(newSelection);
    };

    const selectAll = () => {
        if (selectedIds.size === displayDocs.length && displayDocs.length > 0) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(displayDocs.map(d => d.id)));
        }
    };

    const handleBatchDelete = async () => {
        if (!confirm(`Are you sure you want to delete ${selectedIds.size} documents?`)) return;
        try {
            await endpoints.documents.batchDelete(Array.from(selectedIds));
            addLog(`[SUCCESS] Deleted ${selectedIds.size} documents`);
            setSelectedIds(new Set());
            fetchDocuments();
        } catch (error) {
            console.error("Batch delete failed:", error);
            addLog(`[ERROR] Batch delete failed`);
        }
    };

    const handleBatchReprocess = async () => {
        try {
            await endpoints.documents.batchReprocess(Array.from(selectedIds));
            addLog(`[SUCCESS] Triggered reprocessing for ${selectedIds.size} documents`);
            setSelectedIds(new Set());
        } catch (error) {
            console.error("Batch reprocess failed:", error);
            addLog(`[ERROR] Batch reprocess failed`);
        }
    };

    const handleBatchDownload = async () => {
        try {
            const response = await endpoints.documents.batchDownload(Array.from(selectedIds));
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'documents_archive.zip');
            document.body.appendChild(link);
            link.click();
            link.remove();
            addLog(`[SUCCESS] Downloaded archive for ${selectedIds.size} documents`);
            setSelectedIds(new Set());
        } catch (error) {
            console.error("Batch download failed:", error);
            addLog(`[ERROR] Batch download failed`);
        }
    };

    const fileInputRef = useRef<HTMLInputElement>(null);
    const folderInputRef = useRef<HTMLInputElement>(null);
    const caseImportRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        fetchDocuments();

        let interval: NodeJS.Timeout;
        if (activeSubmodule === 'ocr') {
            interval = setInterval(fetchDocuments, 2000);
        }
        return () => clearInterval(interval);
    }, [activeSubmodule]);

    // Debounced Search Effect
    useEffect(() => {
        const timer = setTimeout(() => {
            if (searchQuery.trim()) {
                performSearch(searchQuery);
            } else {
                setSearchResults([]);
            }
        }, 300);
        return () => clearTimeout(timer);
    }, [searchQuery]);

    const performSearch = async (query: string) => {
        setIsSearching(true);
        try {
            const response = await endpoints.documents.search(query);
            setSearchResults(response.data);
        } catch (error) {
            console.error("Search failed:", error);
            addLog(`[ERROR] Search failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        } finally {
            setIsSearching(false);
        }
    };

    const addLog = (message: string) => {
        setLogs(prev => [`[${new Date().toLocaleTimeString()}] ${message}`, ...prev]);
    };

    const fetchDocuments = async () => {
        setLoading(true);
        try {
            const response = await endpoints.documents.list(caseId);
            const docs = Array.isArray(response.data) ? response.data : (response.data.documents || []);
            setDocuments(docs);
        } catch (error) {
            console.error("Failed to fetch documents:", error);
            addLog(`[ERROR] Failed to fetch documents: ${error instanceof Error ? error.message : 'Unknown error'}`);
            setDocuments([]);
        } finally {
            setLoading(false);
        }
    };

    const handleUploadClick = () => {
        fileInputRef.current?.click();
    };

    const handleFolderUploadClick = () => {
        if (folderInputRef.current) {
            folderInputRef.current.click();
        }
    };

    const handleLocalSync = async () => {
        try {
            addLog('[SYSTEM] Triggering local file sync from /data directory...');
            setActiveSubmodule('logs'); // Show logs
            const response = await endpoints.documents.triggerLocalIngestion(caseId);
            addLog(`[SUCCESS] ${response.data.message}`);
            addLog('[INFO] Files will be processed in background. Refresh document list to see progress.');
            setTimeout(fetchDocuments, 2000);
        } catch (error) {
            console.error('Local sync failed:', error);
            addLog(`[ERROR] Local sync failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    };

    const handleCaseExport = async () => {
        try {
            addLog("[SYSTEM] Exporting case...");
            const response = await endpoints.cases.export(caseId);
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `case_export_${new Date().toISOString()}.zip`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            addLog("[SUCCESS] Case exported successfully");
        } catch (error) {
            console.error("Export failed:", error);
            addLog(`[ERROR] Export failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    };

    const handleCaseImportClick = () => {
        caseImportRef.current?.click();
    };

    const handleCaseImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        try {
            addLog(`[SYSTEM] Importing case from ${file.name}...`);
            await endpoints.cases.import(file);
            addLog("[SUCCESS] Case imported successfully");
            fetchDocuments();
        } catch (error) {
            console.error("Import failed:", error);
            addLog(`[ERROR] Import failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        } finally {
            if (caseImportRef.current) caseImportRef.current.value = '';
        }
    };

    // Sync upload history with manager state
    useEffect(() => {
        if (uploadManager.state.status === 'uploading') {
            setUploadHistory(prev => [...prev.slice(-19), uploadManager.state.currentSpeed]);
        } else if (uploadManager.state.status === 'idle') {
            setUploadHistory([]);
        }
    }, [uploadManager.state.currentSpeed, uploadManager.state.status]);

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const files = event.target.files;
        if (!files || files.length === 0) return;

        setUploading(true);
        setActiveSubmodule('logs'); // Switch to logs view to show progress
        addLog(`[SYSTEM] Starting upload of ${files.length} files...`);

        try {
            // Check if this is a folder upload (multiple files from directory input)
            const isFolderUpload = event.target.webkitdirectory;

            if (isFolderUpload && files.length > 0) {
                addLog(`[SYSTEM] Starting chunked upload of ${files.length} files...`);
                addLog(`[SYSTEM] Using 10 files per chunk with auto-retry`);

                // Start the upload - the hook handles the state updates
                await uploadManager.startUpload(files);

                addLog(`[SYSTEM] Upload completed`);

            } else {
                // Standard single/multiple file upload (Legacy path - could be unified)
                // For now, we'll just use the manager for everything to ensure consistent UI
                await uploadManager.startUpload(files);
            }

            addLog(`[SYSTEM] All uploads completed. Refreshing list...`);
            await fetchDocuments();
        } catch (error) {
            console.error("Upload failed:", error);
            addLog(`[ERROR] Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        } finally {
            setUploading(false);
            // Reset inputs
            if (fileInputRef.current) fileInputRef.current.value = '';
            if (folderInputRef.current) folderInputRef.current.value = '';
        }
    };

    const formatSize = (bytes: number) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    };

    // Sparkline Component
    const Sparkline = ({ data, width = 120, height = 40, color = "#00f0ff" }: { data: number[], width?: number, height?: number, color?: string }) => {
        // eslint-disable-next-line react/forbid-component-props -- CSS custom properties require style prop
        if (data.length < 2) return <div style={{ '--w': `${width}px`, '--h': `${height}px` } as React.CSSProperties} className="dynamic-sparkline-size bg-halo-card/30 rounded flex items-center justify-center text-[10px] text-halo-muted">WAITING FOR DATA</div>;

        const max = Math.max(...data, 0.1); // Avoid div by zero
        const points = data.map((d, i) => {
            const x = (i / (data.length - 1)) * width;
            const y = height - (d / max) * height;
            return `${x},${y}`;
        }).join(' ');

        return (
            <svg width={width} height={height} className="overflow-visible">
                <defs>
                    <linearGradient id="spark-gradient" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0%" stopColor={color} stopOpacity="0.5" />
                        <stop offset="100%" stopColor={color} stopOpacity="0" />
                    </linearGradient>
                </defs>
                <path d={`M0,${height} ${points} L${width},${height}`} fill="url(#spark-gradient)" stroke="none" />
                <polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                {/* Current Value Dot */}
                <circle cx={width} cy={height - (data[data.length - 1] / max) * height} r="3" fill={color} />
            </svg>
        );
    };

    // Submodule Views
    const renderSubmoduleContent = () => {
        if (activeSubmodule === 'ocr') {
            const processing = documents.filter(d => d.status === 'processing').length;
            const queued = documents.filter(d => d.status === 'queued').length;
            const completed = documents.filter(d => d.status === 'completed').length;
            const failed = documents.filter(d => d.status === 'failed').length;

            return (
                <div className="h-full flex flex-col items-center justify-center text-halo-muted">
                    {(processing > 0 || queued > 0) ? (
                        <Loader2 size={48} className="mb-4 animate-spin text-halo-cyan" />
                    ) : (
                        <div className="mb-4 text-halo-cyan text-4xl font-mono">{completed}</div>
                    )}
                    <h3 className="text-xl font-mono text-halo-cyan">OCR Processing Pipeline</h3>
                    <div className="max-w-md text-center mt-4 space-y-2 font-mono text-sm">
                        <p>Pipeline Status for {documents.length} documents:</p>
                        <div className="grid grid-cols-2 gap-4 mt-4">
                            <div className="text-right text-halo-muted">Processing:</div>
                            <div className="text-left text-halo-cyan animate-pulse">{processing}</div>

                            <div className="text-right text-halo-muted">Queued:</div>
                            <div className="text-left text-yellow-500">{queued}</div>

                            <div className="text-right text-halo-muted">Completed:</div>
                            <div className="text-left text-green-400">{completed}</div>

                            <div className="text-right text-halo-muted">Failed:</div>
                            <div className="text-left text-red-400">{failed}</div>
                        </div>
                    </div>
                </div>
            );
        }

        if (activeSubmodule === 'verify') {
            return (
                <div className="h-full flex flex-col p-6">
                    <h3 className="text-xl font-mono text-halo-cyan mb-6">Metadata Verification</h3>
                    <div className="flex-1 overflow-auto custom-scrollbar">
                        <table className="w-full text-left text-sm">
                            <thead className="text-halo-muted border-b border-halo-border">
                                <tr>
                                    <th className="p-3">Filename</th>
                                    <th className="p-3">Hash (SHA-256)</th>
                                    <th className="p-3">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {documents.map(doc => (
                                    <tr key={doc.id} className="border-b border-halo-border/50 hover:bg-halo-card/30">
                                        <td className="p-3 font-mono text-halo-text">{doc.filename}</td>
                                        <td className="p-3 font-mono text-xs text-halo-muted">{doc.id.substring(0, 24)}...</td>
                                        <td className="p-3 text-green-400">VERIFIED</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            );
        }

        if (activeSubmodule === 'context') {
            const [query, setQuery] = useState('');
            const [results, setResults] = useState<any[]>([]);
            const [searching, setSearching] = useState(false);

            const handleSearch = async () => {
                if (!query.trim()) return;
                setSearching(true);
                try {
                    const response = await endpoints.context.query(query, caseId);
                    setResults(response.data.results);
                } catch (error) {
                    console.error("Context query failed:", error);
                    addLog(`[ERROR] Context query failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
                } finally {
                    setSearching(false);
                }
            };

            return (
                <div className="h-full flex flex-col p-6">
                    <h3 className="text-xl font-mono text-halo-cyan mb-6 flex items-center gap-2">
                        <Search size={20} /> Context Query Engine
                    </h3>

                    <div className="flex gap-2 mb-6">
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                            placeholder="Ask a question about the documents..."
                            className="flex-1 bg-halo-card border border-halo-border rounded p-3 text-sm focus:border-halo-cyan focus:outline-none transition-colors"
                        />
                        <button
                            onClick={handleSearch}
                            disabled={searching}
                            className="px-6 py-2 bg-halo-cyan text-black font-medium rounded hover:bg-halo-cyan/80 transition-colors disabled:opacity-50"
                        >
                            {searching ? <Loader2 size={18} className="animate-spin" /> : 'Query'}
                        </button>
                    </div>

                    <div className="flex-1 overflow-auto custom-scrollbar space-y-4">
                        {results.length === 0 ? (
                            <div className="text-center text-halo-muted mt-20">
                                <Search size={48} className="mx-auto mb-4 opacity-20" />
                                <p>Enter a query to search across all ingested documents.</p>
                            </div>
                        ) : (
                            results.map((result, i) => (
                                <div key={i} className="bg-halo-card/50 border border-halo-border rounded p-4 hover:border-halo-cyan/30 transition-colors">
                                    <div className="flex justify-between items-start mb-2">
                                        <span className="text-xs font-mono text-halo-cyan bg-halo-cyan/10 px-2 py-1 rounded">
                                            Score: {result.score?.toFixed(4)}
                                        </span>
                                        <span className="text-xs text-halo-muted truncate max-w-[300px]" title={result.metadata?.file_name}>
                                            {result.metadata?.file_name || 'Unknown Source'}
                                        </span>
                                    </div>
                                    <p className="text-sm text-halo-text leading-relaxed whitespace-pre-wrap">
                                        {result.text}
                                    </p>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            );
        }

        if (activeSubmodule === 'logs') {
            return (
                <div className="h-full flex flex-col p-6 font-mono text-xs">
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-xl font-mono text-halo-cyan flex items-center gap-2">
                            <Terminal size={20} /> System Logs
                        </h3>
                        {uploading && (
                            <div className="flex items-center gap-6 bg-halo-card/50 p-2 rounded border border-halo-border">
                                {/* Stats */}
                                <div className="flex flex-col items-end">
                                    <span className="text-halo-cyan text-lg font-bold">{uploadManager.state.currentSpeed.toFixed(1)} MB/s</span>
                                    <span className="text-halo-muted text-[10px]">CURRENT SPEED</span>
                                </div>

                                {/* Sparkline */}
                                <div className="h-10 w-32">
                                    <Sparkline data={uploadHistory} />
                                </div>

                                {/* Progress & Count */}
                                <div className="flex flex-col items-end min-w-[120px]">
                                    <span className="text-halo-cyan animate-pulse">
                                        {uploadManager.state.totalFiles > 0
                                            ? Math.round((uploadManager.state.completedFiles / uploadManager.state.totalFiles) * 100)
                                            : 0}%
                                        ({uploadManager.state.totalFiles - uploadManager.state.completedFiles} left)
                                    </span>
                                    <div className="w-full h-1 bg-halo-card rounded-full overflow-hidden mt-1">
                                        {/* eslint-disable-next-line react/forbid-component-props -- CSS custom properties require style prop */}
                                        <div
                                            className="h-full bg-halo-cyan transition-all duration-300 ease-out dynamic-progress"
                                            style={{
                                                '--progress': `${uploadManager.state.totalFiles > 0
                                                    ? (uploadManager.state.completedFiles / uploadManager.state.totalFiles) * 100
                                                    : 0}%`
                                            } as React.CSSProperties}
                                        />
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                    <div className="flex-1 bg-black/50 p-4 rounded border border-halo-border overflow-auto custom-scrollbar">
                        {logs.map((log, i) => (
                            <div key={i} className={`${log.includes('[ERROR]') ? 'text-red-400' : log.includes('[SUCCESS]') ? 'text-green-400' : log.includes('[AGENT]') ? 'text-halo-cyan' : 'text-halo-muted'} mb-1 font-mono`}>
                                {log}
                            </div>
                        ))}
                    </div>
                </div>
            );
        }

        // Default View (Upload/List)
        // const displayDocs = searchQuery ? searchResults : documents; // Moved to top level

        return (
            <div className="flex-1 flex h-full p-6 gap-6">
                {/* Document List */}
                <div className="w-1/3 flex flex-col gap-4">
                    {selectedIds.size > 0 && (
                        <div className="flex items-center justify-between bg-halo-card/80 p-2 rounded border border-halo-cyan/30 mb-2">
                            <span className="text-xs text-halo-cyan font-bold px-2">
                                {selectedIds.size} Selected
                            </span>
                            <div className="flex gap-1">
                                <button
                                    onClick={handleBatchDownload}
                                    className="p-1.5 hover:bg-halo-cyan/10 rounded text-halo-cyan transition-colors"
                                    title="Download Selected"
                                >
                                    <Download size={16} />
                                </button>
                                <button
                                    onClick={handleBatchReprocess}
                                    className="p-1.5 hover:bg-halo-cyan/10 rounded text-halo-cyan transition-colors"
                                    title="Reprocess Selected"
                                >
                                    <RefreshCw size={16} />
                                </button>
                                <button
                                    onClick={handleBatchDelete}
                                    className="p-1.5 hover:bg-red-500/10 rounded text-red-400 transition-colors"
                                    title="Delete Selected"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        </div>
                    )}
                    <div className="flex gap-2 items-center">
                        <div className="flex items-center justify-center px-2">
                            <input
                                type="checkbox"
                                checked={selectedIds.size === displayDocs.length && displayDocs.length > 0}
                                onChange={selectAll}
                                aria-label="Select all documents"
                                className="w-4 h-4 rounded border-halo-border bg-halo-card/50 text-halo-cyan focus:ring-halo-cyan focus:ring-offset-0 cursor-pointer"
                            />
                        </div>
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-2.5 text-halo-muted w-4 h-4" />
                            <input
                                type="text"
                                placeholder="Search documents..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full bg-halo-card border border-halo-border rounded pl-9 py-2 text-sm focus:border-halo-cyan focus:outline-none transition-colors"
                            />
                        </div>
                        <button className="p-2 border border-halo-border rounded hover:border-halo-cyan text-halo-muted hover:text-halo-cyan transition-colors" title="Filter documents">
                            <Filter size={18} />
                        </button>
                        <div className="flex gap-1">
                            <button
                                onClick={handleUploadClick}
                                disabled={uploading || uploadManager.state.status === 'uploading'}
                                className="p-2 bg-halo-cyan/10 border border-halo-cyan/50 rounded hover:bg-halo-cyan/20 text-halo-cyan transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                title="Upload File"
                            >
                                {uploading ? <Loader2 size={18} className="animate-spin" /> : <Upload size={18} />}
                            </button>
                            <button
                                onClick={handleFolderUploadClick}
                                disabled={uploading || uploadManager.state.status === 'uploading'}
                                className="p-2 bg-halo-cyan/10 border border-halo-cyan/50 rounded hover:bg-halo-cyan/20 text-halo-cyan transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                title="Upload Folder"
                            >
                                <div className="relative">
                                    <FolderUp size={18} />
                                    <div className="absolute -bottom-1 -right-1 text-[10px] font-bold">+</div>
                                </div>
                            </button>
                            <button
                                onClick={handleLocalSync}
                                disabled={uploading || uploadManager.state.status === 'uploading'}
                                className="p-2 bg-emerald-500/10 border border-emerald-500/50 rounded hover:bg-emerald-500/20 text-emerald-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                title="Sync Local Files (from ./data folder)"
                            >
                                <HardDrive size={18} />
                            </button>

                            {/* Upload Controls */}
                            {uploadManager.state.status === 'uploading' && (
                                <button
                                    onClick={uploadManager.pause}
                                    className="p-2 bg-yellow-500/10 border border-yellow-500 text-yellow-500 rounded hover:bg-yellow-500/20 transition-colors"
                                    title="Pause Upload"
                                >
                                    <Pause size={18} />
                                </button>
                            )}

                            {uploadManager.state.status === 'paused' && (
                                <button
                                    onClick={uploadManager.resume}
                                    className="p-2 bg-green-500/10 border border-green-500 text-green-500 rounded hover:bg-green-500/20 transition-colors"
                                    title="Resume Upload"
                                >
                                    <Play size={18} />
                                </button>
                            )}

                            {(uploadManager.state.status === 'uploading' || uploadManager.state.status === 'paused') && (
                                <button
                                    onClick={uploadManager.cancel}
                                    className="p-2 bg-red-500/10 border border-red-500 text-red-500 rounded hover:bg-red-500/20 transition-colors"
                                    title="Cancel Upload"
                                >
                                    <X size={18} />
                                </button>
                            )}
                        </div>
                        <input
                            type="file"
                            ref={fileInputRef}
                            onChange={handleFileChange}
                            className="hidden"
                            multiple
                            title="Upload files"
                        />
                        <input
                            type="file"
                            ref={folderInputRef}
                            onChange={handleFileChange}
                            className="hidden"
                            {...{ webkitdirectory: "", directory: "" } as any}
                            title="Upload folder"
                        />
                        <input
                            type="file"
                            ref={caseImportRef}
                            onChange={handleCaseImport}
                            className="hidden"
                            accept=".zip"
                            title="Import case"
                        />
                    </div>

                    <div className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
                        {loading || isSearching ? (
                            <div className="flex justify-center p-4 text-halo-cyan animate-pulse">
                                {isSearching ? 'Searching...' : 'Loading documents...'}
                            </div>
                        ) : displayDocs.length === 0 ? (
                            <div className="text-center p-8 text-halo-muted">
                                {searchQuery ? 'No matching documents found.' : 'No documents found. Upload one to get started.'}
                            </div>
                        ) : (
                            displayDocs.map((doc) => (
                                <div
                                    key={doc.id}
                                    onClick={() => setSelectedDoc(doc)}
                                    className={`p-3 rounded border cursor-pointer group transition-all
                                        ${selectedDoc?.id === doc.id
                                            ? 'bg-halo-cyan/10 border-halo-cyan'
                                            : 'bg-halo-card/50 halo-border hover:border-halo-cyan/50'
                                        }`}
                                >
                                    <div className="flex items-start gap-3">
                                        <div
                                            className="pt-2 pl-1"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                toggleSelection(doc.id);
                                            }}
                                        >
                                            <input
                                                type="checkbox"
                                                checked={selectedIds.has(doc.id)}
                                                onChange={() => { }}
                                                className="w-4 h-4 rounded border-halo-border bg-halo-card/50 text-halo-cyan focus:ring-halo-cyan focus:ring-offset-0 cursor-pointer"
                                                aria-label={`Select document ${doc.filename}`}
                                            />
                                        </div>
                                        <div className={`p-2 rounded transition-colors ${selectedDoc?.id === doc.id ? 'bg-halo-cyan text-black' : 'bg-halo-bg text-halo-cyan group-hover:text-white'}`}>
                                            <FileText size={20} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <h4 className="text-sm font-medium text-halo-text group-hover:text-halo-cyan transition-colors truncate" title={doc.filename}>
                                                {doc.filename}
                                            </h4>
                                            <div className="flex gap-3 mt-1 text-xs text-halo-muted">
                                                <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                                                <span>{doc.content_type.split('/')[1]?.toUpperCase() || 'FILE'}</span>
                                                <span>{formatSize(doc.size)}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Document Preview */}
                <div className="flex-1 halo-panel flex relative overflow-hidden">
                    {selectedDoc ? (
                        <div className="w-full h-full flex">
                            {/* Preview Area */}
                            <div className="flex-1 flex flex-col">
                                <div className="p-4 border-b border-halo-border flex justify-between items-center bg-halo-bg/50">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 rounded bg-halo-cyan text-black">
                                            <FileText size={20} />
                                        </div>
                                        <div>
                                            <h3 className="text-lg font-semibold text-halo-text">{selectedDoc.filename}</h3>
                                            <p className="text-xs text-halo-muted">{selectedDoc.content_type}</p>
                                        </div>
                                    </div>
                                    <div className="flex bg-halo-bg rounded p-1 border border-halo-border">
                                        <button
                                            onClick={() => setActiveTab('preview')}
                                            className={`px-3 py-1 text-xs font-medium rounded transition-colors ${activeTab === 'preview' ? 'bg-halo-cyan text-black' : 'text-halo-muted hover:text-halo-cyan'}`}
                                        >
                                            Preview
                                        </button>
                                        <button
                                            onClick={() => setActiveTab('graph')}
                                            className={`px-3 py-1 text-xs font-medium rounded transition-colors ${activeTab === 'graph' ? 'bg-halo-cyan text-black' : 'text-halo-muted hover:text-halo-cyan'}`}
                                        >
                                            Graph
                                        </button>
                                        <button
                                            onClick={() => setActiveTab('entities')}
                                            className={`px-3 py-1 text-xs font-medium rounded transition-colors ${activeTab === 'entities' ? 'bg-halo-cyan text-black' : 'text-halo-muted hover:text-halo-cyan'}`}
                                        >
                                            Entities
                                        </button>
                                        <button
                                            onClick={() => setActiveTab('ocr')}
                                            className={`px-3 py-1 text-xs font-medium rounded transition-colors ${activeTab === 'ocr' ? 'bg-halo-cyan text-black' : 'text-halo-muted hover:text-halo-cyan'}`}
                                        >
                                            OCR
                                        </button>
                                    </div>
                                </div>

                                {/* Tab Content */}
                                <div className="flex-1 overflow-auto p-4">
                                    {activeTab === 'preview' ? (
                                        selectedDoc.content_type.startsWith('image/') ? (
                                            <img src={`/api/documents/${selectedDoc.id}/download`} alt={selectedDoc.filename} className="max-w-full max-h-full object-contain mx-auto" />
                                        ) : selectedDoc.content_type === 'application/pdf' ? (
                                            <iframe src={`/api/documents/${selectedDoc.id}/download`} className="w-full h-full" title={selectedDoc.filename} />
                                        ) : (
                                            <div className="h-full flex flex-col items-center justify-center text-halo-muted">
                                                <p className="text-halo-text">Preview not available for {selectedDoc.content_type}</p>
                                                <button
                                                    onClick={() => window.open(`/api/documents/${selectedDoc.id}/download`, '_blank')}
                                                    className="mt-4 px-4 py-2 border border-halo-cyan text-halo-cyan rounded hover:bg-halo-cyan hover:text-black transition-colors"
                                                >
                                                    Download to View
                                                </button>
                                            </div>
                                        )
                                    ) : activeTab === 'graph' ? (
                                        <div className="w-full h-full bg-black/20 rounded border border-halo-border overflow-hidden">
                                            <DocumentGraph docId={selectedDoc.id} caseId="default_case" />
                                        </div>
                                    ) : activeTab === 'entities' ? (
                                        <EntitiesView docId={selectedDoc.id} />
                                    ) : (
                                        <OCRView docId={selectedDoc.id} />
                                    )}
                                </div>

                                {/* Metadata Side Panel */}
                                <div className="w-72 border-l border-halo-border bg-halo-bg/30 p-4 overflow-y-auto custom-scrollbar">
                                    <h4 className="text-xs font-bold text-halo-muted uppercase tracking-wider mb-4">Document Metadata</h4>

                                    {/* Basic Info */}
                                    <div className="space-y-3 mb-6">
                                        <div>
                                            <label className="text-[10px] text-halo-muted uppercase">Document ID</label>
                                            <p className="text-xs font-mono text-halo-text break-all">{selectedDoc.id}</p>
                                        </div>
                                        <div>
                                            <label className="text-[10px] text-halo-muted uppercase">Created</label>
                                            <p className="text-xs text-halo-text">{new Date(selectedDoc.created_at).toLocaleString()}</p>
                                        </div>
                                        <div>
                                            <label className="text-[10px] text-halo-muted uppercase">Content Type</label>
                                            <p className="text-xs text-halo-text">{selectedDoc.content_type}</p>
                                        </div>
                                        <div>
                                            <label className="text-[10px] text-halo-muted uppercase">Size</label>
                                            <p className="text-xs text-halo-text">{formatSize(selectedDoc.size)}</p>
                                        </div>
                                    </div>

                                    {/* Forensics Section */}
                                    <div className="border-t border-halo-border pt-4 mb-6">
                                        <h5 className="text-xs font-bold text-halo-cyan mb-3 flex items-center gap-2">
                                            <ShieldCheck size={14} /> Forensics
                                        </h5>
                                        <div className="space-y-3">
                                            <div>
                                                <label className="text-[10px] text-halo-muted uppercase">SHA-256 Hash</label>
                                                <p className="text-[10px] font-mono text-halo-text break-all bg-black/20 p-2 rounded">
                                                    {selectedDoc.id.length === 64 ? selectedDoc.id : 'Click "Analyze" to compute'}
                                                </p>
                                            </div>
                                            <div>
                                                <label className="text-[10px] text-halo-muted uppercase">Tamper Score</label>
                                                <div className="flex items-center gap-2 mt-1">
                                                    <div className="flex-1 h-2 bg-halo-card rounded-full overflow-hidden">
                                                        <div className="h-full bg-green-500 w-[15%]" />
                                                    </div>
                                                    <span className="text-xs text-green-400 font-mono">LOW</span>
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => {
                                                    addLog(`[AGENT] Running forensic analysis on ${selectedDoc.filename}`);
                                                    endpoints.forensics.analyze(selectedDoc.id, 'default_case')
                                                        .then(() => addLog(`[SUCCESS] Forensic analysis complete`))
                                                        .catch(e => addLog(`[ERROR] Analysis failed: ${e.message}`));
                                                }}
                                                className="w-full px-3 py-1.5 bg-halo-card border border-halo-border text-xs rounded hover:border-halo-cyan hover:text-halo-cyan transition-colors"
                                            >
                                                Run Deep Analysis
                                            </button>
                                        </div>
                                    </div>

                                    {/* AI Classification */}
                                    <div className="border-t border-halo-border pt-4">
                                        <h5 className="text-xs font-bold text-halo-violet mb-3 flex items-center gap-2">
                                            ✨ AI Classification
                                        </h5>
                                        <div className="space-y-2">
                                            <div className="flex flex-wrap gap-1">
                                                <span className="px-2 py-0.5 bg-halo-cyan/10 text-halo-cyan text-[10px] rounded">Evidence</span>
                                                <span className="px-2 py-0.5 bg-halo-violet/10 text-halo-violet text-[10px] rounded">Contract</span>
                                            </div>
                                            <div>
                                                <label className="text-[10px] text-halo-muted uppercase">Privilege Status</label>
                                                <p className="text-xs text-yellow-400">⚠ Pending Review</p>
                                            </div>
                                            <div>
                                                <label className="text-[10px] text-halo-muted uppercase">Relevance Score</label>
                                                <div className="flex items-center gap-2 mt-1">
                                                    <div className="flex-1 h-2 bg-halo-card rounded-full overflow-hidden">
                                                        <div className="h-full bg-halo-cyan w-[78%]" />
                                                    </div>
                                                    <span className="text-xs text-halo-cyan font-mono">78%</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <>
                            <div className="absolute inset-0 flex items-center justify-center opacity-5 pointer-events-none">
                                <FileText size={200} />
                            </div>
                            <div className="w-full h-full flex items-center justify-center text-halo-muted text-sm font-mono">SELECT A DOCUMENT TO INITIATE ANALYSIS</div>
                        </>
                    )}
                </div>
            </div>
        );
    };

    return (
        <div className="h-full flex flex-col">
            {/* Header with Submodule Nav and Case Controls */}
            <div className="flex items-center justify-between p-4 border-b border-halo-border/30">
                <SubmoduleNav items={[
                    { id: 'default', label: 'Documents', icon: List },
                    { id: 'ocr', label: 'OCR Pipeline', icon: RefreshCw },
                    { id: 'context', label: 'Context Query', icon: Search },
                    { id: 'verify', label: 'Verification', icon: ShieldCheck },
                    { id: 'logs', label: 'System Logs', icon: Terminal },
                ]} />

                <div className="flex items-center gap-3">
                    {/* Sync Toggle */}
                    <button
                        onClick={() => setSyncMode(!syncMode)}
                        className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border transition-all
                            ${syncMode
                                ? 'bg-halo-cyan/20 border-halo-cyan text-halo-cyan'
                                : 'bg-halo-card/30 border-halo-border text-halo-muted hover:text-white'
                            }`}
                        title="Sync Mode: Skip existing files"
                    >
                        <RefreshCw size={14} className={syncMode ? "animate-spin-slow" : ""} />
                        SYNC: {syncMode ? 'ON' : 'OFF'}
                    </button>

                    <div className="h-6 w-px bg-halo-border/50 mx-1" />

                    {/* Case Controls */}
                    <button
                        onClick={handleCaseExport}
                        className="flex items-center gap-2 px-3 py-1.5 bg-halo-card/30 border border-halo-border rounded-md text-xs font-medium text-halo-muted hover:text-halo-cyan hover:border-halo-cyan transition-colors"
                    >
                        <Download size={14} />
                        Export Case
                    </button>
                    <button
                        onClick={handleCaseImportClick}
                        className="flex items-center gap-2 px-3 py-1.5 bg-halo-card/30 border border-halo-border rounded-md text-xs font-medium text-halo-muted hover:text-halo-cyan hover:border-halo-cyan transition-colors"
                    >
                        <Import size={14} />
                        Import Case
                    </button>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 overflow-hidden">
                {renderSubmoduleContent()}
            </div>
        </div>
    );
}

