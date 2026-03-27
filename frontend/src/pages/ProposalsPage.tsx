import { Link } from 'react-router-dom';
import { useReadContract } from 'wagmi';

import { contractAbis } from '../lib/abis';
import { formatAddress, formatTokenAmount } from '../lib/formatters';
import { fundingProposalStatusLabel, governorStateLabel } from '../lib/governance';
import { isPreviewRuntime } from '../lib/runtimeMode';
import type { FundingProposal, RuntimeBundle } from '../types';

interface ProposalsPageProps {
  bundle: RuntimeBundle;
}

type ProposalTuple = readonly [
  bigint,
  `0x${string}`,
  `0x${string}`,
  string,
  string,
  bigint,
  number,
  number,
  bigint,
  `0x${string}`
];

function ProposalListItem({
  proposal,
  fundingRegistryAddress,
  governorAddress,
  previewMode,
}: {
  proposal: FundingProposal;
  fundingRegistryAddress: string;
  governorAddress: string;
  previewMode: boolean;
}) {
  const proposalId = BigInt(proposal.proposalId);
  const { data, error } = useReadContract({
    address: fundingRegistryAddress as `0x${string}`,
    abi: contractAbis.FundingRegistry,
    functionName: 'getProposal',
    args: [proposalId],
    query: { enabled: !previewMode },
  });

  const liveProposal = data as ProposalTuple | undefined;
  const liveStatus = liveProposal ? fundingProposalStatusLabel(Number(liveProposal[7])) : proposal.status;
  const governorProposalId = liveProposal?.[8] ?? BigInt(proposal.governorProposalId);

  const { data: governorState } = useReadContract({
    address: governorAddress as `0x${string}`,
    abi: contractAbis.InnovationGovernor,
    functionName: 'state',
    args: [governorProposalId > 0n ? governorProposalId : 0n],
    query: { enabled: !previewMode && governorProposalId > 0n },
  });
  const governorStateValue = governorState as bigint | undefined;
  const governorLabel = previewMode
    ? governorProposalId > 0n
      ? 'Recorded'
      : 'Unlinked'
    : governorProposalId > 0n
      ? governorStateLabel(governorStateValue !== undefined ? Number(governorStateValue) : null)
      : 'Unlinked';

  return (
    <article className="panel proposal-card">
      <div className="proposal-header">
        <div>
          <h3>{liveProposal?.[3] ?? proposal.title}</h3>
          <p className="muted">{liveProposal?.[4] ?? proposal.metadataURI}</p>
        </div>
        <span className="status">{liveStatus}</span>
      </div>
      {!previewMode && error ? <p className="inline-error">{error.message}</p> : null}
      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-label">Proposal ID</span>
          <strong className="metric-value">{proposal.proposalId}</strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Requested Funding</span>
          <strong className="metric-value">
            {formatTokenAmount(liveProposal?.[5] ?? proposal.requestedFundingWeth)} WETH
          </strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Recipient</span>
          <strong className="metric-value">{formatAddress(liveProposal?.[2] ?? proposal.recipient)}</strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Governor State</span>
          <strong className="metric-value">{governorLabel}</strong>
        </div>
      </div>
      <div className="button-row">
        <Link className="action-button" to={`/proposals/${proposal.proposalId}`}>
          View Proposal Detail
        </Link>
        {proposal.projectId !== '0x0000000000000000000000000000000000000000000000000000000000000000' ? (
          <Link className="secondary-button" to={`/projects/${proposal.projectId}`}>
            Open Project
          </Link>
        ) : null}
      </div>
    </article>
  );
}

export function ProposalsPage({ bundle }: ProposalsPageProps) {
  const previewMode = isPreviewRuntime(bundle);

  return (
    <div className="page-grid single-column">
      <section className="panel panel-wide">
        <h2>Funding Pipeline</h2>
        <p className="muted">
          Review each request, its live governance status, and the capital it is asking the
          treasury to commit.
        </p>
      </section>
      {bundle.fundingState.proposals.map((proposal) => (
        <ProposalListItem
          key={proposal.proposalId}
          proposal={proposal}
          fundingRegistryAddress={bundle.config.contracts.FundingRegistry}
          governorAddress={bundle.config.contracts.InnovationGovernor}
          previewMode={previewMode}
        />
      ))}
    </div>
  );
}
