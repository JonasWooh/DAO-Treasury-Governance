from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.contract import Contract
from web3.exceptions import ContractCustomError, ContractLogicError


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts"

DEFAULT_DEPLOYMENT_MANIFEST = ROOT / "deployments" / "deployments.sepolia.json"
DEFAULT_SCENARIO_MANIFEST = ROOT / "deployments" / "proposal_scenarios.sepolia.json"
DEFAULT_EVIDENCE_MANIFEST = ROOT / "deployments" / "demo_evidence.sepolia.json"
DEFAULT_FUNDING_STATE_MANIFEST = ROOT / "deployments" / "funding_state.sepolia.json"
DEFAULT_EVIDENCE_MARKDOWN = ROOT / "deployments" / "demo_evidence.sepolia.md"
DEFAULT_SCREENSHOT_CHECKLIST = ROOT / "evidence" / "screenshots" / "screenshot-checklist.sepolia.md"

SEPOLIA_CHAIN_ID = 11155111
SEPOLIA_ETHERSCAN_BASE_URL = "https://sepolia.etherscan.io"

TOKEN_UNIT = 10**18
INITIAL_VOTER_ALLOCATION = 200_000 * TOKEN_UNIT
INITIAL_MEMBER_REPUTATION = 100
DEMO_TREASURY_FUNDING_WETH = 3 * TOKEN_UNIT
DEMO_PROJECT_MAX_BUDGET_WETH = TOKEN_UNIT // 5
DEMO_AAVE_DEPOSIT_WETH = (3 * TOKEN_UNIT) // 5
DEMO_MILESTONE_PAYOUT_WETH = TOKEN_UNIT // 10
DEMO_POST_PROPOSAL2_LIQUID_WETH = DEMO_TREASURY_FUNDING_WETH - DEMO_AAVE_DEPOSIT_WETH
DEMO_POST_PROPOSAL3_SUPPLIED_WETH = DEMO_AAVE_DEPOSIT_WETH - DEMO_MILESTONE_PAYOUT_WETH
DEMO_POST_PROPOSAL3_TOTAL_MANAGED_WETH = DEMO_TREASURY_FUNDING_WETH - DEMO_MILESTONE_PAYOUT_WETH

PROJECT_NAME = "Smart Recycling Kiosk"
PROJECT_KEY = "SMART_RECYCLING_KIOSK"
DEMO_PROPOSAL_TITLE = "Smart Recycling Kiosk Pilot"
DEMO_PROPOSAL_METADATA_URI = "ipfs://campus-innovation-fund/sepolia/proposals/smart-recycling-kiosk-v2"
DEMO_PROPOSAL_1_DESCRIPTION = "Proposal 1: Approve Smart Recycling Kiosk project"
DEMO_PROPOSAL_2_DESCRIPTION = "Proposal 2: Deposit 0.6 WETH into Aave"
DEMO_PROPOSAL_3_DESCRIPTION = "Proposal 3: Withdraw 0.1 WETH and release milestone 0"
DEMO_MILESTONE_DESCRIPTIONS = [
    "Install kiosk hardware and telemetry on campus",
    "Publish pilot impact report and expansion plan",
]
DEMO_MILESTONE_EVIDENCE_URIS = {
    0: "ipfs://campus-innovation-fund/sepolia/evidence/smart-recycling-kiosk/milestone-0",
    1: "ipfs://campus-innovation-fund/sepolia/evidence/smart-recycling-kiosk/milestone-1",
}
DEMO_BOOTSTRAP_DESCRIPTION = "Bootstrap Demo Members: register voterA, voterB, and voterC with initial reputation"

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

FUNDING_PROPOSAL_STATUS_NAMES = {
    0: "Submitted",
    1: "Voting",
    2: "Approved",
    3: "Rejected",
    4: "Cancelled",
}

FUNDING_PROJECT_STATUS_NAMES = {
    0: "Active",
    1: "Completed",
    2: "Cancelled",
}

FUNDING_MILESTONE_STATE_NAMES = {
    0: "Locked",
    1: "OpenForClaim",
    2: "ClaimSubmitted",
    3: "ClaimRejected",
    4: "Released",
}

