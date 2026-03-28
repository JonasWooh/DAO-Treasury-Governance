# Repository Layout

This document is the practical handoff map for the repository. It focuses on what a new collaborator should read first, which directories are authoritative, which outputs are generated, and which folders are safe to ignore during normal work.

## 1. Core Smart-Contract Source

These files are the best entry point if you need to understand system logic.

- `src/governance/`
  - `CampusInnovationFundToken.sol`
    - ERC20Votes token used as the token half of hybrid governance
  - `ReputationRegistry.sol`
    - member registry and reputation checkpoint storage
  - `HybridVotesAdapter.sol`
    - combines token voting power and reputation into a Governor-compatible votes source
  - `InnovationGovernor.sol`
    - the main governance contract for proposal creation, voting, queueing, and execution
  - `GovernanceConstants.sol`
    - governance configuration values shared across the governance layer
- `src/funding/`
  - `FundingRegistry.sol`
    - workflow state for submissions, projects, milestone claims, evidence URIs, and execution bookkeeping
    - also enforces strict proposal and milestone state transitions, governor-state validation, and duplicate settlement prevention
- `src/treasury/`
  - `InnovationTreasury.sol`
    - treasury policy, reserve checks, milestone payout execution, and treasury-controlled actions
    - includes `ReentrancyGuard`, disabled ownership transfer and renounce paths, and stale-oracle validation before NAV-sensitive operations
  - `TreasuryConstants.sol`
    - treasury limits and reusable treasury configuration constants
- `src/oracle/`
  - `TreasuryOracle.sol`
    - Chainlink `ETH / USD` valuation wrapper with freshness checks
    - validates round completeness, timestamps, and decimal normalization before returning values to the treasury layer
- `src/adapters/`
  - `AaveWethAdapter.sol`
    - constrained adapter used by the treasury to supply and withdraw WETH from Aave
    - guarded by `onlyTreasury`, `nonReentrant`, and strict pre/post balance reconciliation around external protocol calls
- `src/interfaces/`
  - internal interfaces for the treasury, funding, governance, reputation, and oracle modules
  - `external/` contains external protocol interfaces such as Aave V3 and Chainlink aggregator definitions
- `src/mocks/`
  - mock contracts used by the Python unit and integration tests

## 2. Tests And Quality Gates

This is the main place to understand expected behavior and submission guarantees.

- `test/support.py`
  - shared helpers for deployment, test setup, and runtime fixtures
- `test/unit/`
  - focused contract and deliverable tests
  - key files include:
    - `test_governance_token.py`
    - `test_funding_registry.py`
    - `test_repo_secret_scan.py`
    - `test_treasury_oracle.py`
    - `test_aave_weth_adapter.py`
    - `test_v2_reputation_and_hybrid.py`
    - `test_submission_deliverables.py`
- `test/integration/`
  - cross-contract and end-to-end workflow tests
  - key files include:
    - `test_governance_lifecycle.py`
    - `test_funding_workflow.py`
    - `test_governor_funding_end_to_end.py`
    - `test_innovation_treasury.py`

## 3. Automation And Deployment Scripts

The `scripts/` directory is organized more by workflow stage than by contract area.

- Compile and artifact generation
  - `compile_contracts.py`
    - installs or invokes the pinned Solidity compiler and writes `artifacts/`
- Deployment
  - `deploy_governance_spine.py`
    - deploys the token, reputation registry, hybrid votes adapter, timelock, and governor
  - `deploy_treasury_stack.py`
    - deploys the oracle, funding registry, Aave adapter, and treasury against the governance deployment
- Demo-state creation and governance execution
  - `seed_sepolia_demo_state.py`
    - funds the treasury and seeds the live Sepolia demo state
  - `run_sepolia_demo_proposals.py`
    - runs the staged proposal scenarios used in the final evidence package
  - `sepolia_demo_common.py`
    - shared helpers for the live Sepolia workflow scripts
