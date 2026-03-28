import { Link, useParams } from 'react-router-dom';
import {
  useAccount,
  useChainId,
  useReadContract,
  useWaitForTransactionReceipt,
  useWriteContract,
} from 'wagmi';

import { RuntimeErrorPanel } from '../components/RuntimeErrorPanel';
import { contractAbis } from '../lib/abis';
import {
  normalizeMemberResult,
  normalizeMilestoneResult,
  normalizeProposalResult,
} from '../lib/contractResults';
import {
  formatAddress,
  formatCompactIdentifier,
  formatTokenAmount,
  toEtherscanAddressLink,
  toEtherscanTxLink,
} from '../lib/formatters';
import {
  fundingProposalStatusLabel,
  governorStateLabel,
  milestoneStateLabel,
  supportLabel,
} from '../lib/governance';
import { isPreviewRuntime } from '../lib/runtimeMode';
import type { FundingMilestone, RuntimeBundle } from '../types';

interface ProposalDetailPageProps {
  bundle: RuntimeBundle;
}

function GovernorStateValue({
  governorAddress,
  governorProposalId,
}: {
  governorAddress: string;
  governorProposalId: bigint;
}) {
  const { data, error } = useReadContract({
    address: governorAddress as `0x${string}`,
    abi: contractAbis.InnovationGovernor,
    functionName: 'state',
    args: [governorProposalId],
  });

  if (error) {
    return <span className="inline-error">{error.message}</span>;
  }

  const governorState = data as bigint | undefined;

  return <span>{governorStateLabel(governorState !== undefined ? Number(governorState) : null)}</span>;
}

function MilestoneRow({
  fundingRegistryAddress,
  governorAddress,
  proposalId,
  milestoneIndex,
  previewMode,
  previewMilestone,
}: {
  fundingRegistryAddress: string;
  governorAddress: string;
  proposalId: bigint;
  milestoneIndex: number;
  previewMode: boolean;
  previewMilestone?: FundingMilestone;
}) {
  const { data, error } = useReadContract({
    address: fundingRegistryAddress as `0x${string}`,
    abi: contractAbis.FundingRegistry,
    functionName: 'getMilestone',
    args: [proposalId, milestoneIndex],
    query: { enabled: !previewMode },
  });

  const milestone = normalizeMilestoneResult(data);
  const claimGovernorProposalId = previewMode
    ? BigInt(previewMilestone?.claimGovernorProposalId ?? '0')
    : milestone?.claimGovernorProposalId ?? 0n;

  return (
    <tr>
      <td>{milestoneIndex}</td>
      <td>{previewMode ? previewMilestone?.description ?? 'Preview' : milestone?.description ?? 'Loading...'}</td>
      <td>
        {previewMode
          ? previewMilestone
            ? `${formatTokenAmount(previewMilestone.amountWeth)} WETH`
            : 'Preview'
          : milestone
            ? `${formatTokenAmount(milestone.amountWeth)} WETH`
            : 'Loading...'}
      </td>
      <td>
        {previewMode
          ? previewMilestone?.state ?? 'Preview'
          : milestone
            ? milestoneStateLabel(Number(milestone.state))
            : 'Loading...'}
      </td>
      <td>
        {previewMode
          ? previewMilestone?.evidenceURI || 'Not submitted'
          : milestone?.evidenceURI
            ? milestone.evidenceURI
            : 'Not submitted'}
      </td>
      <td>
        {!previewMode && error ? (
          <span className="inline-error">{error.message}</span>
        ) : claimGovernorProposalId > 0n ? (
          previewMode ? (
            'Recorded'
          ) : (
            <GovernorStateValue governorAddress={governorAddress} governorProposalId={claimGovernorProposalId} />
          )
        ) : (
          'Unlinked'
        )}
      </td>
    </tr>
  );
}

