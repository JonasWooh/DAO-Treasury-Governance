import { describe, expect, it } from 'vitest';

import { flattenEvidenceTransactions, requireParticipantAddress } from './evidence';
import { mockRuntimeBundle } from '../testFixtures';
import {
  assertConfiguredFrontendConfig,
  validateDeploymentManifest,
  validateProposalScenarioManifest,
  validateScreenshotManifest,
} from './runtimeValidation';

describe('runtimeValidation', () => {
  it('accepts a configured frontend bundle', () => {
    expect(() => assertConfiguredFrontendConfig(mockRuntimeBundle.config)).not.toThrow();
  });

  it('rejects malformed deployment manifests', () => {
    expect(() => validateDeploymentManifest({ network: { name: 'sepolia', chainId: 11155111 }, contracts: {}, externalProtocols: {} })).toThrow();
  });

  it('accepts valid scenario and screenshot manifests', () => {
    expect(() => validateProposalScenarioManifest(mockRuntimeBundle.scenarios)).not.toThrow();
    expect(() => validateScreenshotManifest(mockRuntimeBundle.screenshots)).not.toThrow();
  });
});

describe('evidence helpers', () => {
  it('flattens evidence transaction rows', () => {
    const rows = flattenEvidenceTransactions(mockRuntimeBundle.evidence, mockRuntimeBundle.config.etherscanBaseUrl);
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.some((row) => row.section === 'Seed State')).toBe(true);
  });

  it('requires participant addresses', () => {
    expect(requireParticipantAddress(mockRuntimeBundle.evidence, 'voterA')).toBe(mockRuntimeBundle.evidence.participants.voterA);
    expect(() => requireParticipantAddress(mockRuntimeBundle.evidence, 'unknown')).toThrow();
  });
});
