import { useState, useEffect, useCallback } from 'react';
import { Shield, FileText, Activity, Lock, CheckCircle, Binary } from 'lucide-react';
import { endpoints } from '../../services/api';
import { HexViewer } from './forensics/HexViewer';
import { MetadataPanel } from './forensics/MetadataPanel';

interface ForensicDoc {
  id: string;
  filename: string;
  size: number;
  created_at: string;
  hash: string;
  status: 'verified' | 'tampered' | 'pending';
  custodian: string;
  forensic_metadata?: {
    size_bytes?: number;
    [key: string]: any;
  };
}

interface HexData {
  head: string;
  tail: string;
  total_size: number;
  doc_id: string;
}

// Interface for the raw API response to allow mapping
interface ApiDocResponse {
  id: string;
  name: string;
  created_at?: string;
  hash_sha256?: string;
  forensic_metadata?: {
    size_bytes?: number;
    [key: string]: any;
  };
}

export function ForensicsModule() {
  const [documents, setDocuments] = useState<ForensicDoc[]>([]);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState<string | null>(null);
  const [hexData, setHexData] = useState<HexData | null>(null);
  const [showHex, setShowHex] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any | null>(null);
  const [analyzing, setAnalyzing] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    try {
      // @ts-ignore - explicitly ignoring if type definition is lagging
      const response = await endpoints.documents.list('default_case');

      const docs = response.data.map((d: ApiDocResponse) => ({
        id: d.id,
        filename: d.name,
        size: d.forensic_metadata?.size_bytes ?? 0,
        created_at: d.created_at ?? new Date().toISOString(),
        hash: d.hash_sha256 ?? 'PENDING_HASH_CALCULATION',
        status: d.hash_sha256 ? 'verified' : 'pending',
        custodian: 'Evidence Locker',
        forensic_metadata: d.forensic_metadata,
      }));
      setDocuments(docs as ForensicDoc[]);
    } catch (error) {
      console.error("Failed to fetch forensic documents:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleDeepAnalysis = async (id: string) => {
    setAnalyzing(id);
    try {
      // @ts-ignore
      const response = await endpoints.forensics.analyze(id, 'default_case');
      setAnalysisResult(response.data); // Now returns ForensicAnalysisResult dict
    } catch (error) {
      console.error("Failed to run deep analysis:", error);
      alert("Deep Analysis Failed. Check backend logs.");
    } finally {
      setAnalyzing(null);
    }
  };

  const handleAudit = async (id: string) => {
    setVerifying(id);
    try {
      // @ts-ignore - explicitly ignoring if type definition is lagging
      const response = await endpoints.forensics.getHexView(id);
      setHexData(response.data);
      setShowHex(true);
    } catch (error) {
      console.error("Failed to fetch hex view:", error);
      alert("Could not fetch raw bytes. Ensure backend is running.");
    } finally {
      setVerifying(null);
    }
  };

  return (
    <div className="w-full h-full flex flex-col p-8 text-halo-text overflow-y-auto custom-scrollbar relative">
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
                <th className="p-4 font-medium">SHA-256 Hash</th>
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
                    <td className="p-4 font-mono text-[10px] text-halo-muted max-w-[200px] truncate" title={doc.hash}>
                      {doc.hash}
                    </td>
                    <td className="p-4 text-halo-muted">{doc.custodian}</td>
                    <td className="p-4">
                      {doc.status === 'verified' ? (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded bg-green-500/10 text-green-400 text-xs border border-green-500/20">
                          <CheckCircle size={10} />
                          VERIFIED
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded bg-yellow-500/10 text-yellow-400 text-xs border border-yellow-500/20">
                          <Activity size={10} className="animate-pulse" />
                          PENDING
                        </span>
                      )}
                    </td>
                    <td className="p-4 text-right flex justify-end gap-2">
                      <button
                        onClick={() => handleDeepAnalysis(doc.id)}
                        disabled={analyzing === doc.id}
                        className="text-xs text-purple-400 hover:text-purple-300 hover:underline disabled:opacity-50 flex items-center gap-1"
                      >
                        {analyzing === doc.id ? 'ANALYZING...' : 'DEEP ANALYZE'}
                      </button>
                      <button
                        onClick={() => handleAudit(doc.id)}
                        disabled={verifying === doc.id}
                        className="text-xs text-halo-cyan hover:text-white hover:underline disabled:opacity-50 flex items-center gap-1"
                      >
                        {verifying === doc.id ? (
                          'LOADING...'
                        ) : (
                          <>
                            <Binary size={12} />
                            HEX VIEW
                          </>
                        )}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Hex Viewer Modal */}
      {showHex && hexData && (
        <HexViewer hexData={hexData} onClose={() => setShowHex(false)} />
      )}

      {/* Analysis Result Modal */}
      {analysisResult && (
        <MetadataPanel analysisResult={analysisResult} onClose={() => setAnalysisResult(null)} />
      )}
    </div>
  );
}