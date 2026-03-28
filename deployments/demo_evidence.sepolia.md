# Sepolia V2 Demo Evidence

- Network: `sepolia`
- Chain ID: `11155111`
- Funding members: `3`
- Funding proposals: `1`
- Active reputation total: `316`
- Project ID: `0x8f648b169ca5ff7384f0ef53d4dbf787d59183e01f4b9170598c0902e7717002`
- Project recipient: `0x219d5a2a550a3e8fCa237E5E30F16d5052A5655D`

## Contract Addresses

| Name | Address | Etherscan |
| --- | --- | --- |
| CampusInnovationFundToken | `0xCEd46b584d1adC32144fb53B30571bfc3E26Ac0A` | [link](https://sepolia.etherscan.io/address/0xCEd46b584d1adC32144fb53B30571bfc3E26Ac0A) |
| ReputationRegistry | `0xCdcE19D2E9bFDec7A47FEcD77Fb33E10d2D91aa0` | [link](https://sepolia.etherscan.io/address/0xCdcE19D2E9bFDec7A47FEcD77Fb33E10d2D91aa0) |
| HybridVotesAdapter | `0xB7eA2f70AafB10155b6182f4CFBD5DB7e40B6750` | [link](https://sepolia.etherscan.io/address/0xB7eA2f70AafB10155b6182f4CFBD5DB7e40B6750) |
| TimelockController | `0x24bee92d9a67D9D242266B7A771e27f9C783B706` | [link](https://sepolia.etherscan.io/address/0x24bee92d9a67D9D242266B7A771e27f9C783B706) |
| InnovationGovernor | `0xE520cd271c41aC8EEE57EFdF12D1cC8229113451` | [link](https://sepolia.etherscan.io/address/0xE520cd271c41aC8EEE57EFdF12D1cC8229113451) |
| TreasuryOracle | `0x8Cb05908b16057ce83BF7BE906b363BE0f94D1aA` | [link](https://sepolia.etherscan.io/address/0x8Cb05908b16057ce83BF7BE906b363BE0f94D1aA) |
| FundingRegistry | `0x02D01f71a5A33246453673E4d5C8a1A4C43c3508` | [link](https://sepolia.etherscan.io/address/0x02D01f71a5A33246453673E4d5C8a1A4C43c3508) |
| AaveWethAdapter | `0x2351A29BBF20Db7cF1266A0AC0AC2dBb25cdE6F8` | [link](https://sepolia.etherscan.io/address/0x2351A29BBF20Db7cF1266A0AC0AC2dBb25cdE6F8) |
| InnovationTreasury | `0x3f3C8D1C6CE2ff332C75bC56fB059B62059d39d6` | [link](https://sepolia.etherscan.io/address/0x3f3C8D1C6CE2ff332C75bC56fB059B62059d39d6) |
| WETH | `0xC558DBdd856501FCd9aaF1E62eae57A9F0629a3c` | [link](https://sepolia.etherscan.io/address/0xC558DBdd856501FCd9aaF1E62eae57A9F0629a3c) |
| ChainlinkEthUsdFeed | `0x694AA1769357215DE4FAC081bf1f309aDC325306` | [link](https://sepolia.etherscan.io/address/0x694AA1769357215DE4FAC081bf1f309aDC325306) |
| AavePool | `0x6Ae43d3271ff6888e7Fc43Fd7321a503ff738951` | [link](https://sepolia.etherscan.io/address/0x6Ae43d3271ff6888e7Fc43Fd7321a503ff738951) |
| AaveAWeth | `0x5b071b590a59395fE4025A0Ccc1FcC931AAc1830` | [link](https://sepolia.etherscan.io/address/0x5b071b590a59395fE4025A0Ccc1FcC931AAc1830) |

## Seed State

- Bootstrap proposal: `99491819197843310350441332683670700630451918718995327786362415253155581079780` with description hash `0x7add1a6ca8aaa291c44cb6e1adba94c3e344202a49ff0a50564d557c28fee49e`
- Treasury seed target: `3000000000000000000`

## Funding Workflow Summary

### Proposal 1

- Description: `Proposal 1: Approve Smart Recycling Kiosk project`
- Governor proposal ID: `55522379004979784243154073825652185598607396307460019166722436029771493969218`
- Funding proposal ID: `1`
- Project ID: `0x8f648b169ca5ff7384f0ef53d4dbf787d59183e01f4b9170598c0902e7717002`
- Final state: `Executed`

### Proposal 2

- Description: `Proposal 2: Deposit 0.6 WETH into Aave`
- Governor proposal ID: `21097311793780875520220966102813492745851725950080990582918625528967233070817`
- Final state: `Executed`

### Proposal 3

- Description: `Proposal 3: Withdraw 0.1 WETH and release milestone 0`
- Governor proposal ID: `111399561018444129992237408883692073814110890150110607660428901138111338772838`
- Funding proposal ID: `1`
- Project ID: `0x8f648b169ca5ff7384f0ef53d4dbf787d59183e01f4b9170598c0902e7717002`
- Milestone index: `0`
- Final state: `Executed`

## Funding State Snapshot

- Project `0x8f648b169ca5ff7384f0ef53d4dbf787d59183e01f4b9170598c0902e7717002` released `100000000000000000` / `200000000000000000` WETH, next milestone `1`, status `Active`.
- Member `0x9F6f568626a1254111Bf300dB87bED0DEcEdBA4B` active=`True` reputation=`108`.
- Member `0x9460ABA95c0a699D28f7Db1709095431C496dC04` active=`True` reputation=`104`.
- Member `0xCfE3BCAba47C85F59d6127d289984408e8F0A716` active=`True` reputation=`104`.

## Transaction Hash Table

| Section | Step | Transaction Hash | Etherscan |
| --- | --- | --- | --- |
| Deployment | deployToken | `35f5385fd5e3fa1adea1a379a7df0ab5183913be631fd577e83dbb55e9c0026d` | [link](https://sepolia.etherscan.io/tx/35f5385fd5e3fa1adea1a379a7df0ab5183913be631fd577e83dbb55e9c0026d) |
| Deployment | deployTimelock | `b40bd4348f75f32028e78e71ff900d01dce75a99477bd973276161985f142c73` | [link](https://sepolia.etherscan.io/tx/b40bd4348f75f32028e78e71ff900d01dce75a99477bd973276161985f142c73) |
| Deployment | deployReputationRegistry | `d26106894b97c1a8c14d83019de977082bbcbe4d2336b16cf71fe99d1bf469e1` | [link](https://sepolia.etherscan.io/tx/d26106894b97c1a8c14d83019de977082bbcbe4d2336b16cf71fe99d1bf469e1) |
| Deployment | deployHybridVotesAdapter | `c3ac56b71368a447acd54472851e491ec3fdf9424ef1d681e0a83bde90e0435c` | [link](https://sepolia.etherscan.io/tx/c3ac56b71368a447acd54472851e491ec3fdf9424ef1d681e0a83bde90e0435c) |
| Deployment | deployGovernor | `4ccdefe3360aea02b45b4db814fe55cd02175a2015887a059e0bcb6d56b41997` | [link](https://sepolia.etherscan.io/tx/4ccdefe3360aea02b45b4db814fe55cd02175a2015887a059e0bcb6d56b41997) |
| Deployment | mintVoterA | `2c8326b0372f43bda2648fccfaf362073818bb1cb5beb62b22a7bdfb2832a32b` | [link](https://sepolia.etherscan.io/tx/2c8326b0372f43bda2648fccfaf362073818bb1cb5beb62b22a7bdfb2832a32b) |
| Deployment | mintVoterB | `301581c2762def44fe5877e933602d853e69c47aee732409cbc65c422c348854` | [link](https://sepolia.etherscan.io/tx/301581c2762def44fe5877e933602d853e69c47aee732409cbc65c422c348854) |
| Deployment | mintVoterC | `3210288a8e3b5a169acae3bc34023d55dad2dc31cdf92da2e5615b2afd2e6235` | [link](https://sepolia.etherscan.io/tx/3210288a8e3b5a169acae3bc34023d55dad2dc31cdf92da2e5615b2afd2e6235) |
| Deployment | mintGovernanceReserve | `4e69b8e6defdc6ce2a47ca8913b666df8769000d2d85eb649b8e329de89bea00` | [link](https://sepolia.etherscan.io/tx/4e69b8e6defdc6ce2a47ca8913b666df8769000d2d85eb649b8e329de89bea00) |
| Deployment | grantProposerRole | `8dbbdb4526c8f6890209c2fb92d37ab1d38538f5b931a5a8eb6fa82651ee6c6e` | [link](https://sepolia.etherscan.io/tx/8dbbdb4526c8f6890209c2fb92d37ab1d38538f5b931a5a8eb6fa82651ee6c6e) |
| Deployment | grantCancellerRole | `ae830e8b16f2ce90974e760ee28351bb299a07e0fc7f02d6c090e6dd6355db34` | [link](https://sepolia.etherscan.io/tx/ae830e8b16f2ce90974e760ee28351bb299a07e0fc7f02d6c090e6dd6355db34) |
| Deployment | renounceAdminRole | `961149b1c2bf3911d95e6dc510e4ceaf4b6e62b8730529930679e3a5fce0ea33` | [link](https://sepolia.etherscan.io/tx/961149b1c2bf3911d95e6dc510e4ceaf4b6e62b8730529930679e3a5fce0ea33) |
| Deployment | renounceTokenOwnership | `01b63d56eae415a5b6098d27f9531e885612ffdda223e3c911955c69249983cb` | [link](https://sepolia.etherscan.io/tx/01b63d56eae415a5b6098d27f9531e885612ffdda223e3c911955c69249983cb) |
| Deployment | deployTreasuryOracle | `400c4a4843dcf7de2433ad679ed094e784aa195f51cfe196f79a747483e288bb` | [link](https://sepolia.etherscan.io/tx/400c4a4843dcf7de2433ad679ed094e784aa195f51cfe196f79a747483e288bb) |
| Deployment | deployFundingRegistry | `9b76292ea12dd4cebae6864e03257183eab31da61a9f81aebf27b238bd99f93a` | [link](https://sepolia.etherscan.io/tx/9b76292ea12dd4cebae6864e03257183eab31da61a9f81aebf27b238bd99f93a) |
| Deployment | deployAaveWethAdapter | `27b5b4350d3270c1f11dc5d4d731e5bb5b27898f95972ee30495bdd8521cfc0d` | [link](https://sepolia.etherscan.io/tx/27b5b4350d3270c1f11dc5d4d731e5bb5b27898f95972ee30495bdd8521cfc0d) |
| Deployment | deployInnovationTreasury | `251654e6d1eb51ad745b88307dfd46013efd47735a9c184fb2d9152ef83746f1` | [link](https://sepolia.etherscan.io/tx/251654e6d1eb51ad745b88307dfd46013efd47735a9c184fb2d9152ef83746f1) |

## Manual Verification Notes

- Member bootstrap is executed through Governor and Timelock, not through a privileged direct write.
- Proposal 1 batches FundingRegistry approval and Treasury project activation.
- Proposal 2 demonstrates idle WETH deployment into Aave without changing funding workflow state.
- Proposal 3 captures milestone claim execution, Treasury release, and FundingRegistry milestone release.
- Funding proposal vote participation settlement is exported as a standalone post-Proposal-1 transaction.
- Milestone claim vote participation settlement is exported as a standalone post-Proposal-3 transaction.
- The funding_state snapshot records the proposer milestone-release reward and the final settled voter reputation values.
- Browser screenshots should be captured using the checklist generated alongside this Markdown file.
