import { useState, useRef } from 'react';
// @ts-ignore
import { ForceGraph2D } from 'react-force-graph';
import { Search, DollarSign, AlertTriangle, Wallet, Globe, Briefcase, FileText } from 'lucide-react';
import { endpoints } from '../../services/api';

interface CryptoResult {
    address: string;
    chain: string;
    risk_score: number;
    flags: string[];
    attributed_clusters: string[];
    graph: { nodes: any[]; links: any[] };
    error?: string;
}

interface AssetScanResult {
    assets: { type: string; entity: string; value: string; suspicion_level: string; reason: string }[];
    risk_score: number;
    summary: string;
}

export function AssetHunterModule() {
    const [mode, setMode] = useState<'crypto' | 'assets'>('crypto');
    const [address, setAddress] = useState('');
    const [chain, setChain] = useState('BTC');
    const [cryptoResult, setCryptoResult] = useState<CryptoResult | null>(null);
    const [assetResult, setAssetResult] = useState<AssetScanResult | null>(null);
    const [loading, setLoading] = useState(false);
    const fgRef = useRef<any>();

    const handleTrace = async () => {
        if (!address) return;
        setLoading(true);
        try {
            const response = await endpoints.financial.traceCrypto(address, chain);
            setCryptoResult(response.data);
        } catch (error) {
            console.error("Trace failed:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleScan = async () => {
        setLoading(true);
        try {
            const response = await endpoints.financial.scanAssets('default_case');
            setAssetResult(response.data);
        } catch (error) {
            console.error("Scan failed:", error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full h-full flex flex-col p-8 text-halo-text overflow-hidden relative bg-gradient-to-br from-black via-[#051a1a] to-black">
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/30 shadow-[0_0_20px_rgba(16,185,129,0.2)]">
                        <DollarSign className="text-emerald-500 w-8 h-8" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-light text-emerald-100 uppercase tracking-wider">Asset Hunter</h2>
                        <p className="text-emerald-400/60 text-sm">Financial Forensics & Crypto Tracing</p>
                    </div>
                </div>
                <div className="flex bg-black/40 rounded-lg p-1 border border-emerald-500/20">
                    <button
                        onClick={() => setMode('crypto')}
                        className={`px-4 py-2 rounded text-sm uppercase tracking-wide transition-colors ${mode === 'crypto' ? 'bg-emerald-500/20 text-emerald-100' : 'text-halo-muted hover:text-halo-text'}`}
                    >
                        Crypto Tracer
                    </button>
                    <button
                        onClick={() => setMode('assets')}
                        className={`px-4 py-2 rounded text-sm uppercase tracking-wide transition-colors ${mode === 'assets' ? 'bg-emerald-500/20 text-emerald-100' : 'text-halo-muted hover:text-halo-text'}`}
                    >
                        Hidden Assets
                    </button>
                </div>
            </div>

            <div className="flex-1 overflow-hidden flex gap-8">
                {mode === 'crypto' ? (
                    <>
                        {/* Crypto Controls */}
                        <div className="w-1/3 flex flex-col gap-4">
                            <div className="halo-card p-4 border-emerald-500/20 bg-black/40">
                                <h3 className="text-emerald-400 font-mono text-sm uppercase mb-4 flex items-center gap-2">
                                    <Search size={16} /> Target Wallet
                                </h3>
                                <div className="flex gap-2 mb-4">
                                    <select
                                        value={chain}
                                        onChange={(e) => setChain(e.target.value)}
                                        className="bg-black/60 border border-emerald-500/30 rounded px-3 py-2 text-halo-text text-sm focus:outline-none focus:border-emerald-500"
                                    >
                                        <option value="BTC">BTC</option>
                                        <option value="ETH">ETH</option>
                                    </select>
                                    <input
                                        type="text"
                                        value={address}
                                        onChange={(e) => setAddress(e.target.value)}
                                        placeholder="Enter Wallet Address"
                                        className="flex-1 bg-black/60 border border-emerald-500/30 rounded px-3 py-2 text-halo-text text-sm focus:outline-none focus:border-emerald-500 font-mono"
                                    />
                                </div>
                                <button
                                    onClick={handleTrace}
                                    disabled={loading || !address}
                                    className="w-full py-3 bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/50 text-emerald-100 rounded transition-all uppercase tracking-widest text-sm font-bold disabled:opacity-50"
                                >
                                    {loading ? 'Tracing...' : 'Trace Funds'}
                                </button>
                            </div>

                            {cryptoResult && (
                                <div className="flex-1 overflow-y-auto custom-scrollbar space-y-4">
                                    {cryptoResult.error ? (
                                        <div className="p-4 bg-red-950/30 border border-red-500/30 rounded text-red-200 text-sm">
                                            Error: {cryptoResult.error}
                                        </div>
                                    ) : (
                                        <>
                                            <div className="halo-card p-4 border-emerald-500/20 bg-black/40">
                                                <h4 className="text-emerald-400 text-xs uppercase mb-2">Risk Score</h4>
                                                <div className="flex items-end gap-2">
                                                    <span className={`text-3xl font-bold ${cryptoResult.risk_score > 0.7 ? 'text-red-500' : 'text-emerald-500'}`}>
                                                        {(cryptoResult.risk_score * 100).toFixed(0)}
                                                    </span>
                                                    <span className="text-halo-muted text-sm mb-1">/ 100</span>
                                                </div>
                                            </div>

                                            {cryptoResult.flags.length > 0 && (
                                                <div className="halo-card p-4 border-red-500/20 bg-red-950/10">
                                                    <h4 className="text-red-400 text-xs uppercase mb-2 flex items-center gap-2">
                                                        <AlertTriangle size={14} /> Red Flags
                                                    </h4>
                                                    <ul className="space-y-2">
                                                        {cryptoResult.flags.map((flag, i) => (
                                                            <li key={i} className="text-red-200 text-xs">• {flag}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}

                                            {cryptoResult.attributed_clusters.length > 0 && (
                                                <div className="halo-card p-4 border-emerald-500/20 bg-black/40">
                                                    <h4 className="text-emerald-400 text-xs uppercase mb-2 flex items-center gap-2">
                                                        <Globe size={14} /> Attributed Entities
                                                    </h4>
                                                    <div className="flex flex-wrap gap-2">
                                                        {cryptoResult.attributed_clusters.map((cluster, i) => (
                                                            <span key={i} className="px-2 py-1 bg-emerald-500/10 border border-emerald-500/30 rounded text-emerald-200 text-xs">
                                                                {cluster}
                                                            </span>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Graph View */}
                        <div className="flex-1 halo-card border-emerald-500/20 bg-black/60 relative overflow-hidden rounded-lg">
                            {cryptoResult && !cryptoResult.error && (
                                <ForceGraph2D
                                    ref={fgRef}
                                    graphData={cryptoResult.graph}
                                    nodeLabel={(node: any) => node.id}
                                    nodeColor={(node: any) => node.group === 'target' ? '#ef4444' : node.group === 'mixer' ? '#f97316' : node.group === 'exchange' ? '#3b82f6' : '#10b981'}
                                    nodeRelSize={6}
                                    linkColor={() => '#10b98140'}
                                    backgroundColor="#00000000"
                                    onNodeClick={(node: any) => {
                                        fgRef.current?.centerAt(node.x, node.y, 1000);
                                        fgRef.current?.zoom(8, 2000);
                                    }}
                                />
                            )}
                            {!cryptoResult && (
                                <div className="absolute inset-0 flex items-center justify-center text-emerald-500/20">
                                    <Wallet size={64} />
                                </div>
                            )}
                        </div>
                    </>
                ) : (
                    <div className="w-full flex flex-col items-center">
                        {/* Hidden Assets View */}
                        {!assetResult ? (
                            <div className="text-center mt-20">
                                <Briefcase size={64} className="text-emerald-500/30 mx-auto mb-6" />
                                <h3 className="text-xl text-emerald-100 mb-4">Scan Documents for Hidden Assets</h3>
                                <p className="text-halo-muted max-w-md mx-auto mb-8">
                                    Our AI agent will analyze your timeline and documents for indicators of offshore accounts, trusts, and undisclosed property.
                                </p>
                                <button
                                    onClick={handleScan}
                                    disabled={loading}
                                    className="px-8 py-4 bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/50 text-emerald-100 rounded transition-all uppercase tracking-widest text-sm font-bold"
                                >
                                    {loading ? 'Scanning Case Files...' : 'Start Asset Scan'}
                                </button>
                            </div>
                        ) : (
                            <div className="w-full max-w-4xl space-y-6">
                                <div className="bg-emerald-950/20 border border-emerald-500/30 rounded-lg p-6">
                                    <h3 className="text-emerald-400 font-mono text-sm uppercase mb-2">Executive Summary</h3>
                                    <p className="text-emerald-100 leading-relaxed">{assetResult.summary}</p>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {assetResult.assets.map((asset, i) => (
                                        <div key={i} className="bg-black/40 border border-emerald-500/20 rounded p-4 hover:border-emerald-500/40 transition-colors">
                                            <div className="flex justify-between items-start mb-2">
                                                <div className="flex items-center gap-2">
                                                    <FileText size={16} className="text-emerald-500" />
                                                    <span className="font-bold text-emerald-100">{asset.entity}</span>
                                                </div>
                                                <span className={`text-[10px] px-2 py-0.5 rounded uppercase font-bold ${asset.suspicion_level === 'High' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
                                                    }`}>
                                                    {asset.suspicion_level} Risk
                                                </span>
                                            </div>
                                            <div className="text-sm text-halo-muted mb-2">Type: {asset.type}</div>
                                            <p className="text-xs text-halo-text/80 italic">"{asset.reason}"</p>
                                        </div>
                                    ))}
                                </div>
                                <button onClick={() => setAssetResult(null)} className="text-emerald-500/50 hover:text-emerald-500 text-sm mt-4">
                                    ← Start New Scan
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
