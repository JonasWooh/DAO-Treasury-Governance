from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = ROOT / ".githooks" / "pre-commit"


def main() -> None:
    if not HOOK_PATH.exists():
        raise FileNotFoundError(f"Missing git hook script: {HOOK_PATH}")

    os.chmod(HOOK_PATH, 0o755)
    subprocess.run(
        ["git", "config", "--local", "core.hooksPath", ".githooks"],
        cwd=ROOT,
        check=True,
    )
    print("Configured git hooks to use .githooks/")


if __name__ == "__main__":
    main()