- Export and packaging helpers
  - `export_sepolia_evidence.py`
    - turns runtime manifests into report-ready markdown and screenshot checklists
  - `export_frontend_bundle.py`
    - copies authoritative manifest data into frontend ABI, config, and runtime bundle files
  - `export_etherscan_standard_input.py`
    - creates the Standard JSON Input payload for Etherscan verification
  - `deliverable_common.py`
    - shared utilities reused by workbook, report, and validation scripts
- Repository security and secret hygiene
  - `check_repo_secrets.py`
    - scans the worktree and git history for sensitive file paths, suspicious secret assignments, and exact matches to local secret values
  - `cli_security.py`
    - shared helper that makes deployment and demo scripts prefer environment variables and warn when secrets are passed through CLI flags
  - `install_git_hooks.py`
    - configures git to use `.githooks/` so the repository scanner runs before commits
- Analysis and deliverable generation
  - `generate_coverage_report.py`
  - `generate_gas_report.py`
  - `run_slither_analysis.py`
    - also verifies the pinned Windows `solc.exe` checksum before static analysis runs
  - `generate_treasury_workbook.py`
  - `generate_final_report.py`
- Validation and verification
  - `validate_submission_package.py`
    - asserts that required manifests, screenshots, workbook outputs, runtime files, and report files exist and line up
  - `verify_etherscan_contracts.py`
    - submits contract verification jobs through the Etherscan API

## 4. Frontend Application And Runtime Data

The React app is the main demo surface and the easiest place to inspect the end-to-end workflow.

- `frontend/package.json`
  - frontend scripts: `dev`, `build`, `preview`, `test`
- `frontend/src/App.tsx`
  - route map and runtime bundle loading
- `frontend/src/pages/`
  - `OverviewPage.tsx`
    - top-level DAO and proposal summary
  - `ProposalsPage.tsx`
    - proposal pipeline and governance timeline
  - `ProposalDetailPage.tsx`
    - detailed proposal state, votes, evidence, and execution context
  - `ProjectDetailPage.tsx`
    - project state after proposal approval
  - `SubmitProposalPage.tsx`
    - submission guidance and workflow explanation
  - `MilestoneClaimPage.tsx`
    - claim submission and milestone review context
  - `TreasuryPage.tsx`
    - NAV, reserve position, and Aave allocation view
  - `EvidencePage.tsx`
    - contract registry, transaction evidence, and screenshot/report support
- `frontend/src/components/`, `frontend/src/hooks/`, `frontend/src/types/`
  - shared UI, runtime loading helpers, and typed bundle definitions
- `frontend/src/generated/`
  - generated inputs for the app, including:
    - `frontend.config.sepolia.json`
    - `abi/*.json`
  - treat this directory as generated, not hand-edited source
- `frontend/public/runtime/`
  - runtime copies of Sepolia manifests consumed by the app
  - current files include:
    - `deployments.sepolia.json`
    - `proposal_scenarios.sepolia.json`
    - `demo_evidence.sepolia.json`
    - `funding_state.sepolia.json`
    - `screenshot-manifest.sepolia.json`

## 5. Manifests, Evidence, And Final Deliverables

These folders are critical for handoff because they describe the checked-in Sepolia state and the final submission package.

- `deployments/`
  - `deployments.sepolia.json`
    - authoritative address and deployment transaction manifest
  - `proposal_scenarios.sepolia.json`
    - staged governance scenario data used by the frontend and report
  - `funding_state.sepolia.json`
    - final workflow state snapshot for projects and claims
  - `demo_evidence.sepolia.json`
    - raw evidence manifest for proposal, vote, queue, execute, and treasury actions
  - `demo_evidence.sepolia.md`
    - report-friendly evidence summary derived from the JSON manifests
- `evidence/screenshots/`
  - `screenshot-manifest.sepolia.json`
    - canonical list of required screenshot filenames and captions
  - `screenshot-checklist.sepolia.md`
    - capture guidance for the report package
  - required report screenshots
  - `raw-*.png` support captures used to build the final screenshot package
- `excel/`
  - `treasury_analysis.sepolia.xlsx`
    - treasury scenario workbook
  - `treasury_analysis.sepolia.summary.json`
    - machine-readable workbook summary used by the report generator
