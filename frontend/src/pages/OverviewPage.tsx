import { useReadContract } from 'wagmi';

import { MetricCard } from '../components/MetricCard';
import { WalletPanel } from '../components/WalletPanel';
import { contractAbis } from '../lib/abis';
import { formatAddress, formatTokenAmount, formatUsd18 } from '../lib/formatters';
import { isPreviewRuntime } from '../lib/runtimeMode';
import type { Member, RuntimeBundle } from '../types';

interface OverviewPageProps {
  bundle: RuntimeBundle;
}

type MemberTuple = readonly [boolean, boolean, bigint];

function MemberLiveRow({
  member,
  reputationRegistryAddress,
  hybridVotesAddress,
  previewMode,
}: {
  member: Member;
  reputationRegistryAddress: string;
  hybridVotesAddress: string;
  previewMode: boolean;
}) {
  const { data: memberData } = useReadContract({
    address: reputationRegistryAddress as `0x${string}`,
    abi: contractAbis.ReputationRegistry,
    functionName: 'getMember',
    args: [member.account],
    query: { enabled: !previewMode },
  });
  const { data: hybridVotes } = useReadContract({
    address: hybridVotesAddress as `0x${string}`,
    abi: contractAbis.HybridVotesAdapter,
    functionName: 'getVotes',
    args: [member.account],
    query: { enabled: !previewMode },
  });

  const liveMember = memberData as MemberTuple | undefined;
  const liveHybridVotes = hybridVotes as bigint | undefined;

  return (
    <div className="address-block">
      <span className="wallet-label">{formatAddress(member.account)}</span>
      <code>{member.account}</code>
      <span className="muted">
        {previewMode
          ? `${member.isActive ? 'active' : 'inactive'} / reputation ${member.currentReputation} / hybrid snapshot`
          : liveMember
          ? `${liveMember[1] ? 'active' : 'inactive'} / reputation ${liveMember[2].toString()} / hybrid ${formatTokenAmount(liveHybridVotes ?? 0n)}`
          : 'Loading member state...'}
      </span>
    </div>
  );
}

export function OverviewPage({ bundle }: OverviewPageProps) {
  const previewMode = isPreviewRuntime(bundle);
  const treasuryAddress = bundle.config.contracts.InnovationTreasury;
  const tokenAddress = bundle.config.contracts.CampusInnovationFundToken;

  const { data: liquidWeth } = useReadContract({
    address: treasuryAddress as `0x${string}`,
    abi: contractAbis.InnovationTreasury,
    functionName: 'liquidWethBalance',
    query: { enabled: !previewMode },
  });
  const { data: totalManagedWeth } = useReadContract({
    address: treasuryAddress as `0x${string}`,
    abi: contractAbis.InnovationTreasury,
    functionName: 'totalManagedWeth',
    query: { enabled: !previewMode },
  });
  const { data: navUsd } = useReadContract({
    address: treasuryAddress as `0x${string}`,
    abi: contractAbis.InnovationTreasury,
    functionName: 'navUsd',
    query: { enabled: !previewMode },
  });
  const { data: totalSupply } = useReadContract({
    address: tokenAddress as `0x${string}`,
    abi: contractAbis.CampusInnovationFundToken,
    functionName: 'totalSupply',
    query: { enabled: !previewMode },
  });

  const liquidWethValue = liquidWeth as bigint | undefined;
  const totalManagedValue = totalManagedWeth as bigint | undefined;
  const navUsdValue = navUsd as bigint | undefined;
  const totalSupplyValue = totalSupply as bigint | undefined;

  const activeMembers = bundle.fundingState.members.filter((member) => member.isActive).length;

  return (
    <div className="page-grid">
      <section className="panel panel-wide">
        <div className="panel-header">
          <div>
            <h2>Fund Overview</h2>
            <p className="muted">
              Track treasury health, active governance participation, and the current funding
              pipeline from a single operating view.
            </p>
          </div>
        </div>
        <div className="metrics-grid">
          <MetricCard
            label="Liquid Treasury"
            value={liquidWethValue ? `${formatTokenAmount(liquidWethValue)} WETH` : previewMode ? 'Preview' : 'Loading...'}
          />
          <MetricCard
            label="Total Managed"
            value={totalManagedValue ? `${formatTokenAmount(totalManagedValue)} WETH` : previewMode ? 'Preview' : 'Loading...'}
          />
          <MetricCard label="Net Asset Value" value={navUsdValue ? formatUsd18(navUsdValue) : previewMode ? 'Preview' : 'Loading...'} />
          <MetricCard
            label="Token Supply"
            value={totalSupplyValue ? `${formatTokenAmount(totalSupplyValue)} CIF` : previewMode ? 'Preview' : 'Loading...'}
          />
          <MetricCard label="Funding Requests" value={bundle.fundingState.proposals.length.toString()} />
          <MetricCard label="Active Members" value={activeMembers.toString()} />
        </div>
      </section>

      <WalletPanel
        tokenAddress={tokenAddress}
        expectedChainId={bundle.config.network.chainId}
      />

      <section className="panel">
        <h2>Member Directory</h2>
        <div className="stack compact-stack">
          {bundle.fundingState.members.map((member) => (
            <MemberLiveRow
              key={member.account}
              member={member}
              reputationRegistryAddress={bundle.config.contracts.ReputationRegistry}
              hybridVotesAddress={bundle.config.contracts.HybridVotesAdapter}
              previewMode={previewMode}
            />
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>Contract Registry</h2>
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
