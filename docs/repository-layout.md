# Repository Layout

This repository is structured to keep governance, treasury, integrations, QA, UI, and submission artifacts clearly separated.

## Smart contracts

- `src/governance/`
  - governance token, governor, governance constants
- `src/treasury/`
  - constrained treasury contracts
- `src/oracle/`
  - Chainlink-backed valuation contracts
- `src/adapters/`
  - protocol adapters such as Aave integration
- `src/interfaces/`
  - explicit cross-module interfaces
- `src/mocks/`
  - mock targets and test-only support contracts

## Testing and automation

- `test/unit/`
  - isolated contract and deliverable tests
- `test/integration/`
  - cross-contract and protocol-flow tests
- `scripts/`
  - compile, deployment, QA, frontend bundle export, workbook/report generation, and Sepolia demo automation
  - includes `seed_sepolia_demo_state.py`, `run_sepolia_demo_proposals.py`, `export_sepolia_evidence.py`, `export_frontend_bundle.py`, `generate_treasury_workbook.py`, `generate_final_report.py`, and `validate_submission_package.py`

## App and config

- `frontend/`
  - Vite + React + TypeScript submission UI with exactly four routes: Overview, Proposals, Treasury & NAV, Evidence
  - contains generated ABI/config files under `frontend/src/generated/`
  - contains runtime manifest copies under `frontend/public/runtime/`
- `config/`
  - checked-in example environment files and network configuration
  - includes `frontend/.env.example` expectations through the frontend build process
- `deployments/`
  - generated deployment and demo manifests such as `deployments.sepolia.json`, `proposal_scenarios.sepolia.json`, and `demo_evidence.sepolia.json`
- `artifacts/`
  - compiled ABI and bytecode outputs

## Analysis and deliverables

- `analysis/coverage/`
  - coverage outputs
- `analysis/gas/`
  - gas benchmarking outputs
- `analysis/static/`
  - static-analysis artifacts such as Slither reports
- `evidence/screenshots/`
  - screenshot manifest, report-ready screenshots, and checklist assets
- `reports/`
  - generated PDF report exports
- `excel/`
  - treasury scenario workbook and workbook summary JSON

## Root-level project files

- `Industrial-Quality DAO Prototype Plan on Sepolia.md`
  - source implementation plan and requirements
- `Grading Details.png`
  - grading reference captured from the course materials
- `foundry.toml`
  - Solidity project configuration for Foundry-compatible workflows
- `requirements-dev.txt`
  - pinned Python tooling dependencies for compile, deployment, and deliverable automation
- `environment.yml`
  - conda environment definition, including Python and Node.js for the frontend build
