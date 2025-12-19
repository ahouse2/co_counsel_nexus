import { useState, useEffect, useRef } from 'react';
import { Gavel, Users, Play, Brain, Sword, Shield } from 'lucide-react';
import { endpoints } from '../../services/api';
import { VoiceConsole } from '../voice/VoiceConsole';

interface SimulationStep {
    id: string;
    role: 'prosecution' | 'defense' | 'judge' | 'opposing_counsel';
    type?: 'statement' | 'objection' | 'ruling';
    content: string;
    tool?: string;
    timestamp: number;
    jury_reactions?: any[];
    data?: any;
}

const JuryHeatmap = ({ reactions }: { reactions: any[] }) => {
    if (!reactions || reactions.length === 0) return null;
    return (
        <div className="flex gap-2 mt-3 bg-black/40 p-2 rounded-lg border border-white/5 w-fit">
            <span className="text-[10px] text-halo-muted uppercase tracking-wider self-center mr-2">Jury Reaction</span>
            {reactions.map((r, i) => (
                <div key={i} className="relative group cursor-help">
                    <div
                        className={`w-3 h-3 rounded-full transition-all duration-500 ${r.sentiment_score > 0.6 ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' :
                            r.sentiment_score < 0.4 ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]' :
                                'bg-yellow-500 shadow-[0_0_8px_rgba(234,179,8,0.6)]'
                            }`}
                    />
                    {/* Tooltip */}
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block bg-slate-900 border border-halo-border p-3 rounded-lg text-xs w-48 z-50 shadow-xl pointer-events-none">
                        <div className="font-bold text-halo-cyan mb-1">Juror {i + 1} ({Math.round(r.sentiment_score * 100)}%)</div>
                        <div className="text-white mb-1">{r.reaction}</div>
                        <div className="text-halo-muted italic">"{r.internal_thought}"</div>
                    </div>
                </div>
            ))}
        </div>
    );
};

interface MockTrialArenaModuleProps {
    caseId: string;
}

