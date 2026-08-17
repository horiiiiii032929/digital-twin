# Professor-fidelity v2 anchor 002 DeepSeek swapped attempt 001 invalid results

Result ID: `professor-fidelity-v2-anchor-002-deepseek-swapped-attempt-001-invalid`

Date: 2026-08-14

Status: Invalid and stopped; rerun prohibited

Decision: Drop this attempt from calibration and retain its partial aggregate
only as a position-sensitivity warning.

## Result

The contract-v4 swapped-order run checkpointed 5/12 cases and 25 calls at one
exact V4 Pro fingerprint. A subsequent case-6 call returned empty content, so
the runner failed closed and wrote no final result. The failing call was not
checkpointed; its usage must not be invented.

- Clean code revision:
  `a34ff6ecca595901ed41941ae7f209ed94e90a06`.
- Ignored private checkpoint SHA-256:
  `e51f7b5bf1295927ecfb326045aa63cac63109a24ccf613458d7752490c788ef`.
- Checkpointed cost: USD 0.100141785.
- Checkpointed input/output/reasoning tokens: 38,213 / 95,999 / 82,178.
- Retries, Gemma calls, development access, and held-out access: zero.

On the overlapping invalid partial sample, primary-versus-swapped single-label
agreement was 84/116 (72.41%; weighted kappa 0.4897), and pairwise position
agreement was 24/29 (82.76%). Both are below their intended calibration levels,
but neither partial estimate is a valid completed-run metric.

Attempt 001 must not be resumed or rerun. A new swapped attempt would require a
new prospective decision and cannot repair the already failed primary repeat
gate.
