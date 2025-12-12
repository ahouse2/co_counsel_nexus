import { useState, useEffect, useRef, useMemo } from 'react';
import { endpoints } from '../../services/api';
import ForceGraph3D from 'react-force-graph-3d';
import { Network, XCircle, Search, Maximize2, Loader2, AlertCircle } from 'lucide-react';
import { useHalo } from '../../context/HaloContext';


// Types for our graph data
interface Node {
    id: string;
    group: 'evidence' | 'element' | 'source';
    label: string;
    val: number; // size
    color?: string;
    desc?: string;
    status?: string;
}

interface Link {
    source: string;
    target: string;
    type: 'supports' | 'contradicts' | 'relates_to';
    width?: number;
    color?: string;
    particles?: number; // for visual flow
}

interface GraphData {
    nodes: Node[];
    links: Link[];
}

export function EvidenceMapModule() {
    const { activeSubmodule } = useHalo();
    const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedNode, setSelectedNode] = useState<Node | null>(null);
    const [filter, setFilter] = useState('all');
    const fgRef = useRef<any>();
    const containerRef = useRef<HTMLDivElement>(null);

    // Mock data generator (fallback if API fails or is empty)
    const generateMockData = () => {
        const nodes: Node[] = [
            { id: 'case_root', group: 'source', label: 'CASE: Doe v. Smith', val: 20, color: '#ffffff' },
            { id: 'element_duty', group: 'element', label: 'Duty of Care', val: 10, color: '#a855f7', desc: 'Legal obligation to adhere to a standard of reasonable care.' },
            { id: 'element_breach', group: 'element', label: 'Breach', val: 10, color: '#a855f7', desc: 'Failure to meet the standard of care.' },
            { id: 'element_causation', group: 'element', label: 'Causation', val: 10, color: '#a855f7', desc: 'The breach directly caused the injury.' },
            { id: 'element_damages', group: 'element', label: 'Damages', val: 10, color: '#a855f7', desc: 'Quantifiable harm suffered by the plaintiff.' },

            { id: 'ev_contract', group: 'evidence', label: 'Service Contract', val: 5, color: '#00f0ff', status: 'strong', desc: 'Signed agreement stipulating safety protocols.' },
            { id: 'ev_email', group: 'evidence', label: 'Email: "Ignore warnings"', val: 5, color: '#ef4444', status: 'strong', desc: 'Internal email instructing staff to bypass safety checks.' },
            { id: 'ev_report', group: 'evidence', label: 'Safety Audit 2024', val: 5, color: '#eab308', status: 'moderate', desc: 'Third-party audit highlighting potential risks.' },
            { id: 'ev_witness', group: 'evidence', label: 'Witness Deposition', val: 5, color: '#00f0ff', status: 'weak', desc: 'Testimony of former employee regarding safety practices.' },
        ];

        const links: Link[] = [
            { source: 'case_root', target: 'element_duty', type: 'relates_to' },
            { source: 'case_root', target: 'element_breach', type: 'relates_to' },
            { source: 'case_root', target: 'element_causation', type: 'relates_to' },
            { source: 'case_root', target: 'element_damages', type: 'relates_to' },

            { source: 'ev_contract', target: 'element_duty', type: 'supports', color: '#00f0ff' },
            { source: 'ev_email', target: 'element_breach', type: 'supports', color: '#00f0ff' },
            { source: 'ev_report', target: 'element_breach', type: 'supports', color: '#eab308' },
            { source: 'ev_witness', target: 'element_causation', type: 'contradicts', color: '#ef4444' },
            { source: 'ev_contract', target: 'ev_email', type: 'contradicts', color: '#ef4444' },
        ];

        return { nodes, links };
    };

    useEffect(() => {
        loadEvidenceMap();
    }, []);

    const loadEvidenceMap = async () => {
        setLoading(true);
        setError(null);
        try {
            // Try to fetch real data
            const response = await endpoints.evidenceMap.get('default_case');
            if (response.data && response.data.nodes && response.data.nodes.length > 0) {
                setGraphData(response.data);
            } else {
                // Fallback to mock data if empty
                setGraphData(generateMockData());
            }
        } catch (err) {
            console.error("Failed to load evidence map, using mock data:", err);
            setError("Failed to load evidence map from server. Displaying demo data.");
            setGraphData(generateMockData());
        } finally {
            setLoading(false);
        }
    };

    const handleNodeClick = (node: any) => {
        setSelectedNode(node);

        // Aim camera at node
        const distance = 40;
        const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);

        fgRef.current.cameraPosition(
            { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio }, // new position
            node, // lookAt ({ x, y, z })
            3000  // ms transition duration
        );
    };

    const filteredData = useMemo(() => {
        if (filter === 'all') return graphData;

        const nodes = graphData.nodes.filter(n =>
            n.group === 'source' || // always keep root
            n.group === filter ||
            (filter === 'strong' && n.status === 'strong') ||
            (filter === 'weak' && n.status === 'weak')
        );

        const nodeIds = new Set(nodes.map(n => n.id));
        const links = graphData.links.filter(l =>
            nodeIds.has(typeof l.source === 'object' ? (l.source as any).id : l.source) &&
            nodeIds.has(typeof l.target === 'object' ? (l.target as any).id : l.target)
        );

        return { nodes, links };
    }, [graphData, filter]);

    return (
        <div className="w-full h-full flex flex-col relative overflow-hidden bg-black">
            {/* Loading Overlay */}
            {loading && (
                <div className="absolute inset-0 z-50 bg-black/80 flex items-center justify-center backdrop-blur-sm">
                    <div className="flex flex-col items-center gap-4">
                        <Loader2 className="w-12 h-12 text-purple-500 animate-spin" />
                        <p className="text-purple-300 text-sm uppercase tracking-wider">Loading Evidence Map...</p>
                    </div>
                </div>
            )}

            {/* Error Toast */}
            {error && (
                <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 bg-yellow-500/20 border border-yellow-500/50 rounded-lg px-4 py-2 flex items-center gap-2 backdrop-blur-sm">
                    <AlertCircle className="w-5 h-5 text-yellow-400" />
                    <span className="text-yellow-300 text-sm">{error}</span>
                </div>
            )}

            {/* Header Overlay */}
            <div className="absolute top-0 left-0 right-0 z-10 p-6 flex justify-between items-start pointer-events-none">
                <div className="pointer-events-auto">
                    <div className="flex items-center gap-4 mb-2">
                        <div className="p-3 bg-purple-500/10 rounded-lg border border-purple-500/30 shadow-[0_0_15px_rgba(168,85,247,0.2)] backdrop-blur-sm">
                            <Network className="text-purple-500 w-8 h-8" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-light text-white uppercase tracking-wider text-shadow-glow">Evidence Nexus</h2>
                            <p className="text-purple-300/70 text-sm">
                                {activeSubmodule === 'analysis' ? 'Gap Analysis Mode' : '3D Force-Directed Analysis Graph'}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="flex gap-2 pointer-events-auto">
                    <select
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        className="bg-black/60 border border-purple-500/30 rounded px-4 py-2 text-sm text-purple-300 focus:border-purple-500 focus:outline-none backdrop-blur-sm"
                    >
                        <option value="all">View All Nodes</option>
                        <option value="element">Legal Elements Only</option>
                        <option value="evidence">Evidence Only</option>
                        <option value="strong">Strong Evidence</option>
                        <option value="weak">Weak Evidence</option>
                    </select>
                    <button
                        onClick={() => {
                            fgRef.current.zoomToFit(1000);
                            setSelectedNode(null);
                        }}
                        className="p-2 bg-black/60 border border-purple-500/30 rounded text-purple-300 hover:bg-purple-500/20 transition-colors backdrop-blur-sm"
                        title="Reset View"
                    >
                        <Maximize2 size={20} />
                    </button>
                </div>
            </div>

            {/* 3D Graph */}
            <div className="flex-1" ref={containerRef}>
                <ForceGraph3D
                    ref={fgRef}
                    graphData={filteredData}
                    nodeLabel="label"
                    nodeColor="color"
                    nodeVal="val"
                    linkColor={(link: any) => link.color || '#ffffff'}
                    linkWidth={(link: any) => link.width || 1}
                    linkDirectionalParticles={2}
                    linkDirectionalParticleSpeed={0.005}
                    linkDirectionalParticleWidth={2}
                    onNodeClick={handleNodeClick}
                    backgroundColor="#000000"
                    showNavInfo={false}
                    nodeResolution={16}
                    linkResolution={12}
                    linkOpacity={0.3}
                    warmupTicks={100}
                    cooldownTicks={0}
                />
            </div>

            {/* Detail Panel Overlay */}
            {selectedNode && (
                <div className="absolute bottom-6 right-6 w-96 bg-black/80 border border-purple-500/30 rounded-xl p-6 backdrop-blur-md shadow-2xl animate-in fade-in slide-in-from-right-10 z-20">
                    <div className="flex justify-between items-start mb-4">
                        <h3 className="text-xl font-bold text-white">{selectedNode.label}</h3>
                        <button
                            onClick={() => setSelectedNode(null)}
                            className="text-gray-500 hover:text-white transition-colors"
                        >
                            <XCircle size={20} />
                        </button>
                    </div>

                    <div className="space-y-4">
                        <div>
                            <span className={`text-xs font-bold uppercase px-2 py-1 rounded border ${selectedNode.group === 'element' ? 'bg-purple-500/20 border-purple-500 text-purple-400' :
                                selectedNode.group === 'evidence' ? 'bg-cyan-500/20 border-cyan-500 text-cyan-400' :
                                    'bg-white/10 border-white/20 text-white'
                                }`}>
                                {selectedNode.group}
                            </span>
                            {selectedNode.status && (
                                <span className={`ml-2 text-xs font-bold uppercase px-2 py-1 rounded border ${selectedNode.status === 'strong' ? 'bg-green-500/20 border-green-500 text-green-400' :
                                    selectedNode.status === 'weak' ? 'bg-red-500/20 border-red-500 text-red-400' :
                                        'bg-yellow-500/20 border-yellow-500 text-yellow-400'
                                    }`}>
                                    {selectedNode.status}
                                </span>
                            )}
                        </div>

                        <p className="text-gray-300 text-sm leading-relaxed">
                            {selectedNode.desc || "No detailed description available for this node."}
                        </p>

                        {selectedNode.group === 'evidence' && (
                            <button className="w-full py-2 bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/50 text-purple-300 rounded transition-colors text-sm font-bold flex items-center justify-center gap-2">
                                <Search size={14} /> INSPECT SOURCE DOCUMENT
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* Legend */}
            <div className="absolute bottom-6 left-6 bg-black/60 border border-white/10 rounded-lg p-4 backdrop-blur-sm pointer-events-none">
                <h4 className="text-xs font-bold text-gray-400 uppercase mb-2">Legend</h4>
                <div className="space-y-2 text-xs">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-[#a855f7]"></div>
                        <span className="text-gray-300">Legal Element</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-[#00f0ff]"></div>
                        <span className="text-gray-300">Supporting Evidence</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-[#ef4444]"></div>
                        <span className="text-gray-300">Contradicting Evidence</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-[#eab308]"></div>
                        <span className="text-gray-300">Neutral / Mixed</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
