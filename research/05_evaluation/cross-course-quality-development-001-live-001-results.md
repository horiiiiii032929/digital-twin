# Cross-course quality development live 001

## Decision

**Integration failed; Refine the transport and outcome classification.** All 88
product cases completed, but all 44 actual external calls were rejected by
post-response validation. Four further ledger attempts were deliberately injected
timeouts. No semantic model-quality comparison or candidate promotion is supported.

## Execution and scope

The two arms used the 44-case development packet across four fictional
mini-courses. The incumbent retained the selected deterministic composition. The
candidate combined authorized top-five admission, asynchronous question-specific
generation, and approved profile context. Both used actual product services and
profile approval; student history messages were submitted and tutor replies
recorded. Source installation was synthetic, not an ingestion/UI journey.

Revision `e441193c7fa1260ed327ebf43c59483f85817be8` was dirty. The manifest captured
source bindings, packet/profile hashes, file hashes and tracked diff hash before
execution. The model identifier was `gpt-5.6-luna`; limits were 500 attempts and
USD 5, concurrency two. Source labels are AI-authored and pending independent
review. This packet is development data, not sealed confirmation.

## Failure and accounting

The request serializer supported the new `question_specific_profile_tutoring`
task, but the transport's post-response validator did not have the corresponding
task branch. It rejected the returned new response shape as malformed. The
candidate then took its safe failure path rather than delivering assessed content.
The retained ledger records identity, usage and the error, but not the rejected
raw content; this diagnosis does not independently establish that all underlying
model responses were semantically valid.

| Measure | Value |
| --- | --- |
| Product cases / history exceptions | 88 / 0 |
| Actual external attempts / accepted responses | 44 / 0 |
| External malformed-response failures | 44 |
| Separate injected timeout attempts | 4 |
| Input / output / total tokens | 30,739 / 7,486 / 38,225 |
| Reported cost | USD 0.015131 |
| Reserved allowance | USD 0.48 |
| Incumbent mechanical containment diagnostic | 28/44 |
| Candidate mechanical containment diagnostic | 6/44 |

The 28/44 versus 6/44 counts are retained observations of this failed integration,
**not comparative model-quality results**. Mechanical containment does not grade
full semantic correctness even in a successful transport run. Every requested
candidate call failed validation here, contaminating the comparison.

The raw runner returned `development-pending-independent-content-review` because
there were no history exceptions. That label is misleading when all external
responses fail. This result records `integration-failed` and requires the runner
to inspect provider coverage/failure before assigning its decision. The raw
summary and ledgers remain unchanged.

## Next action and evidence

Add the missing response-validation branch and a transport regression test,
correct the runner decision, then execute a separately named development
successor. Reusing this open development packet for an integration correction
does not make it held-out confirmation. Preserve the current failure and cost;
do not rescore it into a success or attribute it to inferior model pedagogy.

[Machine record](records/cross-course-quality-development-001-live-001.json)
contains the execution configuration and hashes for the ignored artifacts under
`reports/generated/cross-course-quality-development-001-live-001/`. The
[quality audit](../../docs/evaluation-quality-audit-2026-09-06.md) describes source
permissions, review limitations and the prospective independent confirmation bar.
