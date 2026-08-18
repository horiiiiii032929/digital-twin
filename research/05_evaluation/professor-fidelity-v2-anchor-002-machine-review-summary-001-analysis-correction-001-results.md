# Professor-fidelity v2 anchor 002 machine-review analysis correction 001

Result ID: `professor-fidelity-v2-anchor-002-machine-review-summary-001-analysis-correction-001`

Date: 2026-08-17

Status: Complete and ineligible

Decision: Refine / Paused. The correction changes the interpretation and
reporting safeguards, but it does not make automated pedagogy eligible or open
development, human audit, or held-out execution.

## Correction

The original closeout incorrectly treated one all-pass pedagogy portfolio on a
deterministic hard-gate failure as a pedagogy-evaluator false pass. The judge
was explicitly blinded to citations, permissions, and deterministic hard-gate
results. The underlying C3 citation-source failure remains valid system
evidence, but the cross-layer disagreement is diagnostic and is not an
evaluator-calibration gate.

The correction also:

- computes pairwise repeat agreement from the preserved labels instead of a
  literal value;
- states that repeat agreement covers two repeated cases, eight condition
  responses, and 48 dimension labels—not 48 independent repeated responses;
- reports citation-source correctness over the eight claim-applicable cases
  per condition while retaining unconditional hard-gate counts over all 12;
- binds future calibrated judgments to the exact run, judge run, model,
  digest, and contract;
- requires every authored human-review dimension and the exact dataset hash;
- stores a SHA-256 for every future canonical judge input.

## Recomputed evidence

- Generation: 48/48 completed at the frozen V4 Pro fingerprint.
- Primary judge: 12 base cases, two repeated cases, eight repeated condition
  responses, 48 repeated dimension labels, and 70 calls.
- Single-label repeat: 33/48 = 68.75%; linear-weighted kappa 0.5707.
- Pairwise repeat: 11/12 = 91.67%, recomputed from source labels.
- Swapped DeepSeek: invalid after 5/12 cases.
- Local Qwen: invalid after 2/12 cases.
- Human reference: 0/48 responses labeled; deferred, not passed or waived.
- Held-out: unopened.

The repeat metrics are clustered within only two cases. They diagnose the
preserved attempt but do not provide a broad independent reliability estimate.

## Corrected gate interpretation

| Gate or diagnostic | Result | Evidence |
| --- | --- | --- |
| Generator completion | Pass | 48/48 responses at the exact fingerprint |
| Primary completion | Pass | 70 calls; all 12 base cases plus two case-level repeats |
| Repeat consistency >= 90% | Fail | 33/48 labels = 68.75% |
| Pairwise repeat consistency >= 90% | Pass, narrow | 11/12 labels = 91.67%; same two repeated cases |
| Swapped run complete | Fail | Invalid after 5/12 cases |
| Qwen sensitivity complete | Fail | Invalid after 2/12 cases |
| Position consistency >= 90% | Unresolved / fail | Invalid partial only; 24/29 = 82.76% |
| Pedagogy all-pass plus hidden hard-gate failure | Diagnostic, not a gate | One C3 citation-source failure; the pedagogy judge could not see it |
| Blinded human reference | Pending | 0/48 response judgments |
| Held-out isolation | Pass | No development or held-out execution |

## Corrected citation denominators

| Condition | Hard gates, all 12 | Structural, all 12 | Action, all 12 | Citation ID, all 12 | Citation source, eight applicable |
| --- | ---: | ---: | ---: | ---: | ---: |
| C0 | 4/12 | 1/12 | 9/12 | 4/12 | 0/8 |
| C1 | 10/12 | 9/12 | 9/12 | 12/12 | 8/8 |
| C2 | 10/12 | 9/12 | 10/12 | 12/12 | 8/8 |
| C3 | 6/12 | 5/12 | 9/12 | 11/12 | 4/8 |

Citation-source correctness still establishes source/locator alignment only.
It does not establish semantic entailment or citation completeness.

## Reproducibility

- Correction code revision:
  `dbd7a71c4fd7da48773f68bd3358faab099ef4cc`.
- Working tree at correction execution: clean.
- Corrected ignored aggregate SHA-256:
  `a4df8b27343d3527cb1ca3574d8a51b2cecf18525d5c720d6e84b3210b58e4fc`.
- Command: `npm run correct:professor-fidelity-anchor-machine`.
- No provider or local-model call was made.
- The original result, record, and raw aggregate remain preserved.

## Decision impact

No decision changes. Automated pedagogy remains ineligible because repeat
consistency failed, both required sensitivity runs are incomplete/invalid, and
the blinded human reference is absent. Development and held-out remain closed,
P3 remains unselected, and the historical selected profile remains unchanged.
