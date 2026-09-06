# Pedagogical improvement program

## Decision and scope

The user's instruction is to improve the working tutor and include measured
changes in the English LaTeX report. The engineering objective is a useful,
evidence-linked response after a learner question or attempt, with preserved
course, evidence, integrity and persistence boundaries. An actual instructor's
approval and student learning effects cannot be manufactured by code tests.

The immediate causal hypothesis is that the v4 representation discards teaching
content: every elicitation becomes one generic template and every explanation
becomes concatenated quotations. The v5 comparison changes that representation
while retaining v4 as the control, the same provider and approved inputs.
Evidence-linked instructional questions, feedback and explanation steps may
improve usefulness; exact support links do not prove semantic correctness.

## Evaluation sequence

1. Freeze synthetic development contexts, explicit current-turn expectations,
   failure categories and acceptance criteria before observing candidate output.
   Keep separate confirmation sources and contexts untouched during development.
2. Compare v4/v5 under shared provider, output allowance and persistent runtime;
   retain all responses, actual histories, costs, latency, failures and source
   snapshots. Test normal, mistaken, stuck, switched-topic, incomplete-evidence,
   privacy and graded-work contexts.
3. Review meaning and useful progression separately from machine-verifiable
   provenance and action contracts. The rejected advisory judge is not reused
   as an accuracy authority. Assistant review remains explicitly non-human.
4. If development identifies a causal defect, record it and make a prospectively
   named correction; do not overwrite outcomes or consume confirmation as a
   tuning set. Confirmation is attempted only for a frozen candidate that meets
   its development gates.
5. Record a bounded experimental selection only when supported, retaining the
   control. Exercise the same candidate in integration before any broader
   qualification claim. Update report claims, evidence mapping and compile/visual
   checks after observed results are available.

## Limits on the conclusion

A new synthetic packet is stronger than repeatedly testing old failure strings,
but does not replace evaluation on the permitted heterogeneous course portfolio.
A successful local candidate is not automatically a professor-approved release.
No simulated knowledge trajectory, model self-rating or fluent response is
reported as learning benefit. The report preserves the historical 63.25% factual
result and earlier failures alongside subsequent development evidence.

## Measurement rationale

