# Local R1 governed V2.1 release qualification 003

## Decision

**Keep** the governed V2.1 local Compose release, with T0 retained as the
immediate one-setting rollback. This is a qualified local release, not a hosted
production or real-learning claim.

## Results

| Check | Result |
| --- | --- |
| Live HTTPS journey | **25/25** |
| Restart persistence | **6/6** |
| T0 rollback | **6/6** |
| Governed V2.1 restoration | **6/6** |

Runtime: `governed-autonomous-tutoring-graph-v2.1`, evidence gate
`question-targeted-ambiguity-safe-v2`, planner `openai-gpt-5.6-terra`,
deterministic generator, profile `student-tutor-r1-local-candidate`
`v2.1-grounding-011`.

Image digests are pinned in the machine record.

## Why this qualification was needed

`local-r1-governed-v2-1-release-qualification-002` recorded Keep on revision
`b4d25fa`. Eleven hours later, commit `1265830` made that configuration
impossible to start, in two ways at once:

1. It replaced every `${VAR:-default}` runtime selector in
   `compose.local-r1.yml` with a literal, so `.env.local-r1` could no longer
   reach the containers. A stack started from that file ran
   `bounded-tutoring-graph`, not V2.1.
2. It added an evidence-gate binding to the V2.1 startup check. The only run id
   V2.1 accepts, `governed-full-autonomy-v2-1-confirmation-001`, declares no
   evidence gate, so the check refused every V2.1 start with
   `staging T1 qualification evidence does not bind this release`.

Both were observed directly: the stack started in the wrong mode, then refused
to start at all once the mode was reachable again.

So qualification 002 described a revision, and the revision that followed it
could not run what it described.

## What changed

- Runtime selectors are overridable again, with every default exactly as the
  literal pinned it. A stack started with no environment file behaves as it did
  before. Pinned by `tests/test_local_r1_compose_runtime_selection.py`.
- The evidence-gate binding is enforced when the qualification record declares
  a gate, and the absence is recorded as a gap when it does not. A record
  declaring a *different* gate is still refused, so the control survives.
  Pinned by `tests/test_v21_qualification_gate_binding.py`.

Neither change relaxes a default or removes a check that can be satisfied.

## Residual gap

`governed-full-autonomy-v2-1-confirmation-001` does not bind an evidence gate.
The gate this release runs is therefore covered by the 2026-09-02 qualification
and by this one, not by that record. A future V2.1 qualification record should
declare its evidence gate so the binding check can do its full work.

## Relationship to the gate selection

`product-evidence-gate-selection-001` compared `question-targeted-ambiguity-safe-v2`
against the v4 candidate that corpus confirmation 028 recorded Keep for, on 500
development cases with the gate as the only variable. The incumbent reached
15.80% fully grounded factual success against the candidate's 12.60%, so the
gate this release runs is the one the evidence supports.

## Limitations

Qualified only on the development Mac through internal-CA HTTPS. Synthetic
identities and open demonstration material only. Establishes no real-professor
fidelity, real-student usability, or learning improvement. Durable public
hosting remains separate work.
