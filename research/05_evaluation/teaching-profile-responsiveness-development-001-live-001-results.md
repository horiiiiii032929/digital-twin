# Teaching-profile responsiveness development 001

## Decision

**Refine. Do not promote as teaching-fidelity completion.** Approved context
changes some model decisions, but the preregistered style-intent diagnostic is
3/6 for both context off and on. Differentiation alone is insufficient. The
current renderer presents the entire source explanation even after a Socratic
question, defeating the intended ask-and-wait behavior.

## Design and results

The [plan](../04_experiments/2026-09-05-project-completion-plan.md) and versioned
packet define two synthetic profiles, two context conditions, three style
questions and three boundaries. All 24isolated actual-runtime cases completed.
Twelve actual Luna reactive-intent calls succeeded with no provider failures;
reported estimated provider cost is USD 0.002261. Boundary/fast paths do not
require model calls. Context candidate is opt-in; the selected release is unchanged.

| Diagnostic | Context off | Context on |
| --- | --- | --- |
| Style-intent matches | 3/6 | 3/6 |
| Matched questions with different delivered content | 0/3 | 2/3 |
| Runtime case exceptions | 0/12 | 0/12 |

## Content review and failures

The coding assistant inspected all 24delivered responses; this is not an
independent human/professor assessment. In the candidate's Socratic checksum
response, a diagnostic instruction is immediately followed by the complete
mechanism. The escrow next-step question likewise includes the complete source
explanation. Explanatory settings still produce hints in two cases. Misconception
handling remains identical across settings. These observations support Refine,
not acceptance based merely on differing intent labels.

The 12boundary responses visibly refuse assessed-work solutions or abstain. This
content inspection does not establish all authority-state invariants; the raw
summary correctly leaves independent boundary scoring null. Profile withdrawal,
hash mismatch and malformed-client cases have separate contract tests.

## Provenance and next decision

The [machine record](records/teaching-profile-responsiveness-development-001-live-001.json) retains revision/dirty state,
profile/packet/harness hashes, aggregate diagnostics, per-case output locations
and explicit limitations. Raw evidence is preserved unchanged. This small single
trial does not estimate professor fidelity or learning outcomes. Profile-aware
answer planning/rendering requires a separate general candidate and comparison,
with source support and policy validation retained. Do not rerun sealed consumed
benchmarks to tune this result.
