import type { DemoEvidenceManifest, ProposalScenarioManifest, ScreenshotManifestEntry } from '../types';

export interface EvidenceTransactionRow {
  section: string;
  step: string;
  txHash: string;
  url: string;
}

export function requireParticipantAddress(evidence: DemoEvidenceManifest, label: string): string {
  const address = evidence.participants[label];
  if (!address) {
    throw new Error(`Evidence manifest is missing participant address for ${label}.`);
  }
  return address;
}

export function requireProjectDefinition(scenarios: ProposalScenarioManifest) {
  if (!scenarios.project) {
    throw new Error('Proposal scenario manifest is missing the project definition.');
  }
  return scenarios.project;
}

export function flattenEvidenceTransactions(
  evidence: DemoEvidenceManifest,
  etherscanBaseUrl: string,
): EvidenceTransactionRow[] {
  const rows: EvidenceTransactionRow[] = [];
  const transactionLinks = evidence.etherscanLinks.transactions;

  const appendRow = (section: string, step: string, txHash: string) => {
    rows.push({
      section,
      step,
      txHash,
      url: transactionLinks[`${section === 'Seed State' ? 'seedState' : section}.${step}`] ?? `${etherscanBaseUrl}/tx/${txHash}`,
    });
  };

  const walkTransactions = (section: string, prefix: string, value: unknown): void => {
    if (!value) {
      return;
    }
    if (typeof value === 'string' && value.startsWith('0x') && value.length === 66) {
      appendRow(section, prefix, value);
      return;
    }
    if (typeof value !== 'object') {
      return;
    }

    const record = value as Record<string, unknown>;
    if (
      typeof record.transactionHash === 'string' &&
      record.transactionHash.startsWith('0x') &&
      record.transactionHash.length === 66
    ) {
      appendRow(section, prefix, record.transactionHash);
      return;
    }

    for (const [key, child] of Object.entries(record)) {
      const nextPrefix = prefix ? `${prefix}.${key}` : key;
      walkTransactions(section, nextPrefix, child);
    }
  };

  const fundTreasuryHash = (evidence.seedState.fundTreasury as { transactionHash?: string } | undefined)?.transactionHash;
  if (fundTreasuryHash) {
    appendRow('Seed State', 'fundTreasury', fundTreasuryHash);
  }

  walkTransactions('Seed State', 'selfDelegations', evidence.seedState.selfDelegations);
  walkTransactions(
    'Seed State',
    'bootstrapMembers',
    (evidence.seedState.bootstrapMembers as { transactions?: Record<string, unknown> } | undefined)?.transactions,
  );

  for (const [proposalSlug, proposalRecord] of Object.entries(evidence.proposals)) {
    walkTransactions(proposalSlug, '', proposalRecord.transactions);
  }

  return rows;
}

export function groupScreenshots(entries: ScreenshotManifestEntry[]): Record<string, ScreenshotManifestEntry[]> {
  return entries.reduce<Record<string, ScreenshotManifestEntry[]>>((accumulator, entry) => {
    const current = accumulator[entry.reportSection] ?? [];
    current.push(entry);
    accumulator[entry.reportSection] = current;
    return accumulator;
  }, {});
}
