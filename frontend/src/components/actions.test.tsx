import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ProposalCard } from './ProposalCard';
import { WalletPanel } from './WalletPanel';
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
    fireEvent.click(screen.getByRole('button', { name: 'Self-Delegate CIF' }));
    expect(mockWriteContract).toHaveBeenCalledWith(expect.objectContaining({
      functionName: 'delegate',
      address: mockAddresses.token,
    }));
  });

  it('blocks writes on the wrong network', () => {
    wagmiState.chainId = 1;
    renderWithQuery(<WalletPanel tokenAddress={mockAddresses.token} expectedChainId={11155111} />);
    expect(screen.getByText(/not on Sepolia/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Self-Delegate CIF' })).toBeDisabled();
  });
});

describe('ProposalCard vote action', () => {
  beforeEach(() => {
    mockWriteContract.mockReset();
    wagmiState.chainId = 11155111;
    wagmiState.isConnected = true;
  });

  it('wires Vote For to castVote', () => {
    renderWithQuery(
      <ProposalCard
        governorAddress={mockAddresses.governor}
        proposal={mockRuntimeBundle.scenarios.proposals[0]}
        expectedChainId={11155111}
      />, 
    );
    fireEvent.click(screen.getByRole('button', { name: 'Vote For' }));
    expect(mockWriteContract).toHaveBeenCalledWith(expect.objectContaining({
      functionName: 'castVote',
      address: mockAddresses.governor,
    }));
  });
});
