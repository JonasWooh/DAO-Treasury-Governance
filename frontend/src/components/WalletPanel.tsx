import { useMemo } from 'react';
import {
  useAccount,
  useChainId,
  useConnect,
  useDisconnect,
  useReadContract,
  useWaitForTransactionReceipt,
  useWriteContract,
} from 'wagmi';

import { contractAbis } from '../lib/abis';
import {
  formatAddress,
  formatTokenAmount,
  toEtherscanAddressLink,
  toEtherscanTxLink,
} from '../lib/formatters';

interface WalletPanelProps {
  tokenAddress: string;
  expectedChainId: number;
  etherscanBaseUrl: string;
}

export function WalletPanel({ tokenAddress, expectedChainId, etherscanBaseUrl }: WalletPanelProps) {
  const { address, isConnected, connector } = useAccount();
  const chainId = useChainId();
  const networkMismatch = isConnected && chainId !== expectedChainId;
  const { connect, connectors, error: connectError, isPending: connectPending } = useConnect();
  const { disconnect } = useDisconnect();
  const { data: delegateeData, error: delegateeError } = useReadContract({
    address: tokenAddress as `0x${string}`,
    abi: contractAbis.CampusInnovationFundToken,
    functionName: 'delegates',
    args: address ? [address] : undefined,
    query: { enabled: isConnected && Boolean(address) && !networkMismatch },
  });
  const { data: liveVotesData, error: liveVotesError } = useReadContract({
    address: tokenAddress as `0x${string}`,
    abi: contractAbis.CampusInnovationFundToken,
    functionName: 'getVotes',
    args: address ? [address] : undefined,
    query: { enabled: isConnected && Boolean(address) && !networkMismatch },
  });
  const { data: delegateHash, error: delegateError, isPending: delegatePending, writeContract } =
    useWriteContract();
  const delegateReceipt = useWaitForTransactionReceipt({
    hash: delegateHash,
  });

  const primaryConnector = useMemo(() => connectors[0] ?? null, [connectors]);
  const delegatee = delegateeData as `0x${string}` | undefined;
  const liveVotes = liveVotesData as bigint | undefined;
  const selfDelegated =
    Boolean(address) &&
    typeof delegatee === 'string' &&
    delegatee.toLowerCase() === address?.toLowerCase();
  const votesActive = selfDelegated && Boolean(liveVotes && liveVotes > 0n);

  function handleDelegate() {
    if (!address || votesActive) {
      return;
    }
    writeContract({
      address: tokenAddress as `0x${string}`,
      abi: contractAbis.CampusInnovationFundToken,
      functionName: 'delegate',
      args: [address],
    });
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Wallet &amp; Voting Access</h2>
          <p className="muted">
            Connect an active Sepolia member wallet to delegate votes and sign governance actions.
          </p>
        </div>
      </div>
      <div className="stack">
        <div className="wallet-row">
          <span className="wallet-label">Wallet</span>
          <span className="wallet-value">
            {isConnected && address ? `${formatAddress(address)} via ${connector?.name ?? 'wallet'}` : 'Disconnected'}
          </span>
        </div>
        <div className="wallet-row">
          <span className="wallet-label">Network</span>
          <span className={networkMismatch ? 'status status-error' : 'status status-good'}>
            {isConnected ? `chainId ${chainId}` : `Expected chainId ${expectedChainId}`}
          </span>
        </div>
        {connectError ? <p className="inline-error">{connectError.message}</p> : null}
        {delegateError ? <p className="inline-error">{delegateError.message}</p> : null}
        {delegateeError ? <p className="inline-error">{delegateeError.message}</p> : null}
        {liveVotesError ? <p className="inline-error">{liveVotesError.message}</p> : null}
        {networkMismatch ? (
          <p className="inline-error">Connected wallet is not on Sepolia. Switch networks before writing.</p>
        ) : null}
        <div className="button-row">
          {!isConnected ? (
            <button
              type="button"
              className="action-button"
              onClick={() => primaryConnector && connect({ connector: primaryConnector })}
              disabled={!primaryConnector || connectPending}
            >
              {connectPending ? 'Connecting...' : 'Connect Wallet'}
            </button>
          ) : (
            <button type="button" className="secondary-button" onClick={() => disconnect()}>
              Disconnect
            </button>
          )}
          <button
            type="button"
            className="action-button"
            onClick={handleDelegate}
            disabled={!isConnected || !address || networkMismatch || delegatePending || votesActive}
          >
            {votesActive ? 'Votes Active' : delegatePending ? 'Submitting...' : 'Delegate Votes'}
          </button>
        </div>
        <p className="muted">
          {votesActive
            ? `Voting power is active for this wallet (${formatTokenAmount(liveVotes ?? 0n)} CIF).`
            : "Delegate once to activate this wallet's CIF voting power before casting governance votes."}
        </p>
        <div className="quick-links">
          {address ? (
            <a
              className="quick-link"
              href={toEtherscanAddressLink(etherscanBaseUrl, address)}
              target="_blank"
              rel="noreferrer"
            >
              View wallet on Etherscan
            </a>
          ) : null}
          <a
            className="quick-link"
            href={toEtherscanAddressLink(etherscanBaseUrl, tokenAddress)}
            target="_blank"
            rel="noreferrer"
          >
            View CIF token contract
          </a>
        </div>
        {delegateHash ? (
          <p className="muted">
            Delegate tx:{' '}
            <a href={toEtherscanTxLink(etherscanBaseUrl, delegateHash)} target="_blank" rel="noreferrer">
              <code>{delegateHash}</code>
            </a>{' '}
            ({delegateReceipt.isLoading ? 'pending' : 'confirmed'})
          </p>
        ) : null}
      </div>
    </section>
  );
}
