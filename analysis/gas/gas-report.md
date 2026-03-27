# Gas Report

## Optimization Pass

- Baseline: InnovationTreasury emitted post-action supplied balances by calling suppliedWethBalance() again.
- Optimized: InnovationTreasury now reuses already-known balance deltas to compute supplied balances without an extra adapter read.

## Measured Actions

| Action | Baseline Gas | Optimized Gas | Delta | Delta % |
|---|---:|---:|---:|---:|
| propose | 75881 | 75881 | 0 | 0.0% |
| castVote | 83515 | 83515 | 0 | 0.0% |
| queue | 145057 | 145057 | 0 | 0.0% |
| execute | 112589 | 112589 | 0 | 0.0% |
| approveProject | 135690 | 135690 | 0 | 0.0% |
| releaseMilestone | 97035 | 97035 | 0 | 0.0% |
| depositIdleFunds | 185507 | 184321 | -1186 | -0.64% |
| withdrawIdleFunds | 82311 | 82407 | 96 | 0.12% |

## Notes

- Governance actions are unchanged by this optimization pass, so their baseline and optimized measurements are identical.
- Treasury action gas was measured against a direct-owner local harness to isolate contract-level execution cost.
- Baseline Treasury measurements were compiled from the pre-optimization event-accounting variant of InnovationTreasury.