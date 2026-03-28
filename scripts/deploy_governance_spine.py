from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import rlp
from cli_security import resolve_env_or_cli
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_utils import keccak, to_canonical_address, to_checksum_address as eth_utils_to_checksum_address
from web3 import Web3
from web3.contract import Contract


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts"
DEFAULT_OUTPUT_PATH = ROOT / "deployments" / "deployments.sepolia.json"

TOKEN_ARTIFACT = ARTIFACTS_DIR / "src" / "governance" / "CampusInnovationFundToken" / "CampusInnovationFundToken.json"
GOVERNOR_ARTIFACT = ARTIFACTS_DIR / "src" / "governance" / "InnovationGovernor" / "InnovationGovernor.json"
REPUTATION_ARTIFACT = ARTIFACTS_DIR / "src" / "governance" / "ReputationRegistry" / "ReputationRegistry.json"
HYBRID_VOTES_ARTIFACT = ARTIFACTS_DIR / "src" / "governance" / "HybridVotesAdapter" / "HybridVotesAdapter.json"
TIMELOCK_ARTIFACT = (
    ARTIFACTS_DIR
    / "lib"
    / "openzeppelin-contracts"
    / "contracts"
    / "governance"
    / "TimelockController"
    / "TimelockController.json"
)

TOKEN_UNIT = 10**18
INITIAL_VOTER_ALLOCATION = 200_000 * TOKEN_UNIT
INITIAL_GOVERNANCE_RESERVE = 400_000 * TOKEN_UNIT
TIMELOCK_MIN_DELAY_SECONDS = 120
GOVERNANCE_DEPLOYMENT_COUNT = 5
GOVERNANCE_POST_DEPLOYMENT_CALL_COUNT = 8
TREASURY_PRE_FUNDING_DEPLOYMENTS = 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deploy the governance spine to Sepolia.",
        epilog="Prefer SEPOLIA_PRIVATE_KEY in the environment. Passing --private-key directly is discouraged because shells persist history.",
    )
    parser.add_argument("--rpc-url", default=None, help="Override SEPOLIA_RPC_URL for this run.")
    parser.add_argument(
        "--private-key",
        default=None,
        help="UNSAFE override for SEPOLIA_PRIVATE_KEY. Prefer the environment variable to avoid shell history leaks.",
    )
    parser.add_argument("--voter-a", default=os.environ.get("CIF_VOTER_A"))
    parser.add_argument("--voter-b", default=os.environ.get("CIF_VOTER_B"))
    parser.add_argument("--voter-c", default=os.environ.get("CIF_VOTER_C"))
    parser.add_argument("--reserve-recipient", default=os.environ.get("CIF_GOVERNANCE_RESERVE"))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument(
        "--gas-price-wei",
        type=int,
        default=None,
        help="Override the gas price used for every transaction.",
    )
    return parser.parse_args()


def require_value(value: str | None, name: str) -> str:
    if value is None or value.strip() == "":
        raise ValueError(f"Missing required parameter: {name}")
    return value


def to_checksum_address(w3: Web3, raw_value: str, label: str) -> str:
    if not Web3.is_address(raw_value):
        raise ValueError(f"Invalid address for {label}: {raw_value}")
    return w3.to_checksum_address(raw_value)


