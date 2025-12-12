import { useState, useEffect } from 'react';
import { Lightbulb, Target, FileText, Loader2, Scale, Zap, Play, Pause, MessageSquare, BrainCircuit } from 'lucide-react';
import { endpoints } from '../../services/api';
import { useHalo } from '../../context/HaloContext';

export function LegalTheoryModule() {
    const { activeSubmodule } = useHalo();
    const [facts, setFacts] = useState<string | null>(null);
    const [strategies, setStrategies] = useState<string | null>(null);
    const [elements, setElements] = useState<string | null>(null);
    const [loadingFacts, setLoadingFacts] = useState(false);
    const [loadingStrategy, setLoadingStrategy] = useState(false);
    const [loadingElements, setLoadingElements] = useState(false);

    // Autonomous Mode State
    const [autonomousMode, setAutonomousMode] = useState(false);
    const [autoStep, setAutoStep] = useState(0);
    const [customQuery, setCustomQuery] = useState('');
    const [customResponse, setCustomResponse] = useState<string | null>(null);
    const [loadingCustom, setLoadingCustom] = useState(false);

    // Autonomous Loop
    useEffect(() => {
        if (!autonomousMode) return;

        const runAutoStep = async () => {
            // Step 0: Extract Facts
            if (autoStep === 0 && !loadingFacts && !facts) {
                await handleExtractFacts();
                setAutoStep(1);
            }
            // Step 1: Generate Strategy (once facts are done)
            else if (autoStep === 1 && !loadingStrategy && !strategies) {
                await handleGenerateStrategy();
                setAutoStep(2);
            }
            // Step 2: Analyze Elements
            else if (autoStep === 2 && !loadingElements && !elements) {
                await handleAnalyzeElements();
                setAutoStep(3);
            }
            // Step 3: Loop or Wait
            else if (autoStep === 3) {
                setTimeout(() => {
                    setFacts(null);
                    setStrategies(null);
                    setElements(null);
                    setAutoStep(0);
                }, 60000);
            }
        };

        const interval = setInterval(runAutoStep, 3000);
        return () => clearInterval(interval);
    }, [autonomousMode, autoStep, facts, strategies, elements, loadingFacts, loadingStrategy, loadingElements]);

    const handleExtractFacts = async () => {
        setLoadingFacts(true);
        try {
            const response = await endpoints.context.query("Extract the key fact patterns from the available evidence, focusing on timeline, causality, and inconsistencies.", "default_case");
            const answer = response.data.response || response.data.answer || (typeof response.data === 'string' ? response.data : JSON.stringify(response.data));
            setFacts(answer);
        } catch (error) {
            console.error("Failed to extract facts:", error);
            setFacts("Unable to extract facts. Please ensure the knowledge base is populated.");
        } finally {
            setLoadingFacts(false);
        }
    };

    const handleGenerateStrategy = async () => {
        setLoadingStrategy(true);
        try {
            const response = await endpoints.context.query("Based on the known facts, outline 3 potential legal strategies for the defense, citing relevant legal principles where possible.", "default_case");
            const answer = response.data.response || response.data.answer || (typeof response.data === 'string' ? response.data : JSON.stringify(response.data));
            setStrategies(answer);
        } catch (error) {
            console.error("Failed to generate strategy:", error);
            setStrategies("Unable to generate strategy. Please ensure the knowledge base is populated.");
        } finally {
            setLoadingStrategy(false);
        }
    };

    const handleAnalyzeElements = async () => {
        setLoadingElements(true);
        try {
            const response = await endpoints.context.query("Break down the case into key legal elements (e.g., Duty, Breach, Causation, Damages) and map the available evidence to each element. Identify any missing elements.", "default_case");
            const answer = response.data.response || response.data.answer || (typeof response.data === 'string' ? response.data : JSON.stringify(response.data));
            setElements(answer);
        } catch (error) {
            console.error("Failed to analyze elements:", error);
            setElements("Unable to analyze legal elements.");
        } finally {
            setLoadingElements(false);
        }
    };

    const handleCustomQuery = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!customQuery.trim()) return;

        setAutonomousMode(false); // Pause auto mode
        setLoadingCustom(true);
        try {
            const response = await endpoints.context.query(customQuery, "default_case");
            const answer = response.data.response || response.data.answer || (typeof response.data === 'string' ? response.data : JSON.stringify(response.data));
            setCustomResponse(answer);
        } catch (error) {
            console.error("Custom query failed:", error);
            setCustomResponse("Error processing query.");
        } finally {
            setLoadingCustom(false);
        }
    };

    // Submodule Views
    if (activeSubmodule === 'strategy') {
        return (
            <div className="w-full h-full flex flex-col p-8 text-halo-text overflow-hidden">
                <div className="flex items-center justify-between mb-6 shrink-0">
                    <div className="flex items-center gap-3 text-halo-cyan">
                        <Lightbulb size={24} />
                        <h3 className="text-lg font-mono uppercase tracking-wide">Strategic Analysis</h3>
                    </div>
                    <button
                        onClick={handleGenerateStrategy}
                        disabled={loadingStrategy || autonomousMode}
                        className="flex items-center gap-2 px-4 py-2 bg-halo-cyan/10 hover:bg-halo-cyan/20 text-halo-cyan border border-halo-cyan/30 rounded transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm uppercase tracking-wider"
                    >
                        {loadingStrategy ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
                        {loadingStrategy ? 'Drafting...' : 'Generate Strategy'}
                    </button>
                </div>
                <div className="flex-1 bg-black/30 rounded-lg p-6 border border-halo-border overflow-y-auto custom-scrollbar relative">
                    {loadingStrategy && (
                        <div className="absolute inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-10">
                            <div className="text-halo-cyan animate-pulse flex flex-col items-center gap-2">
                                <Loader2 size={32} className="animate-spin" />
                                <span className="text-xs font-mono">FORMULATING STRATEGY...</span>
                            </div>
                        </div>
                    )}
                    {strategies ? (
                        <div className="prose prose-invert prose-sm max-w-none">
                            <div className="whitespace-pre-wrap leading-relaxed text-halo-text/90">{strategies}</div>
                        </div>
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center text-halo-muted opacity-50">
                            <BrainCircuit size={48} className="mb-4" />
                            <p className="text-center max-w-xs">Generate potential legal strategies based on extracted facts and case law precedents.</p>
                        </div>
                    )}
                </div>
            </div>
        );
    }

    if (activeSubmodule === 'elements') {
        return (
            <div className="w-full h-full flex flex-col p-8 text-halo-text overflow-hidden">
                <div className="flex items-center justify-between mb-6 shrink-0">
                    <div className="flex items-center gap-3 text-halo-cyan">
                        <Scale size={24} />
                        <h3 className="text-lg font-mono uppercase tracking-wide">Legal Elements Map</h3>
                    </div>
                    <button
                        onClick={handleAnalyzeElements}
                        disabled={loadingElements || autonomousMode}
                        className="flex items-center gap-2 px-4 py-2 bg-halo-cyan/10 hover:bg-halo-cyan/20 text-halo-cyan border border-halo-cyan/30 rounded transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm uppercase tracking-wider"
                    >
                        {loadingElements ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
                        {loadingElements ? 'Mapping...' : 'Map Elements'}
                    </button>
                </div>
                <div className="flex-1 bg-black/30 rounded-lg p-6 border border-halo-border overflow-y-auto custom-scrollbar relative">
                    {loadingElements && (
                        <div className="absolute inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-10">
                            <div className="text-halo-cyan animate-pulse flex flex-col items-center gap-2">
                                <Loader2 size={32} className="animate-spin" />
                                <span className="text-xs font-mono">MAPPING EVIDENCE TO ELEMENTS...</span>
                            </div>
                        </div>
                    )}
                    {elements ? (
                        <div className="prose prose-invert prose-sm max-w-none">
                            <div className="whitespace-pre-wrap leading-relaxed text-halo-text/90">{elements}</div>
                        </div>
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center text-halo-muted opacity-50">
                            <Scale size={48} className="mb-4" />
                            <p className="text-center max-w-xs">Map available evidence to specific legal elements (Duty, Breach, Causation, Damages).</p>
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // Default / Facts View
    return (
        <div className="w-full h-full flex flex-col p-8 text-halo-text overflow-hidden">
            {/* Header & Controls */}
            <div className="flex items-center justify-between mb-8 shrink-0">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-halo-cyan/10 rounded-lg border border-halo-cyan/30 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                        <Scale className="text-halo-cyan w-8 h-8" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider">Legal Theory</h2>
                        <p className="text-halo-muted text-sm">Automated fact pattern analysis and strategy formulation</p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    {/* Custom Query Input */}
                    <form onSubmit={handleCustomQuery} className="relative w-96">
                        <input
                            type="text"
                            value={customQuery}
                            onChange={(e) => setCustomQuery(e.target.value)}
                            placeholder="Ask a specific legal question..."
                            className="w-full bg-black/50 border border-halo-border rounded-full pl-4 pr-12 py-2 text-sm focus:border-halo-cyan focus:outline-none transition-all"
                        />
                        <button
                            type="submit"
                            disabled={loadingCustom}
                            className="absolute right-2 top-1.5 p-1 text-halo-cyan hover:text-white disabled:opacity-50"
                        >
                            {loadingCustom ? <Loader2 size={16} className="animate-spin" /> : <MessageSquare size={16} />}
                        </button>
                    </form>

                    {/* Auto Toggle */}
                    <button
                        onClick={() => setAutonomousMode(!autonomousMode)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-full border transition-all uppercase text-xs font-bold tracking-wider ${autonomousMode
                            ? 'bg-halo-cyan text-black border-halo-cyan shadow-[0_0_15px_#00f0ff]'
                            : 'bg-transparent text-halo-muted border-halo-border hover:border-halo-cyan hover:text-halo-cyan'
                            }`}
                    >
                        {autonomousMode ? <Pause size={14} /> : <Play size={14} />}
                        {autonomousMode ? 'Auto-Analysis ON' : 'Start Auto-Analysis'}
                    </button>
                </div>
            </div>

            {/* Custom Response Area (if active) */}
            {customResponse && (
                <div className="mb-8 bg-halo-cyan/5 border border-halo-cyan/20 rounded-lg p-6 shrink-0 animate-in fade-in slide-in-from-top-4">
                    <div className="flex justify-between items-start mb-2">
                        <h3 className="text-halo-cyan font-bold text-sm uppercase tracking-wider flex items-center gap-2">
                            <MessageSquare size={16} /> Custom Analysis
                        </h3>
                        <button onClick={() => setCustomResponse(null)} className="text-halo-muted hover:text-white"><Zap size={14} /></button>
                    </div>
                    <p className="text-halo-text/90 leading-relaxed whitespace-pre-wrap">{customResponse}</p>
                </div>
            )}

            {/* Fact Pattern Extraction (Default View) */}
            <div className="halo-card flex flex-col flex-1 overflow-hidden">
                <div className="flex items-center justify-between mb-6 shrink-0">
                    <div className="flex items-center gap-3 text-halo-cyan">
                        <Target size={24} />
                        <h3 className="text-lg font-mono uppercase tracking-wide">Fact Patterns</h3>
                    </div>
                    <button
                        onClick={handleExtractFacts}
                        disabled={loadingFacts || autonomousMode}
                        className="flex items-center gap-2 px-4 py-2 bg-halo-cyan/10 hover:bg-halo-cyan/20 text-halo-cyan border border-halo-cyan/30 rounded transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm uppercase tracking-wider"
                    >
                        {loadingFacts ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
                        {loadingFacts ? 'Analyzing...' : 'Extract Facts'}
                    </button>
                </div>

                <div className="flex-1 bg-black/30 rounded-lg p-6 border border-halo-border overflow-y-auto custom-scrollbar relative">
                    {loadingFacts && (
                        <div className="absolute inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-10">
                            <div className="text-halo-cyan animate-pulse flex flex-col items-center gap-2">
                                <Loader2 size={32} className="animate-spin" />
                                <span className="text-xs font-mono">EXTRACTING PATTERNS...</span>
                            </div>
                        </div>
                    )}
                    {facts ? (
                        <div className="prose prose-invert prose-sm max-w-none">
                            <div className="whitespace-pre-wrap leading-relaxed text-halo-text/90">{facts}</div>
                        </div>
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center text-halo-muted opacity-50">
                            <FileText size={48} className="mb-4" />
                            <p className="text-center max-w-xs">Initiate analysis to extract key facts and timeline inconsistencies from the evidence corpus.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
