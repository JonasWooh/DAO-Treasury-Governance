import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { WalletPanel } from './WalletPanel';
import { ProposalDetailPage } from '../pages/ProposalDetailPage';
import { SubmitProposalPage } from '../pages/SubmitProposalPage';
import { MilestoneClaimPage } from '../pages/MilestoneClaimPage';
import { mockAddresses, mockRuntimeBundle } from '../testFixtures';

const mockWriteContract = vi.fn();
const mockConnect = vi.fn();
const mockDisconnect = vi.fn();

const wagmiState = {
  address: mockAddresses.voterA,
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
      state: 1n,
      proposalVotes: [0n, 600000000000000000000000n, 0n],
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
      getMilestone: [0, 'Install robotics hardware', 100000000000000000n, 'ipfs://milestone-0', 4, 103n],
      getMember: [true, true, 108n],
      getVotes: 200000000000000000000000n,
      hasVoted: false,
    };
    return { data: map[functionName], error: null };
  },
}));

function renderWithQuery(ui: React.ReactNode) {
  const queryClient = new QueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('WalletPanel actions', () => {
  beforeEach(() => {
    mockWriteContract.mockReset();
    mockConnect.mockReset();
    mockDisconnect.mockReset();
    wagmiState.isConnected = true;
    wagmiState.chainId = 11155111;
  });

  it('wires self-delegation to the token contract', () => {
    renderWithQuery(<WalletPanel tokenAddress={mockAddresses.token} expectedChainId={11155111} />);
    fireEvent.click(screen.getByRole('button', { name: 'Delegate Votes' }));
    expect(mockWriteContract).toHaveBeenCalledWith(expect.objectContaining({
      functionName: 'delegate',
      address: mockAddresses.token,
    }));
  });

  it('blocks writes on the wrong network', () => {
    wagmiState.chainId = 1;
    renderWithQuery(<WalletPanel tokenAddress={mockAddresses.token} expectedChainId={11155111} />);
    expect(screen.getByText(/not on Sepolia/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delegate Votes' })).toBeDisabled();
  });
});

describe('Funding workflow write actions', () => {
  beforeEach(() => {
    mockWriteContract.mockReset();
    wagmiState.chainId = 11155111;
    wagmiState.isConnected = true;
  });

  it('wires vote action from proposal detail', () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/proposals/1']}>
        <Routes>
          <Route path="/proposals/:proposalId" element={<ProposalDetailPage bundle={mockRuntimeBundle} />} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Vote For' }));
    expect(mockWriteContract).toHaveBeenCalledWith(expect.objectContaining({
      functionName: 'castVote',
      address: mockAddresses.governor,
      args: [101n, 1],
    }));
  });

  it('wires submitProposal to FundingRegistry', () => {
    renderWithQuery(<SubmitProposalPage bundle={mockRuntimeBundle} />);
    fireEvent.click(screen.getByRole('button', { name: 'Submit Proposal' }));
    expect(mockWriteContract).toHaveBeenCalledWith(expect.objectContaining({
      functionName: 'submitProposal',
      address: mockAddresses.funding,
    }));
  });

  it('wires submitMilestoneClaim to FundingRegistry', () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/claims/1/1']}>
        <Routes>
          <Route path="/claims/:proposalId/:milestoneIndex" element={<MilestoneClaimPage bundle={mockRuntimeBundle} />} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Submit Claim' }));
    expect(mockWriteContract).toHaveBeenCalledWith(expect.objectContaining({
      functionName: 'submitMilestoneClaim',
      address: mockAddresses.funding,
    }));
  });
});
