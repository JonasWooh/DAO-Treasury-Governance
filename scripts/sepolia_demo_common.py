from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.contract import Contract
from web3.exceptions import ContractLogicError


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts"

DEFAULT_DEPLOYMENT_MANIFEST = ROOT / "deployments" / "deployments.sepolia.json"
DEFAULT_SCENARIO_MANIFEST = ROOT / "deployments" / "proposal_scenarios.sepolia.json"
DEFAULT_EVIDENCE_MANIFEST = ROOT / "deployments" / "demo_evidence.sepolia.json"
DEFAULT_EVIDENCE_MARKDOWN = ROOT / "deployments" / "demo_evidence.sepolia.md"
DEFAULT_SCREENSHOT_CHECKLIST = ROOT / "evidence" / "screenshots" / "screenshot-checklist.sepolia.md"

SEPOLIA_CHAIN_ID = 11155111
SEPOLIA_ETHERSCAN_BASE_URL = "https://sepolia.etherscan.io"

TOKEN_UNIT = 10**18
INITIAL_VOTER_ALLOCATION = 200_000 * TOKEN_UNIT
DEMO_TREASURY_FUNDING_WETH = 5 * TOKEN_UNIT
DEMO_AAVE_DEPOSIT_WETH = 3 * TOKEN_UNIT
DEMO_MILESTONE_PAYOUT_WETH = TOKEN_UNIT // 2

PROJECT_NAME = "Smart Recycling Kiosk"
PROJECT_KEY = "SMART_RECYCLING_KIOSK"
PROJECT_ID = Web3.keccak(text=PROJECT_KEY).hex()

ZERO_ADDRESS = Web3.to_checksum_address("0x0000000000000000000000000000000000000000")
ZERO_BYTES32 = "0x" + ("00" * 32)
VOTE_SUPPORT_FOR = 1

PROPOSAL_STATE_NAMES = {
    0: "Pending",
    1: "Active",
    2: "Canceled",
    3: "Defeated",
    4: "Succeeded",
    5: "Queued",
    6: "Expired",
    7: "Executed",
}

TOKEN_ARTIFACT = ARTIFACTS_DIR / "src" / "governance" / "CampusInnovationFundToken" / "CampusInnovationFundToken.json"
GOVERNOR_ARTIFACT = ARTIFACTS_DIR / "src" / "governance" / "InnovationGovernor" / "InnovationGovernor.json"
TIMELOCK_ARTIFACT = (
    ARTIFACTS_DIR
    / "lib"
    / "openzeppelin-contracts"
    / "contracts"
    / "governance"
    / "TimelockController"
    / "TimelockController.json"
)
TREASURY_ARTIFACT = ARTIFACTS_DIR / "src" / "treasury" / "InnovationTreasury" / "InnovationTreasury.json"

MINIMAL_ERC20_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "value", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


class TransactionSender:
    def __init__(self, w3: Web3, account: LocalAccount, gas_price_wei: int | None) -> None:
        self.w3 = w3
        self.account = account
        self.gas_price_wei = gas_price_wei
        self.nonce = w3.eth.get_transaction_count(account.address)

    def _base_transaction(self) -> dict[str, Any]:
        return {
            "from": self.account.address,
            "nonce": self.nonce,
            "chainId": self.w3.eth.chain_id,
            "gasPrice": self.gas_price_wei if self.gas_price_wei is not None else self.w3.eth.gas_price,
        }

    def send_call(self, call) -> tuple[str, Any]:
        transaction = call.build_transaction(self._base_transaction())
        transaction["gas"] = self.w3.eth.estimate_gas(transaction)
        signed = self.account.sign_transaction(transaction)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.nonce += 1
        return tx_hash.hex(), receipt


def require_value(value: str | None, label: str) -> str:
    if value is None or value.strip() == "":
        raise ValueError(f"Missing required parameter: {label}")
    return value


def parse_account_from_key(private_key: str) -> LocalAccount:
    return Account.from_key(require_value(private_key, "private key"))


def connect_to_sepolia(rpc_url: str) -> Web3:
    w3 = Web3(Web3.HTTPProvider(require_value(rpc_url, "rpc-url or SEPOLIA_RPC_URL")))
    if not w3.is_connected():
        raise ConnectionError("Unable to connect to the configured RPC endpoint.")
    if w3.eth.chain_id != SEPOLIA_CHAIN_ID:
        raise RuntimeError(f"Connected to chainId {w3.eth.chain_id}, expected {SEPOLIA_CHAIN_ID}.")
    return w3


