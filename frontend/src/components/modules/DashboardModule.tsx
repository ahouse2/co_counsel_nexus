import React, { useState, useEffect, useCallback } from 'react';
import { Activity, Server, Cpu, Database, Shield, Zap, AlertCircle, Play, RefreshCw, Loader2, X, Briefcase, Plus } from 'lucide-react';
import { endpoints } from '../../services/api';
import { useHalo } from '../../context/HaloContext';

interface ActivityEntry {
    timestamp: string;
    type: string;
    details: string;
}

interface PipelineStage {
    name: string;
    stage: number;
    status: 'idle' | 'running' | 'complete' | 'error';
}

interface PipelineStatus {
    is_running: boolean;
    current_stage: string | null;
    stages: PipelineStage[];
    processed_events: number;
    pending_events: number;
}

export const DashboardModule: React.FC = () => {
    const { caseId, setActiveModule, createCase } = useHalo();
    const [activities, setActivities] = useState<ActivityEntry[]>([]);
    const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null);
    const [loading, _setLoading] = useState(false);
    const [triggering, setTriggering] = useState(false);

    // Create Case Modal state
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newCaseName, setNewCaseName] = useState('');
    const [newCaseDescription, setNewCaseDescription] = useState('');
    const [isCreating, setIsCreating] = useState(false);

    // System Stats (real metrics would come from a metrics endpoint)
    const [stats, setStats] = useState({
        cpu: 12,
        memory: 45,
        apiLatency: 120,
        activeAgents: 8
    });

    const fetchActivity = useCallback(async () => {
        try {
            const [activityRes, statusRes] = await Promise.all([
                endpoints.orchestrator.activity(),
                endpoints.orchestrator.status()
            ]);
            setActivities(activityRes.data || []);
            setPipelineStatus(statusRes.data);
        } catch (error) {
            console.error('Failed to fetch orchestrator data:', error);
        }
    }, []);

    useEffect(() => {
        fetchActivity();
        // Poll every 5 seconds for live updates
        const interval = setInterval(fetchActivity, 5000);
        return () => clearInterval(interval);
    }, [fetchActivity]);

    // Simulated system stats (would be real in production)
    useEffect(() => {
        const interval = setInterval(() => {
            setStats(prev => ({
                cpu: Math.min(100, Math.max(5, prev.cpu + (Math.random() - 0.5) * 10)),
                memory: Math.min(100, Math.max(20, prev.memory + (Math.random() - 0.5) * 5)),
                apiLatency: Math.max(50, prev.apiLatency + (Math.random() - 0.5) * 20),
                activeAgents: prev.activeAgents
            }));
        }, 3000);
        return () => clearInterval(interval);
    }, []);

    const handleTriggerPipeline = async () => {
        setTriggering(true);
        try {
            await endpoints.orchestrator.trigger(caseId);
            await fetchActivity();
        } catch (error) {
            console.error('Failed to trigger pipeline:', error);
        } finally {
            setTriggering(false);
        }
    };

    const handleCreateCase = async () => {
        if (!newCaseName.trim()) return;
        setIsCreating(true);
        try {
            const newCase = await createCase(newCaseName.trim(), newCaseDescription.trim() || undefined);
            if (newCase) {
                setShowCreateModal(false);
                setNewCaseName('');
                setNewCaseDescription('');
                // Navigate to documents to start uploading evidence
                setActiveModule('documents');
            }
        } catch (error) {
            console.error('Failed to create case:', error);
        } finally {
            setIsCreating(false);
        }
    };

    const handleQuickAction = (action: string) => {
        switch (action) {
            case 'New Case':
                setShowCreateModal(true); // Open modal instead of redirect
                break;
            case 'Upload Evidence':
                setActiveModule('documents');
                break;
            case 'Run Diagnostics':
                fetchActivity();
                break;
            case 'Deploy Swarm':
                handleTriggerPipeline();
                break;
        }
    };

    const getStageColor = (status: string) => {
        switch (status) {
            case 'complete': return 'bg-green-500';
            case 'running': return 'bg-halo-cyan animate-pulse';
            case 'error': return 'bg-red-500';
            default: return 'bg-gray-600';
        }
    };

    return (
        <div className="w-full h-full p-8 overflow-y-auto">
            <header className="mb-8">
                <h1 className="text-4xl font-light text-white mb-2">Command Center</h1>
                <p className="text-halo-muted">
                    System Status: <span className={pipelineStatus?.is_running ? 'text-halo-cyan animate-pulse' : 'text-green-400'}>
                        {pipelineStatus?.is_running ? 'PIPELINE RUNNING' : 'OPERATIONAL'}
                    </span>
                </p>
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
                    label="Events Processed"
                    value={pipelineStatus?.processed_events?.toString() || '0'}
                    color="text-green-400"
                />
                <StatCard
                    icon={<Activity />}
                    label="Pending Events"
                    value={pipelineStatus?.pending_events?.toString() || '0'}
                    color={pipelineStatus?.pending_events ? 'text-yellow-400' : 'text-blue-400'}
                />
            </div>

            {/* Pipeline Status */}
            {pipelineStatus && (
                <div className="bg-black/40 border border-white/10 rounded-xl p-6 mb-8">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-xl font-light flex items-center gap-2">
                            <Server size={20} className="text-halo-cyan" />
                            Autonomous Pipeline Status
                        </h2>
                        <div className="flex gap-2">
                            <button
                                onClick={fetchActivity}
                                className="p-2 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
                                title="Refresh"
                            >
                                <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                            </button>
                            <button
                                onClick={handleTriggerPipeline}
                                disabled={triggering || pipelineStatus.is_running}
                                className="px-4 py-2 rounded-lg bg-halo-cyan/20 border border-halo-cyan/50 text-halo-cyan hover:bg-halo-cyan/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {triggering ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
                                Run Full Pipeline
                            </button>
                        </div>
                    </div>
                    <div className="flex gap-2 items-center">
                        {pipelineStatus.stages.map((stage, idx) => (
                            <React.Fragment key={stage.name}>
                                <div className="flex flex-col items-center gap-1">
                                    <div className={`w-8 h-8 rounded-full ${getStageColor(stage.status)} flex items-center justify-center text-xs font-bold text-white`}>
                                        {stage.stage}
                                    </div>
                                    <span className="text-xs text-halo-muted whitespace-nowrap">{stage.name}</span>
                                </div>
                                {idx < pipelineStatus.stages.length - 1 && (
                                    <div className={`h-0.5 flex-1 ${stage.status === 'complete' ? 'bg-green-500' : 'bg-gray-600'}`} />
                                )}
                            </React.Fragment>
                        ))}
                    </div>
                </div>
            )}

            {/* Main Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 h-[400px]">

                {/* Left: Live Swarm Activity Feed */}
                <div className="lg:col-span-2 bg-black/40 border border-white/10 rounded-xl p-6 flex flex-col">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-xl font-light flex items-center gap-2">
                            <Server size={20} className="text-halo-cyan" />
                            Swarm Activity
                        </h2>
                        <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full animate-pulse">LIVE</span>
                    </div>
                    <div className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
                        {activities.length === 0 ? (
                            <div className="text-center text-halo-muted py-8">
                                No recent activity. Trigger a pipeline to see events.
                            </div>
                        ) : (
                            activities.slice().reverse().map((activity, i) => (
                                <LogEntry
                                    key={i}
                                    agent={activity.type}
                                    action={activity.details}
                                    time={new Date(activity.timestamp).toLocaleTimeString()}
                                />
                            ))
                        )}
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
                                <p>Orchestrator: {pipelineStatus?.is_running ? 'Running' : 'Idle'}</p>
                            </div>
                            <div className="flex items-start gap-3 text-sm text-green-200/80">
                                <div className="w-1.5 h-1.5 rounded-full bg-green-500 mt-1.5" />
                                <p>Events processed: {pipelineStatus?.processed_events || 0}</p>
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
                            <ActionButton label="New Case" onClick={() => handleQuickAction('New Case')} />
                            <ActionButton label="Upload Evidence" onClick={() => handleQuickAction('Upload Evidence')} />
                            <ActionButton label="Run Diagnostics" onClick={() => handleQuickAction('Run Diagnostics')} />
                            <ActionButton label="Deploy Swarm" onClick={() => handleQuickAction('Deploy Swarm')} />
                        </div>
                    </div>
                </div>
            </div>

            {/* Create Case Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
                    <div className="bg-gray-900 border border-halo-cyan/30 rounded-xl p-6 w-full max-w-md shadow-2xl">
                        <div className="flex items-center justify-between mb-6">
                            <div className="flex items-center gap-3">
                                <div className="p-2 rounded-lg bg-halo-cyan/20">
                                    <Briefcase className="w-5 h-5 text-halo-cyan" />
                                </div>
                                <h2 className="text-xl font-medium text-white">Create New Case</h2>
                            </div>
                            <button
                                onClick={() => setShowCreateModal(false)}
                                className="text-gray-400 hover:text-white transition-colors"
                                title="Close modal"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm text-halo-muted mb-1">Case Name *</label>
                                <input
                                    type="text"
                                    value={newCaseName}
                                    onChange={(e) => setNewCaseName(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && handleCreateCase()}
                                    placeholder="e.g., Smith v. Jones Divorce"
                                    className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder:text-gray-500 focus:border-halo-cyan focus:outline-none"
                                    autoFocus
                                />
                            </div>
                            <div>
                                <label className="block text-sm text-halo-muted mb-1">Description (optional)</label>
                                <textarea
                                    value={newCaseDescription}
                                    onChange={(e) => setNewCaseDescription(e.target.value)}
                                    placeholder="Brief description of the case..."
                                    rows={3}
                                    className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder:text-gray-500 focus:border-halo-cyan focus:outline-none resize-none"
                                />
                            </div>
                        </div>

                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={() => setShowCreateModal(false)}
                                className="flex-1 px-4 py-3 bg-gray-800 text-gray-300 rounded-lg hover:bg-gray-700 transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleCreateCase}
                                disabled={!newCaseName.trim() || isCreating}
                                className="flex-1 px-4 py-3 bg-halo-cyan text-black font-medium rounded-lg hover:bg-halo-cyan/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                            >
                                {isCreating ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        Creating...
                                    </>
                                ) : (
                                    <>
                                        <Plus className="w-4 h-4" />
                                        Create Case
                                    </>
                                )}
                            </button>
                        </div>

                        <p className="text-xs text-halo-muted mt-4 text-center">
                            A unique case number will be automatically assigned (e.g., CC-2025-001)
                        </p>
                    </div>
                </div>
            )}
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

const ActionButton = ({ label, onClick }: { label: string, onClick?: () => void }) => (
    <button
        onClick={onClick}
        className="p-4 rounded-lg bg-white/5 border border-white/10 hover:bg-halo-cyan/10 hover:border-halo-cyan/50 hover:text-halo-cyan transition-all text-sm font-medium"
    >
        {label}
    </button>
);
