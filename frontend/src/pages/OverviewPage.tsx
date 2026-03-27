import { useReadContract } from 'wagmi';

import { MetricCard } from '../components/MetricCard';
import { RuntimeErrorPanel } from '../components/RuntimeErrorPanel';
import { WalletPanel } from '../components/WalletPanel';
import { formatAddress, formatTokenAmount, formatUsd18 } from '../lib/formatters';
import { requireParticipantAddress } from '../lib/evidence';
import { contractAbis } from '../lib/abis';
import type { RuntimeBundle } from '../types';

interface OverviewPageProps {
  bundle: RuntimeBundle;
}

export function OverviewPage({ bundle }: OverviewPageProps) {
  let voterA: string;
  let voterB: string;
  let voterC: string;

  try {
    voterA = requireParticipantAddress(bundle.evidence, 'voterA');
    voterB = requireParticipantAddress(bundle.evidence, 'voterB');
    voterC = requireParticipantAddress(bundle.evidence, 'voterC');
  } catch (error) {
    return (
      <RuntimeErrorPanel
        title="Overview Manifest Error"
        error={error instanceof Error ? error.message : 'Unknown participant manifest error.'}
      />
    );
  }

  const treasuryAddress = bundle.config.contracts.InnovationTreasury;
  const tokenAddress = bundle.config.contracts.CampusInnovationFundToken;

  const { data: liquidWeth, error: liquidError } = useReadContract({
    address: treasuryAddress as `0x${string}`,
    abi: contractAbis.InnovationTreasury,
    functionName: 'liquidWethBalance',
  });
  const { data: totalManagedWeth, error: totalManagedError } = useReadContract({
    address: treasuryAddress as `0x${string}`,
    abi: contractAbis.InnovationTreasury,
    functionName: 'totalManagedWeth',
  });
  const { data: navUsd, error: navError } = useReadContract({
    address: treasuryAddress as `0x${string}`,
    abi: contractAbis.InnovationTreasury,
    functionName: 'navUsd',
  });
  const { data: totalSupply, error: supplyError } = useReadContract({
    address: tokenAddress as `0x${string}`,
    abi: contractAbis.CampusInnovationFundToken,
    functionName: 'totalSupply',
  });
  const { data: voterAVotes } = useReadContract({
    address: tokenAddress as `0x${string}`,
    abi: contractAbis.CampusInnovationFundToken,
    functionName: 'getVotes',
    args: [voterA],
  });
  const { data: voterBVotes } = useReadContract({
    address: tokenAddress as `0x${string}`,
    abi: contractAbis.CampusInnovationFundToken,
    functionName: 'getVotes',
    args: [voterB],
  });
  const { data: voterCVotes } = useReadContract({
    address: tokenAddress as `0x${string}`,
    abi: contractAbis.CampusInnovationFundToken,
    functionName: 'getVotes',
    args: [voterC],
  });

  return (
    <div className="page-grid">
      <section className="panel panel-wide">
        <div className="panel-header">
          <div>
            <h2>DAO Overview</h2>
            <p className="muted">
              This interface surfaces the fixed Sepolia demo path defined in the implementation
              plan: constrained treasury, timelocked governance, Chainlink NAV, and Aave idle-fund
              management.
            </p>
          </div>
        </div>
        {liquidError ? <p className="inline-error">{liquidError.message}</p> : null}
        {totalManagedError ? <p className="inline-error">{totalManagedError.message}</p> : null}
        {navError ? <p className="inline-error">{navError.message}</p> : null}
        {supplyError ? <p className="inline-error">{supplyError.message}</p> : null}
        <div className="metrics-grid">
          <MetricCard
            label="Treasury Liquid WETH"
            value={liquidWeth ? `${formatTokenAmount(liquidWeth.toString())} WETH` : 'Loading...'}
          />
          <MetricCard
            label="Treasury Total Managed"
            value={totalManagedWeth ? `${formatTokenAmount(totalManagedWeth.toString())} WETH` : 'Loading...'}
          />
          <MetricCard
            label="Treasury NAV"
            value={navUsd ? formatUsd18(navUsd.toString()) : 'Loading...'}
          />
          <MetricCard
            label="CIF Total Supply"
            value={totalSupply ? `${formatTokenAmount(totalSupply.toString())} CIF` : 'Loading...'}
          />
        </div>
      </section>

      <WalletPanel
        tokenAddress={tokenAddress}
        expectedChainId={bundle.config.network.chainId}
      />

      <section className="panel">
        <h2>Voting Members</h2>
        <div className="stack compact-stack">
          <div className="address-block">
            <span className="wallet-label">voterA</span>
            <code>{formatAddress(voterA)}</code>
            <span className="muted">{voterAVotes ? `${formatTokenAmount(voterAVotes.toString())} votes` : 'Loading votes...'}</span>
          </div>
          <div className="address-block">
            <span className="wallet-label">voterB</span>
            <code>{formatAddress(voterB)}</code>
            <span className="muted">{voterBVotes ? `${formatTokenAmount(voterBVotes.toString())} votes` : 'Loading votes...'}</span>
          </div>
          <div className="address-block">
            <span className="wallet-label">voterC</span>
            <code>{formatAddress(voterC)}</code>
            <span className="muted">{voterCVotes ? `${formatTokenAmount(voterCVotes.toString())} votes` : 'Loading votes...'}</span>
          </div>
        </div>
      </section>

      <section className="panel">
        <h2>Deployment Surface</h2>
        <ul className="mono-list compact-list">
          {Object.entries(bundle.deployments.contracts).map(([name, address]) => (
            <li key={name}>
              <span>{name}</span>
              <code>{address}</code>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
