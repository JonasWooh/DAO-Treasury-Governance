import { useMemo } from 'react';
import {
  useAccount,
  useChainId,
  useReadContract,
  useWaitForTransactionReceipt,
  useWriteContract,
} from 'wagmi';

import { contractAbis } from '../lib/abis';
import { formatAddress, formatTokenAmount } from '../lib/formatters';
import { governorStateLabel } from '../lib/governance';
import type { ProposalScenario } from '../types';

interface ProposalCardProps {
  governorAddress: string;
  proposal: ProposalScenario;
  expectedChainId: number;
}

export function ProposalCard({ governorAddress, proposal, expectedChainId }: ProposalCardProps) {
  const { isConnected } = useAccount();
  const chainId = useChainId();
  const networkMismatch = isConnected && chainId !== expectedChainId;

  const proposalId = useMemo(() => BigInt(proposal.proposalId), [proposal.proposalId]);
  const { data: proposalState, error: stateError } = useReadContract({
    address: governorAddress as `0x${string}`,
    abi: contractAbis.InnovationGovernor,
    functionName: 'state',
    args: [proposalId],
  });
  const { data: proposalVotes, error: votesError } = useReadContract({
    address: governorAddress as `0x${string}`,
    abi: contractAbis.InnovationGovernor,
    functionName: 'proposalVotes',
    args: [proposalId],
  });

  const votesTuple = proposalVotes as readonly [bigint, bigint, bigint] | undefined;

  const { data: voteHash, error: voteError, isPending: votePending, writeContract } =
    useWriteContract();
  const voteReceipt = useWaitForTransactionReceipt({ hash: voteHash });

  function handleVoteFor() {
    writeContract({
      address: governorAddress as `0x${string}`,
      abi: contractAbis.InnovationGovernor,
      functionName: 'castVote',
      args: [proposalId, 1],
    });
  }

  const againstVotes = votesTuple ? formatTokenAmount(votesTuple[0].toString()) : 'Unavailable';
  const forVotes = votesTuple ? formatTokenAmount(votesTuple[1].toString()) : 'Unavailable';
  const abstainVotes = votesTuple ? formatTokenAmount(votesTuple[2].toString()) : 'Unavailable';

  return (
    <article className="panel proposal-card">
      <div className="proposal-header">
        <div>
          <h3>{proposal.title}</h3>
          <p className="muted">{proposal.description}</p>
        </div>
        <span className="status">{governorStateLabel(proposalState ? Number(proposalState) : null)}</span>
      </div>
      {stateError ? <p className="inline-error">{stateError.message}</p> : null}
      {votesError ? <p className="inline-error">{votesError.message}</p> : null}
      {voteError ? <p className="inline-error">{voteError.message}</p> : null}
      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-label">For Votes</span>
          <strong className="metric-value">{forVotes}</strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Against Votes</span>
          <strong className="metric-value">{againstVotes}</strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Abstain Votes</span>
          <strong className="metric-value">{abstainVotes}</strong>
        </div>
      </div>
      <div className="stack">
        <div>
          <h4>Payload</h4>
          <ul className="mono-list">
            {proposal.targets.map((target, index) => (
              <li key={`${proposal.slug}-action-${index}`}>
                <span>Target {index + 1}: {formatAddress(target)}</span>
                <code>{proposal.calldatas[index]}</code>
              </li>
            ))}
          </ul>
        </div>
        <div className="button-row">
          <button
            type="button"
            className="action-button"
            onClick={handleVoteFor}
            disabled={!isConnected || networkMismatch || votePending}
          >
            {votePending ? 'Submitting Vote...' : 'Vote For'}
          </button>
          {networkMismatch ? (
            <span className="inline-error">Switch to Sepolia to cast votes.</span>
          ) : null}
        </div>
        {voteHash ? (
          <p className="muted">
            Vote tx: <code>{voteHash}</code> ({voteReceipt.isLoading ? 'pending' : 'confirmed'})
          </p>
        ) : null}
      </div>
    </article>
  );
}
