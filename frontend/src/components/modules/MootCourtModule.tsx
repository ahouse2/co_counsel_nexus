import { useState, useRef, useEffect } from 'react';
import { endpoints } from '../../services/api';
import { motion } from 'framer-motion';
import { Gavel, ShieldAlert, Send, User, Bot, AlertTriangle, TrendingUp } from 'lucide-react';

interface Message {
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: Date;
    metadata?: any;
}

interface SimulationLogItem {
    role: string;
    statement: string;
    internal_strategy?: any[];
}

export function MootCourtModule() {
    const [messages, setMessages] = useState<Message[]>([
        {
            role: 'system',
            content: 'Welcome to the War Room. I am your Opposing Counsel simulation. State your case theory or argument, and I will attempt to dismantle it.',
            timestamp: new Date()
        }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [riskScore, setRiskScore] = useState<number>(0);
    const [simulationLog, setSimulationLog] = useState<SimulationLogItem[]>([]);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSendMessage = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const userMsg: Message = {
            role: 'user',
            content: input,
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setIsLoading(true);

        try {
            // We treat a single message as a mini-simulation for now
            const response = await endpoints.simulation.mootCourt({
                case_brief: "User provided argument context",
                agent_role: "prosecutor", // User is playing prosecutor/defense
                objectives: ["win the argument"],
                initial_statement: input,
                max_turns: 1 // Single turn response for chat-like feel
            });

            const result = response.data;
            const log = result.simulation_log || [];

            // Extract opposing counsel's response
            const opposingResponse = log.find((l: any) => l.role === 'opposing_counsel');

            if (opposingResponse) {
                const botMsg: Message = {
                    role: 'assistant',
                    content: opposingResponse.statement,
                    timestamp: new Date(),
                    metadata: opposingResponse.internal_strategy
                };
                setMessages(prev => [...prev, botMsg]);

                // Calculate risk score from opposing counsel's strategy analysis
                if (opposingResponse.internal_strategy) {
                    const avgRisk = opposingResponse.internal_strategy.reduce((acc: number, curr: any) => acc + (curr.risk_score || 0), 0) / opposingResponse.internal_strategy.length;
                    setRiskScore(avgRisk);
                }
            }

            setSimulationLog(log);

        } catch (error) {
            console.error("Simulation failed:", error);
            setMessages(prev => [...prev, {
                role: 'system',
                content: 'Simulation error. Opposing counsel is currently unavailable.',
                timestamp: new Date()
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="w-full h-full flex flex-col p-8 text-halo-text relative overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-red-500/10 rounded-lg border border-red-500/30 shadow-[0_0_15px_rgba(255,0,0,0.2)]">
                        <Gavel className="text-red-500 w-8 h-8" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider">Devil's Advocate</h2>
                        <p className="text-halo-muted text-sm">Adversarial Simulation & Risk Analysis</p>
                    </div>
                </div>

                {/* Risk Meter */}
                <div className="flex items-center gap-4 bg-black/40 border border-halo-border rounded-xl p-4">
                    <div className="text-right">
                        <div className="text-xs text-halo-muted uppercase font-bold tracking-wider">Current Risk Level</div>
                        <div className={`text-2xl font-mono font-bold ${riskScore > 0.7 ? 'text-red-500' :
                            riskScore > 0.4 ? 'text-yellow-500' : 'text-green-500'
                            }`}>
                            {(riskScore * 100).toFixed(0)}%
                        </div>
                    </div>
                    <div className="h-12 w-1 bg-halo-border/30 rounded-full overflow-hidden relative">
                        <div
                            className={`absolute bottom-0 left-0 right-0 transition-all duration-1000 ${riskScore > 0.7 ? 'bg-red-500' :
                                riskScore > 0.4 ? 'bg-yellow-500' : 'bg-green-500'
                                }`}
                            style={{ height: `${riskScore * 100}%` }}
                        />
                    </div>
                    <AlertTriangle className={`${riskScore > 0.7 ? 'text-red-500 animate-pulse' : 'text-halo-muted'
                        }`} />
                </div>
            </div>

            <div className="flex-1 flex gap-8 overflow-hidden">
                {/* Chat Area */}
                <div className="flex-1 flex flex-col bg-black/20 border border-halo-border/30 rounded-xl overflow-hidden">
                    <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
                        {messages.map((msg, idx) => (
                            <motion.div
                                key={idx}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                            >
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-halo-cyan/20 text-halo-cyan' :
                                    msg.role === 'assistant' ? 'bg-red-500/20 text-red-500' : 'bg-gray-700 text-gray-400'
                                    }`}>
                                    {msg.role === 'user' ? <User size={20} /> : msg.role === 'assistant' ? <Bot size={20} /> : <ShieldAlert size={20} />}
                                </div>

                                <div className={`max-w-[80%] space-y-2`}>
                                    <div className={`p-4 rounded-xl backdrop-blur-sm border ${msg.role === 'user' ? 'bg-halo-cyan/5 border-halo-cyan/20 text-white' :
                                        msg.role === 'assistant' ? 'bg-red-900/10 border-red-500/20 text-gray-200' : 'bg-gray-800/50 border-gray-700 text-gray-400 italic'
                                        }`}>
                                        <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                                    </div>

                                    {/* Strategy Metadata Display */}
                                    {msg.metadata && (
                                        <div className="text-xs space-y-1 ml-2">
                                            {msg.metadata.map((meta: any, i: number) => (
                                                <div key={i} className="flex items-center gap-2 text-red-400/70">
                                                    <TrendingUp size={12} />
                                                    <span>Counter-point: {meta.counter_point} (Risk: {meta.risk_score})</span>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    <div className={`text-xs text-halo-muted ${msg.role === 'user' ? 'text-right' : ''}`}>
                                        {msg.timestamp.toLocaleTimeString()}
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input Area */}
                    <form onSubmit={handleSendMessage} className="p-4 bg-black/40 border-t border-halo-border/30 flex gap-4">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Argue your case..."
                            className="flex-1 bg-black/50 border border-halo-border rounded-lg px-4 py-3 focus:border-halo-cyan focus:outline-none transition-all"
                            disabled={isLoading}
                        />
                        <button
                            type="submit"
                            disabled={isLoading || !input.trim()}
                            className="px-6 py-3 bg-halo-cyan/10 hover:bg-halo-cyan/20 text-halo-cyan border border-halo-cyan/50 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                            <Send size={18} />
                            {isLoading ? 'ANALYZING...' : 'CHALLENGE'}
                        </button>
                    </form>
                </div>

                {/* War Room Dashboard (Right Panel) */}
                <div className="w-80 bg-black/20 border border-halo-border/30 rounded-xl p-6 overflow-y-auto custom-scrollbar">
                    <h3 className="text-sm font-mono text-halo-muted uppercase tracking-widest mb-6 flex items-center gap-2">
                        <ShieldAlert size={16} /> War Room Intel
                    </h3>

                    <div className="space-y-6">
                        <div className="p-4 bg-black/40 border border-halo-border/50 rounded-lg">
                            <h4 className="text-halo-cyan font-bold mb-2 text-sm">Opponent Profile</h4>
                            <div className="flex items-center gap-3 mb-2">
                                <div className="w-12 h-12 bg-red-500/20 rounded-full flex items-center justify-center border border-red-500/50">
                                    <Bot className="text-red-500" />
                                </div>
                                <div>
                                    <div className="font-bold text-white">The Opposer</div>
                                    <div className="text-xs text-halo-muted">Aggressive Strategy</div>
                                </div>
                            </div>
                            <div className="text-xs text-gray-400 mt-2">
                                Specializes in finding logical inconsistencies and evidentiary gaps.
                            </div>
                        </div>

                        {simulationLog.length > 0 && (
                            <div className="space-y-4">
                                <h4 className="text-halo-cyan font-bold text-sm border-b border-halo-border/30 pb-2">Recent Maneuvers</h4>
                                {simulationLog.filter(l => l.role === 'opposing_counsel').slice(-3).map((log, i) => (
                                    <div key={i} className="text-xs text-gray-400 bg-black/30 p-3 rounded border-l-2 border-red-500">
                                        <div className="font-bold text-red-400 mb-1">Counter-Argument</div>
                                        <div className="line-clamp-3 italic">"{log.statement}"</div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
