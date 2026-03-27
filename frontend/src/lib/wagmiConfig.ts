import { injected } from 'wagmi/connectors';
import { createConfig, http } from 'wagmi';
import { sepolia } from 'wagmi/chains';

export interface FrontendEnvironment {
  rpcUrl: string;
  chainId: number;
}

export function readFrontendEnvironment(): FrontendEnvironment {
  const rpcUrl = import.meta.env.VITE_SEPOLIA_RPC_URL;
  const rawChainId = import.meta.env.VITE_CHAIN_ID;

  if (typeof rpcUrl !== 'string' || rpcUrl.trim() === '') {
    throw new Error('Missing VITE_SEPOLIA_RPC_URL. Copy frontend/.env.example and provide a Sepolia RPC URL.');
  }

  const chainId = Number(rawChainId);
  if (!Number.isInteger(chainId) || chainId !== 11155111) {
    throw new Error('VITE_CHAIN_ID must be set to 11155111 for Sepolia.');
  }

  return { rpcUrl, chainId };
}

export function createFrontendWagmiConfig(environment: FrontendEnvironment) {
  if (environment.chainId !== sepolia.id) {
    throw new Error(`Unsupported chain id ${environment.chainId}. Only Sepolia is allowed.`);
  }

  return createConfig({
    chains: [sepolia],
    connectors: [injected()],
    transports: {
      [sepolia.id]: http(environment.rpcUrl),
    },
  });
}