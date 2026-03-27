from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

import compile_contracts


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / "analysis" / "static"
RAW_DIR = ANALYSIS_DIR / "slither-json"
TEMP_PROJECT = Path(tempfile.gettempdir()) / "bc_ctc_slither_project"
TEMP_HOME = Path(tempfile.gettempdir()) / "bc_ctc_slither_env"
SUMMARY_JSON = ANALYSIS_DIR / "slither-summary.json"
SUMMARY_MD = ANALYSIS_DIR / "slither-summary.md"
SLITHER_BIN = (Path(sys.executable).resolve().parent / "Scripts" / "slither.exe") if os.name == "nt" else (Path(sys.executable).resolve().parent / "slither")
SOLC_BIN = ROOT / ".tooling" / "solcx" / "solc-v0.8.24" / ("solc.exe" if os.name == "nt" else "solc")

TARGETS = [
    "src/governance/CampusInnovationFundToken.sol",
    "src/governance/InnovationGovernor.sol",
    "src/treasury/InnovationTreasury.sol",
    "src/oracle/TreasuryOracle.sol",
    "src/adapters/AaveWethAdapter.sol",
]

JUSTIFICATION_NOTES = {
    "src/governance/CampusInnovationFundToken.sol": [
        "Resolved the project-owned shadowing warning by renaming the `nonces` parameter from `owner` to `account`.",
        "Remaining pragma/version findings come from the vendored OpenZeppelin dependency range rather than privileged project code.",
    ],
    "src/governance/InnovationGovernor.sol": [
        "No project-owned access-control or dead-code findings remain in the governor wrapper; the remaining raw findings are inherited from OpenZeppelin Governor/Timelock internals.",
    ],
    "src/treasury/InnovationTreasury.sol": [
        "Added `ReentrancyGuard` and marked `releaseMilestone`, `depositIdleFunds`, and `withdrawIdleFunds` as `nonReentrant` to harden the treasury's external-call paths.",
        "Slither still emits balance-pattern reentrancy warnings because these functions intentionally compare pre/post external-call balances; after the guard, these are reviewed as residual pattern-based warnings rather than exploitable recursive entry.",
        "The remaining timestamp-based stale-price check is intentional and required by the project plan's guarded NAV policy.",
        "No rescue, sweep, arbitrary-call, or privileged ownership-transfer backdoors were introduced; `transferOwnership` and `renounceOwnership` still hard-revert.",
    ],
    "src/oracle/TreasuryOracle.sol": [
        "Added explicit Chainlink round-completeness validation before returning price data.",
        "The remaining `unused-return` signal is acceptable here because the wrapper intentionally exposes only the subset of Chainlink tuple fields needed by the Treasury-facing interface after validating round completeness.",
        "The remaining timestamp checks are intentional because stale-price rejection is part of the required oracle safety policy.",
    ],
    "src/adapters/AaveWethAdapter.sol": [
        "Added `ReentrancyGuard` to both `supply` and `withdraw` to harden the adapter against nested external callbacks.",
        "Slither still emits balance-pattern reentrancy warnings because the adapter deliberately performs strict before/after balance reconciliation around external protocol calls; with `nonReentrant` in place, these were reviewed as residual pattern-based warnings.",
        "`arbitrary-send-erc20` is a false positive here because `transferFrom` always pulls from the immutable `treasury` address and the function is gated by `onlyTreasury`.",
    ],
}

def normalize_return_code(return_code: int) -> int:
    return return_code - 2**32 if return_code > 2**31 - 1 else return_code


def force_remove_readonly(function, path, _excinfo) -> None:
    os.chmod(path, 0o666)
    function(path)

def prepare_temp_project() -> None:
    if TEMP_PROJECT.exists():
        shutil.rmtree(TEMP_PROJECT, onexc=force_remove_readonly)
    if TEMP_HOME.exists():
        shutil.rmtree(TEMP_HOME, onexc=force_remove_readonly)

    shutil.copytree(ROOT / "src", TEMP_PROJECT / "src")
    shutil.copytree(ROOT / "lib", TEMP_PROJECT / "lib", ignore=shutil.ignore_patterns(".git"))
    for foundry_file in TEMP_PROJECT.rglob("foundry.toml"):
        foundry_file.unlink()
    TEMP_HOME.mkdir(parents=True, exist_ok=True)
    (TEMP_HOME / ".solc-select" / "artifacts").mkdir(parents=True, exist_ok=True)


