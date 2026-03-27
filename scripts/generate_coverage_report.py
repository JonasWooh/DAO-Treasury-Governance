from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / "analysis" / "coverage"
COVERAGE_DATA = ANALYSIS_DIR / ".coverage"
COVERAGE_XML = ANALYSIS_DIR / "python-coverage.xml"
COVERAGE_JSON = ANALYSIS_DIR / "python-coverage.json"
COVERAGE_TEXT = ANALYSIS_DIR / "coverage-report.txt"
COVERAGE_SUMMARY = ANALYSIS_DIR / "coverage-summary.md"


def run_command(command: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )


def main() -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    run_command([sys.executable, str(ROOT / "scripts" / "compile_contracts.py"), "--clean"])

    env = os.environ.copy()
    env["COVERAGE_FILE"] = str(COVERAGE_DATA)

    test_run = run_command(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--source",
            "test",
            "-m",
            "unittest",
            "discover",
            "-s",
            "test",
            "-p",
            "test_*.py",
            "-v",
        ],
        env=env,
    )

    xml_run = run_command(
        [sys.executable, "-m", "coverage", "xml", "-o", str(COVERAGE_XML)],
        env=env,
    )
    json_run = run_command(
        [sys.executable, "-m", "coverage", "json", "-o", str(COVERAGE_JSON)],
        env=env,
    )
    text_run = run_command([sys.executable, "-m", "coverage", "report"], env=env)

    COVERAGE_TEXT.write_text(text_run.stdout, encoding="utf-8")

    coverage_payload = json.loads(COVERAGE_JSON.read_text(encoding="utf-8"))
    totals = coverage_payload.get("totals", {})
    percent_covered = totals.get("percent_covered_display", "n/a")

    summary = f"""# Coverage Summary

## Commands

```powershell
python scripts/compile_contracts.py --clean
python -m coverage run --source test -m unittest discover -s test -p \"test_*.py\" -v
python -m coverage xml -o analysis/coverage/python-coverage.xml
python -m coverage json -o analysis/coverage/python-coverage.json
python -m coverage report
```

## Result

- Python test-harness coverage: `{percent_covered}%`
- XML artifact: `analysis/coverage/python-coverage.xml`
- JSON artifact: `analysis/coverage/python-coverage.json`
- Console report snapshot: `analysis/coverage/coverage-report.txt`

## Requirement Traceability

| Planned QA Requirement | Covered By |
|---|---|
| governance token minting, delegation, vote snapshots | `test.unit.test_governance_token` |
| governor lifecycle from propose to execute | `test.integration.test_governance_lifecycle` |
| no queue means no execute | `test.integration.test_governance_lifecycle` |
| timelock not expired means no execute | `test.integration.test_governance_lifecycle` |
| EOA direct Treasury call reverts | `test.integration.test_innovation_treasury` |
| unapproved project cannot release milestone | `test.integration.test_innovation_treasury` |
| release beyond approved budget reverts | `test.integration.test_innovation_treasury` |
| reserve-breaking Aave deposit reverts | `test.integration.test_innovation_treasury` |
| stale oracle blocks guarded Treasury NAV | `test.integration.test_innovation_treasury`, `test.unit.test_treasury_oracle` |
| adapter supply/withdraw exactness and failure paths | `test.unit.test_aave_weth_adapter` |

## Raw Coverage Commands

- `coverage xml` output:

```text
{xml_run.stdout.strip()}
```

- `coverage json` output:

```text
{json_run.stdout.strip()}
```
"""
    COVERAGE_SUMMARY.write_text(summary, encoding="utf-8")

    print(f"Coverage artifacts written to {ANALYSIS_DIR}")
    print(test_run.stdout)
    if test_run.stderr:
        print(test_run.stderr, file=sys.stderr)


if __name__ == "__main__":
    main()