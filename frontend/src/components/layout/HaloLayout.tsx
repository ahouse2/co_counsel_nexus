import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { useHalo, ModuleId } from '../../context/HaloContext';
import { Settings, Menu, Activity } from 'lucide-react';

// Module definitions - Complete list from Halo spec
const PRIMARY_MODULES: { id: ModuleId; label: string }[] = [
    { id: 'graph', label: 'Graph Explorer' },
    { id: 'documents', label: 'Evidence Ingestion Pipeline' },
    { id: 'context', label: 'AI Context Engine' },
    { id: 'theory', label: 'Legal Theory Team' },
    { id: 'forensics', label: 'Forensics / Chain of Custody' },
    { id: 'timeline', label: 'Timeline Builder' },
    { id: 'binder', label: 'Exhibit / Trial Binder Creator' },
    { id: 'arena', label: 'Mock Trial Arena' },
    { id: 'mootcourt', label: 'Moot Court / Devil\'s Advocate' },
    { id: 'evidencemap', label: 'Evidence Map' },
    { id: 'jurysentiment', label: 'Jury Sentiment Predictor' },
    { id: 'university', label: 'Trial University' },
    { id: 'chat', label: 'Live Co-Counsel Chat' },
    { id: 'research', label: 'Legal Research / Case Law Engine' },
];

// Submodule definitions
const SUBMODULES: Record<ModuleId, { id: string; label: string }[]> = {
    graph: [
        { id: 'vector', label: 'Vector Space View' },
        { id: 'structured', label: 'Structured Graph View' },
        { id: 'heatmap', label: 'Relationship Heatmap' },
        { id: 'query', label: 'Autonomous Query Panel' },
    ],
    documents: [
        { id: 'upload', label: 'Folder Upload' },
        { id: 'ocr', label: 'OCR + Embedding' },
        { id: 'verify', label: 'Metadata Verification' },
        { id: 'logs', label: 'Fault Tolerance Logs' },
    ],
    context: [
        { id: 'query', label: 'Context Query' },
        { id: 'rag', label: 'RAG Status' },
    ],
    theory: [
        { id: 'facts', label: 'Fact Pattern Extraction' },
        { id: 'elements', label: 'Legal Element Linking' },
        { id: 'strategy', label: 'Strategy Drafting' },
    ],
    forensics: [
        { id: 'chain', label: 'Chain of Custody' },
        { id: 'hashing', label: 'File Hashing / Dedup' },
    ],
    timeline: [
        { id: 'builder', label: 'Timeline Builder' },
        { id: 'visualizer', label: 'Visualizer' },
    ],
    binder: [
        { id: 'designate', label: 'Designate Exhibits' },
        { id: 'covers', label: 'Cover Sheets' },
        { id: 'export', label: 'TrialPad Export' },
    ],
    arena: [
        { id: 'simulate', label: 'Witness Simulation' },
        { id: 'critic', label: 'AI Critic Combat' },
    ],
    university: [
        { id: 'lessons', label: 'Lessons' },
        { id: 'quiz', label: 'Quizzes' },
    ],
    chat: [
        { id: 'team', label: 'Team View' },
        { id: 'direct', label: 'Direct Message' },
    ],
    research: [
        { id: 'search', label: 'Case Law Search' },
        { id: 'statutes', label: 'Statutes & Codes' },
    ],
    drafting: [
        { id: 'templates', label: 'Templates' },
        { id: 'editor', label: 'Editor' },
    ],
    presentation: [
        { id: 'slides', label: 'Slides' },
        { id: 'present', label: 'Present Mode' },
    ],
    process: [
        { id: 'servers', label: 'Process Servers' },
        { id: 'status', label: 'Service Status' },
    ],
    agents: [
        { id: 'monitor', label: 'Agent Monitor' },
        { id: 'logs', label: 'Activity Logs' },
    ],
    mootcourt: [
        { id: 'warroom', label: 'War Room' },
        { id: 'simulation', label: 'Simulation History' },
    ],
    evidencemap: [
        { id: 'network', label: 'Evidence Network' },
        { id: 'analysis', label: 'Gap Analysis' },
    ],
    jurysentiment: [
        { id: 'analysis', label: 'Sentiment Analysis' },
        { id: 'simulation', label: 'Jury Simulation' },
    ],
    classification: [
        { id: 'review', label: 'Review Queue' },
        { id: 'history', label: 'History' },
    ],
    narrative: [
        { id: 'timeline', label: 'Timeline View' },
        { id: 'contradictions', label: 'Contradiction Analysis' },
    ],
    devils_advocate: [
        { id: 'challenge', label: 'Challenge Theory' },
        { id: 'analysis', label: 'Weakness Analysis' },
    ],
};

