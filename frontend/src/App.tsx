import { HaloLayout } from './components/layout/HaloLayout';
import { HaloGraph } from './components/visualizations/HaloGraph';

import { ChatModule } from './components/modules/ChatModule';
import { DocumentModule } from './components/modules/DocumentModule';
import { TimelineModule } from './components/modules/TimelineModule';
import { TrialUniversityModule } from './components/modules/TrialUniversityModule';
import { MockTrialArenaModule } from './components/modules/MockTrialArenaModule';
import { ContextEngineModule } from './components/modules/ContextEngineModule';
import { LegalTheoryModule } from './components/modules/LegalTheoryModule';
import { ForensicsModule } from './components/modules/ForensicsModule';
import { TrialBinderModule } from './components/modules/TrialBinderModule';
import { LegalResearchModule } from './components/modules/LegalResearchModule';
import { useHalo } from './context/HaloContext';

function App() {
    const { activeModule } = useHalo();

    return (
        <HaloLayout>
            {/* The content inside the Halo Viewport */}
            <div className="w-full h-full relative flex items-center justify-center">

                {/* Dynamic Module Content */}
                <div className="w-full h-full p-8 overflow-auto custom-scrollbar">
                    {activeModule === 'graph' && <HaloGraph />}
                    {activeModule === 'chat' && <ChatModule />}
                    {activeModule === 'documents' && <DocumentModule />}
                    {activeModule === 'timeline' && <TimelineModule />}
                    {activeModule === 'university' && <TrialUniversityModule />}
                    {activeModule === 'arena' && <MockTrialArenaModule />}
                    {activeModule === 'context' && <ContextEngineModule />}
                    {activeModule === 'theory' && <LegalTheoryModule />}
                    {activeModule === 'forensics' && <ForensicsModule />}
                    {activeModule === 'binder' && <TrialBinderModule />}
                    {activeModule === 'research' && <LegalResearchModule />}
                </div>

                {/* Optional: NodeDetails could be a floating overlay or integrated into specific modules */}
                {/* <NodeDetails /> */}
            </div>
        </HaloLayout>
    );
}

export default App;
