# Evaluation result: post-report-source-assessment-001

## Run identity

Two live component runs on 2026-09-08; code `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty. Status: completed, failed target-support gate. Exact source snapshots and invocation are in each generated directory and machine record. Reproduce with `uv run python -m scripts.run_post_report_assessment --model luna --live --output-dir <new-path>` (Sol uses `--model sol`), after reserving $6 under the shared $30 ledger. Original V1 source is archived; later versions must be identified explicitly.

## Decision context

The [prospective plan](../04_experiments/post-report-source-assessment-001.md) compares literal assessment with the same source-bound semantic assessor under Luna-low and Sol-medium. Prediction: useful paraphrase/contradiction coverage improves without false-correct outcomes or judgments on unsupported targets. No independent human gold validation or default profile change.

## Data and sample size

32 frozen synthetic cases: literal/paraphrase/partial/contradiction/unsupported-addition/question across four concepts, plus eight source/scope/adversarial cases. No real user records. Expected labels and case categories never enter provider requests. One repetition; no provider seed. Small structured diagnostic sample, not broad educational validity. Wilson intervals are recorded but correlations within four concepts limit a population interpretation.

## Exact configuration

Actual `SourceBoundModelAssessor(version="v1")`, canonical source ranges, current-version/permission checks and typed OpenAI Responses transport. Luna-low and Sol-medium, cap 3000, maximum 32 calls/$6 per arm, $0.16 reserved per possible call. Literal baseline uses exact target clauses and abstains on paraphrase/negation. Each source/model configuration is independently archived.

## Aggregate and slice results

| Arm | Exact labels | Non-abstaining coverage | Conditional accuracy | False correct | Unsupported-target judgments | Calls | USD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Literal | 24/32 | 8/32 | 8/8 | 0 | 0 | 0 | 0 |
| [luna](records/post-report-source-assessment-001-luna-live-001.json) | 30/32 | 18/32 | 0.889 | 0 | 1 | 26 | 0.0059766 |
| [sol](records/post-report-source-assessment-001-sol-live-001.json) | 31/32 | 17/32 | 0.941 | 0 | 1 | 26 | 0.0955760 |

Both model arms classified all eight correct attempts and all four explicit contradictions as expected. Literal abstention on paraphrases/contradictions reduces its coverage; its high conditional accuracy is not complete task success. Both models incorrectly marked the unsupported target's assertion incorrect instead of declining to assess an unestablished criterion. Luna also marked one complete answer with an unsupported appended guarantee partial rather than unassessed. These judgments are preserved in per-case records, including quotes/reasons/confidence. Neither model falsely marked a wrong case correct in this small sample.

## Operational measurements

Luna: 26 calls, $0.0059766. Sol: 26 calls, $0.0955760. Unknown costs zero. Six source/scope boundary cases per model prevented calls. Per-model timing, peak process memory and tokens are recorded; source start/end hashes agree. Component latency includes model round trips and processing, not a service load test. Necessary target-support boundary failure is not a disclosure or evidence of actual foreign-source access.

## Failures and limitations

Both returned approximately 0.98–0.99 confidence on an unsupported-target judgment. Confidence alone cannot establish correctness. The source states necessary lease/token conditions; it does not establish an unconditional guarantee or validate the altered target. The predeclared gold requires abstention. Independent reviewers may further examine label wording; their agreement is not available. Existing persisted observations and estimates remain model-dependent evidence, not measured human mastery.

## Decision and next action

**Refine both models; no promotion.** Add an explicit V2 criterion-source gate and distinguish unsupported appended claims from genuinely incomplete attempts. Keep V1 and literal controls. Sol made one fewer label error here at higher cost, but this tiny comparison does not establish it as universally superior. Repeat the fixed packet under V2 and obtain fresh/human confirmation before broader claims. Submitted report unchanged.
