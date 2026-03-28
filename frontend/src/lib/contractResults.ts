type UnknownRecord = Record<string, unknown>;

function asRecord(value: unknown): UnknownRecord | null {
  return typeof value === 'object' && value !== null ? (value as UnknownRecord) : null;
}

function readField<T>(value: unknown, index: number, key: string): T | undefined {
  const record = asRecord(value);
  if (!record) {
    return undefined;
  }
  const indexedValue = record[index];
  if (indexedValue !== undefined) {
    return indexedValue as T;
  }
  const namedValue = record[key];
  return namedValue !== undefined ? (namedValue as T) : undefined;
}

export interface LiveMemberResult {
  isRegistered: boolean;
  isActive: boolean;
  currentReputation: bigint;
}

export function normalizeMemberResult(value: unknown): LiveMemberResult | null {
  const isRegistered = readField<boolean>(value, 0, 'isRegistered');
  const isActive = readField<boolean>(value, 1, 'isActive');
  const currentReputation = readField<bigint>(value, 2, 'currentReputation');
  if (
    typeof isRegistered !== 'boolean' ||
    typeof isActive !== 'boolean' ||
    typeof currentReputation !== 'bigint'
  ) {
    return null;
  }
  return { isRegistered, isActive, currentReputation };
}

export interface LiveProposalResult {
  proposalId: bigint;
  proposer: `0x${string}`;
  recipient: `0x${string}`;
  title: string;
  metadataURI: string;
  requestedFundingWeth: bigint;
  milestoneCount: number;
  status: number;
  governorProposalId: bigint;
  projectId: `0x${string}`;
}

export function normalizeProposalResult(value: unknown): LiveProposalResult | null {
  const proposalId = readField<bigint>(value, 0, 'proposalId');
  const proposer = readField<`0x${string}`>(value, 1, 'proposer');
  const recipient = readField<`0x${string}`>(value, 2, 'recipient');
  const title = readField<string>(value, 3, 'title');
  const metadataURI = readField<string>(value, 4, 'metadataURI');
  const requestedFundingWeth = readField<bigint>(value, 5, 'requestedFundingWeth');
  const milestoneCount = readField<number>(value, 6, 'milestoneCount');
  const status = readField<number>(value, 7, 'status');
  const governorProposalId = readField<bigint>(value, 8, 'governorProposalId');
  const projectId = readField<`0x${string}`>(value, 9, 'projectId');
  if (
    typeof proposalId !== 'bigint' ||
    typeof proposer !== 'string' ||
    typeof recipient !== 'string' ||
    typeof title !== 'string' ||
    typeof metadataURI !== 'string' ||
    typeof requestedFundingWeth !== 'bigint' ||
    typeof milestoneCount !== 'number' ||
    typeof status !== 'number' ||
    typeof governorProposalId !== 'bigint' ||
    typeof projectId !== 'string'
  ) {
    return null;
  }
  return {
    proposalId,
    proposer,
    recipient,
    title,
    metadataURI,
    requestedFundingWeth,
    milestoneCount,
    status,
    governorProposalId,
    projectId,
  };
}

export interface LiveProjectResult {
  projectId: `0x${string}`;
  sourceProposalId: bigint;
  recipient: `0x${string}`;
  approvedBudgetWeth: bigint;
  releasedWeth: bigint;
  nextClaimableMilestone: number;
  status: number;
}

export function normalizeProjectResult(value: unknown): LiveProjectResult | null {
  const projectId = readField<`0x${string}`>(value, 0, 'projectId');
  const sourceProposalId = readField<bigint>(value, 1, 'sourceProposalId');
  const recipient = readField<`0x${string}`>(value, 2, 'recipient');
  const approvedBudgetWeth = readField<bigint>(value, 3, 'approvedBudgetWeth');
  const releasedWeth = readField<bigint>(value, 4, 'releasedWeth');
  const nextClaimableMilestone = readField<number>(value, 5, 'nextClaimableMilestone');
  const status = readField<number>(value, 6, 'status');
  if (
    typeof projectId !== 'string' ||
    typeof sourceProposalId !== 'bigint' ||
    typeof recipient !== 'string' ||
    typeof approvedBudgetWeth !== 'bigint' ||
    typeof releasedWeth !== 'bigint' ||
    typeof nextClaimableMilestone !== 'number' ||
    typeof status !== 'number'
  ) {
    return null;
  }
  return {
    projectId,
    sourceProposalId,
    recipient,
    approvedBudgetWeth,
    releasedWeth,
    nextClaimableMilestone,
    status,
  };
}

export interface LiveMilestoneResult {
  index: number;
  description: string;
  amountWeth: bigint;
  evidenceURI: string;
  state: number;
  claimGovernorProposalId: bigint;
}

export function normalizeMilestoneResult(value: unknown): LiveMilestoneResult | null {
  const index = readField<number>(value, 0, 'index');
  const description = readField<string>(value, 1, 'description');
  const amountWeth = readField<bigint>(value, 2, 'amountWeth');
  const evidenceURI = readField<string>(value, 3, 'evidenceURI');
  const state = readField<number>(value, 4, 'state');
  const claimGovernorProposalId = readField<bigint>(value, 5, 'claimGovernorProposalId');
  if (
    typeof index !== 'number' ||
    typeof description !== 'string' ||
    typeof amountWeth !== 'bigint' ||
    typeof evidenceURI !== 'string' ||
    typeof state !== 'number' ||
    typeof claimGovernorProposalId !== 'bigint'
  ) {
    return null;
  }
  return { index, description, amountWeth, evidenceURI, state, claimGovernorProposalId };
}
