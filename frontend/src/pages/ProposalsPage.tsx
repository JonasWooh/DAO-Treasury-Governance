import { Link } from 'react-router-dom';
import { useReadContract } from 'wagmi';

import { contractAbis } from '../lib/abis';
import { normalizeProposalResult } from '../lib/contractResults';
import {
  formatAddress,
  formatCompactIdentifier,
  formatTokenAmount,
  toEtherscanAddressLink,
  toEtherscanTxLink,
} from '../lib/formatters';
import { fundingProposalStatusLabel, governorStateLabel } from '../lib/governance';
import { isPreviewRuntime } from '../lib/runtimeMode';
import type {
  DemoEvidenceProposalRecord,
  DemoEvidenceTransactionTree,
  FundingProposal,
  ProposalScenario,
  RuntimeBundle,
} from '../types';

interface ProposalsPageProps {
  bundle: RuntimeBundle;
}

function readTxHash(tree: DemoEvidenceTransactionTree | undefined, key: string): string | null {
  const value = tree?.[key];
  return typeof value === 'string' && value.length > 0 ? value : null;
}

function countTransactions(tree: DemoEvidenceTransactionTree | undefined): number {
  if (!tree) {
    return 0;
  }

  let count = 0;
  for (const value of Object.values(tree)) {
    if (typeof value === 'string' && value.length > 0) {
      count += 1;
      continue;
    }
    if (value && typeof value === 'object') {
      count += countTransactions(value as DemoEvidenceTransactionTree);
    }
  }
  return count;
}

function scenarioTrackLabel(slug: string): string {
  switch (slug) {
    case 'proposal1_approve_project':
      return 'Funding approval';
    case 'proposal2_deposit_idle_funds':
      return 'Treasury action';
    case 'proposal3_release_milestone':
      return 'Milestone release';
    default:
      return 'Governance step';
  }
}

function scenarioActionLabel(entry: ProposalScenario): string {
  if (entry.slug === 'proposal1_approve_project') {
    return 'Approve funding request';
  }
  if (entry.slug === 'proposal2_deposit_idle_funds') {
    return 'Deploy idle capital into Aave';
  }
  if (entry.slug === 'proposal3_release_milestone') {
    return 'Withdraw and release milestone 0';
  }
  return entry.description;
}

function scenarioOutcomeLabel(entry: ProposalScenario): string {
  const outcome = entry.expectedOutcome;
  if (entry.slug === 'proposal1_approve_project') {
    return `${String(outcome.fundingProposalStatus ?? 'Approved')} / ${String(outcome.projectStatus ?? 'Active')}`;
  }
  if (entry.slug === 'proposal2_deposit_idle_funds') {
    return `${formatTokenAmount(String(outcome.treasurySuppliedWeth ?? '0'))} WETH supplied`;
  }
  if (entry.slug === 'proposal3_release_milestone') {
    return `${String(outcome.milestone0State ?? 'Released')} / ${formatTokenAmount(String(outcome.projectReleasedWeth ?? '0'))} WETH released`;
  }
  return 'Recorded in scenario manifest';
}

