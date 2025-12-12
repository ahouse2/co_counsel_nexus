import { useHalo } from '../context/HaloContext';
import { motion } from 'framer-motion';
import {
    LayoutGrid,
    Scale,
    Fingerprint,
    FileText,
    Presentation,
    Search,
    Cpu,
    FileStack,
    Clock,
    BrainCircuit,
    Swords,
    GraduationCap,
    FolderOpen,
    Tag
} from 'lucide-react';

const NAV_LINKS = [
    { id: 'graph', label: 'Graph Explorer', icon: LayoutGrid },
    { id: 'theory', label: 'Legal Theory', icon: Scale },
    { id: 'forensics', label: 'Forensics', icon: Fingerprint },
    { id: 'drafting', label: 'Drafting', icon: FileText },
    { id: 'presentation', label: 'Presentation', icon: Presentation },
    { id: 'research', label: 'Legal Research', icon: Search },
    { id: 'process', label: 'Service of Process', icon: FileText },
    { id: 'agents', label: 'Agent Console', icon: Cpu },
    { id: 'documents', label: 'Documents', icon: FolderOpen },
    { id: 'timeline', label: 'Timeline', icon: Clock },
    { id: 'context', label: 'Context Engine', icon: BrainCircuit },
    { id: 'arena', label: 'Mock Trial', icon: Swords },
    { id: 'university', label: 'Trial University', icon: GraduationCap },
    { id: 'binder', label: 'Evidence Binder', icon: FileStack },
    { id: 'classification', label: 'Classification', icon: Tag },
];

export function SlideOutMenu() {
    const { activeModule, setActiveModule, isMenuOpen, setIsMenuOpen } = useHalo();

    return (
        <motion.div
            initial={{ width: 60 }}
            animate={{ width: isMenuOpen ? 240 : 60 }}
            className="h-full bg-black/90 backdrop-blur-md border-r border-halo-border/50 flex flex-col z-50 relative"
            onMouseEnter={() => setIsMenuOpen(true)}
            onMouseLeave={() => setIsMenuOpen(false)}
        >
            <div className="p-4 flex items-center justify-center border-b border-halo-border/30 h-16">
                <div className="w-8 h-8 rounded-full bg-halo-cyan/20 flex items-center justify-center shadow-[0_0_10px_rgba(0,240,255,0.3)]">
                    <div className="w-4 h-4 rounded-full bg-halo-cyan animate-pulse" />
                </div>
                {isMenuOpen && (
                    <motion.span
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="ml-3 font-mono font-bold text-halo-cyan tracking-widest whitespace-nowrap"
                    >
                        NEURO-SAN
                    </motion.span>
                )}
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar py-4">
                {NAV_LINKS.map(link => (
                    <button
                        key={link.id}
                        onClick={() => setActiveModule(link.id as any)}
                        className={`w-full flex items-center px-4 py-3 transition-all relative group ${activeModule === link.id ? 'text-halo-cyan bg-halo-cyan/10' : 'text-halo-muted hover:text-white hover:bg-white/5'}`}
                    >
                        <link.icon size={20} className={`min-w-[20px] ${activeModule === link.id ? 'drop-shadow-[0_0_5px_rgba(0,240,255,0.5)]' : ''}`} />
                        {isMenuOpen && (
                            <motion.span
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                className="ml-3 text-sm font-medium whitespace-nowrap"
                            >
                                {link.label}
                            </motion.span>
                        )}
                        {activeModule === link.id && (
                            <div className="absolute left-0 top-0 bottom-0 w-1 bg-halo-cyan shadow-[0_0_10px_#00f0ff]" />
                        )}
                    </button>
                ))}
            </div>

            <div className="p-4 border-t border-halo-border/30">
                <div className="flex items-center justify-center text-xs text-halo-muted font-mono">
                    {isMenuOpen ? 'v2.0.0 PRODUCTION' : 'v2.0'}
                </div>
            </div>
        </motion.div>
    );
}
