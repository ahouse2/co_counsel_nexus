import { createContext, useContext, useState, ReactNode } from 'react';

export type ModuleId =
    | 'graph'
    | 'chat'
    | 'timeline'
    | 'documents'
    | 'university'
    | 'arena'
    | 'context'
    | 'theory'
    | 'forensics'
    | 'binder'
    | 'research'
    | 'drafting'
    | 'presentation'
    | 'process'
    | 'agents'
    | 'mootcourt'
    | 'evidencemap'
    | 'jurysentiment'
    | 'classification'
    | 'narrative'
    | 'devils_advocate';

export type SubmoduleId = string | null;

interface HaloContextType {
    activeModule: ModuleId;
    setActiveModule: (module: ModuleId) => void;
    activeSubmodule: SubmoduleId;
    setActiveSubmodule: (submodule: SubmoduleId) => void;
    isMenuOpen: boolean;
    setIsMenuOpen: (isOpen: boolean) => void;
    isSettingsOpen: boolean;
    setIsSettingsOpen: (isOpen: boolean) => void;
}

const HaloContext = createContext<HaloContextType | undefined>(undefined);

export function HaloProvider({ children }: { children: ReactNode }) {
    const [activeModule, setActiveModule] = useState<ModuleId>('graph');
    const [activeSubmodule, setActiveSubmodule] = useState<SubmoduleId>(null);
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);

    return (
        <HaloContext.Provider value={{
            activeModule,
            setActiveModule,
            activeSubmodule,
            setActiveSubmodule,
            isMenuOpen,
            setIsMenuOpen,
            isSettingsOpen,
            setIsSettingsOpen
        }}>
            {children}
        </HaloContext.Provider>
    );
}

export function useHalo() {
    const context = useContext(HaloContext);
    if (context === undefined) {
        throw new Error('useHalo must be used within a HaloProvider');
    }
    return context;
}
