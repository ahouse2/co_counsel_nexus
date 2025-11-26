import React from 'react';
import { useHalo, ModuleId } from '../../context/HaloContext';
import {
    Network,
    MessageSquare,
    Clock,
    FileText,
    GraduationCap,
    Gavel,
    BrainCircuit
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

const MENU_ITEMS: { id: ModuleId; label: string; icon: React.ElementType }[] = [
    { id: 'graph', label: 'Graph Explorer', icon: Network },
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'timeline', label: 'Timeline', icon: Clock },
    { id: 'documents', label: 'Document Viewer', icon: FileText },
    { id: 'university', label: 'Trial University', icon: GraduationCap },
    { id: 'arena', label: 'Mock Trial Arena', icon: Gavel },
    { id: 'context', label: 'Context Engine', icon: BrainCircuit },
];

export function Sidebar() {
    const { activeModule, setActiveModule } = useHalo();

    return (
        <div className="w-20 lg:w-64 h-full border-r border-halo-border bg-halo-bg flex flex-col py-6 z-20 relative">
            <div className="flex flex-col gap-2 px-2">
                {MENU_ITEMS.map((item) => {
                    const isActive = activeModule === item.id;
                    return (
                        <button
                            key={item.id}
                            onClick={() => setActiveModule(item.id)}
                            className={clsx(
                                "flex items-center gap-4 p-3 rounded-lg transition-all duration-300 group relative overflow-hidden",
                                isActive ? "text-halo-cyan" : "text-halo-muted hover:text-halo-text"
                            )}
                        >
                            {isActive && (
                                <motion.div
                                    layoutId="active-indicator"
                                    className="absolute inset-0 bg-halo-cyan-dim border-l-2 border-halo-cyan"
                                    initial={false}
                                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                                />
                            )}

                            <div className="relative z-10 flex items-center gap-4">
                                <item.icon className={clsx("w-6 h-6", isActive && "drop-shadow-[0_0_8px_rgba(0,240,255,0.5)]")} />
                                <span className="hidden lg:block font-medium tracking-wide text-sm uppercase">
                                    {item.label}
                                </span>
                            </div>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}
