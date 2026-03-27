import frontendConfig from '../generated/frontend.config.sepolia.json';
import type {
  DemoEvidenceManifest,
  DeploymentManifest,
  FundingStateManifest,
  FrontendConfig,
  ProposalScenarioManifest,
  ScreenshotManifest,
} from '../types';

const REQUIRED_CONTRACT_NAMES = [
  'CampusInnovationFundToken',
  'ReputationRegistry',
  'HybridVotesAdapter',
  'InnovationGovernor',
  'FundingRegistry',
  'TimelockController',
  'InnovationTreasury',
  'TreasuryOracle',
  'AaveWethAdapter',
] as const;

const REQUIRED_EXTERNAL_PROTOCOL_NAMES = [
  'WETH',
  'ChainlinkEthUsdFeed',
  'AavePool',
  'AaveAWeth',
] as const;

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isAddress(value: unknown): value is string {
  return typeof value === 'string' && /^0x[a-fA-F0-9]{40}$/.test(value);
}

function isHash(value: unknown): value is string {
  return typeof value === 'string' && /^0x[a-fA-F0-9]{64}$/.test(value);
}

function expectObject(value: unknown, label: string): Record<string, unknown> {
  if (!isObject(value)) {
    throw new Error(`${label} must be an object.`);
  }
  return value;
}

export function validateFrontendConfig(): FrontendConfig {
  const config = frontendConfig as FrontendConfig;
  if (config.network.name !== 'sepolia' || config.network.chainId !== 11155111) {
    throw new Error('Frontend config must target Sepolia (chainId 11155111).');
  }
  if (!config.evidenceSources.deployments || !config.evidenceSources.proposalScenarios || !config.evidenceSources.demoEvidence || !config.evidenceSources.screenshotManifest) {
    throw new Error('Frontend config is missing one or more evidence source paths.');
  }
  if (!config.evidenceSources.fundingState) {
    throw new Error('Frontend config is missing the funding state source path.');
  }
  return config;
}

export function assertConfiguredFrontendConfig(config: FrontendConfig): void {
  if (!config.configured) {
    throw new Error(config.note ?? 'Frontend bundle is not configured. Run the frontend bundle export script first.');
  }
  for (const contractName of REQUIRED_CONTRACT_NAMES) {
    if (!isAddress(config.contracts[contractName])) {
      throw new Error(`Frontend config is missing a valid address for ${contractName}.`);
    }
  }
  for (const externalProtocolName of REQUIRED_EXTERNAL_PROTOCOL_NAMES) {
    if (!isAddress(config.externalProtocols[externalProtocolName])) {
      throw new Error(`Frontend config is missing a valid address for ${externalProtocolName}.`);
    }
  }
}

export function validateDeploymentManifest(payload: unknown): DeploymentManifest {
  const manifest = expectObject(payload, 'Deployment manifest');
  const network = expectObject(manifest.network, 'Deployment manifest.network');
  const contracts = expectObject(manifest.contracts, 'Deployment manifest.contracts');
  const externalProtocols = expectObject(manifest.externalProtocols, 'Deployment manifest.externalProtocols');

  if (network.name !== 'sepolia' || network.chainId !== 11155111) {
    throw new Error('Deployment manifest must target Sepolia.');
  }
  for (const contractName of REQUIRED_CONTRACT_NAMES) {
    if (!isAddress(contracts[contractName])) {
      throw new Error(`Deployment manifest is missing a valid address for ${contractName}.`);
    }
  }
  for (const externalProtocolName of REQUIRED_EXTERNAL_PROTOCOL_NAMES) {
    if (!isAddress(externalProtocols[externalProtocolName])) {
      throw new Error(`Deployment manifest is missing a valid address for ${externalProtocolName}.`);
    }
  }
  return manifest as unknown as DeploymentManifest;
}

export function validateProposalScenarioManifest(payload: unknown): ProposalScenarioManifest {
  const manifest = expectObject(payload, 'Proposal scenario manifest');
  const project = expectObject(manifest.project, 'Proposal scenario manifest.project');
  const proposals = manifest.proposals;

  if (!isHash(project.projectId) || !isAddress(project.recipient)) {
    throw new Error('Proposal scenario manifest is missing a valid project definition.');
  }
  if (!Array.isArray(proposals) || proposals.length === 0) {
    throw new Error('Proposal scenario manifest must contain at least one proposal.');
  }
  for (const proposal of proposals) {
    const entry = expectObject(proposal, 'Proposal scenario manifest entry');
    if (typeof entry.slug !== 'string' || typeof entry.description !== 'string' || !isHash(entry.descriptionHash) || !isHash(entry.operationId)) {
      throw new Error('Proposal scenario manifest contains a malformed proposal entry.');
    }
    if (!Array.isArray(entry.targets) || entry.targets.some((target) => !isAddress(target))) {
      throw new Error(`Proposal ${String(entry.slug)} contains an invalid target address.`);
    }
  }
  return manifest as unknown as ProposalScenarioManifest;
}

export function validateDemoEvidenceManifest(payload: unknown): DemoEvidenceManifest {
  const manifest = expectObject(payload, 'Demo evidence manifest');
  const etherscanLinks = expectObject(manifest.etherscanLinks, 'Demo evidence manifest.etherscanLinks');
  expectObject(etherscanLinks.addresses, 'Demo evidence manifest.etherscanLinks.addresses');
  expectObject(etherscanLinks.transactions, 'Demo evidence manifest.etherscanLinks.transactions');
  return manifest as unknown as DemoEvidenceManifest;
}

export function validateFundingStateManifest(payload: unknown): FundingStateManifest {
  const manifest = expectObject(payload, 'Funding state manifest');
  const network = expectObject(manifest.network, 'Funding state manifest.network');
  const contracts = expectObject(manifest.contracts, 'Funding state manifest.contracts');
  const reputationSummary = expectObject(manifest.reputationSummary, 'Funding state manifest.reputationSummary');

  if (network.name !== 'sepolia' || network.chainId !== 11155111) {
    throw new Error('Funding state manifest must target Sepolia.');
  }
  if (typeof manifest.generatedAt !== 'string' || manifest.generatedAt.length === 0) {
    throw new Error('Funding state manifest is missing generatedAt.');
  }
  for (const contractName of ['FundingRegistry', 'ReputationRegistry', 'HybridVotesAdapter'] as const) {
    if (!isAddress(contracts[contractName])) {
      throw new Error(`Funding state manifest is missing a valid address for ${contractName}.`);
    }
  }
  for (const key of ['members', 'proposals', 'projects', 'milestones'] as const) {
    if (!Array.isArray(manifest[key])) {
      throw new Error(`Funding state manifest.${key} must be an array.`);
    }
  }
  if (typeof reputationSummary.totalActiveReputation !== 'string' || typeof reputationSummary.activeMemberCount !== 'number') {
    throw new Error('Funding state manifest.reputationSummary is malformed.');
  }

  return manifest as unknown as FundingStateManifest;
}

export function validateScreenshotManifest(payload: unknown): ScreenshotManifest {
  const manifest = expectObject(payload, 'Screenshot manifest');
  const network = expectObject(manifest.network, 'Screenshot manifest.network');
  if (network.name !== 'sepolia' || network.chainId !== 11155111) {
    throw new Error('Screenshot manifest must target Sepolia.');
  }
  if (!Array.isArray(manifest.screenshots) || manifest.screenshots.length === 0) {
    throw new Error('Screenshot manifest must contain at least one screenshot entry.');
  }
  return manifest as unknown as ScreenshotManifest;
}
