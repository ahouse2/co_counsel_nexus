import { useState, useEffect } from 'react';
import { Activity, Terminal, Cpu, Network } from 'lucide-react';

interface Agent {
    id: string;
    name: string;
    role: string;
    status: 'idle' | 'thinking' | 'executing' | 'error';
    currentTask?: string;
}

export function AgentConsoleModule() {
    const [agents, setAgents] = useState<Agent[]>([]);
    const [logs, setLogs] = useState<string[]>([]);

    useEffect(() => {
        const eventSource = new EventSource('/api/agents/stream');

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                const timestamp = new Date(data.timestamp).toLocaleTimeString();

                // Update Logs
                const newLog = `[${timestamp}] ${data.agent}: ${data.message}`;
                setLogs(prev => [newLog, ...prev].slice(0, 50));

                // Update Agents
                setAgents(prev => {
                    const agentId = data.agent;
                    const existingAgentIndex = prev.findIndex(a => a.id === agentId);

                    let status: Agent['status'] = 'executing';
                    if (data.action.includes('completed') || data.outcome === 'success') status = 'idle';
                    if (data.outcome === 'error' || data.outcome === 'failed') status = 'error';

                    // Map known roles or default
                    let role = 'Agent';
                    if (agentId.toLowerCase().includes('strategy')) role = 'Legal Strategy';
                    if (agentId.toLowerCase().includes('research')) role = 'Legal Research';
                    if (agentId.toLowerCase().includes('ingestion')) role = 'Data Ingestion';
                    if (agentId.toLowerCase().includes('graph')) role = 'Knowledge Graph';
                    if (agentId.toLowerCase().includes('qa')) role = 'Quality Assurance';

                    const updatedAgent: Agent = {
                        id: agentId,
                        name: agentId,
                        role: role,
                        status: status,
                        currentTask: status === 'executing' ? data.action : undefined
                    };

                    if (existingAgentIndex >= 0) {
                        const newAgents = [...prev];
                        newAgents[existingAgentIndex] = { ...newAgents[existingAgentIndex], ...updatedAgent };
                        return newAgents;
                    } else {
                        return [...prev, updatedAgent];
                    }
                });

            } catch (e) {
                console.error("Error parsing agent event:", e);
            }
        };

        eventSource.onerror = (err) => {
            console.error("EventSource failed:", err);
            eventSource.close();
        };

        return () => {
            eventSource.close();
        };
    }, []);

    return (
        <div className="w-full h-full flex flex-col p-8 text-halo-text overflow-hidden">
            <div className="flex items-center gap-4 mb-8">
                <div className="p-3 bg-halo-cyan/10 rounded-lg border border-halo-cyan/30 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                    <Network className="text-halo-cyan w-8 h-8" />
                </div>
                <div>
                    <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider">Agent Command Center</h2>
                    <p className="text-halo-muted text-sm">Network observation and task orchestration</p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 flex-1 overflow-hidden">
                {/* Agent Grid */}
                <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-6 overflow-y-auto custom-scrollbar pr-2">
                    {agents.map(agent => (
                        <div key={agent.id} className="halo-card relative group hover:border-halo-cyan/50 transition-all">
                            <div className="flex items-start justify-between mb-4">
                                <div className="flex items-center gap-3">
                                    <div className={`p-2 rounded-full ${agent.status === 'thinking' ? 'bg-yellow-500/20 text-yellow-400 animate-pulse' : agent.status === 'executing' ? 'bg-green-500/20 text-green-400' : 'bg-gray-800 text-gray-400'}`}>
                                        <Cpu size={20} />
                                    </div>
                                    <div>
                                        <h3 className="font-mono font-bold text-halo-text">{agent.name}</h3>
                                        <p className="text-xs text-halo-muted">{agent.role}</p>
                                    </div>
                                </div>
                                <div className={`px-2 py-1 rounded text-xs font-bold uppercase ${agent.status === 'thinking' ? 'text-yellow-400 border border-yellow-500/30' : agent.status === 'executing' ? 'text-green-400 border border-green-500/30' : 'text-gray-500 border border-gray-700'}`}>
                                    {agent.status}
                                </div>
                            </div>

                            {agent.currentTask && (
                                <div className="mt-4 p-3 bg-black/40 rounded border border-halo-border/50">
                                    <div className="flex items-center gap-2 text-xs text-halo-cyan mb-1">
                                        <Activity size={12} className="animate-spin" /> CURRENT TASK
                                    </div>
                                    <p className="text-sm text-halo-text/90 font-mono">{agent.currentTask}</p>
                                </div>
                            )}

                            <div className="absolute inset-0 bg-gradient-to-br from-halo-cyan/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                        </div>
                    ))}
                </div>

                {/* System Logs */}
                <div className="halo-card flex flex-col overflow-hidden border-l-4 border-l-halo-cyan/50">
                    <div className="flex items-center gap-2 mb-4 text-halo-muted border-b border-halo-border pb-2">
                        <Terminal size={16} />
                        <span className="font-mono text-xs uppercase tracking-wider">System Stream</span>
                    </div>
                    <div className="flex-1 overflow-y-auto custom-scrollbar font-mono text-xs space-y-2">
                        {logs.map((log, i) => (
                            <div key={i} className="text-halo-text/70 hover:text-halo-cyan transition-colors border-b border-white/5 pb-1">
                                {log}
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
