# Campus Innovation Fund DAO

This repository implements the `Campus Innovation Fund DAO` described in `Industrial-Quality DAO Prototype Plan on Sepolia.md`.

The build order follows the original engineering plan:

1. Governance spine
2. Treasury rules
3. Oracle and Aave integration
4. Testing, QA, and static analysis
5. Sepolia deployment and evidence capture
6. Front-end and final deliverables

## Current status

The repository now includes Milestones 1 through 7:

- `CampusInnovationFundToken` based on `ERC20Votes`
- `InnovationGovernor` and `TimelockController` governance wiring
- `InnovationTreasury` with constrained grant and reserve policy logic
- `TreasuryOracle` wrapping Chainlink `ETH/USD`
- `AaveWethAdapter` wrapping Sepolia Aave V3 `WETH`
- Local protocol mocks and Python unit/integration tests
- Coverage, gas, and Slither analysis scripts under `scripts/`
- Semi-automated Sepolia demo scripts for seed state, proposal execution, and evidence export
- A `React + Vite + TypeScript` frontend with four pages: `Overview`, `Proposals`, `Treasury & NAV`, and `Evidence`
- Frontend ABI/config export, Excel treasury workbook generation, PDF report generation, and final submission validation scripts

## Repository layout

See `docs/repository-layout.md` for the folder plan and ownership of each top-level directory.

## Local workflow

1. Create the dedicated conda environment:

```powershell
conda env create -f environment.yml
```

2. Activate it:

```powershell
conda activate cif_dao_env
```

3. Install the pinned Solidity compiler explicitly:

```powershell
python scripts/compile_contracts.py --install-solc
```

4. Compile contracts:

```powershell
python scripts/compile_contracts.py --clean
```

5. Review the checked-in Sepolia protocol addresses:

```powershell
Get-Content config/sepolia.protocols.json
```

6. Install frontend packages inside the conda environment:

```powershell
npm --prefix frontend install
```

## Local verification

Run the complete Python unit and integration suite:

```powershell
python -m unittest discover -s test -p "test_*.py" -v
```

Run focused suites when iterating:

```powershell
python -m unittest test.integration.test_governance_lifecycle -v
python -m unittest test.integration.test_innovation_treasury -v
python -m unittest test.unit.test_governance_token -v
python -m unittest test.unit.test_treasury_oracle -v
python -m unittest test.unit.test_aave_weth_adapter -v
python -m unittest test.unit.test_submission_deliverables -v
```

Run frontend tests:

```powershell
npm --prefix frontend run test
```

Build the frontend bundle:

```powershell
$env:VITE_SEPOLIA_RPC_URL="https://your-sepolia-rpc-url"
$env:VITE_CHAIN_ID="11155111"
npm --prefix frontend run build
```

## Quality artifacts

Generate the required QA and engineering outputs:

```powershell
python scripts/generate_coverage_report.py
python scripts/generate_gas_report.py
python scripts/run_slither_analysis.py
```

The resulting files are written to:

- `analysis/coverage/`
- `analysis/gas/`
- `analysis/static/`

## Milestone 5 demo flow

The Sepolia demo is split into three scripts instead of a single all-in-one command.

1. Prepare the on-chain seed state:

```powershell
python scripts/seed_sepolia_demo_state.py --help
```

2. Run Proposal 1 through Proposal 3 with automatic waits for voting delay, voting period, and timelock delay:

```powershell
python scripts/run_sepolia_demo_proposals.py --help
```

3. Export evidence manifests, a report-ready Markdown transaction table, and a screenshot checklist:

```powershell
python scripts/export_sepolia_evidence.py --help
```

The Milestone 5 outputs are written to:

- `deployments/deployments.sepolia.json`
- `deployments/proposal_scenarios.sepolia.json`
- `deployments/demo_evidence.sepolia.json`
- `deployments/demo_evidence.sepolia.md`
- `evidence/screenshots/screenshot-checklist.sepolia.md`

## Milestone 6-7 deliverables

The frontend and final-deliverable pipeline is explicit and strict.

1. Export the authoritative frontend ABI/config/runtime bundle after real Sepolia manifests exist:

```powershell
python scripts/export_frontend_bundle.py
```

2. Generate the Excel treasury workbook and summary JSON:

```powershell
python scripts/generate_treasury_workbook.py
```

3. Capture every required screenshot listed in:

```powershell
Get-Content evidence/screenshots/screenshot-manifest.sepolia.json
```

4. Generate the final PDF report. This step fails hard if any required screenshot is missing:

```powershell
python scripts/generate_final_report.py
```

5. Run the final package validator. This checks manifest consistency, ABI/config presence, screenshots, workbook, report, gas/static artifacts, and frontend build success:

```powershell
python scripts/validate_submission_package.py
```

The Milestone 6-7 outputs are written to:

- `frontend/src/generated/frontend.config.sepolia.json`
- `frontend/src/generated/abi/*.json`
- `frontend/public/runtime/*.json`
- `excel/treasury_analysis.sepolia.xlsx`
- `excel/treasury_analysis.sepolia.summary.json`
- `reports/final_report.sepolia.pdf`

## Environment variables

Use `config/sepolia.env.example` as the reference for the Sepolia deployment, demo voter, funder, and project recipient inputs.

For the frontend build, provide:

- `VITE_SEPOLIA_RPC_URL`
- `VITE_CHAIN_ID=11155111`

## Important note on strictness

The frontend runtime, report builder, workbook/report pipeline, and final validator do not silently fall back to mock data, empty manifests, placeholder screenshots, or network auto-correction. If authoritative Sepolia artifacts are missing or malformed, the relevant step fails explicitly and must be fixed before sign-off.
