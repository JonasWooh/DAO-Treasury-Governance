from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
OZ_DIR = ROOT / "lib" / "openzeppelin-contracts" / "contracts"
DEFAULT_OUTPUT = ROOT / "output" / "etherscan" / "standard-input.full.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a full Solidity Standard JSON Input file for Etherscan verification."
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Path to write the Standard JSON Input file.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Write formatted JSON instead of a compact file.",
    )
    return parser.parse_args()


def collect_sources(base_dir: Path) -> dict[str, dict[str, str]]:
    sources: dict[str, dict[str, str]] = {}
    for source_path in sorted(base_dir.rglob("*.sol")):
        source_name = source_path.relative_to(ROOT).as_posix()
        sources[source_name] = {"content": source_path.read_text(encoding="utf-8")}
    return sources


def build_standard_input() -> dict:
    sources = {}
    sources.update(collect_sources(SRC_DIR))
    sources.update(collect_sources(OZ_DIR))

    # Match the deployed artifacts' compiler settings exactly enough for Etherscan verification.
    return {
        "language": "Solidity",
        "sources": sources,
        "settings": {
            "optimizer": {"enabled": True, "runs": 200},
            "evmVersion": "shanghai",
            "metadata": {"bytecodeHash": "none"},
            "remappings": [":@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/"],
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


def main() -> None:
    args = parse_args()
    payload = build_standard_input()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.pretty:
        rendered = json.dumps(payload, indent=2)
    else:
        rendered = json.dumps(payload, separators=(",", ":"))

    output_path.write_text(rendered, encoding="utf-8")
    print(f"Wrote Standard JSON Input to {output_path}")


if __name__ == "__main__":
    main()