def load_json_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def summarize_production_detectors(target_rel_path: str, detectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    marker = f"({target_rel_path}#"
    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    for detector in detectors:
        description = detector.get("description", "")
        if marker not in description:
            continue

        first_line = description.splitlines()[0]
        key = (
            detector.get("check", "unknown"),
            detector.get("impact", "unknown"),
            detector.get("confidence", "unknown"),
            first_line,
        )
        if key not in grouped:
            grouped[key] = {
                "check": detector.get("check", "unknown"),
                "impact": detector.get("impact", "unknown"),
                "confidence": detector.get("confidence", "unknown"),
                "summary": first_line,
                "occurrences": 1,
            }
        else:
            grouped[key]["occurrences"] += 1

    return list(grouped.values())


def run_slither(target_rel_path: str) -> dict[str, Any]:
    target_path = TEMP_PROJECT / target_rel_path
    json_output_path = RAW_DIR / (Path(target_rel_path).stem + ".json")
    if json_output_path.exists():
        json_output_path.unlink()

    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(TEMP_HOME)
    env["HOME"] = str(TEMP_HOME)
    env["USERPROFILE"] = str(TEMP_HOME)

    command = [
        str(SLITHER_BIN),
        str(target_path),
        "--compile-force-framework",
        "solc",
        "--solc",
        str(SOLC_BIN),
        "--solc-remaps",
        "@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/",
        "--solc-working-dir",
        str(TEMP_PROJECT),
        "--exclude-dependencies",
        "--json",
        str(json_output_path),
    ]
    completed = subprocess.run(
        command,
        cwd=TEMP_PROJECT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    payload = load_json_payload(json_output_path)
    detectors = payload.get("results", {}).get("detectors", []) if payload else []
    production_detectors = summarize_production_detectors(target_rel_path, detectors)
    severity_counts = Counter(item["impact"] for item in production_detectors)

    return {
        "target": target_rel_path,
        "returnCode": normalize_return_code(completed.returncode),
        "rawDetectorCount": len(detectors),
        "productionDetectorCount": len(production_detectors),
        "productionDetectors": production_detectors,
        "severityCounts": dict(severity_counts),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "jsonOutput": str(json_output_path),
        "notes": JUSTIFICATION_NOTES.get(target_rel_path, []),
    }


def write_summary(results: list[dict[str, Any]]) -> None:
    SUMMARY_JSON.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")

    rows = []
    for result in results:
        rows.append(
            "| {target} | {return_code} | {raw_count} | {production_count} | {json_output} |".format(
                target=result["target"],
                return_code=result["returnCode"],
                raw_count=result["rawDetectorCount"],
                production_count=result["productionDetectorCount"],
                json_output=result["jsonOutput"],
            )
        )

    md_parts = [
        "# Slither Summary",
        "",
        "## Command Shape",
        "",
        "```powershell",
        "slither <target.sol> --compile-force-framework solc --solc .tooling/solcx/solc-v0.8.24/solc.exe --solc-remaps \"@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/\" --solc-working-dir <temp-project> --exclude-dependencies --json <output>",
        "```",
        "",
        "## Production Summary",
        "",
        "| Target | Exit Code | Raw Detector Count | Production Detector Count | JSON Artifact |",
        "|---|---:|---:|---:|---|",
        *rows,
        "",
        "## Notes",
        "",
        "- Raw detector counts include dependency noise retained in the full JSON artifacts for auditability.",
        "- Production detector counts only include findings whose descriptions point at the project's own `src/` files.",
        "- Slither exits with `-1` when findings are present; that is expected and indicates analysis completed with reported issues rather than a tooling crash.",
    ]

    for result in results:
        md_parts.extend(
            [
                "",
                f"### {result['target']}",
                "",
                f"- Exit code: `{result['returnCode']}`",
                f"- Raw detector count: `{result['rawDetectorCount']}`",
                f"- Production detector count: `{result['productionDetectorCount']}`",
            ]
        )

        if result["severityCounts"]:
            severity_line = ", ".join(
                f"{severity}={count}" for severity, count in sorted(result["severityCounts"].items())
            )
            md_parts.append(f"- Production severities: {severity_line}")

        if result["notes"]:
            md_parts.append("- Resolution / justification:")
            for note in result["notes"]:
                md_parts.append(f"  - {note}")

        if result["productionDetectors"]:
            md_parts.append("- Production findings:")
            for detector in result["productionDetectors"]:
                occurrence_suffix = f" x{detector['occurrences']}" if detector["occurrences"] > 1 else ""
                md_parts.append(
                    f"  - `{detector['check']}` ({detector['impact']}/{detector['confidence']}){occurrence_suffix}: {detector['summary']}"
                )
        else:
            md_parts.append("- Production findings: none after dependency filtering.")

    SUMMARY_MD.write_text("\n".join(md_parts), encoding="utf-8")


def main() -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    compile_contracts.ensure_solc_available(install_requested=False)
    if not SLITHER_BIN.exists():
        raise FileNotFoundError(f"Slither executable not found at {SLITHER_BIN}")
    if not SOLC_BIN.exists():
        raise FileNotFoundError(f"Solc executable not found at {SOLC_BIN}")

    prepare_temp_project()
    results = [run_slither(target) for target in TARGETS]
    write_summary(results)
    print(f"Slither summary written to {SUMMARY_JSON} and {SUMMARY_MD}")


if __name__ == "__main__":
    main()