# Professor-fidelity v2 anchor 002 DeepSeek primary attempt 002 results

> Correction (2026-08-17): the all-pass pedagogy portfolio paired with a hidden
> citation hard-gate failure is a cross-layer diagnostic, not a false pedagogy
> pass. The judge was intentionally blind to citation and hard-gate evidence.
> See [analysis correction 001](professor-fidelity-v2-anchor-002-machine-review-summary-001-analysis-correction-001-results.md).
> The preserved labels and ineligible decision do not change.

Result ID: `professor-fidelity-v2-anchor-002-deepseek-primary-attempt-002`

Date: 2026-08-14

Status: Complete but calibration-ineligible

Decision: Refine the automated pedagogy evaluator. Retain labels as diagnostic
evidence only; do not use them for condition selection.

## Binding and operation

- Source run: `professor-fidelity-v2-anchor-002`.
- Contract: `per-dimension-pairwise-v4-empty-response-display`, qualified by
  the passed public probe.
- Judge: official `deepseek-v4-pro`, high thinking, JSON mode, no retry.
- Exact fingerprint on all 70 calls:
  `a307abda487cd1b463329ccb945ce396`.
- Clean code revision:
  `a34ff6ecca595901ed41941ae7f209ed94e90a06`.
- Ignored private result SHA-256:
  `d86d554aa42bf372ecb793c0bca432910fe9bbd89a99526b8b5c57b17a6ae41d`.
- Cases: 12 base plus two frozen repeats; 70 calls; every finish reason
  `stop`.
- Cost: USD 0.26753631 for 107,610 input, 253,708 output, and 216,387
  reasoning tokens.
- Quote handling: 2 punctuation/case-only unique source alignments; zero
  semantic or ambiguous fuzzy repairs.

## Reliability result

Across the two repeated cases, single-dimension labels agreed on 33/48
(68.75%) with linear-weighted kappa 0.5707. This fails the prospectively frozen
90% repeat-consistency gate. Pairwise C1/C2 preferences agreed on 11/12
(91.67%), but that narrower pass cannot override the single-label failure.

One C3 response portfolio received all-pass pedagogy labels despite a
deterministic hard-gate failure. This fails the zero-false-pass gate and shows
why pedagogy judgments cannot be interpreted without the deterministic safety
boundary.

## Limitations

The generator and primary judge use the same DeepSeek V4 Pro family. The anchor
is small, and only two cases were repeated. Swapped and Qwen diagnostics did not
complete. No independent human reference exists. The result is useful evidence
of evaluator instability, not evidence that one C0-C3 condition is superior.
