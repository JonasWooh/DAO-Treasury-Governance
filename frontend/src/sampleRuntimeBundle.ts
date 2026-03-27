import type { RuntimeBundle } from './types';

export const mockAddresses = {
  token: '0x1000000000000000000000000000000000000001',
  reputation: '0x1000000000000000000000000000000000000002',
  hybrid: '0x1000000000000000000000000000000000000003',
  governor: '0x1000000000000000000000000000000000000004',
  funding: '0x1000000000000000000000000000000000000005',
  timelock: '0x1000000000000000000000000000000000000006',
  treasury: '0x1000000000000000000000000000000000000007',
  oracle: '0x1000000000000000000000000000000000000008',
  adapter: '0x1000000000000000000000000000000000000009',
  weth: '0x1000000000000000000000000000000000000010',
  chainlink: '0x1000000000000000000000000000000000000011',
  aavePool: '0x1000000000000000000000000000000000000012',
  aWeth: '0x1000000000000000000000000000000000000013',
  voterA: '0x2000000000000000000000000000000000000001',
  voterB: '0x2000000000000000000000000000000000000002',
  voterC: '0x2000000000000000000000000000000000000003',
  recipient: '0x2000000000000000000000000000000000000004',
};

const fundingProjectId = '0x1111111111111111111111111111111111111111111111111111111111111111';

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
      ReputationRegistry: mockAddresses.reputation,
      HybridVotesAdapter: mockAddresses.hybrid,
      InnovationGovernor: mockAddresses.governor,
      FundingRegistry: mockAddresses.funding,
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
      fundingState: '/runtime/funding_state.sepolia.json',
      screenshotManifest: '/runtime/screenshot-manifest.sepolia.json',
    },
    etherscanBaseUrl: 'https://sepolia.etherscan.io',
    note: 'Preview data is active because the published Sepolia manifests have not been exported into the frontend bundle yet.',
  },
  deployments: {
    network: {
      name: 'sepolia',
      chainId: 11155111,
    },
    contracts: {
      CampusInnovationFundToken: mockAddresses.token,
      ReputationRegistry: mockAddresses.reputation,
      HybridVotesAdapter: mockAddresses.hybrid,
      InnovationGovernor: mockAddresses.governor,
      FundingRegistry: mockAddresses.funding,
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
      projectId: fundingProjectId,
      recipient: mockAddresses.recipient,
      maxBudgetWeth: '200000000000000000',
      milestoneCount: 2,
      milestonePayoutsWeth: {
        milestone0: '100000000000000000',
        milestone1: '100000000000000000',
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
    ],
  },
  evidence: {
    network: {
      name: 'sepolia',
      chainId: 11155111,
    },
    contracts: {
      CampusInnovationFundToken: mockAddresses.token,
      ReputationRegistry: mockAddresses.reputation,
      HybridVotesAdapter: mockAddresses.hybrid,
      InnovationGovernor: mockAddresses.governor,
      FundingRegistry: mockAddresses.funding,
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
      projectId: fundingProjectId,
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
      bootstrapMembers: {
        transactions: {
          propose: '0x1111111111111111111111111111111111111111111111111111111111111111',
          votes: {
            voterA: '0x1212121212121212121212121212121212121212121212121212121212121212',
            voterB: '0x1313131313131313131313131313131313131313131313131313131313131313',
            voterC: '0x1414141414141414141414141414141414141414141414141414141414141414',
          },
          queue: '0x1515151515151515151515151515151515151515151515151515151515151515',
          execute: '0x1616161616161616161616161616161616161616161616161616161616161616',
        },
      },
    },
    proposals: {
      proposal1_approve_project: {
        proposalId: '101',
        transactions: {
          submitFundingProposal: '0x1717171717171717171717171717171717171717171717171717171717171717',
          linkGovernorProposal: '0x1818181818181818181818181818181818181818181818181818181818181818',
          propose: '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1',
          votes: {
            voterA: '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa2',
            voterB: '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa5',
            voterC: '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa6',
          },
          queue: '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa3',
          execute: '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa4',
          settleFundingVoteParticipation: '0x1919191919191919191919191919191919191919191919191919191919191919',
        },
      },
      proposal2_deposit_idle_funds: {
        proposalId: '102',
        transactions: {
          propose: '0x2020202020202020202020202020202020202020202020202020202020202020',
          votes: {
            voterA: '0x2121212121212121212121212121212121212121212121212121212121212121',
            voterB: '0x2222222222222222222222222222222222222222222222222222222222222222',
            voterC: '0x2323232323232323232323232323232323232323232323232323232323232323',
          },
          queue: '0x2424242424242424242424242424242424242424242424242424242424242424',
          execute: '0x2525252525252525252525252525252525252525252525252525252525252525',
        },
      },
      proposal3_release_milestone: {
        proposalId: '103',
        transactions: {
          submitMilestoneClaim: '0x2626262626262626262626262626262626262626262626262626262626262626',
          linkMilestoneGovernorProposal: '0x2727272727272727272727272727272727272727272727272727272727272727',
          propose: '0x2828282828282828282828282828282828282828282828282828282828282828',
          votes: {
            voterA: '0x2929292929292929292929292929292929292929292929292929292929292929',
            voterB: '0x3030303030303030303030303030303030303030303030303030303030303030',
            voterC: '0x3131313131313131313131313131313131313131313131313131313131313131',
          },
          queue: '0x3232323232323232323232323232323232323232323232323232323232323232',
          execute: '0x3333333333333333333333333333333333333333333333333333333333333333',
          settleMilestoneVoteParticipation: '0x3434343434343434343434343434343434343434343434343434343434343434',
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
  fundingState: {
    network: {
      name: 'sepolia',
      chainId: 11155111,
    },
    contracts: {
      FundingRegistry: mockAddresses.funding,
      ReputationRegistry: mockAddresses.reputation,
      HybridVotesAdapter: mockAddresses.hybrid,
    },
    generatedAt: '2026-03-27T00:00:00Z',
    members: [
      {
        account: mockAddresses.voterA,
        isRegistered: true,
        isActive: true,
        currentReputation: '108',
      },
      {
        account: mockAddresses.voterB,
        isRegistered: true,
        isActive: true,
        currentReputation: '104',
      },
      {
        account: mockAddresses.voterC,
        isRegistered: true,
        isActive: true,
        currentReputation: '104',
      },
    ],
    proposals: [
      {
        proposalId: '1',
        proposer: mockAddresses.voterA,
        recipient: mockAddresses.recipient,
        title: 'Student robotics lab expansion',
        metadataURI: 'ipfs://proposal-metadata',
        requestedFundingWeth: '200000000000000000',
        milestoneCount: 2,
        status: 'Approved',
        governorProposalId: '101',
        projectId: fundingProjectId,
      },
    ],
    projects: [
      {
        projectId: fundingProjectId,
        sourceProposalId: '1',
        recipient: mockAddresses.recipient,
        approvedBudgetWeth: '200000000000000000',
        releasedWeth: '100000000000000000',
        nextClaimableMilestone: 1,
        status: 'Active',
      },
    ],
    milestones: [
      {
        proposalId: '1',
        projectId: fundingProjectId,
        milestoneIndex: 0,
        description: 'Install robotics hardware',
        amountWeth: '100000000000000000',
        evidenceURI: 'ipfs://milestone-0',
        state: 'Released',
        claimGovernorProposalId: '103',
      },
      {
        proposalId: '1',
        projectId: fundingProjectId,
        milestoneIndex: 1,
        description: 'Commission the expanded lab',
        amountWeth: '100000000000000000',
        evidenceURI: '',
        state: 'OpenForClaim',
        claimGovernorProposalId: '0',
      },
    ],
    reputationSummary: {
      totalActiveReputation: '316',
      activeMemberCount: 3,
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
