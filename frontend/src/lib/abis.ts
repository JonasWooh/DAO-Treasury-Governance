import aaveWethAdapterArtifact from '../generated/abi/AaveWethAdapter.json';
import campusInnovationFundTokenArtifact from '../generated/abi/CampusInnovationFundToken.json';
import fundingRegistryArtifact from '../generated/abi/FundingRegistry.json';
import hybridVotesAdapterArtifact from '../generated/abi/HybridVotesAdapter.json';
import innovationGovernorArtifact from '../generated/abi/InnovationGovernor.json';
import innovationTreasuryArtifact from '../generated/abi/InnovationTreasury.json';
import reputationRegistryArtifact from '../generated/abi/ReputationRegistry.json';
import treasuryOracleArtifact from '../generated/abi/TreasuryOracle.json';

export const contractAbis = {
  CampusInnovationFundToken: campusInnovationFundTokenArtifact.abi,
  ReputationRegistry: reputationRegistryArtifact.abi,
  HybridVotesAdapter: hybridVotesAdapterArtifact.abi,
  InnovationGovernor: innovationGovernorArtifact.abi,
  FundingRegistry: fundingRegistryArtifact.abi,
  InnovationTreasury: innovationTreasuryArtifact.abi,
  TreasuryOracle: treasuryOracleArtifact.abi,
  AaveWethAdapter: aaveWethAdapterArtifact.abi,
} as const;