function GovernanceTimelineItem({
  entry,
  bundle,
  previewMode,
}: {
  entry: ProposalScenario;
  bundle: RuntimeBundle;
  previewMode: boolean;
}) {
  const proposalId = BigInt(entry.proposalId);
  const evidenceRecord: DemoEvidenceProposalRecord | undefined = bundle.evidence.proposals[entry.slug];
  const hasOnChainLifecycle = previewMode || Boolean(evidenceRecord?.transactions?.propose);

  const { data: governorState, error: governorError } = useReadContract({
    address: bundle.config.contracts.InnovationGovernor as `0x${string}`,
    abi: contractAbis.InnovationGovernor,
    functionName: 'state',
    args: [proposalId],
    query: { enabled: !previewMode && hasOnChainLifecycle },
  });
  const { data: proposalVotes, error: votesError } = useReadContract({
    address: bundle.config.contracts.InnovationGovernor as `0x${string}`,
    abi: contractAbis.InnovationGovernor,
    functionName: 'proposalVotes',
    args: [proposalId],
    query: { enabled: !previewMode && hasOnChainLifecycle },
  });

  const governorStateValue = governorState as bigint | undefined;
  const voteTuple = proposalVotes as readonly [bigint, bigint, bigint] | undefined;
  const transactionCount = countTransactions(evidenceRecord?.transactions);
  const stateLabel = previewMode
    ? evidenceRecord?.finalState ?? 'Recorded'
    : hasOnChainLifecycle
      ? governorStateLabel(governorStateValue !== undefined ? Number(governorStateValue) : null)
      : 'Scheduled';
  const forVotes = previewMode
    ? evidenceRecord?.finalVotes?.forVotes ?? 'Recorded'
    : voteTuple
      ? formatTokenAmount(voteTuple[1])
      : 'Loading...';

  const relatedFundingProposalId =
    typeof entry.workflow?.fundingProposalId === 'string' ? entry.workflow.fundingProposalId : null;
  const projectId = typeof entry.workflow?.projectId === 'string' ? entry.workflow.projectId : bundle.scenarios.project?.projectId ?? null;
  const compactProposalId = formatCompactIdentifier(entry.proposalId, 12, 10);
  const proposeTxHash = readTxHash(evidenceRecord?.transactions, 'propose');
  const queueTxHash = readTxHash(evidenceRecord?.transactions, 'queue');
  const executeTxHash = readTxHash(evidenceRecord?.transactions, 'execute');

  return (
    <article className="panel proposal-card">
      <div className="proposal-header">
        <div>
          <span className="eyebrow eyebrow-inline">{scenarioTrackLabel(entry.slug)}</span>
          <h3>{entry.title}</h3>
          <p className="muted">{scenarioActionLabel(entry)}</p>
        </div>
        <span className="status">{stateLabel}</span>
      </div>
      {!previewMode && governorError ? <p className="inline-error">{governorError.message}</p> : null}
      {!previewMode && votesError ? <p className="inline-error">{votesError.message}</p> : null}
      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-label">Governor Proposal ID</span>
          <strong className="metric-value metric-value-mono" title={entry.proposalId}>
            {compactProposalId}
          </strong>
          <span className="metric-helper metric-helper-code">Full id available on hover</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">For Votes</span>
          <strong className="metric-value">{forVotes}</strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Recorded Actions</span>
          <strong className="metric-value">{transactionCount.toString()}</strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Expected Outcome</span>
          <strong className="metric-value timeline-outcome">{scenarioOutcomeLabel(entry)}</strong>
        </div>
      </div>
      <div className="quick-links">
        <a
          className="quick-link"
          href={toEtherscanAddressLink(bundle.config.etherscanBaseUrl, bundle.config.contracts.InnovationGovernor)}
          target="_blank"
          rel="noreferrer"
        >
          View governor contract
        </a>
        {proposeTxHash ? (
          <a
            className="quick-link"
            href={toEtherscanTxLink(bundle.config.etherscanBaseUrl, proposeTxHash)}
            target="_blank"
            rel="noreferrer"
          >
            View propose tx
          </a>
        ) : null}
        {queueTxHash ? (
          <a
            className="quick-link"
            href={toEtherscanTxLink(bundle.config.etherscanBaseUrl, queueTxHash)}
            target="_blank"
            rel="noreferrer"
          >
            View queue tx
          </a>
        ) : null}
        {executeTxHash ? (
          <a
            className="quick-link"
            href={toEtherscanTxLink(bundle.config.etherscanBaseUrl, executeTxHash)}
            target="_blank"
            rel="noreferrer"
          >
            View execute tx
          </a>
        ) : null}
      </div>
      <div className="button-row">
        {relatedFundingProposalId ? (
          <Link className="action-button" to={`/proposals/${relatedFundingProposalId}`}>
            Open Funding Request
          </Link>
        ) : (
          <Link className="action-button" to="/treasury">
            Open Treasury View
          </Link>
        )}
        {projectId ? (
          <Link className="secondary-button" to={`/projects/${projectId}`}>
            Open Project
          </Link>
        ) : null}
      </div>
    </article>
  );
}

function FundingRequestCard({
  proposal,
  fundingRegistryAddress,
  governorAddress,
  etherscanBaseUrl,
  previewMode,
}: {
  proposal: FundingProposal;
  fundingRegistryAddress: string;
  governorAddress: string;
  etherscanBaseUrl: string;
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

  const liveProposal = normalizeProposalResult(data);
  const liveStatus = liveProposal ? fundingProposalStatusLabel(liveProposal.status) : proposal.status;
  const governorProposalId = liveProposal?.governorProposalId ?? BigInt(proposal.governorProposalId);
  const proposerAddress = liveProposal?.proposer ?? proposal.proposer;
  const recipientAddress = liveProposal?.recipient ?? proposal.recipient;

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
          <span className="eyebrow eyebrow-inline">Funding request</span>
          <h3>{liveProposal?.title ?? proposal.title}</h3>
          <p className="muted">{liveProposal?.metadataURI ?? proposal.metadataURI}</p>
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
            {formatTokenAmount(liveProposal?.requestedFundingWeth ?? proposal.requestedFundingWeth)} WETH
          </strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Recipient</span>
          <strong className="metric-value">{formatAddress(recipientAddress)}</strong>
        </div>
        <div className="metric-card">
          <span className="metric-label">Governor State</span>
          <strong className="metric-value">{governorLabel}</strong>
        </div>
      </div>
      <div className="quick-links">
        <a
          className="quick-link"
          href={toEtherscanAddressLink(etherscanBaseUrl, proposerAddress)}
          target="_blank"
          rel="noreferrer"
        >
          View proposer wallet
        </a>
        <a
          className="quick-link"
          href={toEtherscanAddressLink(etherscanBaseUrl, recipientAddress)}
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
          Review the capital request itself, then follow the three governance steps that moved it
          from submission to treasury action and milestone release.
        </p>
      </section>
      {bundle.fundingState.proposals.map((proposal) => (
        <FundingRequestCard
          key={proposal.proposalId}
          proposal={proposal}
          fundingRegistryAddress={bundle.config.contracts.FundingRegistry}
          governorAddress={bundle.config.contracts.InnovationGovernor}
          etherscanBaseUrl={bundle.config.etherscanBaseUrl}
          previewMode={previewMode}
        />
      ))}

      <section className="panel panel-wide">
        <div className="panel-header">
          <div>
            <h2>Governance Timeline</h2>
            <p className="muted">
              This sequence shows the three Governor proposals that approved the project, deployed
              idle treasury capital, and released the first milestone payout.
            </p>
          </div>
          <span className="status">{bundle.scenarios.proposals.length} proposals tracked</span>
        </div>
      </section>
      {bundle.scenarios.proposals.map((entry) => (
        <GovernanceTimelineItem
          key={entry.slug}
          entry={entry}
          bundle={bundle}
          previewMode={previewMode}
        />
      ))}
    </div>
  );
}