def load_artifact(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing artifact: {path}. Run `python scripts/compile_contracts.py` before deployment."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def build_contract(w3: Web3, artifact: dict[str, Any], address: str | None = None) -> Contract:
    if address is None:
        return w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
    return w3.eth.contract(address=address, abi=artifact["abi"])


def predict_create_address(deployer: str, nonce: int) -> str:
    encoded = rlp.encode([to_canonical_address(deployer), nonce])
    return eth_utils_to_checksum_address(keccak(encoded)[12:])


class TransactionSender:
    def __init__(self, w3: Web3, account: LocalAccount, gas_price_wei: int | None) -> None:
        self.w3 = w3
        self.account = account
        self.gas_price_wei = gas_price_wei
        self.nonce = w3.eth.get_transaction_count(account.address)

    @staticmethod
    def _apply_gas_buffer(estimated_gas: int) -> int:
        return max(estimated_gas + 25_000, (estimated_gas * 120) // 100)

    def _base_transaction(self) -> dict[str, Any]:
        return {
            "from": self.account.address,
            "nonce": self.nonce,
            "chainId": self.w3.eth.chain_id,
            "gasPrice": self.gas_price_wei if self.gas_price_wei is not None else self.w3.eth.gas_price,
        }

    def send_contract_deployment(self, contract: Contract, constructor_args: list[Any]) -> tuple[str, str]:
        transaction = contract.constructor(*constructor_args).build_transaction(self._base_transaction())
        estimated_gas = self.w3.eth.estimate_gas(transaction)
        transaction["gas"] = self._apply_gas_buffer(estimated_gas)
        signed = self.account.sign_transaction(transaction)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.nonce += 1
        if receipt.get("status") != 1:
            raise RuntimeError(f"Contract deployment failed: {tx_hash.hex()}")
        return receipt["contractAddress"], tx_hash.hex()

    def send_call(self, call, label: str | None = None) -> str:
        transaction = call.build_transaction(self._base_transaction())
        estimated_gas = self.w3.eth.estimate_gas(transaction)
        transaction["gas"] = self._apply_gas_buffer(estimated_gas)
        signed = self.account.sign_transaction(transaction)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.nonce += 1
        if receipt.get("status") != 1:
            raise RuntimeError(
                f"Transaction failed while executing {label or 'contract call'}: {tx_hash.hex()}"
            )
        return tx_hash.hex()


def main() -> None:
    args = parse_args()

    rpc_url = require_value(
        resolve_env_or_cli(args.rpc_url, "SEPOLIA_RPC_URL", cli_flag="--rpc-url"),
        "rpc-url or SEPOLIA_RPC_URL",
    )
    private_key = require_value(
        resolve_env_or_cli(
            args.private_key,
            "SEPOLIA_PRIVATE_KEY",
            cli_flag="--private-key",
            sensitive=True,
        ),
        "SEPOLIA_PRIVATE_KEY or --private-key",
    )

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError("Unable to connect to the configured RPC endpoint.")

    account: LocalAccount = Account.from_key(private_key)
    voter_a = to_checksum_address(w3, require_value(args.voter_a, "voter-a or CIF_VOTER_A"), "voter-a")
    voter_b = to_checksum_address(w3, require_value(args.voter_b, "voter-b or CIF_VOTER_B"), "voter-b")
    voter_c = to_checksum_address(w3, require_value(args.voter_c, "voter-c or CIF_VOTER_C"), "voter-c")
    reserve_recipient = to_checksum_address(
        w3,
        require_value(args.reserve_recipient, "reserve-recipient or CIF_GOVERNANCE_RESERVE"),
        "reserve-recipient",
    )

    token_artifact = load_artifact(TOKEN_ARTIFACT)
    governor_artifact = load_artifact(GOVERNOR_ARTIFACT)
    reputation_artifact = load_artifact(REPUTATION_ARTIFACT)
    hybrid_votes_artifact = load_artifact(HYBRID_VOTES_ARTIFACT)
    timelock_artifact = load_artifact(TIMELOCK_ARTIFACT)

    tx = TransactionSender(w3=w3, account=account, gas_price_wei=args.gas_price_wei)

    predicted_timelock_address = predict_create_address(account.address, tx.nonce + 1)
    # FundingRegistry is deployed in the second script after:
    # 1. every governance-spine deployment transaction,
    # 2. every post-deployment governance setup call in this script, and
    # 3. the TreasuryOracle deployment that precedes FundingRegistry there.
    predicted_funding_registry_address = predict_create_address(
        account.address,
        tx.nonce
        + GOVERNANCE_DEPLOYMENT_COUNT
        + GOVERNANCE_POST_DEPLOYMENT_CALL_COUNT
        + TREASURY_PRE_FUNDING_DEPLOYMENTS,
    )

    token_contract = build_contract(w3, token_artifact)
    token_address, token_deploy_tx = tx.send_contract_deployment(token_contract, [account.address])

    timelock_contract = build_contract(w3, timelock_artifact)
    timelock_address, timelock_deploy_tx = tx.send_contract_deployment(
        timelock_contract,
        [TIMELOCK_MIN_DELAY_SECONDS, [], [Web3.to_checksum_address("0x0000000000000000000000000000000000000000")], account.address],
    )
    if timelock_address != predicted_timelock_address:
        raise RuntimeError(
            f"Predicted timelock address mismatch: expected {predicted_timelock_address}, got {timelock_address}"
        )

    reputation_contract = build_contract(w3, reputation_artifact)
    reputation_address, reputation_deploy_tx = tx.send_contract_deployment(
        reputation_contract,
        [timelock_address, predicted_funding_registry_address],
    )

    hybrid_votes_contract = build_contract(w3, hybrid_votes_artifact)
    hybrid_votes_address, hybrid_votes_deploy_tx = tx.send_contract_deployment(
        hybrid_votes_contract,
        [token_address, reputation_address],
    )

    governor_contract = build_contract(w3, governor_artifact)
    governor_address, governor_deploy_tx = tx.send_contract_deployment(
        governor_contract,
        [hybrid_votes_address, timelock_address],
    )

    token_instance = build_contract(w3, token_artifact, token_address)
    timelock_instance = build_contract(w3, timelock_artifact, timelock_address)

    mint_transactions = {
        "mintVoterA": tx.send_call(
            token_instance.functions.mint(voter_a, INITIAL_VOTER_ALLOCATION),
            label="mintVoterA",
        ),
        "mintVoterB": tx.send_call(
            token_instance.functions.mint(voter_b, INITIAL_VOTER_ALLOCATION),
            label="mintVoterB",
        ),
        "mintVoterC": tx.send_call(
            token_instance.functions.mint(voter_c, INITIAL_VOTER_ALLOCATION),
            label="mintVoterC",
        ),
        "mintGovernanceReserve": tx.send_call(
            token_instance.functions.mint(reserve_recipient, INITIAL_GOVERNANCE_RESERVE),
            label="mintGovernanceReserve",
        ),
    }

    proposer_role = timelock_instance.functions.PROPOSER_ROLE().call()
    canceller_role = timelock_instance.functions.CANCELLER_ROLE().call()
    admin_role = timelock_instance.functions.DEFAULT_ADMIN_ROLE().call()

    timelock_role_transactions = {
        "grantProposerRole": tx.send_call(
            timelock_instance.functions.grantRole(proposer_role, governor_address),
            label="grantProposerRole",
        ),
        "grantCancellerRole": tx.send_call(
            timelock_instance.functions.grantRole(canceller_role, governor_address),
            label="grantCancellerRole",
        ),
        "renounceAdminRole": tx.send_call(
            timelock_instance.functions.renounceRole(admin_role, account.address),
            label="renounceAdminRole",
        ),
    }

    expected_balances = {
        "voterA": (voter_a, INITIAL_VOTER_ALLOCATION),
        "voterB": (voter_b, INITIAL_VOTER_ALLOCATION),
        "voterC": (voter_c, INITIAL_VOTER_ALLOCATION),
        "governanceReserve": (reserve_recipient, INITIAL_GOVERNANCE_RESERVE),
    }
    for label, (recipient, expected_balance) in expected_balances.items():
        actual_balance = token_instance.functions.balanceOf(recipient).call()
        if actual_balance != expected_balance:
            raise RuntimeError(
                f"Token allocation mismatch for {label}: expected {expected_balance}, got {actual_balance} "
                f"at {recipient}."
            )

    token_ownership_tx = tx.send_call(
        token_instance.functions.renounceOwnership(),
        label="renounceTokenOwnership",
    )

    max_supply = token_instance.functions.maxSupply().call()
    total_supply = token_instance.functions.totalSupply().call()
    owner = token_instance.functions.owner().call()

    if total_supply != max_supply:
        raise RuntimeError(f"Token total supply mismatch: expected {max_supply}, got {total_supply}")

    if owner != "0x0000000000000000000000000000000000000000":
        raise RuntimeError(f"Token ownership was not renounced. Current owner: {owner}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    deployment_manifest = {
        "network": {
            "name": "sepolia",
            "chainId": w3.eth.chain_id,
        },
        "config": {
            "timelockMinDelaySeconds": TIMELOCK_MIN_DELAY_SECONDS,
            "initialAllocations": {
                "voterA": str(INITIAL_VOTER_ALLOCATION),
                "voterB": str(INITIAL_VOTER_ALLOCATION),
                "voterC": str(INITIAL_VOTER_ALLOCATION),
                "governanceReserve": str(INITIAL_GOVERNANCE_RESERVE),
            },
        },
        "contracts": {
            "CampusInnovationFundToken": token_address,
            "ReputationRegistry": reputation_address,
            "HybridVotesAdapter": hybrid_votes_address,
            "TimelockController": timelock_address,
            "InnovationGovernor": governor_address,
        },
        "allocationRecipients": {
            "voterA": voter_a,
            "voterB": voter_b,
            "voterC": voter_c,
            "governanceReserve": reserve_recipient,
        },
        "transactions": {
            "deployToken": token_deploy_tx,
            "deployTimelock": timelock_deploy_tx,
            "deployReputationRegistry": reputation_deploy_tx,
            "deployHybridVotesAdapter": hybrid_votes_deploy_tx,
            "deployGovernor": governor_deploy_tx,
            **mint_transactions,
            **timelock_role_transactions,
            "renounceTokenOwnership": token_ownership_tx,
        },
        "constructorArgs": {
            "ReputationRegistry": [timelock_address, predicted_funding_registry_address],
            "HybridVotesAdapter": [token_address, reputation_address],
            "InnovationGovernor": [hybrid_votes_address, timelock_address],
        },
    }

    output_path.write_text(json.dumps(deployment_manifest, indent=2), encoding="utf-8")
    print(f"Deployment manifest written to {output_path}")


if __name__ == "__main__":
    main()
