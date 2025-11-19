import { useId } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import DashboardPage from '@/pages/DashboardPage';
import UploadEvidencePage from '@/pages/UploadEvidencePage';
import GraphExplorerPage from '@/pages/GraphExplorerPage';
import TrialUniversityPage from '@/pages/TrialUniversityPage';
import MockTrialArenaPage from '@/pages/MockTrialArenaPage';
import LiveCoCounselChatPage from '@/pages/LiveCoCounselChatPage';
import DesignSystemPage from '@/pages/DesignSystemPage';
import DevTeamPage from '@/pages/DevTeamPage';
import ForensicsReportPage from '@/pages/ForensicsReportPage';
import DocumentDraftingPage from '@/pages/DocumentDraftingPage';
import ServiceOfProcessPage from '@/pages/ServiceOfProcessPage';
import InCourtPresentationPage from '@/pages/InCourtPresentationPage';
import TimelinePage from '@/pages/TimelinePage';
import LegalTheoryPage from '@/pages/LegalTheoryPage';
import { CaseProvider } from './context/CaseContext';
import { HaloProvider } from './context/HaloContext';
import AgentConsolePage from './pages/AgentConsolePage';

export function App() {
  const id = useId(); // Keep useId if it's used elsewhere in Layout or children

  return (
    <Router>
      <CaseProvider>
        <HaloProvider>
          <Layout>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/login" element={<DashboardPage />} />
              <Route path="/agents-console" element={<AgentConsolePage />} />
              <Route path="/upload" element={<UploadEvidencePage />} />
              <Route path="/graph" element={<GraphExplorerPage />} />
              <Route path="/trial-university" element={<TrialUniversityPage />} />
              <Route path="/mock-trial" element={<MockTrialArenaPage />} />
              <Route path="/live-chat" element={<LiveCoCounselChatPage />} />
              <Route path="/design-system" element={<DesignSystemPage />} />
              <Route path="/dev-team" element={<DevTeamPage />} />
              <Route path="/forensics/:caseId/:docType/:docId" element={<ForensicsReportPage />} />
              <Route path="/drafting" element={<DocumentDraftingPage />} />
              <Route path="/service-of-process" element={<ServiceOfProcessPage />} />
              <Route path="/in-court-presentation" element={<InCourtPresentationPage />} />
              <Route path="/timeline" element={<TimelinePage />} />
              <Route path="/legal-theory" element={<LegalTheoryPage />} />
              <Route path="*" element={<DashboardPage />} />
            </Routes>
          </Layout>
        </HaloProvider>
      </CaseProvider>
    </Router>
  );
}