- `reports/`
  - `final_report.sepolia.pdf`
    - checked-in final PDF deliverable
- `analysis/`
  - `coverage/`
    - Python coverage reports and summaries
  - `gas/`
    - gas report markdown and JSON
  - `static/`
    - Slither summaries and supporting JSON outputs
- `output/`
  - `etherscan/`
    - helper payloads such as `standard-input.full.json`
  - `playwright/`
    - local browser helper logs

## 6. Generated Artifacts Versus Source

These directories are important, but they should not be confused with hand-authored implementation logic.

- `artifacts/`
  - compiled Solidity metadata, ABI, and bytecode outputs
- `frontend/src/generated/`
  - generated frontend config and ABI files
- `frontend/public/runtime/`
  - generated runtime bundle copies of authoritative manifests
- `analysis/`, `excel/`, `reports/`, `evidence/screenshots/`
  - deliverable outputs that are intentionally checked in
- `output/`
  - helper outputs and logs rather than core implementation

If you need to understand behavior, start with `src/`, `scripts/`, `test/`, and the hand-written parts of `frontend/src/`.

## 7. Third-Party Dependencies And Tooling

These files explain how the project pulls in external Solidity and Python/Node tooling.

- `lib/openzeppelin-contracts/`
  - Git submodule containing the main Solidity dependency tree
- `remappings.txt`
  - maps `@openzeppelin/contracts/` to `lib/openzeppelin-contracts/contracts/`
- `.gitmodules`
  - declares the OpenZeppelin submodule and the Slither analysis sandbox submodule copy
- `foundry.toml`
  - Foundry-compatible project configuration
- `environment.yml`
  - conda environment definition for Python, Node.js, and report-generation tooling
- `requirements-dev.txt`
  - pinned Python dependencies for local installs outside the conda flow
- `config/`
  - `sepolia.env.example`
    - required environment variable names for live Sepolia usage
  - `sepolia.env`
    - local-only environment file for private deployment credentials
  - `sepolia.protocols.json`
    - external protocol addresses and protocol configuration for the treasury deployment

## 8. Project Notes And Historical Context

These files are useful context, but they are not the primary source for current implementation behavior.

- `DAO Prototype Plan on Sepolia.md`
  - baseline project plan and assignment framing
- `Refine.md`
  - historical refinement note for the V2 workflow design
  - treat it as supplemental context, not the main onboarding document
- `Grading Details.png`
  - assignment rubric reference

## 9. Repository Security And Push Guardrails

These files are part of the repository hygiene layer rather than the on-chain product logic.

- `.githooks/pre-commit`
  - local commit hook that runs `scripts/check_repo_secrets.py`
- `.github/workflows/secret-scan.yml`
  - CI workflow that reruns the repository secret scan on pushes and pull requests
- `docs/push-security-checklist.md`
  - manual checklist for reviewing generated attachments and secret exposure before push
- `.gitignore`
  - ignore rules for local env files, keystore-like artifacts, and raw screenshot support assets

## 10. Not Core Implementation

These paths can usually be ignored during normal code reading and handoff.

- `node_modules/`
  - installed frontend dependencies
- `.vite/`
  - Vite cache output
- `test/.tmp/`
  - temporary test artifacts
- `__pycache__/`
  - Python bytecode caches
- `.playwright-cli/`
  - local Playwright helper state
- `.tooling/slither_project/`
  - analysis sandbox used for Slither runs, including its own OpenZeppelin submodule copy

## 11. Recommended Reading Order

For a fast handoff, read in this order:

1. `README.md`
2. `deployments/deployments.sepolia.json`
3. `src/governance/InnovationGovernor.sol`
4. `src/funding/FundingRegistry.sol`
5. `src/treasury/InnovationTreasury.sol`
6. `scripts/deploy_governance_spine.py`
7. `scripts/run_sepolia_demo_proposals.py`
8. `frontend/src/App.tsx`
9. `frontend/src/pages/TreasuryPage.tsx`
10. `deployments/demo_evidence.sepolia.md`
