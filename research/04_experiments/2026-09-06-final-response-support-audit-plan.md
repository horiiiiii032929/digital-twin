# Final-response verification boundary study

## Problem, decision and baseline

V16 is not integrated. Its fresh comparison scored103/112 useful, with one critical and two uncertain judgments,
the same useful total as V14; it failed the preregistered gates:
a repaired negative Nelwick answer introduced an unsupported positive passing
example. It also kept generic Hespar and Ulmar starting questions. Preserve these
failures and their original labels; a source-only audit cannot repair missing
pedagogical usefulness. This plan authorizes no implementation or external calls.

The current code validates a draft before assessment and validates/composes a
replacement afterward, but does not independently assess the final replacement's
meaning. `conditional_revision.py` accepts a schema-valid REPAIR; `typed_instruction.py`
requires citations for explanation/feedback units; `compact_instruction.py` checks
action/unit compatibility and source IDs. Whole-chunk association is not entailment.
An elicitation unit may contain an assertion or a prohibited solution, even without
source IDs. `missing_details` and server-rendered boundary prefixes also affect what
the learner sees. Checking only factual units or only the first answer sentence
would miss these paths.

Decision question: does a separate final-output gate materially reduce unsupported
content while preserving useful, stage-appropriate teaching, relative to the fixed
V16 response? Compare exact inputs; do not tune the frozen V16 helper again. The
new boundary separates proposing a response from deciding whether that exact final
response is deliverable. The verifier remains fallible and is not a proof engine.

Freeze completed V16 fresh-study responses and their public source/question/history/
profile bindings as an exposed diagnostic bank before doing anything else. Retain
all112 planned cases, failures, unknown usage and reviewer uncertainty. Do not call
these responses fresh validation, and do not regenerate favorable replacements.
Existing response-generation expense belongs to the historical run, not the added
verifier cost. The new study must include separately authored prospective data
before any integration decision.

## Explicit alternatives

| Candidate | Final decision path | What it can establish |
|---|---|---|
| C0: fixed V16 | Deliver the frozen response unchanged | Baseline usefulness and failures |
| C1: minimal support auditor | Audit the exact response once; pass it unchanged or quarantine it | Added factual-risk detection and its abstention cost; no repair of generic questions |
| C2: final quality verifier | Audit factual support, requested coverage and teaching/policy stage; at most one issue-guided bounded repair; audit the complete repaired response again | Whether verified repair restores usefulness without delivering unchecked new text |

C1 never writes replacement prose and never infers a teaching-policy pass from a
supported fact. It audits factual claims in questions as well as explanation and
feedback, but treats ordinary questions with no asserted proposition as
`no_factual_assertion`, not universally correct. A grounded solution may still be
prohibited graded work or premature disclosure. A factual pass is not permission to
bypass the existing application policy; report academic/style errors left unchanged.

C2 is the candidate for project-level progression. It checks a concrete cue against
actual evidence features and the current concept's attempt history. A generic
request for the learner's existing explanation is not useful merely because it
contains no unsupported claim. The verifier must also preserve direct explanations,
correct-attempt applications, specific misconception correction, repeated-stuck
progression, missing information and privacy/graded boundaries. No broad profile
keyword alone determines the teaching stage.

A different-context call reduces exposure to the reviser's prior diagnosis but
may share the same model's errors. Primary auditors use an explicitly configured
Sol-high client, while a separately versioned issue-guided repair uses Sol-medium. These are the same
model family, not independent truth authorities. A future different-family auditor
would require a separately preregistered comparison, privacy/transport configuration
and cost bound; do not silently substitute it during this study. Human reviewers or
formal checks on carefully specified abstractions remain potential independent
evidence, not outcomes that this plan assumes have happened.

## Input and output contract

Give each unit and missing-detail entry a stable server-assigned ID. Full proposal,
rendered output and context hashes bind the complete content; there are no separate
per-entry hashes. Bind
the audit to the candidate proposal hash, rendered-response hash, source snapshot,
public question, profile version and actual history. The candidate's draft/revision
verdict, diagnosis, gold labels and prior grader scores are excluded. Source IDs,
student text and model-generated messages are untrusted content, not instructions.
Explicit student example conditions are premises for that example, not generally
true course rules; incorrect student attempts must not become supporting evidence.

