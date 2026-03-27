from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from solcx import compile_standard, get_installed_solc_versions, install_solc, set_solc_version


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
ARTIFACTS_DIR = ROOT / "artifacts"
SOLCX_DIR = ROOT / ".tooling" / "solcx"
SOLC_VERSION = "0.8.24"
REMAPPINGS = ["@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile Solidity contracts into JSON artifacts.")
    parser.add_argument(
        "--install-solc",
        action="store_true",
        help="Install the pinned solc version before compiling.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete the existing artifacts directory before writing new artifacts.",
    )
    return parser.parse_args()


def collect_entry_sources() -> dict[str, dict[str, str]]:
    sources: dict[str, dict[str, str]] = {}
    for source_path in sorted(SRC_DIR.rglob("*.sol")):
        source_name = source_path.relative_to(ROOT).as_posix()
        sources[source_name] = {"content": source_path.read_text(encoding="utf-8")}
    return sources


def ensure_solc_available(install_requested: bool) -> None:
    SOLCX_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["SOLCX_BINARY_PATH"] = str(SOLCX_DIR)

    installed = {str(version) for version in get_installed_solc_versions(solcx_binary_path=SOLCX_DIR)}
    if SOLC_VERSION not in installed:
        if not install_requested:
            raise RuntimeError(
                f"solc {SOLC_VERSION} is not installed. Run "
                f"`python scripts/compile_contracts.py --install-solc` first."
            )
        install_solc(SOLC_VERSION, solcx_binary_path=SOLCX_DIR)

    set_solc_version(SOLC_VERSION, solcx_binary_path=SOLCX_DIR)


def compile_contracts() -> dict:
    input_json = {
        "language": "Solidity",
        "sources": collect_entry_sources(),
        "settings": {
            "optimizer": {"enabled": True, "runs": 200},
            "metadata": {"bytecodeHash": "none"},
            "remappings": REMAPPINGS,
            "outputSelection": {
                "*": {
                    "*": [
                        "abi",
                        "evm.bytecode.object",
                        "evm.deployedBytecode.object",
                        "metadata",
                    ]
                }
            },
        },
    }

    return compile_standard(
        input_json,
        base_path=str(ROOT),
        allow_paths=str(ROOT),
    )


def write_artifacts(compiled: dict, clean: bool) -> int:
    if clean and ARTIFACTS_DIR.exists():
        shutil.rmtree(ARTIFACTS_DIR)

    contracts = compiled.get("contracts", {})
    count = 0

    for source_name, contract_map in contracts.items():
        source_root = ARTIFACTS_DIR / Path(source_name).with_suffix("")
        for contract_name, contract_output in contract_map.items():
            artifact_dir = source_root
            artifact_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = artifact_dir / f"{contract_name}.json"

            artifact_payload = {
                "contractName": contract_name,
                "sourceName": source_name,
                "abi": contract_output["abi"],
                "bytecode": contract_output["evm"]["bytecode"]["object"],
                "deployedBytecode": contract_output["evm"]["deployedBytecode"]["object"],
                "metadata": contract_output["metadata"],
            }

            artifact_path.write_text(json.dumps(artifact_payload, indent=2), encoding="utf-8")
            count += 1

    return count


def main() -> None:
    args = parse_args()
    ensure_solc_available(install_requested=args.install_solc)
    compiled = compile_contracts()

    if "errors" in compiled:
        errors = [entry for entry in compiled["errors"] if entry.get("severity") == "error"]
        if errors:
            rendered = json.dumps(errors, indent=2)
            raise RuntimeError(f"Solidity compilation failed:\n{rendered}")

    artifact_count = write_artifacts(compiled=compiled, clean=args.clean)
    print(f"Wrote {artifact_count} contract artifacts to {ARTIFACTS_DIR}")


if __name__ == "__main__":
    main()