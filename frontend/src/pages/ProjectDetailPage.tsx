import { Link, useParams } from 'react-router-dom';
import { useReadContract } from 'wagmi';

import { RuntimeErrorPanel } from '../components/RuntimeErrorPanel';
import { contractAbis } from '../lib/abis';
import {
  normalizeMemberResult,
  normalizeMilestoneResult,
  normalizeProjectResult,
  normalizeProposalResult,
} from '../lib/contractResults';
import { formatAddress, toEtherscanAddressLink, formatTokenAmount } from '../lib/formatters';
import { milestoneStateLabel, projectStatusLabel } from '../lib/governance';
import { isPreviewRuntime } from '../lib/runtimeMode';
import type { FundingMilestone, RuntimeBundle } from '../types';

interface ProjectDetailPageProps {
  bundle: RuntimeBundle;
}

function MilestoneProjectRow({
  fundingRegistryAddress,
  proposalId,
  milestoneIndex,
  previewMode,
  previewMilestone,
}: {
  fundingRegistryAddress: string;
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
        ) : previewMode ? (
          previewMilestone?.claimGovernorProposalId === '0' ? '0' : previewMilestone?.claimGovernorProposalId ?? '0'
        ) : (
          milestone?.claimGovernorProposalId.toString() ?? '0'
        )}
      </td>
    </tr>
  );
}

export function ProjectDetailPage({ bundle }: ProjectDetailPageProps) {
  const previewMode = isPreviewRuntime(bundle);
  const params = useParams();
  const snapshot = bundle.fundingState.projects.find((entry) => entry.projectId === params.projectId);

  if (!snapshot) {
    return (
      <RuntimeErrorPanel
        title="Project Not Found"
        error={`No project with id ${params.projectId ?? 'unknown'} exists in funding_state.sepolia.json.`}
      />
    );
  }

  const fundingRegistryAddress = bundle.config.contracts.FundingRegistry;
  const reputationRegistryAddress = bundle.config.contracts.ReputationRegistry;
  const etherscanBaseUrl = bundle.config.etherscanBaseUrl;
  const projectId = snapshot.projectId as `0x${string}`;
  const proposalSnapshot = bundle.fundingState.proposals.find((entry) => entry.proposalId === snapshot.sourceProposalId);
  const milestoneSnapshots = bundle.fundingState.milestones.filter(
    (milestone) => milestone.projectId === snapshot.projectId || milestone.proposalId === snapshot.sourceProposalId,
  );

  const { data: projectData, error: projectError } = useReadContract({
    address: fundingRegistryAddress as `0x${string}`,
    abi: contractAbis.FundingRegistry,
    functionName: 'getProject',
    args: [projectId],
    query: { enabled: !previewMode },
  });
  const project = normalizeProjectResult(projectData);

  const proposalId = project?.sourceProposalId ?? BigInt(snapshot.sourceProposalId);
  const { data: proposalData, error: proposalError } = useReadContract({
    address: fundingRegistryAddress as `0x${string}`,
    abi: contractAbis.FundingRegistry,
    functionName: 'getProposal',
    args: [proposalId],
    query: { enabled: !previewMode },
  });
  const proposal = normalizeProposalResult(proposalData);

  const proposerAddress = (proposal?.proposer ?? proposalSnapshot?.proposer) as `0x${string}` | undefined;
  const { data: proposerMemberData, error: proposerMemberError } = useReadContract({
    address: reputationRegistryAddress as `0x${string}`,
    abi: contractAbis.ReputationRegistry,
    functionName: 'getMember',
    args: proposerAddress ? [proposerAddress] : undefined,
    query: { enabled: !previewMode && Boolean(proposerAddress) },
  });
  const proposerMember = normalizeMemberResult(proposerMemberData);
  const snapshotMember = bundle.fundingState.members.find((member) => member.account === proposerAddress);

  return (
    <div className="page-grid single-column">
      <section className="panel panel-wide">
        <div className="panel-header">
          <div>
            <h2>Project Detail</h2>
            <p className="muted">
              Track the approved budget, release progress, and proposer standing for this funded
              initiative.
            </p>
          </div>
          <div className="panel-actions">
            <Link className="secondary-button" to="/proposals">
              Back To Pipeline
            </Link>
            <Link className="secondary-button" to={`/proposals/${proposalId.toString()}`}>
              Back To Proposal
            </Link>
          </div>
        </div>
        {!previewMode && projectError ? <p className="inline-error">{projectError.message}</p> : null}
        {!previewMode && proposalError ? <p className="inline-error">{proposalError.message}</p> : null}
        {!previewMode && proposerMemberError ? <p className="inline-error">{proposerMemberError.message}</p> : null}
        <div className="metrics-grid">
          <div className="metric-card">
            <span className="metric-label">Project ID</span>
            <strong className="metric-value">{formatAddress(project?.projectId ?? snapshot.projectId)}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Approved Budget</span>
            <strong className="metric-value">
              {formatTokenAmount(project?.approvedBudgetWeth ?? snapshot.approvedBudgetWeth)} WETH
            </strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Released</span>
            <strong className="metric-value">
              {formatTokenAmount(project?.releasedWeth ?? snapshot.releasedWeth)} WETH
            </strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Next Claimable Milestone</span>
            <strong className="metric-value">
              {(project?.nextClaimableMilestone ?? snapshot.nextClaimableMilestone).toString()}
            </strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Status</span>
            <strong className="metric-value">
              {project ? projectStatusLabel(Number(project.status)) : snapshot.status}
            </strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Recipient</span>
            <strong className="metric-value">{formatAddress(project?.recipient ?? snapshot.recipient)}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Proposer Reputation</span>
            <strong className="metric-value">
              {previewMode ? snapshotMember?.currentReputation ?? 'Preview' : proposerMember ? proposerMember.currentReputation.toString() : 'Loading...'}
            </strong>
          </div>
        </div>
        <div className="stack compact-stack">
          <div className="address-block">
            <span className="wallet-label">Proposal Title</span>
            <strong>{proposal?.title ?? proposalSnapshot?.title ?? 'Loading...'}</strong>
            <span className="muted">{proposal?.metadataURI ?? proposalSnapshot?.metadataURI ?? 'Loading metadata URI...'}</span>
          </div>
          <div className="quick-links">
            <a
              className="quick-link"
              href={toEtherscanAddressLink(etherscanBaseUrl, project?.recipient ?? snapshot.recipient)}
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
            {proposerAddress ? (
              <a
                className="quick-link"
                href={toEtherscanAddressLink(etherscanBaseUrl, proposerAddress)}
                target="_blank"
                rel="noreferrer"
              >
                View proposer wallet
              </a>
            ) : null}
          </div>
          <div className="button-row">
            <Link
              className="action-button"
              to={`/claims/${proposalId.toString()}/${(project?.nextClaimableMilestone ?? snapshot.nextClaimableMilestone).toString()}`}
            >
              Submit Delivery Proof
            </Link>
          </div>
        </div>
      </section>

      <section className="panel panel-wide">
        <h3>Release Ledger</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Index</th>
              <th>Description</th>
              <th>Amount</th>
              <th>State</th>
              <th>Evidence URI</th>
              <th>Claim Governor Proposal</th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: proposal?.milestoneCount ?? proposalSnapshot?.milestoneCount ?? 0 }, (_, milestoneIndex) => (
              <MilestoneProjectRow
                key={`${snapshot.projectId}-${milestoneIndex}`}
                fundingRegistryAddress={fundingRegistryAddress}
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
