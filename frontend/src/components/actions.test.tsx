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
  delegatee: '0x0000000000000000000000000000000000000000',
  walletVotes: 0n,
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
      delegates: wagmiState.delegatee,
      getVotes: wagmiState.walletVotes,
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
    wagmiState.delegatee = '0x0000000000000000000000000000000000000000';
    wagmiState.walletVotes = 0n;
  });

  it('wires self-delegation to the token contract', () => {
    renderWithQuery(
      <WalletPanel
        tokenAddress={mockAddresses.token}
        expectedChainId={11155111}
        etherscanBaseUrl="https://sepolia.etherscan.io"
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Delegate Votes' }));
    expect(mockWriteContract).toHaveBeenCalledWith(expect.objectContaining({
      functionName: 'delegate',
      address: mockAddresses.token,
    }));
    expect(screen.getByRole('link', { name: 'View wallet on Etherscan' })).toHaveAttribute(
      'href',
      `https://sepolia.etherscan.io/address/${mockAddresses.voterA}`,
    );
  });

  it('blocks writes on the wrong network', () => {
    wagmiState.chainId = 1;
    renderWithQuery(
      <WalletPanel
        tokenAddress={mockAddresses.token}
        expectedChainId={11155111}
        etherscanBaseUrl="https://sepolia.etherscan.io"
      />,
    );
    expect(screen.getByText(/not on Sepolia/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delegate Votes' })).toBeDisabled();
  });

  it('shows when voting power is already active', () => {
    wagmiState.delegatee = mockAddresses.voterA;
    wagmiState.walletVotes = 200000000000000000000000n;
    renderWithQuery(
      <WalletPanel
        tokenAddress={mockAddresses.token}
        expectedChainId={11155111}
        etherscanBaseUrl="https://sepolia.etherscan.io"
      />,
    );
    expect(screen.getByRole('button', { name: 'Votes Active' })).toBeDisabled();
    expect(screen.getByText(/Voting power is active/i)).toBeInTheDocument();
  });
});

describe('Funding workflow write actions', () => {
  beforeEach(() => {
    mockWriteContract.mockReset();
    wagmiState.chainId = 11155111;
    wagmiState.isConnected = true;
    wagmiState.delegatee = '0x0000000000000000000000000000000000000000';
    wagmiState.walletVotes = 0n;
  });

  it('wires vote action from proposal detail', () => {
    wagmiState.walletVotes = 200000000000000000000000n;
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
    renderWithQuery(
      <MemoryRouter initialEntries={['/submit']}>
        <Routes>
          <Route path="/submit" element={<SubmitProposalPage bundle={mockRuntimeBundle} />} />
        </Routes>
      </MemoryRouter>,
    );
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
    fireEvent.click(screen.getByRole('button', { name: 'Submit Delivery Proof' }));
    expect(mockWriteContract).toHaveBeenCalledWith(expect.objectContaining({
      functionName: 'submitMilestoneClaim',
      address: mockAddresses.funding,
    }));
  });
});
