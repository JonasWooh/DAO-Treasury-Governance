# Campus Innovation Fund DAO

![Solidity](https://img.shields.io/badge/Solidity-0.8.24-2f2f2f?logo=solidity)
![Python](https://img.shields.io/badge/Python-Automation-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18.3-149ECA?logo=react&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-7.1-646CFF?logo=vite&logoColor=white)
![Network](https://img.shields.io/badge/Network-Sepolia-6D28D9)

This repository is the handoff-ready working tree for a Sepolia deployment of a campus grant DAO. It combines hybrid governance, milestone-based funding, treasury policy, Chainlink valuation, Aave reserve management, evidence export, and a React frontend into one reproducible project.

The main audience for this README is a collaborator who needs to answer three questions quickly:

1. What does the system do?
2. Where is the source of truth?
3. Which commands and files matter for normal use?

See `docs/repository-layout.md` for the directory-by-directory map.

## At A Glance

| Area | Current implementation |
| --- | --- |
| Governance | ERC20Votes token plus reputation-weighted voting through `HybridVotesAdapter` |
| Treasury | Timelocked WETH treasury with Chainlink NAV checks and Aave reserve deployment |
| Workflow | Proposal intake, project activation, milestone claims, vote settlement, and payout tracking |
| Frontend | React + Vite application with overview, proposals, project, treasury, submission, and evidence routes |
| Deliverables | Checked-in Sepolia manifests, screenshot package, workbook, QA summaries, and final PDF report |

## What This Repository Contains

- Hybrid voting built from an ERC20Votes token plus a reputation registry
- Governor plus timelock execution for DAO proposals on Sepolia
- A funding workflow for proposal intake, project activation, milestone claims, and treasury releases
- Treasury valuation through Chainlink `ETH / USD`
- Idle WETH management through an Aave adapter
- Contract-side safety checks for reentrancy, stale or incomplete oracle data, strict balance reconciliation, disabled ownership handoff on timelocked modules, and workflow state validation
- Repository-side secret hygiene with repo scanning, safer CLI secret handling, git hooks, and CI rechecks
- A React app that exposes governance, project, treasury, submission, and evidence views
- A Python deliverables pipeline that exports manifests, workbook artifacts, screenshots, and the final PDF report

## How the System Fits Together

The core on-chain flow is:

`CampusInnovationFundToken -> HybridVotesAdapter -> InnovationGovernor -> TimelockController -> InnovationTreasury`

Supporting modules add state and integrations around that path:

- `ReputationRegistry` stores member and reputation checkpoints used by the hybrid voting adapter
- `FundingRegistry` stores workflow state for submissions, approved projects, milestone claims, evidence URIs, and payout tracking
- `TreasuryOracle` wraps the Chainlink `ETH / USD` feed and enforces freshness checks
- `AaveWethAdapter` gives the treasury a constrained interface for supplying and withdrawing WETH on Aave
- `frontend/src/generated/` and `frontend/public/runtime/` bridge authoritative manifests into the frontend and evidence views

## Where To Start Reading

If you are new to the repository, read in this order:

1. Contracts
   - `src/governance/InnovationGovernor.sol`
   - `src/governance/HybridVotesAdapter.sol`
   - `src/governance/ReputationRegistry.sol`
   - `src/funding/FundingRegistry.sol`
   - `src/treasury/InnovationTreasury.sol`
   - `src/oracle/TreasuryOracle.sol`
   - `src/adapters/AaveWethAdapter.sol`
2. Deployment and demo automation
   - `scripts/deploy_governance_spine.py`
   - `scripts/deploy_treasury_stack.py`
   - `scripts/seed_sepolia_demo_state.py`
   - `scripts/run_sepolia_demo_proposals.py`
   - `scripts/export_sepolia_evidence.py`
3. Frontend routes
   - `frontend/src/App.tsx`
   - `frontend/src/pages/OverviewPage.tsx`
   - `frontend/src/pages/ProposalsPage.tsx`
   - `frontend/src/pages/ProposalDetailPage.tsx`
   - `frontend/src/pages/ProjectDetailPage.tsx`
   - `frontend/src/pages/TreasuryPage.tsx`
   - `frontend/src/pages/EvidencePage.tsx`
4. Checked-in manifests and deliverables
   - `deployments/deployments.sepolia.json`
   - `deployments/demo_evidence.sepolia.md`
   - `frontend/src/generated/frontend.config.sepolia.json`
   - `excel/treasury_analysis.sepolia.xlsx`
   - `reports/final_report.sepolia.pdf`

## Current Checked-In Sepolia State

The current checked-in deployment manifest is `deployments/deployments.sepolia.json`.

Core contract addresses:

| Contract | Address |
| --- | --- |
| `CampusInnovationFundToken` | `0xCEd46b584d1adC32144fb53B30571bfc3E26Ac0A` |
| `ReputationRegistry` | `0xCdcE19D2E9bFDec7A47FEcD77Fb33E10d2D91aa0` |
| `HybridVotesAdapter` | `0xB7eA2f70AafB10155b6182f4CFBD5DB7e40B6750` |
| `TimelockController` | `0x24bee92d9a67D9D242266B7A771e27f9C783B706` |
| `InnovationGovernor` | `0xE520cd271c41aC8EEE57EFdF12D1cC8229113451` |
| `TreasuryOracle` | `0x8Cb05908b16057ce83BF7BE906b363BE0f94D1aA` |
| `FundingRegistry` | `0x02D01f71a5A33246453673E4d5C8a1A4C43c3508` |
| `AaveWethAdapter` | `0x2351A29BBF20Db7cF1266A0AC0AC2dBb25cdE6F8` |
| `InnovationTreasury` | `0x3f3C8D1C6CE2ff332C75bC56fB059B62059d39d6` |

Key checked-in deliverables already present:

- `deployments/demo_evidence.sepolia.md`
- `frontend/src/generated/frontend.config.sepolia.json`
- `frontend/public/runtime/*.json`
- `analysis/coverage/coverage-summary.md`
- `analysis/gas/gas-report.md`
- `analysis/static/slither-summary.md`
- `excel/treasury_analysis.sepolia.xlsx`
- `reports/final_report.sepolia.pdf`
- `evidence/screenshots/screenshot-manifest.sepolia.json`

For full transaction evidence, scenario details, and frontend runtime wiring, start with:

- `deployments/demo_evidence.sepolia.md`
- `deployments/demo_evidence.sepolia.json`
- `deployments/proposal_scenarios.sepolia.json`
- `frontend/src/generated/frontend.config.sepolia.json`

## Security Guardrails

The current repository includes both contract-level and repository-level safety checks.

Contract-side protections:

- `InnovationTreasury` uses `ReentrancyGuard` on milestone release and Aave reserve movement paths, rejects stale or malformed oracle data before NAV-sensitive operations, and hard-disables direct ownership transfer and renounce flows
- `AaveWethAdapter` is restricted to the treasury, uses `nonReentrant`, and performs strict before-and-after balance reconciliation around `transferFrom`, `supply`, and `withdraw`
- `TreasuryOracle` validates Chainlink round completeness, rejects zero or stale timestamps, and normalizes decimals before returning values to the treasury layer
- `FundingRegistry` rejects invalid proposal and milestone state transitions, checks linked governor proposal states, and prevents duplicate vote-participation settlement

Repository and automation protections:

- `scripts/check_repo_secrets.py` scans both the worktree and git history for sensitive paths, suspicious secret assignments, and exact matches to locally configured secret values
- `scripts/cli_security.py` is used by deployment and live-demo scripts to prefer environment variables over CLI secrets and to warn when private keys are passed on the command line
- `scripts/install_git_hooks.py` enables `.githooks/pre-commit`, which runs the repository secret scan before each commit
- `.github/workflows/secret-scan.yml` reruns the same scanner in CI on pushes and pull requests
- `scripts/run_slither_analysis.py` verifies the pinned Windows `solc.exe` checksum before static analysis runs
- `docs/push-security-checklist.md` is the manual pre-push checklist for generated attachments and secret hygiene

## Standard Workflows

### 1. Environment Setup

Clone with submodules or initialize them after checkout:

```powershell
git submodule update --init --recursive
```

Create and activate the Python and Node-ready development environment:

```powershell
conda env create -f environment.yml
conda activate cif_dao_env
npm --prefix frontend install
```

Prepare the local environment templates:

```powershell
Copy-Item config\sepolia.env.example config\sepolia.env
Copy-Item frontend\.env.example frontend\.env
```

Important: the Python scripts read from the live shell environment, not directly from `config/sepolia.env`. Keep `config/sepolia.env` as your local reference file, then load the values into the current shell before running Sepolia scripts.

One PowerShell-friendly way to load `config\sepolia.env` into the current session is:

```powershell
Get-Content config\sepolia.env | ForEach-Object {
  if ($_ -match '^\s*([^#=]+)=(.*)$') {
    Set-Item -Path ("Env:" + $matches[1].Trim()) -Value $matches[2].Trim()
  }
}
```

The frontend uses `frontend/.env` through Vite, while the Python deployment and demo scripts use normal environment variables from the shell.

### Environment Variables

`config/sepolia.env.example` is the template for the Sepolia workflow variables:

| Variable | Used by | Purpose |
| --- | --- | --- |
| `SEPOLIA_RPC_URL` | deployment, demo, verification scripts | RPC endpoint for Sepolia |
| `SEPOLIA_PRIVATE_KEY` | `deploy_governance_spine.py`, `deploy_treasury_stack.py` | deployer key for the two deployment stages |
| `CIF_VOTER_A` | governance-spine deploy | address that receives the first seeded governance allocation |
| `CIF_VOTER_B` | governance-spine deploy | address that receives the second seeded governance allocation |
| `CIF_VOTER_C` | governance-spine deploy | address that receives the third seeded governance allocation |
| `CIF_GOVERNANCE_RESERVE` | governance-spine deploy | reserve recipient for the remaining initial token allocation |
| `CIF_TIMELOCK` | treasury-stack deploy | timelock address from the governance deployment |
| `CIF_GOVERNOR` | treasury-stack deploy | governor address from the governance deployment |
| `CIF_REPUTATION_REGISTRY` | treasury-stack deploy | reputation registry address from the governance deployment |
| `CIF_TREASURY_FUNDER_PRIVATE_KEY` | demo seeding | account used to fund the treasury during the Sepolia demo setup |
| `CIF_VOTER_A_PRIVATE_KEY` | demo seeding and proposal execution | voter A signer used for delegation and votes |
| `CIF_VOTER_B_PRIVATE_KEY` | demo seeding and proposal execution | voter B signer used for delegation and votes |
| `CIF_VOTER_C_PRIVATE_KEY` | demo seeding and proposal execution | voter C signer used for delegation and votes |
| `CIF_PROJECT_RECIPIENT` | demo seeding and proposal execution | recipient address used by the sample project and milestone payout flow |

Notes:

- `CIF_GOVERNOR` and `CIF_REPUTATION_REGISTRY` are required by `deploy_treasury_stack.py` even though they are filled after the governance-spine deployment step.
- The easiest source for `CIF_TIMELOCK`, `CIF_GOVERNOR`, and `CIF_REPUTATION_REGISTRY` is `deployments/deployments.sepolia.json` after `deploy_governance_spine.py` completes.
- The scripts now prefer environment variables over CLI secret flags and warn if you pass private keys directly on the command line.

`frontend/.env.example` is the template for the frontend-only variables:

| Variable | Purpose |
| --- | --- |
| `VITE_SEPOLIA_RPC_URL` | RPC endpoint used by the frontend for wallet-connected reads and transactions |
| `VITE_CHAIN_ID` | chain id expected by the frontend, currently `11155111` for Sepolia |

### Push Safety

Before committing or pushing:

```powershell
python scripts/install_git_hooks.py
python scripts/check_repo_secrets.py --skip-history
```

Before a real push, run the full worktree-plus-history scan:

```powershell
python scripts/check_repo_secrets.py
```

Security rules for this repository:

- keep real secrets only in local env files such as `config/sepolia.env` and `frontend/.env`
- prefer environment variables over `--private-key` style CLI flags because shells persist history
- manually review new screenshots, PDFs, XLSX files, and ad hoc JSON exports before staging them
- treat the checked-in Sepolia addresses and transaction hashes as public demo data; the matching private keys must stay disposable test-only accounts

Deployment and live-demo scripts now warn when secrets are passed via CLI flags instead of environment variables.

See `docs/push-security-checklist.md` for the full push checklist and the pinned `solc.exe` checksum used by Slither on Windows.

### 2. Compile And Test

Install the pinned Solidity compiler and rebuild artifacts:

```powershell
python scripts/compile_contracts.py --install-solc
python scripts/compile_contracts.py --clean
```

Run Python tests:

```powershell
python -m unittest discover -s test -p "test_*.py" -v
```

Run frontend tests and produce a production build:

```powershell
npm --prefix frontend run test
npm --prefix frontend run build
```

### 3. Run The Frontend Locally

Start the development server:

```powershell
npm --prefix frontend run dev
```

Open the local URL printed by Vite, typically `http://localhost:5173`.

The app reads its checked-in runtime data from:

- `frontend/src/generated/frontend.config.sepolia.json`
- `frontend/public/runtime/*.json`

If you regenerate manifests or ABI files, run `python scripts/export_frontend_bundle.py` before refreshing the frontend.

For a local production-style preview:

```powershell
npm --prefix frontend run build
npm --prefix frontend run preview
```

### 4. Deploy To Sepolia

Deploy the governance spine first, then the treasury stack:

```powershell
python scripts/deploy_governance_spine.py
python scripts/deploy_treasury_stack.py
```

The checked-in deployment manifest is written to `deployments/deployments.sepolia.json`.

### 5. Seed Demo State And Execute Governance Scenarios

Seed the project, treasury, and voter state used by the live demo:

```powershell
python scripts/seed_sepolia_demo_state.py
```

Run the staged governance proposals:

```powershell
python scripts/run_sepolia_demo_proposals.py
```

Export evidence tables and checklist material:

```powershell
python scripts/export_sepolia_evidence.py
```

These steps update the authoritative Sepolia runtime manifests under `deployments/`.

### 6. Export The Frontend Bundle

Regenerate frontend ABI files, config, and runtime bundle copies from authoritative manifests:

```powershell
python scripts/export_frontend_bundle.py
```

This updates:

- `frontend/src/generated/abi/*.json`
- `frontend/src/generated/frontend.config.sepolia.json`
- `frontend/public/runtime/*.json`

### 7. Generate Workbook, Report, And Submission Checks

Generate the treasury analysis workbook:

```powershell
python scripts/generate_treasury_workbook.py
```

Generate the final PDF report:

```powershell
python scripts/generate_final_report.py
```

Validate the final submission package:

```powershell
python scripts/validate_submission_package.py
```

If the frontend build is already current and you only want a quick package re-check:

```powershell
python scripts/validate_submission_package.py --skip-frontend-build
```

### 8. Etherscan Verification Helpers

Regenerate the Standard JSON Input payload used for Etherscan verification:

```powershell
python scripts/export_etherscan_standard_input.py --pretty
```

Run verification through the Etherscan API helper:

```powershell
$env:ETHERSCAN_API_KEY="your-api-key"
python scripts/verify_etherscan_contracts.py --deployer-address <deployment-eoa>
```

For a targeted contract-only run:

```powershell
python scripts/verify_etherscan_contracts.py --deployer-address <deployment-eoa> --contracts CampusInnovationFundToken
```

Helper outputs are written under `output/etherscan/`.

## Frontend Route Map

The frontend route table is defined in `frontend/src/App.tsx`.

| Route | Page | Purpose |
| --- | --- | --- |
| `/` | `OverviewPage` | High-level project and proposal summary |
| `/proposals` | `ProposalsPage` | Proposal pipeline and governance timeline |
| `/proposals/:proposalId` | `ProposalDetailPage` | Proposal state, evidence, votes, and execution context |
| `/projects/:projectId` | `ProjectDetailPage` | Project-level state after proposal approval |
| `/submit` | `SubmitProposalPage` | Submission walkthrough and workflow explanation |
| `/claims/:proposalId/:milestoneIndex` | `MilestoneClaimPage` | Milestone claim submission and review context |
| `/treasury` | `TreasuryPage` | Liquid WETH, Aave-supplied WETH, NAV, and oracle view |
| `/evidence` | `EvidencePage` | Contract registry, execution log, and report support assets |

## Source Of Truth Vs Generated Outputs

Source-of-truth code and configuration:

- `src/` for Solidity contracts and interfaces
- `scripts/` for deployment, demo execution, reporting, validation, and verification logic
- `frontend/src/` for application code, except for `frontend/src/generated/`
- `config/` for checked-in example environment and protocol configuration
- `deployments/` for checked-in Sepolia manifests after deployment and demo runs

Generated outputs that are intentionally checked in for grading and handoff:

- `artifacts/` compiled Solidity outputs
- `frontend/src/generated/` generated ABI and frontend config inputs
- `frontend/public/runtime/` runtime bundle copies consumed by the app
- `analysis/` QA outputs such as coverage, gas, and static analysis summaries
- `excel/` workbook deliverables
- `reports/` final PDF report deliverables
- `evidence/screenshots/` screenshot manifest, required screenshots, and supporting raw captures
- `output/` helper outputs such as Etherscan payloads and Playwright logs

## Notes On Project Documents

- `DAO Prototype Plan on Sepolia.md` is the baseline plan and assignment-oriented design note.
- `Refine.md` is a historical refinement note rather than the primary onboarding document. Use it only as supplemental context.

## License

This repository is licensed under the MIT License. See `LICENSE` for details.
