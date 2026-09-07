# Bounded disclosure in instructional revision

## Observed failure and decision

V12 StageA repaired32/32 authored defective proposals, but preserved only31/32
adequate ones. In control038 it replaced an appropriate question about a new
concept with its complete recovery rule, despite an attempt concerning only the
preceding concept. Keep the64-call result and its critical failure unchanged.
This is not evidence to lower a gate or open StageB.

V13 retains the Luna draft and one Sol revision, but adds an explicit structural
ceiling to the reviser's role. If the draft action is `question`, `private` or
`graded`, or is `no_evidence` with elicitation units, the revision must use an
elicitation/boundary-only schema: no explanation/feedback units and no
instruction/partial action. Other drafts keep the V12 typed schema. The new
restricted task uses the same revision model, cap, evidence and actual history;
its instruction asks for minimal corrections within that ceiling, preserving an
already appropriate question. It must not embed a withheld solution inside a
question. Structural restriction does not prove this semantic property.

The tradeoff is deliberate: the reviser cannot repair every under-helpful draft
by turning a question into an answer. The draft generator remains responsible
for the teaching move. Retain these residual defects as unqualified, not forced
successes. Never return an unchecked original as a fallback when revision fails.
Do not add subject-specific code, answer templates or iterative retry loops.
Keep V12/V11 and all release defaults selectable and unchanged.

## Implementation and checks

Add explicit `v13-luna-sol` configuration and a distinct prompt/implementation ID.
The two revision tasks both route only to Sol; planning and draft generation
remain Luna-low. Use an actual restricted provider schema plus server validation,
not only a textual request to keep the action. Preserve exact source bindings,
role identity, separate call ledgers, combined-usage scope, unknown-cost stopping,
restart and public-trace exclusion of rejected drafts. A malformed or unavailable
revision fails closed. No new call is added: the same up-to-five-call-per-turn
conservative calculation applies.

Test the restricted schema through the actual provider serializer, appropriate
selection for each draft action, rejection of a factual-unit bypass, retained
unrestricted controls, actual API/worker selection, and absence of model drift.
Include an explicitly planted answer inside an elicitation unit to demonstrate
that passing the structural ceiling is not semantic certification. Meaning-based content
review remains necessary for that failure class.

## Prospective evaluation

StageA reuses the64 exposed controls and adds a separately authored fresh16-case
supplement: eight new-concept scenarios, each with an adequate question and a
schema-valid question containing its prohibited complete solution. Prior attempts
concern another concept. Vary entities, rules and phrasing; do not read the sealed
confirmation or include a checksum answer patch. Independently review all16
source/history/profile/gold mappings before dispatch. Preserve the original64
packet bytes and the earlier V12 outcome; record new supplement and combined
packet hashes and deterministic ordering.

Run all80 once under the frozen V13 source. Require40/40 adequate drafts preserved,
at least30/32 old defective drafts repaired, all8 new defective drafts repaired,
and zero critical errors or uncertain-as-success classifications anywhere. All
planned controls must have known usage and valid identity/source snapshots.
Review actual rendered answers, not action labels; a solution embedded in an
elicitation unit is still a critical error. Separate the32 reused scenario pairs
from eight fresh pairs; these are not80 independent source situations. Record
exact prospective bounds of80 calls/USD12.80 at.16 per call, no output-selected
retry or favorable early stop.

Only if all StageA criteria pass, run the integrated StageB from the
[independent revision plan](2026-09-06-independent-factual-revision-plan.md) with
V13 and its unchanged quality gates, followed conditionally by the unopened
confirmation and permitted real-course checkpoint. One structural restriction
must not inherit V11's content scores or V12's correction scores. Full-composition
quantity, professor generated-response approval, 30-virtual-day operations,
authenticated capacity and browser evidence remain separate completion work.
