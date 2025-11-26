import React from 'react';
import { useHalo } from '../../context/HaloContext';
import { Filter, Layers, Play, Download, History } from 'lucide-react';

export function NodeDetails() {
    const { activeModule } = useHalo();

    return (
        <div className="w-80 border-l border-halo-border bg-halo-bg/95 backdrop-blur-sm p-6 flex flex-col gap-6 z-20">
            {/* Node Info Card */}
            <div className="halo-card bg-halo-card/50">
                <h3 className="text-halo-muted uppercase text-xs tracking-widest mb-4">
                    Selected Node
                </h3>
                <div className="text-xl font-light text-halo-cyan mb-1 capitalize">
                    {activeModule.replace('-', ' ')}
                </div>
                <div className="text-sm text-halo-muted mb-4">
                    Summary: A central node representing the current active module context.
                </div>

                <div className="space-y-3">
                    <div className="text-xs uppercase tracking-wider text-halo-muted font-semibold">Related Cases</div>
                    <div className="text-sm text-halo-text">Case No-201</div>
                    <div className="text-sm text-halo-text">Smith v. Smith</div>
                </div>

                <button className="mt-6 w-full halo-button text-xs">
                    View Details
                </button>
            </div>

            {/* Actions Panel */}
            <div className="halo-card bg-halo-card/50 flex-1">
                <h3 className="text-halo-muted uppercase text-xs tracking-widest mb-4">
                    Actions
                </h3>

                <div className="flex flex-col gap-2">
                    <ActionButton icon={Filter} label="Filter" />
                    <ActionButton icon={Layers} label="Clusters" />
                    <ActionButton icon={Play} label="Run Agents" />
                    <ActionButton icon={Download} label="Export" />
                    <ActionButton icon={History} label="History" />
                </div>
            </div>
        </div>
    );
}

function ActionButton({ icon: Icon, label }: { icon: React.ElementType, label: string }) {
    return (
        <button className="flex items-center gap-3 p-2 rounded hover:bg-halo-border/50 text-halo-muted hover:text-halo-cyan transition-colors text-sm group">
            <Icon className="w-4 h-4 group-hover:drop-shadow-[0_0_4px_rgba(0,240,255,0.5)]" />
            <span>{label}</span>
        </button>
    );
}
