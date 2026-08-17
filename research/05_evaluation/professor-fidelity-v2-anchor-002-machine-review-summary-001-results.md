# Professor-fidelity v2 anchor 002 machine-review summary 001 results

> Correction (2026-08-17): the hidden hard-gate disagreement below is a
> cross-layer diagnostic, not a pedagogy-calibration gate, because the judge
> could not see citation or deterministic hard-gate evidence. Current
> interpretation and corrected denominators are recorded in
> [analysis correction 001](professor-fidelity-v2-anchor-002-machine-review-summary-001-analysis-correction-001-results.md).
> This historical result remains unchanged as evidence of the original analysis.

Result ID: `professor-fidelity-v2-anchor-002-machine-review-summary-001`

Date: 2026-08-14

Status: Complete and ineligible

Decision: Refine the automated pedagogy evaluator. Defer both bounded human
packets without treating either as passed, and keep development and held-out
closed.

## Evidence boundary

- Source generation: `professor-fidelity-v2-anchor-002`, 48/48 responses.
- Primary judge: completed contract-v4 attempt 002, 12 base cases plus two
  repeats.
- Swapped judge: invalid attempt 001, 5/12 checkpointed cases.
- Local-Qwen sensitivity: invalid attempt 001, 2/12 checkpointed cases.
- Human reference packet: 48 draft judgments, zero labels filled, blinded
  mapping frozen.
- Separate authoring audit: still unfilled and not waived.
- Held-out access: zero; ledger remains unopened.
- Clean summary revision:
  `3e4d97ef1fec3b91b19c1094f3bf23f3971ee7a2`.
- Ignored aggregate-only raw SHA-256:
  `ec7807949ca319e06c014815cf8ae6ef92cfd051f97dd4403050f34b775cd740`.
- Private response text emitted by the summary: zero.

## Gate result

| Gate | Result | Evidence |
| --- | --- | --- |
| Generator completion | Pass | 48/48 responses, exact V4 Pro fingerprint |
| Primary completion | Pass | 12/12 base cases plus two repeats, 70 calls |
| Repeat consistency ≥ 90% | Fail | 33/48 = 68.75%; weighted kappa 0.5707 |
| Pairwise repeat consistency ≥ 90% | Pass, narrow | 11/12 = 91.67% |
| Swapped run complete | Fail | Invalid after 5/12 cases and 25 checkpointed calls |
| Qwen sensitivity complete | Fail | Invalid after 2/12 cases and 10 local calls |
| Position consistency ≥ 90% | Unresolved/fail | Invalid swapped partial was 24/29 = 82.76% |
| Zero false pedagogy passes | Fail | One C3 portfolio passed all pedagogy labels while a deterministic hard gate failed |
| Blinded human reference | Pending | Packet prepared; 0/48 labels filled |
| Held-out isolation | Pass | No development or held-out execution |

The invalid partial model comparisons are retained for diagnosis only. They do
not count as completed calibration estimates. Primary versus invalid swapped
partial agreement was 72.41% (weighted kappa 0.4897); primary versus invalid
Qwen partial agreement was 15% (weighted kappa 0).

## Condition diagnostics

| Condition | Hard gates | Structural | Action | Citation ID | Citation source |
| --- | ---: | ---: | ---: | ---: | ---: |
| C0 | 4/12 | 1/12 | 9/12 | 4/12 | 4/12 |
| C1 | 10/12 | 9/12 | 9/12 | 12/12 | 12/12 |
| C2 | 10/12 | 9/12 | 10/12 | 12/12 | 12/12 |
| C3 | 6/12 | 5/12 | 9/12 | 11/12 | 7/12 |

C2 has one additional action pass over C1 but no hard-gate or structural gain.
C3 is materially weaker than oracle-evidence C1/C2. Because semantic citation
completeness and calibrated pedagogy remain unresolved, these figures cannot
select a condition.

## Stop point

All authorized non-human anchor work is complete. The next decision is whether
to redesign the evaluator or pause #24 and report the diagnostic outcome. Human
review is not the immediate blocker because the machine calibration already
fails independent gates. If human work resumes later, Codex/models must not
fill either blinded packet.