export function ProposalDetailPage({ bundle }: ProposalDetailPageProps) {
  const previewMode = isPreviewRuntime(bundle);
  const params = useParams();
  const { address, isConnected } = useAccount();
  const chainId = useChainId();
  const snapshot = bundle.fundingState.proposals.find((entry) => entry.proposalId === params.proposalId);

  if (!snapshot) {
    return (
      <RuntimeErrorPanel
        title="Proposal Not Found"
        error={`No proposal with id ${params.proposalId ?? 'unknown'} exists in funding_state.sepolia.json.`}
      />
    );
  }

  const fundingRegistryAddress = bundle.config.contracts.FundingRegistry;
  const reputationRegistryAddress = bundle.config.contracts.ReputationRegistry;
  const hybridVotesAddress = bundle.config.contracts.HybridVotesAdapter;
  const governorAddress = bundle.config.contracts.InnovationGovernor;
  const etherscanBaseUrl = bundle.config.etherscanBaseUrl;
  const proposalId = BigInt(snapshot.proposalId);
  const networkMismatch = isConnected && chainId !== bundle.config.network.chainId;
  const snapshotMember = bundle.fundingState.members.find((member) => member.account === snapshot.proposer);
  const milestoneSnapshots = bundle.fundingState.milestones.filter(
    (milestone) => milestone.proposalId === snapshot.proposalId,
  );

  const { data: proposalData, error: proposalError } = useReadContract({
    address: fundingRegistryAddress as `0x${string}`,
    abi: contractAbis.FundingRegistry,
    functionName: 'getProposal',
    args: [proposalId],
    query: { enabled: !previewMode },
  });
  const liveProposal = normalizeProposalResult(proposalData);

  const { data: proposerMember, error: memberError } = useReadContract({
    address: reputationRegistryAddress as `0x${string}`,
    abi: contractAbis.ReputationRegistry,
    functionName: 'getMember',
    args: [snapshot.proposer],
    query: { enabled: !previewMode },
  });
  const memberTuple = normalizeMemberResult(proposerMember);

  const { data: hybridVotes, error: hybridError } = useReadContract({
    address: hybridVotesAddress as `0x${string}`,
    abi: contractAbis.HybridVotesAdapter,
    functionName: 'getVotes',
    args: [snapshot.proposer],
    query: { enabled: !previewMode },
  });
  const hybridVotesValue = hybridVotes as bigint | undefined;

  const governorProposalId = liveProposal?.governorProposalId ?? BigInt(snapshot.governorProposalId);
  const liveStatus = liveProposal ? fundingProposalStatusLabel(liveProposal.status) : snapshot.status;
  const { data: governorStateData, error: governorStateError } = useReadContract({
    address: governorAddress as `0x${string}`,
    abi: contractAbis.InnovationGovernor,
    functionName: 'state',
    args: [governorProposalId > 0n ? governorProposalId : 0n],
    query: { enabled: !previewMode && governorProposalId > 0n },
  });
  const governorStateValue = governorStateData as bigint | undefined;
  const { data: proposalVotesData, error: proposalVotesError } = useReadContract({
    address: governorAddress as `0x${string}`,
    abi: contractAbis.InnovationGovernor,
    functionName: 'proposalVotes',
    args: [governorProposalId > 0n ? governorProposalId : 0n],
    query: { enabled: !previewMode && governorProposalId > 0n },
  });
  const proposalVotes = proposalVotesData as readonly [bigint, bigint, bigint] | undefined;
  const { data: hasVotedData, error: hasVotedError } = useReadContract({
    address: governorAddress as `0x${string}`,
    abi: contractAbis.InnovationGovernor,
    functionName: 'hasVoted',
    args: governorProposalId > 0n && address ? [governorProposalId, address] : undefined,
    query: { enabled: !previewMode && governorProposalId > 0n && Boolean(address) },
  });
  const hasVoted = hasVotedData as boolean | undefined;
  const { data: voteTxHash, error: voteError, isPending: votePending, writeContract } = useWriteContract();
  const voteReceipt = useWaitForTransactionReceipt({ hash: voteTxHash });

  if (liveProposal && liveProposal.status > 0 && governorProposalId === 0n) {
    return (
      <RuntimeErrorPanel
        title="Missing Governor Link"
        error={`Proposal ${snapshot.proposalId} has progressed beyond Submitted but has no linked governorProposalId.`}
      />
    );
  }

  function handleCastVote(support: number) {
    if (governorProposalId === 0n) {
      return;
    }
    writeContract({
      address: governorAddress as `0x${string}`,
      abi: contractAbis.InnovationGovernor,
      functionName: 'castVote',
      args: [governorProposalId, support],
    });
  }

  const votingOpen = governorStateValue !== undefined && Number(governorStateValue) === 1;
  const voteButtonsDisabled =
    !isConnected || networkMismatch || !votingOpen || votePending || Boolean(hasVoted);

  return (
    <div className="page-grid single-column">
      <section className="panel panel-wide">
        <div className="proposal-header">
          <div>
            <h2>{liveProposal?.title ?? snapshot.title}</h2>
            <p className="muted">
              Funding request, governance progress, and release readiness for this project.
            </p>
          </div>
          <div className="panel-actions">
            <span className="status">{liveStatus}</span>
            <Link className="secondary-button" to="/proposals">
              Back To Pipeline
            </Link>
          </div>
        </div>
        <p className="subtle-kicker">Reference: {liveProposal?.metadataURI ?? snapshot.metadataURI}</p>
        {!previewMode && proposalError ? <p className="inline-error">{proposalError.message}</p> : null}
        {!previewMode && memberError ? <p className="inline-error">{memberError.message}</p> : null}
        {!previewMode && hybridError ? <p className="inline-error">{hybridError.message}</p> : null}
        {!previewMode && governorStateError ? <p className="inline-error">{governorStateError.message}</p> : null}
        {!previewMode && proposalVotesError ? <p className="inline-error">{proposalVotesError.message}</p> : null}
        {!previewMode && hasVotedError ? <p className="inline-error">{hasVotedError.message}</p> : null}
        {voteError ? <p className="inline-error">{voteError.message}</p> : null}
        <div className="metrics-grid">
          <div className="metric-card">
            <span className="metric-label">Recipient</span>
            <strong className="metric-value">{formatAddress(liveProposal?.recipient ?? snapshot.recipient)}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Requested Funding</span>
            <strong className="metric-value">
              {formatTokenAmount(liveProposal?.requestedFundingWeth ?? snapshot.requestedFundingWeth)} WETH
            </strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Governor Proposal</span>
            <strong
              className={governorProposalId > 0n ? 'metric-value metric-value-mono' : 'metric-value'}
              title={governorProposalId > 0n ? governorProposalId.toString() : undefined}
            >
              {governorProposalId > 0n ? formatCompactIdentifier(governorProposalId.toString(), 12, 10) : 'Unlinked'}
            </strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Governor State</span>
            <strong className="metric-value">
              {previewMode ? (
                governorProposalId > 0n ? 'Recorded' : 'Unlinked'
              ) : governorProposalId > 0n ? (
                <GovernorStateValue
                  governorAddress={governorAddress}
                  governorProposalId={governorProposalId}
                />
              ) : (
                'Unlinked'
              )}
            </strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Proposer Reputation</span>
            <strong className="metric-value">
              {previewMode ? snapshotMember?.currentReputation ?? 'Preview' : memberTuple ? memberTuple.currentReputation.toString() : 'Loading...'}
            </strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Proposer Hybrid Votes</span>
            <strong className="metric-value">
              {previewMode ? 'Preview' : hybridVotesValue ? formatTokenAmount(hybridVotesValue) : 'Loading...'}
            </strong>
          </div>
        </div>
        <div className="stack compact-stack">
          <div className="address-block">
            <span className="wallet-label">Proposer</span>
            <a
              className="quick-link quick-link-code"
              href={toEtherscanAddressLink(etherscanBaseUrl, liveProposal?.proposer ?? snapshot.proposer)}
              target="_blank"
              rel="noreferrer"
            >
              <code>{formatAddress(liveProposal?.proposer ?? snapshot.proposer)}</code>
            </a>
            <span className="muted">
              {previewMode
                ? `${snapshotMember?.isRegistered ? 'registered' : 'unregistered'} / ${snapshotMember?.isActive ? 'active' : 'inactive'}`
                : memberTuple
                  ? `${memberTuple.isRegistered ? 'registered' : 'unregistered'} / ${memberTuple.isActive ? 'active' : 'inactive'}`
                  : 'Loading membership...'}
            </span>
          </div>
          {(liveProposal?.projectId ?? snapshot.projectId) &&
          (liveProposal?.projectId ?? snapshot.projectId) !==
            '0x0000000000000000000000000000000000000000000000000000000000000000' ? (
            <div className="button-row">
              <Link className="secondary-button" to={`/projects/${liveProposal?.projectId ?? snapshot.projectId}`}>
                Open Project Detail
              </Link>
            </div>
          ) : null}
          <div className="quick-links">
            <a
              className="quick-link"
              href={toEtherscanAddressLink(etherscanBaseUrl, liveProposal?.recipient ?? snapshot.recipient)}
              target="_blank"
              rel="noreferrer"
            >
              View recipient wallet
            </a>
            <a
              className="quick-link"
              href={toEtherscanAddressLink(etherscanBaseUrl, fundingRegistryAddress)}
              target="_blank"
              rel="noreferrer"
            >
              View funding registry
            </a>
            <a
              className="quick-link"
              href={toEtherscanAddressLink(etherscanBaseUrl, governorAddress)}
              target="_blank"
              rel="noreferrer"
            >
              View governor contract
            </a>
          </div>
        </div>
      </section>

      <section className="panel panel-wide">
        <div className="panel-header">
          <div>
            <h3>Vote Window</h3>
            <p className="muted">
              Cast a decision from the connected wallet while the linked governor proposal is open.
            </p>
          </div>
        </div>
        <div className="metrics-grid">
          <div className="metric-card">
            <span className="metric-label">For Votes</span>
            <strong className="metric-value">
              {previewMode ? 'Preview' : proposalVotes ? formatTokenAmount(proposalVotes[1]) : 'Loading...'}
            </strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Against Votes</span>
            <strong className="metric-value">
              {previewMode ? 'Preview' : proposalVotes ? formatTokenAmount(proposalVotes[0]) : 'Loading...'}
            </strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Abstain Votes</span>
            <strong className="metric-value">
              {previewMode ? 'Preview' : proposalVotes ? formatTokenAmount(proposalVotes[2]) : 'Loading...'}
            </strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Your Vote Status</span>
            <strong className="metric-value">
              {previewMode ? 'Preview' : address ? (hasVoted ? 'Already voted' : 'Not yet voted') : 'Connect wallet'}
            </strong>
          </div>
        </div>
        <div className="button-row">
          {[0, 1, 2].map((support) => (
            <button
              key={support}
              type="button"
              className={support === 1 ? 'action-button' : 'secondary-button'}
              onClick={() => handleCastVote(support)}
              disabled={voteButtonsDisabled}
            >
              {votePending ? 'Submitting Vote...' : `Vote ${supportLabel(support)}`}
            </button>
          ))}
        </div>
        {networkMismatch ? (
          <p className="inline-error">Connected wallet is not on Sepolia. Switch networks before voting.</p>
        ) : null}
        {previewMode ? (
          <p className="muted">Preview mode shows the proposal record without loading live vote totals.</p>
        ) : !networkMismatch && isConnected && !votingOpen ? (
          <p className="muted">
            Voting becomes available only while the linked governor proposal is in the Active state.
          </p>
        ) : null}
        {voteTxHash ? (
          <p className="muted">
            Vote tx:{' '}
            <a href={toEtherscanTxLink(etherscanBaseUrl, voteTxHash)} target="_blank" rel="noreferrer">
              <code>{voteTxHash}</code>
            </a>{' '}
            ({voteReceipt.isLoading ? 'pending' : 'confirmed'})
          </p>
        ) : null}
      </section>

      <section className="panel panel-wide">
        <div className="panel-header">
          <div>
            <h3>Milestone Schedule</h3>
            <p className="muted">
              Follow each delivery checkpoint, attached evidence, and the linked release decision.
            </p>
          </div>
          <Link className="action-button" to={`/claims/${snapshot.proposalId}/0`}>
            Submit Delivery Proof
          </Link>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Index</th>
              <th>Description</th>
              <th>Amount</th>
              <th>State</th>
              <th>Evidence URI</th>
              <th>Claim Governor State</th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: liveProposal?.milestoneCount ?? snapshot.milestoneCount }, (_, milestoneIndex) => (
              <MilestoneRow
                key={`${snapshot.proposalId}-${milestoneIndex}`}
                fundingRegistryAddress={fundingRegistryAddress}
                governorAddress={governorAddress}
                proposalId={proposalId}
                milestoneIndex={milestoneIndex}
                previewMode={previewMode}
                previewMilestone={milestoneSnapshots.find((milestone) => milestone.milestoneIndex === milestoneIndex)}
              />
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
