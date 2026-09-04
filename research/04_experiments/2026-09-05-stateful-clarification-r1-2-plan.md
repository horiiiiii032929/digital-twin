# Stateful clarification R1.2 plan

Date: 2026-09-05

Issue: #212

Evaluation ID: `stateful-clarification-confirmation-001`

Status: frozen before the clean network-free execution

## Decision question

Can one persistent, source-derived clarification turn recover genuinely tied
evidence cases without weakening the selected R1.1 fail-closed boundary?

## Why this mechanism

The selected `dominance-scoped-ambiguity-safe-v3` gate is the safest measured
grounding design, but its remaining floor is dominated by genuinely tied
source interpretations. Existing one-turn score, coverage, and citation
tie-breakers selected a wrong region too often to release safely. The next
mechanism therefore changes the interaction contract instead of relaxing the
grounding gate.

Mixed-initiative clarification is established in ambiguous question answering
and information-seeking dialogue. AmbigQA models multiple valid interpretations
of an ambiguous question; Qulac evaluates clarification in information
retrieval; InSCIt treats information-seeking as a conversation grounded in
evidence. These works motivate the mechanism, but this repository's own
product evaluation determines whether it is selected.

- AmbigQA: <https://arxiv.org/abs/2004.10645>
- Qulac: <https://arxiv.org/abs/1907.06554>
- InSCIt: <https://doi.org/10.1162/tacl_a_00559>
- Clarifying-question generation: <https://doi.org/10.1145/3366423.3380126>

## Baseline and candidate

- Baseline: the selected gate returns a terminal `clarify` response for a
  genuine tie.
- Candidate: the same gate emits only the tied, approved source regions. The
  product stores one bounded clarification request, presents two to five
  source-derived interpretations, and answers only after an explicit student
  selection.
- The candidate does not lower evidence, citation, source-version, course,
  release, or policy requirements.
- A reply that does not identify exactly one option remains a safe
  clarification. The product never guesses.

## Prediction

The candidate will recover at least 95% of scripted resolvable ties while
preserving 100% boundary safety, source-version validity, restart consistency,
and idempotency, with no unsupported releases, duplicate deliveries, loops, or
provider calls.

## Frozen confirmation

The fresh public-synthetic package contains 200 product-service cases:

- 120 resolvable two-source ambiguities;
- 40 unambiguous answerable controls;
- 20 no-evidence boundaries; and
- 20 invalid clarification replies.

Every scenario has unique source IDs. The runner exercises the actual
`StudentTutoringService`, SQLite migration, release checks, citation mapping,
restart restoration, and duplicate request handling. It is network-free and
does not read, rerun, or rescore the immutable known 10,000+1,000 package.

## Finite decision rule

Run the frozen confirmation once from a clean committed revision. A valid pass
selects stateful clarification for an R1.2 local candidate, subject to exact
local requalification. A valid quality failure is recorded and stops this
mechanism. Only a demonstrated harness defect may receive one correction.

## Claim boundary

This can establish mechanism correctness for source-bound clarification. It
cannot establish that real students choose the intended option, that learning
improves, or that the tutor matches the real professor.
