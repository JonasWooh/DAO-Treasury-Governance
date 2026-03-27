import { Navigate, Route, Routes } from 'react-router-dom';

import { LoadingState } from './components/LoadingState';
import { RuntimeErrorPanel } from './components/RuntimeErrorPanel';
import { AppShell } from './components/AppShell';
import { useRuntimeBundle } from './hooks/useRuntimeBundle';
import { EvidencePage } from './pages/EvidencePage';
import { MilestoneClaimPage } from './pages/MilestoneClaimPage';
import { OverviewPage } from './pages/OverviewPage';
import { ProjectDetailPage } from './pages/ProjectDetailPage';
import { ProposalDetailPage } from './pages/ProposalDetailPage';
import { ProposalsPage } from './pages/ProposalsPage';
import { SubmitProposalPage } from './pages/SubmitProposalPage';
import { TreasuryPage } from './pages/TreasuryPage';
import type { RuntimeState } from './types';

interface AppProps {
  runtimeStateOverride?: RuntimeState;
}

export function App({ runtimeStateOverride }: AppProps) {
  const runtimeState = runtimeStateOverride ?? useRuntimeBundle();

  if (runtimeState.loading) {
    return (
      <LoadingState
        title="Preparing Workspace"
        message="Loading the current network bundle, governance data, and treasury context."
      />
    );
  }

  if (runtimeState.error || !runtimeState.bundle) {
    return (
      <RuntimeErrorPanel
        title="Runtime Bundle Error"
        error={runtimeState.error ?? 'The runtime bundle did not load successfully.'}
      />
    );
  }

  const { bundle } = runtimeState;

  return (
    <Routes>
      <Route element={<AppShell bundle={bundle} runtimeNote={bundle.config.note} />}>
        <Route index element={<OverviewPage bundle={bundle} />} />
        <Route path="proposals" element={<ProposalsPage bundle={bundle} />} />
        <Route path="proposals/:proposalId" element={<ProposalDetailPage bundle={bundle} />} />
        <Route path="projects/:projectId" element={<ProjectDetailPage bundle={bundle} />} />
        <Route path="submit" element={<SubmitProposalPage bundle={bundle} />} />
        <Route path="claims/:proposalId/:milestoneIndex" element={<MilestoneClaimPage bundle={bundle} />} />
        <Route path="treasury" element={<TreasuryPage bundle={bundle} />} />
        <Route path="evidence" element={<EvidencePage bundle={bundle} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
