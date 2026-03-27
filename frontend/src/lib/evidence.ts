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

  const fundTreasuryHash = (evidence.seedState.fundTreasury as { transactionHash?: string } | undefined)?.transactionHash;
  if (fundTreasuryHash) {
    rows.push({
      section: 'Seed State',
      step: 'fundTreasury',
      txHash: fundTreasuryHash,
      url: transactionLinks['seedState.fundTreasury'] ?? `${etherscanBaseUrl}/tx/${fundTreasuryHash}`,
    });
  }

  const selfDelegations = (evidence.seedState.selfDelegations as Record<string, { transactionHash?: string }> | undefined) ?? {};
  for (const [label, record] of Object.entries(selfDelegations)) {
    if (!record.transactionHash) {
      continue;
    }
    rows.push({
      section: 'Seed State',
      step: `selfDelegate.${label}`,
      txHash: record.transactionHash,
      url:
        transactionLinks[`seedState.selfDelegations.${label}`] ??
        `${etherscanBaseUrl}/tx/${record.transactionHash}`,
    });
  }

  for (const [proposalSlug, proposalRecord] of Object.entries(evidence.proposals)) {
    const transactions = proposalRecord.transactions ?? {};
    if (transactions.propose) {
      rows.push({
        section: proposalSlug,
        step: 'propose',
        txHash: transactions.propose,
        url: transactionLinks[`${proposalSlug}.propose`] ?? `${etherscanBaseUrl}/tx/${transactions.propose}`,
      });
    }
    for (const [label, txHash] of Object.entries(transactions.votes ?? {})) {
      if (!txHash) {
        continue;
      }
      rows.push({
        section: proposalSlug,
        step: `vote.${label}`,
        txHash,
        url: transactionLinks[`${proposalSlug}.vote.${label}`] ?? `${etherscanBaseUrl}/tx/${txHash}`,
      });
    }
    if (transactions.queue) {
      rows.push({
        section: proposalSlug,
        step: 'queue',
        txHash: transactions.queue,
        url: transactionLinks[`${proposalSlug}.queue`] ?? `${etherscanBaseUrl}/tx/${transactions.queue}`,
      });
    }
    if (transactions.execute) {
      rows.push({
        section: proposalSlug,
        step: 'execute',
        txHash: transactions.execute,
        url: transactionLinks[`${proposalSlug}.execute`] ?? `${etherscanBaseUrl}/tx/${transactions.execute}`,
      });
    }
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
