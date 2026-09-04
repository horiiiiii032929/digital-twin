# Local R1 release qualification 004 — promoted gate

## Decision

**Keep.** The governed V2.1 local Compose release now runs
`dominance-scoped-ambiguity-safe-v3`, the gate
`product-evidence-gate-selection-004` promoted. T0 remains the immediate
one-setting rollback.

This qualification is what the selection rule required before anything shipped.

| Check | Result |
| --- | --- |
| Live HTTPS journey | **25/25** |
| Restart persistence | **6/6** |
| T0 rollback | **6/6** |
| Governed V2.1 restoration | **6/6** |

Runtime: `governed-autonomous-tutoring-graph-v2.1`, evidence gate
`dominance-scoped-ambiguity-safe-v3`, planner `openai-gpt-5.6-terra`,
deterministic generator, profile `student-tutor-r1-local-candidate`
`v2.1-grounding-011`.

- API image: `sha256:c3ee2d4e07de903495aa139eb5c14ac1fc51f5a425501deb2b8f647cda51d4bf`
- Web image: `sha256:675c2e1d6fda3a1853ec50c6b9915de3929a6dd109d82271077085dfdc4833f2`

## What the promoted gate changes

The previous gate let any passage clearing a coverage threshold veto an answer,
with no ranking at all, so a strictly weaker passage saying something else
refused a question its leading passage answered outright. The successor contests
only the passages that tie the leader.

Measured before it was built, on 263 ambiguous targets: 76 had a strictly
dominant leader and in **all 76** that leader was the gold region. The remaining
187 are genuine ties and stay refused — gold sits inside the tied set in 184,
but the best available tiebreaker isolates it in 105 and picks a wrong region in
61, and buying coverage with unsupported releases is the trade the sealed
benchmark priced at 478 down to 4.

On the 500-case development corpus this moves 69 answerable cases from
`clarify` to `answer`: 50.00% fully grounded factual success against the
previous gate's 36.80%, with severe unsupported releases and operational
failures zero in both arms.

## Two runtime bindings widened by evidence

Both refused the promoted gate by name and were narrowed rather than removed.

1. `GOVERNED_DETERMINISTIC_EVIDENCE_GATES` replaces a literal equality on
   `question-targeted-ambiguity-safe-v2`. Governed deterministic generation
   still refuses any gate outside the qualified pairing; the qualified set now
   has two members instead of one, and it grew by measurement.
2. The compose runtime selectors and the V2.1 gate binding were already
   restored in qualification 003 and are unchanged here.

## Limitations

Qualified only on the development Mac through internal-CA HTTPS. Synthetic
identities and open demonstration material only. Establishes no real-professor
fidelity, real-student usability, or learning improvement. Durable public
hosting remains separate work. The promoted gate's development-split evidence
selects a method; it is not a generalization claim, and the product retrieves
through a dense published index while that comparison retrieved locally.
