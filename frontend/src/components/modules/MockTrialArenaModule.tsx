import { useState, useEffect, useRef } from 'react';
import { Gavel, Users, Activity, Play, Shield, Sword, Brain, Terminal } from 'lucide-react';
import { endpoints } from '../../services/api';

interface SimulationStep {
    id: string;
    role: 'prosecution' | 'defense' | 'judge';
    content: string;
    tool?: string;
    timestamp: number;
}

export function MockTrialArenaModule() {
    const [activeSimulation, setActiveSimulation] = useState(false);
    const [simulationSteps, setSimulationSteps] = useState<SimulationStep[]>([]);
    const scrollRef = useRef<HTMLDivElement>(null);
    const [caseContext, setCaseContext] = useState<string>('');

    useEffect(() => {
        // Fetch case context on mount
        const fetchContext = async () => {
            try {
                const res = await endpoints.context.query("Provide a detailed factual summary and list of contested issues for a mock trial debate.");
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

            // const scenario = "Current Case Simulation";
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

    if (!activeSimulation) {
        return (
            <div className="flex-1 flex items-center justify-center p-6 h-full">
                <div className="text-center max-w-2xl w-full">
                    <div className="w-32 h-32 rounded-full bg-halo-cyan/5 border border-halo-cyan flex items-center justify-center mx-auto mb-8 animate-pulse-slow shadow-[0_0_30px_rgba(0,240,255,0.2)]">
                        <Gavel size={64} className="text-halo-cyan" />
                    </div>
                    <h2 className="text-3xl font-light text-halo-text mb-4 uppercase tracking-widest">Mock Trial Arena</h2>
                    <p className="text-halo-muted mb-12 text-lg">
                        Configure adversarial AI agents to simulate trial outcomes. Test strategies against specific judge profiles and jury demographics.
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <button className="halo-card hover:bg-halo-cyan/10 transition-all group py-8 flex flex-col items-center gap-4">
                            <Users className="text-halo-cyan group-hover:scale-110 transition-transform" size={32} />
                            <div className="text-center">
                                <span className="block text-sm uppercase tracking-wider font-bold text-halo-text">Jury Selection</span>
                                <span className="text-xs text-halo-muted mt-1">Configure Demographics</span>
                            </div>
                        </button>
                        <button className="halo-card hover:bg-halo-cyan/10 transition-all group py-8 flex flex-col items-center gap-4">
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
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col h-full p-6 overflow-hidden">
            {/* Header */}
            <div className="flex justify-between items-center mb-6 border-b border-halo-border pb-4">
                <div>
                    <h2 className="text-xl font-light text-halo-text uppercase tracking-widest flex items-center gap-3">
                        <Activity className="text-halo-cyan animate-pulse" size={20} />
                        Live Simulation
                    </h2>
                    <div className="text-xs text-halo-muted mt-1 font-mono">SCENARIO_ID: SIM-8842-ALPHA // STATE V. MILLER</div>
                </div>
                <button
                    onClick={() => { setActiveSimulation(false); setSimulationSteps([]); }}
                    className="px-4 py-2 border border-halo-border rounded hover:border-halo-cyan text-halo-muted hover:text-halo-cyan transition-colors text-sm uppercase tracking-wider"
                >
                    Abort Simulation
                </button>
            </div>

            {/* Arena */}
            <div className="flex-1 flex gap-6 overflow-hidden">
                {/* Left: Prosecution */}
                <div className="w-1/4 hidden md:flex flex-col gap-4 opacity-50">
                    <div className="halo-card h-full flex flex-col items-center justify-center border-red-500/30 bg-red-500/5">
                        <Sword size={48} className="text-red-500 mb-4" />
                        <h3 className="text-red-500 font-mono uppercase tracking-widest">Prosecution</h3>
                        <div className="mt-4 text-xs text-red-400/70 font-mono">AGENT: ARES-V4</div>
                    </div>
                </div>

                {/* Center: Transcript */}
                <div className="flex-1 halo-card bg-black/40 flex flex-col overflow-hidden relative">
                    <div className="absolute inset-0 bg-[url('/grid.png')] opacity-5 pointer-events-none" />
                    <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar" ref={scrollRef}>
                        {simulationSteps.map((step) => (
                            <div
                                key={step.id}
                                className={`flex flex-col ${step.role === 'prosecution' ? 'items-start' :
                                    step.role === 'defense' ? 'items-end' : 'items-center'
                                    }`}
                            >
                                <div className={`max-w-[80%] rounded-lg p-4 border ${step.role === 'prosecution' ? 'bg-red-950/20 border-red-500/30 text-red-100 rounded-tl-none' :
                                    step.role === 'defense' ? 'bg-blue-950/20 border-blue-500/30 text-blue-100 rounded-tr-none' :
                                        'bg-halo-bg border-halo-border text-halo-text text-center italic'
                                    }`}>
                                    <div className="flex justify-between items-center mb-2 gap-4">
                                        <span className={`text-xs font-bold uppercase tracking-wider ${step.role === 'prosecution' ? 'text-red-400' :
                                            step.role === 'defense' ? 'text-blue-400' : 'text-halo-muted'
                                            }`}>
                                            {step.role}
                                        </span>
                                        {step.tool && (
                                            <span className="flex items-center gap-1 text-[10px] font-mono bg-black/30 px-2 py-0.5 rounded text-halo-cyan border border-halo-cyan/20">
                                                <Terminal size={10} />
                                                TOOL: {step.tool}
                                            </span>
                                        )}
                                    </div>
                                    <p className="leading-relaxed">{step.content}</p>
                                </div>
                            </div>
                        ))}
                        {simulationSteps.length === 0 && (
                            <div className="text-center text-halo-muted mt-20 animate-pulse">
                                Initializing agents...
                            </div>
                        )}
                    </div>
                </div>

                {/* Right: Defense */}
                <div className="w-1/4 hidden md:flex flex-col gap-4 opacity-50">
                    <div className="halo-card h-full flex flex-col items-center justify-center border-blue-500/30 bg-blue-500/5">
                        <Shield size={48} className="text-blue-500 mb-4" />
                        <h3 className="text-blue-500 font-mono uppercase tracking-widest">Defense</h3>
                        <div className="mt-4 text-xs text-blue-400/70 font-mono">AGENT: ATHENA-V9</div>
                    </div>
                </div>
            </div>
        </div>
    );
}
