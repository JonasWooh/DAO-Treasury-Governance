from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import rlp
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_utils import keccak, to_canonical_address, to_checksum_address
from web3 import Web3
from web3.contract import Contract


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts"
DEFAULT_PROTOCOL_CONFIG = ROOT / "config" / "sepolia.protocols.json"
DEFAULT_OUTPUT_PATH = ROOT / "deployments" / "deployments.sepolia.json"

ORACLE_ARTIFACT = ARTIFACTS_DIR / "src" / "oracle" / "TreasuryOracle" / "TreasuryOracle.json"
FUNDING_REGISTRY_ARTIFACT = ARTIFACTS_DIR / "src" / "funding" / "FundingRegistry" / "FundingRegistry.json"
ADAPTER_ARTIFACT = ARTIFACTS_DIR / "src" / "adapters" / "AaveWethAdapter" / "AaveWethAdapter.json"
TREASURY_ARTIFACT = ARTIFACTS_DIR / "src" / "treasury" / "InnovationTreasury" / "InnovationTreasury.json"
SEPOLIA_CHAIN_ID = 11155111


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy the Treasury protocol stack to Sepolia.")
    parser.add_argument("--rpc-url", default=os.environ.get("SEPOLIA_RPC_URL"))
    parser.add_argument("--private-key", default=os.environ.get("SEPOLIA_PRIVATE_KEY"))
    parser.add_argument("--timelock", default=os.environ.get("CIF_TIMELOCK"))
    parser.add_argument("--governor", default=os.environ.get("CIF_GOVERNOR"))
    parser.add_argument("--reputation-registry", default=os.environ.get("CIF_REPUTATION_REGISTRY"))
    parser.add_argument("--protocol-config", default=str(DEFAULT_PROTOCOL_CONFIG))
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


def to_checked_address(w3: Web3, raw_value: str, label: str) -> str:
    if not Web3.is_address(raw_value):
        raise ValueError(f"Invalid address for {label}: {raw_value}")
    return w3.to_checksum_address(raw_value)


def predict_create_address(deployer: str, nonce: int) -> str:
    encoded = rlp.encode([to_canonical_address(deployer), nonce])
    return to_checksum_address(keccak(encoded)[12:])


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

    def send_contract_deployment(self, contract: Contract, constructor_args: list[Any]) -> tuple[str, str]:
        transaction = contract.constructor(*constructor_args).build_transaction(self._base_transaction())
        transaction["gas"] = self.w3.eth.estimate_gas(transaction)
        signed = self.account.sign_transaction(transaction)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.nonce += 1
        return receipt["contractAddress"], tx_hash.hex()


def load_protocol_config(w3: Web3, config_path: Path) -> dict[str, Any]:
    raw_config = json.loads(config_path.read_text(encoding="utf-8"))

    chain_id = raw_config.get("network", {}).get("chainId")
    if chain_id != SEPOLIA_CHAIN_ID:
        raise ValueError(f"Protocol config chainId must be {SEPOLIA_CHAIN_ID}, got {chain_id}")

    helper_stale_price_threshold = raw_config.get("chainlink", {}).get("helperStalePriceThreshold")
    if not isinstance(helper_stale_price_threshold, int) or helper_stale_price_threshold <= 0:
        raise ValueError("chainlink.helperStalePriceThreshold must be a positive integer")

    return {
        "network": raw_config["network"],
        "assets": {
            "weth": to_checked_address(w3, raw_config["assets"]["weth"], "assets.weth"),
        },
        "chainlink": {
            "ethUsdFeed": to_checked_address(w3, raw_config["chainlink"]["ethUsdFeed"], "chainlink.ethUsdFeed"),
            "helperStalePriceThreshold": helper_stale_price_threshold,
        },
        "aave": {
            "pool": to_checked_address(w3, raw_config["aave"]["pool"], "aave.pool"),
            "aWeth": to_checked_address(w3, raw_config["aave"]["aWeth"], "aave.aWeth"),
        },
    }


