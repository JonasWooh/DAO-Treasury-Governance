import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
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
  useReadContract: ({ functionName, args }: { functionName: string; args?: unknown[] }) => {
    const proposalId = args?.[0]?.toString();
    const milestoneIndex = Number(args?.[1] ?? 0);
    const map: Record<string, unknown> = {
      liquidWethBalance: 2400000000000000000n,
      suppliedWethBalance: 500000000000000000n,
      totalManagedWeth: 2900000000000000000n,
      navUsd: 5800000000000000000000n,
      totalSupply: 1000000000000000000000000n,
      getVotes: 200000000000000000000000n,
      totalActiveReputation: 316n,
      state: proposalId === '103' ? 7n : 5n,
      hasVoted: false,
      proposalVotes: [0n, 600000000000000000000000n, 0n],
      riskPolicy: [3000n, 2000n, 3600n],
      latestEthUsd: [200000000000n, 1700000000n, 8],
      getProject: [
        mockRuntimeBundle.fundingState.projects[0].projectId,
        1n,
        mockRuntimeBundle.fundingState.projects[0].recipient,
        200000000000000000n,
        100000000000000000n,
        1,
        0,
      ],
      getProposal: [
        1n,
        mockRuntimeBundle.fundingState.proposals[0].proposer,
        mockRuntimeBundle.fundingState.proposals[0].recipient,
        mockRuntimeBundle.fundingState.proposals[0].title,
        mockRuntimeBundle.fundingState.proposals[0].metadataURI,
        200000000000000000n,
        2,
        2,
        101n,
        mockRuntimeBundle.fundingState.proposals[0].projectId,
      ],
      getMilestone: milestoneIndex === 0
        ? [0, 'Install robotics hardware', 100000000000000000n, 'ipfs://milestone-0', 4, 103n]
        : [1, 'Commission the expanded lab', 100000000000000000n, '', 1, 0n],
      getMember: [true, true, 108n],
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
    expect(screen.getByText('Fund Overview')).toBeInTheDocument();
    expect(screen.getByText('Member Directory')).toBeInTheDocument();
  });

  it('renders the Proposals page', () => {
    renderApp(['/proposals']);
    expect(screen.getByText('Funding Pipeline')).toBeInTheDocument();
    expect(screen.getByText('Student robotics lab expansion')).toBeInTheDocument();
  });

  it('renders the Proposal Detail page', () => {
    renderApp(['/proposals/1']);
    expect(screen.getByText('Milestone Schedule')).toBeInTheDocument();
    expect(screen.getByText('Proposer Reputation')).toBeInTheDocument();
  });

  it('renders the Project Detail page', () => {
    renderApp([`/projects/${mockRuntimeBundle.fundingState.projects[0].projectId}`]);
    expect(screen.getByText('Release Ledger')).toBeInTheDocument();
    expect(screen.getByText('Project Detail')).toBeInTheDocument();
    expect(screen.getByText('Proposer Reputation')).toBeInTheDocument();
  });

  it('renders the Submit Proposal page', () => {
    renderApp(['/submit']);
    expect(screen.getByText('New Funding Request')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Submit Proposal' })).toBeInTheDocument();
  });

  it('renders the Milestone Claim page', () => {
    renderApp(['/claims/1/1']);
    expect(screen.getByText('Submit Milestone Evidence')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Submit Claim' })).toBeInTheDocument();
  });

  it('renders the Treasury page', () => {
    renderApp(['/treasury']);
    expect(screen.getByRole('heading', { name: 'Treasury Dashboard' })).toBeInTheDocument();
    expect(screen.getByText('Active Project Allocation')).toBeInTheDocument();
  });

  it('renders the Evidence page', () => {
    renderApp(['/evidence']);
    expect(screen.getByText('Execution Log')).toBeInTheDocument();
    expect(screen.getByText('Network Snapshot')).toBeInTheDocument();
    expect(screen.getByText('Member Standing')).toBeInTheDocument();
    expect(screen.getByText('108')).toBeInTheDocument();
  });

  it('falls back to the bundled sample runtime when the exported frontend config is still unconfigured', async () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/']}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await screen.findByText('Fund Overview')).toBeInTheDocument();
    expect(screen.getByText(/preview data is active/i)).toBeInTheDocument();
  });
});
