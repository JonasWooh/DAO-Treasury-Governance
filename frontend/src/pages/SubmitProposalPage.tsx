import { useState } from 'react';
import { parseEther } from 'viem';
import { useAccount, useChainId, useWaitForTransactionReceipt, useWriteContract } from 'wagmi';

import { contractAbis } from '../lib/abis';
import type { RuntimeBundle } from '../types';

interface SubmitProposalPageProps {
  bundle: RuntimeBundle;
}

interface MilestoneDraft {
  description: string;
  amountWeth: string;
}

function buildInitialMilestones(): MilestoneDraft[] {
  return [
    { description: 'Milestone 0 scope', amountWeth: '0.10' },
    { description: 'Milestone 1 scope', amountWeth: '0.10' },
  ];
}

export function SubmitProposalPage({ bundle }: SubmitProposalPageProps) {
  const { isConnected } = useAccount();
  const chainId = useChainId();
  const networkMismatch = isConnected && chainId !== bundle.config.network.chainId;
  const [title, setTitle] = useState('Student robotics lab expansion');
  const [metadataURI, setMetadataURI] = useState('ipfs://proposal-metadata');
  const [recipient, setRecipient] = useState(bundle.fundingState.members[0]?.account ?? '');
  const [requestedFundingWeth, setRequestedFundingWeth] = useState('0.20');
  const [milestones, setMilestones] = useState<MilestoneDraft[]>(buildInitialMilestones);
  const [formError, setFormError] = useState<string | null>(null);
  const { data: txHash, error: writeError, isPending, writeContract } = useWriteContract();
  const receipt = useWaitForTransactionReceipt({ hash: txHash });

  function updateMilestone(index: number, field: keyof MilestoneDraft, value: string) {
    setMilestones((current) =>
      current.map((milestone, milestoneIndex) =>
        milestoneIndex === index ? { ...milestone, [field]: value } : milestone,
      ),
    );
  }

  function addMilestone() {
    setMilestones((current) => [...current, { description: '', amountWeth: '' }]);
  }

  function handleSubmit() {
    try {
      setFormError(null);
      const parsedRequestedFunding = parseEther(requestedFundingWeth);
      const milestoneDescriptions = milestones.map((milestone) => milestone.description.trim());
      const milestoneAmounts = milestones.map((milestone) => parseEther(milestone.amountWeth));

      if (milestoneDescriptions.some((description) => description.length === 0)) {
        throw new Error('Every milestone description must be non-empty.');
      }

      const milestoneAmountSum = milestoneAmounts.reduce((sum, value) => sum + value, 0n);
      if (milestoneAmountSum !== parsedRequestedFunding) {
        throw new Error('Requested funding must exactly equal the sum of milestone amounts.');
      }

      writeContract({
        address: bundle.config.contracts.FundingRegistry as `0x${string}`,
        abi: contractAbis.FundingRegistry,
        functionName: 'submitProposal',
        args: [title, metadataURI, recipient as `0x${string}`, parsedRequestedFunding, milestoneDescriptions, milestoneAmounts],
      });
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Unable to prepare proposal submission.');
    }
  }

  return (
    <div className="page-grid single-column">
      <section className="panel panel-wide">
        <h2>New Funding Request</h2>
        <p className="muted">
          Create a treasury request with milestone-based releases and send it to on-chain review.
        </p>
        {networkMismatch ? <p className="inline-error">Switch to Sepolia before submitting.</p> : null}
        {formError ? <p className="inline-error">{formError}</p> : null}
        {writeError ? <p className="inline-error">{writeError.message}</p> : null}
        <div className="stack">
          <label className="wallet-row">
            <span className="wallet-label">Title</span>
            <input value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label className="wallet-row">
            <span className="wallet-label">Metadata URI</span>
            <input value={metadataURI} onChange={(event) => setMetadataURI(event.target.value)} />
          </label>
          <label className="wallet-row">
            <span className="wallet-label">Recipient</span>
            <input value={recipient} onChange={(event) => setRecipient(event.target.value)} />
          </label>
          <label className="wallet-row">
            <span className="wallet-label">Requested Funding (WETH)</span>
            <input value={requestedFundingWeth} onChange={(event) => setRequestedFundingWeth(event.target.value)} />
          </label>
          <div className="stack">
            <h3>Delivery Plan</h3>
            {milestones.map((milestone, index) => (
              <div className="project-grid" key={`draft-${index}`}>
                <label className="wallet-row">
                  <span className="wallet-label">Description</span>
                  <input
                    value={milestone.description}
                    onChange={(event) => updateMilestone(index, 'description', event.target.value)}
                  />
                </label>
                <label className="wallet-row">
                  <span className="wallet-label">Amount (WETH)</span>
                  <input
                    value={milestone.amountWeth}
                    onChange={(event) => updateMilestone(index, 'amountWeth', event.target.value)}
                  />
                </label>
              </div>
            ))}
            <div className="button-row">
              <button type="button" className="secondary-button" onClick={addMilestone}>
                Add Milestone
              </button>
            </div>
          </div>
          <div className="button-row">
            <button
              type="button"
              className="action-button"
              onClick={handleSubmit}
              disabled={!isConnected || networkMismatch || isPending}
            >
              {isPending ? 'Submitting...' : 'Submit Proposal'}
            </button>
          </div>
          {txHash ? (
            <p className="muted">
              Proposal tx: <code>{txHash}</code> ({receipt.isLoading ? 'pending' : 'confirmed'})
            </p>
          ) : null}
        </div>
      </section>
    </div>
  );
}
