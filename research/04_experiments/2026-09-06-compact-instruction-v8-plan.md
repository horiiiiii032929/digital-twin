# Compact instructional composition V8: prospective development plan

## Decision and prediction

Can a smaller standalone rendering contract preserve source authority and improve usable, profile-aligned continuation relative to V4 after V7 failed all three quality gates (main 33/48; boundary 6/8; mixed-stage 5/8)? V7 remains an unfavorable, preserved result. The prediction is fewer representational rejections without additional provider calls. This is not a prediction of guaranteed factuality.

## Baseline and candidate

Keep V4 as the paired literal baseline and retain V5–V7 implementations/configurations for reproduction. V8 is opt-in, has its own task/schema, coherent standalone prompt, implementation identifier and exact source archive. No selected release change follows from implementation or a schema-success improvement alone.

Proposed compact response: action (`question`, `instruction`, `partial`, `no_evidence`, `clarify`, `private`, `graded`); at most four text units, each with kind (`explanation`, `feedback`, `elicitation`), bounded text and approved source IDs; a bounded list of missing requested details. No aspect indexes, model-copied support spans, copied request focus, or copied student excerpt. The server owns current-message linkage. A response with factual feedback followed by elicitation uses `instruction`, not a pure `question` action.

All explanation/feedback units require authorized retrieved source IDs. The server attaches their authoritative citations and exact source chunk bindings. Unknown IDs, contradictory actions, empty instructional responses and invalid field combinations fail closed. Pure questions may have no factual units. Partial responses visibly identify missing items and provide permitted known material or elicitation. Privacy/clarification boundaries use fixed server wording. The model is responsible for selecting the appropriate semantic boundary; structural validation cannot establish that an own-record request was correctly classified.

## Deliberate trust tradeoff

A whole-chunk binding associates the prose with approved material; it does not show that the prose follows from it. Granularity is lower than validated exact spans. Diagnostic metadata must say structural source association and semantic support unverified, with no factual-accuracy score or verified badge. Semantic review must reject invented conditions, removed exceptions, unsolicited policy claims, premature solutions, missing requested details and useless continuation even when every source ID is valid. A planted wrong paraphrase with valid IDs must demonstrate this limitation in tests. No extra judge or repair loop is introduced.

The prompt must distinguish an incorrect learner attempt from absent evidence: approved material may support assessment and correction of an incorrect attempt. It must preserve all requested goals, scope qualifications and permitted pedagogical progression. It contains no fixture strings, course-specific rules or hidden rubric answers.

## Evaluation and failure cases

Reuse the same openly labeled development packets: 48 main contexts, 8 boundary contexts and 8 mixed-stage contexts, with V4 control, the prospectively fixed Luna model and 3000 output-token limit. Keep the unopened confirmation untouched until all existing gates permit it. The runner owner records provider schema failures, delivered actions, latency, billed usage/cost, all outcomes and exact source/input hashes. Reused development is not independent confirmation. No gate is relaxed after observing V8.

Before paid dispatch, test the real factory/graph and fake HTTP transport: supported explanation; feedback plus next prompt; initial Socratic mixed withholding; post-attempt mixed application and absence notices; own-record versus third-party privacy; source exceptions; compound coverage; unknown/cross-course sources; nonempty content; contradictory action; no-evidence; and deliberately unsupported paraphrase admitted structurally but requiring quality rejection. These fixtures demonstrate contract mechanics, not model semantic behavior.

## Diagnostics

Prefer stable, non-sensitive invariant codes for new local failures (unknown_source_id, action_unit_mismatch, missing_detail_required, factual_unit_without_source). Do not log raw private provider bodies or claim that generic root Pydantic errors identify a particular violated predicate. If model-level validators remain, make their invariant labels recoverable independently of user text. Preserve historic V7 limited diagnostics unchanged.

## Execution constraint

This draft is outside the repository while the parent's repository-wide checks run. Independent design review precedes code. No new paid calls are authorized by this draft alone; parent-approved bounded runner dispatch follows stable tested source hashes.

Mixed factual responses declare every generated prose unit, including elicitation, in the source-association audit. For elicitation with no explicit IDs the server uses the union of factual-unit IDs; this does not endorse the question as semantically correct. Pure questions remain claim-free. The standalone scope instruction also forbids unsolicited secondary-concept solutions as a workaround for withholding.
