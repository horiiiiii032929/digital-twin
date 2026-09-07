# Evidence-linked instructional moves v5

Decision: does a bounded typed instructional representation improve specific
elicitation and feedback after actual learner attempts compared with v4's
hardcoded generic question and concatenated source spans?

Prediction: explicitly representing a task-specific question, evidence-linked
feedback and ordered explanatory steps enables useful continuation that v4
cannot render. V4 remains the control/default; v5 is an explicit opt-in requiring
v4 named-referent and bounded-contract settings. No judge/repair loop is added.

V5 keeps boundary and complete requested-aspect assessment, then adds a typed
instructional question (kind, bounded text, focus lineage), at most three bounded
explanation steps with approved exact support spans and declared aspect indexes,
and optional bounded feedback tied to an exact current learner excerpt and
approved support. Focus must be a current-message substring or an exact approved
current-release concept label; source answer text is not an allowed focus source.
Ask renders only the question. Hint retains the partial-source-span guard and
adds a specific question. Explain renders supported feedback/steps. Every
requested aspect must be assigned to a step; insufficient capacity requires
clarification, never truncation. Existing approval/citation/source/scope gates
remain. Natural prose is confined to typed, length-bounded units; no free trailing
response block is accepted.

Local checks establish structure, lineage and exact-source binding, not semantic
entailment, correct feedback, helpfulness, or non-disclosure in question text.
These limitations are deliberate and must be evaluated independently. A question
can disclose an answer even without citations; a feedback label can be wrong.

Before live calls test provider HTTP envelope/schema dispatch as well as actual
factory integration. Cover specific question, correct/incorrect attempt feedback,
unknown focus, unsupported prose references, absent evidence, privacy/integrity,
full-answer hint, missing aspect coverage and output limits. No provider calls
until the separately prepared finite v4/v5 packet and rubric are frozen.

The independent packet covers four synthetic courses, distinct dialogue forms,
actual submitted histories, boundaries and adverse cases. A separate unchanged
confirmation set remains unused during development. Evaluate semantic usefulness,
requested-detail coverage, premature disclosure, feedback accuracy, source
support and profile progression with transparent independent review; parsing and
span checks are separate mechanical diagnostics. Record all calls, tokens/cost,
latency, exact task/model/config/source hashes and unfavorable cases. No broad
quality or real-learning claim follows from this implementation or unit tests.

## Explicit experimental validation boundary

The incumbent graph validates literal source quotes and would correctly reject
paraphrased instructional prose. V5 therefore needs an explicitly separate
source-binding validator, not a hidden bypass or a fake entailment score. Each
rendered claim retains its exact source bindings. The candidate validator checks
eligible source IDs, exact quoted binding spans, bounded unit counts and complete
binding lineage. Its result explicitly says semantic support is unverified;
`score` denotes structural binding only, `supported_claim_count` remains zero,
and checked bindings are reported separately. No model-derived prose receives
an entailment=1 signal. Existing exact-quote policy remains the default.

A planted wrong paraphrase with a valid binding must be used in contract tests
to demonstrate the limitation: structural binding can pass while meaning is
wrong. Independent semantic review treats unsupported paraphrase and disclosure
as hard failures; this experimental boundary cannot be promoted on structural
success. Check actual graph/audit/UI text does not label this as verified accuracy.
Explanation steps reference already-validated aspect indexes instead of repeating
source quotes; feedback can declare separate exact support where needed. This
reduces output redundancy while preserving source bindings in rendered claims.
