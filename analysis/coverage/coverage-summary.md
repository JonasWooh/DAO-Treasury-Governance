# Coverage Summary

## Commands

```powershell
python scripts/compile_contracts.py --clean
python -m coverage run --source test -m unittest discover -s test -p "test_*.py" -v
python -m coverage xml -o analysis/coverage/python-coverage.xml
python -m coverage json -o analysis/coverage/python-coverage.json
python -m coverage report
```

## Result

- Python test-harness coverage: `99%`
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
Wrote XML report to D:\Codex_Repo\BC_and_CTC_Final\analysis\coverage\python-coverage.xml
```

- `coverage json` output:

```text
Wrote JSON report to D:\Codex_Repo\BC_and_CTC_Final\analysis\coverage\python-coverage.json
```