C1 receives approved source passages, exact final output, the question and only the
public conversational context needed to resolve references/example premises. Its
scope is source-grounded support, not institution policy. C2 additionally receives
the authoritative teaching profile and bounded actual history required for current
stage, plus application policy. Both see the actual rendered prefixes and missing
notices, not only the proposal's source-tagged units.

Prospective typed response (strict schema, no generated final-answer field):

- Exact audited response hash and complete IDs for all units/missing notices.
- Per unit `supported`, `unsupported`, `uncertain` or `no_factual_assertion`;
  bounded evidence-reference IDs and an enumerated issue code; no free prose.
- For C2, `adequate`, `defective` or `uncertain` for requested coverage,
  current-stage teaching move, attempt use and privacy/graded limits, plus the
  affected IDs. Referent uncertainty is recorded explicitly.
- Five quality dimensions with affected entry IDs; no separate model-authored
  request-aspect coverage proof or mapping. Mixed-request controls test this
  limitation; a dimension verdict does not establish complete aspect coverage.
- No confidence-based override, free-form replacement, private chain of thought,
  invented source ID or unbound overall PASS that ignores a defective dimension.

The server derives acceptance: complete schema and identity/hash agreement, no
unsupported/uncertain required support decision, all required C2 quality dimensions
adequate, and successful unchanged application policy/composer checks. Reject
missing/duplicate IDs, altered hashes, unknown sources, malformed output, provider
identity drift and unknown usage. Any such failure quarantines the response and
stops further spending through the shared budget. Never fall back to unchecked
original or repair text. A source-only `no_factual_assertion` does not satisfy C2's
cue/coverage/stage checks.

For C2, a defective first audit may trigger exactly one separately versioned
issue-guided repair call. Supply the original public context, candidate proposal,
server-assigned entries and only validated bounded machine issue codes plus affected
entry IDs. No auditor free prose, gold, reasoning or expected answer enters repair.
The versioned repair instruction explicitly requires fixing reported generic cues,
coverage, support or stage issues while preserving required content; no replacement
action ceiling. This changes the repair intervention: C2 evaluates verification
plus feedback-guided bounded repair, not a pure gate effect or unchanged V16 rerun.

A KEEP result after a failed audit does not reverse the failure: if the proposal
is unchanged (including reserialized equivalent JSON), quarantine without a second
audit. A changed proposal is re-rendered by the actual composer/policy boundary
and audited in full; the final pass must bind to its new hash. If the second audit
fails or is uncertain, quarantine. No third audit, recursive self-improvement or
output-selected retry. Root approved this design revision before implementation.

## Quarantine, deletion and academic limits

Use a fixed application-owned message explaining that this response could not be
verified and requesting an instructor review or a narrower question. Do not assert
that the course material is absent when the problem is verification failure.
Do not actually send a message to an instructor or student during the experiment.
Record `quarantined` separately from useful tutoring; for answerable/source-supported
controls it is a usefulness failure, even if it removes an unsafe claim.

Do not initially delete substrings or splice model prose. A single unit can mix a
correct required negative answer and an unsupported optional converse example;
deterministic whole-unit deletion could discard the requested answer. Model-authored
`optional` labels cannot safely authorize deletion by themselves.

Optional future pruning is a separate candidate: remove only whole units declared
optional before model outputs by the evaluation author/server-owned response
contract, with no cross-unit references or required aspect assigned to them.
Retain original bytes for remaining units. If required coverage cannot be established,
quarantine rather than silently produce an incomplete answer. Re-run composition,
policy and final quality assessment on the pruned exact output; stripping a
warning could otherwise reveal graded content or change an implication's meaning.
No pruning variant is selected or included in this study's primary outcome.

Existing deterministic policy enforcement remains an earlier boundary, but it is
not assumed to detect every semantic solution leak. C2 must evaluate answer content
against the actual academic stage even when the source entails every word. Human
review is a fallback state, not a simulated approval or claimed professor validation.

## Dataset and prospective evaluation