def main() -> None:
    args = parse_args()

    rpc_url = require_value(args.rpc_url, "rpc-url or SEPOLIA_RPC_URL")
    private_key = require_value(args.private_key, "private-key or SEPOLIA_PRIVATE_KEY")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError("Unable to connect to the configured RPC endpoint.")
    if w3.eth.chain_id != SEPOLIA_CHAIN_ID:
        raise RuntimeError(f"Connected to chainId {w3.eth.chain_id}, expected {SEPOLIA_CHAIN_ID}.")

    protocol_config = load_protocol_config(w3, Path(args.protocol_config))

    output_path = Path(args.output)
    if output_path.exists():
        deployment_manifest: dict[str, Any] = json.loads(output_path.read_text(encoding="utf-8"))
    else:
        deployment_manifest = {}

    governance_contracts = deployment_manifest.get("contracts", {})
    timelock_raw = args.timelock or governance_contracts.get("TimelockController")
    governor_raw = args.governor or governance_contracts.get("InnovationGovernor")
    reputation_raw = args.reputation_registry or governance_contracts.get("ReputationRegistry")

    timelock_address = to_checked_address(w3, require_value(timelock_raw, "timelock or CIF_TIMELOCK"), "timelock")
    governor_address = to_checked_address(w3, require_value(governor_raw, "governor or CIF_GOVERNOR"), "governor")
    reputation_registry_address = to_checked_address(
        w3,
        require_value(reputation_raw, "reputation-registry or CIF_REPUTATION_REGISTRY"),
        "reputation-registry",
    )

    account: LocalAccount = Account.from_key(private_key)
    tx = TransactionSender(w3=w3, account=account, gas_price_wei=args.gas_price_wei)

    expected_funding_registry_address = (
        deployment_manifest.get("constructorArgs", {}).get("ReputationRegistry", [None, None])[1]
    )
    predicted_funding_registry_address = predict_create_address(account.address, tx.nonce + 1)
    if expected_funding_registry_address is not None:
        expected_funding_registry_address = to_checked_address(
            w3,
            expected_funding_registry_address,
            "deployment-manifest constructorArgs.ReputationRegistry[1]",
        )
        if expected_funding_registry_address != predicted_funding_registry_address:
            raise RuntimeError(
                "FundingRegistry deployment address no longer matches the address baked into ReputationRegistry. "
                f"Expected {expected_funding_registry_address}, but the next deployment flow will create "
                f"{predicted_funding_registry_address}. Use a clean deployer nonce sequence or rerun the "
                "governance spine deployment before continuing."
            )

    oracle_artifact = load_artifact(ORACLE_ARTIFACT)
    funding_registry_artifact = load_artifact(FUNDING_REGISTRY_ARTIFACT)
    adapter_artifact = load_artifact(ADAPTER_ARTIFACT)
    treasury_artifact = load_artifact(TREASURY_ARTIFACT)

    oracle_contract = build_contract(w3, oracle_artifact)
    oracle_address, oracle_deploy_tx = tx.send_contract_deployment(
        oracle_contract,
        [
            protocol_config["chainlink"]["ethUsdFeed"],
            protocol_config["chainlink"]["helperStalePriceThreshold"],
        ],
    )

    funding_registry_contract = build_contract(w3, funding_registry_artifact)
    funding_registry_address, funding_registry_deploy_tx = tx.send_contract_deployment(
        funding_registry_contract,
        [timelock_address, governor_address, reputation_registry_address],
    )

    predicted_treasury_address = predict_create_address(account.address, tx.nonce + 1)

    adapter_contract = build_contract(w3, adapter_artifact)
    adapter_address, adapter_deploy_tx = tx.send_contract_deployment(
        adapter_contract,
        [
            predicted_treasury_address,
            protocol_config["assets"]["weth"],
            protocol_config["aave"]["pool"],
            protocol_config["aave"]["aWeth"],
        ],
    )

    treasury_contract = build_contract(w3, treasury_artifact)
    treasury_address, treasury_deploy_tx = tx.send_contract_deployment(
        treasury_contract,
        [
            timelock_address,
            protocol_config["assets"]["weth"],
            oracle_address,
            adapter_address,
            funding_registry_address,
        ],
    )

    if treasury_address != predicted_treasury_address:
        raise RuntimeError(
            f"Predicted treasury address mismatch: expected {predicted_treasury_address}, got {treasury_address}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    deployment_manifest["network"] = protocol_config["network"]
    deployment_manifest.setdefault("contracts", {})
    deployment_manifest.setdefault("transactions", {})
    deployment_manifest.setdefault("externalProtocols", {})
    deployment_manifest.setdefault("constructorArgs", {})
    deployment_manifest.setdefault("config", {})

    deployment_manifest["contracts"].update(
        {
            "TreasuryOracle": oracle_address,
            "FundingRegistry": funding_registry_address,
            "AaveWethAdapter": adapter_address,
            "InnovationTreasury": treasury_address,
        }
    )
    deployment_manifest["externalProtocols"].update(
        {
            "WETH": protocol_config["assets"]["weth"],
            "ChainlinkEthUsdFeed": protocol_config["chainlink"]["ethUsdFeed"],
            "AavePool": protocol_config["aave"]["pool"],
            "AaveAWeth": protocol_config["aave"]["aWeth"],
        }
    )
    deployment_manifest["constructorArgs"].update(
        {
            "TreasuryOracle": [
                protocol_config["chainlink"]["ethUsdFeed"],
                protocol_config["chainlink"]["helperStalePriceThreshold"],
            ],
            "FundingRegistry": [timelock_address, governor_address, reputation_registry_address],
            "AaveWethAdapter": [
                treasury_address,
                protocol_config["assets"]["weth"],
                protocol_config["aave"]["pool"],
                protocol_config["aave"]["aWeth"],
            ],
            "InnovationTreasury": [
                timelock_address,
                protocol_config["assets"]["weth"],
                oracle_address,
                adapter_address,
                funding_registry_address,
            ],
        }
    )
    deployment_manifest["config"]["treasuryProtocolConfig"] = {
        "helperStalePriceThreshold": protocol_config["chainlink"]["helperStalePriceThreshold"],
        "predictedTreasuryAddress": predicted_treasury_address,
        "timelock": timelock_address,
        "governor": governor_address,
        "reputationRegistry": reputation_registry_address,
    }
    deployment_manifest["transactions"].update(
        {
            "deployTreasuryOracle": oracle_deploy_tx,
            "deployFundingRegistry": funding_registry_deploy_tx,
            "deployAaveWethAdapter": adapter_deploy_tx,
            "deployInnovationTreasury": treasury_deploy_tx,
        }
    )

    output_path.write_text(json.dumps(deployment_manifest, indent=2), encoding="utf-8")
    print(f"Treasury deployment manifest written to {output_path}")


if __name__ == "__main__":
    main()
