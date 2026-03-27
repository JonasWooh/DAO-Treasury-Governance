export interface FrontendConfig {
  generatedAt: string;
  configured: boolean;
  network: {
    name: string;
    chainId: number;
  };
  contracts: Record<string, string>;
  externalProtocols: Record<string, string>;
  evidenceSources: {
    deployments: string;
    proposalScenarios: string;
    demoEvidence: string;
    screenshotManifest: string;
  };
  etherscanBaseUrl: string;
  note?: string;
}

export interface DeploymentManifest {
  configured?: boolean;
  network: {
    name: string;
    chainId: number;
  };
  contracts: Record<string, string>;
  externalProtocols: Record<string, string>;
  transactions: Record<string, string>;
  constructorArgs?: Record<string, unknown>;
  config?: Record<string, unknown>;
  allocationRecipients?: Record<string, string>;
}

export interface ProposalScenario {
  slug: string;
  title: string;
  description: string;
  targets: string[];
  values: string[];
  calldatas: string[];
  descriptionHash: string;
  proposalId: string;
  operationId: string;
  expectedOutcome: Record<string, string | boolean | number>;
}

export interface ProposalScenarioManifest {
  configured?: boolean;
  network?: {
    name: string;
    chainId: number;
  };
  contracts?: Record<string, string>;
  project: {
    name: string;
    projectKey: string;
    projectId: string;
    recipient: string;
    maxBudgetWeth: string;
    milestoneCount: number;
    milestonePayoutsWeth?: Record<string, string>;
  } | null;
  proposals: ProposalScenario[];
}

export interface DemoEvidenceProposalRecord {
  title?: string;
  description?: string;
  proposalId?: string;
  descriptionHash?: string;
  operationId?: string;
  finalState?: string;
  finalVotes?: Record<string, string>;
  transactions?: {
    propose?: string | null;
    votes?: Record<string, string | null>;
    queue?: string | null;
    execute?: string | null;
  };
  snapshots?: Record<string, unknown>;
}

export interface DemoEvidenceManifest {
  configured?: boolean;
  network?: {
    name: string;
    chainId: number;
  };
  contracts?: Record<string, string>;
  participants: Record<string, string>;
  project: {
    projectId: string;
    recipient: string;
    [key: string]: unknown;
  } | null;
  seedState: Record<string, unknown>;
  proposals: Record<string, DemoEvidenceProposalRecord>;
  etherscanLinks: {
    addresses: Record<string, string>;
    transactions: Record<string, string>;
  };
  note?: string;
}

export interface ScreenshotManifestEntry {
  id: string;
  caption: string;
  reportSection: string;
  expectedPath: string;
  required: boolean;
  category: string;
}

export interface ScreenshotManifest {
  network: {
    name: string;
    chainId: number;
  };
  generatedAt: string;
  screenshots: ScreenshotManifestEntry[];
}

export interface RuntimeBundle {
  config: FrontendConfig;
  deployments: DeploymentManifest;
  scenarios: ProposalScenarioManifest;
  evidence: DemoEvidenceManifest;
  screenshots: ScreenshotManifest;
}

export interface RuntimeState {
  loading: boolean;
  bundle: RuntimeBundle | null;
  error: string | null;
}