Use two separately reported sets, never averaged to hide a failed confirmation:

1. The exposed112 fixed V16 final responses: diagnostic failure attribution and
   direct C0/C1/C2 comparison. Include all known failed/generic outputs and cases
   that were already adequate. Freeze their source/output hashes after full review.
2. A new128-response bank from64 scenarios, with one adequate and one defective
   final response per scenario. Four strata each contain16 scenario pairs:
   source relations/application; initial/new-concept stages; attempts/progression;
   boundary/mixed evidence. Use new propositions and multi-unit cases, not renamed
   known failures. Both adequate and defective responses must be schema-valid and
   renderable by the actual composer. Authors disclose synthetic permissions,
   source/version/locator hashes and current-stage assumptions.

In the new128 bank, C0 is the authored adequate/flawed response control, not an
actual V16 generation: C0 usefulness is64/128 by construction before checker
intervention. This bank measures preservation and repair behavior, not population
quality uplift over V16. Only the exposed112 bank offers a descriptive actual-V16
comparison. Both use no new Luna generation; actual integrated draft evaluation
remains required after any component pass.

The second bank is authored and cross-reviewed before auditor calls. Define exact
adequate/defective action and unit-count distributions per stratum before sealing
its local input manifest; V16's action-dependent repair makes this necessary.
Include supported required units with unsupported optional examples, required
unsupported answers, unsupported question presuppositions, factual initial-solution
leaks, generic but fact-free cues, valid direct applications, accurate boundaries,
false evidence-absence notices and own/third-party distinctions. Include at least
one pair for each failure type in each applicable stratum. Do not read the existing
sealed confirmation or its builder for either set.

Independent assistant authors/reviewers record disagreements and root adjudication
before any outputs; these are not human-validated gold labels. Reviewer uncertainty
is unqualified and remains in the denominator. The final128-bank hashes, exact
model configuration and implementation source snapshot are an execution precondition;
this plan intentionally contains no fabricated hashes for uncreated artifacts.

Primary fresh-bank progression gates for C2, fixed before outputs:

- At least61/64 adequate responses remain useful and61/64 defective responses
  become useful (minimum122/128,95.31%); no dropping abstentions or failures.
- Each stratum at least30/32 useful; zero verified critical violations across
  every delivered final response, including question/policy content.
- Paired useful total not below C0, and no increase in critical responses relative
  to C0. Known usage, complete planned records and unchanged input/source hashes.
- No unchecked rewritten response, false hash binding or bypass of application
  policy. Any such integration error fails regardless of semantic aggregate.

C1 is a minimum-boundary comparator, not an automatic promotion candidate. Report
unsupported-claim detection recall/precision, false acceptance and false quarantine
on adequate cases, remaining criticals, useful coverage and request completeness.
For C2 add repair invocation rate, successful verified repair rate, failed second
audits and useful responses lost. Decompose data/oracle, support, teaching stage,
coverage, privacy/policy, schema, transport and operational failures. Report per-unit
and whole-response results; optional-unit counts must not inflate scenario sample
size. Resample paired differences by64 scenario pairs stratified by family, rather
than treating128 responses or their units as independent learners. Confidence
intervals describe this synthetic bank only. Zero observed criticals does not prove
zero future risk.

The exposed bank cannot authorize progression if the fresh bank fails. Preserve
both unfavorable and inconclusive results. A fresh pass is Go Deeper for a separately
planned integration, not a release, instructor-fidelity or learning-effect claim.

## Reproduction, budget and stopping

Implement a dedicated offline-response evaluation runner behind an explicit audit
interface; do not add flags to product orchestration during this component study.
For every input replay exact C0, call C1 once, and run C2 with at most audit→repair→audit.
C1 and C2 auditor prompts/tasks are separately versioned and frozen. Auditor model
is Sol-high, cap3000; repair is the separately versioned issue-guided Sol-medium helper, cap3000. Validate
actual Responses payload and conservative request reservation for both before calls.
No new Luna generation occurs. Keep all provider contexts separated and record
roles `support_audit`, `quality_audit`, `repair`, `post_repair_audit` distinctly.

