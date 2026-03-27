from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import rlp
from eth_utils import keccak, to_canonical_address, to_checksum_address


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts"


def ensure_compiled(*, clean: bool) -> None:
    command = [sys.executable, str(ROOT / "scripts" / "compile_contracts.py")]
    if clean:
        command.append("--clean")
    subprocess.run(command, cwd=ROOT, check=True)


def load_artifact(relative_path: str) -> dict:
    return json.loads((ARTIFACTS_DIR / relative_path).read_text(encoding="utf-8"))


def predict_create_address(deployer: str, nonce: int) -> str:
    encoded = rlp.encode([to_canonical_address(deployer), nonce])
    return to_checksum_address(keccak(encoded)[12:])