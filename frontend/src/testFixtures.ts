import type { RuntimeBundle } from './types';

export const mockAddresses = {
  token: '0x1000000000000000000000000000000000000001',
  governor: '0x1000000000000000000000000000000000000002',
  timelock: '0x1000000000000000000000000000000000000003',
  treasury: '0x1000000000000000000000000000000000000004',
  oracle: '0x1000000000000000000000000000000000000005',
  adapter: '0x1000000000000000000000000000000000000006',
  weth: '0x1000000000000000000000000000000000000007',
  chainlink: '0x1000000000000000000000000000000000000008',
  aavePool: '0x1000000000000000000000000000000000000009',
  aWeth: '0x1000000000000000000000000000000000000010',
  voterA: '0x2000000000000000000000000000000000000001',
  voterB: '0x2000000000000000000000000000000000000002',
  voterC: '0x2000000000000000000000000000000000000003',
  recipient: '0x2000000000000000000000000000000000000004',
};

export const mockRuntimeBundle: RuntimeBundle = {
  config: {
    generatedAt: '2026-03-27T00:00:00Z',
    configured: true,
    network: {
      name: 'sepolia',
      chainId: 11155111,
    },
    contracts: {
      CampusInnovationFundToken: mockAddresses.token,
      InnovationGovernor: mockAddresses.governor,
      TimelockController: mockAddresses.timelock,
      InnovationTreasury: mockAddresses.treasury,
      TreasuryOracle: mockAddresses.oracle,
      AaveWethAdapter: mockAddresses.adapter,
    },
    externalProtocols: {
      WETH: mockAddresses.weth,
      ChainlinkEthUsdFeed: mockAddresses.chainlink,
      AavePool: mockAddresses.aavePool,
      AaveAWeth: mockAddresses.aWeth,
    },
    evidenceSources: {
      deployments: '/runtime/deployments.sepolia.json',
      proposalScenarios: '/runtime/proposal_scenarios.sepolia.json',
      demoEvidence: '/runtime/demo_evidence.sepolia.json',
      screenshotManifest: '/runtime/screenshot-manifest.sepolia.json',
    },
    etherscanBaseUrl: 'https://sepolia.etherscan.io',
  },
  deployments: {
    network: {
      name: 'sepolia',
      chainId: 11155111,
    },
    contracts: {
      CampusInnovationFundToken: mockAddresses.token,
      InnovationGovernor: mockAddresses.governor,
      TimelockController: mockAddresses.timelock,
      InnovationTreasury: mockAddresses.treasury,
      TreasuryOracle: mockAddresses.oracle,
      AaveWethAdapter: mockAddresses.adapter,
    },
    externalProtocols: {
      WETH: mockAddresses.weth,
      ChainlinkEthUsdFeed: mockAddresses.chainlink,
      AavePool: mockAddresses.aavePool,
      AaveAWeth: mockAddresses.aWeth,
    },
    transactions: {
      deployToken: '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      deployGovernor: '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
    },
  },
  scenarios: {
    project: {
      name: 'Smart Recycling Kiosk',
      projectKey: 'SMART_RECYCLING_KIOSK',
      projectId: '0x1111111111111111111111111111111111111111111111111111111111111111',
      recipient: mockAddresses.recipient,
      maxBudgetWeth: '1000000000000000000',
      milestoneCount: 2,
      milestonePayoutsWeth: {
        milestone0: '500000000000000000',
      },
    },
    proposals: [
      {
        slug: 'proposal1_approve_project',
        title: 'Proposal 1',
        description: 'Proposal 1: Approve Smart Recycling Kiosk project',
        targets: [mockAddresses.treasury],
        values: ['0'],
        calldatas: ['0xaaaa'],
        descriptionHash: '0x2222222222222222222222222222222222222222222222222222222222222222',
        proposalId: '101',
        operationId: '0x3333333333333333333333333333333333333333333333333333333333333333',
        expectedOutcome: {
          projectActive: true,
        },
      },
      {
        slug: 'proposal2_deposit_idle_funds',
        title: 'Proposal 2',
        description: 'Proposal 2: Deposit 3.0 WETH into Aave',
        targets: [mockAddresses.treasury],
        values: ['0'],
        calldatas: ['0xbbbb'],
        descriptionHash: '0x4444444444444444444444444444444444444444444444444444444444444444',
        proposalId: '102',
        operationId: '0x5555555555555555555555555555555555555555555555555555555555555555',
        expectedOutcome: {
          treasuryLiquidWeth: '2000000000000000000',
        },
      },
    ],
  },
  evidence: {
    network: {
      name: 'sepolia',
      chainId: 11155111,
    },
    contracts: {
      CampusInnovationFundToken: mockAddresses.token,
      InnovationGovernor: mockAddresses.governor,
      TimelockController: mockAddresses.timelock,
      InnovationTreasury: mockAddresses.treasury,
      TreasuryOracle: mockAddresses.oracle,
      AaveWethAdapter: mockAddresses.adapter,
    },
    participants: {
      voterA: mockAddresses.voterA,
      voterB: mockAddresses.voterB,
      voterC: mockAddresses.voterC,
    },
    project: {
      projectId: '0x1111111111111111111111111111111111111111111111111111111111111111',
      recipient: mockAddresses.recipient,
    },
    seedState: {
      fundTreasury: {
        transactionHash: '0x6666666666666666666666666666666666666666666666666666666666666666',
      },
      selfDelegations: {
        voterA: { transactionHash: '0x7777777777777777777777777777777777777777777777777777777777777777' },
        voterB: { transactionHash: '0x8888888888888888888888888888888888888888888888888888888888888888' },
        voterC: { transactionHash: '0x9999999999999999999999999999999999999999999999999999999999999999' },
      },
    },
    proposals: {
      proposal1_approve_project: {
        proposalId: '101',
        transactions: {
          propose: '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1',
          votes: {
            voterA: '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa2',
          },
          queue: '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa3',
          execute: '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa4',
        },
      },
      proposal2_deposit_idle_funds: {
        proposalId: '102',
        transactions: {
          propose: '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb1',
          votes: {
            voterA: '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb2',
          },
          queue: '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb3',
          execute: '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb4',
        },
        snapshots: {
          postExecution: {
            treasury: {
              liquidWeth: '2000000000000000000',
              suppliedWeth: '3000000000000000000',
              totalManagedWeth: '5000000000000000000',
              navUsd: '10000000000000000000000',
              riskPolicy: {
                minLiquidReserveBps: 3000,
                maxSingleGrantBps: 2000,
                stalePriceThreshold: 3600,
              },
            },
          },
        },
      },
    },
    etherscanLinks: {
      addresses: {
        CampusInnovationFundToken: 'https://sepolia.etherscan.io/address/0x1000000000000000000000000000000000000001',
      },
      transactions: {
        'seedState.fundTreasury': 'https://sepolia.etherscan.io/tx/0x6666666666666666666666666666666666666666666666666666666666666666',
      },
    },
  },
  screenshots: {
    network: {
      name: 'sepolia',
      chainId: 11155111,
    },
    generatedAt: '2026-03-27T00:00:00Z',
    screenshots: [
      {
        id: 'proposal-1-lifecycle',
        caption: 'Proposal 1 lifecycle screenshot',
        reportSection: 'Sepolia deployment and evidence',
        expectedPath: 'evidence/screenshots/proposal-1-lifecycle.png',
        required: true,
        category: 'proposal',
      },
      {
        id: 'frontend-evidence-page',
        caption: 'Evidence page screenshot',
        reportSection: 'Appendix with addresses, tx hashes, and artifact index',
        expectedPath: 'evidence/screenshots/frontend-evidence-page.png',
        required: true,
        category: 'frontend',
      },
    ],
  },
};
