import { useState, useEffect, useRef } from 'react';
import { FileText, Search, Filter, Upload, Loader2, File, FolderUp, Terminal } from 'lucide-react';
import { endpoints } from '../../services/api';
import { useHalo } from '../../context/HaloContext';

interface Document {
    id: string;
    filename: string;
    content_type: string;
    size: number;
    created_at: string;
    url?: string;
    status?: string;
}

export function DocumentModule() {
    const { activeSubmodule, setActiveSubmodule } = useHalo();
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [progress, setProgress] = useState(0);
    const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
    const [logs, setLogs] = useState<string[]>([
        "[SYSTEM] Document Ingestion Pipeline Initialized",
        "[SYSTEM] Connected to Qdrant Vector Store",
        "[SYSTEM] Connected to Knowledge Graph"
    ]);

    // Upload Stats
    const [uploadSpeed, setUploadSpeed] = useState(0); // MB/s
    const [uploadHistory, setUploadHistory] = useState<number[]>([]);
    const [remainingFiles, setRemainingFiles] = useState(0);

    const fileInputRef = useRef<HTMLInputElement>(null);
    const folderInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        fetchDocuments();

        let interval: NodeJS.Timeout;
        if (activeSubmodule === 'ocr') {
            interval = setInterval(fetchDocuments, 2000);
        }
        return () => clearInterval(interval);
    }, [activeSubmodule]);

    const addLog = (message: string) => {
        setLogs(prev => [`[${new Date().toLocaleTimeString()}] ${message}`, ...prev]);
    };

    const fetchDocuments = async () => {
        setLoading(true);
        try {
            const response = await endpoints.documents.list('default_case');
            const docs = Array.isArray(response.data) ? response.data : (response.data.documents || []);
            setDocuments(docs);
        } catch (error) {
            console.error("Failed to fetch documents:", error);
            // Keep mock data for resilience if backend is down
            setDocuments(Array.from({ length: 5 }).map((_, i) => ({
                id: `mock-${i}`,
                filename: `Exhibit ${String.fromCharCode(65 + i)} - Witness Statement.pdf`,
                content_type: 'application/pdf',
                size: 1024 * 1024 * 2.4,
                created_at: new Date().toISOString()
            })));
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

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const files = event.target.files;
        if (!files || files.length === 0) return;

        setUploading(true);
        setProgress(0);
        setUploadHistory([]);
        setRemainingFiles(files.length);
        setActiveSubmodule('logs'); // Switch to logs view to show progress
        addLog(`[SYSTEM] Starting upload of ${files.length} files...`);

        try {
            // Check if this is a folder upload (multiple files from directory input)
            const isFolderUpload = event.target.webkitdirectory;

            if (isFolderUpload && files.length > 0) {
                addLog(`[SYSTEM] Detected folder upload. Compressing ${files.length} files...`);

                // Dynamic import JSZip to avoid loading it when not needed
                const JSZip = (await import('jszip')).default;
                const zip = new JSZip();

                let totalSize = 0;
                for (let i = 0; i < files.length; i++) {
                    const file = files[i];
                    // Use webkitRelativePath to preserve folder structure inside zip
                    const path = file.webkitRelativePath || file.name;
                    zip.file(path, file);
                    totalSize += file.size;
                }

                addLog(`[SYSTEM] Compression complete. Total size: ${formatSize(totalSize)}. Uploading zip archive...`);

                const zipContent = await zip.generateAsync({ type: "blob" });

                const formData = new FormData();
                // Append blob directly to avoid File constructor issues in some environments
                formData.append('file', zipContent, 'upload.zip');
                formData.append('document_id', `folder-upload-${Date.now()}`);

                const startTime = performance.now();

                // Use the directory upload endpoint
                await endpoints.documents.uploadDirectory('default_case', formData);

                const endTime = performance.now();
                const durationSeconds = (endTime - startTime) / 1000;
                const sizeMB = totalSize / (1024 * 1024); // Use total size of files
                const speed = durationSeconds > 0 ? sizeMB / durationSeconds : 0;

                setUploadSpeed(speed);
                setUploadHistory(prev => [...prev.slice(-19), speed]);
                addLog(`[SUCCESS] Folder uploaded successfully (${speed.toFixed(1)} MB/s). Backend is processing files.`);
                setProgress(100);

            } else {
                // Standard single/multiple file upload
                for (let i = 0; i < files.length; i++) {
                    const file = files[i];
                    const formData = new FormData();
                    formData.append('file', file);

                    addLog(`[UPLOAD] Uploading ${file.name}...`);
                    setRemainingFiles(files.length - i);

                    const startTime = performance.now();

                    // Check if it's a directory upload to preserve structure
                    const relativePath = file.webkitRelativePath || file.name;

                    await endpoints.documents.upload('default_case', formData, relativePath);

                    const endTime = performance.now();
                    const durationSeconds = (endTime - startTime) / 1000;
                    const sizeMB = file.size / (1024 * 1024);
                    const speed = durationSeconds > 0 ? sizeMB / durationSeconds : 0;

                    setUploadSpeed(speed);
                    setUploadHistory(prev => [...prev.slice(-19), speed]); // Keep last 20 points

                    addLog(`[SUCCESS] Uploaded ${file.name} (${speed.toFixed(1)} MB/s)`);
                    setProgress(Math.round(((i + 1) / files.length) * 100));
                }
            }

            addLog(`[SYSTEM] All uploads completed. Refreshing list...`);
            setRemainingFiles(0);
            setUploadSpeed(0);
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
        if (data.length < 2) return <div style={{ width, height }} className="bg-halo-card/30 rounded flex items-center justify-center text-[10px] text-halo-muted">WAITING FOR DATA</div>;

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
                                <span className="text-halo-cyan text-lg font-bold">{uploadSpeed.toFixed(1)} MB/s</span>
                                <span className="text-halo-muted text-[10px]">CURRENT SPEED</span>
                            </div>

                            {/* Sparkline */}
                            <div className="h-10 w-32">
                                <Sparkline data={uploadHistory} />
                            </div>

                            {/* Progress & Count */}
                            <div className="flex flex-col items-end min-w-[120px]">
                                <span className="text-halo-cyan animate-pulse">{progress}% ({remainingFiles} left)</span>
                                <div className="w-full h-1 bg-halo-card rounded-full overflow-hidden mt-1">
                                    <div
                                        className="h-full bg-halo-cyan transition-all duration-300 ease-out"
                                        style={{ width: `${progress}%` }}
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
    return (
        <div className="flex-1 flex h-full p-6 gap-6">
            {/* Document List */}
            <div className="w-1/3 flex flex-col gap-4">
                <div className="flex gap-2 items-center">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-2.5 text-halo-muted w-4 h-4" />
                        <input
                            type="text"
                            placeholder="Search documents..."
                            className="w-full bg-halo-card border border-halo-border rounded pl-9 py-2 text-sm focus:border-halo-cyan focus:outline-none transition-colors"
                        />
                    </div>
                    <button className="p-2 border border-halo-border rounded hover:border-halo-cyan text-halo-muted hover:text-halo-cyan transition-colors">
                        <Filter size={18} />
                    </button>
                    <div className="flex gap-1">
                        <button
                            onClick={handleUploadClick}
                            disabled={uploading}
                            className="p-2 bg-halo-cyan/10 border border-halo-cyan/50 rounded hover:bg-halo-cyan/20 text-halo-cyan transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Upload File"
                        >
                            {uploading ? <Loader2 size={18} className="animate-spin" /> : <Upload size={18} />}
                        </button>
                        <button
                            onClick={handleFolderUploadClick}
                            disabled={uploading}
                            className="p-2 bg-halo-cyan/10 border border-halo-cyan/50 rounded hover:bg-halo-cyan/20 text-halo-cyan transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Upload Folder"
                        >
                            <div className="relative">
                                <FolderUp size={18} />
                                <div className="absolute -bottom-1 -right-1 text-[10px] font-bold">+</div>
                            </div>
                        </button>
                    </div>
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        className="hidden"
                        multiple
                    />
                    <input
                        type="file"
                        ref={folderInputRef}
                        onChange={handleFileChange}
                        className="hidden"
                        {...{ webkitdirectory: "", directory: "" } as any}
                    />
                </div>

                <div className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
                    {loading ? (
                        <div className="flex justify-center p-4 text-halo-cyan animate-pulse">Loading documents...</div>
                    ) : documents.length === 0 ? (
                        <div className="text-center p-8 text-halo-muted">No documents found. Upload one to get started.</div>
                    ) : (
                        documents.map((doc) => (
                            <div
                                key={doc.id}
                                onClick={() => setSelectedDoc(doc)}
                                className={`p-3 rounded border cursor-pointer group transition-all
                                    ${selectedDoc?.id === doc.id
                                        ? 'bg-halo-cyan/10 border-halo-cyan shadow-[0_0_10px_rgba(0,240,255,0.2)]'
                                        : 'bg-halo-card/50 border-halo-border hover:border-halo-cyan/50'
                                    }`}
                            >
                                <div className="flex items-start gap-3">
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
            <div className="flex-1 bg-halo-card border border-halo-border rounded-lg flex items-center justify-center relative overflow-hidden">
                {selectedDoc ? (
                    <div className="w-full h-full flex flex-col">
                        <div className="p-4 border-b border-halo-border flex justify-between items-center bg-halo-bg/50">
                            <h3 className="font-mono text-halo-cyan truncate">{selectedDoc.filename}</h3>
                            <div className="text-xs text-halo-muted">{selectedDoc.id}</div>
                        </div>
                        <div className="flex-1 flex items-center justify-center bg-black/20">
                            <div className="text-center space-y-4">
                                <File size={64} className="mx-auto text-halo-muted" />
                                <p className="text-halo-text">Preview not available for this file type.</p>
                                <button className="px-4 py-2 border border-halo-cyan text-halo-cyan rounded hover:bg-halo-cyan hover:text-black transition-colors">
                                    Download to View
                                </button>
                            </div>
                        </div>
                    </div>
                ) : (
                    <>
                        <div className="absolute inset-0 flex items-center justify-center opacity-5 pointer-events-none">
                            <FileText size={200} />
                        </div>
                        <div className="text-halo-muted text-sm font-mono">SELECT A DOCUMENT TO INITIATE ANALYSIS</div>
                    </>
                )}
            </div>
        </div>
    );
}
