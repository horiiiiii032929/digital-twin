# Matched development dialogue review: Terra and Luna

Review date: 2026-09-06. Runs: `final-profile-operational-dialogue-development-001-progression-terra-live-001` and `final-profile-operational-dialogue-development-001-progression-live-001`.

**Decision: Refine; this comparison does not justify a model replacement or teaching-quality promotion.** The reviewer is a separate assistant from the implementer, unblinded to model identity. The same four synthetic histories and 16 fixed student stimuli are reused development material, not fresh confirmation or instructor assessment. The [existing prospective rubric](dialogue-progression-assistant-review-rubric-v1.md) is unchanged. This review inspected all 16 Terra tutor responses and generation proposals against the already reviewed [Luna outputs](dialogue-progression-live-001-assistant-review.md). No retrospective semantic pass threshold is introduced.

## Observed comparison

| Dimension/history | Luna | Terra | Interpretation |
| --- | --- | --- | --- |
| Socratic, correct | Explains after correct attempt; application request receives guarded failure | Same explanation after attempt; application request receives generic question about the older update | Terra avoids a failure message but still does not deliver substantive application support. |
| Socratic, incorrect | Partial hint after attempt, then rejection-rule explanation | Guarded failure after attempt, then conditional fragment hint | No progression improvement: Terra does not reach the requested rule explanation in this finite history. |
| Explanatory | Explains first; generic re-elicitation after correct attempt; prerequisite hint on application | Generic elicitation first; explains after correct attempt; conditional fragment hint on application | Mixed: Terra improves one continuation but misses the approved initial explanatory mode. Neither provides a worked application. |
| Never-answer | Generic question after error; guarded failure on application | Guarded failure after error; prerequisite hint on application | Neither delivers a complete solution. Neither demonstrates useful misconception correction consistently. |
| New concept after restart | Socratic/never-answer ask; explanatory explains | Same mode pattern | Four examples support this bounded reset behavior, not general concept-episode control. |

Both runs delivered eight questions, six answers, and two `safe-graph-failure` responses. Luna had two delivered hints and Terra three; counting hints does not establish usefulness. Terra's two failures occur at the incorrect-attempt stage in the Socratic and never-answer histories. The raw proposals label the complete older-update rejection rule as a hint. The existing guard rejects them because that hint covers the sole internally proposed answer span. As with Luna, this is successful defensive validation and failed substantive help at the same time.

Terra's application hints quote “its slot number is older than the stored number”. This is a relevant condition but repeats the scenario already given by the learner and omits the action to take. Its never-answer hint quotes the prerequisite that slot seal attaches a slot number before storage. These are source-grounded partial fragments; the reviewer does not treat their exactness as sufficient evidence of pedagogical quality.

## Operational measurements and limits

Both runs completed four histories, 16 tutor turns, four restarts, and 24/24 accepted external responses, with zero external failures and unchanged files within each run. Terra's recorded requested and returned identities both equal `gpt-5.6-terra`. Reported cost was USD 0.084888 for Terra versus USD 0.0113548 for Luna, approximately 7.48 times as much in these particular runs. These observed costs do not establish general efficiency or price-normalized quality.

The same v2 generation prompt and profiles were used. Infrastructure changed between executions: SQLite contention handling and optional provider-budget concurrency support were added; the Terra run retained per-case provider concurrency one. The run manifests preserve the differing source bindings. It is therefore not an exact single-variable code-frozen experiment. Concurrent G6 work also confounds latency comparison, so no speed ranking is inferred. One realization per model across four deliberately selected histories provides no credible population quality estimate or confidence interval for model superiority.

Retain current release/profile selection. Address the continuation, application-support, and recovery weaknesses through an explicit candidate comparison before promoting teaching quality; a more expensive model alone has not resolved them here. Larger operating simulations may characterize operational behavior while preserving this Refine decision.
