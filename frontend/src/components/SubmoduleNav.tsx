import { useHalo } from '../context/HaloContext';
import { motion } from 'framer-motion';

interface SubmoduleNavProps {
    items: { id: string; label: string; icon?: React.ElementType }[];
}

export function SubmoduleNav({ items }: SubmoduleNavProps) {
    const { activeSubmodule, setActiveSubmodule } = useHalo();

    return (
        <div className="flex items-center gap-2 p-1 bg-halo-card/30 rounded-lg border border-halo-border/50 backdrop-blur-sm">
            {items.map((item) => {
                const isActive = activeSubmodule === item.id || (!activeSubmodule && item.id === 'default');

                return (
                    <button
                        key={item.id}
                        onClick={() => setActiveSubmodule(item.id === 'default' ? null : item.id as any)}
                        className={`relative px-4 py-2 rounded-md text-sm font-medium transition-all duration-300 flex items-center gap-2
                            ${isActive ? 'text-black' : 'text-halo-muted hover:text-halo-cyan hover:bg-white/5'}
                        `}
                    >
                        {isActive && (
                            <motion.div
                                layoutId="activeSubmodule"
                                className="absolute inset-0 bg-halo-cyan rounded-md"
                                transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                            />
                        )}
                        <span className="relative z-10 flex items-center gap-2">
                            {item.icon && <item.icon size={16} />}
                            {item.label}
                        </span>
                    </button>
                );
            })}
        </div>
    );
}