TOKEN_ARTIFACT = ARTIFACTS_DIR / "src" / "governance" / "CampusInnovationFundToken" / "CampusInnovationFundToken.json"
GOVERNOR_ARTIFACT = ARTIFACTS_DIR / "src" / "governance" / "InnovationGovernor" / "InnovationGovernor.json"
REPUTATION_ARTIFACT = ARTIFACTS_DIR / "src" / "governance" / "ReputationRegistry" / "ReputationRegistry.json"
HYBRID_VOTES_ARTIFACT = ARTIFACTS_DIR / "src" / "governance" / "HybridVotesAdapter" / "HybridVotesAdapter.json"
FUNDING_REGISTRY_ARTIFACT = ARTIFACTS_DIR / "src" / "funding" / "FundingRegistry" / "FundingRegistry.json"
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
        self.nonce = w3.eth.get_transaction_count(account.address, "pending")

    @staticmethod
    def _apply_gas_buffer(estimated_gas: int) -> int:
        return max(estimated_gas + 25_000, (estimated_gas * 120) // 100)

    def _next_nonce(self) -> int:
        onchain_nonce = self.w3.eth.get_transaction_count(self.account.address, "pending")
        self.nonce = max(self.nonce, onchain_nonce)
        return self.nonce

    def _base_transaction(self) -> dict[str, Any]:
        return {
            "from": self.account.address,
            "nonce": self._next_nonce(),
            "chainId": self.w3.eth.chain_id,
            "gasPrice": self.gas_price_wei if self.gas_price_wei is not None else self.w3.eth.gas_price,
        }

    def send_call(self, call) -> tuple[str, Any]:
        transaction = call.build_transaction(self._base_transaction())
        estimated_gas = self.w3.eth.estimate_gas(transaction)
        transaction["gas"] = self._apply_gas_buffer(estimated_gas)
        signed = self.account.sign_transaction(transaction)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.nonce += 1
        if receipt.get("status") != 1:
            raise RuntimeError(f"Transaction failed: {tx_hash.hex()}")
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
    return Web3.to_hex(Web3.keccak(text=description))


def timelock_salt(governor_address: str, description_hash_hex: str) -> str:
    governor_bytes = Web3.to_bytes(hexstr=governor_address)
    description_hash_bytes = Web3.to_bytes(hexstr=description_hash_hex)
    padded_governor = governor_bytes + (b"\x00" * (32 - len(governor_bytes)))
    salt_bytes = bytes(left ^ right for left, right in zip(padded_governor, description_hash_bytes))
    return Web3.to_hex(salt_bytes)


def proposal_state_name(state_value: int) -> str:
    return PROPOSAL_STATE_NAMES.get(state_value, f"Unknown({state_value})")


def funding_proposal_status_name(state_value: int) -> str:
    return FUNDING_PROPOSAL_STATUS_NAMES.get(state_value, f"Unknown({state_value})")


def funding_project_status_name(state_value: int) -> str:
    return FUNDING_PROJECT_STATUS_NAMES.get(state_value, f"Unknown({state_value})")


def funding_milestone_state_name(state_value: int) -> str:
    return FUNDING_MILESTONE_STATE_NAMES.get(state_value, f"Unknown({state_value})")


def etherscan_address_url(address: str) -> str:
    return f"{SEPOLIA_ETHERSCAN_BASE_URL}/address/{address}"


def etherscan_tx_url(tx_hash: str) -> str:
    return f"{SEPOLIA_ETHERSCAN_BASE_URL}/tx/{tx_hash}"


def load_required_contracts(w3: Web3, deployment_manifest: dict[str, Any]) -> dict[str, Contract]:
    contracts = deployment_manifest.get("contracts", {})
    external_protocols = deployment_manifest.get("externalProtocols", {})

    required_contract_names = [
        "CampusInnovationFundToken",
        "ReputationRegistry",
        "HybridVotesAdapter",
        "InnovationGovernor",
        "FundingRegistry",
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
        "reputation": build_contract_from_artifact(w3, REPUTATION_ARTIFACT, contracts["ReputationRegistry"]),
        "hybridVotes": build_contract_from_artifact(w3, HYBRID_VOTES_ARTIFACT, contracts["HybridVotesAdapter"]),
        "governor": build_contract_from_artifact(w3, GOVERNOR_ARTIFACT, contracts["InnovationGovernor"]),
        "fundingRegistry": build_contract_from_artifact(w3, FUNDING_REGISTRY_ARTIFACT, contracts["FundingRegistry"]),
        "timelock": build_contract_from_artifact(w3, TIMELOCK_ARTIFACT, contracts["TimelockController"]),
        "treasury": build_contract_from_artifact(w3, TREASURY_ARTIFACT, contracts["InnovationTreasury"]),
        "weth": build_minimal_erc20(w3, external_protocols["WETH"]),
    }


def encode_call(contract: Contract, function_name: str, *args: Any) -> str:
    contract_function = getattr(contract.functions, function_name)(*args)
    return contract_function._encode_transaction_data()


def bytes32_hex(value: Any) -> str:
    if isinstance(value, str):
        return value
    return Web3.to_hex(value)


def make_project_definition(
    funding_registry: Contract,
    funding_proposal_id: int,
    proposer: str,
    recipient: str,
) -> dict[str, Any]:
    project_id = bytes32_hex(
        funding_registry.functions.deriveProjectId(funding_proposal_id, proposer, recipient).call()
    )
    return {
        "name": PROJECT_NAME,
        "projectKey": PROJECT_KEY,
        "projectId": project_id,
        "sourceProposalId": str(funding_proposal_id),
        "proposer": proposer,
        "recipient": recipient,
        "maxBudgetWeth": str(DEMO_PROJECT_MAX_BUDGET_WETH),
        "milestoneCount": len(DEMO_MILESTONE_DESCRIPTIONS),
        "milestonePayoutsWeth": {
            f"milestone{index}": str(amount)
            for index, amount in enumerate([DEMO_MILESTONE_PAYOUT_WETH, DEMO_MILESTONE_PAYOUT_WETH])
        },
    }


def build_demo_scenarios(
    governor: Contract,
    timelock: Contract,
    treasury: Contract,
    funding_registry: Contract,
    proposer: str,
    recipient: str,
    voter_addresses: dict[str, str],
    funding_proposal_id: int,
) -> dict[str, Any]:
    project = make_project_definition(funding_registry, funding_proposal_id, proposer, recipient)
    proposals: list[dict[str, Any]] = []
    proposal_specs = [
        {
            "slug": "proposal1_approve_project",
            "title": "Proposal 1",
            "description": DEMO_PROPOSAL_1_DESCRIPTION,
            "targets": [funding_registry.address, treasury.address],
            "values": [0, 0],
            "calldatas": [
                encode_call(
                    funding_registry,
                    "markProposalApproved",
                    funding_proposal_id,
                    Web3.to_bytes(hexstr=project["projectId"]),
                ),
                encode_call(
                    treasury,
                    "approveProject",
                    Web3.to_bytes(hexstr=project["projectId"]),
                    recipient,
                    DEMO_PROJECT_MAX_BUDGET_WETH,
                    len(DEMO_MILESTONE_DESCRIPTIONS),
                ),
            ],
            "workflow": {
                "fundingProposalId": str(funding_proposal_id),
                "projectId": project["projectId"],
                "settledVoters": list(voter_addresses.values()),
            },
            "expectedOutcome": {
                "fundingProposalStatus": "Approved",
                "projectStatus": "Active",
                "projectReleasedWeth": "0",
                "nextClaimableMilestone": 0,
                "treasuryLiquidWeth": str(DEMO_TREASURY_FUNDING_WETH),
                "treasurySuppliedWeth": "0",
            },
        },
        {
            "slug": "proposal2_deposit_idle_funds",
            "title": "Proposal 2",
            "description": DEMO_PROPOSAL_2_DESCRIPTION,
            "targets": [treasury.address],
            "values": [0],
            "calldatas": [encode_call(treasury, "depositIdleFunds", DEMO_AAVE_DEPOSIT_WETH)],
            "workflow": {
                "treasuryAction": "depositIdleFunds",
                "amountWeth": str(DEMO_AAVE_DEPOSIT_WETH),
            },
            "expectedOutcome": {
                "treasuryLiquidWeth": str(DEMO_POST_PROPOSAL2_LIQUID_WETH),
                "treasurySuppliedWeth": str(DEMO_AAVE_DEPOSIT_WETH),
                "treasuryTotalManagedWeth": str(DEMO_TREASURY_FUNDING_WETH),
            },
        },
        {
            "slug": "proposal3_release_milestone",
            "title": "Proposal 3",
            "description": DEMO_PROPOSAL_3_DESCRIPTION,
            "targets": [treasury.address, treasury.address, funding_registry.address],
            "values": [0, 0, 0],
            "calldatas": [
                encode_call(treasury, "withdrawIdleFunds", DEMO_MILESTONE_PAYOUT_WETH),
                encode_call(
                    treasury,
                    "releaseMilestone",
                    Web3.to_bytes(hexstr=project["projectId"]),
                    0,
                    DEMO_MILESTONE_PAYOUT_WETH,
                ),
                encode_call(funding_registry, "markMilestoneReleased", funding_proposal_id, 0),
            ],
            "workflow": {
                "fundingProposalId": str(funding_proposal_id),
                "projectId": project["projectId"],
                "milestoneIndex": 0,
                "evidenceURI": DEMO_MILESTONE_EVIDENCE_URIS[0],
                "settledVoters": list(voter_addresses.values()),
            },
            "expectedOutcome": {
                "projectReleasedWeth": str(DEMO_MILESTONE_PAYOUT_WETH),
                "projectNextClaimableMilestone": 1,
                "projectStatus": "Active",
                "milestone0State": "Released",
                "treasuryLiquidWeth": str(DEMO_POST_PROPOSAL2_LIQUID_WETH),
                "treasurySuppliedWeth": str(DEMO_POST_PROPOSAL3_SUPPLIED_WETH),
                "treasuryTotalManagedWeth": str(DEMO_POST_PROPOSAL3_TOTAL_MANAGED_WETH),
                "proposerMilestoneReward": "4",
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
        salt = timelock_salt(governor.address, desc_hash)
        operation_id = timelock.functions.hashOperationBatch(
            spec["targets"],
            spec["values"],
            spec["calldatas"],
            Web3.to_bytes(hexstr=ZERO_BYTES32),
            Web3.to_bytes(hexstr=salt),
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
                "operationId": bytes32_hex(operation_id),
                "workflow": spec["workflow"],
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
    except ContractCustomError:
        return None
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


def wait_until_operation_ready(
    timelock: Contract,
    operation_id_hex: str,
    poll_interval_seconds: float,
    timeout_seconds: float,
) -> None:
    deadline = time.time() + timeout_seconds
    while not timelock.functions.isOperationReady(Web3.to_bytes(hexstr=operation_id_hex)).call():
        if time.time() > deadline:
            raise TimeoutError(f"Timed out waiting for timelock operation {operation_id_hex} to become ready.")
        time.sleep(poll_interval_seconds)


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


def snapshot_votes(
    token: Contract,
    participants: dict[str, str],
    hybrid_votes: Contract | None = None,
    reputation_registry: Contract | None = None,
) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for label, address in participants.items():
        entry: dict[str, Any] = {
            "address": address,
            "tokenBalance": str(token.functions.balanceOf(address).call()),
            "currentVotes": str(token.functions.getVotes(address).call()),
            "delegate": token.functions.delegates(address).call(),
        }
        if hybrid_votes is not None:
            entry["hybridVotes"] = str(hybrid_votes.functions.getVotes(address).call())
        if reputation_registry is not None:
            member = reputation_registry.functions.getMember(address).call()
            entry["member"] = {
                "isRegistered": bool(member[0]),
                "isActive": bool(member[1]),
                "currentReputation": str(member[2]),
            }
        snapshot[label] = entry
    return snapshot


def snapshot_project_state(funding_registry: Contract, project_id: str) -> dict[str, Any]:
    project = funding_registry.functions.getProject(Web3.to_bytes(hexstr=project_id)).call()
    return {
        "projectId": bytes32_hex(project[0]),
        "sourceProposalId": str(project[1]),
        "recipient": project[2],
        "approvedBudgetWeth": str(project[3]),
        "releasedWeth": str(project[4]),
        "nextClaimableMilestone": project[5],
        "status": funding_project_status_name(project[6]),
    }


def snapshot_proposal_state(funding_registry: Contract, proposal_id: int) -> dict[str, Any]:
    proposal = funding_registry.functions.getProposal(proposal_id).call()
    return {
        "proposalId": str(proposal[0]),
        "proposer": proposal[1],
        "recipient": proposal[2],
        "title": proposal[3],
        "metadataURI": proposal[4],
        "requestedFundingWeth": str(proposal[5]),
        "milestoneCount": proposal[6],
        "status": funding_proposal_status_name(proposal[7]),
        "governorProposalId": str(proposal[8]),
        "projectId": bytes32_hex(proposal[9]),
    }


def snapshot_milestone_state(funding_registry: Contract, proposal_id: int, milestone_index: int) -> dict[str, Any]:
    milestone = funding_registry.functions.getMilestone(proposal_id, milestone_index).call()
    return {
        "index": milestone[0],
        "description": milestone[1],
        "amountWeth": str(milestone[2]),
        "evidenceURI": milestone[3],
        "state": funding_milestone_state_name(milestone[4]),
        "claimGovernorProposalId": str(milestone[5]),
    }


def build_funding_state_manifest(
    deployment_manifest: dict[str, Any],
    funding_registry: Contract,
    reputation_registry: Contract,
) -> dict[str, Any]:
    members: list[dict[str, Any]] = []
    active_member_count = 0
    member_count = funding_registry.functions.memberCount().call()
    for index in range(member_count):
        member = funding_registry.functions.getMemberByIndex(index).call()
        if member[2]:
            active_member_count += 1
        members.append(
            {
                "account": member[0],
                "isRegistered": bool(member[1]),
                "isActive": bool(member[2]),
                "currentReputation": str(member[3]),
            }
        )

    proposals: list[dict[str, Any]] = []
    milestones: list[dict[str, Any]] = []
    proposal_count = funding_registry.functions.proposalCount().call()
    for index in range(proposal_count):
        proposal = funding_registry.functions.getProposalByIndex(index).call()
        proposal_id = int(proposal[0])
        proposal_id_text = str(proposal_id)
        project_id_text = bytes32_hex(proposal[9])
        proposals.append(
            {
                "proposalId": proposal_id_text,
                "proposer": proposal[1],
                "recipient": proposal[2],
                "title": proposal[3],
                "metadataURI": proposal[4],
                "requestedFundingWeth": str(proposal[5]),
                "milestoneCount": proposal[6],
                "status": funding_proposal_status_name(proposal[7]),
                "governorProposalId": str(proposal[8]),
                "projectId": project_id_text,
            }
        )

        milestone_count = funding_registry.functions.milestoneCount(proposal_id).call()
        for milestone_index in range(milestone_count):
            milestone = funding_registry.functions.getMilestone(proposal_id, milestone_index).call()
            milestone_entry: dict[str, Any] = {
                "proposalId": proposal_id_text,
                "milestoneIndex": milestone[0],
                "description": milestone[1],
                "amountWeth": str(milestone[2]),
                "evidenceURI": milestone[3],
                "state": funding_milestone_state_name(milestone[4]),
                "claimGovernorProposalId": str(milestone[5]),
            }
            if project_id_text != ZERO_BYTES32:
                milestone_entry["projectId"] = project_id_text
            milestones.append(milestone_entry)

    projects: list[dict[str, Any]] = []
    project_count = funding_registry.functions.projectCount().call()
    for index in range(project_count):
        project = funding_registry.functions.getProjectByIndex(index).call()
        projects.append(
            {
                "projectId": bytes32_hex(project[0]),
                "sourceProposalId": str(project[1]),
                "recipient": project[2],
                "approvedBudgetWeth": str(project[3]),
                "releasedWeth": str(project[4]),
                "nextClaimableMilestone": project[5],
                "status": funding_project_status_name(project[6]),
            }
        )

    return {
        "configured": True,
        "network": deployment_manifest.get("network", {"name": "sepolia", "chainId": SEPOLIA_CHAIN_ID}),
        "contracts": deployment_manifest.get("contracts", {}),
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "members": members,
        "proposals": proposals,
        "projects": projects,
        "milestones": milestones,
        "reputationSummary": {
            "totalActiveReputation": str(reputation_registry.functions.totalActiveReputation().call()),
            "activeMemberCount": active_member_count,
        },
    }


def write_funding_state_manifest(
    path: Path,
    deployment_manifest: dict[str, Any],
    funding_registry: Contract,
    reputation_registry: Contract,
) -> dict[str, Any]:
    manifest = build_funding_state_manifest(deployment_manifest, funding_registry, reputation_registry)
    write_json(path, manifest)
    return manifest


def build_empty_evidence_manifest(
    deployment_manifest: dict[str, Any],
    project_recipient: str | None = None,
) -> dict[str, Any]:
    project: dict[str, Any] | None = None
    if project_recipient is not None:
        project = {
            "name": PROJECT_NAME,
            "projectKey": PROJECT_KEY,
            "recipient": project_recipient,
        }
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


def _iter_transaction_hashes(prefix: str, value: Any) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(_iter_transaction_hashes(next_prefix, child))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            next_prefix = f"{prefix}.{index}" if prefix else str(index)
            rows.extend(_iter_transaction_hashes(next_prefix, child))
    elif isinstance(value, str) and value.startswith("0x") and len(value) == 66:
        rows.append((prefix, value))
    return rows


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

    seed_state = evidence_manifest.get("seedState", {})
    fund_treasury = seed_state.get("fundTreasury", {})
    if fund_treasury.get("transactionHash"):
        evidence_manifest["etherscanLinks"]["transactions"]["seedState.fundTreasury"] = etherscan_tx_url(
            fund_treasury["transactionHash"]
        )

    for voter_label, tx_record in seed_state.get("selfDelegations", {}).items():
        tx_hash = tx_record.get("transactionHash")
        if tx_hash is not None:
            evidence_manifest["etherscanLinks"]["transactions"][f"seedState.selfDelegations.{voter_label}"] = (
                etherscan_tx_url(tx_hash)
            )

    bootstrap_transactions = seed_state.get("bootstrapMembers", {}).get("transactions", {})
    for label, tx_hash in _iter_transaction_hashes("seedState.bootstrapMembers", bootstrap_transactions):
        evidence_manifest["etherscanLinks"]["transactions"][label] = etherscan_tx_url(tx_hash)

    for proposal_slug, proposal_record in evidence_manifest.get("proposals", {}).items():
        for label, tx_hash in _iter_transaction_hashes(proposal_slug, proposal_record.get("transactions", {})):
            evidence_manifest["etherscanLinks"]["transactions"][label] = etherscan_tx_url(tx_hash)

    return evidence_manifest


def execute_governor_proposal(
    w3: Web3,
    governor: Contract,
    timelock: Contract,
    proposer_sender: TransactionSender,
    voter_senders: dict[str, TransactionSender],
    proposal_record: dict[str, Any],
    targets: list[str],
    values: list[int],
    calldatas: list[str],
    description: str,
    poll_interval_seconds: float,
    timeout_seconds: float,
    persist_callback: Callable[[], None],
) -> tuple[int, int]:
    desc_hash = description_hash(description)
    proposal_id = governor.functions.hashProposal(targets, values, calldatas, desc_hash).call()
    salt = timelock_salt(governor.address, desc_hash)
    operation_id = timelock.functions.hashOperationBatch(
        targets,
        values,
        calldatas,
        Web3.to_bytes(hexstr=ZERO_BYTES32),
        Web3.to_bytes(hexstr=salt),
    ).call()

    proposal_record["description"] = description
    proposal_record["descriptionHash"] = desc_hash
    proposal_record["proposalId"] = str(proposal_id)
    proposal_record["operationId"] = bytes32_hex(operation_id)
    transactions = proposal_record.setdefault("transactions", {})
    transactions.setdefault("propose", None)
    transactions.setdefault("votes", {})
    transactions.setdefault("queue", None)
    transactions.setdefault("execute", None)
    snapshots = proposal_record.setdefault("snapshots", {})

    state_value = safe_governor_state(governor, proposal_id)
    if state_value is None:
        propose_tx_hash, propose_receipt = proposer_sender.send_call(
            governor.functions.propose(targets, values, calldatas, description)
        )
        transactions["propose"] = propose_tx_hash
        snapshots["proposalCreated"] = {
            "blockNumber": propose_receipt["blockNumber"],
            "transactionHash": propose_tx_hash,
        }
        persist_callback()
        state_value = governor.functions.state(proposal_id).call()

    snapshot_block = governor.functions.proposalSnapshot(proposal_id).call()
    deadline_block = governor.functions.proposalDeadline(proposal_id).call()
    proposal_record["snapshotBlock"] = snapshot_block
    proposal_record["deadlineBlock"] = deadline_block
    proposal_record["proposer"] = proposer_sender.account.address

    if state_value == 0:
        wait_for_block_number(w3, snapshot_block + 1, poll_interval_seconds, timeout_seconds)
        state_value = governor.functions.state(proposal_id).call()

    if state_value == 1:
        for label, sender in voter_senders.items():
            if governor.functions.hasVoted(proposal_id, sender.account.address).call():
                transactions["votes"].setdefault(label, None)
                continue
            vote_tx_hash, _ = sender.send_call(governor.functions.castVote(proposal_id, VOTE_SUPPORT_FOR))
            transactions["votes"][label] = vote_tx_hash
            persist_callback()

        wait_for_block_number(w3, deadline_block + 1, poll_interval_seconds, timeout_seconds)
        state_value = governor.functions.state(proposal_id).call()

    if state_value in {2, 3, 6}:
        raise RuntimeError(
            f"Proposal {proposal_record.get('title', proposal_id)} entered terminal failure state {proposal_state_name(state_value)}."
        )

    if state_value == 4:
        queue_tx_hash, queue_receipt = proposer_sender.send_call(
            governor.functions.queue(targets, values, calldatas, desc_hash)
        )
        transactions["queue"] = queue_tx_hash
        proposal_record["queueEta"] = governor.functions.proposalEta(proposal_id).call()
        snapshots["queued"] = {
            "blockNumber": queue_receipt["blockNumber"],
            "transactionHash": queue_tx_hash,
        }
        persist_callback()
        state_value = governor.functions.state(proposal_id).call()

    if state_value == 5:
        eta = governor.functions.proposalEta(proposal_id).call()
        proposal_record["queueEta"] = eta
        wait_for_timestamp(w3, eta, poll_interval_seconds, timeout_seconds)
        wait_until_operation_ready(timelock, proposal_record["operationId"], poll_interval_seconds, timeout_seconds)
        execute_tx_hash, execute_receipt = proposer_sender.send_call(
            governor.functions.execute(targets, values, calldatas, desc_hash)
        )
        transactions["execute"] = execute_tx_hash
        snapshots["executed"] = {
            "blockNumber": execute_receipt["blockNumber"],
            "transactionHash": execute_tx_hash,
        }
        persist_callback()
        state_value = governor.functions.state(proposal_id).call()

    if state_value != 7:
        raise RuntimeError(
            "Proposal did not reach Executed state. "
            f"Current state is {proposal_state_name(state_value)} for proposal {proposal_id}."
        )

    proposal_votes = governor.functions.proposalVotes(proposal_id).call()
    proposal_record["finalState"] = proposal_state_name(state_value)
    proposal_record["finalVotes"] = {
        "againstVotes": str(proposal_votes[0]),
        "forVotes": str(proposal_votes[1]),
        "abstainVotes": str(proposal_votes[2]),
    }
    persist_callback()
    return proposal_id, state_value


def env_default(name: str) -> str | None:
    return os.environ.get(name)
