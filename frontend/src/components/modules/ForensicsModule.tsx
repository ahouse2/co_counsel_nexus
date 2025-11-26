import { useState, useEffect } from 'react';
import { Shield, FileText, Activity, Lock, CheckCircle } from 'lucide-react';
import { endpoints } from '../../services/api';

interface ForensicDoc {
    id: string;
    filename: string;
    size: number;
    created_at: string;
    hash: string;
    status: 'verified' | 'tampered' | 'pending';
    custodian: string;
}

export function ForensicsModule() {
    const [documents, setDocuments] = useState<ForensicDoc[]>([]);
    const [loading, setLoading] = useState(false);
    const [verifying, setVerifying] = useState<string | null>(null);

    useEffect(() => {
        fetchDocuments();
    }, []);

    const fetchDocuments = async () => {
        setLoading(true);
        try {
            // Fetch real documents from case '1' (default)
            const response = await endpoints.documents.list('1');

            // Transform to forensic format
            // In a real app, we'd fetch specific forensic metadata. 
            // Here we map available fields and simulate the hash/custodian for the UI.
            const docs = response.data.map((d: any) => ({
                id: d.id,
                filename: d.filename,
                size: d.size,
                created_at: d.created_at,
                hash: `SHA256-${d.id.substring(0, 8)}...${d.id.substring(d.id.length - 8)}`, // Simulated hash based on ID
                status: 'verified',
                custodian: 'Evidence Locker'
            }));
            setDocuments(docs);
        } catch (error) {
            console.error("Failed to fetch forensic documents:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleVerify = async (id: string) => {
        setVerifying(id);
        // Simulate verification process
        await new Promise(r => setTimeout(r, 1500));
        setVerifying(null);
    };

    return (
        <div className="w-full h-full flex flex-col p-8 text-halo-text overflow-y-auto custom-scrollbar">
            <div className="flex items-center gap-4 mb-8">
                <div className="p-3 bg-halo-cyan/10 rounded-lg border border-halo-cyan/30 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                    <Shield className="text-halo-cyan w-8 h-8" />
                </div>
                <div>
                    <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider">Forensics & Chain of Custody</h2>
                    <p className="text-halo-muted text-sm">Evidence integrity verification and audit logging</p>
                </div>
            </div>

            <div className="halo-card flex-1 flex flex-col overflow-hidden">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3 text-halo-cyan">
                        <Activity size={20} />
                        <h3 className="text-lg font-mono uppercase tracking-wide">Evidence Ledger</h3>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-halo-muted">
                        <Lock size={12} />
                        <span>IMMUTABLE RECORD</span>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto custom-scrollbar">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="text-xs text-halo-muted uppercase tracking-wider border-b border-halo-border">
                                <th className="p-4 font-medium">Evidence ID</th>
                                <th className="p-4 font-medium">Filename</th>
                                <th className="p-4 font-medium">Cryptographic Hash</th>
                                <th className="p-4 font-medium">Custodian</th>
                                <th className="p-4 font-medium">Status</th>
                                <th className="p-4 font-medium text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody className="text-sm">
                            {loading ? (
                                <tr>
                                    <td colSpan={6} className="p-8 text-center text-halo-muted">Loading ledger...</td>
                                </tr>
                            ) : documents.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="p-8 text-center text-halo-muted">No evidence records found.</td>
                                </tr>
                            ) : (
                                documents.map((doc) => (
                                    <tr key={doc.id} className="border-b border-halo-border/30 hover:bg-halo-cyan/5 transition-colors group">
                                        <td className="p-4 font-mono text-xs text-halo-muted">{doc.id.substring(0, 8)}</td>
                                        <td className="p-4 text-halo-text flex items-center gap-2">
                                            <FileText size={14} className="text-halo-cyan opacity-50 group-hover:opacity-100" />
                                            {doc.filename}
                                        </td>
                                        <td className="p-4 font-mono text-xs text-halo-muted">{doc.hash}</td>
                                        <td className="p-4 text-halo-muted">{doc.custodian}</td>
                                        <td className="p-4">
                                            <span className="inline-flex items-center gap-1 px-2 py-1 rounded bg-green-500/10 text-green-400 text-xs border border-green-500/20">
                                                <CheckCircle size={10} />
                                                VERIFIED
                                            </span>
                                        </td>
                                        <td className="p-4 text-right">
                                            <button
                                                onClick={() => handleVerify(doc.id)}
                                                disabled={verifying === doc.id}
                                                className="text-xs text-halo-cyan hover:text-white hover:underline disabled:opacity-50"
                                            >
                                                {verifying === doc.id ? 'VERIFYING...' : 'AUDIT'}
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
