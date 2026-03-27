import { useReadContract } from 'wagmi';

import { MetricCard } from '../components/MetricCard';
import { RuntimeErrorPanel } from '../components/RuntimeErrorPanel';
import { contractAbis } from '../lib/abis';
import { requireProjectDefinition } from '../lib/evidence';
import { formatAddress, formatTokenAmount, formatUsd18 } from '../lib/formatters';
import type { RuntimeBundle } from '../types';

interface TreasuryPageProps {
  bundle: RuntimeBundle;
}

export function TreasuryPage({ bundle }: TreasuryPageProps) {
  let project;
  try {
    project = requireProjectDefinition(bundle.scenarios);
  } catch (error) {
    return (
      <RuntimeErrorPanel
        title="Treasury Manifest Error"
        error={error instanceof Error ? error.message : 'Unknown treasury manifest error.'}
      />
    );
  }

  const treasuryAddress = bundle.config.contracts.InnovationTreasury;
  const oracleAddress = bundle.config.contracts.TreasuryOracle;

  const { data: liquidWeth, error: liquidError } = useReadContract({
    address: treasuryAddress as `0x${string}`,
    abi: contractAbis.InnovationTreasury,
    functionName: 'liquidWethBalance',
  });
  const { data: suppliedWeth, error: suppliedError } = useReadContract({
    address: treasuryAddress as `0x${string}`,
    abi: contractAbis.InnovationTreasury,
    functionName: 'suppliedWethBalance',
  });
  const { data: totalManagedWeth, error: totalError } = useReadContract({
    address: treasuryAddress as `0x${string}`,
    abi: contractAbis.InnovationTreasury,
    functionName: 'totalManagedWeth',
  });
  const { data: navUsd, error: navError } = useReadContract({
    address: treasuryAddress as `0x${string}`,
    abi: contractAbis.InnovationTreasury,
    functionName: 'navUsd',
  });
  const { data: riskPolicy, error: riskError } = useReadContract({
    address: treasuryAddress as `0x${string}`,
    abi: contractAbis.InnovationTreasury,
    functionName: 'riskPolicy',
  });
  const { data: latestEthUsd, error: oracleError } = useReadContract({
    address: oracleAddress as `0x${string}`,
    abi: contractAbis.TreasuryOracle,
    functionName: 'latestEthUsd',
  });
  const { data: projectState, error: projectError } = useReadContract({
    address: treasuryAddress as `0x${string}`,
    abi: contractAbis.InnovationTreasury,
    functionName: 'getProject',
    args: [project.projectId as `0x${string}`],
  });

  const oracleTuple = latestEthUsd as readonly [bigint, bigint, number] | undefined;
  const riskPolicyTuple = riskPolicy as readonly [bigint, bigint, bigint] | undefined;
  const projectTuple = projectState as readonly [string, bigint, bigint, number, number, boolean] | undefined;

  const normalizedPrice = oracleTuple ? oracleTuple[0].toString() : null;
  const oracleDecimals = oracleTuple ? Number(oracleTuple[2]) : null;

  return (
    <div className="page-grid">
      <section className="panel panel-wide">
        <h2>Treasury & NAV</h2>
        <p className="muted">
          These reads come directly from the deployed Treasury and Oracle wrappers. No off-chain
          treasury math is substituted at runtime.
        </p>
        {liquidError ? <p className="inline-error">{liquidError.message}</p> : null}
        {suppliedError ? <p className="inline-error">{suppliedError.message}</p> : null}
        {totalError ? <p className="inline-error">{totalError.message}</p> : null}
        {navError ? <p className="inline-error">{navError.message}</p> : null}
        {riskError ? <p className="inline-error">{riskError.message}</p> : null}
        {oracleError ? <p className="inline-error">{oracleError.message}</p> : null}
        <div className="metrics-grid">
          <MetricCard label="Liquid WETH" value={liquidWeth ? `${formatTokenAmount(liquidWeth.toString())} WETH` : 'Loading...'} />
          <MetricCard label="Aave-Supplied WETH" value={suppliedWeth ? `${formatTokenAmount(suppliedWeth.toString())} WETH` : 'Loading...'} />
          <MetricCard label="Total Managed WETH" value={totalManagedWeth ? `${formatTokenAmount(totalManagedWeth.toString())} WETH` : 'Loading...'} />
          <MetricCard label="Treasury NAV" value={navUsd ? formatUsd18(navUsd.toString()) : 'Loading...'} />
          <MetricCard
            label="Chainlink ETH / USD"
            value={normalizedPrice && oracleDecimals !== null ? `$${formatTokenAmount(normalizedPrice, oracleDecimals, 2)}` : 'Loading...'}
            helper={oracleTuple ? `Updated at unix ${oracleTuple[1].toString()}` : undefined}
          />
          <MetricCard
            label="Risk Policy"
            value={riskPolicyTuple ? `${riskPolicyTuple[0].toString()} / ${riskPolicyTuple[1].toString()} / ${riskPolicyTuple[2].toString()}` : 'Loading...'}
            helper="min reserve bps / max grant bps / stale threshold"
          />
        </div>
      </section>

      <section className="panel panel-wide">
        <h2>Approved Project</h2>
        {projectError ? <p className="inline-error">{projectError.message}</p> : null}
        <div className="project-grid">
          <div className="address-block">
            <span className="wallet-label">Project</span>
            <strong>{project.name}</strong>
            <span className="muted">{project.projectKey}</span>
          </div>
          <div className="address-block">
            <span className="wallet-label">Recipient</span>
            <code>{formatAddress(project.recipient)}</code>
          </div>
          <div className="address-block">
            <span className="wallet-label">Project ID</span>
            <code>{project.projectId}</code>
          </div>
          <div className="address-block">
            <span className="wallet-label">Budget</span>
            <span>{projectTuple ? `${formatTokenAmount(projectTuple[1].toString())} WETH` : 'Loading...'}</span>
          </div>
          <div className="address-block">
            <span className="wallet-label">Released</span>
            <span>{projectTuple ? `${formatTokenAmount(projectTuple[2].toString())} WETH` : 'Loading...'}</span>
          </div>
          <div className="address-block">
            <span className="wallet-label">Milestones</span>
            <span>
              {projectTuple
                ? `${projectTuple[4].toString()} / ${projectTuple[3].toString()} released (${projectTuple[5] ? 'active' : 'closed'})`
                : 'Loading...'}
            </span>
          </div>
        </div>
      </section>
    </div>
  );
}
