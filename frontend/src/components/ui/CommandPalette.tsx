import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Command, ArrowRight, LayoutDashboard, FileText, Gavel, Activity, Users, Database } from 'lucide-react';
import { useHalo } from '../../context/HaloContext';

interface CommandItem {
    id: string;
    label: string;
    icon: React.ReactNode;
    action: () => void;
    shortcut?: string;
}

export const CommandPalette: React.FC = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [query, setQuery] = useState('');
    const [selectedIndex, setSelectedIndex] = useState(0);
    const { setActiveModule } = useHalo();

    const commands: CommandItem[] = [
        { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} />, action: () => setActiveModule('dashboard') },
        { id: 'documents', label: 'Document Explorer', icon: <FileText size={18} />, action: () => setActiveModule('documents') },
        { id: 'graph', label: 'Knowledge Graph', icon: <Database size={18} />, action: () => setActiveModule('graph') },
        { id: 'timeline', label: 'Timeline', icon: <Activity size={18} />, action: () => setActiveModule('timeline') },
        { id: 'arena', label: 'Mock Trial Arena', icon: <Gavel size={18} />, action: () => setActiveModule('arena') },
        { id: 'agents', label: 'Agent Console', icon: <Users size={18} />, action: () => setActiveModule('agents') },
    ];

    const filteredCommands = commands.filter(cmd =>
        cmd.label.toLowerCase().includes(query.toLowerCase())
    );

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                setIsOpen(prev => !prev);
            }
            if (e.key === 'Escape') {
                setIsOpen(false);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    useEffect(() => {
        setSelectedIndex(0);
    }, [query]);

    const executeCommand = (cmd: CommandItem) => {
        cmd.action();
        setIsOpen(false);
        setQuery('');
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh] px-4">
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                        onClick={() => setIsOpen(false)}
                    />

                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: -20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: -20 }}
                        className="relative w-full max-w-2xl bg-black/90 border border-halo-border rounded-xl shadow-2xl overflow-hidden flex flex-col"
                    >
                        {/* Search Input */}
                        <div className="flex items-center px-4 py-4 border-b border-white/10">
                            <Search className="text-halo-muted mr-3" size={20} />
                            <input
                                autoFocus
                                type="text"
                                placeholder="Type a command or search..."
                                className="flex-1 bg-transparent border-none outline-none text-lg text-white placeholder-halo-muted"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'ArrowDown') {
                                        e.preventDefault();
                                        setSelectedIndex(prev => Math.min(prev + 1, filteredCommands.length - 1));
                                    } else if (e.key === 'ArrowUp') {
                                        e.preventDefault();
                                        setSelectedIndex(prev => Math.max(prev - 1, 0));
                                    } else if (e.key === 'Enter') {
                                        e.preventDefault();
                                        if (filteredCommands[selectedIndex]) {
                                            executeCommand(filteredCommands[selectedIndex]);
                                        }
                                    }
                                }}
                            />
                            <div className="flex items-center gap-2 text-xs text-halo-muted">
                                <span className="px-1.5 py-0.5 rounded bg-white/10">ESC</span> to close
                            </div>
                        </div>

                        {/* Results */}
                        <div className="max-h-[60vh] overflow-y-auto py-2">
                            {filteredCommands.length === 0 ? (
                                <div className="px-4 py-8 text-center text-halo-muted">
                                    No commands found.
                                </div>
                            ) : (
                                filteredCommands.map((cmd, index) => (
                                    <button
                                        key={cmd.id}
                                        onClick={() => executeCommand(cmd)}
                                        className={`w-full px-4 py-3 flex items-center justify-between transition-colors ${index === selectedIndex ? 'bg-halo-cyan/10 text-halo-cyan' : 'text-halo-text hover:bg-white/5'
                                            }`}
                                        onMouseEnter={() => setSelectedIndex(index)}
                                    >
                                        <div className="flex items-center gap-3">
                                            {cmd.icon}
                                            <span className="font-medium">{cmd.label}</span>
                                        </div>
                                        {index === selectedIndex && <ArrowRight size={16} />}
                                    </button>
                                ))
                            )}
                        </div>

                        {/* Footer */}
                        <div className="px-4 py-2 bg-white/5 border-t border-white/5 text-[10px] text-halo-muted flex justify-between">
                            <span>Op Veritas 2.0</span>
                            <div className="flex gap-2">
                                <span>Select <kbd className="font-sans">↵</kbd></span>
                                <span>Navigate <kbd className="font-sans">↑↓</kbd></span>
                            </div>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
};
