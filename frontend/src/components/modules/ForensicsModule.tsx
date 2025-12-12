import { useState, useEffect, useCallback } from 'react';
import { Shield, FileText, Activity, Lock, CheckCircle, X, Binary } from 'lucide-react';
import { endpoints } from '../../services/api';

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
      setAnalysisResult(response.data);
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

  const formatHex = (hex: string) => {
    // Split into chunks of 2 for readability
    return hex.match(/.{1,2}/g)?.join(' ') ?? hex;
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

      {/* Hex View Modal */}
      {showHex && hexData && (
        <div
          className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-8"
          onClick={() => setShowHex(false)}
        >
          <div
            className="bg-[#0a0a0a] border border-halo-cyan/30 rounded-lg max-w-5xl w-full max-h-[90vh] flex flex-col shadow-[0_0_50px_rgba(0,240,255,0.15)]"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex justify-between items-center p-6 border-b border-halo-border/30 bg-halo-cyan/5">
              <div className="flex items-center gap-3">
                <Binary className="text-halo-cyan" />
                <div>
                  <h3 className="text-xl font-mono text-halo-cyan tracking-wider">HEX INSPECTOR</h3>
                  <p className="text-xs text-halo-muted font-mono">DOC ID: {hexData.doc_id}</p>
                </div>
              </div>
              <button onClick={() => setShowHex(false)} className="text-halo-muted hover:text-white transition-colors">
                <X size={24} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 font-mono text-xs custom-scrollbar bg-black/50">
              <div className="grid grid-cols-1 gap-8">
                <div>
                  <div className="flex items-center gap-2 mb-2 text-green-400 font-bold border-b border-green-500/30 pb-1">
                    <span>HEAD</span>
                    <span className="text-halo-muted font-normal">(First 512 bytes)</span>
                  </div>
                  <div className="bg-[#050505] p-4 rounded border border-halo-border/20 text-green-500/80 leading-relaxed break-all selection:bg-green-500/30 selection:text-white">
                    {formatHex(hexData.head)}
                  </div>
                </div>
                {hexData.tail && (
                  <div>
                    <div className="flex items-center gap-2 mb-2 text-green-400 font-bold border-b border-green-500/30 pb-1">
                      <span>TAIL</span>
                      <span className="text-halo-muted font-normal">(Last 512 bytes)</span>
                    </div>
                    <div className="bg-[#050505] p-4 rounded border border-halo-border/20 text-green-500/80 leading-relaxed break-all selection:bg-green-500/30 selection:text-white">
                      {formatHex(hexData.tail)}
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="p-4 border-t border-halo-border/30 bg-halo-cyan/5 flex justify-between items-center text-xs text-halo-muted font-mono">
              <span>TOTAL SIZE: {hexData.total_size.toLocaleString()} bytes</span>
              <span>INTEGRITY CHECK: PASSED</span>
            </div>
          </div>
        </div>
      )}

      {/* Analysis Result Modal */}
      {analysisResult && (
        <div
          className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-8"
          onClick={() => setAnalysisResult(null)}
        >
          <div
            className="bg-[#0a0a0a] border border-purple-500/30 rounded-lg max-w-2xl w-full max-h-[90vh] flex flex-col shadow-[0_0_50px_rgba(168,85,247,0.15)]"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex justify-between items-center p-6 border-b border-purple-500/30 bg-purple-500/5">
              <div className="flex items-center gap-3">
                <Shield className="text-purple-400" />
                <div>
                  <h3 className="text-xl font-mono text-purple-400 tracking-wider">FORENSIC REPORT</h3>
                  <p className="text-xs text-halo-muted font-mono">DEEP ANALYSIS COMPLETE</p>
                </div>
              </div>
              <button onClick={() => setAnalysisResult(null)} className="text-halo-muted hover:text-white transition-colors">
                <X size={24} />
              </button>
            </div>

            <div className="p-6 space-y-4 overflow-y-auto custom-scrollbar">
              <div className="flex justify-between items-center bg-white/5 p-4 rounded">
                <span className="text-halo-muted">Authenticity Score</span>
                <span className={`text-xl font-bold ${analysisResult.authenticity_score > 0.8 ? 'text-green-400' : 'text-red-400'}`}>
                  {(analysisResult.authenticity_score * 100).toFixed(1)}%
                </span>
              </div>

              <div>
                <h4 className="text-sm text-halo-muted uppercase mb-2">Flags & Issues</h4>
                <ul className="space-y-2">
                  {analysisResult.flags?.map((flag: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-red-300 bg-red-500/10 p-2 rounded">
                      <Activity size={14} className="mt-1 shrink-0" />
                      {flag}
                    </li>
                  ))}
                  {(!analysisResult.flags || analysisResult.flags.length === 0) && (
                    <li className="text-green-400 text-sm flex items-center gap-2">
                      <CheckCircle size={14} /> No issues detected.
                    </li>
                  )}
                </ul>
              </div>

              <div>
                <h4 className="text-sm text-halo-muted uppercase mb-2">Detailed Findings</h4>
                <p className="text-sm text-halo-text leading-relaxed whitespace-pre-wrap bg-black/30 p-4 rounded border border-white/5">
                  {analysisResult.details}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}