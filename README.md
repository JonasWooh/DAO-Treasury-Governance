# Campus Innovation Fund DAO

Student-run treasury governance on Sepolia, with a full DAO stack covering on-chain voting, timelocked execution, treasury controls, Chainlink valuation, Aave reserve management, QA automation, and a React front end.

![Solidity](https://img.shields.io/badge/Solidity-0.8.24-1f2937?logo=solidity)
![Foundry](https://img.shields.io/badge/Foundry-Enabled-b45309)
![React](https://img.shields.io/badge/React-18.3.1-0f766e?logo=react)
![Vite](https://img.shields.io/badge/Vite-7.1-1d4ed8?logo=vite)
![Network](https://img.shields.io/badge/Network-Sepolia-065f46)

## Overview

This repository implements a realistic campus grant DAO rather than a minimal voting demo. Token holders govern a student innovation treasury, decide which campus projects receive funding, enforce reserve rules, and manage idle WETH through Aave on Sepolia.

The project is built around a core governance and treasury story:

- `CampusInnovationFundToken` provides ERC20Votes-based governance power
- `InnovationGovernor` and `TimelockController` enforce proposal, voting, queue, and execution flow
- `InnovationTreasury` applies constrained treasury policy instead of unrestricted transfers
- `TreasuryOracle` tracks treasury value through Chainlink `ETH/USD`
- `AaveWethAdapter` demonstrates yield-aware reserve deployment on Sepolia
- the frontend presents governance state, proposal history, treasury NAV, and grading evidence

## Highlights

- End-to-end DAO architecture with token, governor, timelock, treasury, oracle, and adapter modules
- Sepolia deployment and proposal automation for repeatable demo execution
- Python-based QA pipeline for coverage, gas analysis, static analysis, workbook generation, PDF reporting, and final package validation
- React + Vite + TypeScript front end with four routes: `Overview`, `Proposals`, `Treasury & NAV`, and `Evidence`
- Strict deliverable generation that fails fast if required manifests, screenshots, or runtime artifacts are missing

## Architecture

| Layer | Main components | Purpose |
| --- | --- | --- |
| Governance | `CampusInnovationFundToken`, `InnovationGovernor`, `TimelockController` | Proposal lifecycle, voting, quorum, and delayed execution |
| Treasury | `InnovationTreasury`, `TreasuryConstants` | Grant disbursement rules, reserve constraints, and treasury permissions |
| Integrations | `TreasuryOracle`, `AaveWethAdapter` | Chainlink valuation and Aave V3 WETH reserve management |
| QA and Automation | `scripts/`, `test/`, `analysis/` | Compile, deploy, validate, test, benchmark, and export deliverables |
| UI and Evidence | `frontend/`, `deployments/`, `evidence/`, `reports/`, `excel/` | Demo interface, manifests, screenshots, workbook, and final report |

## Tech Stack

- Solidity `0.8.24`
- Foundry project layout with OpenZeppelin contracts
- Python automation and unit/integration testing
- React `18`, Vite, TypeScript, `wagmi`, `viem`, and React Query
- Chainlink `ETH/USD` and Aave V3 on Sepolia

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
python -m unittest test.integration.test_governance_lifecycle -v
python -m unittest test.integration.test_innovation_treasury -v
python -m unittest test.unit.test_governance_token -v
python -m unittest test.unit.test_treasury_oracle -v
python -m unittest test.unit.test_aave_weth_adapter -v
python -m unittest test.unit.test_submission_deliverables -v
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

2. Run Proposal 1 through Proposal 3 with automatic waits for governance timing.

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

- `src/` for contracts, interfaces, adapters, oracle, and mocks
- `test/` for Python unit and integration tests
- `scripts/` for compile, deployment, QA, and deliverable automation
- `frontend/` for the React application and runtime bundles
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

The original implementation plan is captured in:

- `Industrial-Quality DAO Prototype Plan on Sepolia.md`

## License

This repository is licensed under the MIT License. See `LICENSE` for details.
