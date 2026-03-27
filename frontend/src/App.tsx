import { Navigate, Route, Routes } from 'react-router-dom';

import { LoadingState } from './components/LoadingState';
import { RuntimeErrorPanel } from './components/RuntimeErrorPanel';
import { AppShell } from './components/AppShell';
import { useRuntimeBundle } from './hooks/useRuntimeBundle';
import { EvidencePage } from './pages/EvidencePage';
import { OverviewPage } from './pages/OverviewPage';
import { ProposalsPage } from './pages/ProposalsPage';
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
        title="Loading Runtime Bundle"
        message="Fetching the generated config and authoritative Sepolia manifests."
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
      <Route element={<AppShell />}>
        <Route index element={<OverviewPage bundle={bundle} />} />
        <Route path="proposals" element={<ProposalsPage bundle={bundle} />} />
        <Route path="treasury" element={<TreasuryPage bundle={bundle} />} />
        <Route path="evidence" element={<EvidencePage bundle={bundle} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