def to_checksum_address(w3: Web3, raw_value: str, label: str) -> str:
    if not Web3.is_address(raw_value):
        raise ValueError(f"Invalid address for {label}: {raw_value}")
    return w3.to_checksum_address(raw_value)


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(f"Missing required file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_artifact(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing artifact: {path}. Run `python scripts/compile_contracts.py --clean` before running the demo scripts."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def build_contract_from_artifact(w3: Web3, artifact_path: Path, address: str) -> Contract:
    artifact = load_artifact(artifact_path)
    return w3.eth.contract(address=address, abi=artifact["abi"])


def build_minimal_erc20(w3: Web3, address: str) -> Contract:
    return w3.eth.contract(address=address, abi=MINIMAL_ERC20_ABI)


def description_hash(description: str) -> str:
    return Web3.keccak(text=description).hex()


def proposal_state_name(state_value: int) -> str:
    return PROPOSAL_STATE_NAMES.get(state_value, f"Unknown({state_value})")


def etherscan_address_url(address: str) -> str:
    return f"{SEPOLIA_ETHERSCAN_BASE_URL}/address/{address}"


def etherscan_tx_url(tx_hash: str) -> str:
    return f"{SEPOLIA_ETHERSCAN_BASE_URL}/tx/{tx_hash}"


def load_required_contracts(w3: Web3, deployment_manifest: dict[str, Any]) -> dict[str, Contract]:
    contracts = deployment_manifest.get("contracts", {})
    external_protocols = deployment_manifest.get("externalProtocols", {})

    required_contract_names = [
        "CampusInnovationFundToken",
        "InnovationGovernor",
        "TimelockController",
        "InnovationTreasury",
        "TreasuryOracle",
        "AaveWethAdapter",
    ]
    for contract_name in required_contract_names:
        if contract_name not in contracts:
            raise KeyError(f"Deployment manifest is missing contracts.{contract_name}")
    if "WETH" not in external_protocols:
        raise KeyError("Deployment manifest is missing externalProtocols.WETH")

    return {
        "token": build_contract_from_artifact(w3, TOKEN_ARTIFACT, contracts["CampusInnovationFundToken"]),
        "governor": build_contract_from_artifact(w3, GOVERNOR_ARTIFACT, contracts["InnovationGovernor"]),
        "timelock": build_contract_from_artifact(w3, TIMELOCK_ARTIFACT, contracts["TimelockController"]),
        "treasury": build_contract_from_artifact(w3, TREASURY_ARTIFACT, contracts["InnovationTreasury"]),
        "weth": build_minimal_erc20(w3, external_protocols["WETH"]),
    }


def encode_call(contract: Contract, function_name: str, *args: Any) -> str:
    contract_function = getattr(contract.functions, function_name)(*args)
    return contract_function._encode_transaction_data()


def make_project_definition(recipient: str) -> dict[str, Any]:
    return {
        "name": PROJECT_NAME,
        "projectKey": PROJECT_KEY,
        "projectId": PROJECT_ID,
        "recipient": recipient,
        "maxBudgetWeth": str(TOKEN_UNIT),
        "milestoneCount": 2,
        "milestonePayoutsWeth": {
            "milestone0": str(DEMO_MILESTONE_PAYOUT_WETH),
        },
    }


def build_demo_scenarios(
    governor: Contract,
    timelock: Contract,
    treasury: Contract,
    recipient: str,
) -> dict[str, Any]:
    project = make_project_definition(recipient)
    proposals: list[dict[str, Any]] = []

    proposal_specs = [
        {
            "slug": "proposal1_approve_project",
            "title": "Proposal 1",
            "description": "Proposal 1: Approve Smart Recycling Kiosk project",
            "targets": [treasury.address],
            "values": [0],
            "calldatas": [
                encode_call(
                    treasury,
                    "approveProject",
                    Web3.to_bytes(hexstr=project["projectId"]),
                    recipient,
                    TOKEN_UNIT,
                    2,
                )
            ],
            "expectedOutcome": {
                "projectActive": True,
                "projectReleasedWeth": "0",
                "treasuryLiquidWeth": str(DEMO_TREASURY_FUNDING_WETH),
                "treasurySuppliedWeth": "0",
            },
        },
        {
            "slug": "proposal2_deposit_idle_funds",
            "title": "Proposal 2",
            "description": "Proposal 2: Deposit 3.0 WETH into Aave",
            "targets": [treasury.address],
            "values": [0],
            "calldatas": [
                encode_call(
                    treasury,
                    "depositIdleFunds",
                    DEMO_AAVE_DEPOSIT_WETH,
                )
            ],
            "expectedOutcome": {
                "treasuryLiquidWeth": str(2 * TOKEN_UNIT),
                "treasurySuppliedWeth": str(3 * TOKEN_UNIT),
                "treasuryTotalManagedWeth": str(DEMO_TREASURY_FUNDING_WETH),
            },
        },
        {
            "slug": "proposal3_withdraw_and_release_milestone",
            "title": "Proposal 3",
            "description": "Proposal 3: Withdraw 0.5 WETH and release milestone 0",
            "targets": [treasury.address, treasury.address],
            "values": [0, 0],
            "calldatas": [
                encode_call(
                    treasury,
                    "withdrawIdleFunds",
                    DEMO_MILESTONE_PAYOUT_WETH,
                ),
                encode_call(
                    treasury,
                    "releaseMilestone",
                    Web3.to_bytes(hexstr=project["projectId"]),
                    0,
                    DEMO_MILESTONE_PAYOUT_WETH,
                ),
            ],
            "expectedOutcome": {
                "projectReleasedWeth": str(DEMO_MILESTONE_PAYOUT_WETH),
                "projectMilestonesReleased": 1,
                "projectActive": True,
                "treasuryLiquidWeth": str(2 * TOKEN_UNIT),
                "treasurySuppliedWeth": str((5 * TOKEN_UNIT) // 2),
                "treasuryTotalManagedWeth": str((9 * TOKEN_UNIT) // 2),
                "recipientIncreaseWeth": str(DEMO_MILESTONE_PAYOUT_WETH),
            },
        },
    ]

    for spec in proposal_specs:
        desc_hash = description_hash(spec["description"])
        proposal_id = governor.functions.hashProposal(
            spec["targets"],
            spec["values"],
            spec["calldatas"],
            desc_hash,
        ).call()
        operation_id = timelock.functions.hashOperationBatch(
            spec["targets"],
            spec["values"],
            spec["calldatas"],
            Web3.to_bytes(hexstr=ZERO_BYTES32),
            Web3.to_bytes(hexstr=desc_hash),
        ).call()

        proposals.append(
            {
                "slug": spec["slug"],
                "title": spec["title"],
                "description": spec["description"],
                "targets": spec["targets"],
                "values": [str(value) for value in spec["values"]],
                "calldatas": spec["calldatas"],
                "descriptionHash": desc_hash,
                "proposalId": str(proposal_id),
                "operationId": operation_id.hex(),
                "expectedOutcome": spec["expectedOutcome"],
            }
        )

    return {
        "project": project,
        "proposals": proposals,
    }


def safe_governor_state(governor: Contract, proposal_id: int) -> int | None:
    try:
        return governor.functions.state(proposal_id).call()
    except ContractLogicError as exc:
        if "GovernorNonexistentProposal" in str(exc):
            return None
        raise
    except ValueError as exc:
        if "GovernorNonexistentProposal" in str(exc):
            return None
        raise


def wait_for_block_number(
    w3: Web3,
    target_block_number: int,
    poll_interval_seconds: float,
    timeout_seconds: float,
) -> int:
    deadline = time.time() + timeout_seconds
    latest_block_number = w3.eth.block_number
    while latest_block_number < target_block_number:
        if time.time() > deadline:
            raise TimeoutError(
                f"Timed out waiting for block {target_block_number}. Latest block is {latest_block_number}."
            )
        time.sleep(poll_interval_seconds)
        latest_block_number = w3.eth.block_number
    return latest_block_number


def wait_for_timestamp(
    w3: Web3,
    target_timestamp: int,
    poll_interval_seconds: float,
    timeout_seconds: float,
) -> int:
    deadline = time.time() + timeout_seconds
    latest_timestamp = w3.eth.get_block("latest")["timestamp"]
    while latest_timestamp < target_timestamp:
        if time.time() > deadline:
            raise TimeoutError(
                f"Timed out waiting for timestamp {target_timestamp}. Latest block timestamp is {latest_timestamp}."
            )
        time.sleep(poll_interval_seconds)
        latest_timestamp = w3.eth.get_block("latest")["timestamp"]
    return latest_timestamp


def wait_for_proposal_state(
    governor: Contract,
    proposal_id: int,
    desired_states: set[int],
    poll_interval_seconds: float,
    timeout_seconds: float,
) -> int:
    deadline = time.time() + timeout_seconds
    state_value = governor.functions.state(proposal_id).call()
    while state_value not in desired_states:
        if time.time() > deadline:
            raise TimeoutError(
                "Timed out waiting for proposal "
                f"{proposal_id} to reach one of {sorted(desired_states)}. Current state is {proposal_state_name(state_value)}."
            )
        time.sleep(poll_interval_seconds)
        state_value = governor.functions.state(proposal_id).call()
    return state_value


def snapshot_treasury_state(treasury: Contract) -> dict[str, Any]:
    liquid_weth = treasury.functions.liquidWethBalance().call()
    supplied_weth = treasury.functions.suppliedWethBalance().call()
    total_managed_weth = treasury.functions.totalManagedWeth().call()
    min_liquid_reserve_bps, max_single_grant_bps, stale_price_threshold = treasury.functions.riskPolicy().call()
    nav_usd = treasury.functions.navUsd().call()

    return {
        "liquidWeth": str(liquid_weth),
        "suppliedWeth": str(supplied_weth),
        "totalManagedWeth": str(total_managed_weth),
        "navUsd": str(nav_usd),
        "riskPolicy": {
            "minLiquidReserveBps": min_liquid_reserve_bps,
            "maxSingleGrantBps": max_single_grant_bps,
            "stalePriceThreshold": stale_price_threshold,
        },
    }


def snapshot_votes(token: Contract, participants: dict[str, str]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for label, address in participants.items():
        snapshot[label] = {
            "address": address,
            "tokenBalance": str(token.functions.balanceOf(address).call()),
            "currentVotes": str(token.functions.getVotes(address).call()),
            "delegate": token.functions.delegates(address).call(),
        }
    return snapshot


def snapshot_project_state(treasury: Contract, project_id: str) -> dict[str, Any]:
    project = treasury.functions.getProject(Web3.to_bytes(hexstr=project_id)).call()
    return {
        "recipient": project[0],
        "maxBudgetWeth": str(project[1]),
        "releasedWeth": str(project[2]),
        "milestoneCount": project[3],
        "milestonesReleased": project[4],
        "active": project[5],
    }


def build_empty_evidence_manifest(
    deployment_manifest: dict[str, Any],
    project_recipient: str | None = None,
) -> dict[str, Any]:
    project = make_project_definition(project_recipient) if project_recipient is not None else None
    return {
        "network": deployment_manifest.get("network", {"name": "sepolia", "chainId": SEPOLIA_CHAIN_ID}),
        "contracts": deployment_manifest.get("contracts", {}),
        "participants": {},
        "project": project,
        "seedState": {},
        "proposals": {},
        "etherscanLinks": {
            "addresses": {},
            "transactions": {},
        },
    }


def update_etherscan_links(
    deployment_manifest: dict[str, Any],
    evidence_manifest: dict[str, Any],
) -> dict[str, Any]:
    evidence_manifest.setdefault("etherscanLinks", {})
    evidence_manifest["etherscanLinks"].setdefault("addresses", {})
    evidence_manifest["etherscanLinks"].setdefault("transactions", {})

    for name, address in deployment_manifest.get("contracts", {}).items():
        evidence_manifest["etherscanLinks"]["addresses"][name] = etherscan_address_url(address)

    for name, address in deployment_manifest.get("externalProtocols", {}).items():
        evidence_manifest["etherscanLinks"]["addresses"][name] = etherscan_address_url(address)

    for name, tx_hash in deployment_manifest.get("transactions", {}).items():
        evidence_manifest["etherscanLinks"]["transactions"][name] = etherscan_tx_url(tx_hash)

    fund_treasury = evidence_manifest.get("seedState", {}).get("fundTreasury", {})
    if fund_treasury.get("transactionHash"):
        evidence_manifest["etherscanLinks"]["transactions"]["seedState.fundTreasury"] = etherscan_tx_url(
            fund_treasury["transactionHash"]
        )

    for voter_label, tx_record in evidence_manifest.get("seedState", {}).get("selfDelegations", {}).items():
        tx_hash = tx_record.get("transactionHash")
        if tx_hash is not None:
            evidence_manifest["etherscanLinks"]["transactions"][f"seedState.selfDelegations.{voter_label}"] = (
                etherscan_tx_url(tx_hash)
            )

    for proposal_slug, proposal_record in evidence_manifest.get("proposals", {}).items():
        transactions = proposal_record.get("transactions", {})
        if transactions.get("propose"):
            evidence_manifest["etherscanLinks"]["transactions"][f"{proposal_slug}.propose"] = etherscan_tx_url(
                transactions["propose"]
            )
        for voter_label, tx_hash in transactions.get("votes", {}).items():
            if tx_hash is not None:
                evidence_manifest["etherscanLinks"]["transactions"][
                    f"{proposal_slug}.vote.{voter_label}"
                ] = etherscan_tx_url(tx_hash)
        if transactions.get("queue"):
            evidence_manifest["etherscanLinks"]["transactions"][f"{proposal_slug}.queue"] = etherscan_tx_url(
                transactions["queue"]
            )
        if transactions.get("execute"):
            evidence_manifest["etherscanLinks"]["transactions"][f"{proposal_slug}.execute"] = etherscan_tx_url(
                transactions["execute"]
            )

    return evidence_manifest


def env_default(name: str) -> str | None:
    return os.environ.get(name)