| Set | Inputs | C1 maximum calls | C2 maximum calls | Total call ceiling | Total USD ceiling |
|---|---:|---:|---:|---:|---:|
| Exposed V16 diagnostics | 112 | 112 | 336 | 448 | 71.68 |
| New prospective comparison | 128 | 128 | 384 | 512 | 81.92 |
| Both sets | 240 | 240 | 720 | 960 | 153.60 |

Reserve USD0.16 per allowed call, with nested per-input1/3-call bounds and one shared
hard total ledger. These are worst-case ceilings, not predicted usage or spent
cost. Auditors cannot consume repair allowance or borrow from another input after a
stop; unknown cost halts subsequent calls. Limit four inputs in flight (default four) and retain
input-level lineage across the repair dependency. Source/size limits must fit the
existing transport's conservative reservation check; fail before dispatch if they
do not. Do not increase caps automatically. Record input/output tokens, every role's
actual cost, audit/repair and end-to-end latency, and failure rates; concurrent runs
are not production capacity measurements.

Root confirmed implementation of the isolated helper/tests and the issue-guided
repair design revision within the authorized workflow. Root owns the finite bank
specification, runner and execution provenance; provider dispatch remains conditional
on those preconditions. Before calls, add explicit allowlisted runner
and documented reproducible commands, validate frozen manifests, archive source
and prompt/schema versions, and run injected contracts including malformed/hash/
unknown-usage failures and unchanged KEEP suppression. Registry entries must
retain all named runs and artifact hashes. Do not implement, dispatch, integrate,
relax thresholds or select the candidate merely because this plan exists.

## Root-fixed prospective bank composition

Before new bank authoring or outputs, fix the following64scenario pairs/128responses.
Both drafts in a pair share every public input except proposal. Different source
relations and examples must be authored; no renamed Nelwick/Hespar controls.

| Stratum | Adequate actions and unit counts | Defective actions and unit counts |
|---|---|---|
| Source relations/application16pairs | instruction16;8one-unit and8three-unit | instruction16;8one-unit and8three-unit, corresponding by pair |
| Initial/new-concept16pairs | question16;one unit each | question8 and instruction8;one unit each |
| Attempts/progression16pairs | instruction16;8one-unit and8two-unit | question8(one unit) and instruction8(two units), corresponding by pair |
| Boundary/mixed16pairs | private3,graded3,clarify3(one unit each);no_evidence3(zero units,one missing notice);partial4(one factual unit,one missing notice) | instruction13(one unit),no_evidence3(zero units,one missing notice) |

Boundary subtypes are3privacy,3graded,3ownunknown,4mixed,3ambiguity; flawed
no-evidence corresponds to three mixed pairs, with the fourth mixed pair containing
an invented answer to the unavailable part. The remaining13flawed are instruction.
Progression contains4correct-attempt,6specific-misconception,6repeated-difficulty
pairs. Initials contain8first-concept and8topic-switch pairs. For initial cues,
require at least one source-relevant feature that supports a meaningful first step;
do not demand every input feature when that would turn a hint into the solution.
Write exact case-specific meanings before outputs; this new criterion does not
alter the preceding112-bank's frozen labels or scores.

In source strata, four of the eight multi-unit pairs specifically combine a
supported required answer with an unsupported optional example; two mix unsupported
assertions into elicitation units and two test entity/event/quantifier changes.
The single-unit pairs cover necessary versus sufficient conditions, explicit
complete procedures, strict/inclusive boundaries, cardinality and conditional
events. Necessary-only sources and complete procedures must be unambiguous;
source review must not infer missing converses or unspecified exclusivity.

Root accepts bounded component implementation within existing user authorization.
No product integration or external dispatch follows from that acceptance. Complete
new-bank cross-review, source/schema/model payload contracts, finite ledger,
preflight, and source/output hashes before any new live study. Existing fixed112
is separately reported diagnostic evidence; the new128bank is fresh exposed
comparison, not the unopened project-level sealed confirmation.

Both banks run sequentially, or share an overall four-input concurrency ceiling.
Previously admitted calls may complete after shared stop; no subsequent admission
is permitted. Concurrency is an operational cap, not a throughput qualification.
