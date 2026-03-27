# Campus Innovation Fund DAO

Student-run treasury governance on Sepolia, with a full DAO stack covering hybrid token-plus-reputation voting, milestone-based funding workflows, timelocked treasury execution, Chainlink valuation, Aave reserve management, QA automation, and a React front end.

![Solidity](https://img.shields.io/badge/Solidity-0.8.24-1f2937?logo=solidity)
![Foundry](https://img.shields.io/badge/Foundry-Enabled-b45309)
![React](https://img.shields.io/badge/React-18.3.1-0f766e?logo=react)
![Vite](https://img.shields.io/badge/Vite-7.1-1d4ed8?logo=vite)
![Network](https://img.shields.io/badge/Network-Sepolia-065f46)

## Overview

This repository implements a realistic campus grant DAO rather than a minimal voting demo. Members govern a student innovation treasury, submit and review project proposals, approve milestone-based funding, enforce reserve rules, and manage idle WETH through Aave on Sepolia.

The current repository combines the original treasury-governance spine with a V2 workflow layer for proposal intake, project tracking, milestone claims, and hybrid governance.

- `CampusInnovationFundToken` provides the ERC20Votes token base
- `ReputationRegistry` tracks active members, checkpoints, and reputation changes
- `HybridVotesAdapter` combines token voting power and reputation into a Governor-compatible voting source
- `InnovationGovernor` and `TimelockController` enforce proposal, voting, queue, and execution flow
- `FundingRegistry` manages proposal, project, and milestone workflow state
- `InnovationTreasury` applies constrained treasury policy and milestone release rules
- `TreasuryOracle` tracks treasury value through Chainlink `ETH/USD`
- `AaveWethAdapter` demonstrates yield-aware reserve deployment on Sepolia
- the frontend presents pipeline status, submission flows, proposal and project detail views, treasury NAV, and grading evidence

## Highlights

- End-to-end DAO architecture with token, hybrid votes, reputation, funding workflow, timelock, treasury, oracle, and adapter modules
- Sepolia deployment and proposal automation for repeatable milestone and treasury demo execution
- Python-based QA pipeline for coverage, gas analysis, static analysis, workbook generation, PDF reporting, and final package validation
- React + Vite + TypeScript front end with dashboard, pipeline, submit, detail, claim, treasury, and evidence views
- Strict deliverable generation that fails fast if required manifests, screenshots, or runtime artifacts are missing

## Architecture

| Layer | Main components | Purpose |
| --- | --- | --- |
| Governance | `CampusInnovationFundToken`, `HybridVotesAdapter`, `ReputationRegistry`, `InnovationGovernor`, `TimelockController` | Hybrid vote accounting, member reputation, proposal lifecycle, quorum, and delayed execution |
| Funding Workflow | `FundingRegistry` | Proposal intake, project records, milestone claims, workflow status, and evidence linkage |
| Treasury | `InnovationTreasury`, `TreasuryConstants` | Grant disbursement rules, milestone releases, reserve constraints, and treasury permissions |
| Integrations | `TreasuryOracle`, `AaveWethAdapter` | Chainlink valuation and Aave V3 WETH reserve management |
| QA and Automation | `scripts/`, `test/`, `analysis/` | Compile, deploy, validate, test, benchmark, and export deliverables |
| UI and Evidence | `frontend/`, `deployments/`, `evidence/`, `reports/`, `excel/` | Demo interface, workflow dashboards, manifests, screenshots, workbook, and final report |

## Tech Stack

- Solidity `0.8.24`
- Foundry project layout with OpenZeppelin contracts
- Python automation and unit/integration testing
- React `18`, Vite, TypeScript, `wagmi`, `viem`, and React Query
- Chainlink `ETH/USD`, Aave V3, and hybrid token-plus-reputation governance on Sepolia

## Quick Start

Clone the repository with submodules:

```powershell
git clone --recurse-submodules https://github.com/JonasWooh/Dao-Treasury-Governance.git
cd Dao-Treasury-Governance
```

Create and activate the project environment:

```powershell
conda env create -f environment.yml
conda activate cif_dao_env
```

Install the pinned Solidity compiler and compile contracts:

```powershell
python scripts/compile_contracts.py --install-solc
python scripts/compile_contracts.py --clean
```

Install frontend dependencies:

```powershell
npm --prefix frontend install
```

Review checked-in protocol and environment references before deploying:

```powershell
Get-Content config/sepolia.protocols.json
Get-Content config/sepolia.env.example
```

## Local Verification

Run the full Python suite:

```powershell
python -m unittest discover -s test -p "test_*.py" -v
```

Run targeted suites while iterating:

```powershell
python -m unittest test.integration.test_funding_workflow -v
python -m unittest test.integration.test_governor_funding_end_to_end -v
python -m unittest test.integration.test_governance_lifecycle -v
python -m unittest test.integration.test_innovation_treasury -v
python -m unittest test.unit.test_funding_registry -v
python -m unittest test.unit.test_governance_token -v
python -m unittest test.unit.test_treasury_oracle -v
python -m unittest test.unit.test_aave_weth_adapter -v
python -m unittest test.unit.test_submission_deliverables -v
python -m unittest test.unit.test_v2_reputation_and_hybrid -v
```

Run frontend tests and build the UI:

```powershell
npm --prefix frontend run test
$env:VITE_SEPOLIA_RPC_URL="https://your-sepolia-rpc-url"
$env:VITE_CHAIN_ID="11155111"
npm --prefix frontend run build
```

## Sepolia Demo Flow

The live demo pipeline is intentionally split into explicit steps so each artifact can be verified independently.

1. Seed the treasury and governance demo state.

```powershell
python scripts/seed_sepolia_demo_state.py --help
```

2. Run the staged governance demo with proposal approvals, treasury actions, and milestone transitions.

```powershell
python scripts/run_sepolia_demo_proposals.py --help
```

3. Export evidence manifests, transaction tables, and screenshot checklists.

```powershell
python scripts/export_sepolia_evidence.py --help
```

Core Sepolia outputs are written to:

- `deployments/deployments.sepolia.json`
- `deployments/proposal_scenarios.sepolia.json`
- `deployments/demo_evidence.sepolia.json`
- `deployments/demo_evidence.sepolia.md`
- `evidence/screenshots/screenshot-checklist.sepolia.md`

## Deliverables Pipeline

After Sepolia manifests are available, generate the final deliverables:

```powershell
python scripts/export_frontend_bundle.py
python scripts/generate_treasury_workbook.py
python scripts/generate_final_report.py
python scripts/validate_submission_package.py
```

Generated outputs include:

- `frontend/src/generated/frontend.config.sepolia.json`
- `frontend/src/generated/abi/*.json`
- `frontend/public/runtime/*.json`
- `excel/treasury_analysis.sepolia.xlsx`
- `excel/treasury_analysis.sepolia.summary.json`
- `reports/final_report.sepolia.pdf`
- `analysis/coverage/*`
- `analysis/gas/*`
- `analysis/static/*`

## Repository Map

See `docs/repository-layout.md` for the full directory-by-directory reference.

Important top-level areas:

- `src/` for governance, funding, treasury, oracle, adapters, interfaces, and mocks
- `test/` for Python unit and integration tests
- `scripts/` for compile, deployment, QA, and deliverable automation
- `frontend/` for the React application, runtime bundles, dashboard pages, and workflow detail pages
- `deployments/` and `evidence/` for Sepolia manifests and screenshot assets
- `analysis/`, `excel/`, and `reports/` for generated review artifacts

## Environment Notes

- Use `config/sepolia.env.example` as the source of truth for Sepolia deployment inputs
- `config/sepolia.env` is local-only and should not be committed with real keys
- The frontend expects `VITE_SEPOLIA_RPC_URL` and `VITE_CHAIN_ID=11155111`
- The repository uses OpenZeppelin as a submodule, so `--recurse-submodules` is recommended for fresh clones

## Strictness by Design

This project does not silently fall back to fake runtime data or missing deliverables. If required Sepolia manifests, screenshots, workbook outputs, ABI exports, or report inputs are absent or malformed, the relevant step fails explicitly. That strictness is intentional: the repository is designed to support grading, reproducibility, and final-package confidence.

## Project Plan

The repository currently reflects both the original baseline plan and a later workflow refinement:

- `DAO Prototype Plan on Sepolia.md`
- `Refine.md`

## License

This repository is licensed under the MIT License. See `LICENSE` for details.
