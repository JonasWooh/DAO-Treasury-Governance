from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from export_etherscan_standard_input import build_standard_input


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "deployments" / "deployments.sepolia.json"
DEFAULT_STANDARD_INPUT = ROOT / "output" / "etherscan" / "standard-input.full.json"
ETHERSCAN_V2_API = "https://api.etherscan.io/v2/api"

CHAIN_ID_SEPOLIA = "11155111"
COMPILER_VERSION = "v0.8.24+commit.e11b9ed9"
LICENSE_TYPE_MIT = "3"
EVM_VERSION = "shanghai"

CONTRACT_CONFIG: dict[str, dict[str, Any]] = {
    "CampusInnovationFundToken": {
        "contractname": "src/governance/CampusInnovationFundToken.sol:CampusInnovationFundToken",
        "constructor_types": ["address"],
        "constructor_source": "token_deployer",
    },
    "TimelockController": {
        "contractname": "lib/openzeppelin-contracts/contracts/governance/TimelockController.sol:TimelockController",
        "constructor_types": ["uint256", "address[]", "address[]", "address"],
        "constructor_source": "timelock_static",
    },
    "ReputationRegistry": {
        "contractname": "src/governance/ReputationRegistry.sol:ReputationRegistry",
        "constructor_types": ["address", "address"],
        "constructor_source": "manifest",
    },
    "HybridVotesAdapter": {
        "contractname": "src/governance/HybridVotesAdapter.sol:HybridVotesAdapter",
        "constructor_types": ["address", "address"],
        "constructor_source": "manifest",
    },
    "InnovationGovernor": {
        "contractname": "src/governance/InnovationGovernor.sol:InnovationGovernor",
        "constructor_types": ["address", "address"],
        "constructor_source": "manifest",
    },
    "TreasuryOracle": {
        "contractname": "src/oracle/TreasuryOracle.sol:TreasuryOracle",
        "constructor_types": ["address", "uint256"],
        "constructor_source": "manifest",
    },
    "FundingRegistry": {
        "contractname": "src/funding/FundingRegistry.sol:FundingRegistry",
        "constructor_types": ["address", "address", "address"],
        "constructor_source": "manifest",
    },
    "AaveWethAdapter": {
        "contractname": "src/adapters/AaveWethAdapter.sol:AaveWethAdapter",
        "constructor_types": ["address", "address", "address", "address"],
        "constructor_source": "manifest",
    },
    "InnovationTreasury": {
        "contractname": "src/treasury/InnovationTreasury.sol:InnovationTreasury",
        "constructor_types": ["address", "address", "address", "address", "address"],
        "constructor_source": "manifest",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Sepolia contracts on Etherscan via API V2.")
    parser.add_argument("--api-key", default=os.environ.get("ETHERSCAN_API_KEY"))
    parser.add_argument("--rpc-url", default=os.environ.get("SEPOLIA_RPC_URL"))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--standard-input", default=str(DEFAULT_STANDARD_INPUT))
    parser.add_argument(
        "--deployer-address",
        default=None,
        help="Optional deployer EOA for constructors that depend on the deployment sender.",
    )
    parser.add_argument(
        "--contracts",
        nargs="*",
        default=list(CONTRACT_CONFIG.keys()),
        choices=list(CONTRACT_CONFIG.keys()),
        help="Specific contract keys to verify. Defaults to all project contracts.",
    )
    parser.add_argument("--chain-id", default=CHAIN_ID_SEPOLIA)
    parser.add_argument("--compiler-version", default=COMPILER_VERSION)
    parser.add_argument("--license-type", default=LICENSE_TYPE_MIT)
    parser.add_argument("--evm-version", default=EVM_VERSION)
    parser.add_argument("--poll-seconds", type=int, default=8)
    parser.add_argument("--max-attempts", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def require_value(value: str | None, name: str) -> str:
    if value is None or value.strip() == "":
        raise ValueError(f"Missing required parameter: {name}")
    return value


def pad32(raw: bytes) -> bytes:
    return raw.rjust(32, b"\x00")


def encode_uint256(value: int) -> bytes:
    return value.to_bytes(32, byteorder="big", signed=False)


def encode_address(value: str) -> bytes:
    hex_value = value.lower().removeprefix("0x")
    return pad32(bytes.fromhex(hex_value))


def is_dynamic(sol_type: str) -> bool:
    return sol_type.endswith("[]")


def encode_dynamic_array(base_type: str, values: list[Any]) -> bytes:
    encoded = encode_uint256(len(values))
    for value in values:
        if base_type == "address":
            encoded += encode_address(value)
        elif base_type == "uint256":
            encoded += encode_uint256(int(value))
        else:
            raise ValueError(f"Unsupported dynamic array base type: {base_type}")
    return encoded


def abi_encode(types: list[str], values: list[Any]) -> str:
    head = b""
    tail = b""
    head_size = 32 * len(types)

    for sol_type, value in zip(types, values):
        if is_dynamic(sol_type):
            offset = head_size + len(tail)
            head += encode_uint256(offset)
            tail += encode_dynamic_array(sol_type[:-2], value)
            continue

        if sol_type == "address":
            head += encode_address(value)
        elif sol_type == "uint256":
            head += encode_uint256(int(value))
        else:
            raise ValueError(f"Unsupported ABI type: {sol_type}")

    return "0x" + (head + tail).hex()


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_or_build_standard_input(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return json.dumps(build_standard_input(), separators=(",", ":"))


def json_rpc(rpc_url: str, method: str, params: list[Any]) -> Any:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    request = urllib.request.Request(
        rpc_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    if "error" in result:
        raise RuntimeError(f"RPC error for {method}: {result['error']}")
    return result["result"]


def fetch_tx_sender(rpc_url: str, tx_hash: str) -> str:
    tx = json_rpc(rpc_url, "eth_getTransactionByHash", [tx_hash])
    if tx is None:
        raise RuntimeError(f"Could not fetch transaction {tx_hash} from RPC.")
    return tx["from"]


def constructor_values_for(
    contract_key: str,
    manifest: dict[str, Any],
    rpc_url: str,
    deployer_address: str | None,
) -> list[Any]:
    config = CONTRACT_CONFIG[contract_key]
    source = config["constructor_source"]

    if source == "manifest":
        values = manifest.get("constructorArgs", {}).get(contract_key)
        if values is None:
            raise KeyError(f"constructorArgs.{contract_key} is missing from the deployment manifest.")
        return values

    if source == "token_deployer":
        if deployer_address:
            return [deployer_address]
        tx_hash = manifest["transactions"]["deployToken"]
        return [fetch_tx_sender(rpc_url, tx_hash)]

    if source == "timelock_static":
        if deployer_address:
            deployer = deployer_address
        else:
            tx_hash = manifest["transactions"]["deployTimelock"]
            deployer = fetch_tx_sender(rpc_url, tx_hash)
        return [120, [], ["0x0000000000000000000000000000000000000000"], deployer]

    raise ValueError(f"Unsupported constructor source: {source}")


def post_etherscan(payload: dict[str, str]) -> dict[str, Any]:
    query_keys = {"apikey", "chainid", "module", "action", "guid"}
    query_payload = {key: value for key, value in payload.items() if key in query_keys}
    body_payload = {key: value for key, value in payload.items() if key not in query_keys}

    url = ETHERSCAN_V2_API
    if query_payload:
        url = f"{url}?{urllib.parse.urlencode(query_payload)}"

    body = urllib.parse.urlencode(body_payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def submit_verification(
    api_key: str,
    chain_id: str,
    source_code: str,
    contract_address: str,
    contract_name: str,
    compiler_version: str,
    constructor_arguments: str,
    evm_version: str,
    license_type: str,
) -> dict[str, Any]:
    payload = {
        "apikey": api_key,
        "chainid": chain_id,
        "module": "contract",
        "action": "verifysourcecode",
        "contractaddress": contract_address,
        "sourceCode": source_code,
        "codeformat": "solidity-standard-json-input",
        "contractname": contract_name,
        "compilerversion": compiler_version,
        "optimizationUsed": "1",
        "runs": "200",
        "constructorArguments": constructor_arguments.removeprefix("0x"),
        "evmVersion": evm_version,
        "licenseType": license_type,
    }
    return post_etherscan(payload)


def check_status(api_key: str, chain_id: str, guid: str) -> dict[str, Any]:
    payload = {
        "apikey": api_key,
        "chainid": chain_id,
        "module": "contract",
        "action": "checkverifystatus",
        "guid": guid,
    }
    return post_etherscan(payload)


def main() -> None:
    args = parse_args()

    rpc_url = args.rpc_url
    api_key = args.api_key
    if not args.dry_run:
        api_key = require_value(api_key, "api-key or ETHERSCAN_API_KEY")

    needs_rpc = any(
        CONTRACT_CONFIG[contract_key]["constructor_source"] in {"token_deployer", "timelock_static"}
        for contract_key in args.contracts
    ) and not args.deployer_address
    if needs_rpc:
        rpc_url = require_value(rpc_url, "rpc-url or SEPOLIA_RPC_URL")

    manifest = load_manifest(Path(args.manifest))
    source_code = load_or_build_standard_input(Path(args.standard_input))

    print(f"Using manifest: {Path(args.manifest)}")
    print(f"Using standard input: {Path(args.standard_input)}")
    print(f"Contracts queued: {', '.join(args.contracts)}")

    for contract_key in args.contracts:
        address = manifest["contracts"][contract_key]
        config = CONTRACT_CONFIG[contract_key]
        constructor_values = constructor_values_for(
            contract_key,
            manifest,
            rpc_url,
            args.deployer_address,
        )
        constructor_args = abi_encode(config["constructor_types"], constructor_values)

        print("")
        print(f"[{contract_key}]")
        print(f"Address: {address}")
        print(f"Contract name: {config['contractname']}")
        print(f"Constructor args: {constructor_args}")

        if args.dry_run:
            continue

        submission = submit_verification(
            api_key=api_key,
            chain_id=args.chain_id,
            source_code=source_code,
            contract_address=address,
            contract_name=config["contractname"],
            compiler_version=args.compiler_version,
            constructor_arguments=constructor_args,
            evm_version=args.evm_version,
            license_type=args.license_type,
        )
        print(f"Submit response: {submission}")

        if submission.get("status") != "1":
            print(f"Verification submit failed for {contract_key}.")
            continue

        guid = submission["result"]
        final_status = None
        for attempt in range(1, args.max_attempts + 1):
            time.sleep(args.poll_seconds)
            status = check_status(api_key=api_key, chain_id=args.chain_id, guid=guid)
            print(f"Status attempt {attempt}: {status}")

            result_text = str(status.get("result", ""))
            if "Pass - Verified" in result_text:
                final_status = status
                break
            if "Already Verified" in result_text:
                final_status = status
                break
            if "Fail -" in result_text:
                final_status = status
                break

        if final_status is None:
            print(f"Timed out waiting for final verification status for {contract_key}.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - CLI guard
        print(str(exc), file=sys.stderr)
        raise
