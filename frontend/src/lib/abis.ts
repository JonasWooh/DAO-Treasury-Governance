import aaveWethAdapterArtifact from '../generated/abi/AaveWethAdapter.json';
import campusInnovationFundTokenArtifact from '../generated/abi/CampusInnovationFundToken.json';
import innovationGovernorArtifact from '../generated/abi/InnovationGovernor.json';
import innovationTreasuryArtifact from '../generated/abi/InnovationTreasury.json';
import treasuryOracleArtifact from '../generated/abi/TreasuryOracle.json';

export const contractAbis = {
  CampusInnovationFundToken: campusInnovationFundTokenArtifact.abi,
  InnovationGovernor: innovationGovernorArtifact.abi,
  InnovationTreasury: innovationTreasuryArtifact.abi,
  TreasuryOracle: treasuryOracleArtifact.abi,
  AaveWethAdapter: aaveWethAdapterArtifact.abi,
} as const;