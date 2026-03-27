export const GOVERNOR_STATE_LABELS: Record<number, string> = {
  0: 'Pending',
  1: 'Active',
  2: 'Canceled',
  3: 'Defeated',
  4: 'Succeeded',
  5: 'Queued',
  6: 'Expired',
  7: 'Executed',
};

export function governorStateLabel(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return 'Unavailable';
  }
  return GOVERNOR_STATE_LABELS[value] ?? `Unknown (${value})`;
}

export function supportLabel(value: number): string {
  if (value === 0) {
    return 'Against';
  }
  if (value === 1) {
    return 'For';
  }
  if (value === 2) {
    return 'Abstain';
  }
  return `Unknown (${value})`;
}

export const FUNDING_PROPOSAL_STATUS_LABELS: Record<number, string> = {
  0: 'Submitted',
  1: 'Voting',
  2: 'Approved',
  3: 'Rejected',
  4: 'Cancelled',
};

export const PROJECT_STATUS_LABELS: Record<number, string> = {
  0: 'Active',
  1: 'Completed',
  2: 'Cancelled',
};

export const MILESTONE_STATE_LABELS: Record<number, string> = {
  0: 'Locked',
  1: 'OpenForClaim',
  2: 'ClaimSubmitted',
  3: 'ClaimRejected',
  4: 'Released',
};

export function fundingProposalStatusLabel(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return 'Unavailable';
  }
  return FUNDING_PROPOSAL_STATUS_LABELS[value] ?? `Unknown (${value})`;
}

export function projectStatusLabel(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return 'Unavailable';
  }
  return PROJECT_STATUS_LABELS[value] ?? `Unknown (${value})`;
}

export function milestoneStateLabel(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return 'Unavailable';
  }
  return MILESTONE_STATE_LABELS[value] ?? `Unknown (${value})`;
}