The current approach follows the distinction between question answering and
pedagogical response assessment discussed by [Maurya et al.](https://aclanthology.org/2025.naacl-long.57/).
Their benchmark includes human annotations; this project's assistant-authored
packet does not inherit that validity. Explicit staged tutoring also has precedent
in [Puech et al.](https://aclanthology.org/2025.findings-acl.1348/), but the present
candidate is not a replication of StratL or its student study. These references
motivate the design rather than certify the implementation.

Before live generation, the root assistant reviewed the 16 calibration anchor
texts, with source/profile contexts for representative pairs. Supported paraphrase
and explicit arithmetic/logical application are valid; exact wording is not
required. Fabricated facts, false corrections, full initial disclosure and generic
loops are defects on different axes. This is a second assistant check, not a
human gold-label audit or a measured reviewer-accuracy estimate.

## First development result

The [first paired run](../research/05_evaluation/paired-pedagogy-development-001-live-001-results.md)
completed 168 turns and 216 external calls on the setup-corrected v2 packet.
The [full assistant review](../research/05_evaluation/paired-pedagogy-development-live-001-assistant-review.md)
found 16/48 useful target responses for v4 and 30/48 for v5. V5's 8/16 primary
instructional targets also fell short of the prespecified 13/16 threshold.
No critical violation was identified; that finding is limited to this review.
Confirmation remains closed because the development gates failed.

Local replay identified all 29 v5 guarded failures: twelve punctuation checks,
six prohibited feedback/elicitation combinations, ten full-answer hint guards,
and one non-exact hint. These are the first failing checks and can overlap in
underlying cause. The [v6 plan](../research/04_experiments/2026-09-06-instructional-continuation-v6-plan.md)
addresses the general representation problems while retaining original outcomes,
the v4 control, the same 3,000-token model configuration and the fixed rubric.
Repeated development is explicitly development; it will not be called a fresh
confirmation or independent test set.


## Corrected development result

V6 completed the same 168 paired turns with 216 provider attempts, including
two candidate schema failures. Full assistant review found 43/48 useful targets
and 13/16 primary targets, against the concurrently run control's 15/48 and 1/16.
The main gates passed; this reused development set is not confirmation.

The separate eight-context privacy/partial-evidence sidecar passed only 6/8.
One response omitted absence of the requested personal messages; another
volunteered an access restriction that omitted the permitted staff exception.
No private values were disclosed, and no ordinary policy question was classified
as a third-party disclosure request. Nevertheless, the 7/8 usefulness gate failed.
V6 remains **Refine**, and confirmation remains closed. A successor must preserve
all unavailable requested details and the qualifications of any volunteered
source claim. Mixed-evidence Socratic initial withholding also needs explicit
coverage; the main mixed-evidence cases used an explanation-first profile.

## Request-coverage regression and simpler alternative

V7 failed all three unchanged development gates: main33/48 (primary10/16),
boundary6/8 and mixed-evidence stage5/8. Twelve provider-schema failures and ten
additional local rejections were retained. An inherited instruction allowed
empty missing-evidence aspects while the new schema required them; mixed
responses also confused server-rendered absence notices with source-linked
explanation steps. Request copying and index remapping created additional
mechanical failures. This is evidence against adding further output detail as
a solution by itself.

The next comparison therefore simplifies the response representation to bounded
instructional text units and approved source identifiers. It retains the fixed
quality criteria and source provenance controls, and explicitly does not claim
that whole-chunk association establishes semantic support.

The [adverse review erratum](../research/05_evaluation/pedagogy-secondary-disclosure-review-erratum-001-results.md)
also corrects the earlier v5 result to29/48: a premature unrequested secondary
concept was missed in its original review. The original30/48 rating and raw
outputs remain intact; the correction is separately registered. This reinforces
why assistant review is not human validation or a guarantee of safety.

## Compact representation and explicit profile authority

V8 replaces duplicated source text and indices with bounded instructional units
and approved source identifiers. It improves main usefulness to39/48 and primary
instruction to16/16; both sidecars reach8/8. Six explanatory-profile targets still
receive questions. The narrower schema solves representation failures, not all
teaching-policy conflicts. V9 removes advisory planner fields from model input
when approved profile context is present and makes that profile authoritative.
It reaches45/48, but11/12 explanatory targets fails the prospective12/12 component
criterion. One missing source ID causes a guarded response, and two initial
ambiguous references terminate before clarification. All adverse outcomes remain
in their registered runs.

V10 makes source IDs mandatory for factual units in the provider schema and adds
fresh-conversation clarification before empty-evidence termination. Its main
result is48/48 useful targets,16/16 primary and12/12 explanatory targets; both
sidecars pass8/8. One preceding local rejection remains recorded. The decision
is to freeze V10 for a single unopened confirmation, approved-context comparison,
permissioned course diagnostic, and operational checks using the same selector.
No result here establishes human fidelity, learning benefit or project-wide
representative qualification. The default release remains unchanged.

## Confirmation failure and generation-model comparison

The consumed V10 confirmation has44/48 definite useful targets and15/16 primary,
but fails its zero-critical gate through unsupported cross-entity attribution.
An uncertain implied workflow and two local rejections also remain. The separate
profile-context diagnostic fails at5/6 useful context-on style responses: a
checksum explanation asserts collision-free detection. Three teaching-move
contrasts occur, but only two are fully qualified. These outcomes show that
structural grounding and observed profile responsiveness do not establish truth.

Before increasing response-contract complexity again, compare unchanged V10
with Luna-low, Luna-medium and Sol-low generation while retaining Luna-low
planning. The prospective [model comparison plan](../research/04_experiments/2026-09-06-v10-generation-model-comparison-plan.md)
fixes role bindings, semantic gates, budget and selection rules before outputs.
Any winner needs existing development checks, newly sealed confirmation and
same-configuration application evidence. Neither the failed confirmation nor
historical operations is relabelled as successful qualification.
