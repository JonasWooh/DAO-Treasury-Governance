import { useReadContract } from 'wagmi';

import { MetricCard } from '../components/MetricCard';
import { RuntimeErrorPanel } from '../components/RuntimeErrorPanel';
import { contractAbis } from '../lib/abis';
import { normalizeProjectResult } from '../lib/contractResults';
import {
  formatAddress,
  formatDateTime,
  formatTokenAmount,
  formatUsd18,
  toEtherscanAddressLink,
} from '../lib/formatters';
import { projectStatusLabel } from '../lib/governance';
import { isPreviewRuntime } from '../lib/runtimeMode';
import type { RuntimeBundle } from '../types';

interface TreasuryPageProps {
  bundle: RuntimeBundle;
}

export function TreasuryPage({ bundle }: TreasuryPageProps) {
  const previewMode = isPreviewRuntime(bundle);
  const treasuryAddress = bundle.config.contracts.InnovationTreasury;
  const oracleAddress = bundle.config.contracts.TreasuryOracle;
  const fundingRegistryAddress = bundle.config.contracts.FundingRegistry;
  const etherscanBaseUrl = bundle.config.etherscanBaseUrl;
  const projectSnapshot = bundle.fundingState.projects[0];

  if (!projectSnapshot) {
    return (
      <RuntimeErrorPanel
        title="Funding State Error"
        error="funding_state.sepolia.json does not contain any projects."
      />
    );
  }

  const { data: liquidWeth, error: liquidError } = useReadContract({
    address: treasuryAddress as `0x${string}`,
    abi: contractAbis.InnovationTreasury,
    functionName: 'liquidWethBalance',
    query: { enabled: !previewMode },
  });
  const { data: suppliedWeth, error: suppliedError } = useReadContract({
    address: treasuryAddress as `0x${string}`,
    abi: contractAbis.InnovationTreasury,
    functionName: 'suppliedWethBalance',
    query: { enabled: !previewMode },
  });
  const { data: totalManagedWeth, error: totalError } = useReadContract({
    address: treasuryAddress as `0x${string}`,
    abi: contractAbis.InnovationTreasury,
    functionName: 'totalManagedWeth',
    query: { enabled: !previewMode },
  });
  const { data: navUsd, error: navError } = useReadContract({
    address: treasuryAddress as `0x${string}`,
    abi: contractAbis.InnovationTreasury,
    functionName: 'navUsd',
    query: { enabled: !previewMode },
  });
  const { data: riskPolicy, error: riskError } = useReadContract({
    address: treasuryAddress as `0x${string}`,
    abi: contractAbis.InnovationTreasury,
    functionName: 'riskPolicy',
    query: { enabled: !previewMode },
  });
  const { data: latestEthUsd, error: oracleError } = useReadContract({
    address: oracleAddress as `0x${string}`,
    abi: contractAbis.TreasuryOracle,
    functionName: 'latestEthUsd',
    query: { enabled: !previewMode },
  });
  const { data: liveProject, error: projectError } = useReadContract({
    address: bundle.config.contracts.FundingRegistry as `0x${string}`,
    abi: contractAbis.FundingRegistry,
    functionName: 'getProject',
    args: [projectSnapshot.projectId as `0x${string}`],
    query: { enabled: !previewMode },
  });

  const riskPolicyTuple = riskPolicy as readonly [bigint, bigint, bigint] | undefined;
  const oracleTuple = latestEthUsd as readonly [bigint, bigint, number] | undefined;
  const projectTuple = normalizeProjectResult(liveProject);
  const liquidWethValue = liquidWeth as bigint | undefined;
  const suppliedWethValue = suppliedWeth as bigint | undefined;
  const totalManagedValue = totalManagedWeth as bigint | undefined;
  const navUsdValue = navUsd as bigint | undefined;

  return (
    <div className="page-grid">
      <section className="panel panel-wide">
        <h2>Treasury Dashboard</h2>
        <p className="muted">
          Monitor liquid reserves, deployed capital, market pricing, and the current project
          allocation from one view.
        </p>
        {!previewMode && liquidError ? <p className="inline-error">{liquidError.message}</p> : null}
        {!previewMode && suppliedError ? <p className="inline-error">{suppliedError.message}</p> : null}
        {!previewMode && totalError ? <p className="inline-error">{totalError.message}</p> : null}
        {!previewMode && navError ? <p className="inline-error">{navError.message}</p> : null}
        {!previewMode && riskError ? <p className="inline-error">{riskError.message}</p> : null}
        {!previewMode && oracleError ? <p className="inline-error">{oracleError.message}</p> : null}
        <div className="quick-links">
          <a
            className="quick-link"
            href={toEtherscanAddressLink(etherscanBaseUrl, treasuryAddress)}
            target="_blank"
            rel="noreferrer"
          >
            View treasury contract
          </a>
          <a
            className="quick-link"
            href={toEtherscanAddressLink(etherscanBaseUrl, oracleAddress)}
            target="_blank"
            rel="noreferrer"
          >
            View oracle contract
          </a>
        </div>
        <div className="metrics-grid">
          <MetricCard label="Liquid WETH" value={liquidWethValue ? `${formatTokenAmount(liquidWethValue)} WETH` : previewMode ? 'Preview' : 'Loading...'} />
          <MetricCard label="Aave-Supplied WETH" value={suppliedWethValue ? `${formatTokenAmount(suppliedWethValue)} WETH` : previewMode ? 'Preview' : 'Loading...'} />
          <MetricCard label="Total Managed WETH" value={totalManagedValue ? `${formatTokenAmount(totalManagedValue)} WETH` : previewMode ? 'Preview' : 'Loading...'} />
          <MetricCard label="Treasury NAV" value={navUsdValue ? formatUsd18(navUsdValue) : previewMode ? 'Preview' : 'Loading...'} />
          <MetricCard
            label="Chainlink ETH / USD"
            value={oracleTuple ? `$${formatTokenAmount(oracleTuple[0], oracleTuple[2], 2)}` : previewMode ? 'Preview' : 'Loading...'}
            helper={oracleTuple ? `Updated at ${formatDateTime(Number(oracleTuple[1]))}` : previewMode ? 'Available after live export' : undefined}
          />
          <MetricCard
            label="Risk Policy"
            value={riskPolicyTuple ? `${riskPolicyTuple[0]} / ${riskPolicyTuple[1]} / ${riskPolicyTuple[2]}` : previewMode ? 'Preview' : 'Loading...'}
            helper="reserve floor / grant cap / oracle freshness"
          />
        </div>
      </section>

      <section className="panel panel-wide">
        <h2>Active Project Allocation</h2>
        {!previewMode && projectError ? <p className="inline-error">{projectError.message}</p> : null}
        <div className="quick-links">
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
            href={toEtherscanAddressLink(etherscanBaseUrl, projectTuple?.recipient ?? projectSnapshot.recipient)}
            target="_blank"
            rel="noreferrer"
          >
            View project recipient
          </a>
        </div>
        <div className="project-grid">
          <div className="address-block">
            <span className="wallet-label">Project ID</span>
            <code>{projectSnapshot.projectId}</code>
          </div>
          <div className="address-block">
            <span className="wallet-label">Recipient</span>
            <a
              className="quick-link quick-link-code"
              href={toEtherscanAddressLink(etherscanBaseUrl, projectTuple?.recipient ?? projectSnapshot.recipient)}
              target="_blank"
              rel="noreferrer"
            >
              <code>{formatAddress(projectTuple?.recipient ?? projectSnapshot.recipient)}</code>
            </a>
          </div>
          <div className="address-block">
            <span className="wallet-label">Approved Budget</span>
            <span>{formatTokenAmount(projectTuple?.approvedBudgetWeth ?? projectSnapshot.approvedBudgetWeth)} WETH</span>
          </div>
          <div className="address-block">
            <span className="wallet-label">Released Amount</span>
            <span>{formatTokenAmount(projectTuple?.releasedWeth ?? projectSnapshot.releasedWeth)} WETH</span>
          </div>
          <div className="address-block">
            <span className="wallet-label">Next Claimable Milestone</span>
            <span>{(projectTuple?.nextClaimableMilestone ?? projectSnapshot.nextClaimableMilestone).toString()}</span>
          </div>
          <div className="address-block">
            <span className="wallet-label">Project Status</span>
            <span>{projectStatusLabel(Number(projectTuple?.status ?? 0))}</span>
          </div>
        </div>
      </section>
    </div>
  );
}
