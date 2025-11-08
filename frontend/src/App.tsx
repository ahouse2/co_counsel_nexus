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
import ForensicsReportPage from '@/pages/ForensicsReportPage'; // New import
import DocumentDraftingPage from '@/pages/DocumentDraftingPage';
import ServiceOfProcessPage from '@/pages/ServiceOfProcessPage';
import InCourtPresentationPage from '@/pages/InCourtPresentationPage';

export function App() {
  const id = useId(); // Keep useId if it's used elsewhere in Layout or children

  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/upload" element={<UploadEvidencePage />} />
          <Route path="/graph" element={<GraphExplorerPage />} />
          <Route path="/trial-university" element={<TrialUniversityPage />} />
          <Route path="/mock-trial" element={<MockTrialArenaPage />} />
          <Route path="/live-chat" element={<LiveCoCounselChatPage />} />
          <Route path="/design-system" element={<DesignSystemPage />} />
          <Route path="/dev-team" element={<DevTeamPage />} />
          {/* New route for Forensics Report */}
          <Route path="/forensics/:caseId/:docType/:docId" element={<ForensicsReportPage />} />
          <Route path="/drafting" element={<DocumentDraftingPage />} />
          <Route path="/service-of-process" element={<ServiceOfProcessPage />} />
          <Route path="/in-court-presentation" element={<InCourtPresentationPage />} />
          {/* Add a catch-all for 404 or redirect to dashboard */}
          <Route path="*" element={<DashboardPage />} />
        </Routes>
      </Layout>
    </Router>
  );
}
