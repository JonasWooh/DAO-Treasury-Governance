import { useMemo } from 'react';
import {
  useAccount,
  useChainId,
  useConnect,
  useDisconnect,
  useWaitForTransactionReceipt,
  useWriteContract,
} from 'wagmi';

import { contractAbis } from '../lib/abis';
import { formatAddress } from '../lib/formatters';

interface WalletPanelProps {
  tokenAddress: string;
  expectedChainId: number;
}

export function WalletPanel({ tokenAddress, expectedChainId }: WalletPanelProps) {
  const { address, isConnected, connector } = useAccount();
  const chainId = useChainId();
  const { connect, connectors, error: connectError, isPending: connectPending } = useConnect();
  const { disconnect } = useDisconnect();
  const { data: delegateHash, error: delegateError, isPending: delegatePending, writeContract } =
    useWriteContract();
  const delegateReceipt = useWaitForTransactionReceipt({
    hash: delegateHash,
  });

  const networkMismatch = isConnected && chainId !== expectedChainId;
  const primaryConnector = useMemo(() => connectors[0] ?? null, [connectors]);

  function handleDelegate() {
    if (!address) {
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
          <h2>Wallet Access</h2>
          <p className="muted">Connect a Sepolia wallet to delegate votes and sign governance actions.</p>
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
            disabled={!isConnected || !address || networkMismatch || delegatePending}
          >
            {delegatePending ? 'Submitting...' : 'Delegate Votes'}
          </button>
        </div>
        {delegateHash ? (
          <p className="muted">
            Delegate tx: <code>{delegateHash}</code> ({delegateReceipt.isLoading ? 'pending' : 'confirmed'})
          </p>
        ) : null}
      </div>
    </section>
  );
}
