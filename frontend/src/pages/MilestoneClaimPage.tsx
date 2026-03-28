import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useAccount, useChainId, useWaitForTransactionReceipt, useWriteContract } from 'wagmi';

import { RuntimeErrorPanel } from '../components/RuntimeErrorPanel';
import { contractAbis } from '../lib/abis';
import { toEtherscanAddressLink, toEtherscanTxLink } from '../lib/formatters';
import type { RuntimeBundle } from '../types';

interface MilestoneClaimPageProps {
  bundle: RuntimeBundle;
}

export function MilestoneClaimPage({ bundle }: MilestoneClaimPageProps) {
  const params = useParams();
  const proposalMatch = bundle.fundingState.proposals.find((entry) => entry.proposalId === params.proposalId);
  const milestoneIndex = Number(params.milestoneIndex ?? '');

  if (!proposalMatch || !Number.isInteger(milestoneIndex) || milestoneIndex < 0) {
    return (
      <RuntimeErrorPanel
        title="Claim Route Error"
        error="The milestone claim route is missing a valid proposalId or milestoneIndex."
      />
    );
  }

  const proposal = proposalMatch;

  const { isConnected } = useAccount();
  const chainId = useChainId();
  const networkMismatch = isConnected && chainId !== bundle.config.network.chainId;
  const etherscanBaseUrl = bundle.config.etherscanBaseUrl;
  const [evidenceURI, setEvidenceURI] = useState('ipfs://milestone-evidence');
  const { data: txHash, error, isPending, writeContract } = useWriteContract();
  const receipt = useWaitForTransactionReceipt({ hash: txHash });

  function handleSubmitClaim() {
    writeContract({
      address: bundle.config.contracts.FundingRegistry as `0x${string}`,
      abi: contractAbis.FundingRegistry,
      functionName: 'submitMilestoneClaim',
      args: [BigInt(proposal.proposalId), milestoneIndex, evidenceURI],
    });
  }

  return (
    <div className="page-grid single-column">
      <section className="panel panel-wide">
        <div className="panel-header">
          <div>
            <h2>Submit Delivery Proof</h2>
            <p className="muted">
              Request the next release for proposal {proposal.proposalId} by attaching the evidence
              URI for milestone {milestoneIndex}.
            </p>
          </div>
          <div className="panel-actions">
            <Link className="secondary-button" to="/proposals">
              Back To Pipeline
            </Link>
            <Link className="secondary-button" to={`/proposals/${proposal.proposalId}`}>
              Back To Proposal
            </Link>
          </div>
        </div>
        {networkMismatch ? <p className="inline-error">Switch to Sepolia before submitting.</p> : null}
        {error ? <p className="inline-error">{error.message}</p> : null}
        <div className="stack">
          <div className="quick-links">
            <a
              className="quick-link"
              href={toEtherscanAddressLink(etherscanBaseUrl, bundle.config.contracts.FundingRegistry)}
              target="_blank"
              rel="noreferrer"
            >
              View funding registry
            </a>
            <a
              className="quick-link"
              href={toEtherscanAddressLink(etherscanBaseUrl, proposal.recipient)}
              target="_blank"
              rel="noreferrer"
            >
              View proposal recipient
            </a>
          </div>
          <label className="wallet-row">
            <span className="wallet-label">Evidence URI</span>
            <input value={evidenceURI} onChange={(event) => setEvidenceURI(event.target.value)} />
          </label>
          <div className="button-row">
            <button
              type="button"
              className="action-button"
              onClick={handleSubmitClaim}
              disabled={!isConnected || networkMismatch || isPending || evidenceURI.trim().length === 0}
            >
              {isPending ? 'Submitting...' : 'Submit Delivery Proof'}
            </button>
          </div>
          {txHash ? (
            <p className="muted">
              Claim tx:{' '}
              <a href={toEtherscanTxLink(etherscanBaseUrl, txHash)} target="_blank" rel="noreferrer">
                <code>{txHash}</code>
              </a>{' '}
              ({receipt.isLoading ? 'pending' : 'confirmed'})
            </p>
          ) : null}
        </div>
      </section>
    </div>
  );
}
