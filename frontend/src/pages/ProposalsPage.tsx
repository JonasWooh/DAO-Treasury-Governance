import { ProposalCard } from '../components/ProposalCard';
import type { RuntimeBundle } from '../types';

interface ProposalsPageProps {
  bundle: RuntimeBundle;
}

export function ProposalsPage({ bundle }: ProposalsPageProps) {
  return (
    <div className="page-grid single-column">
      <section className="panel panel-wide">
        <h2>Governance Proposals</h2>
        <p className="muted">
          The demo interface exposes the three fixed Milestone 5 governance proposals. Payloads are
          rendered from the authoritative scenario manifest and proposal state is read live from the
          deployed Governor.
        </p>
      </section>
      {bundle.scenarios.proposals.map((proposal) => (
        <ProposalCard
          key={proposal.slug}
          governorAddress={bundle.config.contracts.InnovationGovernor}
          proposal={proposal}
          expectedChainId={bundle.config.network.chainId}
        />
      ))}
    </div>
  );
}