export function HaloLayout({ children }: { children: React.ReactNode }) {
    const { activeModule, setActiveModule, activeSubmodule, setActiveSubmodule, isSettingsOpen, setIsSettingsOpen } = useHalo();
    const [courtListenerKey, setCourtListenerKey] = React.useState(localStorage.getItem('courtlistener_key') || '');
    const [geminiKey, setGeminiKey] = React.useState(localStorage.getItem('gemini_key') || '');

    const [isMainMenuOpen, setIsMainMenuOpen] = React.useState(false);

    const handleSaveSettings = () => {
        localStorage.setItem('courtlistener_key', courtListenerKey);
        localStorage.setItem('gemini_key', geminiKey);
        setIsSettingsOpen(false);
    };

    // Zoom state derived from active module
    const isZoomed = activeModule !== 'graph';

    // Calculate positions for left perimeter nodes (Primary Modules)
    const primaryNodes = useMemo(() => {
        const count = PRIMARY_MODULES.length;
        // Radius is percentage of the container width
        // When zoomed (container is huge), radius must be smaller % to stay on screen
        const radius = isZoomed ? 38 : 50;

        const startAngle = Math.PI * 0.7; // Start at ~126 degrees (top-leftish)
        const endAngle = Math.PI * 1.3;   // End at ~234 degrees (bottom-leftish)
        const totalAngle = endAngle - startAngle;

        return PRIMARY_MODULES.map((mod, i) => {
            const angle = startAngle + (i / (count - 1)) * totalAngle;
            const x = Math.cos(angle) * radius;
            const y = Math.sin(angle) * radius;
            return { ...mod, x, y };
        });
    }, [isZoomed]);

    // Calculate positions for right perimeter nodes (Submodules)
    const subNodes = useMemo(() => {
        const modules = SUBMODULES[activeModule] || [];
        const count = modules.length;
        if (count === 0) return [];

        const radius = isZoomed ? 38 : 50;

        const startAngle = Math.PI * 1.7; // Start at ~306 degrees (top-rightish)
        const endAngle = Math.PI * 2.3;   // End at ~54 degrees (bottom-rightish)
        const totalAngle = endAngle - startAngle;

        return modules.map((mod, i) => {
            const angle = startAngle + (i / (Math.max(count - 1, 1))) * totalAngle;
            const x = Math.cos(angle) * radius;
            const y = Math.sin(angle) * radius;
            return { ...mod, x, y };
        });
    }, [activeModule, isZoomed]);

    return (
        <div className="relative w-screen h-screen flex items-center justify-center overflow-hidden bg-halo-bg text-halo-text">

            {/* Global UI Elements */}
            <div
                className="absolute top-8 right-8 z-50 cursor-pointer hover:text-halo-cyan transition-colors"
                onClick={() => setIsMainMenuOpen(!isMainMenuOpen)}
            >
                <div className="flex items-center gap-2">
                    <span className="text-xs font-mono uppercase tracking-widest">Menu</span>
                    <Menu size={24} />
                </div>
            </div>

            {/* Main Menu Dropdown */}
            {isMainMenuOpen && (
                <div className="absolute top-20 right-8 z-[60] bg-black/90 border border-halo-cyan/30 rounded-lg p-4 w-48 shadow-[0_0_20px_rgba(0,240,255,0.2)]">
                    <div className="flex flex-col gap-2">
                        <button className="text-left px-4 py-2 hover:bg-halo-cyan/20 hover:text-halo-cyan rounded transition-colors text-sm font-mono">
                            HOME
                        </button>
                        <button className="text-left px-4 py-2 hover:bg-halo-cyan/20 hover:text-halo-cyan rounded transition-colors text-sm font-mono" onClick={() => window.location.reload()}>
                            RESET VIEW
                        </button>
                        <button className="text-left px-4 py-2 hover:bg-halo-cyan/20 hover:text-halo-cyan rounded transition-colors text-sm font-mono">
                            HELP & DOCS
                        </button>
                        <button className="text-left px-4 py-2 hover:bg-halo-cyan/20 hover:text-halo-cyan rounded transition-colors text-sm font-mono">
                            ABOUT
                        </button>
                    </div>
                </div>
            )}

            <div
                className="absolute bottom-8 right-8 z-50 cursor-pointer hover:text-halo-cyan transition-colors"
                onClick={() => setIsSettingsOpen(true)}
            >
                <Settings size={24} className="animate-spin-slow" />
            </div>

            <div className="absolute bottom-8 left-8 z-50 text-xs font-mono text-halo-muted">
                <div className="flex items-center gap-2 hover:text-halo-cyan cursor-pointer transition-colors">
                    <Activity size={14} />
                    <span>SYSTEM NORMAL</span>
                </div>
            </div>

            {/* Settings Modal */}
            {isSettingsOpen && (
                <div className="absolute inset-0 z-[100] bg-black/80 backdrop-blur-md flex items-center justify-center">
                    <div className="bg-halo-card border border-halo-cyan/30 p-8 rounded-xl w-full max-w-md shadow-[0_0_50px_rgba(0,240,255,0.2)]">
                        <h2 className="text-xl font-mono text-halo-cyan mb-6 uppercase tracking-wider flex items-center gap-2">
                            <Settings size={20} /> System Configuration
                        </h2>

                        <div className="space-y-6">
                            <div title="API Key for CourtListener service to fetch legal documents and case metadata.">
                                <label className="block text-xs font-mono text-halo-muted mb-2 uppercase">CourtListener API Key</label>
                                <input
                                    type="password"
                                    value={courtListenerKey}
                                    onChange={(e) => setCourtListenerKey(e.target.value)}
                                    className="w-full bg-black/50 border border-halo-border rounded p-2 text-sm focus:border-halo-cyan focus:outline-none text-white"
                                    placeholder="Enter API Key..."
                                />
                            </div>

                            <div title="API Key for Google Gemini LLM to power the Context Engine and Agents.">
                                <label className="block text-xs font-mono text-halo-muted mb-2 uppercase">Google Gemini API Key</label>
                                <input
                                    type="password"
                                    value={geminiKey}
                                    onChange={(e) => setGeminiKey(e.target.value)}
                                    className="w-full bg-black/50 border border-halo-border rounded p-2 text-sm focus:border-halo-cyan focus:outline-none text-white"
                                    placeholder="Enter API Key..."
                                />
                            </div>

                            <div title="Select the visual theme for the Halo interface.">
                                <label className="block text-xs font-mono text-halo-muted mb-2 uppercase">Interface Theme</label>
                                <select className="w-full bg-black/50 border border-halo-border rounded p-2 text-sm focus:border-halo-cyan focus:outline-none text-white" title="Select theme">
                                    <option>Cyberpunk (Default)</option>
                                    <option>Minimalist</option>
                                    <option>High Contrast</option>
                                </select>
                            </div>

                            <div title="Adjust animation complexity and background processes to save resources.">
                                <label className="block text-xs font-mono text-halo-muted mb-2 uppercase">Performance Mode</label>
                                <select className="w-full bg-black/50 border border-halo-border rounded p-2 text-sm focus:border-halo-cyan focus:outline-none text-white" title="Select performance mode">
                                    <option>High Performance</option>
                                    <option>Battery Saver</option>
                                </select>
                            </div>

                            <div className="pt-4 flex justify-end gap-4">
                                <button
                                    onClick={() => setIsSettingsOpen(false)}
                                    className="px-4 py-2 text-xs font-mono text-halo-muted hover:text-white transition-colors"
                                >
                                    CANCEL
                                </button>
                                <button
                                    onClick={handleSaveSettings}
                                    className="px-6 py-2 bg-halo-cyan/20 border border-halo-cyan/50 rounded text-halo-cyan hover:bg-halo-cyan hover:text-black transition-all text-xs font-bold tracking-wider"
                                >
                                    SAVE CONFIGURATION
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* The Halo Container - Dynamically sized to fit viewport */}
            <motion.div
                className="relative flex items-center justify-center"
                initial={false}
                animate={{
                    width: isZoomed ? '125vmin' : '90vmin', // Reduced from 150vmin to prevent excessive cutoff
                    height: isZoomed ? '125vmin' : '90vmin',
                }}
                transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }} // Smooth apple-like spring/ease
            >

                {/* Outer Glow Ring */}
                <motion.div
                    className="absolute inset-0 rounded-full border border-halo-cyan/10 shadow-[0_0_30px_rgba(0,240,255,0.05)]"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 120, repeat: Infinity, ease: "linear" }}
                />

                {/* Inner Rotating Ring */}
                <motion.div
                    className="absolute inset-4 rounded-full border border-dashed border-halo-cyan/5"
                    animate={{ rotate: -360 }}
                    transition={{ duration: 80, repeat: Infinity, ease: "linear" }}
                />

                {/* Primary Module Nodes (Left Perimeter) */}
                {primaryNodes.map((node) => (
                    <div
                        key={node.id}
                        className={`absolute w-4 h-4 -ml-2 -mt-2 rounded-full border cursor-pointer transition-all duration-300 z-50 group halo-node-position
                            ${activeModule === node.id
                                ? 'bg-halo-cyan border-halo-cyan shadow-[0_0_15px_rgba(0,240,255,0.7)] scale-125'
                                : 'bg-halo-bg border-halo-cyan/30 hover:bg-halo-cyan/30 hover:scale-110 hover:shadow-[0_0_10px_rgba(0,240,255,0.5)]'
                            }`}
                        style={{
                            '--x': `${node.x}%`,
                            '--y': `${node.y}%`
                        } as React.CSSProperties}
                        onClick={() => setActiveModule(node.id)}
                    >
                        {/* Label */}
                        <div className={`absolute right-8 top-1/2 -translate-y-1/2 text-right w-48 transition-all duration-300
                            ${activeModule === node.id ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4 group-hover:opacity-100 group-hover:translate-x-0'}
                        `}>
                            <span className="text-sm font-mono uppercase tracking-widest text-halo-cyan shadow-black drop-shadow-md bg-black/50 px-2 py-1 rounded">
                                {node.label}
                            </span>
                        </div>

                        {/* Connecting Line (Active only) */}
                        {activeModule === node.id && (
                            <motion.div
                                className="absolute left-1/2 top-1/2 h-[1px] bg-halo-cyan origin-left z-[-1]"
                                style={{ width: isZoomed ? '150px' : '100px', transform: 'rotate(0deg)' }}
                                initial={{ scaleX: 0 }}
                                animate={{ scaleX: 1 }}
                            />
                        )}
                    </div>
                ))}

                {/* Submodule Nodes (Right Perimeter) */}
                {subNodes.map((node) => (
                    <div
                        key={node.id}
                        className={`absolute w-3 h-3 -ml-1.5 -mt-1.5 rounded-full border cursor-pointer transition-all duration-300 z-50 group halo-node-position
                            ${activeSubmodule === node.id
                                ? 'bg-halo-cyan border-halo-cyan shadow-[0_0_10px_rgba(0,240,255,0.7)] scale-125'
                                : 'bg-halo-bg border-halo-cyan/30 hover:bg-halo-cyan/30 hover:scale-110 hover:shadow-[0_0_10px_rgba(0,240,255,0.5)]'
                            }`}
                        style={{
                            '--x': `${node.x}%`,
                            '--y': `${node.y}%`
                        } as React.CSSProperties}
                        onClick={() => setActiveSubmodule(node.id)}
                    >
                        {/* Label */}
                        <div className={`absolute left-6 top-1/2 -translate-y-1/2 text-left w-48 transition-all duration-300
                            ${activeSubmodule === node.id ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4 group-hover:opacity-100 group-hover:translate-x-0'}
                        `}>
                            <span className="text-xs font-mono uppercase tracking-widest text-halo-cyan/80 shadow-black drop-shadow-md bg-black/50 px-2 py-1 rounded">
                                {node.label}
                            </span>
                        </div>
                    </div>
                ))}

                {/* Central Viewport (The "Inner Halo") */}
                <motion.div
                    className="absolute rounded-full overflow-hidden bg-black/90 backdrop-blur-xl border border-halo-cyan/10 z-10 shadow-inner flex items-center justify-center"
                    animate={{
                        inset: isZoomed ? '0.5rem' : '3rem', // Maximize space when zoomed
                        scale: 1
                    }}
                    transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                >
                    <div className={`relative transition-all duration-500 ${isZoomed ? 'w-screen h-screen max-w-[100vw] max-h-[100vh]' : 'w-full h-full'}`}>
                        {/* Content goes here */}
                        {children}
                    </div>
                </motion.div>

            </motion.div>
        </div>
    );
}
