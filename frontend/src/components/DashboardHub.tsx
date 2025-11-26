import { useHalo } from '../context/HaloContext';
import { HaloGraph } from './visualizations/HaloGraph';
import { SlideOutMenu } from './SlideOutMenu';
import { LegalTheoryModule } from './modules/LegalTheoryModule';
import { ForensicsModule } from './modules/ForensicsModule';
import { DocumentDraftingModule } from './modules/DocumentDraftingModule';
import { InCourtPresentationModule } from './modules/InCourtPresentationModule';
import { LegalResearchModule } from './modules/LegalResearchModule';
import { ServiceOfProcessModule } from './modules/ServiceOfProcessModule';
import { AgentConsoleModule } from './modules/AgentConsoleModule';
import { DocumentModule } from './modules/DocumentModule';
import { TimelineModule } from './modules/TimelineModule';
import { ContextEngineModule } from './modules/ContextEngineModule';
import { MockTrialArenaModule } from './modules/MockTrialArenaModule';
import { TrialUniversityModule } from './modules/TrialUniversityModule';
import { TrialBinderModule } from './modules/TrialBinderModule';
import { AnimatePresence, motion } from 'framer-motion';

export function DashboardHub() {
    const { activeModule } = useHalo();

    const renderModule = () => {
        switch (activeModule) {
            case 'graph':
                return null;
            case 'theory':
                return <LegalTheoryModule />;
            case 'forensics':
                return <ForensicsModule />;
            case 'drafting':
                return <DocumentDraftingModule />;
            case 'presentation':
                return <InCourtPresentationModule />;
            case 'research':
                return <LegalResearchModule />;
            case 'process':
                return <ServiceOfProcessModule />;
            case 'agents':
                return <AgentConsoleModule />;
            case 'documents':
                return <DocumentModule />;
            case 'timeline':
                return <TimelineModule />;
            case 'context':
                return <ContextEngineModule />;
            case 'arena':
                return <MockTrialArenaModule />;
            case 'university':
                return <TrialUniversityModule />;
            case 'binder':
                return <TrialBinderModule />;
            default:
                return null;
        }
    };

    return (
        <div className="relative w-screen h-screen bg-black overflow-hidden text-halo-text font-sans selection:bg-halo-cyan/30 selection:text-white">
            {/* Background Graph Layer */}
            <div className="absolute inset-0 z-0">
                <HaloGraph />
            </div>

            {/* Main Content Layer */}
            <div className="absolute inset-0 z-10 pointer-events-none flex">
                {/* Left Sidebar / Menu Area */}
                <div className="pointer-events-auto">
                    <SlideOutMenu />
                </div>

                {/* Center/Right Module Area */}
                <main className="flex-1 relative p-6 flex items-center justify-center pointer-events-none">
                    <AnimatePresence mode="wait">
                        {activeModule !== 'graph' && (
                            <motion.div
                                key={activeModule}
                                initial={{ opacity: 0, scale: 0.95, filter: 'blur(10px)' }}
                                animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
                                exit={{ opacity: 0, scale: 1.05, filter: 'blur(10px)' }}
                                transition={{ duration: 0.3, ease: "circOut" }}
                                className="w-full max-w-7xl h-[85vh] bg-black/80 backdrop-blur-xl border border-halo-border/50 rounded-2xl shadow-2xl overflow-hidden pointer-events-auto flex flex-col relative"
                            >
                                <div className="flex-1 overflow-hidden relative">
                                    {renderModule()}
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </main>
            </div>
        </div>
    );
}
