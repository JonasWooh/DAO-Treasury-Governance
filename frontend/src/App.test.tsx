import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import { App } from './App';
import { mockRuntimeBundle } from './testFixtures';

const mockWriteContract = vi.fn();
const mockConnect = vi.fn();
const mockDisconnect = vi.fn();

const wagmiState = {
  address: mockRuntimeBundle.evidence.participants.voterA,
  isConnected: true,
  chainId: 11155111,
};

vi.mock('wagmi', () => ({
  useAccount: () => ({
    address: wagmiState.address,
    isConnected: wagmiState.isConnected,
    connector: { name: 'Injected' },
  }),
  useChainId: () => wagmiState.chainId,
  useConnect: () => ({
    connect: mockConnect,
    connectors: [{ id: 'injected', name: 'Injected' }],
    error: null,
    isPending: false,
  }),
  useDisconnect: () => ({ disconnect: mockDisconnect }),
  useWriteContract: () => ({
    data: undefined,
    error: null,
    isPending: false,
    writeContract: mockWriteContract,
  }),
  useWaitForTransactionReceipt: () => ({ isLoading: false }),
  useReadContract: ({ functionName }: { functionName: string }) => {
    const map: Record<string, unknown> = {
      liquidWethBalance: 2000000000000000000n,
      suppliedWethBalance: 3000000000000000000n,
      totalManagedWeth: 5000000000000000000n,
      navUsd: 10000000000000000000000n,
      totalSupply: 1000000000000000000000000n,
      getVotes: 200000000000000000000000n,
      state: 7n,
      proposalVotes: [0n, 600000000000000000000000n, 0n],
      riskPolicy: [3000n, 2000n, 3600n],
      latestEthUsd: [200000000000n, 1700000000n, 8],
      getProject: [mockRuntimeBundle.evidence.project?.recipient, 1000000000000000000n, 0n, 2, 0, true],
    };
    return { data: map[functionName], error: null };
  },
}));

function renderApp(initialEntries: string[]) {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <App runtimeStateOverride={{ loading: false, error: null, bundle: mockRuntimeBundle }} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('App routes', () => {
  beforeEach(() => {
    mockWriteContract.mockReset();
    mockConnect.mockReset();
    mockDisconnect.mockReset();
    wagmiState.isConnected = true;
    wagmiState.chainId = 11155111;
  });

  it('renders the Overview page', () => {
    renderApp(['/']);
    expect(screen.getByText('DAO Overview')).toBeInTheDocument();
    expect(screen.getByText('Wallet')).toBeInTheDocument();
  });

  it('renders the Proposals page', () => {
    renderApp(['/proposals']);
    expect(screen.getByText('Governance Proposals')).toBeInTheDocument();
    expect(screen.getByText('Proposal 1')).toBeInTheDocument();
  });

  it('renders the Treasury page', () => {
    renderApp(['/treasury']);
    expect(screen.getByRole('heading', { name: 'Treasury & NAV' })).toBeInTheDocument();
    expect(screen.getByText('Approved Project')).toBeInTheDocument();
  });

  it('renders the Evidence page', () => {
    renderApp(['/evidence']);
    expect(screen.getByText('Transaction Hash Table')).toBeInTheDocument();
    expect(screen.getByText('Screenshot Manifest')).toBeInTheDocument();
  });
});
