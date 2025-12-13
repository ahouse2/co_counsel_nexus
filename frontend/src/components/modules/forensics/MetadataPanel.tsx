import React from 'react';
import { Shield, X, AlertTriangle, Activity, Eye, Layers, Type } from 'lucide-react';

interface MetadataPanelProps {
    analysisResult: any;
    onClose: () => void;
}

export const MetadataPanel: React.FC<MetadataPanelProps> = ({ analysisResult, onClose }) => {
    // Helper to safely access nested properties
    const tamperScore = analysisResult.tamper_score?.score ?? 0;
    const tamperDetails = analysisResult.tamper_score?.details;
    const tamperFlags = analysisResult.tamper_score?.flags || [];

    const ela = analysisResult.ela;
    const clone = analysisResult.clone_splicing_detection;
    const font = analysisResult.font_object_analysis;
    const scan = analysisResult.anti_scan_alter_rescan;
    const verdict = analysisResult.overall_verdict || "UNKNOWN";

    // Calculate a display score (1 - tamper_score for authenticity)
    const authenticityScore = Math.max(0, 1 - tamperScore);

    return (
        <div
            className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-8"
            onClick={onClose}
        >
            <div
                className="bg-[#0a0a0a] border border-purple-500/30 rounded-lg max-w-4xl w-full max-h-[90vh] flex flex-col shadow-[0_0_50px_rgba(168,85,247,0.15)]"
                onClick={e => e.stopPropagation()}
            >
                <div className="flex justify-between items-center p-6 border-b border-purple-500/30 bg-purple-500/5">
                    <div className="flex items-center gap-3">
                        <Shield className="text-purple-400" />
                        <div>
                            <h3 className="text-xl font-mono text-purple-400 tracking-wider">FORENSIC REPORT</h3>
                            <p className="text-xs text-halo-muted font-mono">VERDICT: <span className={verdict === 'LOW_TAMPER_RISK' ? 'text-green-400' : 'text-red-400'}>{verdict.replace(/_/g, ' ')}</span></p>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-halo-muted hover:text-white transition-colors" title="Close panel">
                        <X size={24} />
                    </button>
                </div>

                <div className="p-6 space-y-6 overflow-y-auto custom-scrollbar">

                    {/* Top Level Score */}
                    <div className="flex justify-between items-center bg-white/5 p-4 rounded border border-white/10">
                        <span className="text-halo-muted uppercase text-sm tracking-wider">Authenticity Confidence</span>
                        <span className={`text-3xl font-bold ${authenticityScore > 0.8 ? 'text-green-400' : authenticityScore > 0.5 ? 'text-yellow-400' : 'text-red-400'}`}>
                            {(authenticityScore * 100).toFixed(1)}%
                        </span>
                    </div>

                    {/* Flags */}
                    {tamperFlags.length > 0 && (
                        <div>
                            <h4 className="text-sm text-halo-muted uppercase mb-2 flex items-center gap-2">
                                <AlertTriangle size={14} /> Critical Flags
                            </h4>
                            <ul className="space-y-2">
                                {tamperFlags.map((flag: string, i: number) => (
                                    <li key={i} className="flex items-start gap-2 text-sm text-red-300 bg-red-500/10 p-2 rounded border border-red-500/20">
                                        <Activity size={14} className="mt-1 shrink-0" />
                                        {flag}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                        {/* ELA Analysis */}
                        {ela && (
                            <div className="bg-black/30 p-4 rounded border border-white/5">
                                <h4 className="text-sm text-purple-300 uppercase mb-3 flex items-center gap-2">
                                    <Eye size={16} /> Error Level Analysis (ELA)
                                </h4>
                                <div className="space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-halo-muted">Confidence</span>
                                        <span className="text-halo-text">{(ela.confidence * 100).toFixed(1)}%</span>
                                    </div>
                                    <p className="text-xs text-halo-muted leading-relaxed">{ela.details}</p>
                                </div>
                            </div>
                        )}

                        {/* Clone Detection */}
                        {clone && (
                            <div className="bg-black/30 p-4 rounded border border-white/5">
                                <h4 className="text-sm text-purple-300 uppercase mb-3 flex items-center gap-2">
                                    <Layers size={16} /> Clone & Splicing
                                </h4>
                                <div className="space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-halo-muted">Detected</span>
                                        <span className={clone.detected ? "text-red-400" : "text-green-400"}>{clone.detected ? "YES" : "NO"}</span>
                                    </div>
                                    <p className="text-xs text-halo-muted leading-relaxed">{clone.details}</p>
                                    {clone.regions?.length > 0 && (
                                        <p className="text-xs text-red-400 mt-1">{clone.regions.length} suspicious regions identified.</p>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Font Analysis */}
                        {font && (
                            <div className="bg-black/30 p-4 rounded border border-white/5">
                                <h4 className="text-sm text-purple-300 uppercase mb-3 flex items-center gap-2">
                                    <Type size={16} /> Font & Object Analysis
                                </h4>
                                <div className="space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-halo-muted">Inconsistencies</span>
                                        <span className={font.inconsistencies_detected ? "text-red-400" : "text-green-400"}>{font.inconsistencies_detected ? "YES" : "NO"}</span>
                                    </div>
                                    <p className="text-xs text-halo-muted leading-relaxed">{font.details}</p>
                                    {font.anomalies?.map((a: string, i: number) => (
                                        <div key={i} className="text-xs text-red-300 bg-red-500/5 p-1 rounded mt-1">{a}</div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Scan Pattern */}
                        {scan && (
                            <div className="bg-black/30 p-4 rounded border border-white/5">
                                <h4 className="text-sm text-purple-300 uppercase mb-3 flex items-center gap-2">
                                    <Activity size={16} /> Scan Pattern Analysis
                                </h4>
                                <div className="space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-halo-muted">Rescan Detected</span>
                                        <span className={scan.detected ? "text-red-400" : "text-green-400"}>{scan.detected ? "YES" : "NO"}</span>
                                    </div>
                                    <p className="text-xs text-halo-muted leading-relaxed">{scan.details}</p>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Detailed Findings */}
                    <div>
                        <h4 className="text-sm text-halo-muted uppercase mb-2">Analysis Summary</h4>
                        <p className="text-sm text-halo-text leading-relaxed whitespace-pre-wrap bg-black/30 p-4 rounded border border-white/5 font-mono text-xs">
                            {tamperDetails}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};
