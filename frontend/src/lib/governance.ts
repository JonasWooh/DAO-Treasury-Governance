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
