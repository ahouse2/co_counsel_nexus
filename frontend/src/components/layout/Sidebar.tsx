import React from 'react';
import { useHalo, ModuleId } from '../../context/HaloContext';
import { useAuth } from '../../context/AuthContext';
import { CaseSelector } from './CaseSelector';
import {
    Network,
    MessageSquare,
    Clock,
    FileText,
    GraduationCap,
    Gavel,
    BrainCircuit,
    LogOut,
    User,
    Scale
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
    { id: 'jury', label: 'Jury Sentiment', icon: Scale },
];

export function Sidebar() {
    const { activeModule, setActiveModule } = useHalo();
    const { user, logout } = useAuth();

    return (
        <div className="w-20 lg:w-64 h-full border-r border-halo-border bg-halo-bg flex flex-col py-6 z-20 relative">
            {/* Case Selector at top */}
            <div className="px-2 mb-4">
                <CaseSelector />
            </div>

            {/* Module Navigation */}
            <div className="flex flex-col gap-2 px-2 flex-1">
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

            {/* User Info & Logout at bottom */}
            <div className="px-2 mt-auto border-t border-halo-border pt-4">
                {user && (
                    <div className="flex items-center gap-3 px-3 py-2 mb-2">
                        <div className="w-8 h-8 rounded-full bg-halo-cyan/20 flex items-center justify-center">
                            <User className="w-4 h-4 text-halo-cyan" />
                        </div>
                        <div className="hidden lg:block overflow-hidden">
                            <p className="text-xs text-halo-text truncate">{user.email}</p>
                            <p className="text-xs text-halo-muted capitalize">{user.role}</p>
                        </div>
                    </div>
                )}
                <button
                    onClick={logout}
                    className="flex items-center gap-4 p-3 rounded-lg w-full text-halo-muted hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    title="Logout"
                >
                    <LogOut className="w-5 h-5" />
                    <span className="hidden lg:block font-medium text-sm">Logout</span>
                </button>
            </div>
        </div>
    );
}

