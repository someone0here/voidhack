import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { CaseProvider } from './context/CaseContext';
import { useCase } from './context/useCase';
import { AppShell } from './components/shell/AppShell';
import { IntakeView } from './views/IntakeView';
import { CorrelationView } from './views/CorrelationView';
import { RiskDeskView } from './views/RiskDeskView';
import { BriefView } from './views/BriefView';
import { DesignSystemShowcase } from './design-system/DesignSystemShowcase';
import { Button } from './design-system';

const RootIndexRedirect: React.FC = () => {
  const { cases, isLoading } = useCase();

  if (isLoading) {
    return <AppShell />;
  }

  const firstCase = cases[0];
  if (!firstCase) {
    return <AppShell />;
  }

  return <Navigate to={`/cases/${firstCase.id}/intake`} replace />;
};

const TabRedirect: React.FC<{ tab: string }> = ({ tab }) => {
  const { cases, activeCase, isLoading } = useCase();

  if (isLoading) {
    return <AppShell />;
  }

  const firstCase = cases[0];
  if (!firstCase) {
    return <Navigate to="/" replace />;
  }

  const targetId = activeCase ? activeCase.id : firstCase.id;
  return <Navigate to={`/cases/${targetId}/${tab}`} replace />;
};

const DesignSystemRoute: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="relative">
      <DesignSystemShowcase />

      {/* Floating quick switcher to return to Main App Shell */}
      <div className="fixed bottom-5 right-5 z-50">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            void navigate('/');
          }}
          className="border-pine/30 bg-cream/90 shadow-paper backdrop-blur-md"
        >
          ← Return to Main Console
        </Button>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <CaseProvider>
        <Routes>
          {/* Design System Laboratory Route */}
          <Route path="/design-system" element={<DesignSystemRoute />} />

          {/* Root redirect or Empty state */}
          <Route path="/" element={<RootIndexRedirect />} />

          {/* Primary Case Dossier Shell with 4 Section Tabs */}
          <Route path="/cases/:caseId" element={<AppShell />}>
            <Route index element={<Navigate to="intake" replace />} />
            <Route path="intake" element={<IntakeView />} />
            <Route path="correlation" element={<CorrelationView />} />
            <Route path="risk" element={<RiskDeskView />} />
            <Route path="brief" element={<BriefView />} />
          </Route>

          {/* Convenience shorthand routes */}
          <Route path="/intake" element={<TabRedirect tab="intake" />} />
          <Route path="/correlation" element={<TabRedirect tab="correlation" />} />
          <Route path="/risk" element={<TabRedirect tab="risk" />} />
          <Route path="/brief" element={<TabRedirect tab="brief" />} />

          {/* Catch-all fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </CaseProvider>
    </BrowserRouter>
  );
};

export default App;