export function MockTrialArenaModule({ caseId }: MockTrialArenaModuleProps) {
    const [activeSimulation, setActiveSimulation] = useState(false);
    const [simulationSteps, setSimulationSteps] = useState<SimulationStep[]>([]);
    const scrollRef = useRef<HTMLDivElement>(null);
    const [caseContext, setCaseContext] = useState<string>('');

    // Configuration State
    const [showJuryConfig, setShowJuryConfig] = useState(false);
    const [showOpposingConfig, setShowOpposingConfig] = useState(false);
    const [juryDemographics, setJuryDemographics] = useState({ education: 'Mixed', age: '30-50', bias: 'Neutral' });
    const [opposingStyle, setOpposingStyle] = useState('Aggressive');

    // Juror Chat State
    const [activeJurorChat, setActiveJurorChat] = useState(false);

    useEffect(() => {
        // Fetch case context on mount
        const fetchContext = async () => {
            try {
                const res = await endpoints.context.query("Provide a detailed factual summary and list of contested issues for a mock trial debate.", caseId);
                setCaseContext(res.data?.response || "Standard mock trial scenario.");
            } catch (e) {
                console.error("Failed to fetch context", e);
                setCaseContext("Standard mock trial scenario.");
            }
        };
        fetchContext();
    }, []);

    useEffect(() => {
        let isRunning = true;

        const runSimulation = async () => {
            if (!activeSimulation) return;

            // Initial delay
            await new Promise(r => setTimeout(r, 1000));

            let history: SimulationStep[] = [];

            const steps = [
                { role: 'prosecution', prompt: `You are the Lead Prosecutor. Based on the following case context, deliver a powerful, concise opening statement (max 2 sentences) focusing on the key evidence.\n\nCONTEXT: ${caseContext}` },
                { role: 'defense', prompt: `You are the Defense Attorney. Rebut the prosecution's opening statement (max 2 sentences), questioning the reliability of the evidence.\n\nCONTEXT: ${caseContext}` },
                { role: 'judge', prompt: `You are the Presiding Judge. Make a procedural ruling on the opening statements and call the first witness.` },
                { role: 'prosecution', prompt: `You are the Prosecutor. Call your first witness and ask one critical question.` },
                { role: 'defense', prompt: `You are the Defense Attorney. Object to the Prosecutor's question.` },
                { role: 'judge', prompt: `You are the Judge. Rule on the objection.` }
            ];

            for (let i = 0; i < steps.length; i++) {
                if (!isRunning || !activeSimulation) break;

                const stepConfig = steps[i];
                const context = history.map(h => `${h.role.toUpperCase()}: ${h.content}`).join('\n');
                const fullPrompt = `${stepConfig.prompt}\n\nTranscript so far:\n${context}`;

                try {
                    const response = await endpoints.agents.chat(fullPrompt);
                    const content = response.data.response || response.data.answer || (typeof response.data === 'string' ? response.data : JSON.stringify(response.data));

                    const newStep: SimulationStep = {
                        id: `step-${Date.now()}`,
                        role: stepConfig.role as 'prosecution' | 'defense' | 'judge',
                        content: content,
                        tool: i === 3 ? 'Witness Database' : undefined,
                        timestamp: Date.now()
                    };

                    history.push(newStep);
                    setSimulationSteps(prev => [...prev, newStep]);

                } catch (error) {
                    console.error("Agent simulation failed:", error);
                    const newStep: SimulationStep = {
                        id: `err-${Date.now()}`,
                        role: 'judge',
                        content: "Simulation paused due to neural link interruption.",
                        timestamp: Date.now()
                    };
                    setSimulationSteps(prev => [...prev, newStep]);
                    break;
                }

                // Wait before next turn
                await new Promise(r => setTimeout(r, 3000));
            }
        };

        runSimulation();

        return () => {
            isRunning = false;
        };
    }, [activeSimulation, caseContext]);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [simulationSteps]);

    if (activeJurorChat) {
        return (
            <div className="flex-1 flex flex-col h-full bg-black/80 relative">
                {/* Header */}
                <div className="p-4 border-b border-halo-border bg-halo-bg/50 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <Users className="text-halo-cyan" />
                        <div>
                            <span className="font-mono text-sm uppercase tracking-wider text-halo-text block">Juror Persona Chat</span>
                            <span className="text-xs text-halo-muted">
                                {juryDemographics.education} • {juryDemographics.age} • {juryDemographics.bias}
                            </span>
                        </div>
                    </div>
                    <button
                        onClick={() => setActiveJurorChat(false)}
                        className="text-xs text-halo-muted hover:text-white uppercase tracking-wider"
                    >
                        End Chat
                    </button>
                </div>

                {/* Voice Console Integration */}
                <div className="flex-1 flex items-center justify-center p-6">
                    <div className="w-full max-w-2xl space-y-8">
                        <div className="text-center">
                            <h3 className="text-2xl font-light text-halo-text mb-2">Voice Interface Active</h3>
                            <p className="text-halo-muted">Speak naturally to argue your case. The jury is listening.</p>
                        </div>

                        <VoiceConsole caseId="simulation" personaId="juror_composite" />

                        {/* Transcript / History Display could go here if needed, 
                            but VoiceConsole handles the immediate interaction */}
                    </div>
                </div>
            </div>
        );
    }

    if (!activeSimulation) {
        return (
            <div className="flex-1 flex items-center justify-center p-6 h-full relative">
                <div className="text-center max-w-2xl w-full">
                    <div className="w-32 h-32 rounded-full bg-halo-cyan/5 border border-halo-cyan flex items-center justify-center mx-auto mb-8 animate-pulse-slow shadow-[0_0_30px_rgba(0,240,255,0.2)]">
                        <Gavel size={64} className="text-halo-cyan" />
                    </div>
                    <h2 className="text-3xl font-light text-halo-text mb-4 uppercase tracking-widest">Mock Trial Arena</h2>
                    <p className="text-halo-muted mb-12 text-lg">
                        Configure adversarial AI agents to simulate trial outcomes. Test strategies against specific judge profiles and jury demographics.
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <button
                            onClick={() => setShowJuryConfig(true)}
                            className="halo-card hover:bg-halo-cyan/10 transition-all group py-8 flex flex-col items-center gap-4"
                        >
                            <Users className="text-halo-cyan group-hover:scale-110 transition-transform" size={32} />
                            <div className="text-center">
                                <span className="block text-sm uppercase tracking-wider font-bold text-halo-text">Jury Selection</span>
                                <span className="text-xs text-halo-muted mt-1">Configure Demographics</span>
                            </div>
                        </button>
                        <button
                            onClick={() => setActiveJurorChat(true)}
                            className="halo-card hover:bg-halo-cyan/10 transition-all group py-8 flex flex-col items-center gap-4"
                        >
                            <Brain className="text-halo-cyan group-hover:scale-110 transition-transform" size={32} />
                            <div className="text-center">
                                <span className="block text-sm uppercase tracking-wider font-bold text-halo-text">Juror Chat</span>
                                <span className="text-xs text-halo-muted mt-1">Test Arguments (Voice)</span>
                            </div>
                        </button>
                        <button
                            onClick={() => setShowOpposingConfig(true)}
                            className="halo-card hover:bg-halo-cyan/10 transition-all group py-8 flex flex-col items-center gap-4"
                        >
                            <Brain className="text-halo-cyan group-hover:scale-110 transition-transform" size={32} />
                            <div className="text-center">
                                <span className="block text-sm uppercase tracking-wider font-bold text-halo-text">Opposing Counsel</span>
                                <span className="text-xs text-halo-muted mt-1">Set AI Personality</span>
                            </div>
                        </button>
                        <button
                            onClick={() => setActiveSimulation(true)}
                            className="halo-card bg-halo-cyan/10 border-halo-cyan hover:bg-halo-cyan/20 transition-all group py-8 flex flex-col items-center gap-4 shadow-[0_0_15px_rgba(0,240,255,0.1)]"
                        >
                            <Play className="text-halo-cyan group-hover:scale-110 transition-transform fill-current" size={32} />
                            <div className="text-center">
                                <span className="block text-sm uppercase tracking-wider font-bold text-halo-text">Start Simulation</span>
                                <span className="text-xs text-halo-muted mt-1">Run Scenario</span>
                            </div>
                        </button>
                    </div>
                </div>

                {/* Jury Config Modal */}
                {showJuryConfig && (
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50">
                        <div className="bg-halo-bg border border-halo-cyan p-8 rounded-xl max-w-md w-full shadow-[0_0_50px_rgba(0,240,255,0.2)]">
                            <h3 className="text-xl font-bold text-halo-cyan mb-6 uppercase tracking-widest flex items-center gap-2">
                                <Users /> Jury Configuration
                            </h3>
                            <div className="space-y-4 mb-8">
                                <div>
                                    <label className="block text-xs text-halo-muted mb-1 uppercase">Education Level</label>
                                    <select
                                        value={juryDemographics.education}
                                        onChange={(e) => setJuryDemographics(prev => ({ ...prev, education: e.target.value }))}
                                        className="w-full bg-black border border-halo-border rounded p-2 text-halo-text focus:border-halo-cyan outline-none"
                                        title="Select education level"
                                    >
                                        <option>High School</option>
                                        <option>College Graduate</option>
                                        <option>Post-Graduate</option>
                                        <option>Mixed</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs text-halo-muted mb-1 uppercase">Age Range</label>
                                    <select
                                        value={juryDemographics.age}
                                        onChange={(e) => setJuryDemographics(prev => ({ ...prev, age: e.target.value }))}
                                        className="w-full bg-black border border-halo-border rounded p-2 text-halo-text focus:border-halo-cyan outline-none"
                                        title="Select age range"
                                    >
                                        <option>18-30</option>
                                        <option>30-50</option>
                                        <option>50+</option>
                                        <option>Mixed</option>
                                    </select>
                                </div>
                            </div>
                            <div className="flex justify-end gap-4">
                                <button onClick={() => setShowJuryConfig(false)} className="px-4 py-2 text-halo-muted hover:text-white">Cancel</button>
                                <button onClick={() => setShowJuryConfig(false)} className="px-4 py-2 bg-halo-cyan text-black font-bold rounded hover:bg-white transition-colors">Save Configuration</button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Opposing Counsel Config Modal */}
                {showOpposingConfig && (
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50">
                        <div className="bg-halo-bg border border-halo-cyan p-8 rounded-xl max-w-md w-full shadow-[0_0_50px_rgba(0,240,255,0.2)]">
                            <h3 className="text-xl font-bold text-halo-cyan mb-6 uppercase tracking-widest flex items-center gap-2">
                                <Brain /> Opposing Counsel
                            </h3>
                            <div className="space-y-4 mb-8">
                                <div>
                                    <label className="block text-xs text-halo-muted mb-1 uppercase">Personality / Strategy</label>
                                    <div className="grid grid-cols-2 gap-2">
                                        {['Aggressive', 'Logical', 'Emotional', 'Procedural'].map(style => (
                                            <button
                                                key={style}
                                                onClick={() => setOpposingStyle(style)}
                                                className={`p-3 rounded border text-sm transition-all ${opposingStyle === style
                                                    ? 'bg-halo-cyan text-black border-halo-cyan font-bold'
                                                    : 'bg-black border-halo-border text-halo-muted hover:border-halo-cyan'}`}
                                            >
                                                {style}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                            <div className="flex justify-end gap-4">
                                <button onClick={() => setShowOpposingConfig(false)} className="px-4 py-2 text-halo-muted hover:text-white">Cancel</button>
                                <button onClick={() => setShowOpposingConfig(false)} className="px-4 py-2 bg-halo-cyan text-black font-bold rounded hover:bg-white transition-colors">Confirm Agent</button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col h-full overflow-hidden relative">
            {/* Header */}
            <div className="p-4 border-b border-halo-border bg-halo-bg/50 flex justify-between items-center">
                <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                    <span className="font-mono text-sm uppercase tracking-wider text-halo-text">Live Simulation</span>
                </div>
                <button
                    onClick={() => setActiveSimulation(false)}
                    className="text-xs text-halo-muted hover:text-white uppercase tracking-wider"
                >
                    End Session
                </button>
            </div>

            {/* Simulation Stream */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar" ref={scrollRef}>
                {simulationSteps.map((step) => (
                    <div key={step.id} className={`flex gap-4 ${step.role === 'judge' || step.type === 'objection' ? 'justify-center' : ''} animate-in fade-in slide-in-from-bottom-2`}>
                        {step.type === 'objection' ? (
                            <div className="w-full max-w-2xl my-4 animate-in zoom-in duration-300">
                                <div className="bg-red-950/40 border-2 border-red-500/50 px-8 py-6 rounded-xl relative overflow-hidden backdrop-blur-sm">
                                    <div className="absolute inset-0 bg-red-500/5 animate-pulse" />
                                    <h3 className="text-3xl font-black text-red-500 uppercase tracking-widest relative z-10 flex items-center justify-center gap-4 mb-2">
                                        <Gavel size={32} /> Objection!
                                    </h3>
                                    <p className="text-red-200 text-center font-mono relative z-10 text-lg">{step.content.replace("Objection! ", "")}</p>
                                </div>
                            </div>
                        ) : (
                            <>
                                {step.role !== 'judge' && (
                                    <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 
                                        ${step.role === 'prosecution' ? 'bg-red-500/10 text-red-500 border border-red-500/30' :
                                            step.role === 'opposing_counsel' ? 'bg-red-500/10 text-red-500 border border-red-500/30' :
                                                'bg-blue-500/10 text-blue-500 border border-blue-500/30'}`}>
                                        {step.role === 'prosecution' || step.role === 'opposing_counsel' ? <Sword size={20} /> : <Shield size={20} />}
                                    </div>
                                )}

                                <div className={`max-w-3xl ${step.role === 'judge' ? 'w-full' : ''}`}>
                                    <div className={`mb-1 flex items-center gap-2 ${step.role === 'judge' ? 'justify-center' : ''}`}>
                                        <span className={`text-xs font-bold uppercase tracking-wider 
                                            ${step.role === 'prosecution' || step.role === 'opposing_counsel' ? 'text-red-500' :
                                                step.role === 'defense' ? 'text-blue-500' : 'text-yellow-500'}`}>
                                            {step.role === 'opposing_counsel' ? 'Opposing Counsel' : step.role}
                                        </span>
                                        <span className="text-[10px] text-halo-muted">{new Date(step.timestamp).toLocaleTimeString()}</span>
                                    </div>

                                    <div className={`p-4 rounded border ${step.role === 'judge'
                                        ? 'bg-yellow-500/5 border-yellow-500/20 text-center'
                                        : 'bg-halo-card border-halo-border'}`}>
                                        {step.role === 'judge' && <Gavel className="mx-auto mb-2 text-yellow-500" size={24} />}
                                        <p className="text-halo-text leading-relaxed whitespace-pre-wrap">{step.content}</p>

                                        {/* Render Jury Heatmap if reactions exist */}
                                        {step.jury_reactions && <JuryHeatmap reactions={step.jury_reactions} />}
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
