import React, { useState, useEffect } from 'react';
import { Activity, Server, Cpu, Database, Shield, Zap, AlertCircle } from 'lucide-react';

export const DashboardModule: React.FC = () => {
    // Simulated System Stats
    const [stats, setStats] = useState({
        cpu: 12,
        memory: 45,
        apiLatency: 120,
        activeAgents: 8
    });

    useEffect(() => {
        const interval = setInterval(() => {
            setStats(prev => ({
                cpu: Math.min(100, Math.max(5, prev.cpu + (Math.random() - 0.5) * 10)),
                memory: Math.min(100, Math.max(20, prev.memory + (Math.random() - 0.5) * 5)),
                apiLatency: Math.max(50, prev.apiLatency + (Math.random() - 0.5) * 20),
                activeAgents: prev.activeAgents
            }));
        }, 2000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="w-full h-full p-8 overflow-y-auto">
            <header className="mb-8">
                <h1 className="text-4xl font-light text-white mb-2">Command Center</h1>
                <p className="text-halo-muted">System Status: <span className="text-green-400">OPERATIONAL</span></p>
            </header>

            {/* Top Row: System Health */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <StatCard
                    icon={<Cpu />}
                    label="CPU Load"
                    value={`${stats.cpu.toFixed(1)}%`}
                    color={stats.cpu > 80 ? 'text-red-500' : 'text-halo-cyan'}
                />
                <StatCard
                    icon={<Database />}
                    label="Memory Usage"
                    value={`${stats.memory.toFixed(1)}%`}
                    color={stats.memory > 80 ? 'text-yellow-500' : 'text-purple-400'}
                />
                <StatCard
                    icon={<Zap />}
                    label="API Latency"
                    value={`${stats.apiLatency.toFixed(0)}ms`}
                    color={stats.apiLatency > 300 ? 'text-red-500' : 'text-green-400'}
                />
                <StatCard
                    icon={<Activity />}
                    label="Active Agents"
                    value={stats.activeAgents.toString()}
                    color="text-blue-400"
                />
            </div>

            {/* Main Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 h-[600px]">

                {/* Left: Active Swarms Feed */}
                <div className="lg:col-span-2 bg-black/40 border border-white/10 rounded-xl p-6 flex flex-col">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-xl font-light flex items-center gap-2">
                            <Server size={20} className="text-halo-cyan" />
                            Swarm Activity
                        </h2>
                        <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full animate-pulse">LIVE</span>
                    </div>
                    <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
                        <LogEntry agent="GraphBuilder" action="Ingesting document 'Case_Brief_v2.pdf'" time="10:42:05" />
                        <LogEntry agent="LegalResearcher" action="Querying CourtListener for 'Smith v. Jones'" time="10:41:58" />
                        <LogEntry agent="NarrativeWeaver" action="Updating master timeline with new evidence" time="10:41:45" />
                        <LogEntry agent="DevTeam" action="Monitoring system performance - All nominal" time="10:41:30" />
                        <LogEntry agent="Forensics" action="Analyzing image metadata for 'Exhibit_A.jpg'" time="10:40:12" />
                        <LogEntry agent="CommunicationsOfficer" action="Routing message from User to LegalStrategist" time="10:39:55" />
                    </div>
                </div>

                {/* Right: Quick Actions & Alerts */}
                <div className="flex flex-col gap-6">
                    {/* System Status */}
                    <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-6">
                        <h2 className="text-lg font-light text-green-400 mb-4 flex items-center gap-2">
                            <AlertCircle size={20} />
                            System Status
                        </h2>
                        <div className="space-y-3">
                            <div className="flex items-start gap-3 text-sm text-green-200/80">
                                <div className="w-1.5 h-1.5 rounded-full bg-green-500 mt-1.5" />
                                <p>All systems operating normally</p>
                            </div>
                        </div>
                    </div>

                    {/* Quick Actions */}
                    <div className="bg-black/40 border border-white/10 rounded-xl p-6 flex-1">
                        <h2 className="text-xl font-light mb-4 flex items-center gap-2">
                            <Shield size={20} className="text-purple-400" />
                            Quick Actions
                        </h2>
                        <div className="grid grid-cols-2 gap-3">
                            <ActionButton label="New Case" />
                            <ActionButton label="Upload Evidence" />
                            <ActionButton label="Run Diagnostics" />
                            <ActionButton label="Deploy Swarm" />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

const StatCard = ({ icon, label, value, color }: { icon: React.ReactNode, label: string, value: string, color: string }) => (
    <div className="bg-black/40 border border-white/10 rounded-xl p-5 flex items-center gap-4 hover:border-white/20 transition-colors">
        <div className={`p-3 rounded-lg bg-white/5 ${color}`}>
            {icon}
        </div>
        <div>
            <p className="text-xs text-halo-muted uppercase tracking-wider">{label}</p>
            <p className={`text-2xl font-light ${color}`}>{value}</p>
        </div>
    </div>
);

const LogEntry = ({ agent, action, time }: { agent: string, action: string, time: string }) => (
    <div className="flex gap-3 text-sm p-3 rounded bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
        <span className="text-halo-muted font-mono text-xs pt-0.5">{time}</span>
        <div className="flex-1">
            <span className="text-halo-cyan font-medium mr-2">[{agent}]</span>
            <span className="text-gray-300">{action}</span>
        </div>
    </div>
);

const ActionButton = ({ label }: { label: string }) => (
    <button className="p-4 rounded-lg bg-white/5 border border-white/10 hover:bg-halo-cyan/10 hover:border-halo-cyan/50 hover:text-halo-cyan transition-all text-sm font-medium">
        {label}
    </button>
);
