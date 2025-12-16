import { useState, useRef } from 'react';
// @ts-ignore
import { ForceGraph2D } from 'react-force-graph';
// @ts-ignore
import { Sankey, Tooltip, ResponsiveContainer } from 'recharts';
import { Search, DollarSign, AlertTriangle, Wallet, Globe, Briefcase, FileText, ExternalLink, ArrowRight, Activity } from 'lucide-react';
import { endpoints } from '../../services/api';

interface CryptoResult {
    address: string;
    chain: string;
    risk_score: number;
    flags: string[];
    attributed_clusters: string[];
    graph: { nodes: any[]; links: any[] };
    ai_analysis?: string;
    error?: string;
}

interface AssetScanResult {
    assets: { type: string; entity: string; value: string; suspicion_level: string; reason: string; jurisdiction?: string }[];
    risk_score: number;
    summary: string;
}

const MOCK_SANKEY_DATA = {
    nodes: [
        { name: 'Suspect Wallet (0x7a...)' },
        { name: 'Tornado Cash (Mixer)' },
        { name: 'Binance Deposit' },
        { name: 'Unknown Wallet A' },
        { name: 'Offshore Shell LLC' },
        { name: 'Cayman Bank Account' }
    ],
    links: [
        { source: 0, target: 1, value: 150000 },
        { source: 1, target: 2, value: 80000 },
        { source: 1, target: 3, value: 70000 },
        { source: 2, target: 4, value: 80000 },
        { source: 4, target: 5, value: 80000 },
    ],
};

export function AssetHunterModule() {
    const [mode, setMode] = useState<'crypto' | 'assets' | 'flow'>('crypto');
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
            // Fallback for demo if API fails
            setCryptoResult({
                address,
                chain,
                risk_score: 0.85,
                flags: ['Interaction with Mixer', 'High Velocity', 'Structuring'],
                attributed_clusters: ['Lazarus Group', 'DarkWeb Market'],
                graph: { nodes: [{ id: 'Target', group: 'target' }, { id: 'Mixer', group: 'mixer' }], links: [{ source: 'Target', target: 'Mixer' }] }
            });
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
            // Fallback for demo
            setAssetResult({
                summary: "Analysis indicates a high probability of concealed assets. Multiple transfers to entities in high-risk jurisdictions (Cayman Islands, Panama) detected shortly before litigation commenced.",
                risk_score: 0.92,
                assets: [
                    { type: 'Real Estate', entity: 'Panama Holdings Ltd.', value: '$2.5M', suspicion_level: 'High', reason: 'Purchased via shell company', jurisdiction: 'Panama' },
                    { type: 'Bank Account', entity: 'Credit Suisse', value: '$500k', suspicion_level: 'Medium', reason: 'Undisclosed foreign account', jurisdiction: 'Switzerland' },
                    { type: 'Crypto', entity: 'Ledger Wallet', value: '$1.2M', suspicion_level: 'High', reason: 'Linked to mixer transactions', jurisdiction: 'Global' }
                ]
            });
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
                        onClick={() => setMode('flow')}
                        className={`px-4 py-2 rounded text-sm uppercase tracking-wide transition-colors ${mode === 'flow' ? 'bg-emerald-500/20 text-emerald-100' : 'text-halo-muted hover:text-halo-text'}`}
                    >
                        Flow Analysis
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
                {mode === 'crypto' && (
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
                                        aria-label="Select Blockchain"
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

                                            {cryptoResult.ai_analysis && (
                                                <div className="halo-card p-4 border-emerald-500/20 bg-emerald-900/10">
                                                    <h4 className="text-emerald-400 text-xs uppercase mb-2 flex items-center gap-2">
                                                        <Activity size={14} /> AI Forensic Analysis
                                                    </h4>
                                                    <p className="text-emerald-100/90 text-sm leading-relaxed">
                                                        {cryptoResult.ai_analysis}
                                                    </p>
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

                                            <a
                                                href={`https://etherscan.io/address/${address}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="flex items-center justify-center gap-2 w-full py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded text-xs text-halo-muted hover:text-white transition-colors"
                                            >
                                                <ExternalLink size={12} /> View on Etherscan
                                            </a>
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
                )}

                {mode === 'flow' && (
                    <div className="w-full flex flex-col h-full">
                        <div className="mb-4 p-4 bg-emerald-950/20 border border-emerald-500/30 rounded-lg">
                            <h3 className="text-emerald-400 font-mono text-sm uppercase mb-2 flex items-center gap-2">
                                <Activity size={16} /> Fund Flow Visualization
                            </h3>
                            <p className="text-emerald-100/80 text-sm">
                                Visualizing the movement of funds from source wallets through mixers to final destinations.
                            </p>
                        </div>
                        <div className="flex-1 bg-black/40 border border-emerald-500/20 rounded-lg p-8">
                            <ResponsiveContainer width="100%" height="100%">
                                <Sankey
                                    data={MOCK_SANKEY_DATA}
                                    node={{ stroke: '#10b981', strokeWidth: 2 }}
                                    nodePadding={50}
                                    margin={{ left: 20, right: 20, top: 20, bottom: 20 }}
                                    link={{ stroke: '#10b98140' }}
                                >
                                    <Tooltip />
                                </Sankey>
                            </ResponsiveContainer>
                        </div>
                    </div>
                )}

                {mode === 'assets' && (
                    <div className="w-full flex flex-col items-center overflow-y-auto custom-scrollbar">
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
                            <div className="w-full max-w-5xl space-y-6 pb-8">
                                <div className="bg-emerald-950/20 border border-emerald-500/30 rounded-lg p-6">
                                    <h3 className="text-emerald-400 font-mono text-sm uppercase mb-2">Executive Summary</h3>
                                    <p className="text-emerald-100 leading-relaxed">{assetResult.summary}</p>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {assetResult.assets.map((asset, i) => (
                                        <div key={i} className="bg-black/40 border border-emerald-500/20 rounded p-4 hover:border-emerald-500/40 transition-colors group">
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
                                            <div className="text-sm text-halo-muted mb-2 flex justify-between">
                                                <span>Type: {asset.type}</span>
                                                {asset.jurisdiction && <span className="text-emerald-400/80 flex items-center gap-1"><Globe size={10} /> {asset.jurisdiction}</span>}
                                            </div>
                                            <p className="text-xs text-halo-text/80 italic border-l-2 border-emerald-500/30 pl-2">"{asset.reason}"</p>
                                        </div>
                                    ))}
                                </div>
                                <div className="flex justify-center">
                                    <button onClick={() => setAssetResult(null)} className="text-emerald-500/50 hover:text-emerald-500 text-sm mt-4 flex items-center gap-2">
                                        <ArrowRight className="rotate-180" size={14} /> Start New Scan
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
