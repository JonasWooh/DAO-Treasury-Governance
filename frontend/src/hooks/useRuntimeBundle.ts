import { useEffect, useState } from 'react';

import type { RuntimeBundle, RuntimeState } from '../types';
import {
  assertConfiguredFrontendConfig,
  validateDemoEvidenceManifest,
  validateDeploymentManifest,
  validateFrontendConfig,
  validateProposalScenarioManifest,
  validateScreenshotManifest,
} from '../lib/runtimeValidation';

async function fetchJson(path: string): Promise<unknown> {
  const response = await fetch(path, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Failed to fetch ${path}: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export function useRuntimeBundle(): RuntimeState {
  const [state, setState] = useState<RuntimeState>({
    loading: true,
    bundle: null,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;

    async function loadBundle(): Promise<void> {
      try {
        const config = validateFrontendConfig();
        assertConfiguredFrontendConfig(config);

        const [deploymentsPayload, scenariosPayload, evidencePayload, screenshotsPayload] = await Promise.all([
          fetchJson(config.evidenceSources.deployments),
          fetchJson(config.evidenceSources.proposalScenarios),
          fetchJson(config.evidenceSources.demoEvidence),
          fetchJson(config.evidenceSources.screenshotManifest),
        ]);

        const bundle: RuntimeBundle = {
          config,
          deployments: validateDeploymentManifest(deploymentsPayload),
          scenarios: validateProposalScenarioManifest(scenariosPayload),
          evidence: validateDemoEvidenceManifest(evidencePayload),
          screenshots: validateScreenshotManifest(screenshotsPayload),
        };

        if (!cancelled) {
          setState({ loading: false, bundle, error: null });
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            loading: false,
            bundle: null,
            error: error instanceof Error ? error.message : 'Unknown runtime bundle error.',
          });
        }
      }
    }

    void loadBundle();

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}